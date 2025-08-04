import os
from dotenv import load_dotenv
from pathlib import Path
import logging

# 환경 감지
IS_LOCAL = os.path.exists('.env')  # .env 파일 있으면 로컬 환경
IS_DEPLOYMENT = not IS_LOCAL       # Streamlit Cloud 등 배포 환경

# 환경별 .env 로드
if IS_LOCAL:
    load_dotenv()
    logging.info("🏠 로컬 환경에서 실행 중 (.env 로드됨)")
else:
    logging.info("☁️ 배포 환경에서 실행 중")

# ===== 기본 경로 설정 =====
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

# 보도자료 관련 (기존)
PDF_DIR = DATA_DIR / "pdfs"
MD_DIR = DATA_DIR / "md"

# 🔧 업무계획 관련 (신규 추가)
PLANS_DIR = DATA_DIR / "plans"
PLANS_PDF_DIR = PLANS_DIR / "pdfs"
PLANS_MD_DIR = PLANS_DIR / "md"

# 🔧 맛집 관련 (신규 추가)
RESTAURANT_DIR = DATA_DIR / "restaurants"
RESTAURANT_MD_DIR = RESTAURANT_DIR / "md"

TEMPLATE_DIR = ROOT_DIR / "templates"

# 🔧 LOG_FILE 추가
LOG_FILE = ROOT_DIR / "busan_portal.log"

# 유틸리티 경로 (utils → utility로 변경)
UTILITY_DIR = ROOT_DIR / "utility"

# 폰트 경로 (로컬 환경에서만)
if IS_LOCAL:
    FONTS_DIR = ROOT_DIR / "fonts"
    CUSTOM_FONT_PATH = FONTS_DIR / "BMJUA_ttf.ttf"
else:
    FONTS_DIR = None
    CUSTOM_FONT_PATH = None

# 필요한 디렉토리들 자동 생성
directories_to_create = [
    DATA_DIR, PDF_DIR, MD_DIR, TEMPLATE_DIR, UTILITY_DIR,
    PLANS_DIR, PLANS_PDF_DIR, PLANS_MD_DIR,  # 🔧 추가
    RESTAURANT_DIR, RESTAURANT_MD_DIR  # 🔧 맛집 디렉토리 추가
]
if IS_LOCAL and FONTS_DIR:
    directories_to_create.append(FONTS_DIR)

for directory in directories_to_create:
    directory.mkdir(parents=True, exist_ok=True)

# ===== API 설정 =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") if IS_LOCAL else None
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")  # 🔧 카카오 API 키 추가

OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS = 3000  # 🔧 1500 → 3000으로 늘려서 상세한 요약
TEMPERATURE = 0.2  # 🔧 일관된 응답을 위해 낮춤
MAX_RETRIES = 3
RETRY_DELAY = 1.0
CHUNK_SIZE = 3000  # 🔧 입력 토큰 절약

# 🔧 API 키 검증 완화 (경고만 출력)
if IS_LOCAL and not OPENAI_API_KEY:
    logging.warning("⚠️ OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다. 요약 기능을 사용할 수 없습니다.")

# ===== 크롤링 설정 =====
BUSAN_BASE_URL = "https://www.busan.go.kr/nbtnewsBU"
MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "1.0"))

# ===== 태그 설정 (🔧 8개 태그로 개선) =====
AVAILABLE_TAGS = [
    "전체",
    "청년·교육", 
    "일자리·경제", 
    "복지·건강", 
    "교통·주거", 
    "문화·관광",
    "안전·환경",
    "행정·소식"
]

# 태그별 색상 설정 (UI용)
TAG_COLORS = {
    "전체": "#6B7280",        # 회색
    "청년·교육": "#3B82F6",    # 파란색
    "일자리·경제": "#10B981",  # 초록색
    "복지·건강": "#EF4444",    # 빨간색
    "교통·주거": "#8B5CF6",    # 보라색
    "문화·관광": "#F59E0B",    # 주황색
    "안전·환경": "#06B6D4",    # 청록색
    "행정·소식": "#84CC16"     # 라임색
}

