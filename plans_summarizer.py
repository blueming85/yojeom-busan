"""
부산시청 업무계획 요약기 - SimplePlansSummarizer
==============================================
업무계획 PDF → MD 변환 전용 (단순 일괄 처리)

주요 특징:
- 중복 체크 불필요 (29개 고정)
- URL 매핑 불필요 (원문 링크 없음)
- 단순 PDF → MD 변환만
- 썸네일 요약에서 불필요한 중복 정보 제거
"""

import os
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List

import openai
import fitz  # PyMuPDF
from datetime import datetime

from config import (
   OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, TEMPERATURE,
   AVAILABLE_PLAN_TAGS, PLANS_PDF_DIR, PLANS_MD_DIR,
   PLANS_SUMMARY_PROMPT, PLAN_DEPARTMENTS
)

logger = logging.getLogger(__name__)

class SimplePlansSummarizer:
   """업무계획 전용 간단 요약기"""
   
   def __init__(self):
       """초기화"""
       if not OPENAI_API_KEY:
           raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
       
       self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
       self.pdf_dir = PLANS_PDF_DIR
       self.md_dir = PLANS_MD_DIR
       
       # 디렉토리 생성
       Path(self.md_dir).mkdir(parents=True, exist_ok=True)
       
       logger.info("✅ SimplePlansSummarizer 초기화 완료")
   
   def extract_text_from_pdf(self, pdf_path: str) -> str:
       """PDF에서 텍스트 추출 (간단 버전)"""
       doc = None
       try:
           logger.info(f"📄 PDF 텍스트 추출: {Path(pdf_path).name}")
           
           if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 100:
               logger.error("❌ PDF 파일 문제")
               return ""
           
           doc = fitz.open(pdf_path)
           if doc.page_count == 0:
               return ""
           
           # 첫 5페이지만 추출 (업무계획은 보통 앞부분이 중요)
           text_parts = []
           max_pages = min(5, doc.page_count)
           
           for page_num in range(max_pages):
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
               full_text = full_text.strip()
           
           if len(full_text) < 100:
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
   
   def extract_department_from_filename(self, filename: str) -> str:
       """파일명에서 부서명 추출"""
       try:
           # "2025년 부서명 주요업무계획.pdf" 형태에서 부서명 추출
           if "주요업무계획" in filename:
               # "2025년 " 제거하고 " 주요업무계획.pdf" 제거
               dept_part = filename.replace("2025년 ", "").replace(" 주요업무계획.pdf", "")
               return dept_part
           
           return "미분류"
           
       except Exception as e:
           logger.error(f"부서명 추출 실패: {e}")
           return "미분류"
   
   def get_department_category(self, department: str) -> str:
       """부서명으로부터 분류 카테고리 찾기"""
       for display_name, dept_list in PLAN_DEPARTMENTS:
           if dept_list != "전체" and any(dept in department for dept in dept_list):
               # "🏛️ 기획감사" -> "기획감사" 추출
               return display_name.split(' ', 1)[1] if ' ' in display_name else display_name
       
       return "전체"
   
   def generate_summary_with_gpt(self, content: str, department: str) -> Optional[Dict]:
       """GPT를 이용한 업무계획 요약 생성"""
       try:
           # 내용 길이 제한 (업무계획은 길 수 있음)
           if len(content) > 4000:
               content = content[:4000]
           
           # 부서명으로부터 분류 추출
           category = self.get_department_category(department)
           
           # 업무계획 전용 GPT 프롬프트 (썸네일 요약 개선)
           prompt = f"""
아래 부산시 {department}의 업무계획을 **시민 설명회 또는 SNS 카드뉴스**로 활용할 수 있게
**이모지**, **카드형 요약**, **간결하고 실감나는 스토리텔링**으로 
핵심만 뽑아 **1분 이내에 읽는 순간 몰입**될 만큼 구체적으로 요약해주세요.

**📌 절대 규칙:**
- 반드시 "아래 제공된 PDF 텍스트"만 참고하여, 외부 정보, 웹 검색, 주관적 해석, 일반 상식, 타 부서 사업, 인용/창작, 추정 내용은 절대 넣지 마세요.
- PDF 내 **대분류 제목(1/, 2/, 3/, 4/, 5/, 6/ 등)**을 반드시 카드 제목으로 사용하세요.
- 각 대분류 하위의 **구체적 사업명과 실제 내용**을 카드별로 구어체로 요약하세요.
- "지원합니다/계획합니다" 대신 **실제 사업명을 연결해서** 시민들이 무엇이 어떻게 바뀌는지 구체적으로 설명하세요.
- 실제 PDF 내 수치, 정책, 사업명, 성과, 계획, 특이점 등 **명확하게 명시된 정보**만 카드별로 요약하세요.

**[목표]**
시민설명회/SNS 카드뉴스 스타일로, **1분 이내에 핵심만 실감나게 카드 형태로 요약**  
(불필요한 배경설명·도입부·맺음말·PDF에 없는 내용 제외)

PDF의 대분류 제목을 그대로 활용해서 각 제목별로 실제 추진되는 사업들을 
시민들이 "아, 이런 게 바뀌는구나!" 하고 체감할 수 있게 카드별로 요약

각 카드는
"이모지 + 대분류 제목" 

세부내용은 **구어체**로 사업들을 연결해서 설명
"~합니다", "~해요", "~늘려요", "~추진!" 같이
딱딱하지 않고 친근하게 마무리

❌ 나쁜 예: "부산이 발전해요"
✅ 좋은 예: "글로벌허브도시 특별법으로 물류·금융·첨단산업 거점을 만들고, 시민행복부산회의에서 생활 속 의견을 직접 시정에 반영해요"

사업명이나 수치 먼저 쓰고, 세부내용은 실제 PDF에 명시된 것만 사용해서
친근한 구어체로 연결해서 설명

볼드체는 숫자나 진짜 중요한 사업명에만

PDF에 진짜 있는 내용만큼만 카드 개수 조정
없는 건 억지로 채우지 말고,
"있는 정보만, 시민 눈높이에 맞게, 가볍게!"

추가 설명, 안내문, 추정, 외부 예시, 반복 멘트,
뻔한 관료체는 아예 금지!

---
아래의 마크다운 frontmatter 형식을 반드시 포함하여 출력할 것:
---
title: "{department} 2025년 주요업무계획"
date: "2025"
tags: ["{category}"]
thumbnail_summary: "시민이 체감할 수 있는 핵심 변화나 성과를 80자 이내로 요약 (연도나 지역명 중복 제거)"
department: "{department}"
---

**thumbnail_summary 작성 가이드:**
- ❌ 나쁜 예: "2025년 부산 관광객 300만 시대 도약"
- ✅ 좋은 예: "외국인 관광객 300만 시대! 축제·미식·크루즈 확대로 체감하는 변화"
- ❌ 나쁜 예: "2025년 부산시 교통혁신 추진계획"  
- ✅ 좋은 예: "대중교통 30% 단축, 스마트 신호등으로 교통체증 해결"
- **핵심은 시민이 직접 느낄 수 있는 구체적 변화나 수치를 포함**

부산시 {department} 업무계획 전문:
{content}
---

**위 내용만 참고해서, "시민이 진짜 체감하는 변화"를  
카드뉴스/설명회 스타일로 1분 내에 몰입할 수 있게 요약해주세요.**

사용 가능한 분류: {', '.join(AVAILABLE_PLAN_TAGS)}
분류는 부서 성격에 가장 적합한 **1개만** 선택하세요.

**분류 가이드라인:**
- 기획감사: 부산광역시, 기획관, 기획조정실, 대변인실, 감사위원회
- 복지안전: 시민안전실, 사회복지국, 시민건강국, 여성가족국, 자치경찰위원회
- 건설교통: 도시혁신균형실, 도시공간계획국, 주택건축국, 신공항추진본부, 교통혁신국, 건설본부
- 도시환경: 환경물정책실, 푸른도시국, 보건환경연구원, 낙동강관리본부, 상수도사업본부
- 경제산업: 디지털경제실, 금융창업정책관, 첨단산업국, 해양농수산국
- 문화교육: 문화체육국, 관광마이스국, 청년산학국, 인재개발원

반드시 ---로 감싸진 frontmatter 형식을 지켜주세요.
"""
           
           logger.info(f"🤖 GPT 요약 생성 중... ({department})")
           
           response = self.client.chat.completions.create(
               model=OPENAI_MODEL,
               messages=[
                   {
                       "role": "system", 
                       "content": """부산시청 업무계획 요약 전문가입니다.

**추가 엄수사항**
- PDF에서 '2025년 주요업무계획' 이하 각 **대분류 제목(1/, 2/, 3/, 4/, 5/, 6/ 등)**는 반드시 카드 제목으로 사용하세요.
- 카드 본문에는 해당 분류 바로 아래 실제로 표기된 **정책명, 사업명, 수치, 예산, 성과**만 담아주세요.
- 각 카드는 "이모지 + 대분류 제목" 구조, 세부내용은 모두 구어체로 사업들을 연결해서 설명.
- 분류명 아래 구체 내용이 없으면 카드는 생략합니다.
- 반드시 실제 PDF 내 "대분류" 기준으로 카드 개수를 맞춰주세요.
- 추정, 창작, 타 섹션 사업명, 추가 미사여구, 반복·도입·맺음말, AI 안내는 일절 넣지 않습니다.

실용성과 가독성을 중시하여 작업하세요."""
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
           
           # 태그 검증 (부서명 기반으로 올바른 분류인지 확인)
           expected_category = self.get_department_category(department)
           if metadata.get('tags', []) != [expected_category]:
               logger.warning(f"⚠️ GPT 분류 수정: {metadata.get('tags')} → [{expected_category}]")
               metadata['tags'] = [expected_category]
               # 요약 텍스트도 수정
               summary_text = re.sub(
                   r'tags: \[.*?\]', 
                   f'tags: ["{expected_category}"]', 
                   summary_text
               )
           
           logger.info(f"✅ GPT 요약 생성 완료 (분류: {expected_category})")
           return {
               'metadata': metadata,
               'content': summary_text
           }
               
       except Exception as e:
           logger.error(f"❌ GPT 요약 생성 실패: {e}")
           return None
   
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
               metadata['title'] = "업무계획"
           if 'date' not in metadata:
               metadata['date'] = "2025-01-01"
           if 'tags' not in metadata:
               metadata['tags'] = ["전체"]
           if 'department' not in metadata:
               metadata['department'] = "미분류"
           if 'thumbnail_summary' not in metadata:
               metadata['thumbnail_summary'] = "주요업무계획 요약입니다."
           
           return metadata
           
       except Exception as e:
           logger.error(f"❌ frontmatter 파싱 실패: {e}")
           return None
   
   def create_filename_from_metadata(self, metadata: Dict, original_filename: str) -> str:
       """메타데이터로부터 파일명 생성"""
       try:
           department = metadata.get('department', '미분류')
           category = metadata.get('tags', ['전체'])[0]
           
           # 간단한 파일명: 2025년_부서명_업무계획.md
           clean_dept = re.sub(r'[<>:"/\\|?*\[\]{}]', '', department)
           filename = f"2025년_{clean_dept}_업무계획.md"
           
           return filename
           
       except Exception as e:
           logger.error(f"❌ 파일명 생성 실패: {e}")
           # 원본 파일명 기반 대안
           base_name = Path(original_filename).stem
           return f"{base_name}_요약.md"
   
   def save_markdown(self, summary_data: Dict, filename: str) -> str:
       """마크다운 파일 저장"""
       try:
           filepath = Path(self.md_dir) / filename
           
           with open(filepath, 'w', encoding='utf-8') as f:
               f.write(summary_data['content'])
           
           logger.info(f"✅ 마크다운 파일 저장: {filename}")
           return str(filepath)
           
       except Exception as e:
           logger.error(f"❌ 마크다운 파일 저장 실패: {e}")
           return ""
   
   def process_single_pdf(self, pdf_path: str) -> Optional[str]:
       """단일 PDF 파일 처리"""
       try:
           pdf_filename = Path(pdf_path).name
           logger.info(f"🚀 업무계획 PDF 처리: {pdf_filename}")
           
           # 1. 부서명 추출
           department = self.extract_department_from_filename(pdf_filename)
           logger.info(f"🏛️ 담당부서: {department}")
           
           # 2. 텍스트 추출
           content = self.extract_text_from_pdf(pdf_path)
           if not content:
               logger.error(f"❌ 텍스트 추출 실패: {pdf_filename}")
               return None
           
           # 3. GPT 요약
           summary_data = self.generate_summary_with_gpt(content, department)
           if not summary_data:
               logger.error(f"❌ GPT 요약 실패: {pdf_filename}")
               return None
           
           # 4. 파일명 생성 및 저장
           metadata = summary_data['metadata']
           filename = self.create_filename_from_metadata(metadata, pdf_filename)
           
           md_path = self.save_markdown(summary_data, filename)
           
           if md_path:
               category = metadata.get('tags', ['미분류'])[0]
               logger.info(f"🎉 완료: {pdf_filename} → {filename} (분류: {category})")
               return md_path
           
           return None
               
       except Exception as e:
           logger.error(f"❌ PDF 처리 실패 {Path(pdf_path).name}: {e}")
           return None
   
   def process_all_pdfs(self) -> List[str]:
       """모든 업무계획 PDF 파일 처리"""
       try:
           pdf_files = list(Path(self.pdf_dir).glob("*.pdf"))
           if not pdf_files:
               logger.warning("⚠️ 처리할 업무계획 PDF 파일이 없습니다")
               return []
           
           logger.info(f"📋 처리할 업무계획 PDF: {len(pdf_files)}개")
           
           generated_files = []
           for idx, pdf_path in enumerate(pdf_files, 1):
               logger.info(f"📄 [{idx}/{len(pdf_files)}] {pdf_path.name}")
               
               md_file = self.process_single_pdf(str(pdf_path))
               if md_file:
                   generated_files.append(md_file)
               
               # API 제한 방지를 위한 대기
               if idx < len(pdf_files):
                   logger.info("⏱️ API 제한 방지 대기 (3초)...")
                   time.sleep(3)
           
           logger.info(f"🎉 업무계획 처리 완료: {len(generated_files)}개 생성")
           return generated_files
           
       except Exception as e:
           logger.error(f"❌ 전체 처리 실패: {e}")
           return []


# 테스트 함수
def test_plans_summarizer():
   """업무계획 요약기 테스트"""
   print("🧪 업무계획 요약기 테스트 시작...")
   
   try:
       summarizer = SimplePlansSummarizer()
       
       # 테스트용 PDF 파일 확인
       test_files = list(Path(summarizer.pdf_dir).glob("*.pdf"))
       print(f"📁 발견된 PDF 파일: {len(test_files)}개")
       
       if test_files:
           # 첫 번째 파일로 테스트
           test_file = test_files[0]
           print(f"🧪 테스트 파일: {test_file.name}")
           
           result = summarizer.process_single_pdf(str(test_file))
           if result:
               print(f"✅ 테스트 성공: {result}")
           else:
               print("❌ 테스트 실패")
       else:
           print("⚠️ 테스트할 PDF 파일이 없습니다.")
           print(f"   PDF 파일을 다음 경로에 배치하세요: {summarizer.pdf_dir}")
   
   except Exception as e:
       print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
   import time
   test_plans_summarizer()