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

- **형식적이거나 뻔한 말, 피상적인 언급은 모두 배제**  
- **실제 사업명·예산·정책명·추진 수치·성과(%)·신규 도입 등**  
  **시민이 "진짜 변화"라고 느낄 수 있는 디테일을 카드별로 반드시 1가지 이상 포함**
- **2024년 대비 달라지는 점, 최초 도입·확대·전국 최초 등 특이점은 반드시 강조**
- **실제 시민이 체감할 수 있는 변화(교통 대기시간 감소, 체험·축제 확대, 비용 절감 등) 포함**
- **예산·성과·수치·투자계획 등은 반드시 카드별로 실제 숫자로 표기**
- **구체적인 계획은 반드시 세부사항 포함**: 
  - ❌ "국제선 항공노선 확대" → ✅ "국제선 항공노선 확대(동남아 3개, 유럽 2개 신규 추진)"
  - ❌ "해외 관광설명회 개최" → ✅ "해외 관광설명회 개최(일본 3회, 중화권 2회, 동남아 3회)"
  - ❌ "크루즈관광 패키지 신설" → ✅ "크루즈관광 패키지 신설(5개 코스, 연 50회 운항)"
  - ❌ "관광홍보 마케팅 강화" → ✅ "글로벌 온라인 마케팅 강화(5개국 언어, 월 100만 노출)"
- **각 카드는 "이모지 + 카드형 제목 + 개조식 요약"으로 간결하게**
- **개조식 구성**: 핵심 예산이나 사업명을 먼저 제시하고, 하위 항목은 '-'로 구성
- **볼드체는 꼭 필요한 핵심 수치, 예산, 신규사업명, 성과지표만 사용하고 일반 설명은 보통 글씨로**
- **문체**: 개조식이므로 '~해요' 대신 간결한 명사형 또는 '~강화', '~확대' 등으로 마무리
- **슬로건 또는 한 줄 약속은 실제 부산시가 시민에게 전하고 싶은 강렬한 메시지로 마무리**
- **'~합니다, ~임' 대신 개조식 간결체 사용**: '~강화', '~확대', '~추진' 등
- **카드는 7~10개, 각 카드는 간결한 개조식으로 핵심만 담아 가독성 극대화**

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

---
아래는 [카드뉴스 스타일 예시]입니다.  
꼭 아래 예시처럼 **실질 정보·수치·사업명·성과·변화**가 들어가도록 작성하세요.

---
title: "관광마이스국 2025년 주요업무계획"
date: "2025"
tags: ["문화교육"]
thumbnail_summary: "외국인 관광객 300만 시대! 미식·크루즈·축제로 체감하는 글로벌 도시 변화"
department: "관광마이스국"
---

# 🌏 외국인 관광객 **300만 시대** 돌파!

- 올해 외국인 관광객 2,696,477명 → **300만 돌파 임박!**
- 글로벌 관광허브도시 도약 본격화
- ✈️ **국제선 항공노선 확대**(동남아 3개, 유럽 2개 신규 추진)  
- 🚢 **크루즈관광 패키지 신설**(5개 코스, 연 50회 운항)  
- 🤝 **해외 관광설명회 개최**(일본 3회, 중화권 2회, 동남아 3회)  
- 🌐 **글로벌 온라인 마케팅 강화**(5개국 언어, 월 100만 노출)  
- 🗺️ 해외 여행사 연계 상품 개발  



# 💰 관광예산·투자, 어디에 얼마나?

- **세출 758억원** (관광정책과 445억, 마이스산업과 234억 등)
- **관광마이스육성진흥기금 94억원** 신규 조성  
- 관광홍보 마케팅·신규 행사·축제·인프라에 집중 투자
- 🏗️ **관광 인프라 확충**(광안대교 앵커리지 조명교체 33억원)  
- 🎥 **부산관광홍보영상** 글로벌 배포(5개국 언어)  
- 🎟️ **생활관광·도심재생형** 관광지 개발  
- 📈 **중소 관광업체 경영지원**(인바운드 여행사 인센티브 60% 증가)  
- 🛎️ 관광불편 해소·고객서비스 개선  



# 🏆 글로벌 행사 & 컨벤션, 부산이 주도!

- **글로벌도시관광서밋(10월)** 국내외 300여명 참여, 부산 최초 개최
- **UN Tourism과 협력**, 국제관광포럼, 글로벌 미식포럼 개최
- **벡스코 제3전시장** 본격 착공(사업비 2,900억원, 전시면적 46천㎡→64천㎡)
- 🌏 **글로벌 K-컬처 마켓** 개최  
- 🏟️ **한중일 관광장관회의** 유치  
- 💡 **신성장 마이스산업** 아이디어 공모전  
- 🗓️ **연중 국제행사 지원**(20개 이상)  
- 🏅 **MICE산업 전문인력** 인증제 운영  



# 🍽️ 미식관광도시로 도약!