# 🔧 업무계획 태그 설정 (신규 추가)
AVAILABLE_PLAN_TAGS = [
    "전체",
    "기획감사",
    "복지안전", 
    "건설교통", 
    "도시환경", 
    "경제산업",
    "문화교육"
]

# 업무계획 태그별 색상 설정
PLAN_TAG_COLORS = {
    "전체": "#6B7280",        # 회색
    "기획감사": "#8B5CF6",     # 보라색
    "복지안전": "#EF4444",     # 빨간색
    "건설교통": "#F59E0B",     # 주황색
    "도시환경": "#10B981",     # 초록색
    "경제산업": "#06B6D4",     # 청록색
    "문화교육": "#3B82F6"      # 파란색
}

# 🔧 업무계획 부서별 분류
PLAN_DEPARTMENTS = [
    ("🏠 전체", "전체"),
    ("🏛️ 기획감사", ["기획관", "기획조정실", "대변인실", "감사위원회", "부산광역시"]),  # 🔧 부산광역시 추가
    ("👥 복지안전", ["시민안전실", "사회복지국", "시민건강국", "여성가족국", "자치경찰위원회"]),
    ("🏗️ 건설교통", ["도시혁신균형실", "도시공간계획국", "주택건축국", "신공항추진본부", "교통혁신국", "건설본부"]),
    ("🌊 도시환경", ["환경물정책실", "푸른도시국", "보건환경연구원", "낙동강관리본부", "상수도사업본부"]),
    ("💼 경제산업", ["디지털경제실", "금융창업정책관", "첨단산업국", "해양농수산국"]),
    ("🎭 문화교육", ["문화체육국", "관광마이스국", "청년산학국", "인재개발원"]),
]

# ===== 맛집 관련 설정 (🔧 신규 추가) =====

# 맛집 지역 분류 (4권역)
RESTAURANT_REGIONS = {
    "원도심권": ["중구", "동구", "영도구", "서구"],
    "동부산권": ["해운대구", "수영구", "남구", "기장군"],  
    "서부산권": ["사하구", "강서구", "사상구"],
    "북부산권": ["북구", "금정구", "동래구", "연제구", "부산진구"]
}

AVAILABLE_RESTAURANT_REGIONS = ["전체", "원도심권", "동부산권", "서부산권", "북부산권"]

# 맛집 음식 유형 (기타 → 아시아분식으로 변경, 횟집 추가)
RESTAURANT_FOOD_TYPES = [
    "전체",
    "한식", 
    "중식", 
    "일식", 
    "양식", 
    "아시아분식",  # 기타에서 변경
    "횟집",        # 새로 추가
    "카페",
    "베이커리"
]

# 맛집 카테고리
AVAILABLE_RESTAURANT_CATEGORIES = [
    "전체",
    "미쉐린가이드", 
    "부산의맛", 
    "현지인"
]

# 맛집 지역별 색상
RESTAURANT_REGION_COLORS = {
    "전체": "#6B7280",      # 회색
    "원도심권": "#EF4444",  # 빨강
    "동부산권": "#3B82F6",  # 파랑  
    "서부산권": "#10B981",  # 초록
    "북부산권": "#F59E0B"   # 주황
}

# 맛집 음식유형별 색상 (아시아분식으로 변경)
RESTAURANT_FOOD_TYPE_COLORS = {
    "전체": "#6B7280",      # 회색
    "한식": "#EF4444",      # 빨강
    "중식": "#F59E0B",      # 주황  
    "일식": "#3B82F6",      # 파랑
    "양식": "#8B5CF6",      # 보라
    "아시아분식": "#10B981", # 초록 (기타 → 아시아분식)
    "카페": "#EC4899",      # 핑크
    "베이커리": "#84CC16"   # 라임
}

# 맛집 카테고리별 색상 (횟집 추가)
RESTAURANT_CATEGORY_COLORS = {
    "전체": "#6B7280",      # 회색
    "미쉐린가이드": "#FF8C00",  # 🔧 주황색으로 변경
    "부산의맛": "#EF4444",  # 빨강
    "현지인": "#10B981",    # 초록
    "횟집": "#06B6D4"       # 청록색 (새로 추가)
}

