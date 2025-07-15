"""
부산시청 보도자료 요약기 - BusanNewsSummarizer (개선된 OCR 연락처 추출 + 중복 체크)
================================================================
PDF에서 텍스트 추출 → OCR로 연락처 추출 → GPT로 요약 → 마크다운 파일 생성
"""

import os
import logging
import time
import re
import io
from pathlib import Path
from typing import Dict, List, Optional
import openai
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from datetime import datetime

from config import (
    OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, TEMPERATURE,
    AVAILABLE_TAGS, MD_DIR, PDF_DIR
)

logger = logging.getLogger(__name__)

class BusanNewsSummarizer:
    """부산시청 보도자료 요약기 (개선된 OCR 연락처 추출 + 중복 체크)"""
    
    def __init__(self):
        """초기화"""
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.output_dir = MD_DIR
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Tesseract 경로 설정
        self._setup_tesseract()
        
        logger.info("✅ BusanNewsSummarizer 초기화 완료")
    
    def _setup_tesseract(self):
        """Tesseract OCR 설정"""
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"✅ Tesseract 설정: {path}")
                return
        
        logger.warning("⚠️ Tesseract 경로를 찾을 수 없습니다. OCR 기능이 제한될 수 있습니다.")
    
    def check_existing_md_for_pdf(self, pdf_filename: str) -> Optional[str]:
        """🔧 같은 PDF에서 생성된 기존 MD 파일이 있는지 체크"""
        try:
            md_files = list(Path(self.output_dir).glob("*.md"))
            
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # frontmatter에서 source_pdf 필드 찾기
                    if content.startswith('---'):
                        frontmatter_end = content.find('---', 3)
                        if frontmatter_end > 0:
                            frontmatter = content[3:frontmatter_end]
                            if f'source_pdf: "{pdf_filename}"' in frontmatter:
                                logger.info(f"⏭️ 기존 MD 파일 발견: {md_file.name} (PDF: {pdf_filename})")
                                return str(md_file)
                
                except Exception as e:
                    logger.debug(f"MD 파일 체크 중 오류: {md_file.name} - {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 기존 MD 파일 체크 실패: {e}")
            return None
    
    def extract_contact_with_ocr(self, pdf_path: str) -> str:
        """🔧 개선된 OCR 연락처 추출"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]  # 첫 페이지만
            
            # 고해상도 이미지 변환
            mat = fitz.Matrix(4, 4)  # 4배 확대
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # OCR 실행 (한국어 + 영어)
            ocr_text = pytesseract.image_to_string(img, lang='kor+eng')
            doc.close()
            
            logger.info(f"📋 OCR 추출 텍스트 샘플: {ocr_text[:200]}...")
            
            # 🔧 1단계: 부서명 추출 (다양한 패턴 대응)
            dept_name = self._extract_department_name(ocr_text)
            
            # 🔧 2단계: 연락처 추출 (우선순위별)
            phone_number = self._extract_phone_number(ocr_text)
            
            if phone_number:
                result = f"{dept_name} (051-888-{phone_number})"
                logger.info(f"✅ OCR 연락처 추출 성공: {result}")
                return result
            
            # 연락처를 찾을 수 없는 경우
            logger.warning("⚠️ OCR에서 연락처를 찾을 수 없음")
            return f"{dept_name} 문의"
            
        except Exception as e:
            logger.error(f"❌ OCR 연락처 추출 실패: {e}")
            return "해당 부서 문의"
    
    def _extract_department_name(self, ocr_text: str) -> str:
        """부서명 추출 (과, 담당관 우선 선택)"""
        try:
            # 패턴 1: 담당부서 : 바로 다음 첫 번째 부서만 (과 우선)
            pattern1 = r'담당부서\s*:\s*([가-힣\d]+과)'
            match1 = re.search(pattern1, ocr_text)
            if match1:
                return match1.group(1)
            
            # 패턴 2: 담당부서 : 바로 다음 첫 번째 부서만 (담당관 우선)
            pattern2 = r'담당부서\s*:\s*([가-힣\d]+관)'
            match2 = re.search(pattern2, ocr_text)
            if match2:
                return match2.group(1)
            
            # 패턴 3: 담당부서 다음 줄에서 첫 번째 부서만
            lines = ocr_text.split('\n')
            for i, line in enumerate(lines):
                if '담당부서' in line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # 과, 담당관 우선 찾기
                    dept_match = re.search(r'([가-힣\d]+과|[가-힣\d]+관)', next_line)
                    if dept_match:
                        return dept_match.group(1)
                    # 과, 담당관이 없으면 팀
                    team_match = re.search(r'([가-힣\d]+팀)', next_line)
                    if team_match:
                        return team_match.group(1)
            
            return "해당 부서"
            
        except Exception as e:
            logger.error(f"❌ 부서명 추출 실패: {e}")
            return "해당 부서"
    
    def _extract_phone_number(self, ocr_text: str) -> Optional[str]:
        """연락처 추출 (우선순위별 패턴)"""
        try:
            # 🔧 우선순위 1: 담당자 + 전화번호 직접 매칭
            patterns = [
                # 담당자 이름과 전화번호 매칭
                r'담당자\s+([가-힣]{2,4})\s+051[-.\s]*888[-.\s]*(\d{4})',
                # 담당자 라인의 전화번호
                r'담당자.*?051[-.\s]*888[-.\s]*(\d{4})',
                # 테이블 형태에서 담당자 행의 번호
                r'담당자\s*([가-힣\s]*)\s*051[-.\s]*888[-.\s]*(\d{4})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, ocr_text)
                if matches:
                    # 마지막 그룹이 전화번호
                    phone = matches[0][-1] if isinstance(matches[0], tuple) else matches[0]
                    logger.info(f"✅ 담당자 전화번호 패턴 매칭: {phone}")
                    return phone
            
            # 🔧 우선순위 2: 테이블 구조에서 마지막 줄 (보통 담당자)
            lines = ocr_text.split('\n')
            phone_lines = []
            for line in lines:
                if '051-888-' in line or '051.888.' in line or '051 888 ' in line:
                    phone_match = re.search(r'051[-.\s]*888[-.\s]*(\d{4})', line)
                    if phone_match:
                        phone_lines.append((line, phone_match.group(1)))
            
            if phone_lines:
                # 담당자가 포함된 라인 우선
                for line, phone in phone_lines:
                    if '담당자' in line:
                        logger.info(f"✅ 담당자 라인 매칭: {phone}")
                        return phone
                
                # 담당자가 없으면 마지막 번호 (테이블 구조상 보통 담당자)
                logger.info(f"✅ 마지막 전화번호 선택: {phone_lines[-1][1]}")
                return phone_lines[-1][1]
            
            # 🔧 우선순위 3: 첫 번째 051-888 번호
            general_pattern = r'051[-.\s]*888[-.\s]*(\d{4})'
            general_matches = re.findall(general_pattern, ocr_text)
            if general_matches:
                logger.info(f"✅ 첫 번째 전화번호 사용: {general_matches[0]}")
                return general_matches[0]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 연락처 추출 실패: {e}")
            return None

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        doc = None
        try:
            logger.info(f"📄 PDF 텍스트 추출: {Path(pdf_path).name}")
            
            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 100:
                logger.error("❌ PDF 파일 문제")
                return ""
            
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                return ""
            
            text_parts = []
            for page_num in range(doc.page_count):
                try:
                    page_text = doc[page_num].get_text()
                    if page_text.strip():
                        text_parts.append(page_text)
                except Exception:
                    continue
            
            full_text = "\n".join(text_parts)
            
            # 텍스트 정리
            if full_text:
                full_text = re.sub(r'\n\s*\n', '\n\n', full_text)
                full_text = re.sub(r'[ \t]+', ' ', full_text)
                full_text = re.sub(r'\n[ \t]+', '\n', full_text)
                full_text = re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ.,()[\]{}!?%-]', '', full_text)
                full_text = full_text.strip()
            
            if len(full_text) < 50:
                logger.warning("⚠️ 추출된 텍스트가 너무 짧음")
                return ""
            
            logger.info(f"✅ 텍스트 추출 완료: {len(full_text)}자")
            return full_text
            
        except Exception as e:
            logger.error(f"❌ PDF 텍스트 추출 실패: {e}")
            return ""
        finally:
            if doc:
                try:
                    doc.close()
                except:
                    pass

    def generate_summary_with_gpt(self, content: str, source_url: str = "", pdf_filename: str = "") -> Optional[Dict]:
        """🔧 GPT를 이용한 요약 생성 (source_pdf 필드 추가)"""
        try:
            # 내용 길이 제한
            if len(content) > 3000:
                content = content[:3000]
            
            # source_url 기본값
            if not source_url:
                source_url = "https://www.busan.go.kr/nbtnewsBU"
            
            # GPT 프롬프트 (연락처는 별도 처리, source_pdf 추가)
            prompt = f"""
