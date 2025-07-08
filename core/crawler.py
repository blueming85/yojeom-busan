import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
from datetime import datetime
from typing import Optional
import logging
import re
from difflib import SequenceMatcher

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusanNewsCrawler:
    def __init__(self, download_dir="./data/pdfs"):
        self.base_list_url = "https://www.busan.go.kr/nbtnewsBU?curPage={}"
        self.base_url = "https://www.busan.go.kr"
        self.download_dir = download_dir
        self.driver = None
        
        # 다운로드 디렉토리 생성
        os.makedirs(self.download_dir, exist_ok=True)
        
    def setup_driver(self):
        """Selenium 드라이버 설정"""
        logger.info("Selenium 드라이버 준비 중...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), 
                options=options
            )
            logger.info("드라이버 준비 완료")
            return True
        except Exception as e:
            logger.error(f"드라이버 설정 실패: {e}")
            return False
    
    def get_news_links(self, max_pages=5):
        """🔧 보도자료 상세 페이지 링크들을 수집 (제목 추출 개선)"""
        if not self.driver:
            logger.error("드라이버가 설정되지 않았습니다.")
            return []
        
        all_links = []
        
        for page in range(1, max_pages + 1):
            logger.info(f'페이지 {page} 요청 중...')
            try:
                self.driver.get(self.base_list_url.format(page))
                time.sleep(2)
                
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                news_links = soup.select("a.item")
                
                page_links = []
                for a_tag in news_links:
                    if isinstance(a_tag, Tag):
                        detail_href = a_tag.get("href")
                        if detail_href:
                            detail_url = urljoin(self.base_url, str(detail_href))
                            
                            # 🔧 제목 추출 개선 - 여러 선택자 시도
                            title = self._extract_title_from_list_item(a_tag)
                            
                            # 날짜 정보 추출
                            date = self._extract_date_from_list_page(a_tag)
                            
                            page_links.append({
                                'url': detail_url,
                                'title': title,
                                'date': date,
                                'page': page
                            })
                
                logger.info(f'  - 페이지 {page}에서 {len(page_links)}개 링크 발견')
                all_links.extend(page_links)
                
            except Exception as e:
                logger.error(f"페이지 {page} 처리 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(all_links)}개의 보도자료 링크 수집 완료")
        return all_links
    
    def _extract_title_from_list_item(self, a_tag: Tag) -> str:
        """🔧 목록에서 제목 추출 (여러 선택자 시도)"""
        try:
            # 1순위: .subject 클래스
            title_elem = a_tag.select_one(".subject")
            if title_elem and title_elem.get_text(strip=True):
                title = title_elem.get_text(strip=True)
                logger.debug(f"제목 추출 성공 (.subject): {title[:50]}...")
                return title
            
            # 2순위: .title 클래스
            title_elem = a_tag.select_one(".title")
            if title_elem and title_elem.get_text(strip=True):
                title = title_elem.get_text(strip=True)
                logger.debug(f"제목 추출 성공 (.title): {title[:50]}...")
                return title
            
            # 3순위: h3, h4 태그
            for tag in ['h3', 'h4', 'h2']:
                title_elem = a_tag.select_one(tag)
                if title_elem and title_elem.get_text(strip=True):
                    title = title_elem.get_text(strip=True)
                    logger.debug(f"제목 추출 성공 ({tag}): {title[:50]}...")
                    return title
            
            # 4순위: strong 태그
            title_elem = a_tag.select_one("strong")
            if title_elem and title_elem.get_text(strip=True):
                title = title_elem.get_text(strip=True)
                logger.debug(f"제목 추출 성공 (strong): {title[:50]}...")
                return title
            
            # 5순위: a 태그 직접 텍스트에서 추출
            all_text = a_tag.get_text(strip=True)
            if all_text and len(all_text) > 10:
                # 첫 번째 줄만 제목으로 사용
                first_line = all_text.split('\n')[0].strip()
                if len(first_line) > 10:
                    title = first_line[:100]  # 너무 길면 자르기
                    logger.debug(f"제목 추출 성공 (전체 텍스트): {title[:50]}...")
                    return title
            
            logger.warning("제목 추출 실패 - 모든 선택자에서 빈 값")
            return "제목 없음"
            
        except Exception as e:
            logger.error(f"제목 추출 중 오류: {e}")
            return "제목 없음"
    
    def download_pdfs_from_page(self, news_item):
        """🔧 특정 보도자료 페이지에서 PDF 다운로드 (URL 매핑 개선)"""
        url = news_item['url']
        list_title = news_item['title']  # 목록에서 가져온 제목
        original_date = news_item.get('date')
        
        try:
            logger.info(f'상세페이지 진입: {list_title[:50]}...')
            self.driver.get(url)
            time.sleep(1.5)
            
            detail_soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # 🔧 상세 페이지에서 더 정확한 제목 추출
            detail_title = self._extract_title_from_detail_page(detail_soup)
            final_title = detail_title if detail_title and detail_title != "제목 없음" else list_title
            
            # 상세 페이지에서도 날짜 추출 시도
            detail_date = self._extract_date_from_detail_page(detail_soup)
            final_date = detail_date if detail_date else original_date
            
            # PDF 첨부파일 링크 찾기
            pdf_links = detail_soup.find_all("a", string=lambda t: bool(t and ".pdf" in t))
            
            if not pdf_links:
                logger.info(f'      - PDF 링크 없음: {final_title[:50]}...')
                return []
            
            # 기존 파일 목록 가져오기
            existing_files = [f for f in os.listdir(self.download_dir) if f.endswith('.pdf')]
            
            downloaded_files = []
            
            for pdf_link in pdf_links:
                if not isinstance(pdf_link, Tag):
                    continue
                    
                pdf_href = pdf_link.get('href')
                if not pdf_href:
                    continue
                
                pdf_url = urljoin(self.base_url, str(pdf_href))
                pdf_name = pdf_link.text.strip()
                
                # 파일명 정리
                safe_filename = self._clean_filename(pdf_name)
                if not safe_filename.endswith('.pdf'):
                    safe_filename += '.pdf'
                
                pdf_path = os.path.join(self.download_dir, safe_filename)
                
                # 중복 체크
                if os.path.exists(pdf_path):
                    logger.info(f"      - 이미 존재 (정확 매칭): {safe_filename}")
                    downloaded_files.append({
                        'filename': safe_filename,
                        'path': pdf_path,
                        'title': final_title,
                        'date': final_date,
                        'url': url,  # 🔧 상세 페이지 URL
                        'status': 'already_exists'
                    })
                    continue
                
                # 유사한 파일명 체크
                similar_file = self._is_similar_pdf(safe_filename, existing_files)
                if similar_file:
                    similar_path = os.path.join(self.download_dir, similar_file)
                    logger.info(f"      - 이미 존재 (유사 매칭): {safe_filename} ≈ {similar_file}")
                    downloaded_files.append({
                        'filename': similar_file,
                        'path': similar_path,
                        'title': final_title,
                        'date': final_date,
                        'url': url,  # 🔧 상세 페이지 URL
                        'status': 'already_exists_similar'
                    })
                    continue
                
                # 새 파일 다운로드
                try:
                    logger.info(f"      📥 다운로드: {safe_filename}")
                    pdf_response = requests.get(pdf_url, timeout=30)
                    pdf_response.raise_for_status()
                    
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_response.content)
                    
                    existing_files.append(safe_filename)
                    
                    downloaded_files.append({
                        'filename': safe_filename,  # 🔧 실제 저장된 파일명
                        'path': pdf_path,
                        'title': final_title,
                        'date': final_date,
                        'url': url,  # 🔧 상세 페이지 URL (중요!)
                        'status': 'downloaded',
                        'size': len(pdf_response.content)
                    })
                    
                    logger.info(f"      ✅ 완료: {safe_filename} ({len(pdf_response.content)/1024:.1f}KB)")
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"      ❌ 다운로드 실패: {safe_filename} - {e}")
                    continue
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"페이지 처리 중 오류: {final_title[:50]}... - {e}")
            return []
    
    def _extract_title_from_detail_page(self, detail_soup) -> str:
        """🔧 상세 페이지에서 제목 추출"""
        try:
            # 상세 페이지의 제목 선택자들
            title_selectors = [
                ".view_title",
                ".board_view h1",
                ".news_title",
                ".article_title h1",
                "h1.title",
                ".content_title",
                "h1",
                ".subject"
            ]
            
            for selector in title_selectors:
                title_elem = detail_soup.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    title = title_elem.get_text(strip=True)
                    if len(title) > 5:  # 너무 짧은 제목 제외
                        logger.debug(f"상세 페이지 제목 추출: {title[:50]}...")
                        return title
            
            return "제목 없음"
            
        except Exception as e:
            logger.warning(f"상세 페이지 제목 추출 중 오류: {e}")
            return "제목 없음"
    
    def _is_similar_pdf(self, new_filename: str, existing_files: list) -> Optional[str]:
        """PDF 파일 중복 체크 (간소화)"""
        try:
            if not existing_files:
                return None
            
            new_normalized = self._normalize_filename(new_filename)
            
            for existing_file in existing_files:
                if not existing_file.endswith('.pdf'):
                    continue
                
                existing_normalized = self._normalize_filename(existing_file)
                similarity = SequenceMatcher(None, new_normalized, existing_normalized).ratio()
                
                if similarity >= 0.85:
                    return existing_file
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 유사 파일 체크 실패: {e}")
            return None
    
    def _normalize_filename(self, filename: str) -> str:
        """파일명 정규화"""
        try:
            normalized = filename.lower()
            normalized = re.sub(r'[㈜().,\s_\-\[\]{}【】「」『』""''・]', '', normalized)
            normalized = re.sub(r'[^\w가-힣]', '', normalized)
            normalized = normalized.replace('.pdf', '')
            return normalized
        except Exception as e:
            logger.debug(f"파일명 정규화 실패: {filename} - {e}")
            return filename.lower()
    
    def _extract_date_from_list_page(self, news_item_tag):
        """보도자료 목록 페이지에서 날짜 추출"""
        try:
            date_selectors = [".date", ".reg_date", ".write_date", ".board_date"]
            
            for selector in date_selectors:
                date_elem = news_item_tag.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    parsed_date = self._parse_date_string(date_text)
                    if parsed_date:
                        return parsed_date
            
            # 선택자로 찾지 못한 경우, 텍스트에서 날짜 패턴 찾기
            all_text = news_item_tag.get_text()
            parsed_date = self._parse_date_string(all_text)
            if parsed_date:
                return parsed_date
            
            return datetime.now().strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.warning(f"날짜 추출 중 오류: {e}")
            return datetime.now().strftime("%Y-%m-%d")
    
    def _parse_date_string(self, date_text: str) -> Optional[str]:
        """다양한 날짜 형식을 YYYY-MM-DD로 변환"""
        if not date_text:
            return None
        
        import re
        from datetime import datetime
        
        date_patterns = [
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', r'\1-\2-\3'),
            (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', r'\1-\2-\3'),
            (r'(\d{4})/(\d{1,2})/(\d{1,2})', r'\1-\2-\3'),
            (r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', r'\1-\2-\3'),
            (r'(\d{1,2})-(\d{1,2})(?!\d)', f'{datetime.now().year}-\\1-\\2'),
            (r'(\d{1,2})\.(\d{1,2})(?!\d)', f'{datetime.now().year}-\\1-\\2'),
        ]
        
        for pattern, replacement in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    if len(pattern.split('(')) > 3:
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                    else:
                        year = datetime.now().year
                        month = int(match.group(1))
                        day = int(match.group(2))
                    
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        date_obj = datetime(year, month, day)
                        return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        return None
    
    def _extract_date_from_detail_page(self, detail_soup) -> Optional[str]:
        """상세 페이지에서 날짜 정보 추출"""
        try:
            date_selectors = [
                ".view_info .date",
                ".board_view .date", 
                ".news_info .date",
                ".article_info .date",
                "td:contains('작성일')",
                "td:contains('등록일')",
                ".reg_date",
                ".write_date"
            ]
            
            for selector in date_selectors:
                date_elem = detail_soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    parsed_date = self._parse_date_string(date_text)
                    if parsed_date:
                        return parsed_date
            
            page_text = detail_soup.get_text()
            parsed_date = self._parse_date_string(page_text)
            if parsed_date:
                return parsed_date
            
            return None
            
        except Exception as e:
            logger.warning(f"상세 페이지 날짜 추출 중 오류: {e}")
            return None
    
    def _clean_filename(self, filename: str) -> str:
        """파일명에서 특수문자 제거"""
        import re
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def crawl_news(self, max_pages=5):
        """🔧 전체 크롤링 프로세스 실행 (URL 매핑 개선)"""
        logger.info("부산시청 보도자료 크롤링 시작!")
        
        if not self.setup_driver():
            logger.error("크롤링을 시작할 수 없습니다.")
            return []
        
        try:
            # 1. 보도자료 링크 수집
            news_links = self.get_news_links(max_pages)
            if not news_links:
                logger.warning("수집된 보도자료 링크가 없습니다.")
                return []
            
            # 2. 각 페이지에서 PDF 다운로드
            all_downloaded = []
            total_links = len(news_links)
            
            for idx, news_item in enumerate(news_links, 1):
                logger.info(f"[{idx}/{total_links}] 처리 중: {news_item['title'][:50]}...")
                downloaded_files = self.download_pdfs_from_page(news_item)
                all_downloaded.extend(downloaded_files)
            
            # 3. 🔧 URL 매핑 검증 로그
            self._print_url_mapping_summary(all_downloaded)
            
            return all_downloaded
            
        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {e}")
            return []
        finally:
            self.close()
    
    def _print_url_mapping_summary(self, downloaded_files):
        """🔧 URL 매핑 요약 출력"""
        total = len(downloaded_files)
        new_downloads = len([f for f in downloaded_files if f.get('status') == 'downloaded'])
        existing = total - new_downloads
        
        logger.info("\n" + "="*60)
        logger.info("📊 크롤링 결과 요약")
        logger.info("="*60)
        logger.info(f"총 처리된 파일: {total}개")
        logger.info(f"새로 다운로드: {new_downloads}개")
        logger.info(f"기존 파일: {existing}개")
        logger.info(f"저장 위치: {self.download_dir}")
        
        # 🔧 URL 매핑 샘플 출력
        logger.info("\n🔗 URL 매핑 샘플:")
        for i, f in enumerate(downloaded_files[:3]):
            logger.info(f"  {i+1}. 파일: {f['filename']}")
            logger.info(f"     URL: {f['url']}")
            logger.info(f"     제목: {f['title'][:50]}...")
        
        if len(downloaded_files) > 3:
            logger.info(f"  ... 외 {len(downloaded_files) - 3}개")
        
        logger.info("="*60)
    
    def close(self):
        """리소스 정리"""
        if self.driver:
            self.driver.quit()
            logger.info("드라이버 종료 완료")

def main():
    """크롤러 실행 예시"""
    crawler = BusanNewsCrawler()
    downloaded_files = crawler.crawl_news(max_pages=2)
    
    print(f"\n🎯 크롤링 결과: {len(downloaded_files)}개 파일")

if __name__ == "__main__":
    main()