# ===== GPT 프롬프트 템플릿 (🔧 상세한 요약으로 복원 + 원문 링크) =====
SUMMARY_PROMPT = """
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

사용 가능한 태그: {available_tags}
태그는 내용에 가장 적합한 **1개만** 선택해주세요.
반드시 ---로 감싸진 frontmatter 형식을 지켜주세요.
"""

# 🔧 업무계획 전용 GPT 프롬프트 템플릿 (신규 추가)
PLANS_SUMMARY_PROMPT = """
다음 부산시 업무계획을 자연스럽게 상세히 요약해주세요.

업무계획 내용:
{content}

아래 형식으로 작성해주세요:

---
title: "업무계획 제목"
date: "2025-01-01"
tags: ["분류1"]
thumbnail_summary: "80자 이내 한줄요약"
department: "{department}"
---

# 2025년 주요업무계획

## 📋 기본현황
조직, 인력, 예산 등 기본현황을 요약해주세요.

## 🎯 주요 추진과제
올해 중점 추진할 주요 과제들을 상세히 설명해주세요.

## 💰 예산현황
주요 사업별 예산 배분을 정리해주세요.

## 📞 담당부서
{department}

사용 가능한 분류: {available_tags}
분류는 부서 성격에 가장 적합한 **1개만** 선택해주세요.
반드시 ---로 감싸진 frontmatter 형식을 지켜주세요.
"""

# 🔧 맛집용 GPT 프롬프트 템플릿 (아시아분식과 횟집 반영)
RESTAURANT_SUMMARY_PROMPT = """
다음 부산 맛집 정보를 자연스럽게 요약해주세요.

맛집 정보:
{content}

아래 형식으로 작성해주세요:

---
title: "맛집 이름"
region: "지역권"
district: "구/군"
category: "카테고리"
food_type: "음식유형"
representative_menu: "대표메뉴 가격"
phone: "전화번호"
address: "주소"
hours: "영업시간"
closed_days: "휴무일"
date: "YYYY-MM-DD"
---

# 맛집 상세 정보

## 📍 이용안내
## 🍽️ 메뉴 정보
## 📞 연락처 정보

사용 가능한 지역: {available_regions}
사용 가능한 음식유형: {available_food_types}
사용 가능한 카테고리: {available_categories}
"""

# ===== 개발/운영 환경 설정 =====
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 8501))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# 환경별 설정
if IS_LOCAL:
    if DEBUG:
        MAX_PAGES = 2  # 개발시에는 적은 페이지만
        CRAWL_DELAY = 0.5  # 빠른 테스트
    else:
        MAX_PAGES = 5  # 운영시 기본값
        CRAWL_DELAY = 1.0
else:
    # 배포 환경에서는 크롤링 비활성화
    MAX_PAGES = 0
    CRAWL_DELAY = 0

# ===== 기능 가용성 체크 =====
def is_feature_available(feature: str) -> bool:
    """환경별 기능 가용성 확인"""
    if not IS_LOCAL:
        # 배포 환경에서는 읽기 전용 기능만
        readonly_features = ["read_markdown", "show_cards", "filter_tags"]
        return feature in readonly_features
    else:
        # 로컬 환경에서는 모든 기능 가능
        return True

# ===== 환경 정보 =====
def get_env_info() -> dict:
    """현재 환경 정보 반환"""
    return {
        "environment": "로컬 환경" if IS_LOCAL else "배포 환경",
        "root_dir": str(ROOT_DIR),
        "data_dir": str(DATA_DIR),
        "plans_dir": str(PLANS_DIR),  # 🔧 추가
        "restaurant_dir": str(RESTAURANT_DIR),  # 🔧 맛집 디렉토리 추가
        "api_available": OPENAI_API_KEY is not None,
        "kakao_api_available": KAKAO_REST_API_KEY is not None,  # 🔧 카카오 API 추가
        "font_available": CUSTOM_FONT_PATH is not None and CUSTOM_FONT_PATH.exists() if CUSTOM_FONT_PATH else False,
        "debug_mode": DEBUG,
        "max_pages": MAX_PAGES
    }

