"""
Complete Michelin Guide Busan Crawler - 미쉐린 가이드 부산 전용 크롤러
--------------------------------------------------------
미쉐린 가이드 부산 2025 맛집 크롤링:
1. 미쉐린 1스타 ⭐
2. 빕 구르망 (Bib Gourmand) 🍽️  
3. 셀렉티드 (Selected) ✨

새로운 기능:
- 미쉐린 등급별 분류 시스템
- 미쉐린 특화 정보 추출 (추천 이유, 특징 등)
- 품질 점수 시스템 (100점 만점)
- 상세한 디버깅 및 HTML 구조 분석
- 부산의맛 폴더에 통합 저장 (data/restaurants/md)
"""
from __future__ import annotations

import os
import re
import json
import time
import random
import logging
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('michelin_busan_crawler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ============================== 상수 정의 ============================== #

# 미쉐린 등급 및 지역 정보
MICHELIN_GRADES = ["1스타", "빕구르망", "셀렉티드"]
RESTAURANT_FOOD_TYPES = ["한식", "중식", "일식", "양식", "기타", "카페", "베이커리"]
RESTAURANT_REGIONS = {
    "원도심권": ["중구", "동구", "영도구", "서구"],
    "동부산권": ["해운대구", "수영구", "남구", "기장군"],
    "서부산권": ["사하구", "강서구", "사상구"],
    "북부산권": ["북구", "금정구", "동래구", "연제구", "부산진구"],
}

# 미쉐린 가이드 사이트 구조에 최적화된 CSS 셀렉터
MICHELIN_SELECTORS = {
    # 미쉐린 맛집 카드
    "restaurant_cards": [
        ".item",
        ".card",
        ".restaurant_item",
        ".michelin_item",
        "[class*='item']",
        "li",
        "div[onclick*='uc_seq']"
    ],
    
    # 미쉐린 등급 표시
    "grade_indicators": [
        ".michelin_star",
        ".star_rating", 
        ".grade",
        ".rating",
        "[class*='star']",
        "[class*='bib']",
        "[class*='selected']",
        "img[alt*='스타']",
        "img[alt*='빕']",
        "img[alt*='구르망']"
    ],
    
    # 맛집 이름
    "restaurant_names": [
        ".name",
        ".title",
        ".tit",
        "h3",
        "h4", 
        "h5",
        "strong",
        ".restaurant_name"
    ],
    
    # 메인 콘텐츠 영역
    "content_areas": [
        ".view_wrap",
        ".content_wrap", 
        ".detail_wrap",
        "#contents",
        ".main_content",
        ".view_contents",
        ".michelin_content"
    ],
    
    # 정보 테이블 및 리스트
    "info_containers": [
        ".cntInfoDetails",
        ".view_info",
        ".detail_info",
        ".restaurant_info",
        ".place_info",
        ".basic_info",
        ".info_table",
        ".content_info"
    ],
    
    # 설명 및 본문
    "descriptions": [
        ".cont",
        ".view_txt",
        ".detail_txt",
        ".content_txt", 
        ".description",
        ".intro_txt",
        ".summary",
        ".overview",
        "[class*='desc']"
    ]
}

# 정보 추출을 위한 키워드 매핑
INFO_FIELD_KEYWORDS = {
    "menu": [
        "대표 메뉴", "대표메뉴", "메뉴", "주요메뉴", "시그니처", "signature",
        "추천메뉴", "인기메뉴", "특선메뉴", "best menu", "특별 요리"
    ],
    "address": [
        "주소", "소재지", "위치", "address", "location", "addr"
    ],
    "phone": [
        "전화번호", "전화", "연락처", "tel", "phone", "contact"
    ],
    "hours": [
        "영업시간", "운영시간", "이용시간", "운영요일", "hours", "time",
        "오픈시간", "운영일시", "business hours"
    ],
    "closed": [
        "휴무일", "휴무", "정기휴무", "closed", "holiday", "break day"
    ],
    "price": [
        "가격", "요금", "price", "cost", "￦", "원", "만원"
    ],
    "michelin_reason": [
        "미쉐린", "추천 이유", "선정 이유", "특징", "평가", "리뷰"
    ]
}

# 미쉐린 등급 판별 키워드
MICHELIN_GRADE_KEYWORDS = {
    "1스타": ["1스타", "one star", "1 star", "미쉐린스타", "⭐"],
    "빕구르망": ["빕구르망", "bib gourmand", "비브구르망", "빕 구르망", "🍽️"],
    "셀렉티드": ["셀렉티드", "selected", "선정", "추천", "✨"]
}

# 제외할 텍스트 패턴
EXCLUDE_PATTERNS = [
    "로그인", "마이페이지", "언어선택", "Language", "한국어", "English", 
    "中文", "日本語", "부산에가면", "명소", "음식", "숙박", "쇼핑", "축제",
    "내주변", "추천여행", "일정", "테마", "미식투어", "체험", "해양",
    "무장애여행", "심리 테스트", "반려동물", "미쉐린 가이드", "비짓부산",
    "매거진", "여행준비", "AI 여행", "추천 서비스", "큐레이션", "가이드북",
    "지도", "문화관광", "해설사", "정보", "뉴스레터", "관광안내소",
    "유용한정보", "공지", "이벤트", "설문", "행사", "부산여행사진",
    "부산여행영상", "여행공유", "로컬관광상품", "홍보관", "부산관광브랜드",
    "부산이즈굿", "동백전"
]

# 파일명 정리용 정규식
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
INVALID_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def slugify(text: str, maxlen: int = 50) -> str:
    """파일명에 안전한 문자열로 변환"""
    if not text:
        return "untitled"
    
    # 유니코드 정규화
    text = unicodedata.normalize("NFKC", text)
    
    # 제어 문자 제거
    text = CONTROL_CHAR_RE.sub("", text)
    
    # 파일명에 사용할 수 없는 문자 제거
    text = INVALID_FILENAME_RE.sub("_", text)
    
    # 공백을 언더스코어로 변환
    text = re.sub(r"\s+", "_", text).strip("_")
    
    # 길이 제한
    return text[:maxlen]

def is_excluded_text(text: str) -> bool:
    """제외해야 할 텍스트인지 확인"""
    if not text or len(text.strip()) < 3:
        return True
    
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in EXCLUDE_PATTERNS)