- 2024년 **미쉐린 가이드 부산편 첫 발간** (레스토랑 43곳)
- 미식 관광상품 'TASTY 부산'·'부산 미식로드' 신규 운영
- 테마별 파인다이닝, 전통음식, 푸드 페스티벌 상시 확대
- 🍣 부산 해산물 명소 마케팅  
- 🥢 미식관광 스타트업 육성  
- 🍰 지역 디저트 페스티벌  
- 🥂 와인·전통주 체험투어  
- 🥘 글로벌 푸드트럭 행사  



# 🌊 해양레저관광 & 크루즈 전성시대

- **남해안권 해양레저관광벨트** 5개 사업, 1,467억 투자
- 수륙양용 투어버스(수영강~광안대교 21km) 본격 운행
- 크루즈 관광객 신속 입국·무비자 확대, 지역 연계상품 강화
- 🏄 서핑 챌린지 대회 개최  
- 🚤 요트 투어 패키지 운영  
- 🏖️ 해양관광명소 연계버스 신설  
- 🚢 부산항 국제크루즈 승하선장 확대  
- 🏊 부산 해변 레저스포츠 체험장 운영  



# 🏖️ 사계절 축제, 끊임없이!

- 부산바다축제, 록페스티벌, 불꽃축제 등 대규모 축제 강화
- '별바다부산 나이트 페스타' 등 **야간관광** 콘텐츠 확대
- 🎆 부산불꽃축제 글로벌 홍보  
- 🎸 전국 청년밴드 페스티벌  
- 🌊 마린스포츠 페스타  
- 🎤 오페라 갈라 콘서트  
- 🏮 테마별 전통시장 야간축제  



# 👩‍💼 지역 관광기업·인재, 직접 키운다!

- 관광전문인력 85명, 인바운드 여행사 인센티브 지원(60%↑)
- K-콘텐츠 아카데미, 글로벌 여행플랫폼 연계
- 부산 대표 기념품 10선, 지역관광상품 전국 확산
- 🏫 관광창업 지원센터 운영  
- 👨‍🎓 청년 관광일자리 프로젝트  
- 🏅 부산관광 리더 양성 아카데미  
- 🧳 관광기업 해외시장 진출 지원  
- 🛍️ 지역 특화 관광상품 개발·판로 지원  



# 🏥 웰니스·의료관광, 글로벌 브랜드화

- 웰니스 관광지 **10→13곳 확대**
- 의료관광 통역·전문인력 체계적 양성
- 맞춤형 의료·웰니스 추천코스 개발
- 🧘 웰니스 힐링캠프  
- 🏨 프리미엄 헬스케어 패키지  
- 🏥 글로벌 환자맞춤 의료통역  
- 🥗 건강식·로컬푸드 연계 투어  
- 🏃 산림·해양치유 관광코스 운영  



# 🌍 세계와 연결되다!

- 올해 **글로벌 네트워크 51개 도시**로 확장
- 국제도시외교단, 유엔위크 등 실질적 교류
- 자매·우호도시 신규 체결(포르투, 노비사드 등)
- 🤝 부산-포르투 경제교류 프로젝트  
- 📢 국제관광공동마케팅 협약  
- 🏆 글로벌 청년교류 프로그램  
- 🌏 동남아·유럽 시장 특화 프로모션  
- 🗣️ 온라인 외국어 관광안내 서비스 강화  


부산시 {department} 업무계획 전문:
{content}
---

**위 내용만 참고해서, 1분 안에 읽을 수 있는 카드뉴스/설명회 스타일로 요약해주세요.**


사용 가능한 분류: {', '.join(AVAILABLE_PLAN_TAGS)}
분류는 부서 성격에 가장 적합한 **1개만** 선택하세요.

**분류 가이드라인:**
• 기획감사: 기획관, 기획조정실, 대변인실, 감사위원회
• 복지안전: 시민안전실, 사회복지국, 시민건강국, 여성가족국, 자치경찰위원회
• 건설교통: 도시혁신균형실, 도시공간계획국, 주택건축국, 신공항추진본부, 교통혁신국, 건설본부
• 도시환경: 환경물정책실, 푸른도시국, 보건환경연구원, 낙동강관리본부, 상수도사업본부
• 경제산업: 디지털경제실, 금융창업정책관, 첨단산업국, 해양농수산국
• 문화교육: 문화체육국, 관광마이스국, 청년산학국, 인재개발원

반드시 ---로 감싸진 frontmatter 형식을 지켜주세요.
"""
            
            logger.info(f"🤖 GPT 요약 생성 중... ({department})")
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": """부산시청 업무계획 요약 전문가입니다.

🎯 핵심 미션: 정확하고 실용적인 업무계획 요약

📋 필수 역량:
- 업무계획 구조 이해 (기본현황, 추진과제, 예산)
- 핵심 사업과 정책 추출
- 적절한 분류 태그 선택
- 시민이 이해하기 쉬운 요약
- 썸네일 요약에서 불필요한 중복 정보 제거

⚠️ 원칙:
- 업무계획 특성에 맞는 구조화된 요약
- 7개 분류 중 정확한 카테고리 선택
- 부서별 핵심 업무 중심 정리
- 썸네일 요약은 시민 체감 변화 중심으로 간결하게

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