# ===== 설정 검증 =====
def validate_config() -> dict:
    """설정 유효성 검사"""
    issues = []
    
    # 로컬 환경 체크
    if IS_LOCAL:
        # API 키 체크 (경고만, 에러 아님)
        if not OPENAI_API_KEY:
            issues.append("OpenAI API 키가 설정되지 않음 (요약 기능 비활성화)")
        
        if not KAKAO_REST_API_KEY:
            issues.append("Kakao API 키가 설정되지 않음 (지도 기능 비활성화)")
        
        # 폰트 파일 체크
        if CUSTOM_FONT_PATH and not CUSTOM_FONT_PATH.exists():
            issues.append(f"폰트 파일 없음: {CUSTOM_FONT_PATH}")
    
    # 디렉토리 체크
    required_dirs = [DATA_DIR, PDF_DIR, MD_DIR, PLANS_DIR, PLANS_PDF_DIR, PLANS_MD_DIR, RESTAURANT_DIR, RESTAURANT_MD_DIR]  # 🔧 맛집 디렉토리 추가
    for dir_path in required_dirs:
        if not dir_path.exists():
            issues.append(f"필수 디렉토리 없음: {dir_path}")
    
    # 🔧 API 키 없어도 valid=True로 설정 (경고만)
    if issues:
        # API 키 문제만 있는 경우에는 valid=True
        api_only_issues = [issue for issue in issues if "API 키" not in issue]
        if not api_only_issues:  # API 키 문제만 있는 경우
            return {
                "valid": True,
                "message": "; ".join(issues)
            }
        else:  # 다른 심각한 문제가 있는 경우
            return {
                "valid": False,
                "message": "; ".join(issues)
            }
    else:
        return {
            "valid": True,
            "message": "모든 설정이 정상입니다"
        }

# ===== 메시지 템플릿 =====
MESSAGES = {
    "local_only": "⚠️ 이 기능은 로컬 환경에서만 사용 가능합니다.",
    "deployment_mode": "☁️ 배포 환경에서는 읽기 전용으로 실행됩니다.",
    "api_required": "🔑 이 기능은 OpenAI API 키가 필요합니다.",
    "no_api_key": "🔑 OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.",
    "font_not_found": "🎨 배민주아체 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.",
    "crawling_disabled": "📡 배포 환경에서는 크롤링이 비활성화됩니다.",
    "config_error": "⚙️ 설정에 문제가 있습니다. 확인 후 다시 시도해주세요.",
    "success": "✅ 작업이 성공적으로 완료되었습니다.",
    "error": "❌ 작업 중 오류가 발생했습니다.",
    "warning": "⚠️ 주의사항이 있습니다.",
    "info": "ℹ️ 정보"
}

# ===== 로깅 설정 =====
def setup_logging():
    """로깅 설정"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)
    
    # 콘솔 + 파일 로깅
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding='utf-8')  # 🔧 LOG_FILE 사용
        ]
    )

# 초기 설정
if __name__ == "__main__":
    setup_logging()
    env_info = get_env_info()
    validation = validate_config()
    
    print("="*60)
    print("🏢 부산시청 정보포털 설정")
    print("="*60)
    print(f"환경: {env_info['environment']}")
    print(f"루트 디렉토리: {env_info['root_dir']}")
    print(f"데이터 디렉토리: {env_info['data_dir']}")
    print(f"업무계획 디렉토리: {env_info['plans_dir']}")  # 🔧 추가
    print(f"맛집 디렉토리: {env_info['restaurant_dir']}")  # 🔧 맛집 디렉토리 추가
    print(f"API 사용 가능: {env_info['api_available']}")
    print(f"카카오 API 사용 가능: {env_info['kakao_api_available']}")  # 🔧 카카오 API 추가
    print(f"폰트 사용 가능: {env_info['font_available']}")
    print(f"디버그 모드: {env_info['debug_mode']}")
    print(f"최대 크롤링 페이지: {env_info['max_pages']}")
    print("-"*60)
    print(f"설정 검증: {'✅ 통과' if validation['valid'] else '❌ 실패'}")
    if validation['message']:
        print(f"메시지: {validation['message']}")
    print("="*60)