def clean_text(text: str) -> str:
    """텍스트 정리"""
    if not text:
        return ""
    
    # 불필요한 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 특수 문자 정리
    text = re.sub(r'[^\w\s가-힣().,\-:￦₩$⭐🍽️✨]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# ============================== 메인 크롤러 클래스 ============================== #

class MichelinGuideBusanCrawler:
    """미쉐린 가이드 부산 전용 크롤러"""
    
    def __init__(self, output_dir: str = "./data/restaurants/md", debug: bool = False):
        self.base_url = "https://www.visitbusan.net"
        self.michelin_page_url = "https://www.visitbusan.net/index.do?menuCd=DOM_000000202017000000"
        
        # 디렉토리 설정 (부산의맛 폴더에 통합)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.debug_dir = Path("./debug_michelin")
        self.debug_dir.mkdir(exist_ok=True)
        
        self.failure_dir = Path("./failures_michelin")
        self.failure_dir.mkdir(exist_ok=True)
        
        # 상태 변수
        self.driver = None
        self.debug = debug
        
        # 지역 매핑 테이블
        self.district_to_region = {}
        for region, districts in RESTAURANT_REGIONS.items():
            for district in districts:
                self.district_to_region[district] = region
        
        # 통계 정보
        self.stats = {
            "total_items": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "quality_scores": [],
            "michelin_grades": {"1스타": 0, "빕구르망": 0, "셀렉티드": 0}
        }
        
        logger.info("✅ 미쉐린 가이드 부산 크롤러 초기화 완료")

    # ============================== WebDriver 관리 ============================== #
    
    def setup_driver(self) -> bool:
        """Selenium WebDriver 설정"""
        logger.info("🔧 WebDriver 설정 중...")
        
        options = webdriver.ChromeOptions()
        
        # 헤드리스 모드 설정
        if not self.debug:
            options.add_argument("--headless=new")
        
        # 안정성을 위한 옵션들
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        
        # 자동화 탐지 방지
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # 언어 설정
        options.add_argument("--lang=ko-KR")
        options.add_argument("--accept-lang=ko-KR,ko,en-US,en")
        
        # User-Agent 설정
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # 자동화 탐지 방지 스크립트 실행
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            if self.debug:
                logger.info("🔍 디버그 모드: 브라우저 창이 표시됩니다")
            
            logger.info("✅ WebDriver 준비 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ WebDriver 설정 실패: {e}")
            return False

    def wait_for_page_load(self, timeout: int = 20) -> bool:
        """페이지 완전 로딩 대기"""
        try:
            # 기본 페이지 로딩 대기
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # jQuery가 있다면 Ajax 요청 완료 대기
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: driver.execute_script(
                        "return typeof jQuery !== 'undefined' ? jQuery.active == 0 : true"
                    )
                )
            except:
                pass
            
            # 추가 안전 대기
            time.sleep(random.uniform(2.0, 3.0))
            return True
            
        except TimeoutException:
            logger.warning("⚠️ 페이지 로딩 타임아웃")
            return False

    def close_driver(self):
        """WebDriver 종료"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔧 WebDriver 종료 완료")
            except Exception as e:
                logger.warning(f"WebDriver 종료 중 오류: {e}")

    # ============================== 미쉐린 페이지 크롤링 ============================== #
    
    def crawl_michelin_restaurants(self) -> List[Dict[str, Any]]:
        """미쉐린 가이드 부산 맛집 리스트 크롤링"""
        logger.info("🕷️ 미쉐린 가이드 부산 페이지 크롤링 시작...")
        
        if not self.driver:
            logger.error("WebDriver가 초기화되지 않음")
            return []
        
        try:
            # 미쉐린 페이지 이동
            logger.info(f"🌐 미쉐린 페이지 URL: {self.michelin_page_url}")
            self.driver.get(self.michelin_page_url)
            
            # 페이지 로딩 대기
            if not self.wait_for_page_load():
                logger.warning("⚠️ 미쉐린 페이지 로딩 실패")
                return []
            
            # 디버그용 HTML 저장
            if self.debug:
                debug_file = self.debug_dir / "michelin_main_page.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info(f"🔍 미쉐린 페이지 HTML 저장: {debug_file}")
            
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # 미쉐린 맛집 아이템 추출
            items = self.extract_michelin_items_from_page(soup)
            
            logger.info(f"📋 미쉐린 가이드에서 {len(items)}개 맛집 추출 완료")
            return items
            
        except Exception as e:
            logger.error(f"❌ 미쉐린 페이지 크롤링 실패: {e}")
            return []

    def extract_michelin_items_from_page(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """미쉐린 페이지에서 맛집 아이템 추출"""
        items = []
        
        # 미쉐린 맛집 카드들 찾기
        restaurant_cards = []
        
        # 다양한 셀렉터로 카드 찾기
        for selector in MICHELIN_SELECTORS["restaurant_cards"]:
            cards = soup.select(selector)
            if cards:
                restaurant_cards.extend(cards)
                logger.info(f"🔍 '{selector}' 셀렉터로 {len(cards)}개 카드 발견")
        
        # uc_seq가 포함된 링크로도 찾기
        uc_seq_links = soup.find_all("a", href=lambda x: x and "uc_seq=" in x)
        uc_seq_onclick = soup.find_all(attrs={"onclick": lambda x: x and "uc_seq=" in x if x else False})
        
        all_elements = list(set(restaurant_cards + uc_seq_links + uc_seq_onclick))
        logger.info(f"🔍 총 {len(all_elements)}개 미쉐린 관련 요소 발견")
        
        for element in all_elements:
            try:
                # URL 추출
                url = self.extract_url_from_element(element)
                if not url:
                    continue
                
                uc_seq = self.extract_uc_seq_from_url(url)
                if not uc_seq:
                    continue
                
                # 맛집 이름 추출
                name = self.extract_restaurant_name_from_element(element)
                if not name or is_excluded_text(name):
                    continue
                
                # 미쉐린 등급 추출
                michelin_grade = self.extract_michelin_grade_from_element(element, soup)
                
                items.append({
                    "name": name,
                    "url": url,
                    "uc_seq": uc_seq,
                    "michelin_grade": michelin_grade,
                    "extraction_source": "michelin_page"
                })
                
            except Exception as e:
                if self.debug:
                    logger.debug(f"요소 처리 중 오류: {e}")
        
        # 중복 제거 (같은 uc_seq)
        unique_items = []
        seen_uc_seqs = set()
        
        for item in items:
            if item["uc_seq"] not in seen_uc_seqs:
                unique_items.append(item)
                seen_uc_seqs.add(item["uc_seq"])
                self.stats["michelin_grades"][item["michelin_grade"]] += 1
        
        # 디버그 정보 출력
        if self.debug and unique_items:
            logger.info("🔍 추출된 미쉐린 맛집 샘플:")
            for i, item in enumerate(unique_items[:5]):
                logger.info(f"  {i+1}. {item['name']} ({item['michelin_grade']}, uc_seq: {item['uc_seq']})")
        
        return unique_items

    def extract_url_from_element(self, element) -> Optional[str]:
        """요소에서 URL 추출"""
        # href 속성에서 추출
        href = element.get("href")
        if href and "uc_seq=" in href:
            return urljoin(self.base_url, href) if not href.startswith("http") else href
        
        # onclick 속성에서 추출
        onclick = element.get("onclick")
        if onclick and "uc_seq=" in onclick:
            # onclick에서 uc_seq 추출하여 URL 구성
            uc_seq_match = re.search(r"uc_seq[=:]\s*['\"]?(\d+)", onclick)
            if uc_seq_match:
                uc_seq = uc_seq_match.group(1)
                # 기본 상세 페이지 URL 패턴
                return f"{self.base_url}/index.do?menuCd=DOM_000000202017001000&uc_seq={uc_seq}"
        
        # 자식 요소에서 찾기
        link_child = element.find("a", href=lambda x: x and "uc_seq=" in x)
        if link_child:
            href = link_child.get("href")
            return urljoin(self.base_url, href) if not href.startswith("http") else href
        
        return None

    def extract_restaurant_name_from_element(self, element) -> str:
        """요소에서 맛집 이름 추출"""
        # 다양한 방법으로 이름 추출 시도
        name_selectors = MICHELIN_SELECTORS["restaurant_names"]
        
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                text = clean_text(name_elem.get_text(strip=True))
                if text and not is_excluded_text(text) and self.is_valid_restaurant_name(text):
                    return text
        
        # 전체 텍스트에서 추출
        full_text = clean_text(element.get_text(strip=True))
        if full_text and not is_excluded_text(full_text) and self.is_valid_restaurant_name(full_text):
            # 첫 번째 유의미한 단어/구문 추출
            words = full_text.split()
            if words:
                for i in range(1, min(4, len(words) + 1)):
                    candidate = " ".join(words[:i])
                    if 2 <= len(candidate) <= 50 and not is_excluded_text(candidate):
                        return candidate
        
        return ""

    def extract_michelin_grade_from_element(self, element, soup: BeautifulSoup) -> str:
        """요소에서 미쉐린 등급 추출"""
        # 페이지 제목에서 미쉐린 등급 확인 (가장 정확함)
        page_title = soup.find("title")
        if page_title:
            title_text = page_title.get_text().lower()
            if "미쉐린 1스타" in title_text or "michelin 1 star" in title_text:
                return "1스타"
        
        # tit_sub 클래스에서 미쉐린 등급 확인
        tit_sub = soup.select_one(".tit_sub")
        if tit_sub:
            sub_text = tit_sub.get_text().lower()
            if "미쉐린 1스타" in sub_text or "1스타" in sub_text:
                return "1스타"
            elif "빕구르망" in sub_text or "bib gourmand" in sub_text:
                return "빕구르망"
        
        # 요소 내에서 등급 이미지나 텍스트 찾기
        element_text = element.get_text().lower()
        element_html = str(element).lower()
        
        # 이미지 alt 텍스트에서 찾기
        imgs = element.find_all("img")
        for img in imgs:
            alt = img.get("alt", "").lower()
            src = img.get("src", "").lower()
            
            # 1스타 확인
            if any(keyword in alt for keyword in ["1스타", "one star", "1 star", "스타"]):
                return "1스타"
            if any(keyword in src for keyword in ["star", "1star"]):
                return "1스타"
            
            # 빕구르망 확인
            if any(keyword in alt for keyword in ["빕구르망", "bib gourmand", "비브구르망", "빕", "구르망"]):
                return "빕구르망"
            if any(keyword in src for keyword in ["bib", "gourmand"]):
                return "빕구르망"
        
        # 텍스트에서 등급 찾기
        for grade, keywords in MICHELIN_GRADE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in element_text or keyword.lower() in element_html:
                    return grade
        
        # 기본값은 셀렉티드 (미쉐린 가이드에 소개된 맛집)
        return "셀렉티드"

    def is_valid_restaurant_name(self, name: str) -> bool:
        """유효한 맛집 이름인지 확인"""
        if not name or len(name.strip()) < 2:
            return False
        
        name = name.strip()
        
        # 블랙리스트 검사
        blacklist = {
            "길찾기", "위치보기", "상세보기", "더보기", "지도보기", "로드뷰",
            "View", "Map", "Details", "More", "미쉐린", "가이드"
        }
        if name in blacklist:
            return False
        
        # 제외 패턴 검사
        if is_excluded_text(name):
            return False
        
        # 길이 검사
        if len(name) > 100:
            return False
        
        # 숫자만 있는 이름 제외
        if re.match(r"^\d+$", name):
            return False
        
        return True

    @staticmethod
    def extract_uc_seq_from_url(url: str) -> Optional[str]:
        """URL에서 uc_seq 값 추출"""
        try:
            # URL 파라미터에서 추출
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            uc_seq = params.get('uc_seq', [None])[0]
            if uc_seq:
                return uc_seq
            
            # URL 경로에서 추출
            uc_seq_match = re.search(r"uc_seq[=:](\d+)", url)
            if uc_seq_match:
                return uc_seq_match.group(1)
            
            return None
        except Exception:
            return None

    # ============================== 상세 페이지 크롤링 ============================== #
    
    def extract_restaurant_details(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """미쉐린 맛집 상세 정보 추출"""
        try:
            logger.info(f"   📄 상세 정보 추출 중: {item['name']} ({item['michelin_grade']})")
            
            # 상세 페이지 이동
            self.driver.get(item["url"])
            
            # 페이지 로딩 대기
            if not self.wait_for_page_load():
                logger.warning(f"   ⚠️ 상세 페이지 로딩 실패: {item['name']}")
                return None
            
            # 디버그용 HTML 저장
            if self.debug:
                debug_file = self.debug_dir / f"detail_{item['uc_seq']}_{slugify(item['name'])}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info(f"🔍 상세 페이지 HTML 저장: {debug_file}")
            
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # 콘텐츠 영역 찾기
            content_area = self.find_main_content_area(soup)
            if not content_area:
                logger.warning(f"   ⚠️ 콘텐츠 영역을 찾을 수 없음: {item['name']}")
                content_area = soup
            
            # 기본 정보 구조체 생성
            restaurant_data = self.create_base_restaurant_data(item)
            
            # 다양한 방법으로 정보 추출
            self.extract_page_title(content_area, restaurant_data)
            self.extract_information_from_tables(content_area, restaurant_data)
            self.extract_information_from_text_patterns(content_area, restaurant_data)
            self.extract_menu_information(content_area, restaurant_data)
            self.extract_description_text(content_area, restaurant_data)
            self.extract_michelin_specific_info(content_area, restaurant_data)
            
            # 데이터 후처리 및 검증
            self.post_process_restaurant_data(restaurant_data)
            
            logger.info(f"   ✅ 상세 정보 추출 완료: {restaurant_data['name']} ({restaurant_data['michelin_grade']})")
            return restaurant_data
            
        except Exception as e:
            logger.error(f"   ❌ 상세 정보 추출 실패 ({item['name']}): {e}")
            return None

    def find_main_content_area(self, soup: BeautifulSoup):
        """메인 콘텐츠 영역 찾기"""
        # Visit Busan 실제 구조에 맞는 셀렉터들
        visitbusan_content_selectors = [
            ".cntInfoDetails",
            ".cont",
            ".vTab01",
            "#tab_con",
            ".fesL",
            "#section2"
        ]
        
        for selector in visitbusan_content_selectors:
            content = soup.select_one(selector)
            if content:
                return content
        
        # 기존 셀렉터들도 시도
        for selector in MICHELIN_SELECTORS["content_areas"]:
            content = soup.select_one(selector)
            if content:
                return content
        
        return None

    def create_base_restaurant_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """기본 미쉐린 맛집 데이터 구조체 생성"""
        return {
            "name": item["name"],
            "url": item["url"],
            "uc_seq": item["uc_seq"],
            "category": "미쉐린가이드",
            "michelin_grade": item["michelin_grade"],
            "food_type": "한식",
            "address": "",
            "region": "원도심권",
            "district": "",
            "representative_menu": [],
            "phone": "",
            "hours": "",
            "closed_days": "",
            "description": "",
            "michelin_reason": "",
            "tags": [],
            "_flags": [],
            "_extraction_info": {
                "extraction_source": item.get("extraction_source", "unknown"),
                "extraction_timestamp": datetime.now().isoformat()
            }
        }

    def extract_page_title(self, content_area, restaurant_data: Dict[str, Any]):
        """페이지 제목 추출"""
        title_selectors = [
            ".view_tit",
            ".detail_tit", 
            ".page_tit",
            ".content_tit",
            ".main_tit",
            "h1.tit",
            "h2.tit",
            "h1",
            "h2"
        ]
        
        for selector in title_selectors:
            title_elem = content_area.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text(strip=True))
                if title and not is_excluded_text(title) and len(title) >= 2:
                    restaurant_data["name"] = title
                    return

    def extract_information_from_tables(self, content_area, restaurant_data: Dict[str, Any]):
        """테이블에서 정보 추출"""
        # Visit Busan 실제 구조: .cntInfoDetails ul.InfoD-List li 패턴
        info_lists = content_area.select(".cntInfoDetails ul.InfoD-List li")
        
        for li in info_lists:
            label_elem = li.select_one("p")
            value_elem = li.select_one("span")
            
            if label_elem and value_elem:
                label = clean_text(label_elem.get_text(strip=True))
                value = clean_text(value_elem.get_text(strip=True))
                
                if "대표 메뉴" in label and not restaurant_data["representative_menu"]:
                    menu_html = value_elem.decode_contents()
                    menu_items = menu_html.split('<br>')
                    menus = []
                    for item in menu_items:
                        clean_item = clean_text(re.sub(r'<[^>]+>', '', item))
                        if clean_item and len(clean_item) > 3:
                            menus.append(clean_item)
                    restaurant_data["representative_menu"] = menus[:5]
                
                elif "주소" in label and not restaurant_data["address"]:
                    if len(value) > 5:
                        restaurant_data["address"] = value
                        
                elif "전화번호" in label and not restaurant_data["phone"]:
                    restaurant_data["phone"] = value
                    
                elif "휴무일" in label and not restaurant_data["closed_days"]:
                    restaurant_data["closed_days"] = value
                    
                elif ("운영요일" in label or "영업시간" in label) and not restaurant_data["hours"]:
                    restaurant_data["hours"] = value
        
        # 기존 테이블 구조도 시도
        for container_selector in MICHELIN_SELECTORS["info_containers"]:
            containers = content_area.select(container_selector)
            for container in containers:
                # dt/dd 구조
                dt_elements = container.find_all("dt")
                for dt in dt_elements:
                    dt_text = clean_text(dt.get_text(strip=True))
                    dd = dt.find_next_sibling("dd")
                    if dd:
                        dd_text = clean_text(dd.get_text(strip=True))
                        self.assign_field_value_by_keyword(dt_text, dd_text, restaurant_data)

    def extract_information_from_text_patterns(self, content_area, restaurant_data: Dict[str, Any]):
        """텍스트 패턴으로 정보 추출"""
        full_text = content_area.get_text()
        
        # 전화번호 패턴
        if not restaurant_data["phone"]:
            phone_patterns = [
                r"(0\d{2,3}[-\s]\d{3,4}[-\s]\d{4})",
                r"(\d{3}[-\s]\d{3,4}[-\s]\d{4})",
                r"(0\d{10})",
                r"(\d{10,11})"
            ]
            
            for pattern in phone_patterns:
                matches = re.findall(pattern, full_text)
                for match in matches:
                    phone = re.sub(r"[^\d]", "", match)
                    if len(phone) >= 10:
                        if phone.startswith("0"):
                            formatted_phone = f"{phone[:4]}-{phone[4:8]}-{phone[8:]}"
                        else:
                            formatted_phone = f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"
                        restaurant_data["phone"] = formatted_phone
                        break
                if restaurant_data["phone"]:
                    break
        
        # 주소 패턴
        if not restaurant_data["address"]:
            address_patterns = [
                r"주소[:\s]*([^\n]*(?:구|군)[^\n]{5,50})",
                r"(부산[^\n]*(?:구|군)[^\n]{5,50})",
                r"([^\n]*(?:구|군)[^\n]*(?:번길|로|동)[^\n]{5,50})"
            ]
            
            for pattern in address_patterns:
                matches = re.findall(pattern, full_text)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    
                    address = clean_text(match)
                    if (len(address) > 10 and 
                        ("부산" in address or any(district in address for district in self.district_to_region.keys())) and
                        not is_excluded_text(address)):
                        restaurant_data["address"] = address
                        break
                if restaurant_data["address"]:
                    break

    def extract_menu_information(self, content_area, restaurant_data: Dict[str, Any]):
        """메뉴 정보 추출"""
        if restaurant_data["representative_menu"]:
            return
        
        full_text = content_area.get_text()
        menus = []
        
        # 가격이 포함된 메뉴 라인 추출
        price_menu_patterns = [
            r"([^\n]*￦[\d,]+[^\n]*)",
            r"([^\n]*₩[\d,]+[^\n]*)",
            r"([^\n]*\d{1,3}[,\d]*원[^\n]*)",
            r"([^\n]*\d{1,3}[,\d]*천원[^\n]*)",
            r"([^\n]*\d{1,3}[,\d]*만원[^\n]*)"
        ]
        
        for pattern in price_menu_patterns:
            matches = re.findall(pattern, full_text)
            for match in matches:
                menu_text = clean_text(match)
                if (len(menu_text) > 5 and 
                    len(menu_text) < 100 and 
                    not is_excluded_text(menu_text)):
                    menus.append(menu_text)
        
        # 대표 메뉴 키워드로 추출
        if not menus:
            menu_keyword_patterns = [
                r"대표[^\n]*메뉴[:\s]*([^\n]{5,100})",
                r"시그니처[:\s]*([^\n]{5,100})",
                r"추천메뉴[:\s]*([^\n]{5,100})",
                r"인기메뉴[:\s]*([^\n]{5,100})"
            ]
            
            for pattern in menu_keyword_patterns:
                matches = re.findall(pattern, full_text)
                for match in matches:
                    menu_text = clean_text(match)
                    if not is_excluded_text(menu_text):
                        menu_items = re.split(r'[,/·]', menu_text)
                        for item in menu_items:
                            item = item.strip()
                            if len(item) > 3 and len(item) < 50:
                                menus.append(item)
        
        # 중복 제거 및 상위 5개 선택
        unique_menus = []
        seen = set()
        for menu in menus:
            if menu not in seen and len(unique_menus) < 5:
                unique_menus.append(menu)
                seen.add(menu)
        
        restaurant_data["representative_menu"] = unique_menus

    def extract_description_text(self, content_area, restaurant_data: Dict[str, Any]):
        """설명 텍스트 추출"""
        # 1. meta description에서 먼저 추출
        meta_desc = content_area.find('meta', {'name': 'description'})
        if not meta_desc:
            meta_desc = content_area.find_parent('html').find('meta', {'name': 'description'}) if content_area.find_parent('html') else None
        
        if meta_desc:
            desc_content = meta_desc.get('content', '')
            if desc_content and len(desc_content) > 20 and not is_excluded_text(desc_content):
                restaurant_data["description"] = desc_content
                return
        
        # 2. Visit Busan 구조에서 추출
        visitbusan_desc_selectors = [
            ".cont",
            ".vTab01 .cont",
            ".innerwrap .cont"
        ]
        
        for selector in visitbusan_desc_selectors:
            desc_elements = content_area.select(selector)
            for elem in desc_elements:
                desc_text = clean_text(elem.get_text(strip=True))
                if (len(desc_text) > 30 and 
                    len(desc_text) < 500 and 
                    not is_excluded_text(desc_text)):
                    restaurant_data["description"] = desc_text[:300]
                    return
        
        # 3. 기본 설명 섹션에서 추출
        for desc_selector in MICHELIN_SELECTORS["descriptions"]:
            desc_elements = content_area.select(desc_selector)
            for elem in desc_elements:
                desc_text = clean_text(elem.get_text(strip=True))
                if (len(desc_text) > 30 and 
                    len(desc_text) < 500 and 
                    not is_excluded_text(desc_text)):
                    restaurant_data["description"] = desc_text[:300]
                    return

    def extract_michelin_specific_info(self, content_area, restaurant_data: Dict[str, Any]):
        """미쉐린 특화 정보 추출"""
        full_text = content_area.get_text()
        
        # 미쉐린 추천 이유나 특징 추출
        michelin_patterns = [
            r"미쉐린[^\n]*([^\n]{20,200})",
            r"추천[^\n]*이유[:\s]*([^\n]{20,200})",
            r"선정[^\n]*이유[:\s]*([^\n]{20,200})",
            r"특징[:\s]*([^\n]{20,200})",
            r"평가[:\s]*([^\n]{20,200})"
        ]
        
        for pattern in michelin_patterns:
            matches = re.findall(pattern, full_text)
            for match in matches:
                reason_text = clean_text(match)
                if (len(reason_text) > 10 and 
                    not is_excluded_text(reason_text)):
                    restaurant_data["michelin_reason"] = reason_text[:200]
                    break
            if restaurant_data["michelin_reason"]:
                break

    def assign_field_value_by_keyword(self, key: str, value: str, restaurant_data: Dict[str, Any]):
        """키워드 기반으로 필드 값 할당"""
        if not key or not value:
            return
        
        key_lower = key.lower()
        value_clean = clean_text(value)
        
        # 메뉴 정보
        if (any(keyword.lower() in key_lower for keyword in INFO_FIELD_KEYWORDS["menu"]) and 
            not restaurant_data["representative_menu"] and
            not is_excluded_text(value_clean)):
            
            menu_items = re.split(r'[,/·\n]', value_clean)
            menus = []
            for item in menu_items:
                item = item.strip()
                if len(item) > 3 and len(item) < 80 and not is_excluded_text(item):
                    menus.append(item)
            
            if menus:
                restaurant_data["representative_menu"] = menus[:5]
        
        # 주소 정보
        elif (any(keyword.lower() in key_lower for keyword in INFO_FIELD_KEYWORDS["address"]) and 
              not restaurant_data["address"] and
              not is_excluded_text(value_clean)):
            
            if (len(value_clean) > 10 and 
                ("부산" in value_clean or any(district in value_clean for district in self.district_to_region.keys()))):
                restaurant_data["address"] = value_clean
        
        # 전화번호 정보
        elif (any(keyword.lower() in key_lower for keyword in INFO_FIELD_KEYWORDS["phone"]) and 
              not restaurant_data["phone"]):
            
            phone_digits = re.sub(r"[^\d]", "", value_clean)
            if len(phone_digits) >= 10:
                if phone_digits.startswith("0"):
                    formatted_phone = f"{phone_digits[:4]}-{phone_digits[4:8]}-{phone_digits[8:]}"
                else:
                    formatted_phone = f"{phone_digits[:3]}-{phone_digits[3:7]}-{phone_digits[7:]}"
                restaurant_data["phone"] = formatted_phone
        
        # 영업시간 정보
        elif (any(keyword.lower() in key_lower for keyword in INFO_FIELD_KEYWORDS["hours"]) and 
              not restaurant_data["hours"] and
              not is_excluded_text(value_clean)):
            
            if len(value_clean) > 3:
                restaurant_data["hours"] = value_clean
        
        # 휴무일 정보
        elif (any(keyword.lower() in key_lower for keyword in INFO_FIELD_KEYWORDS["closed"]) and 
              not restaurant_data["closed_days"] and
              not is_excluded_text(value_clean)):
            
            if len(value_clean) > 2:
                restaurant_data["closed_days"] = value_clean

    def post_process_restaurant_data(self, restaurant_data: Dict[str, Any]):
        """미쉐린 맛집 데이터 후처리"""
        # 지역 정보 추출
        self.extract_region_from_address(restaurant_data)
        
        # 음식 유형 추정
        restaurant_data["food_type"] = self.estimate_food_type_accurately(restaurant_data)
        
        # 플래그 설정
        self.set_data_quality_flags(restaurant_data)
        
        # 데이터 검증 및 정리
        self.validate_and_clean_data(restaurant_data)

    def extract_region_from_address(self, restaurant_data: Dict[str, Any]):
        """주소에서 지역 정보 추출"""
        address = restaurant_data.get("address", "")
        if not address:
            return
        
        for district, region in self.district_to_region.items():
            if district in address:
                restaurant_data["district"] = district
                restaurant_data["region"] = region
                return

    def estimate_food_type_accurately(self, restaurant_data: Dict[str, Any]) -> str:
        """정확한 음식 유형 추정"""
        text_sources = [
            restaurant_data["name"],
            " ".join(restaurant_data["representative_menu"]),
            restaurant_data["description"],
            restaurant_data["michelin_reason"]
        ]
        analysis_text = " ".join(text_sources).lower()
        
        food_type_patterns = {
            "양식": [
                r"프렌치|프랑스|이탈리안|파스타|스테이크|레스토랑|다이닝|양식|western|french|italian",
                r"피자|햄버거|샐러드|리조또|뇨끼|브런치|브런치카페",
                r"와인|와인바|bistro|brasserie|trattoria|페어링"
            ],
            "카페": [
                r"카페|커피|로스터리|coffee|café|cafe|라떼|에스프레소|아메리카노",
                r"원두|핸드드립|콜드브루|카푸치노|마키아또|모카"
            ],
            "베이커리": [
                r"베이커리|빵|제과|bakery|브레드|파티세리|크루아상",
                r"케이크|마카롱|쿠키|타르트|페이스트리|도넛"
            ],
            "일식": [
                r"일식|일본|스시|사시미|야키토리|라멘|japanese|우동|돈가스",
                r"사케|이자카야|오마카세|초밥|텐푸라|소바"
            ],
            "중식": [
                r"중식|중국|짜장|짬뽕|탕수육|chinese|만두|딤섬|마라",
                r"양장피|유린기|깐풍기|마파두부|볶음밥|울면"
            ],
            "한식": [
                r"국밥|갈비|불고기|비빔밥|냉면|한정식|korean|김치|된장|찌개",
                r"삼겹살|곱창|순대|족발|보쌈|치킨|떡볶이"
            ]
        }
        
        for food_type, pattern_groups in food_type_patterns.items():
            for patterns in pattern_groups:
                if re.search(patterns, analysis_text):
                    return food_type
        
        return "한식"

    def set_data_quality_flags(self, restaurant_data: Dict[str, Any]):
        """데이터 품질 플래그 설정"""
        flags = []
        
        if not restaurant_data["address"] or restaurant_data["address"] == "부산":
            restaurant_data["address"] = "부산"
            flags.append("addr_default")
        
        if not restaurant_data["representative_menu"]:
            restaurant_data["representative_menu"] = [f"{restaurant_data['name']} 메뉴"]
            flags.append("menu_default")
        
        if not restaurant_data["description"]:
            grade_emoji = {"1스타": "⭐", "빕구르망": "🍽️", "셀렉티드": "✨"}
            emoji = grade_emoji.get(restaurant_data["michelin_grade"], "✨")
            restaurant_data["description"] = f"{restaurant_data['name']}은(는) 미쉐린 가이드 부산 {restaurant_data['michelin_grade']} {emoji} 선정 맛집입니다."
            flags.append("desc_default")
        
        if not restaurant_data["hours"]:
            restaurant_data["hours"] = "영업시간 확인 필요"
            flags.append("hours_default")
        
        if not restaurant_data["phone"]:
            flags.append("phone_missing")
        
        if not restaurant_data["closed_days"]:
            flags.append("closed_missing")
        
        restaurant_data["_flags"] = flags

    def validate_and_clean_data(self, restaurant_data: Dict[str, Any]):
        """데이터 검증 및 정리"""
        if restaurant_data["name"]:
            restaurant_data["name"] = clean_text(restaurant_data["name"])
        
        if restaurant_data["address"]:
            restaurant_data["address"] = clean_text(restaurant_data["address"])
        
        clean_menus = []
        for menu in restaurant_data["representative_menu"]:
            clean_menu = clean_text(menu)
            if clean_menu and not is_excluded_text(clean_menu):
                clean_menus.append(clean_menu)
        restaurant_data["representative_menu"] = clean_menus[:5]
        
        if restaurant_data["description"]:
            restaurant_data["description"] = clean_text(restaurant_data["description"])
        
        if restaurant_data["michelin_reason"]:
            restaurant_data["michelin_reason"] = clean_text(restaurant_data["michelin_reason"])

    # ============================== 품질 검사 및 파일 생성 ============================== #
    
    def quality_check(self, restaurant_data: Dict[str, Any]) -> Tuple[bool, str]:
        """데이터 품질 검사"""
        if not restaurant_data:
            return False, "data_empty"
        
        name = restaurant_data.get("name", "")
        if not name or len(name.strip()) < 2:
            return False, "invalid_name"
        
        blacklist = {"길찾기", "위치보기", "상세보기", "더보기", "지도보기", "로드뷰"}
        if name in blacklist:
            return False, "name_blacklisted"
        
        if is_excluded_text(name):
            return False, "name_excluded_pattern"
        
        return True, "passed"

    def calculate_quality_score(self, restaurant_data: Dict[str, Any]) -> int:
        """데이터 품질 점수 계산 (100점 만점)"""
        score = 100
        flags = restaurant_data.get("_flags", [])
        
        # 미쉐린 등급에 따른 기본 점수 보너스
        grade_bonus = {"1스타": 10, "빕구르망": 5, "셀렉티드": 0}
        score += grade_bonus.get(restaurant_data.get("michelin_grade", "셀렉티드"), 0)
        
        # 플래그별 점수 차감
        score_deductions = {
            "addr_default": 15,
            "menu_default": 20,
            "desc_default": 10,
            "hours_default": 10,
            "phone_missing": 15,
            "closed_missing": 5
        }
        
        for flag in flags:
            if flag in score_deductions:
                score -= score_deductions[flag]
        
        return max(0, min(110, score))  # 0-110점 범위

    def create_markdown_file(self, restaurant_data: Dict[str, Any]) -> Optional[str]:
        """미쉐린 맛집 마크다운 파일 생성"""
        try:
            quality_score = self.calculate_quality_score(restaurant_data)
            restaurant_data["quality_score"] = quality_score
            
            # 파일명 생성 (미쉐린 등급 포함)
            safe_name = slugify(restaurant_data['name'])
            safe_food_type = slugify(restaurant_data['food_type'])
            safe_region = slugify(restaurant_data['region'])
            michelin_grade = slugify(restaurant_data['michelin_grade'])
            uc_seq = restaurant_data.get('uc_seq', 'unknown')
            
            if not safe_name or safe_name in ["길찾기", "위치보기", "상세보기"]:
                safe_name = f"michelin_{uc_seq}"
            
            # 부산의맛 폴더에 미쉐린 표시하여 저장
            filename = f"미쉐린_{michelin_grade}_{safe_region}_{safe_food_type}_{safe_name}_{uc_seq}.md"
            
            # 마크다운 내용 생성
            md_content = self.generate_markdown_content(restaurant_data)
            
            # 파일 저장
            file_path = self.output_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            grade_emoji = {"1스타": "⭐", "빕구르망": "🍽️", "셀렉티드": "✨"}
            emoji = grade_emoji.get(restaurant_data["michelin_grade"], "✨")
            logger.info(f"✅ MD 파일 생성: {filename} (미쉐린 {restaurant_data['michelin_grade']} {emoji}, 품질점수: {quality_score}/100)")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ MD 파일 생성 실패: {e}")
            return None

    def generate_markdown_content(self, data: Dict[str, Any]) -> str:
        """미쉐린 맛집 마크다운 내용 생성"""
        # 기본 정보
        name = data['name']
        region = data['region']
        district = data['district']
        category = data['category']
        michelin_grade = data['michelin_grade']
        food_type = data['food_type']
        phone = data.get('phone', '')
        address = data.get('address', '')
        hours = data.get('hours', '')
        closed_days = data.get('closed_days', '')
        url = data.get('url', '')
        uc_seq = data.get('uc_seq', '')
        michelin_reason = data.get('michelin_reason', '')
        current_date = datetime.now().strftime('%Y-%m-%d')

        # 미쉐린 등급 이모지
        grade_emoji = {"1스타": "⭐", "빕구르망": "🍽️", "셀렉티드": "✨"}
        emoji = grade_emoji.get(michelin_grade, "✨")

        # YAML 배열 생성
        menu_yaml = '\n'.join([f'  - "{menu}"' for menu in data.get('representative_menu', [])])
        if not menu_yaml:
            menu_yaml = '  - ""'

        # 메뉴 마크다운
        menu_md = ''.join([f'- {menu}  \n' for menu in data.get('representative_menu', [])])
        description = data.get('description', '') or f"{name}은(는) 미쉐린 가이드 부산 {michelin_grade} {emoji} 선정 맛집입니다."
        
        # 카카오맵 링크 생성
        kakao_search_query = f"{name} {district}" if district else name
        kakao_map_link = f"https://map.kakao.com/link/search/{kakao_search_query}"

        # 미쉐린 추천 이유 섹션
        michelin_section = ""
        if michelin_reason:
            michelin_section = f"""
