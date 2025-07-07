"""
부산시청 보도자료 요약기 - BusanNewsSummarizer
===============================================
PDF에서 텍스트 추출 → GPT로 요약 → 마크다운 파일 생성

주요 기능:
- PDF 텍스트 추출 (PyMuPDF 사용)
- OpenAI GPT를 이용한 지능형 요약
- 태그 자동 분류 및 검증
- 마크다운 파일 생성 및 저장
- 개별 URL 포함 지원
- 중복 처리 방지
"""

import os
import logging
import time
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import openai
import fitz  # PyMuPDF
from datetime import datetime

from config import (
    OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, TEMPERATURE,
    AVAILABLE_TAGS, MD_DIR, PDF_DIR, ROOT_DIR
)

# 로거 설정
logger = logging.getLogger(__name__)

class BusanNewsSummarizer:
    """부산시청 보도자료 요약기"""
    
    def __init__(self):
        """초기화"""
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.output_dir = MD_DIR
        
        # 출력 디렉토리 생성
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ BusanNewsSummarizer 초기화 완료")
        logger.info(f"📁 출력 디렉토리: {self.output_dir}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출 (안전성 개선)"""
        doc = None
        try:
            logger.info(f"📄 PDF 텍스트 추출 시작: {Path(pdf_path).name}")
            
            # 파일 존재 및 크기 확인
            if not os.path.exists(pdf_path):
                logger.error(f"❌ PDF 파일이 존재하지 않음: {pdf_path}")
                return ""
            
            file_size = os.path.getsize(pdf_path)
            if file_size < 100:  # 100바이트 미만
                logger.error(f"❌ PDF 파일이 너무 작음: {file_size}바이트")
                return ""
            
            logger.info(f"📊 파일 크기: {file_size:,}바이트")
            
            # PDF 열기
            doc = fitz.open(pdf_path)
            
            if doc.page_count == 0:
                logger.error("❌ PDF에 페이지가 없음")
                return ""
            
            logger.info(f"📑 총 페이지 수: {doc.page_count}")
            
            text_parts = []
            
            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if page_text.strip():
                        text_parts.append(page_text)
                        logger.debug(f"   페이지 {page_num + 1}: {len(page_text)}자 추출")
                    else:
                        logger.warning(f"   페이지 {page_num + 1}: 텍스트 없음")
                        
                except Exception as page_error:
                    logger.warning(f"   페이지 {page_num + 1} 처리 실패: {page_error}")
                    continue
            
            # 전체 텍스트 결합
            full_text = "\n".join(text_parts)
            
            # 텍스트 정리
            if full_text:
                # 1. 과도한 공백 및 줄바꿈 정리
                full_text = re.sub(r'\n\s*\n', '\n\n', full_text)  # 연속된 빈 줄을 2개로 제한
                full_text = re.sub(r'[ \t]+', ' ', full_text)  # 연속된 공백을 1개로
                full_text = re.sub(r'\n[ \t]+', '\n', full_text)  # 줄 시작의 공백 제거
                
                # 2. 불필요한 문자 제거
                full_text = re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ.,()[\]{}!?%-]', '', full_text)
                
                # 3. 최종 정리
                full_text = full_text.strip()
            
            if len(full_text) < 50:
                logger.warning(f"⚠️ 추출된 텍스트가 너무 짧음: {len(full_text)}자")
                return ""
            
            logger.info(f"✅ 텍스트 추출 완료: {len(full_text)}자 ({doc.page_count}페이지)")
            return full_text
            
        except Exception as e:
            logger.error(f"❌ PDF 텍스트 추출 실패: {e}")
            return ""
        
        finally:
            # 🔧 안전한 document 닫기
            if doc is not None:
                try:
                    doc.close()
                    logger.debug("📋 PDF document 닫기 완료")
                except Exception as close_error:
                    logger.warning(f"⚠️ PDF document 닫기 실패: {close_error}")

    
    def generate_summary_with_gpt(self, content: str, source_url: str = "") -> Optional[Dict]:
        """GPT를 이용한 요약 생성"""
        try:
            # 1. 내용 길이 확인 및 제한
            original_length = len(content)
            if original_length > 3000:
                content = content[:3000]
                logger.warning(f"내용이 너무 길어서 3000자로 자름 (원본: {original_length}자)")
            
            # 2. source_url 기본값 설정
            if not source_url:
                source_url = "https://www.busan.go.kr/nbtnewsBU"
                logger.info("source_url이 없어서 기본 URL 사용")
            
            # 3. 프롬프트 생성
            prompt = self._create_summary_prompt(content, source_url)
            
            logger.info("🤖 GPT 요약 생성 요청 중...")
            
            # 4. GPT API 호출
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "당신은 부산시청 보도자료를 요약하는 전문가입니다. 시민들이 쉽게 이해할 수 있도록 자세하고 친근하게 요약해주세요. 반드시 frontmatter 형식을 정확히 지켜주세요."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            summary_text = response.choices[0].message.content.strip()
            
            # 5. 응답 검증 및 파싱
            if not summary_text:
                logger.error("❌ GPT 응답이 비어있음")
                return None
            
            # 6. Frontmatter 파싱
            metadata = self._parse_frontmatter(summary_text)
            if not metadata:
                logger.error("❌ frontmatter 파싱 실패")
                return None
            
            # 7. source_url 재확인 및 수정
            if not metadata.get('source_url') or metadata.get('source_url') == "원문_URL_여기_입력":
                metadata['source_url'] = source_url
                # summary_text에서도 교체
                summary_text = summary_text.replace("원문_URL_여기_입력", source_url)
            
            logger.info("✅ GPT 요약 생성 완료")
            return {
                'metadata': metadata,
                'content': summary_text
            }
                
        except Exception as e:
            logger.error(f"❌ GPT 요약 생성 실패: {e}")
            return None
    
    def _create_summary_prompt(self, content: str, source_url: str) -> str:
        """요약 프롬프트 생성"""
        return f"""
다음 부산시청 보도자료를 자연스럽게 상세히 요약해주세요.

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
이번 보도자료의 모든 내용을 자연스럽게 상세히 설명해주세요. 시민들이 알아야 할 일정, 장소, 참여방법, 혜택, 신청방법, 연락처, 배경, 기대효과, 의미 등 모든 정보를 포함해서 완전히 끝까지 작성해주세요.

## 🎯 핵심 포인트
- 주요 대상: 누구를 위한 정책/행사인지
- 일정 및 장소: 언제, 어디서 진행되는지
- 참여 방법: 어떻게 참여하거나 신청할 수 있는지
- 혜택 및 지원: 어떤 혜택이나 지원을 받을 수 있는지
- 문의처: 자세한 정보나 문의를 위한 연락처

## 📞 문의 및 신청
관련 부서나 기관의 연락처, 웹사이트, 신청 방법 등을 포함해주세요.

사용 가능한 태그: {', '.join(AVAILABLE_TAGS)}
태그는 내용에 가장 적합한 **1개만** 선택해주세요.
반드시 ---로 감싸진 frontmatter 형식을 지켜주세요.
"""
    
    def _parse_frontmatter(self, content: str) -> Optional[Dict]:
        """Frontmatter 파싱"""
        try:
            # frontmatter 구분자 확인
            if not content.startswith('---'):
                logger.error("frontmatter 시작 구분자(---) 없음")
                return None
            
            # 종료 구분자 찾기
            end_idx = content.find('---', 3)
            if end_idx == -1:
                logger.error("frontmatter 종료 구분자(---) 없음")
                return None
            
            # frontmatter 추출
            frontmatter_text = content[3:end_idx].strip()
            
            # YAML 스타일 파싱
            metadata = {}
            for line in frontmatter_text.split('\n'):
                line = line.strip()
                if not line or ':' not in line:
                    continue
                
                try:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 따옴표 제거
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # tags 필드 특별 처리
                    if key == 'tags':
                        if value.startswith('[') and value.endswith(']'):
                            # ["태그1", "태그2"] 형식 파싱
                            tag_content = value[1:-1].strip()
                            if tag_content:
                                # 개별 태그 추출
                                tags = []
                                for tag_item in tag_content.split(','):
                                    tag_item = tag_item.strip().strip('"\'')
                                    if tag_item:
                                        tags.append(tag_item)
                                metadata[key] = tags if tags else ["전체"]
                            else:
                                metadata[key] = ["전체"]
                        else:
                            metadata[key] = [value] if value else ["전체"]
                    else:
                        metadata[key] = value
                        
                except ValueError:
                    logger.warning(f"frontmatter 라인 파싱 실패: {line}")
                    continue
            
            # 필수 필드 확인
            required_fields = ['title', 'date', 'tags', 'thumbnail_summary']
            for field in required_fields:
                if field not in metadata:
                    logger.warning(f"필수 필드 누락: {field}")
                    # 기본값 설정
                    if field == 'title':
                        metadata[field] = "부산시 보도자료"
                    elif field == 'date':
                        metadata[field] = datetime.now().strftime("%Y-%m-%d")
                    elif field == 'tags':
                        metadata[field] = ["전체"]
                    elif field == 'thumbnail_summary':
                        metadata[field] = "부산시 보도자료입니다."
            
            logger.info(f"✅ frontmatter 파싱 완료: {list(metadata.keys())}")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ frontmatter 파싱 실패: {e}")
            return None
    
    def _enhance_tags(self, gpt_tags: List[str], title: str, content: str) -> List[str]:
        """태그 검증 및 개선 (1개만 선택)"""
        try:
            enhanced_tags = []
            text_for_analysis = f"{title} {content}".lower()
            
            # 1. GPT가 제안한 태그 중 유효한 것 선택
            for tag in gpt_tags:
                if tag in AVAILABLE_TAGS:
                    enhanced_tags.append(tag)
                    logger.info(f"✅ 유효한 GPT 태그 사용: {tag}")
                    break  # 첫 번째 유효한 태그만 사용
            
            # 2. 유효한 태그가 없으면 키워드 매칭으로 추론
            if not enhanced_tags:
                logger.info("🔍 키워드 기반 태그 추론 시작...")
                
                tag_keywords = {
                    "청년·교육": ["청년", "교육", "학교", "대학", "학생", "취업", "진로", "인재"],
                    "일자리·경제": ["일자리", "경제", "기업", "산업", "투자", "창업", "고용", "취업"],
                    "복지·건강": ["복지", "건강", "의료", "병원", "돌봄", "지원", "치료", "보건"],
                    "교통·주거": ["교통", "주거", "주택", "버스", "지하철", "도로", "임대", "아파트"],
                    "문화·여가": ["문화", "여가", "축제", "공연", "전시", "예술", "음악", "체육"],
                    "안전·환경": ["안전", "환경", "화재", "재난", "폐기물", "청소", "오염", "방재"],
                    "행정·참여": ["행정", "참여", "시민", "정책", "회의", "협의", "민원", "서비스"],
                    "관광·소식": ["관광", "소식", "방문", "홍보", "외국인", "국제", "여행", "축제"]
                }
                
                tag_scores = {}
                for tag, keywords in tag_keywords.items():
                    score = sum(1 for keyword in keywords if keyword in text_for_analysis)
                    if score > 0:
                        tag_scores[tag] = score
                        logger.debug(f"   {tag}: {score}점")
                
                if tag_scores:
                    best_tag = max(tag_scores, key=tag_scores.get)
                    enhanced_tags.append(best_tag)
                    logger.info(f"✅ 키워드 기반 태그 선택: {best_tag} ({tag_scores[best_tag]}점)")
            
            # 3. 그래도 없으면 제목으로 간단 추론
            if not enhanced_tags:
                logger.info("🎯 제목 기반 태그 추론...")
                
                title_lower = title.lower()
                if any(word in title_lower for word in ["교육", "학교", "청년", "대학"]):
                    enhanced_tags.append("청년·교육")
                elif any(word in title_lower for word in ["경제", "일자리", "기업", "산업"]):
                    enhanced_tags.append("일자리·경제")
                elif any(word in title_lower for word in ["문화", "축제", "공연", "전시"]):
                    enhanced_tags.append("문화·여가")
                elif any(word in title_lower for word in ["안전", "환경", "화재", "재난"]):
                    enhanced_tags.append("안전·환경")
                elif any(word in title_lower for word in ["교통", "주거", "버스", "주택"]):
                    enhanced_tags.append("교통·주거")
                elif any(word in title_lower for word in ["복지", "건강", "의료", "돌봄"]):
                    enhanced_tags.append("복지·건강")
                elif any(word in title_lower for word in ["관광", "방문", "국제", "외국"]):
                    enhanced_tags.append("관광·소식")
                else:
                    enhanced_tags.append("행정·참여")  # 기본값
                
                logger.info(f"✅ 제목 기반 태그 선택: {enhanced_tags[0]}")
            
            # 4. 최종 검증 (1개만 반환)
            final_tags = enhanced_tags[:1]
            logger.info(f"🏷️ 최종 태그: {final_tags}")
            return final_tags
            
        except Exception as e:
            logger.error(f"❌ 태그 개선 실패: {e}")
            return ["전체"]  # 에러 시 기본값
    
    def create_filename_from_metadata(self, metadata: Dict) -> str:
        """메타데이터로부터 파일명 생성"""
        try:
            title = metadata.get('title', '보도자료')
            date = metadata.get('date', datetime.now().strftime("%Y-%m-%d"))
            tags = metadata.get('tags', ['전체'])
            
            # 날짜 형식 변환: 2025-07-03 → 20250703
            clean_date = date.replace('-', '') if date else datetime.now().strftime("%Y%m%d")
            
            # 태그 (첫 번째만)
            main_tag = tags[0] if tags else '전체'
            
            # 제목 정리
            clean_title = self._clean_title_for_filename(title)
            
            # 파일명 생성
            filename = f"{clean_date}_{main_tag}_{clean_title}.md"
            
            # 파일명 길이 제한 (Windows 파일명 제한 고려)
            if len(filename) > 100:
                clean_title = clean_title[:50]
                filename = f"{clean_date}_{main_tag}_{clean_title}.md"
            
            logger.info(f"📝 파일명 생성: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ 파일명 생성 실패: {e}")
            # 기본 파일명
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{timestamp}_보도자료.md"
    
    def _clean_title_for_filename(self, title: str) -> str:
        """파일명용 제목 정리"""
        try:
            # 1. 특수문자 제거 (파일명에 사용할 수 없는 문자)
            clean_title = re.sub(r'[<>:"/\\|?*\[\]{}]', '', title)
            
            # 2. 공백을 언더스코어로 변환
            clean_title = re.sub(r'\s+', '_', clean_title.strip())
            
            # 3. 연속된 언더스코어 제거
            clean_title = re.sub(r'_+', '_', clean_title)
            
            # 4. 조사 제거
            particles = ['의', '을', '를', '에', '서', '로', '으로', '와', '과', '이', '가', '는', '도']
            words = clean_title.split('_')
            filtered_words = []
            
            for word in words:
                if word and word not in particles and len(word) > 1:
                    filtered_words.append(word)
            
            # 5. 단어 개수 제한 (최대 4개)
            if len(filtered_words) > 4:
                filtered_words = filtered_words[:4]
            
            clean_title = '_'.join(filtered_words)
            
            # 6. 길이 제한 (30자)
            if len(clean_title) > 30:
                clean_title = clean_title[:30]
            
            # 7. 앞뒤 언더스코어 제거
            clean_title = clean_title.strip('_')
            
            # 8. 빈 문자열 처리
            if not clean_title:
                clean_title = "보도자료"
            
            return clean_title
            
        except Exception as e:
            logger.error(f"❌ 제목 정리 실패: {e}")
            return "보도자료"
    
    def save_markdown(self, summary_data: Dict, filename: str) -> str:
        """마크다운 파일 저장"""
        try:
            filepath = Path(self.output_dir) / filename
            
            # 파일이 이미 존재하는 경우 백업
            if filepath.exists():
                backup_path = filepath.with_suffix('.md.bak')
                filepath.rename(backup_path)
                logger.info(f"📦 기존 파일 백업: {backup_path.name}")
            
            # 새 파일 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(summary_data['content'])
            
            # 파일 크기 확인
            file_size = filepath.stat().st_size
            logger.info(f"✅ 마크다운 파일 저장: {filename} ({file_size:,} bytes)")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ 마크다운 파일 저장 실패: {e}")
            return ""
    
    def _check_md_exists_for_pdf(self, pdf_path: str) -> Optional[str]:
        """PDF에 대응하는 MD 파일이 이미 존재하는지 확인"""
        try:
            pdf_filename = Path(pdf_path).name
            
            # MD 폴더의 모든 파일 확인
            md_files = list(Path(self.output_dir).glob("*.md"))
            
            for md_file in md_files:
                try:
                    # MD 파일에서 PDF 파일명과 연관성 확인
                    # 방법 1: 파일명에 PDF 이름 포함 여부 확인
                    pdf_base = pdf_filename.replace('.pdf', '')
                    clean_pdf_name = self._clean_title_for_filename(pdf_base)
                    
                    if clean_pdf_name in md_file.name:
                        logger.info(f"🔍 기존 MD 파일 발견 (파일명 매칭): {md_file.name}")
                        return str(md_file)
                    
                    # 방법 2: MD 파일 내용에서 PDF 파일명 확인 (frontmatter 파싱)
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # frontmatter에서 제목 추출하여 비교
                    if content.startswith('---'):
                        end_idx = content.find('---', 3)
                        if end_idx > 0:
                            frontmatter = content[3:end_idx]
                            for line in frontmatter.split('\n'):
                                if line.strip().startswith('title:'):
                                    title = line.split(':', 1)[1].strip().strip('"\'')
                                    title_clean = self._clean_title_for_filename(title)
                                    
                                    if clean_pdf_name in title_clean or title_clean in clean_pdf_name:
                                        logger.info(f"🔍 기존 MD 파일 발견 (제목 매칭): {md_file.name}")
                                        return str(md_file)
                                    break
                    
                except Exception as e:
                    logger.debug(f"MD 파일 확인 중 오류: {md_file.name} - {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ MD 파일 존재 확인 실패: {e}")
            return None
    
    def process_pdf_file(self, pdf_path: str, source_url: str = "") -> Optional[str]:
        """PDF 파일 하나를 처리해서 마크다운으로 변환"""
        try:
            pdf_filename = Path(pdf_path).name
            logger.info(f"🚀 PDF 처리 시작: {pdf_filename}")
            
            # 🔧 중복 확인 - 이미 처리된 PDF인지 체크
            existing_md = self._check_md_exists_for_pdf(pdf_path)
            if existing_md:
                logger.info(f"⏭️ 이미 처리된 PDF 스킵: {pdf_filename} → {Path(existing_md).name}")
                return existing_md
            
            # source_url 기본값 설정
            if not source_url:
                source_url = "https://www.busan.go.kr/nbtnewsBU"
                logger.info("📎 기본 URL 사용")
            
            # 1. PDF에서 텍스트 추출
            content = self.extract_text_from_pdf(pdf_path)
            if not content:
                logger.warning(f"⚠️ 텍스트 추출 실패: {pdf_filename}")
                return None
            
            # 2. GPT로 요약 생성
            summary_data = self.generate_summary_with_gpt(content, source_url)
            if not summary_data:
                logger.warning(f"⚠️ 요약 생성 실패: {pdf_filename}")
                return None
            
            # 3. 태그 개선
            metadata = summary_data['metadata']
            title = metadata.get('title', pdf_filename)
            gpt_tags = metadata.get('tags', ['전체'])
            
            enhanced_tags = self._enhance_tags(gpt_tags, title, content)
            metadata['tags'] = enhanced_tags
            
            # summary_data에 개선된 메타데이터 반영
            summary_data['metadata'] = metadata
            
            # 4. 파일명 생성
            filename = self.create_filename_from_metadata(metadata)
            
            # 🔧 중복 확인 - 생성될 파일명이 이미 존재하는지 체크
            target_filepath = Path(self.output_dir) / filename
            if target_filepath.exists():
                logger.info(f"⏭️ 동일한 파일명의 MD 파일이 이미 존재하여 스킵: {filename}")
                return str(target_filepath)
            
            # 5. 마크다운 파일 저장
            md_path = self.save_markdown(summary_data, filename)
            
            if md_path:
                logger.info(f"🎉 PDF 처리 완료: {pdf_filename} → {filename}")
                return md_path
            else:
                logger.warning(f"⚠️ 파일 저장 실패: {pdf_filename}")
                return None
                
        except Exception as e:
            logger.error(f"❌ PDF 처리 실패 {Path(pdf_path).name}: {e}")
            return None
    
    def process_all_pdfs(self, source_urls: Dict[str, str] = None) -> List[str]:
        """모든 PDF 파일을 처리"""
        try:
            # PDF 파일 목록 가져오기
            pdf_files = list(Path(PDF_DIR).glob("*.pdf"))
            
            if not pdf_files:
                logger.warning("⚠️ 처리할 PDF 파일이 없습니다")
                return []
            
            logger.info(f"📋 처리할 PDF 파일: {len(pdf_files)}개")
            
            # 🔧 중복 제거 - 이미 처리된 PDF 필터링
            unprocessed_pdfs = []
            skipped_count = 0
            
            for pdf_path in pdf_files:
                existing_md = self._check_md_exists_for_pdf(str(pdf_path))
                if existing_md:
                    logger.info(f"⏭️ 이미 처리된 PDF 스킵: {pdf_path.name}")
                    skipped_count += 1
                else:
                    unprocessed_pdfs.append(pdf_path)
            
            if skipped_count > 0:
                logger.info(f"📊 중복 제거 결과: {skipped_count}개 스킵, {len(unprocessed_pdfs)}개 처리 예정")
            
            if not unprocessed_pdfs:
                logger.info("✅ 모든 PDF가 이미 처리되었습니다!")
                return []
            
            # URL 매핑 정보 출력
            if source_urls:
                logger.info(f"🔗 URL 매핑 정보: {len(source_urls)}개")
            else:
                logger.info("🔗 URL 매핑 없음 - 기본 URL 사용")
            
            generated_files = []
            failed_files = []
            
            for idx, pdf_path in enumerate(unprocessed_pdfs, 1):
                try:
                    logger.info(f"📄 진행상황: {idx}/{len(unprocessed_pdfs)} - {pdf_path.name}")
                    
                    # URL 매핑에서 찾기
                    pdf_filename = pdf_path.name
                    source_url = ""
                    
                    if source_urls and pdf_filename in source_urls:
                        source_url = source_urls[pdf_filename]
                        logger.info(f"🔗 매핑된 URL 사용: {source_url}")
                    
                    # PDF 처리
                    md_file = self.process_pdf_file(str(pdf_path), source_url)
                    
                    if md_file:
                        generated_files.append(md_file)
                        logger.info(f"✅ 성공: {Path(md_file).name}")
                    else:
                        failed_files.append(pdf_filename)
                        logger.warning(f"❌ 실패: {pdf_filename}")
                    
                    # API 요청 간격 (Rate Limit 방지)
                    if idx < len(unprocessed_pdfs):  # 마지막이 아니면 대기
                        time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ PDF 처리 실패 {pdf_path.name}: {e}")
                    failed_files.append(pdf_path.name)
                    continue
            
            # 결과 요약
            logger.info("="*60)
            logger.info("🎉 전체 PDF 처리 완료!")
            logger.info(f"📊 처리 결과:")
            logger.info(f"   📁 전체 PDF: {len(pdf_files)}개")
            logger.info(f"   ⏭️ 스킵 (중복): {skipped_count}개")
            logger.info(f"   ✅ 새로 처리 성공: {len(generated_files)}개")
            logger.info(f"   ❌ 처리 실패: {len(failed_files)}개")
            
            if failed_files:
                logger.info("❌ 실패한 파일들:")
                for failed_file in failed_files[:5]:  # 처음 5개만
                    logger.info(f"   - {failed_file}")
                if len(failed_files) > 5:
                    logger.info(f"   ... 외 {len(failed_files) - 5}개")
            
            logger.info("="*60)
            
            return generated_files
            
        except Exception as e:
            logger.error(f"❌ 전체 PDF 처리 실패: {e}")
            return []

if __name__ == "__main__":
    # 테스트 실행
    import sys
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('summarizer_test.log', encoding='utf-8')
        ]
    )
    
    try:
        # 요약기 초기화
        summarizer = BusanNewsSummarizer()
        
        # 모든 PDF 처리
        results = summarizer.process_all_pdfs()
        
        print(f"\n🎯 요약 결과: {len(results)}개 파일 생성")
        print("생성된 파일들:")
        for result in results[:10]:  # 처음 10개만 출력
            print(f"- {Path(result).name}")
        
        if len(results) > 10:
            print(f"... 외 {len(results) - 10}개")
    
    except Exception as e:
        print(f"❌ 테스트 실행 실패: {e}")
        sys.exit(1)