다음 부산시청 보도자료를 자연스럽게 상세히 요약해주세요.

**🚨 절대 원칙 (반드시 준수!):**
1. **PDF 원문의 모든 내용을 정확히 읽고 이해하세요**
2. **추측하지 말고, PDF에 명시된 내용만 사용하세요**
3. **한 글자, 한 숫자라도 틀리면 안됩니다**

보도자료 내용:
{content}

아래 형식으로 작성해주세요:

---
title: "PDF 제목을 정확히 그대로 복사하세요"
date: "YYYY-MM-DD"
tags: ["태그1"]
thumbnail_summary: "80자 이내 한줄요약"
source_url: "{source_url}"
source_pdf: "{pdf_filename}"
---

# 상세 요약

## 📋 주요 내용
PDF의 모든 내용을 정확하게 상세히 설명해주세요. 특히 숫자, 날짜, 장소, 참석자 등을 원문과 정확히 일치시키세요.

## 🎯 핵심 포인트
- 주요 대상, 일정, 장소, 참여방법, 혜택 등

## 📞 세부문의
[OCR로 별도 추출한 연락처가 여기에 들어갑니다]

사용 가능한 태그: {', '.join(AVAILABLE_TAGS)}
내용의 핵심 목적에 가장 적합한 태그 1개만 선택하세요.

