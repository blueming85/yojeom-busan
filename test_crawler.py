# test_crawler.py - HTML 구조 분석용 테스트 크롤러
import requests
from bs4 import BeautifulSoup
import browser_cookie3
import re

# Edge 쿠키 로드
try:
    cj = browser_cookie3.edge(domain_name="99.1.2.134")
    print("✅ Edge 쿠키 로드 성공")
except Exception as e:
    print(f"⚠️ Edge 쿠키 로드 실패: {e}")
    cj = None

# 세션 설정
session = requests.Session()
if cj:
    session.cookies = cj
else:
    session.cookies.set("JSESSIONID", "UCxsitzvdUu9Jmqh4P47vBwkvfx3pN9byJ-Z2xsp.onnara41")

session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko,en;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Referer': 'http://99.1.2.134/bms/dctlist/oreport_list_receive.do'
})

# 요청 파라미터
payload = {
    "pagenum": "1",
    "searchkey": "detail",
    "searchtext": "",
    "reportsday": "20250809",
    "reporteday": "20250908", 
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

print("HTTP 요청 시작...")
response = session.post("http://99.1.2.134/bms/dctlist/ctrldeptviewsource.do", data=payload)
response.encoding = "utf-8"

print(f"HTTP 상태: {response.status_code}")
print(f"응답 길이: {len(response.text)}")

# HTML 파일로 저장
with open('debug_response.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print("HTML 저장: debug_response.html")

# BeautifulSoup으로 파싱
soup = BeautifulSoup(response.text, 'html.parser')

# 테이블 찾기
table = soup.find('table', {'id': 'dctList'})
if not table:
    print("❌ dctList 테이블 없음")
    exit()

print("✅ dctList 테이블 발견")

# 모든 행 분석
rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
print(f"테이블 행 개수: {len(rows)}")

for i, row in enumerate(rows):
    print(f"\n=== 행 {i+1} ===")
    
    # 모든 셀 내용
    cells = row.find_all('td')
    print(f"셀 개수: {len(cells)}")
    for j, cell in enumerate(cells):
        content = cell.get_text(strip=True)[:50]
        print(f"  셀 {j+1}: '{content}'")
    
    # 모든 <a> 태그 찾기
    links = row.find_all('a')
    print(f"<a> 태그 개수: {len(links)}")
    
    for j, link in enumerate(links):
        onclick = link.get('onclick', '')
        href = link.get('href', '')
        text = link.get_text(strip=True)[:30]
        link_id = link.get('id', '')
        
        print(f"  <a> {j+1}:")
        print(f"    id: '{link_id}'")
        print(f"    onclick: '{onclick}'")
        print(f"    href: '{href}'")
        print(f"    text: '{text}'")
        
        # viewDoc 함수 찾기
        if 'viewDoc' in onclick:
            print(f"    🎯 viewDoc 발견!")
            matches = re.findall(r"'([^']+)'", onclick)
            print(f"    파라미터: {matches}")
    
    # input 태그 찾기
    inputs = row.find_all('input')
    print(f"<input> 태그 개수: {len(inputs)}")
    for j, inp in enumerate(inputs):
        name = inp.get('name', '')
        value = inp.get('value', '')
        inp_type = inp.get('type', '')
        print(f"  <input> {j+1}: name='{name}', value='{value}', type='{inp_type}'")

print("\n분석 완료. debug_response.html 파일을 확인하세요.")