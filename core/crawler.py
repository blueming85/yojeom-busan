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
        options.add_argument('--headless')  # 창 안 띄우고 실행
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
        """보도자료 상세 페이지 링크들을 수집"""
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
                            # 제목과 날짜 함께 수집
                            title_elem = a_tag.select_one(".subject")
                            title = title_elem.get_text(strip=True) if title_elem else "제목없음"
                            
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
    
    def download_pdfs_from_page(self, news_item):
        """특정 보도자료 페이지에서 PDF 다운로드"""
        url = news_item['url']
        title = news_item['title']
        original_date = news_item.get('date')  # 목록에서 가져온 날짜
        
        try:
            logger.info(f'상세페이지 진입: {title}')
            self.driver.get(url)
            time.sleep(1.5)
            
            detail_soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # 상세 페이지에서도 날짜 추출 시도 (더 정확할 수 있음)
            detail_date = self._extract_date_from_detail_page(detail_soup)
            final_date = detail_date if detail_date else original_date
            
            # PDF 첨부파일 링크 찾기
            pdf_links = detail_soup.find_all("a", string=lambda t: bool(t and ".pdf" in t))
            
            if not pdf_links:
                logger.info(f'      - PDF 링크 없음: {title}')
                return []
            
            downloaded_files = []
            
            for pdf_link in pdf_links:
                if not isinstance(pdf_link, Tag):
                    continue
                    
                pdf_href = pdf_link.get('href')
                if not pdf_href:
                    continue
                
                pdf_url = urljoin(self.base_url, str(pdf_href))
                pdf_name = pdf_link.text.strip()
                
                # 파일명 정리 (특수문자 제거)
                safe_filename = self._clean_filename(pdf_name)
                if not safe_filename.endswith('.pdf'):
                    safe_filename += '.pdf'
                
                pdf_path = os.path.join(self.download_dir, safe_filename)
                
                # 이미 존재하는 파일 체크
                if os.path.exists(pdf_path):
                    logger.info(f"      - 이미 존재: {safe_filename}")
                    downloaded_files.append({
                        'filename': safe_filename,
                        'path': pdf_path,
                        'title': title,
                        'date': final_date,  # 날짜 정보 추가
                        'url': url,
                        'status': 'already_exists'
                    })
                    continue
                
                # PDF 다운로드
                try:
                    logger.info(f"      📥 다운로드: {safe_filename}")
                    pdf_response = requests.get(pdf_url, timeout=30)
                    pdf_response.raise_for_status()
                    
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_response.content)
                    
                    downloaded_files.append({
                        'filename': safe_filename,
                        'path': pdf_path,
                        'title': title,
                        'date': final_date,  # 날짜 정보 추가
                        'url': url,
                        'status': 'downloaded',
                        'size': len(pdf_response.content)
                    })
                    
                    logger.info(f"      ✅ 완료: {safe_filename} ({len(pdf_response.content)/1024:.1f}KB)")
                    time.sleep(0.5)  # 서버 부하 방지
                    
                except Exception as e:
                    logger.error(f"      ❌ 다운로드 실패: {safe_filename} - {e}")
                    continue
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"페이지 처리 중 오류: {title} - {e}")
            return []
    
    def _extract_date_from_list_page(self, news_item_tag):
        """보도자료 목록 페이지에서 날짜 추출"""
        try:
            # 여러 가능한 날짜 선택자 시도
            date_selectors = [
                ".date",
                ".reg_date", 
                ".write_date",
                ".board_date"
            ]
            
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
            
            # 날짜를 찾지 못한 경우 현재 날짜 반환
            logger.warning("날짜 정보를 찾을 수 없어 현재 날짜 사용")
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
        
        # 다양한 날짜 패턴 정의
        date_patterns = [
            # 2025-07-04 형식
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', r'\1-\2-\3'),
            # 2025.07.04 형식
            (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', r'\1-\2-\3'),
            # 2025/07/04 형식
            (r'(\d{4})/(\d{1,2})/(\d{1,2})', r'\1-\2-\3'),
            # 2025년 7월 4일 형식
            (r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', r'\1-\2-\3'),
            # 07-04 형식 (년도 없음, 현재 년도 가정)
            (r'(\d{1,2})-(\d{1,2})(?!\d)', f'{datetime.now().year}-\\1-\\2'),
            # 07.04 형식 (년도 없음, 현재 년도 가정)
            (r'(\d{1,2})\.(\d{1,2})(?!\d)', f'{datetime.now().year}-\\1-\\2'),
        ]
        
        for pattern, replacement in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    if len(pattern.split('(')) > 3:  # 년월일이 모두 있는 경우
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                    else:  # 월일만 있는 경우
                        year = datetime.now().year
                        month = int(match.group(1))
                        day = int(match.group(2))
                    
                    # 날짜 유효성 검사
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        date_obj = datetime(year, month, day)
                        return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        return None
    
    def _extract_date_from_detail_page(self, detail_soup) -> Optional[str]:
        """상세 페이지에서 날짜 정보 추출"""
        try:
            # 상세 페이지의 날짜 선택자들
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
            
            # 페이지 전체 텍스트에서 날짜 찾기
            page_text = detail_soup.get_text()
            parsed_date = self._parse_date_string(page_text)
            if parsed_date:
                return parsed_date
            
            return None
            
        except Exception as e:
            logger.warning(f"상세 페이지 날짜 추출 중 오류: {e}")
            return None
    
    def _clean_filename(self, filename: str) -> str:
        """파일명에서 특수문자 제거 (윈도우 호환)"""
        import re
        # 윈도우에서 사용할 수 없는 문자들 제거
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 연속된 공백을 하나로
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def crawl_news(self, max_pages=5):
        """🔧 전체 크롤링 프로세스 실행 (메서드명 변경)"""
        logger.info("부산시청 보도자료 크롤링 시작!")
        
        # 드라이버 설정
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
            
            # 3. 결과 요약
            self._print_summary(all_downloaded)
            return all_downloaded
            
        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {e}")
            return []
        finally:
            self.close()
    
    def _print_summary(self, downloaded_files):
        """크롤링 결과 요약 출력"""
        total = len(downloaded_files)
        new_downloads = len([f for f in downloaded_files if f.get('status') == 'downloaded'])
        existing = len([f for f in downloaded_files if f.get('status') == 'already_exists'])
        
        logger.info("\n" + "="*60)
        logger.info("📊 크롤링 결과 요약")
        logger.info("="*60)
        logger.info(f"총 처리된 파일: {total}개")
        logger.info(f"새로 다운로드: {new_downloads}개")
        logger.info(f"기존 파일: {existing}개")
        logger.info(f"저장 위치: {self.download_dir}")
        logger.info("="*60)
        
        if new_downloads > 0:
            logger.info("🆕 새로 다운로드된 파일들:")
            for f in downloaded_files:
                if f.get('status') == 'downloaded':
                    size_kb = f.get('size', 0) / 1024
                    date_info = f"({f.get('date', 'N/A')})" if f.get('date') else ""
                    logger.info(f"  - {f['filename']} {date_info} ({size_kb:.1f}KB)")
    
    def get_recent_files(self, days=7):
        """최근 N일 내 다운로드된 파일들 반환"""
        if not os.path.exists(self.download_dir):
            return []
        
        recent_files = []
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)
        
        for filename in os.listdir(self.download_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(self.download_dir, filename)
                file_mtime = os.path.getmtime(file_path)
                
                if file_mtime >= cutoff_time:
                    recent_files.append({
                        'filename': filename,
                        'path': file_path,
                        'modified': datetime.fromtimestamp(file_mtime)
                    })
        
        # 수정 시간 기준 내림차순 정렬
        recent_files.sort(key=lambda x: x['modified'], reverse=True)
        return recent_files
    
    def close(self):
        """리소스 정리"""
        if self.driver:
            self.driver.quit()
            logger.info("드라이버 종료 완료")

def main():
    """크롤러 실행 예시"""
    crawler = BusanNewsCrawler()
    
    # 최근 3페이지만 크롤링 (테스트용)
    downloaded_files = crawler.crawl_news(max_pages=3)
    
    # 최근 7일 내 파일들 확인
    recent = crawler.get_recent_files(days=7)
    if recent:
        print(f"\n📅 최근 7일 내 파일 {len(recent)}개:")
        for f in recent[:5]:  # 최대 5개만 표시
            print(f"  - {f['filename']} ({f['modified'].strftime('%Y-%m-%d %H:%M')})")

if __name__ == "__main__":
    main()