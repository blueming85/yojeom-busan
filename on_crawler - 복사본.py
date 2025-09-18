# crawler.py - 철도시설과 생산문서 전용 크롤러 (최종 수정본)
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import random
import re
from datetime import datetime, timedelta
import os
import browser_cookie3
import sys
import fitz
from urllib.parse import quote # URL 인코딩을 위해 import

class RailwayProductionDocCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://99.1.2.134"
        self.list_url = f"{self.base_url}/bms/dctlist/ctrldeptviewsource.do"
        
        try:
            cj = browser_cookie3.edge(domain_name="99.1.2.134")
            self.session.cookies = cj
            print("✅ Edge 브라우저에서 쿠키 자동 로드 성공")
        except Exception as e:
            print(f"⚠️ Edge 쿠키 로드 실패: {e}")
            self.session.cookies.set("JSESSIONID", "UCxsitzvdUu9Jmqh4P47vBwkvfx3pN9byJ-Z2xsp.onnara41")
            print("➡️ 수동 JSESSIONID를 사용합니다.")
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'http://99.1.2.134/bms/dctlist/oreport_list_receive.do'
        })
        
        os.makedirs('data/details', exist_ok=True)
        
        print("철도시설과 생산문서 크롤러 초기화 완료")
    
    def get_date_range(self, months_back=1):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")
    
    def fetch_documents_page(self, page_num=1, months_back=1):
        start_date, end_date = self.get_date_range(months_back)
        payload = {
            "pagenum": str(page_num),
            "searchkey": "detail",
            "searchtext": "",
            "reportsday": start_date,
            "reporteday": end_date,
            "filter": "ALL",
            "rcvflagfilter": "A",
            "desctitle": "",
            "desckeyword": "",
            "descdocno": "",
            "descobjname": "",
            "descasktype": "ALL",
            "descstate": "",
            "descopen": "ALL",
            "descopenbasis": "",
            "deptid": "6261962",
            "deptname": "철도시설과",
            "taskId": "",
            "taskNm": ""
        }
        
        try:
            print(f"페이지 {page_num} 요청 중... ({start_date} ~ {end_date})")
            response = self.session.post(self.list_url, data=payload)
            response.encoding = "utf-8"
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"페이지 {page_num} 요청 실패: {e}")
            return None
    
    def parse_document_list(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', {'id': 'dctList'})
        if not table:
            print("❌ 문서 목록 테이블(id='dctList')을 찾을 수 없습니다.")
            return []
        
        print("✅ dctList 테이블 발견")
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
        print(f"테이블 행 개수: {len(rows)}")
        documents = []
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 9:
                    continue

                doc_info = self.extract_document_info(row)
                if not doc_info:
                    print(f"행 {i+1}: 문서 ID 추출 실패. 건너뜁니다.")
                    continue
                
                doc_data = {
                    'doc_id': doc_info['id'],
                    'doc_type': doc_info['type'],
                    'rcv_flag': doc_info['rcv_flag'],
                    'from_list': doc_info['from_list'],
                    'sequence': cells[1].get_text(strip=True),
                    'title': cells[3].get_text(strip=True),
                    'report_date': cells[2].get_text(strip=True),
                    'sender': cells[4].get_text(strip=True),
                    'reporter': cells[5].get_text(strip=True),
                    'reviewer': cells[6].get_text(strip=True),
                    'department': '철도시설과',
                    'status': cells[8].get_text(strip=True)
                }
                
                documents.append(doc_data)
                print(f"파싱: {doc_data['sequence']} - {doc_data['title'][:50]}...")
            except Exception as e:
                print(f"행 파싱 오류: {e}")
                continue
        
        return documents
    
    def extract_document_info(self, row):
        doc_input = row.find('input', {'name': 'chkDocId'})
        if doc_input:
            doc_id = doc_input.get('value')
            doc_type = 'P' if doc_id.startswith('DCT') else 'R'
            rcv_flag = 'N' 
            from_list = 'Y'
            return {'id': doc_id, 'type': doc_type, 'rcv_flag': rcv_flag, 'from_list': from_list}
        print(f" ❌ input 태그에서 문서 ID를 찾을 수 없음")
        return None
    
    def get_document_detail(self, doc_id, doc_type='R', rcv_flag='N', from_list='Y'):
        """개별 문서의 상세 정보 가져오기 (PDF URL 추출 로직 추가)"""
        try:
            if doc_type == 'P':
                detail_url = f"{self.base_url}/bms/dct/viewreport.do"
                payload = {"docid": doc_id, "fromlistok": from_list, "reqRcvFlag": rcv_flag}
                response = self.session.post(detail_url, data=payload)
            else:
                detail_url = f"{self.base_url}/bms/dctenf/BmsDctEnfReceiptCardDetail.do?enfdocid={doc_id}"
                response = self.session.get(detail_url)
            
            response.encoding = "utf-8"
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 💡 개선된 PDF URL 추출 로직
            pdf_info_input = soup.find('input', {'id': f'newmainpdfinfo~100'})
            if pdf_info_input and pdf_info_input.get('value'):
                pdf_info = pdf_info_input.get('value').split('*')
                
                # 💡 리스트 길이를 체크하여 파싱 오류 방지 (최소 4개 항목: title*filename*size*hash)
                if len(pdf_info) >= 4:
                    doc_title = pdf_info[0].strip()
                    pdf_filename = pdf_info[1].strip()
                    
                    # 💡 URL 파라미터에 docTitle과 transFlag=N 추가 및 인코딩
                    encoded_doc_title = quote(doc_title, encoding='utf-8')
                    pdf_url = f"{self.base_url}/bms/dctenf/Document.pdf?sFileName={pdf_filename}&docTitle={encoded_doc_title}&transFlag=N"
                    
                    print(f"✅ PDF URL 찾음: {pdf_url}")
                    
                    # PDF 파일 다운로드 및 텍스트 추출
                    pdf_response = self.session.get(pdf_url)
                    pdf_response.raise_for_status()
                    content_text = self.extract_text_from_pdf_stream(pdf_response.content)

                    # 메타데이터 구성
                    metadata = {'title': doc_title, 'content_text': content_text}
                    
                    return {
                        'doc_id': doc_id,
                        'doc_type': doc_type,
                        'title': doc_title,
                        'content_text': content_text,
                        'files': [],
                        'raw_data': {},
                        'metadata': metadata
                    }
            
            # 💡 PDF URL을 찾지 못했거나 HTML 문서인 경우 (기존 로직)
            print("❌ PDF URL을 찾을 수 없습니다. HTML 파싱 시도...")
            detail_data = self.extract_json_data(soup)
            metadata = self.extract_metadata(soup)
            
            return {
                'doc_id': doc_id,
                'doc_type': doc_type,
                'title': metadata.get('title', ''),
                'content_text': metadata.get('content_text', ''),
                'files': detail_data.get('files', []),
                'raw_data': detail_data,
                'metadata': metadata
            }
            
        except Exception as e:
            print(f"문서 {doc_id} 상세 정보 가져오기 실패: {e}")
            return None

    def extract_text_from_pdf_stream(self, pdf_stream):
        """PDF 스트림에서 텍스트를 추출하는 함수"""
        try:
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            print(f"✅ PDF 텍스트 추출 완료. 길이: {len(text)}")
            return text
        except Exception as e:
            print(f"❌ PDF 텍스트 추출 실패: {e}")
            return "PDF 텍스트를 추출할 수 없습니다."
    
    def extract_json_data(self, soup):
        for script in soup.find_all('script'):
            script_text = script.string or ""
            if 'bmsDctSingleViewModel' not in script_text:
                continue
            patterns = [
                r'bmsDctSingleViewModel\s*=\s*eval\s*\(\s*(\{.*?\})\s*\)\s*;',
                r'var\s+bmsDctSingleViewModel\s*=\s*(\{.*?\})\s*;',
                r'bmsDctSingleViewModel\s*=\s*(\{.*?\})\s*;',
                r'(?:let|const)\s+bmsDctSingleViewModel\s*=\s*(\{.*?\})\s*;'
            ]
            for i, pattern in enumerate(patterns):
                json_match = re.search(pattern, script_text, re.DOTALL)
                if json_match:
                    try:
                        raw_json = json_match.group(1).replace("'", '"')
                        data = json.loads(raw_json)
                        print(f"JSON 파싱 성공 (패턴 {i+1})")
                        return self.process_document_data(data)
                    except json.JSONDecodeError as e:
                        print(f"JSON 파싱 실패 (패턴 {i+1}): {e}")
                        continue
        return {'files': [], 'raw': {}}
    
    def process_document_data(self, data):
        files = []
        if 'bmsDctCommFileList' in data:
            for file_info in data['bmsDctCommFileList']:
                files.append({
                    'filename': file_info.get('filetitle', ''),
                    'fileid': file_info.get('fileid', ''),
                    'filetype': file_info.get('filegubun', ''),
                    'size': file_info.get('filesize', 0)
                })
        return {'files': files, 'raw': data}
    
    def extract_metadata(self, soup):
        metadata = {}
        title_input = soup.find('input', {'name': 'doctitle'})
        if title_input:
            metadata['title'] = title_input.get('value', '')
        
        content_text = ""
        priority_selectors = ['div.doc-content-body', 'div.report-body', 'div#documentContent', 'div.document-main', 'div#DIV_ENF_DOC', 'div.content-area', 'div#contentDiv', 'article']
        
        main_content_container = None
        for selector in priority_selectors:
            main_content_container = soup.select_one(selector)
            if main_content_container:
                break
        
        if main_content_container:
            for unwanted in main_content_container(['script', 'style', 'nav', 'header', 'footer']):
                unwanted.decompose()
            content_text = main_content_container.get_text(" ", strip=True)

        if not content_text or len(content_text) < 100:
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            text_blocks = [element.get_text(" ", strip=True) for element in soup.find_all(['div', 'p', 'td'], string=False) if len(element.get_text(" ", strip=True)) > 50 and '클릭' not in element.get_text(" ", strip=True) and 'javascript' not in element.get_text(" ", strip=True)]
            content_text = " ".join(text_blocks)
        
        metadata['content_text'] = content_text[:1000] if content_text else ""
        return metadata
    
    def crawl_all_documents(self, months_back=1, max_pages=50, test_limit=None):
        print(f"=== 철도시설과 생산문서 크롤링 시작 (최근 {months_back}개월) ===")
        all_documents = []
        
        for page in range(1, max_pages + 1):
            html = self.fetch_documents_page(page, months_back)
            if not html:
                break
            documents = self.parse_document_list(html)
            if not documents:
                print(f"페이지 {page}: 문서 없음. 크롤링 종료.")
                break
            all_documents.extend(documents)
            print(f"페이지 {page}: {len(documents)}개 문서 수집")
            delay = random.uniform(1.5, 3.5)
            print(f"다음 페이지까지 {delay:.1f}초 대기...")
            time.sleep(delay)
        
        if not all_documents:
            print("수집된 문서가 없습니다.")
            return
        
        print(f"\n총 {len(all_documents)}개 문서 목록 수집 완료")
        
        production_documents = [doc for doc in all_documents if doc.get('doc_type') == 'P']
        print(f"✅ 생산문서 {len(production_documents)}개 필터링 완료")

        self.save_documents_csv(production_documents)
        
        if test_limit:
            print(f"\n💡 테스트를 위해 상위 {test_limit}개 문서만 처리합니다.")
            production_documents = production_documents[:test_limit]
        
        print(f"\n상세 정보 수집 시작...")
        success_count = 0
        
        for i, doc in enumerate(production_documents):
            print(f"[{i+1}/{len(production_documents)}] {doc['title'][:50]}...")
            
            detail = self.get_document_detail(doc['doc_id'], doc.get('doc_type', 'R'), doc.get('rcv_flag', 'N'), doc.get('from_list', 'Y'))
            if detail:
                self.save_detail_markdown(detail, i)
                success_count += 1
            
            delay = random.uniform(2, 4)
            print(f"상세 정보 수집 간격: {delay:.1f}초 대기...")
            time.sleep(delay)
        
        print(f"\n=== 크롤링 완료 ===")
        print(f"문서 목록: {len(production_documents)}개")
        print(f"상세 정보: {success_count}개")
    
    def save_documents_csv(self, documents):
        df = pd.DataFrame(documents)
        filename = 'data/railway_production_docs.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"CSV 저장: {filename}")
    
    def save_detail_markdown(self, detail, index=0):
        """문서 상세 정보를 마크다운 파일로 저장"""
        title = detail.get('title', 'untitled')[:30]
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        
        date_str = ""
        if 'metadata' in detail and 'content_text' in detail['metadata']:
            date_match = re.search(r'20\d{2}[.-]\d{1,2}[.-]\d{1,2}', detail['metadata']['content_text'])
            if date_match:
                date_str = date_match.group().replace('.', '-')[:10]
        
        md_content = f"# {detail.get('title', '제목 없음')}\n\n"
        md_content += f"**문서 ID**: {detail.get('doc_id', 'ID 없음')}\n"
        md_content += f"**문서 타입**: {'생산문서' if detail.get('doc_type') == 'P' else '접수문서'}\n"
        md_content += f"**날짜**: {detail.get('report_date', '날짜 정보 없음')}\n\n"
        
        md_content += "---\n\n"
        md_content += f"{detail.get('content_text', '본문 내용 없음')}\n"
        
        if date_str:
            filename = f"data/details/{date_str}_{safe_title}_{detail['doc_id'][:8]}_{index:03d}.md"
        else:
            filename = f"data/details/{safe_title}_{detail['doc_id'][:8]}_{index:03d}.md"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"마크다운 저장: {filename}")

# 실행 스크립트
if __name__ == "__main__":
    crawler = RailwayProductionDocCrawler()
    
    print("=== 철도시설과 생산문서 크롤러 실행 ===")
    print("🌐 Edge 브라우저에서 쿠키를 자동으로 가져옵니다.")
    print("⚠️ 만약 쿠키 로드가 실패하면 수동 JSESSIONID로 전환됩니다.")
    print("💡 Edge에서 온나라시스템에 로그인되어 있는지 확인하세요.")

    test_limit = 10 if '-test' in sys.argv else None
    
    try:
        crawler.crawl_all_documents(months_back=1, test_limit=test_limit)
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n크롤링 중 오류 발생: {e}")
    
    print("\n크롤링 완료. 결과 파일:")
    print("- data/railway_production_docs.csv (생산문서 목록)")
    print("- data/details/*.md (각 생산문서 상세 정보)")