## {emoji} 미쉐린 가이드 선정 이유

{michelin_reason}
"""

        # 마크다운 내용 생성
        md_content = f"""---
title: "{name}"
region: "{region}"
district: "{district}"
category: "{category}"
michelin_grade: "{michelin_grade}"
food_type: "{food_type}"
representative_menu:
{menu_yaml}
phone: "{phone}"
address: "{address}"
hours: "{hours}"
closed_days: "{closed_days}"
source_url: "{url}"
uc_seq: "{uc_seq}"
extraction_date: "{current_date}"
---

# {name} {emoji}

## 📍 이용안내

**미쉐린 등급**: {michelin_grade} {emoji}  
**대표 메뉴**  
{menu_md}

**전화번호**: {phone}  
**주소**: {address}  
**영업시간**: {hours}  
**휴무일**: {closed_days}

## 🗺️ 위치정보

- **카카오맵**: [지도에서 보기]({kakao_map_link})

## 🏷️ 분류 정보

- **지역**: {region} ({district})  
- **음식 유형**: {food_type}  
- **카테고리**: {category}  
- **미쉐린 등급**: {michelin_grade} {emoji}
{michelin_section}
## 📝 상세 정보

{description}

---
> 출처: 미쉐린 가이드 부산 2025 · 부산광역시(Visit Busan, {current_date[:4]}) · 공공누리 제1유형 · "{name} 소개글"
"""
        return md_content

    def save_failure_log(self, item: Dict[str, Any], error_info: str):
        """실패 로그 저장"""
        try:
            failure_data = {
                "item": item,
                "error": error_info,
                "timestamp": datetime.now().isoformat()
            }
            
            filename = f"failure_{item.get('uc_seq', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file_path = self.failure_dir / filename
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(failure_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"실패 로그 저장 중 오류: {e}")

    # ============================== 메인 실행 로직 ============================== #
    
    def run_michelin_crawling(self) -> List[str]:
        """미쉐린 가이드 부산 크롤링 실행 - 페이지네이션 지원"""
        logger.info("🚀 미쉐린 가이드 부산 크롤링 시작")
        
        # WebDriver 설정
        if not self.setup_driver():
            return []
        
        try:
            # 1단계: 미쉐린 맛집 리스트 수집 (모든 페이지)
            logger.info("=" * 60)
            logger.info("1단계: 미쉐린 가이드 부산 맛집 리스트 수집 (모든 페이지)")
            logger.info("=" * 60)
            
            all_items = []
            page = 1
            max_pages = 3  # 안전장치 (무한루프 방지)
            
            while page <= max_pages:
                logger.info(f"🔍 {page}페이지 크롤링 중...")
                
                # 페이지별 URL 생성 (Visit Busan 페이지네이션 방식)
                if page == 1:
                    page_url = self.michelin_page_url
                else:
                    # Visit Busan 페이지네이션: &page_no=2 방식
                    page_url = f"{self.michelin_page_url}&page_no={page}"
                
                # 페이지 이동
                self.driver.get(page_url)
                
                # 페이지 로딩 대기
                if not self.wait_for_page_load():
                    logger.warning(f"⚠️ {page}페이지 로딩 실패")
                    break
                
                # BeautifulSoup으로 파싱
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                
                # 미쉐린 맛집 아이템 추출
                page_items = self.extract_michelin_items_from_page(soup)
                
                if not page_items:
                    logger.info(f"📄 {page}페이지에서 더 이상 맛집을 찾을 수 없습니다. 크롤링 종료")
                    break
                
                all_items.extend(page_items)
                logger.info(f"📋 {page}페이지에서 {len(page_items)}개 맛집 추출")
                
                # 다음 페이지 존재 여부 확인
                next_page_exists = self.check_next_page_exists(soup, page)
                if not next_page_exists:
                    logger.info(f"📄 {page}페이지가 마지막 페이지입니다.")
                    break
                
                page += 1
                time.sleep(random.uniform(1.0, 2.0))  # 페이지 간 대기
            
            # 중복 제거
            unique_items = self.remove_duplicates(all_items)
            self.stats["total_items"] = len(unique_items)
            
            if not unique_items:
                logger.warning("⚠️ 추출된 미쉐린 맛집이 없습니다. 사이트 구조를 확인하세요.")
                return []
            
            logger.info(f"📊 총 {len(unique_items)}개 미쉐린 맛집 발견 ({len(all_items)}개에서 중복 제거)")
            
            # 등급별 통계 출력
            grade_stats = self.stats["michelin_grades"]
            logger.info(f"🏆 미쉐린 등급별 분포:")
            logger.info(f"  ⭐ 1스타: {grade_stats['1스타']}개")
            logger.info(f"  🍽️ 빕구르망: {grade_stats['빕구르망']}개")
            logger.info(f"  ✨ 셀렉티드: {grade_stats['셀렉티드']}개")
            
            # 2단계: 상세 정보 추출
            logger.info("=" * 60)
            logger.info("2단계: 미쉐린 맛집 상세 정보 추출")
            logger.info("=" * 60)
            
            detailed_restaurants = []
            failed_items = []
            
            for i, item in enumerate(unique_items, 1):
                grade_emoji = {"1스타": "⭐", "빕구르망": "🍽️", "셀렉티드": "✨"}
                emoji = grade_emoji.get(item["michelin_grade"], "✨")
                logger.info(f"[{i}/{len(unique_items)}] 🍽️ 처리 중: {item['name']} ({item['michelin_grade']} {emoji})")
                
                # 상세 정보 추출
                restaurant_data = self.extract_restaurant_details(item)
                
                if restaurant_data:
                    # 품질 검사
                    is_valid, reason = self.quality_check(restaurant_data)
                    if is_valid:
                        detailed_restaurants.append(restaurant_data)
                        self.stats["successful_extractions"] += 1
                        self.stats["quality_scores"].append(self.calculate_quality_score(restaurant_data))
                        logger.info(f"   ✅ 품질 검사 통과: {item['name']}")
                    else:
                        logger.warning(f"   ⚠️ 품질 검사 실패({reason}): {item['name']}")
                        failed_items.append((item, restaurant_data, reason))
                        self.stats["failed_extractions"] += 1
                        self.save_failure_log(item, f"quality_check_failed: {reason}")
                else:
                    logger.warning(f"   ❌ 정보 추출 실패: {item['name']}")
                    failed_items.append((item, None, "extraction_failed"))
                    self.stats["failed_extractions"] += 1
                    self.save_failure_log(item, "detail_extraction_failed")
                
                # 안정성을 위한 대기
                time.sleep(random.uniform(1.0, 2.0))
            
            # 3단계: 마크다운 파일 생성
            logger.info("=" * 60)
            logger.info("3단계: 미쉐린 맛집 마크다운 파일 생성")
            logger.info("=" * 60)
            
            created_files = []
            for restaurant in detailed_restaurants:
                file_path = self.create_markdown_file(restaurant)
                if file_path:
                    created_files.append(file_path)
            
            # 4단계: 결과 요약
            self.print_final_summary(unique_items, detailed_restaurants, failed_items, created_files)
            
            return created_files
            
        except Exception as e:
            logger.error(f"❌ 미쉐린 크롤링 프로세스 실패: {e}")
            return []
        finally:
            self.close_driver()

    def check_next_page_exists(self, soup: BeautifulSoup, current_page: int) -> bool:
        """다음 페이지 존재 여부 확인"""
        # Visit Busan 페이지네이션 패턴 확인
        pagination_selectors = [
            ".pagination",
            ".paging", 
            ".page_nav",
            "[class*='pag']",
            "a[href*='page_no=']"
        ]
        
        for selector in pagination_selectors:
            paging_elements = soup.select(selector)
            for elem in paging_elements:
                # 다음 페이지 번호가 있는지 확인
                next_page_links = elem.find_all("a", href=lambda x: x and f"page_no={current_page + 1}" in x)
                if next_page_links:
                    return True
                
                # "다음" 또는 ">" 버튼 확인
                next_buttons = elem.find_all("a", string=lambda x: x and ("다음" in x or ">" in x or "next" in x.lower()))
                if next_buttons:
                    return True
        
        # 전체 맛집 수 기반 확인 (Visit Busan은 총 43개)
        # 28개 이상 추출되었고 현재 1페이지면 2페이지 있을 가능성 높음
        if current_page == 1:
            return True
        
        return False

    def remove_duplicates(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 항목 제거 (uc_seq 기준)"""
        unique_items = {}
        for item in items:
            uc_seq = item.get("uc_seq")
            if uc_seq and uc_seq not in unique_items:
                unique_items[uc_seq] = item
        return list(unique_items.values())

    def print_final_summary(self, all_items, detailed_restaurants, failed_items, created_files):
        """최종 결과 요약 출력"""
        logger.info("=" * 80)
        logger.info("📊 미쉐린 가이드 부산 크롤링 최종 결과")
        logger.info("=" * 80)
        
        # 기본 통계
        logger.info(f"🔍 발견된 미쉐린 맛집: {len(all_items)}개")
        logger.info(f"✅ 성공적으로 추출: {len(detailed_restaurants)}개")
        logger.info(f"❌ 실패한 항목: {len(failed_items)}개")
        logger.info(f"📁 생성된 MD 파일: {len(created_files)}개")
        logger.info(f"💾 저장 위치: {self.output_dir} (부산의맛 폴더)")
        
        if self.debug:
            logger.info(f"🔍 디버그 데이터: {self.debug_dir}")
        logger.info(f"⚠️ 실패 로그: {self.failure_dir}")
        
        # 성공률 계산
        success_rate = (len(detailed_restaurants) / len(all_items) * 100) if all_items else 0
        logger.info(f"📊 전체 성공률: {success_rate:.1f}%")
        
        # 미쉐린 등급별 성공 통계
        if detailed_restaurants:
            grade_success = {"1스타": 0, "빕구르망": 0, "셀렉티드": 0}
            food_types = {}
            regions = {}
            
            for restaurant in detailed_restaurants:
                grade = restaurant.get('michelin_grade', '셀렉티드')
                grade_success[grade] += 1
                
                food_type = restaurant.get('food_type', '미분류')
                food_types[food_type] = food_types.get(food_type, 0) + 1
                
                region = restaurant.get('region', '미분류')
                regions[region] = regions.get(region, 0) + 1
            
            logger.info(f"🏆 미쉐린 등급별 성공:")
            logger.info(f"  ⭐ 1스타: {grade_success['1스타']}개")
            logger.info(f"  🍽️ 빕구르망: {grade_success['빕구르망']}개")
            logger.info(f"  ✨ 셀렉티드: {grade_success['셀렉티드']}개")
            
            logger.info("📈 추출 데이터 통계:")
            logger.info(f"  🍽️ 음식 유형 분포: {food_types}")
            logger.info(f"  🗺️ 지역 분포: {regions}")
        
        # 품질 점수 분석
        if self.stats["quality_scores"]:
            avg_quality = sum(self.stats["quality_scores"]) / len(self.stats["quality_scores"])
            max_quality = max(self.stats["quality_scores"])
            min_quality = min(self.stats["quality_scores"])
            
            # 품질 등급별 분포
            excellent = len([s for s in self.stats["quality_scores"] if s >= 90])
            good = len([s for s in self.stats["quality_scores"] if 80 <= s < 90])
            fair = len([s for s in self.stats["quality_scores"] if 70 <= s < 80])
            poor = len([s for s in self.stats["quality_scores"] if s < 70])
            
            logger.info(f"🎯 데이터 품질 분석:")
            logger.info(f"  평균 품질 점수: {avg_quality:.1f}/100점")
            logger.info(f"  최고 품질 점수: {max_quality}/100점")
            logger.info(f"  최저 품질 점수: {min_quality}/100점")
            logger.info(f"  품질 등급 분포:")
            logger.info(f"    🌟 최고품질 (90점 이상): {excellent}개")
            logger.info(f"    ✨ 고품질 (80-89점): {good}개")
            logger.info(f"    ✅ 양호 (70-79점): {fair}개")
            logger.info(f"    ⚠️ 개선필요 (70점 미만): {poor}개")
        
        # 실패 원인 분석
        if failed_items:
            failure_reasons = {}
            for _, _, reason in failed_items:
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            
            logger.info(f"🔍 실패 원인 분석:")
            for reason, count in failure_reasons.items():
                logger.info(f"  {reason}: {count}개")
        
        # 성능 통계
        logger.info("⚡ 성능 통계:")
        logger.info(f"  처리된 총 아이템: {self.stats['total_items']}개")
        logger.info(f"  성공적 추출: {self.stats['successful_extractions']}개")
        logger.info(f"  실패한 추출: {self.stats['failed_extractions']}개")
        
        # 개선 제안
        if success_rate < 80:
            logger.info("🔧 개선 제안:")
            logger.info("  • --debug 모드로 실행하여 HTML 구조 분석")
            logger.info("  • debug_michelin/ 폴더의 HTML 파일 확인")
            logger.info("  • failures_michelin/ 폴더의 실패 로그 분석")
            logger.info("  • Visit Busan 미쉐린 페이지 구조 변경 여부 확인")
        
        logger.info("🎉 미쉐린 가이드 부산 크롤링 완료!")
        logger.info("=" * 80)

