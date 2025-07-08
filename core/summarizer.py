"""
부산시청 보도자료 요약기 - BusanNewsSummarizer (삭선 문제 해결)
================================================================
PDF에서 텍스트 추출 → GPT로 요약 → 마크다운 파일 생성
"""

import os
import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
import openai
import fitz  # PyMuPDF
from datetime import datetime
from difflib import SequenceMatcher

from config import (
    OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, TEMPERATURE,
    AVAILABLE_TAGS, MD_DIR, PDF_DIR
)

logger = logging.getLogger(__name__)

class BusanNewsSummarizer:
    """부산시청 보도자료 요약기"""
    
    def __init__(self):
        """초기화"""
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.output_dir = MD_DIR
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        logger.info("✅ BusanNewsSummarizer 초기화 완료")
    
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

    def generate_summary_with_gpt(self, content: str, source_url: str = "") -> Optional[Dict]:
        """GPT를 이용한 요약 생성"""
        try:
            # 내용 길이 제한
            if len(content) > 3000:
                content = content[:3000]
            
            # source_url 기본값
            if not source_url:
                source_url = "https://www.busan.go.kr/nbtnewsBU"
            
            # GPT 프롬프트
            prompt = f"""
다음 부산시청 보도자료를 자연스럽게 상세히 요약해주세요.

**중요 지시사항:**
1. 문서 상단의 날짜를 그대로 사용하세요 (이 날짜를 date 필드에 사용하세요)
2. 문의처는 PDF 오른쪽 상단 표에서 정확히 "담당자" 행의 전화번호만 사용하세요
   - 과장 번호 사용 금지
   - 팀장 번호 사용 금지  
   - 반드시 "담당자" 행의 번호만 사용
   - 예: 담당자 변준철 051-888-1382 → 미디어담당관 (051-888-1382)
   - 예: 담당자 최은락 051-888-3742 → 공공하수인프라과 (051-888-3742)
3. 날짜 범위 표기시 "~" 대신 "-" 또는 "부터"를 사용하세요
   - 잘못된 예: 7월 9일~~30일 (마크다운 취소선 문법)
   - 올바른 예: 7월 9일-30일 또는 7월 9일부터 30일까지
4. 마크다운 문법을 주의해서 사용하세요
   - "~~"는 취소선 문법이므로 날짜 범위에 사용하지 마세요
   - 날짜나 시간 범위는 "-" 또는 "부터~까지" 형태로 표기하세요

보도자료 내용:
{content}

아래 형식으로 작성해주세요:

---
title: "보도자료 제목"
date: "YYYY-MM-DD"
tags: ["태그1"]
thumbnail_summary: "80자 이내 한줄요약"
source_url: "{source_url}"
---

# 상세 요약

## 📋 주요 내용
이번 보도자료의 모든 내용을 자연스럽게 상세히 설명해주세요.

## 🎯 핵심 포인트
- 주요 대상, 일정, 장소, 참여방법, 혜택 등

## 📞 문의 및 신청
해당 부서와 담당자 전화번호만 표기하세요 (예: 공공하수인프라과 (051-888-3742))
반드시 PDF 오른쪽 상단 "담당자" 행의 번호만 사용하세요.

사용 가능한 태그: {', '.join(AVAILABLE_TAGS)}
태그는 1개만 선택해주세요.
"""
            
            logger.info("🤖 GPT 요약 생성 중...")
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "부산시청 보도자료 요약 전문가입니다. frontmatter 형식을 정확히 지켜주세요. 날짜 범위 표기시 마크다운 취소선 문법(~~) 사용을 피해주세요."
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
            
            # 🔧 안전한 source_url 설정 (가장 마지막에)
            if not metadata.get('source_url') or metadata.get('source_url') == "원문_URL_여기_입력":
                metadata['source_url'] = source_url
                summary_text = summary_text.replace("원문_URL_여기_입력", source_url)
            
            # 🔧 문의처 정제 (summary_text 수정 후 별도 처리)
            summary_text = self._clean_contact_info(summary_text)
            
            # 🔧 마크다운 취소선 문법 정제
            summary_text = self._fix_markdown_strikethrough(summary_text)
            
            logger.info("✅ GPT 요약 생성 완료")
            return {
                'metadata': metadata,
                'content': summary_text
            }
                
        except Exception as e:
            logger.error(f"❌ GPT 요약 생성 실패: {e}")
            return None
    
    def _fix_markdown_strikethrough(self, text: str) -> str:
        """🔧 마크다운 취소선 문법 정제"""
        try:
            logger.debug("🔧 마크다운 취소선 문법 정제 시작")
            
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
            
            logger.debug("🔧 마크다운 취소선 문법 정제 완료")
            return text
            
        except Exception as e:
            logger.error(f"❌ 마크다운 취소선 문법 정제 실패: {e}")
            return text
    
    def _clean_contact_info(self, text: str) -> str:
        """🔧 문의처 정제 - GPT가 제대로 안했을 때 백업 처리"""
        try:
            logger.debug("🔧 문의처 정제 시작")
            
            # GPT가 이미 올바른 형태로 만들었는지 확인
            # "부서명 (051-888-XXXX)" 형태가 있으면 그대로 두기
            if re.search(r'[가-힣]{2,}(?:과|팀|실|국|본부|센터)\s*\(051-\d{3}-\d{4}\)', text):
                logger.info("✅ GPT가 올바른 문의처 형태로 생성함")
                return text
            
            # 개인 이름이 포함된 문의처 패턴 찾아서 정제
            contact_patterns = [
                # "김영구 과장 (051-888-3730)" → "공공하수인프라과 (051-888-3742)"
                r'([가-힣]{2,4})\s*(과장|팀장|주임|사무관|담당자?)\s*\(([^)]+)\)',
                # "공공하수인프라과 김영구 과장 (051-888-3730)" 패턴
                r'([가-힣]{2,}(?:과|팀|실|국|본부|센터))\s*([가-힣]{2,4})\s*(과장|팀장|주임|사무관|담당자?)\s*\(([^)]+)\)',
            ]
            
            for pattern in contact_patterns:
                def clean_contact(match):
                    groups = match.groups()
                    if len(groups) == 3:  # 이름 + 직책 + 전화번호
                        return f"해당 부서 ({groups[2]})"
                    elif len(groups) == 4:  # 부서 + 이름 + 직책 + 전화번호
                        dept = groups[0]
                        phone = groups[3]
                        return f"{dept} ({phone})"
                    return match.group(0)
                
                text = re.sub(pattern, clean_contact, text)
            
            logger.debug("🔧 문의처 정제 완료")
            return text
            
        except Exception as e:
            logger.error(f"❌ 문의처 정제 실패: {e}")
            return text
    
    def _parse_frontmatter(self, content: str) -> Optional[Dict]:
        """frontmatter 파싱"""
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
                            metadata[key] = tags if tags else ["전체"]
                        else:
                            metadata[key] = ["전체"]
                    else:
                        metadata[key] = [value] if value else ["전체"]
                else:
                    metadata[key] = value
            
            # 필수 필드 기본값
            if 'title' not in metadata:
                metadata['title'] = "부산시 보도자료"
            if 'date' not in metadata:
                metadata['date'] = datetime.now().strftime("%Y-%m-%d")
            if 'tags' not in metadata:
                metadata['tags'] = ["전체"]
            if 'thumbnail_summary' not in metadata:
                metadata['thumbnail_summary'] = "부산시 보도자료입니다."
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ frontmatter 파싱 실패: {e}")
            return None
    
    def _enhance_tags(self, gpt_tags: List[str], title: str, content: str) -> List[str]:
        """태그 검증 및 개선 (1개만 선택)"""
        try:
            text_for_analysis = f"{title} {content}".lower()
            
            # GPT 태그 중 유효한 것 선택
            for tag in gpt_tags:
                if tag in AVAILABLE_TAGS:
                    return [tag]
            
            # 키워드 매칭
            tag_keywords = {
                "청년·교육": ["청년", "교육", "학교", "대학", "학생"],
                "일자리·경제": ["일자리", "경제", "기업", "산업", "투자"],
                "복지·건강": ["복지", "건강", "의료", "병원", "돌봄"],
                "교통·주거": ["교통", "주거", "주택", "버스", "지하철"],
                "문화·여가": ["문화", "여가", "축제", "공연", "전시"],
                "안전·환경": ["안전", "환경", "화재", "재난", "폐기물"],
                "행정·참여": ["행정", "참여", "시민", "정책", "회의"],
                "관광·소식": ["관광", "소식", "방문", "홍보", "국제"]
            }
            
            tag_scores = {}
            for tag, keywords in tag_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text_for_analysis)
                if score > 0:
                    tag_scores[tag] = score
            
            if tag_scores:
                best_tag = max(tag_scores, key=tag_scores.get)
                return [best_tag]
            
            return ["행정·참여"]  # 기본값
            
        except Exception as e:
            logger.error(f"❌ 태그 개선 실패: {e}")
            return ["전체"]
    
    def create_filename_from_metadata(self, metadata: Dict) -> str:
        """메타데이터로부터 파일명 생성"""
        try:
            title = metadata.get('title', '보도자료')
            date = metadata.get('date', datetime.now().strftime("%Y-%m-%d"))
            tags = metadata.get('tags', ['전체'])
            
            clean_date = date.replace('-', '')
            main_tag = tags[0] if tags else '전체'
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
            
            if filepath.exists():
                backup_path = filepath.with_suffix('.md.bak')
                filepath.rename(backup_path)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(summary_data['content'])
            
            logger.info(f"✅ 마크다운 파일 저장: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ 마크다운 파일 저장 실패: {e}")
            return ""
    
    def _is_duplicate_pdf(self, pdf_path: str) -> Optional[str]:
        """PDF 중복 확인 (간소화)"""
        try:
            pdf_filename = Path(pdf_path).name
            pdf_base = pdf_filename.replace('.pdf', '')
            pdf_normalized = re.sub(r'[^\w가-힣]', '', pdf_base.lower())
            
            md_files = list(Path(self.output_dir).glob("*.md"))
            
            for md_file in md_files:
                md_normalized = re.sub(r'[^\w가-힣]', '', md_file.stem.lower())
                similarity = SequenceMatcher(None, pdf_normalized, md_normalized).ratio()
                
                if similarity >= 0.8:
                    logger.info(f"🔍 중복 파일 발견: {pdf_filename} ≈ {md_file.name}")
                    return str(md_file)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 중복 확인 실패: {e}")
            return None
    
    def process_pdf_file(self, pdf_path: str, source_url: str = "") -> Optional[str]:
        """PDF 파일 처리"""
        try:
            pdf_filename = Path(pdf_path).name
            logger.info(f"🚀 PDF 처리: {pdf_filename}")
            
            # 중복 확인
            existing_md = self._is_duplicate_pdf(pdf_path)
            if existing_md:
                logger.info(f"⏭️ 중복 스킵: {pdf_filename}")
                return existing_md
            
            # 기본 URL 설정
            if not source_url:
                source_url = "https://www.busan.go.kr/nbtnewsBU"
            
            # 텍스트 추출
            content = self.extract_text_from_pdf(pdf_path)
            if not content:
                return None
            
            # GPT 요약
            summary_data = self.generate_summary_with_gpt(content, source_url)
            if not summary_data:
                return None
            
            # 태그 개선
            metadata = summary_data['metadata']
            enhanced_tags = self._enhance_tags(
                metadata.get('tags', ['전체']), 
                metadata.get('title', ''), 
                content
            )
            metadata['tags'] = enhanced_tags
            summary_data['metadata'] = metadata
            
            # 파일 저장
            filename = self.create_filename_from_metadata(metadata)
            md_path = self.save_markdown(summary_data, filename)
            
            if md_path:
                logger.info(f"🎉 완료: {pdf_filename} → {filename}")
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