**태그 분류 가이드라인:**
• 청년·교육: 청년 프로그램, 교육 과정, 대학생 행사, 인재양성, 경진대회, 해킹방어대회, 코딩대회, 학생 참여 대회
• 일자리·경제: 기업 유치, 투자 유치, 취업 지원, 경제 정책, 산업 발전
• 복지·건강: 복지 서비스, 의료 지원, 건강 관리, 돌봄 서비스
• 교통·주거: 교통 인프라, 주택 정책, 대중교통, 도로 건설
• 문화·관광: 축제, 공연, 전시, 관광 진흥, 문화 행사
• 안전·환경: 재난 대응, 화재 안전, 환경 보호, 방역, 하수처리, 수질 관리
• 행정·소식: 행정 서비스, 시민 참여, 정책 발표, 시장 업무, 회의, 민원 처리, 대외 협력, 해외 교류, 국제 행사
"""
            
            logger.info("🤖 GPT 요약 생성 중...")
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": """부산시청 보도자료 요약 전문가입니다. 

🎯 핵심 미션: 정확하고 상세한 요약 생성

📋 필수 역량:
- PDF 내용 완벽 이해
- 정확한 정보 추출 (숫자, 날짜, 고유명사)
- 자연스러운 한국어 요약
- 적절한 태그 분류

⚠️ 절대 원칙:
- 현재 PDF에서만 정보 추출 (이전 기억 사용 금지)
- 추측 금지, 명시된 내용만 사용
- 한 글자, 한 숫자도 틀리면 안됨