# ============================== CLI 실행부 ============================== #

def main():
    """CLI 메인 함수"""
    import argparse
    
    print("🌟 미쉐린 가이드 부산 크롤러")
    print("=" * 80)
    print("✅ 미쉐린 가이드 부산 2025 특화 기능:")
    print("  1. ⭐ 미쉐린 1스타 맛집")
    print("  2. 🍽️ 빕 구르망 (Bib Gourmand) 맛집")
    print("  3. ✨ 셀렉티드 (Selected) 맛집")
    print("  4. 미쉐린 등급별 자동 분류")
    print("  5. 미쉐린 추천 이유 추출")
    print("  6. 부산의맛 폴더에 통합 저장")
    print("=" * 80)
    
    parser = argparse.ArgumentParser(description='미쉐린 가이드 부산 크롤러')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 (브라우저 표시 + 상세 HTML 저장)')
    parser.add_argument('--output', default='./data/restaurants/md', help='MD 파일 출력 디렉토리 (부산의맛 폴더)')
    args = parser.parse_args()
    
    print(f"🎯 실행 설정:")
    print(f"  디버그 모드: {'ON' if args.debug else 'OFF'}")
    print(f"  출력 디렉토리: {args.output}")
    
    if args.debug:
        print("🔍 디버그 모드 활성화:")
        print("  - 브라우저 창 표시")
        print("  - 미쉐린 페이지 HTML: debug_michelin/michelin_main_page.html")
        print("  - 상세 페이지 HTML: debug_michelin/detail_UCSEQ_NAME.html")
        print("  - 실패 로그: failures_michelin/failure_*.json")
    
    print("=" * 80)
    
    # 크롤러 실행
    start_time = datetime.now()
    crawler = MichelinGuideBusanCrawler(output_dir=args.output, debug=args.debug)
    created_files = crawler.run_michelin_crawling()
    end_time = datetime.now()
    
    # 최종 결과 출력
    print("=" * 80)
    execution_time = end_time - start_time
    
    if created_files:
        print(f"🎉 미쉐린 가이드 부산 크롤링 성공!")
        print(f"⏱️ 실행 시간: {execution_time}")
        print(f"📁 생성된 파일: {len(created_files)}개")
        
        print("\n📋 생성된 미쉐린 맛집 파일 (최신 10개):")
        for file_path in created_files[-10:]:
            file_name = Path(file_path).name
            if "미쉐린_1스타" in file_name:
                print(f"  ⭐ {file_name}")
            elif "미쉐린_빕구르망" in file_name:
                print(f"  🍽️ {file_name}")
            else:
                print(f"  ✨ {file_name}")
        
        if len(created_files) > 10:
            print(f"     ... 외 {len(created_files) - 10}개")
        
        print(f"\n📁 저장 위치:")
        print(f"  MD 파일: {crawler.output_dir} (부산의맛 폴더에 통합 저장)")
        if args.debug:
            print(f"  디버그 데이터: {crawler.debug_dir}")
        print(f"  실패 로그: {crawler.failure_dir}")
        
        print("\n🌟 미쉐린 가이드 부산 특징:")
        print("  • ⭐ 미쉐린 1스타 등급 자동 분류")
        print("  • 🍽️ 빕 구르망 등급 자동 분류")
        print("  • ✨ 셀렉티드 등급 자동 분류")
        print("  • 미쉐린 추천 이유 및 특징 추출")
        print("  • 부산의맛 폴더에 통합 관리")
        print("  • 미쉐린 등급별 품질 점수 보너스")
        
    else:
        print("❌ 미쉐린 크롤링 실패")
        print(f"⏱️ 실행 시간: {execution_time}")
        
        print("\n🔧 문제 해결 가이드:")
        print("  1. 디버그 모드로 재실행:")
        print("     python michelin_crawler.py --debug")
        print("  2. HTML 구조 분석:")
        print("     debug_michelin/ 폴더의 HTML 파일 확인")
        print("  3. 실패 원인 분석:")
        print("     failures_michelin/ 폴더의 JSON 로그 확인")
        print("  4. 네트워크 및 사이트 접근성 확인")
        print("  5. Visit Busan 미쉐린 페이지 구조 변경 여부 확인")
    
    print("=" * 80)

if __name__ == "__main__":
    main()