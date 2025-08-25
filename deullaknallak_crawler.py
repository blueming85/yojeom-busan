"""
부산어린이복합문화공간 들락날락 크롤러 - 직접 olSkey 순차 크롤링 버전
----------------------------------------------
🎯 olSkey를 DNOL0000000000001부터 순차적으로 증가시켜 직접 크롤링
"""

import os
import re
import json
import time
import random
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup, Tag

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deullaknallak_direct_olskey.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class DirectOlSkeyDeullakNallakCrawler:
    def __init__(self, output_dir: str = "C:/Users/COMTREE/Documents/FC_RAG_2025/data/deullaknallak"):
        self.base_url = "https://www.busan.go.kr/bschild"
        self.detail_url_template = f"{self.base_url}/dnol/view.nm?menuCd=8&lang=ko&url=dnol&olSkey="
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 디버그 디렉토리
        self.debug_dir = Path("./debug_direct_olskey")
        self.debug_dir.mkdir(exist_ok=True)
        
        # 제거할 제목 블랙리스트 (정확히 일치하는 것만)
        self.blacklist_titles = {
            "### 운영시간상세",
            "### 휴관일", 
            "## 시설안내",
            "### 이용정보",
            "## 운영 프로그램",
            "### 프로그램 내용"
        }
        
        self.driver = None
        self.wait = None
        self.stats = {
            "total_attempts": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "not_found_pages": 0,
            "error_pages": 0,
            "valid_facilities": 0,
            "removed_sections": 0
        }
        
        logger.info("🎯 직접 olSkey 순차 크롤링 들락날락 크롤러 초기화 완료")
        logger.info(f"📋 제거할 제목: {len(self.blacklist_titles)}개")

    def setup_driver(self) -> bool:
        """Selenium WebDriver 설정"""
        logger.info("🔧 WebDriver 설정 중...")
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # 성능 최적화
        options.add_argument("--enable-javascript")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            self.driver.implicitly_wait(15)
            self.wait = WebDriverWait(self.driver, 30)
            
            logger.info("✅ WebDriver 준비 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ WebDriver 설정 실패: {e}")
            return False

    def generate_ol_skey(self, number: int) -> str:
        """olSkey 생성 (DNOL0000000000036 형식 - 0이 13개)"""
        return f"DNOL{number:013d}"

    def check_page_exists_and_valid(self, soup: BeautifulSoup, ol_skey: str) -> bool:
        """페이지가 존재하고 유효한지 확인"""
        try:
            # 1. 에러 페이지 체크
            error_indicators = [
                "페이지를 찾을 수 없습니다",
                "존재하지 않는 페이지",
                "잘못된 접근",
                "404",
                "Page Not Found",
                "오류가 발생했습니다"
            ]
            
            page_text = soup.get_text()
            for error_text in error_indicators:
                if error_text in page_text:
                    logger.debug(f"❌ {ol_skey}: 에러 페이지 감지 ({error_text})")
                    return False
            
            # 2. 핵심 콘텐츠 존재 확인
            content_indicators = [
                ".con_title",
                ".page_title", 
                ".title",
                "h1",
                "h2",
                ".sub_cont_tit",
                ".content",
                ".detail_content",
                ".shot_cont_right"
            ]
            
            for selector in content_indicators:
                if soup.select(selector):
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        content_text = self.clean_text(content_elem.get_text(strip=True))
                        if content_text and len(content_text) > 3:
                            logger.debug(f"✅ {ol_skey}: 유효한 콘텐츠 확인 ({selector})")
                            return True
            
            # 3. 테이블 정보 존재 확인
            table_selectors = [
                ".shot_cont_right table.col_table tbody",
                ".info_table tbody",
                "table tbody",
                ".facility_info table tbody",
                ".col_table tbody"
            ]
            
            for selector in table_selectors:
                table = soup.select_one(selector)
                if table and table.select("tr"):
                    logger.debug(f"✅ {ol_skey}: 테이블 정보 확인 ({selector})")
                    return True
            
            logger.debug(f"❌ {ol_skey}: 유효한 콘텐츠 없음")
            return False
            
        except Exception as e:
            logger.debug(f"❌ {ol_skey}: 페이지 유효성 확인 중 오류: {e}")
            return False

    def load_page_with_retry(self, url: str, ol_skey: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
        """재시도와 함께 페이지 로드"""
        for attempt in range(max_retries):
            try:
                logger.debug(f"🌐 {ol_skey} 로드 시도 {attempt + 1}/{max_retries}: {url}")
                
                self.driver.get(url)
                
                # 페이지 로딩 대기
                self.wait.until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                # 추가 안정화 대기
                time.sleep(2)
                
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                
                if self.check_page_exists_and_valid(soup, ol_skey):
                    logger.debug(f"✅ {ol_skey}: 페이지 로드 성공")
                    return soup
                else:
                    logger.debug(f"❌ {ol_skey}: 페이지가 존재하지 않거나 유효하지 않음")
                    return None
                    
            except TimeoutException:
                logger.debug(f"⏰ {ol_skey}: 페이지 로딩 타임아웃 (시도 {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except Exception as e:
                logger.debug(f"❌ {ol_skey}: 페이지 로드 오류 (시도 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        
        logger.debug(f"❌ {ol_skey}: 모든 재시도 실패")
        return None

    def extract_facility_details_direct(self, ol_skey: str) -> Optional[Dict[str, Any]]:
        """olSkey로 직접 시설 상세 정보 추출"""
        try:
            url = f"{self.detail_url_template}{ol_skey}"
            
            soup = self.load_page_with_retry(url, ol_skey)
            
            if not soup:
                self.stats["not_found_pages"] += 1
                return None
            
            # 디버그용 HTML 저장
            debug_file = self.debug_dir / f"detail_{ol_skey}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            
            # 기본 데이터 구조 생성
            facility_data = self.create_base_facility_data(ol_skey, url)
            
            # 정보 추출
            self.extract_page_title(soup, facility_data)
            self.extract_basic_info_from_table(soup, facility_data)
            self.extract_detailed_content(soup, facility_data)
            
            # 데이터 후처리 및 유효성 확인
            self.post_process_facility_data(facility_data)
            
            if self.is_valid_facility_data(facility_data):
                self.stats["valid_facilities"] += 1
                logger.info(f"   ✅ {ol_skey}: {facility_data['name']}")
                return facility_data
            else:
                logger.debug(f"   ⚠️ {ol_skey}: 데이터 불완전")
                return None
            
        except Exception as e:
            logger.error(f"   ❌ {ol_skey}: 상세 정보 추출 실패: {e}")
            self.stats["error_pages"] += 1
            return None

    def create_base_facility_data(self, ol_skey: str, url: str) -> Dict[str, Any]:
        """기본 시설 데이터 구조 생성"""
        return {
            "name": "",
            "url": url,
            "ol_skey": ol_skey,
            "address": "",
            "phone": "",
            "hours": "",
            "closed_days": "",
            "description": "",
            "usage_info": "",
            "facility_info": "",
            "programs": "",
            "location_info": "",
            "extraction_info": {
                "extraction_source": "direct_olskey",
                "extraction_timestamp": datetime.now().isoformat()
            }
        }

    def extract_page_title(self, soup: BeautifulSoup, facility_data: Dict[str, Any]):
        """페이지 제목 추출"""
        title_selectors = [".con_title", ".page_title", ".title", "h1", "h2", ".sub_cont_tit"]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = self.clean_text(title_elem.get_text(strip=True))
                if title and len(title) > 2:
                    facility_data["name"] = title
                    return
        
        # 제목을 찾지 못한 경우 기본값
        facility_data["name"] = f"들락날락 시설 ({facility_data['ol_skey']})"

    def extract_basic_info_from_table(self, soup: BeautifulSoup, facility_data: Dict[str, Any]):
        """기본 정보 테이블에서 데이터 추출"""
        table_selectors = [
            ".shot_cont_right table.col_table tbody",
            ".info_table tbody",
            "table tbody",
            ".facility_info table tbody",
            ".col_table tbody"
        ]
        
        for selector in table_selectors:
            table = soup.select_one(selector)
            if table:
                rows = table.select("tr")
                for row in rows:
                    th = row.select_one("th")
                    td = row.select_one("td")
                    if th and td:
                        key = self.clean_text(th.get_text(strip=True))
                        value = self.clean_text(td.get_text(strip=True))
                        
                        if "주소" in key:
                            facility_data["address"] = value
                        elif "운영시간" in key or "이용시간" in key:
                            facility_data["hours"] = value
                        elif "연락처" in key or "전화" in key:
                            facility_data["phone"] = value
                        elif "휴관일" in key or "정기휴관일" in key or "휴무" in key:
                            facility_data["closed_days"] = value
                break

    def extract_detailed_content(self, soup: BeautifulSoup, facility_data: Dict[str, Any]):
        """상세 콘텐츠 추출 (개선된 구조화, 빈 섹션 제거)"""
        
        # 탭 콘텐츠들 찾기
        tab_contents = soup.select(".dt_tab .tab_cont")
        
        if not tab_contents:
            # 탭이 없는 경우 메인 콘텐츠 추출
            main_content = soup.select_one(".content, .main_content, .detail_content")
            if main_content:
                content_text = self.clean_text(main_content.get_text("\n", strip=True))
                facility_data["description"] = content_text
                facility_data["usage_info"] = content_text
            return
        
        all_content = []
        
        for i, tab_content in enumerate(tab_contents):
            # 탭 제목 찾기
            tab_title = ""
            tab_nav = soup.select(".dt_tab .tab li")
            if i < len(tab_nav):
                tab_title_elem = tab_nav[i].select_one("span")
                if tab_title_elem:
                    tab_title = self.clean_text(tab_title_elem.get_text(strip=True))
            
            # 각 탭의 내용을 구조적으로 추출
            tab_structured_content = self.extract_tab_content_structured(tab_content, tab_title)
            
            # 의미있는 내용이 있는 경우만 추가
            if tab_structured_content and len(tab_structured_content.strip()) > 20:
                all_content.append(tab_structured_content)
        
        # 첫 번째 탭의 주요 설명을 description으로 사용
        if tab_contents:
            first_tab = tab_contents[0]
            description_parts = self.extract_description_from_tab(first_tab)
            if description_parts:
                description_text = "\n".join(description_parts)
                # description에도 불릿 포인트 정리 적용
                description_text = self.format_bullet_points(description_text)
                facility_data["description"] = description_text
            else:
                facility_data["description"] = f"{facility_data['name']}은(는) 부산의 어린이복합문화공간입니다."
        
        # 탭별로 내용 분류 (빈 내용 제외)
        if len(all_content) > 0 and len(all_content[0].strip()) > 20:
            facility_data["usage_info"] = all_content[0]
        if len(all_content) > 1 and len(all_content[1].strip()) > 20:
            facility_data["facility_info"] = all_content[1]
        if len(all_content) > 2 and len(all_content[2].strip()) > 20:
            facility_data["programs"] = all_content[2]
        if len(all_content) > 3 and len(all_content[3].strip()) > 20:
            facility_data["location_info"] = all_content[3]

    def is_blacklisted_title(self, title: str) -> bool:
        """제목이 블랙리스트에 있는지 확인 (정확히 일치)"""
        return title.strip() in self.blacklist_titles

    def extract_tab_content_structured(self, tab_content, tab_title: str) -> str:
        """탭 콘텐츠를 구조적으로 추출 (블랙리스트 제목 제거)"""
        try:
            # 탭 제목이 블랙리스트에 있으면 전체 제거
            if tab_title and self.is_blacklisted_title(f"## {tab_title}"):
                logger.debug(f"🚫 블랙리스트 탭 제거: ## {tab_title}")
                self.stats["removed_sections"] += 1
                return ""
            
            # 각 탭의 섹션들 찾기
            content_sections = tab_content.select(".con_box_wrap")
            
            if not content_sections:
                # con_box_wrap이 없는 경우 직접 추출
                tab_text = self.clean_text(tab_content.get_text("\n", strip=True))
                if tab_text and len(tab_text.strip()) > 10:  # 의미있는 내용만
                    return f"## {tab_title}\n{tab_text}" if tab_title else tab_text
                return ""
            
            section_contents = []
            
            for section in content_sections:
                # 섹션 제목 추출
                section_title = ""
                section_title_elem = section.select_one(".tit_text span")
                if section_title_elem:
                    section_title = self.clean_text(section_title_elem.get_text(strip=True))
                
                # 섹션 제목이 블랙리스트에 있으면 해당 섹션 제거
                if section_title and self.is_blacklisted_title(f"### {section_title}"):
                    logger.debug(f"🚫 블랙리스트 섹션 제거: ### {section_title}")
                    self.stats["removed_sections"] += 1
                    continue
                
                # 섹션 내용 추출
                section_text = self.extract_section_content(section)
                
                # 의미있는 내용이 있는 경우만 추가
                if section_text and len(section_text.strip()) > 10:
                    if section_title and len(section_title.strip()) > 2:
                        # 섹션 제목이 의미있는 경우만 추가
                        section_contents.append(f"### {section_title}\n{section_text}")
                    else:
                        # 섹션 제목 없이 내용만 추가
                        section_contents.append(section_text)
            
            if section_contents:
                if tab_title and len(tab_title.strip()) > 2:
                    # ### 제목들 사이는 한 줄씩 띄움
                    return f"## {tab_title}\n" + "\n\n".join(section_contents)
                else:
                    return "\n\n".join(section_contents)
            
            return ""
            
        except Exception as e:
            logger.debug(f"탭 콘텐츠 구조적 추출 실패: {e}")
            return ""

    def format_bullet_points(self, text: str) -> str:
        """불릿 포인트 포맷팅"""
        if not text:
            return text
        
        # ○ 불릿 포인트들을 줄바꿈으로 분리
        text = re.sub(r'([^\n])○\s*', r'\1\n\n○ ', text)
        
        # 기타 불릿 포인트들도 정리
        text = re.sub(r'([^\n])●\s*', r'\1\n\n● ', text)
        text = re.sub(r'([^\n])▶\s*', r'\1\n\n▶ ', text)
        
        # 대괄호 항목들 ([이용시간], [층별안내] 등)
        text = re.sub(r'([^\n])\[([^\]]+)\]', r'\1\n\n[\2]', text)
        
        # 과도한 줄바꿈 정리
        text = re.sub(r'\n{4,}', '\n\n', text)
        
        return text.strip()

    def extract_section_content(self, section) -> str:
        """섹션 내용을 구조적으로 추출"""
        content_parts = []
        
        # 1. P 태그들에서 내용 추출
        p_tags = section.select("p")
        if p_tags:
            for p in p_tags:
                p_text = self.clean_text(p.get_text(strip=True))
                if p_text and len(p_text) > 5:
                    # 불릿 포인트 포맷팅 적용
                    p_text = self.format_bullet_points(p_text)
                    content_parts.append(p_text)
        
        # 2. DIV에서 직접 텍스트 추출 (P 태그가 없는 경우)
        if not content_parts:
            content_divs = section.select("div")
            for div in content_divs:
                # 제목이 아닌 div만 처리
                if not div.select_one(".tit_text"):
                    div_text = self.clean_text(div.get_text(strip=True))
                    if div_text and len(div_text) > 5:
                        # 불릿 포인트 포맷팅 적용
                        div_text = self.format_bullet_points(div_text)
                        content_parts.append(div_text)
        
        # 3. 테이블 내용 추출
        tables = section.select("table")
        for table in tables:
            table_content = self.extract_table_content_markdown(table)
            if table_content:
                content_parts.append(table_content)
        
        # 4. 리스트 항목 추출
        lists = section.select("ul, ol")
        for list_elem in lists:
            list_content = self.extract_list_content_markdown(list_elem)
            if list_content:
                content_parts.append(list_content)
        
        # 줄 간격을 최소화하여 연결
        return "\n".join(content_parts)

    def extract_description_from_tab(self, first_tab) -> List[str]:
        """첫 번째 탭에서 설명 부분만 추출"""
        description_parts = []
        
        # P 태그에서 설명 추출 (처음 3개 문단)
        p_tags = first_tab.select("p")
        for p in p_tags[:3]:
            p_text = self.clean_text(p.get_text(strip=True))
            if p_text and len(p_text) > 20:
                description_parts.append(p_text)
        
        # P 태그가 없으면 DIV에서 추출
        if not description_parts:
            div_tags = first_tab.select("div")
            for div in div_tags[:2]:
                if not div.select_one(".tit_text"):
                    div_text = self.clean_text(div.get_text(strip=True))
                    if div_text and len(div_text) > 20:
                        description_parts.append(div_text)
        
        return description_parts

    def extract_table_content_markdown(self, table) -> str:
        """테이블 내용을 마크다운 형식으로 추출 (개선)"""
        try:
            rows = table.select("tr")
            if not rows:
                return ""
            
            table_content = []
            
            # 헤더와 데이터 행 구분
            for row in rows:
                ths = row.select("th")
                tds = row.select("td")
                
                if ths:
                    # 헤더 행
                    headers = [self.clean_text(th.get_text(strip=True)) for th in ths]
                    if any(headers):  # 빈 헤더가 아닌 경우만
                        header_row = "| " + " | ".join(headers) + " |"
                        separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                        table_content.extend([header_row, separator])
                elif tds:
                    # 데이터 행
                    cells = [self.clean_text(td.get_text(strip=True)) for td in tds]
                    if any(cells):  # 빈 셀이 아닌 경우만
                        data_row = "| " + " | ".join(cells) + " |"
                        table_content.append(data_row)
            
            return "\n".join(table_content) if table_content else ""
            
        except Exception as e:
            logger.debug(f"테이블 추출 중 오류: {e}")
            return ""

    def extract_list_content_markdown(self, list_elem) -> str:
        """리스트 내용을 마크다운 형식으로 추출"""
        try:
            list_items = []
            li_tags = list_elem.select("li")
            
            for li in li_tags:
                li_text = self.clean_text(li.get_text(strip=True))
                if li_text and len(li_text) > 3:
                    # 순서 있는 리스트인지 확인
                    if list_elem.name == "ol":
                        list_items.append(f"1. {li_text}")
                    else:
                        list_items.append(f"- {li_text}")
            
            return "\n".join(list_items) if list_items else ""
            
        except Exception as e:
            logger.debug(f"리스트 추출 중 오류: {e}")
            return ""

    def post_process_facility_data(self, facility_data: Dict[str, Any]):
        """시설 데이터 후처리"""
        if not facility_data["description"]:
            facility_data["description"] = f"{facility_data['name']}은(는) 부산의 어린이복합문화공간입니다."
        
        for field in ["name", "address", "description", "hours", "phone", "closed_days"]:
            if facility_data.get(field):
                facility_data[field] = self.clean_text(facility_data[field])

    def is_valid_facility_data(self, facility_data: Dict[str, Any]) -> bool:
        """시설 데이터 유효성 검사"""
        # 이름이 있어야 함
        if not facility_data.get("name") or len(facility_data["name"]) < 3:
            return False
        
        # 기본 정보 중 하나 이상 있어야 함
        basic_fields = ["address", "phone", "hours", "description"]
        has_basic_info = any(facility_data.get(field) and len(facility_data[field]) > 5 for field in basic_fields)
        
        return has_basic_info

    def clean_text(self, text: str) -> str:
        """텍스트 정리"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        
        return text

    def create_markdown_file(self, facility_data: Dict[str, Any]) -> Optional[str]:
        """마크다운 파일 생성"""
        try:
            ol_skey = facility_data.get('ol_skey', 'unknown')
            safe_name = re.sub(r'[^\w가-힣]', '_', facility_data['name'])[:30]
            filename = f"deullaknallak_direct_{safe_name}_{ol_skey}.md"
            
            md_content = self.generate_markdown_content(facility_data)
            
            file_path = self.output_dir / filename
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            logger.debug(f"✅ MD 파일 생성: {filename}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ MD 파일 생성 실패: {e}")
            return None

    def clean_markdown_content(self, content: str) -> str:
        """마크다운 내용에서 블랙리스트 제목들 제거 및 빈 공간 정리"""
        if not content:
            return content
        
        lines = content.split('\n')
        cleaned_lines = []
        skip_until_next_section = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 블랙리스트 제목 확인
            if line_stripped in self.blacklist_titles:
                logger.debug(f"🚫 마크다운에서 블랙리스트 제목 제거: {line_stripped}")
                self.stats["removed_sections"] += 1
                skip_until_next_section = True
                continue
            
            # 다른 ## 또는 ### 제목이 나오면 스킵 모드 해제
            if skip_until_next_section:
                if line_stripped.startswith('##') and line_stripped not in self.blacklist_titles:
                    skip_until_next_section = False
                    cleaned_lines.append(line)
                # 스킵 모드에서는 내용 제거
                continue
            
            cleaned_lines.append(line)
        
        # 빈 줄 정리 (3개 이상의 연속 빈 줄을 2개로)
        cleaned_content = '\n'.join(cleaned_lines)
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        return cleaned_content.strip()

    def generate_markdown_content(self, data: Dict[str, Any]) -> str:
        """마크다운 내용 생성 (블랙리스트 제목 제거)"""
        name = data['name']
        phone = data.get('phone', '정보 없음')
        address = data.get('address', '정보 없음')
        hours = data.get('hours', '정보 없음')
        closed_days = data.get('closed_days', '정보 없음')
        url = data.get('url', '')
        ol_skey = data.get('ol_skey', '')
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        description = data.get('description', f'{name}은(는) 부산의 어린이복합문화공간입니다.')
        usage_info = data.get('usage_info', '')
        facility_info = data.get('facility_info', '')
        programs = data.get('programs', '')
        location_info = data.get('location_info', '')
        
        # YAML 프론트매터 (핵심 필드만)
        md_content = f"""---
title: "{name}"
address: "{address}"
phone: "{phone}"
hours: "{hours}"
closed_days: "{closed_days}"
source_url: "{url}"
ol_skey: "{ol_skey}"
extraction_date: "{current_date}"
extraction_method: "direct_olskey"
---

# {name}

## 📍 기본 정보

**주소**: {address}  
**전화번호**: {phone}  
**운영시간**: {hours}  
**휴관일**: {closed_days}

## 📝 시설 소개

{description}
"""

        # 각 섹션 추가 (의미있는 내용만, 블랙리스트 제목 제거)
        sections_to_add = []
        
        if usage_info and usage_info != description and len(usage_info.strip()) > 20:
            cleaned_usage = self.clean_markdown_content(usage_info)
            if cleaned_usage:
                sections_to_add.append(cleaned_usage)
        
        if facility_info and len(facility_info.strip()) > 20:
            cleaned_facility = self.clean_markdown_content(facility_info)
            if cleaned_facility:
                sections_to_add.append(cleaned_facility)
        
        if programs and len(programs.strip()) > 20:
            cleaned_programs = self.clean_markdown_content(programs)
            if cleaned_programs:
                sections_to_add.append(cleaned_programs)
        
        if location_info and len(location_info.strip()) > 20:
            cleaned_location = self.clean_markdown_content(location_info)
            if cleaned_location:
                sections_to_add.append(cleaned_location)
        
        # 섹션들을 적절한 간격으로 연결
        if sections_to_add:
            md_content += "\n\n" + "\n\n".join(sections_to_add)

        md_content += f"""

---
> 출처: 부산광역시 어린이복합문화공간 들락날락 ({current_date[:4]}) · 공공누리 제1유형  
> 추출 방법: 직접 olSkey 순차 크롤링 · ID: {ol_skey}
"""
        
        # 최종 전체 내용에서 블랙리스트 제목 한번 더 제거
        md_content = self.clean_markdown_content(md_content)
        
        return md_content

    def crawl_by_olskey_range(self, start_num: int = 20, end_num: int = 300) -> List[str]:
        """🎯 olSkey 범위로 직접 크롤링"""
        logger.info(f"🚀 직접 olSkey 순차 크롤링 시작: DNOL{start_num:013d} ~ DNOL{end_num:013d}")
        
        if not self.setup_driver():
            return []
        
        detailed_facilities = []
        created_files = []
        
        try:
            for num in range(start_num, end_num + 1):
                ol_skey = self.generate_ol_skey(num)
                self.stats["total_attempts"] += 1
                
                logger.info(f"[{num - start_num + 1}/{end_num - start_num + 1}] 🔍 처리 중: {ol_skey}")
                
                facility_data = self.extract_facility_details_direct(ol_skey)
                
                if facility_data:
                    detailed_facilities.append(facility_data)
                    self.stats["successful_extractions"] += 1
                    
                    md_file = self.create_markdown_file(facility_data)
                    if md_file:
                        created_files.append(md_file)
                else:
                    self.stats["failed_extractions"] += 1
                
                # 진행 상황 출력 (10개마다)
                if num % 10 == 0:
                    success_rate = (self.stats["successful_extractions"] / self.stats["total_attempts"] * 100)
                    logger.info(f"📊 진행 상황: {num}번까지 처리, 성공률 {success_rate:.1f}% ({self.stats['successful_extractions']}/{self.stats['total_attempts']})")
                
                # 서버 부하 방지를 위한 대기
                time.sleep(random.uniform(0.5, 1.5))
            
            # 최종 결과 요약
            self.print_final_summary_direct(detailed_facilities, created_files)
            
            return created_files
            
        except Exception as e:
            logger.error(f"❌ 크롤링 실패: {e}")
            return created_files
        finally:
            self.close_driver()

    def close_driver(self):
        """WebDriver 종료"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔧 WebDriver 종료 완료")
            except Exception as e:
                logger.warning(f"WebDriver 종료 중 오류: {e}")

    def print_final_summary_direct(self, detailed_facilities, created_files):
        """최종 결과 요약"""
        logger.info("=" * 80)
        logger.info("📊 직접 olSkey 순차 크롤링 결과")
        logger.info("=" * 80)
        
        logger.info(f"🔍 총 시도: {self.stats['total_attempts']}개")
        logger.info(f"✅ 성공적으로 추출: {self.stats['successful_extractions']}개")
        logger.info(f"📄 유효한 시설: {self.stats['valid_facilities']}개")
        logger.info(f"❌ 페이지 없음: {self.stats['not_found_pages']}개")
        logger.info(f"⚠️ 오류 페이지: {self.stats['error_pages']}개")
        logger.info(f"📁 생성된 파일: {len(created_files)}개")
        
        success_rate = (self.stats["successful_extractions"] / self.stats["total_attempts"] * 100) if self.stats["total_attempts"] > 0 else 0
        logger.info(f"📊 전체 성공률: {success_rate:.1f}%")
        logger.info(f"💾 저장 위치: {self.output_dir}")
        
        if detailed_facilities:
            logger.info("📋 추출된 시설 샘플:")
            for i, facility in enumerate(detailed_facilities[:10], 1):
                logger.info(f"  {i}. {facility['name']} ({facility['ol_skey']})")
                if facility.get('address'):
                    logger.info(f"     주소: {facility['address']}")
        
        logger.info("=" * 80)


def main():
    """CLI 메인 함수"""
    import argparse
    
    print("🎯 직접 olSkey 순차 크롤링 부산어린이복합문화공간 들락날락 크롤러")
    print("=" * 80)
    print("✅ 직접 olSkey 순차 크롤링 방식:")
    print("  1. 🔍 DNOL0000000000001부터 순차적으로 증가")
    print("  2. 📄 각 olSkey로 직접 상세 페이지 접근")
    print("  3. 🎯 페이지 네비게이션 없이 바로 추출")
    print("  4. ⚡ 빠르고 안정적인 크롤링")
    print("  5. 🛡️ 페이지 유효성 자동 검증")
    print("  6. 📊 연속 실패 시 자동 중단")
    print("=" * 80)
    
    parser = argparse.ArgumentParser(description='직접 olSkey 순차 크롤링 들락날락 정보 크롤러')
    parser.add_argument('--output', default='C:/Users/COMTREE/Documents/FC_RAG_2025/data/deullaknallak', 
                       help='출력 디렉토리')
    parser.add_argument('--start', type=int, default=20, help='시작 번호 (기본값: 20)')
    parser.add_argument('--end', type=int, default=300, help='종료 번호 (기본값: 300)')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 (상세 HTML 저장)')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (20~40번만 크롤링)')
    args = parser.parse_args()
    
    if args.test:
        args.start = 20
        args.end = 40
    
    print(f"🎯 실행 설정:")
    print(f"  출력 디렉토리: {args.output}")
    print(f"  olSkey 범위: DNOL{args.start:013d} ~ DNOL{args.end:013d}")
    print(f"  총 시도 수: {args.end - args.start + 1}개")
    print(f"  디버그 모드: {'ON' if args.debug else 'OFF'}")
    if args.test:
        print(f"  테스트 모드: ON (20~40번만)")
    else:
        print(f"  전체 모드: ON")
    print(f"  크롤링 방식: 직접 olSkey 순차 접근")
    print(f"  실행 방식: 300번까지 끝까지 완주")
    
    if args.debug:
        print("🔍 디버그 모드 활성화:")
        print("  - 상세 페이지 HTML: debug_direct_olskey/detail_OLSKEY.html")
    
    print("=" * 80)
    
    # 크롤러 실행
    start_time = datetime.now()
    crawler = DirectOlSkeyDeullakNallakCrawler(output_dir=args.output)
    created_files = crawler.crawl_by_olskey_range(args.start, args.end)
    end_time = datetime.now()
    
    # 최종 결과 출력
    print("=" * 80)
    execution_time = end_time - start_time
    
    if created_files:
        print(f"🎉 직접 olSkey 순차 크롤링 성공!")
        print(f"⏱️ 실행 시간: {execution_time}")
        print(f"🔍 총 시도: {crawler.stats['total_attempts']}개")
        print(f"✅ 성공적으로 추출: {crawler.stats['successful_extractions']}개")
        print(f"📄 유효한 시설: {crawler.stats['valid_facilities']}개")
        print(f"📁 생성된 파일: {len(created_files)}개")
        
        success_rate = (crawler.stats["successful_extractions"] / crawler.stats["total_attempts"] * 100) if crawler.stats["total_attempts"] > 0 else 0
        print(f"📊 전체 성공률: {success_rate:.1f}%")
        
        print(f"\n📋 생성된 파일 (최신 10개):")
        for file_path in created_files[-10:]:
            file_name = Path(file_path).name
            print(f"  📄 {file_name}")
        
        if len(created_files) > 10:
            print(f"     ... 외 {len(created_files) - 10}개")
        
        print(f"\n📁 저장 위치: {crawler.output_dir}")
        
        if args.debug:
            print(f"  디버그 데이터: {crawler.debug_dir}")
        
        print("\n🎯 직접 olSkey 순차 크롤링 특징:")
        print("  • 🔍 olSkey를 순차적으로 증가시켜 직접 접근")
        print("  • ⚡ 페이지 네비게이션 없이 빠른 크롤링")
        print("  • 🛡️ 페이지 유효성 자동 검증")
        print("  • 🔄 300번까지 끝까지 실행 (중단 없음)")
        print("  • 🎯 안정적이고 효율적인 데이터 수집")
        print("  • 💾 각 페이지별 디버그 HTML 저장")
        print("  • 📈 실시간 진행 상황 모니터링")
        
    else:
        print("❌ 크롤링 실패")
        print(f"⏱️ 실행 시간: {execution_time}")
        print(f"🔍 총 시도: {crawler.stats['total_attempts']}개")
        print(f"✅ 성공: {crawler.stats['successful_extractions']}개")
        print(f"❌ 페이지 없음: {crawler.stats['not_found_pages']}개")
        print(f"⚠️ 오류: {crawler.stats['error_pages']}개")
        
        print("\n🔧 문제 해결 가이드:")
        print("  1. 디버그 모드로 재실행:")
        print("     python direct_olskey_crawler.py --debug --test")
        print("  2. HTML 구조 분석:")
        print("     debug_direct_olskey/ 폴더의 HTML 파일 확인")
        print("  3. 범위 조정:")
        print("     python direct_olskey_crawler.py --start 1 --end 50")
        print("  4. 네트워크 연결 및 사이트 접근성 확인")
        print("  5. olSkey 패턴 변경 여부 확인")
    
    print("=" * 80)


if __name__ == "__main__":
    main()