정확성이 생명입니다. 신중하게 작업하세요."""
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            summary_text = response.choices[0].message.content.strip()
            if not summary_text:
                return None
            
            # frontmatter 파싱
            metadata = self._parse_frontmatter(summary_text)
            if not metadata:
                return None
            
            # GPT 태그 검증
            gpt_tags = metadata.get('tags', [])
            validated_tags = self._validate_gpt_tags(gpt_tags, content)
            metadata['tags'] = validated_tags
            
            # 안전한 source_url 설정
            if not metadata.get('source_url') or metadata.get('source_url') == "원문_URL_여기_입력":
                metadata['source_url'] = source_url
                summary_text = summary_text.replace("원문_URL_여기_입력", source_url)
            
            # 🔧 source_pdf 필드 확인 및 설정
            if not metadata.get('source_pdf'):
                metadata['source_pdf'] = pdf_filename
            
            # 마크다운 취소선 문법 정제
            summary_text = self._fix_markdown_strikethrough(summary_text)
            
            logger.info(f"✅ GPT 요약 생성 완료 (태그: {validated_tags}, PDF: {pdf_filename})")
            return {
                'metadata': metadata,
                'content': summary_text
            }
                
        except Exception as e:
            logger.error(f"❌ GPT 요약 생성 실패: {e}")
            return None
    
    def _validate_gpt_tags(self, gpt_tags: List[str], content: str) -> List[str]:
        """GPT 태그 검증 (GPT 우선, 최소한의 보정만)"""
        try:
            # GPT가 선택한 태그가 유효한 태그 목록에 있으면 그대로 사용
            for tag in gpt_tags:
                if tag in AVAILABLE_TAGS:
                    logger.info(f"✅ GPT 태그 검증 통과: {tag}")
                    return [tag]
            
            # GPT가 유효하지 않은 태그를 선택했을 때만 최소한의 키워드 보정
            logger.warning(f"⚠️ GPT 태그 무효: {gpt_tags}, 키워드 보정 적용")
            
            text_lower = content.lower()
            
            # 8개 태그에 맞춘 키워드 매칭
            if any(keyword in text_lower for keyword in ["청년", "대학생", "학생", "교육", "해킹", "경진대회", "인재양성", "코딩", "해킹방어", "대회"]):
                return ["청년·교육"]
            elif any(keyword in text_lower for keyword in ["투자", "기업", "일자리", "경제", "산업"]):
                return ["일자리·경제"]
            elif any(keyword in text_lower for keyword in ["복지", "건강", "의료", "돌봄"]):
                return ["복지·건강"]
            elif any(keyword in text_lower for keyword in ["교통", "주거", "주택", "버스", "지하철"]):
                return ["교통·주거"]
            elif any(keyword in text_lower for keyword in ["문화", "축제", "공연", "전시", "관광", "여가"]):
                return ["문화·관광"]
            elif any(keyword in text_lower for keyword in ["안전", "화재", "환경", "재난", "하수", "수질"]):
                return ["안전·환경"]
            else:
                return ["행정·소식"]  # 기본값
            
        except Exception as e:
            logger.error(f"❌ 태그 검증 실패: {e}")
            return ["행정·소식"]
    
    def _fix_markdown_strikethrough(self, text: str) -> str:
        """마크다운 취소선 문법 정제"""
        try:
            # 패턴 1: 숫자일~~숫자일 → 숫자일-숫자일
            text = re.sub(r'(\d+일)~~(\d+일)', r'\1-\2', text)
            
            # 패턴 2: 숫자월 숫자일~~숫자일 → 숫자월 숫자일-숫자일
            text = re.sub(r'(\d+월\s*\d+일)~~(\d+일)', r'\1-\2', text)
            
            # 패턴 3: 년.월.일~~년.월.일 → 년.월.일-년.월.일
            text = re.sub(r'(\d+\.\d+\.\d+)~~(\d+\.\d+\.\d+)', r'\1-\2', text)
            
            # 패턴 4: 시간~~시간 → 시간-시간
            text = re.sub(r'(\d+:\d+)~~(\d+:\d+)', r'\1-\2', text)
            
            # 패턴 5: 일반적인 범위 표기 A~~B → A-B
            text = re.sub(r'([가-힣\d\s]+)~~([가-힣\d\s]+)', r'\1-\2', text)
            
            return text
            
        except Exception as e:
            logger.error(f"❌ 마크다운 취소선 문법 정제 실패: {e}")
            return text
    
    def _parse_frontmatter(self, content: str) -> Optional[Dict]:
        """🔧 frontmatter 파싱 (source_pdf 필드 추가)"""
        try:
            if not content.startswith('---'):
                return None
            
            end_idx = content.find('---', 3)
            if end_idx == -1:
                return None
            
            frontmatter_text = content[3:end_idx].strip()
            metadata = {}
            
            for line in frontmatter_text.split('\n'):
                line = line.strip()
                if not line or ':' not in line:
                    continue
                
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                if key == 'tags':
                    if value.startswith('[') and value.endswith(']'):
                        tag_content = value[1:-1].strip()
                        if tag_content:
                            tags = [tag.strip().strip('"\'') for tag in tag_content.split(',') if tag.strip()]
                            metadata[key] = tags if tags else ["행정·소식"]
                        else:
                            metadata[key] = ["행정·소식"]
                    else:
                        metadata[key] = [value] if value else ["행정·소식"]
                else:
                    metadata[key] = value
            
            # 필수 필드 기본값
            if 'title' not in metadata:
                metadata['title'] = "부산시 보도자료"
            if 'date' not in metadata:
                metadata['date'] = datetime.now().strftime("%Y-%m-%d")
            if 'tags' not in metadata:
                metadata['tags'] = ["행정·소식"]
            if 'thumbnail_summary' not in metadata:
                metadata['thumbnail_summary'] = "부산시 보도자료입니다."
            if 'source_pdf' not in metadata:
                metadata['source_pdf'] = ""
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ frontmatter 파싱 실패: {e}")
            return None
    
    def create_filename_from_metadata(self, metadata: Dict) -> str:
        """메타데이터로부터 파일명 생성"""
        try:
            title = metadata.get('title', '보도자료')
            date = metadata.get('date', datetime.now().strftime("%Y-%m-%d"))
            tags = metadata.get('tags', ['행정·소식'])
            
            clean_date = date.replace('-', '')
            main_tag = tags[0] if tags else '행정·소식'
            clean_title = self._clean_title_for_filename(title)
            
            filename = f"{clean_date}_{main_tag}_{clean_title}.md"
            
            if len(filename) > 100:
                clean_title = clean_title[:50]
                filename = f"{clean_date}_{main_tag}_{clean_title}.md"
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ 파일명 생성 실패: {e}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{timestamp}_보도자료.md"
    
    def _clean_title_for_filename(self, title: str) -> str:
        """파일명용 제목 정리"""
        try:
            clean_title = re.sub(r'[<>:"/\\|?*\[\]{}]', '', title)
            clean_title = re.sub(r'\s+', '_', clean_title.strip())
            clean_title = re.sub(r'_+', '_', clean_title)
            
            # 조사 제거 및 단어 제한
            particles = ['의', '을', '를', '에', '서', '로', '으로', '와', '과', '이', '가', '는', '도']
            words = [w for w in clean_title.split('_') if w and w not in particles and len(w) > 1]
            
            if len(words) > 4:
                words = words[:4]
            
            clean_title = '_'.join(words)
            if len(clean_title) > 30:
                clean_title = clean_title[:30]
            
            return clean_title.strip('_') if clean_title else "보도자료"
            
        except Exception as e:
            return "보도자료"
    
    def save_markdown(self, summary_data: Dict, filename: str) -> str:
        """마크다운 파일 저장"""
        try:
            filepath = Path(self.output_dir) / filename
            
            # 파일 존재 체크
            if filepath.exists():
                logger.info(f"⏭️ 파일 이미 존재, 스킵: {filename}")
                return str(filepath)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(summary_data['content'])
            
            logger.info(f"✅ 마크다운 파일 저장: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ 마크다운 파일 저장 실패: {e}")
            return ""
    
    def process_pdf_file(self, pdf_path: str, source_url: str = "") -> Optional[str]:
        """🔧 PDF 파일 처리 (중복 체크 로직 추가)"""
        try:
            pdf_filename = Path(pdf_path).name
            logger.info(f"🚀 PDF 처리: {pdf_filename}")
            
            # 🔧 1단계: 중복 체크 - 같은 PDF에서 생성된 MD 파일이 있는지 확인
            existing_md = self.check_existing_md_for_pdf(pdf_filename)
            if existing_md:
                logger.info(f"⏭️ 이미 처리된 PDF: {pdf_filename} → {Path(existing_md).name}")
                return existing_md
            
            # 기본 URL 설정
            if not source_url:
                source_url = "https://www.busan.go.kr/nbtnewsBU"
            
            # 텍스트 추출
            content = self.extract_text_from_pdf(pdf_path)
            if not content:
                return None
            
            # GPT 요약 (태그 분류 포함, PDF 파일명 전달)
            summary_data = self.generate_summary_with_gpt(content, source_url, pdf_filename)
            if not summary_data:
                return None
            
            # 🔧 개선된 OCR로 연락처 추출 및 교체
            ocr_contact = self.extract_contact_with_ocr(pdf_path)
            
            # 요약 내용에서 "## 📞 세부문의" 섹션 교체
            summary_content = summary_data['content']
            contact_pattern = r'## 📞 세부문의.*?(?=\n##|\Z)'
            new_contact_section = f"## 📞 세부문의\n{ocr_contact}"
            
            summary_content = re.sub(contact_pattern, new_contact_section, summary_content, flags=re.DOTALL)
            summary_data['content'] = summary_content
            
            # 파일명 생성 및 저장
            metadata = summary_data['metadata']
            filename = self.create_filename_from_metadata(metadata)
            
            # 파일 존재 체크 및 중복 방지
            md_path = self.save_markdown(summary_data, filename)
            
            if md_path:
                tag = metadata.get('tags', ['미분류'])[0]
                logger.info(f"🎉 완료: {pdf_filename} → {filename} (태그: {tag}, 연락처: {ocr_contact})")
                return md_path
            
            return None
                
        except Exception as e:
            logger.error(f"❌ PDF 처리 실패 {Path(pdf_path).name}: {e}")
            return None
    
    def process_all_pdfs(self, source_urls: Dict[str, str] = None) -> List[str]:
        """모든 PDF 파일 처리"""
        try:
            pdf_files = list(Path(PDF_DIR).glob("*.pdf"))
            if not pdf_files:
                logger.warning("⚠️ 처리할 PDF 파일이 없습니다")
                return []
            
            logger.info(f"📋 처리할 PDF: {len(pdf_files)}개")
            
            generated_files = []
            for idx, pdf_path in enumerate(pdf_files, 1):
                logger.info(f"📄 [{idx}/{len(pdf_files)}] {pdf_path.name}")
                
                source_url = ""
                if source_urls and pdf_path.name in source_urls:
                    source_url = source_urls[pdf_path.name]
                
                md_file = self.process_pdf_file(str(pdf_path), source_url)
                if md_file:
                    generated_files.append(md_file)
                
                if idx < len(pdf_files):
                    time.sleep(2)  # API 제한
            
            logger.info(f"🎉 처리 완료: {len(generated_files)}개 생성")
            return generated_files
            
        except Exception as e:
            logger.error(f"❌ 전체 처리 실패: {e}")
            return []


# 🧪 테스트 함수
def test_ocr_extraction():
    """OCR 연락처 추출 테스트"""
    summarizer = BusanNewsSummarizer()
    
    # 테스트용 PDF 파일 경로
    test_pdf_path = "./data/pdfs/test_document.pdf"
    
    if os.path.exists(test_pdf_path):
        print("🧪 OCR 연락처 추출 테스트 시작...")
        contact = summarizer.extract_contact_with_ocr(test_pdf_path)
        print(f"📞 추출된 연락처: {contact}")
    else:
        print("⚠️ 테스트 PDF 파일이 없습니다.")


def test_duplicate_check():
    """🧪 중복 체크 로직 테스트"""
    summarizer = BusanNewsSummarizer()
    
    # 기존 MD 파일들 체크
    test_filename = "test_document.pdf"
    existing_md = summarizer.check_existing_md_for_pdf(test_filename)
    
    if existing_md:
        print(f"✅ 중복 체크 성공: {test_filename} → {existing_md}")
    else:
        print(f"⚠️ 기존 MD 파일 없음: {test_filename}")


if __name__ == "__main__":
    # 테스트 실행
    test_ocr_extraction()
    test_duplicate_check()