"""
부산시청 정보포털 - Streamlit 앱 (보도자료 + 업무계획)
=====================================================
태그 색상 기반 카드형 UI로 보도자료와 업무계획을 쉽게 검색하고 확인할 수 있는 통합 포털

실행 방법:
    streamlit run app.py
"""

import streamlit as st
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import streamlit.components.v1 as components
import time
from streamlit_scroll_to_top import scroll_to_here

# 프로젝트 모듈 import
from config import (
    MD_DIR, AVAILABLE_TAGS, TAG_COLORS,
    PLANS_MD_DIR, PLAN_DEPARTMENTS, AVAILABLE_PLAN_TAGS, PLAN_TAG_COLORS,
    IS_LOCAL, get_env_info, MESSAGES
)
from plans_portal import BusanPlansPortal

# 페이지 설정
st.set_page_config(
    page_title="요즘 부산",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔧 정교한 CSS - Deploy 버튼과 메뉴 숨기고 사이드바 토글은 보존
st.markdown("""
<style>
/* 🔧 Deploy 버튼과 세 줄 메뉴 강력하게 숨기기 */
[data-testid="stToolbar"],
[data-testid="stHeader"],
header[data-testid="stHeader"],
.stDeployButton,
button[title*="Deploy"],
button[aria-label*="Deploy"],
a[href*="deploy"],
button[kind="header"],
iframe[title="streamlit_app"],
div[data-testid="stToolbar"],
section[data-testid="stToolbar"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
    left: -9999px !important;
}

/* 🔧 상단 공간 제거 */
.stApp > header {
    display: none !important;
}

/* 🔧 모든 Deploy 관련 텍스트까지 숨기기 */
*[class*="deploy" i],
*[id*="deploy" i],
*[data-testid*="deploy" i] {
    display: none !important;
}

/* 🔧 사이드바 토글 버튼은 명시적으로 보이도록 강제 */
[data-testid="collapsedControl"],
button[data-testid="collapsedControl"],
div[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    position: fixed !important;
    top: 0.75rem !important;
    left: 0.75rem !important;
    z-index: 999999 !important;
    background: #ffffff !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 8px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    width: 40px !important;
    height: 40px !important;
    align-items: center !important;
    justify-content: center !important;
}

/* 🔧 사이드바 토글 버튼 호버 효과 */
[data-testid="collapsedControl"]:hover,
button[data-testid="collapsedControl"]:hover {
    background: #f7fafc !important;
    border-color: #cbd5e0 !important;
    box-shadow: 0 6px 16px rgba(0,0,0,0.2) !important;
}

/* 🔧 사이드바 토글 버튼 아이콘 스타일 */
[data-testid="collapsedControl"] svg,
button[data-testid="collapsedControl"] svg {
    color: #4a5568 !important;
    width: 18px !important;
    height: 18px !important;
}

/* 🔧 다른 가능한 토글 버튼 선택자들도 활성화 */
button[aria-label*="Open"],
button[title*="Open"],
button[aria-label*="sidebar"],
button[title*="sidebar"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}

/* 🔧 모든 호버 효과 완전 제거 */
*, *:hover {
    transition: none !important;
}

/* 🔧 모든 버튼 기본 스타일 (흰색 바탕 + 보라 테두리로 통일) */
button, 
.stButton button,
div.stButton > button,
[data-testid="baseButton-primary"],
[data-testid="baseButton-secondary"],
a[data-testid="stLinkButton"],
.stLinkButton > a {
    height: auto !important;
    padding: 20px 18px !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    background: #fff !important;
    background-color: #fff !important;
    color: #4A148C !important;
    border: 2px solid #4A148C !important;
    border-radius: 15px !important;
    outline: none !important;
    box-shadow: none !important;
    text-decoration: none !important;
    display: block !important;
    text-align: center !important;
}

/* 🔧 호버시 찐보라색 배경 */
button:hover, button:focus,
.stButton button:hover, .stButton button:focus,
div.stButton > button:hover, div.stButton > button:focus,
[data-testid="baseButton-primary"]:hover, [data-testid="baseButton-primary"]:focus,
[data-testid="baseButton-secondary"]:hover, [data-testid="baseButton-secondary"]:focus,
a[data-testid="stLinkButton"]:hover, a[data-testid="stLinkButton"]:focus,
.stLinkButton > a:hover, .stLinkButton > a:focus {
    outline: none !important;
    box-shadow: none !important;
    border: 2px solid #4A148C !important;
    background: #4A148C !important;
    background-color: #4A148C !important;
    color: white !important;
}

/* 🔧 사이드바 버튼들만 기본 스타일로 덮어쓰기 */
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] .stButton button,
section[data-testid="stSidebar"] div.stButton > button {
    background: transparent !important;
    background-color: transparent !important;
    border: 1px solid #ddd !important;
    color: #333 !important;
    padding: 10px 15px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
}

/* 🔧 사이드바 버튼 호버 효과 제거 */
section[data-testid="stSidebar"] button:hover,
section[data-testid="stSidebar"] button:focus,
section[data-testid="stSidebar"] .stButton button:hover,
section[data-testid="stSidebar"] .stButton button:focus,
section[data-testid="stSidebar"] div.stButton > button:hover,
section[data-testid="stSidebar"] div.stButton > button:focus {
    outline: none !important;
    box-shadow: none !important;
    border: 1px solid #ddd !important;
    background: transparent !important;
    background-color: transparent !important;
    color: #333 !important;
}

/* 🔧 선택된 사이드바 버튼 (primary) 스타일 */
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] .stButton button[kind="primary"],
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
    background: #e3f2fd !important;
    background-color: #e3f2fd !important;
    border: 1px solid #1976d2 !important;
    color: #1976d2 !important;
}

/* 🔧 네비게이션 버튼 - primary(활성) 스타일 - 보라색 배경 */
button[kind="primary"][data-testid*="nav_"],
button[data-testid="nav_news"][kind="primary"],
button[data-testid="nav_plans"][kind="primary"] {
    background: #4A148C !important;
    background-color: #4A148C !important;
    color: white !important;
    border: 2px solid #4A148C !important;
    font-weight: 700 !important;
    padding: 12px 16px !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

/* 🔧 네비게이션 버튼 - primary 호버 효과 */
button[kind="primary"][data-testid*="nav_"]:hover,
button[data-testid="nav_news"][kind="primary"]:hover,
button[data-testid="nav_plans"][kind="primary"]:hover {
    background: #6B21A8 !important;
    background-color: #6B21A8 !important;
    color: white !important;
    border: 2px solid #6B21A8 !important;
    box-shadow: none !important;
}

/* 🔧 네비게이션 버튼 - secondary(비활성) 스타일 - 흰색 배경 */
button[kind="secondary"][data-testid*="nav_"],
button[data-testid="nav_news"][kind="secondary"],
button[data-testid="nav_plans"][kind="secondary"] {
    background: #fff !important;
    background-color: #fff !important;
    color: #4A148C !important;
    border: 2px solid #4A148C !important;
    font-weight: 700 !important;
    padding: 12px 16px !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

/* 🔧 네비게이션 버튼 - secondary 호버 효과 */
button[kind="secondary"][data-testid*="nav_"]:hover,
button[data-testid="nav_news"][kind="secondary"]:hover,
button[data-testid="nav_plans"][kind="secondary"]:hover {
    background: #4A148C !important;
    background-color: #4A148C !important;
    color: white !important;
    border: 2px solid #4A148C !important;
    box-shadow: none !important;
}

/* 사이드바 넓이 증가 */
.css-1d391kg {
    width: 300px;
}
.css-1lcbmhc {
    width: 300px;
}

/* 그리드 스타일링 */
.stColumn {
    padding: 0 0.3rem;
}
.stColumn > div {
    height: 100%;
}

/* 태그 색상 기반 제목 박스 스타일 */
.news-title-box {
    padding: 20px;
    border-radius: 12px;
    margin: 10px 0;
    color: white;
    text-align: center;
    font-weight: bold;
    min-height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.news-summary {
    margin: 1rem 0;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
    border-left: 4px solid #dee2e6;
    line-height: 1.6;
}

/* 상세 페이지 전용 CSS */
.detail-page {
    font-size: 18px !important;
    line-height: 1.8 !important;
}
.detail-page h1 {
    font-size: 36px !important;
    line-height: 1.4 !important;
    margin-bottom: 20px !important;
}
.detail-page h2 {
    font-size: 28px !important;
    line-height: 1.5 !important;
    margin: 25px 0 15px 0 !important;
}
.detail-page h3 {
    font-size: 24px !important;
    line-height: 1.5 !important;
    margin: 20px 0 10px 0 !important;
}
.detail-page p {
    font-size: 18px !important;
    line-height: 1.8 !important;
    margin-bottom: 15px !important;
}
.detail-page li {
    font-size: 18px !important;
    line-height: 1.8 !important;
    margin-bottom: 8px !important;
}
.detail-page strong, .detail-page b {
    font-size: 19px !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

class BusanNewsPortal:
    """부산시청 보도자료 포털 메인 클래스"""
    
    def __init__(self):
        self.md_dir = MD_DIR
        self.news_data = []
        self.load_news_data()
    
    def load_news_data(self) -> List[Dict]:
        """마크다운 파일들에서 뉴스 데이터 로드"""
        news_list = []
        
        if not self.md_dir.exists():
            st.error(f"📁 마크다운 디렉토리가 없습니다: {self.md_dir}")
            return []
        
        md_files = list(self.md_dir.glob("*.md"))
        
        if not md_files:
            st.warning("📄 마크다운 파일이 없습니다. 크롤링을 먼저 실행해주세요.")
            return []
        
        for md_file in md_files:
            try:
                news_item = self._parse_markdown_file(md_file)
                if news_item:
                    news_list.append(news_item)
            except Exception as e:
                st.error(f"파일 파싱 오류 {md_file.name}: {e}")
                continue
        
        # 날짜순 정렬 (최신순)
        news_list.sort(key=lambda x: x['date'], reverse=True)
        self.news_data = news_list
        
        return news_list
    
    def _parse_markdown_file(self, md_file: Path) -> Optional[Dict]:
        """마크다운 파일에서 메타데이터와 내용 추출"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # frontmatter 파싱
            if not content.startswith('---'):
                return None
            
            frontmatter_end = content.find('---', 3)
            if frontmatter_end == -1:
                return None
            
            frontmatter = content[3:frontmatter_end]
            body = content[frontmatter_end + 3:].strip()
            
            # 메타데이터 추출
            metadata = {}
            for line in frontmatter.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    if key == 'tags':
                        # JSON 형태의 태그 파싱
                        try:
                            metadata[key] = json.loads(value)
                        except:
                            # 간단한 형태 파싱
                            tags = value.strip('[]').replace('"', '').split(',')
                            metadata[key] = [tag.strip() for tag in tags if tag.strip()]
                    else:
                        metadata[key] = value
            
            # 본문에서 요약 추출
            summary = self._extract_summary_from_body(body)
            
            return {
                'title': metadata.get('title', '제목 없음'),
                'date': metadata.get('date', '날짜 없음'),
                'tags': metadata.get('tags', []),
                'source_url': metadata.get('source_url', ''),
                'thumbnail_summary': metadata.get('thumbnail_summary', ''),
                'detailed_summary': summary,
                'file_path': str(md_file)
            }
            
        except Exception as e:
            st.error(f"마크다운 파싱 오류: {e}")
            return None
    
    def _extract_summary_from_body(self, body: str) -> str:
        """본문에서 요약 추출"""
        lines = body.split('\n')
        summary_lines = []
        
        # "## 📋 주요 내용" 부분 찾기
        in_main_content = False
        
        for line in lines:
            line = line.strip()
            if '## 📋 주요 내용' in line or '## 📋 핵심 내용' in line:
                in_main_content = True
                continue
            elif line.startswith('##') and in_main_content:
                break
            elif in_main_content and line and not line.startswith('#'):
                summary_lines.append(line)
        
        return '\n'.join(summary_lines).strip() if summary_lines else body[:200] + "..."
    
    def get_tag_stats(self) -> Dict:
        """태그별 통계 계산"""
        tag_counts = {}
        
        for news in self.news_data:
            for tag in news['tags']:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return tag_counts
    
    def get_recent_stats(self, days: int = 7) -> Dict:
        """최근 통계 계산"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_count = 0
        
        for news in self.news_data:
            try:
                news_date = datetime.strptime(news['date'], '%Y-%m-%d')
                if news_date >= cutoff_date:
                    recent_count += 1
            except:
                continue
        
        return {
            'total': len(self.news_data),
            'recent': recent_count,
            'days': days
        }
    
    def filter_news(self, selected_tags: List[str] = None, 
                   search_query: str = "", 
                   date_range: tuple = None) -> List[Dict]:
        """뉴스 필터링"""
        filtered_news = self.news_data.copy()
        
        # 태그 필터링
        if selected_tags and "전체" not in selected_tags:
            filtered_news = [
                news for news in filtered_news 
                if any(tag in selected_tags for tag in news['tags'])
            ]
        
        # 검색어 필터링
        if search_query:
            search_query = search_query.lower()
            filtered_news = [
                news for news in filtered_news
                if (search_query in news['title'].lower() or 
                    search_query in news.get('detailed_summary', '').lower())
            ]
        
        # 날짜 필터링
        if date_range:
            start_date, end_date = date_range
            filtered_news = [
                news for news in filtered_news
                if start_date <= datetime.strptime(news['date'], '%Y-%m-%d').date() <= end_date
            ]
        
        return filtered_news

def extract_contact_from_content(md_content: str) -> str:
    """마크다운 내용에서 연락처 정보 추출"""
    try:
        # "## 📞 세부문의" 섹션 찾기
        contact_pattern = r'## 📞 세부문의\s*\n([^\n#]+)'
        match = re.search(contact_pattern, md_content)
        
        if match:
            contact_info = match.group(1).strip()
            return contact_info
        
        # 대안 패턴 찾기
        alternative_patterns = [
            r'문의.*?(\d{3}-\d{3,4}-\d{4})',
            r'연락처.*?(\d{3}-\d{3,4}-\d{4})',
            r'담당.*?(\d{3}-\d{3,4}-\d{4})',
        ]
        
        for pattern in alternative_patterns:
            match = re.search(pattern, md_content)
            if match:
                return f"담당 부서 ({match.group(1)})"
        
        return "담당 부서 (부산시청 원문참고)"
        
    except Exception as e:
        return "문의처 정보 오류"

def render_header():
    """헤더 렌더링 (탭 네비게이션 포함)"""
    # 제목과 탭을 나란히 배치
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.title("🏢 요즘 부산")
    
    with col2:
        # 탭 스타일 네비게이션
        current_page = st.session_state.get('page', 'news')
        
        # 탭 스타일 CSS와 함께 버튼 생성
        st.markdown("""
        <style>
        .tab-container {
            display: flex;
            border-bottom: 2px solid #e0e0e0;
            margin-top: 20px;
            margin-bottom: 0px;
        }
        .tab-button {
            padding: 12px 24px;
            background: #f5f5f5;
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            margin-right: 4px;
            color: #666;
            border-bottom: 3px solid transparent;
        }
        .tab-button.active {
            background: white;
            color: #4A148C;
            border-bottom: 3px solid #4A148C;
        }
        .tab-button:hover {
            background: #e9e9e9;
        }
        .tab-button.active:hover {
            background: white;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 컬럼으로 탭 버튼 배치
        tab_col1, tab_col2 = st.columns(2)
        
        with tab_col1:
            news_active = "active" if current_page == 'news' else ""
            if st.button("📰 보도자료 바로가기", key="nav_news", use_container_width=True, 
                        type="primary" if current_page == 'news' else "secondary"):
                st.session_state.page = 'news'
                st.session_state.items_to_show = 12
                st.rerun()
        
        with tab_col2:
            plans_active = "active" if current_page == 'plans' else ""
            if st.button("📋 업무계획 바로가기", key="nav_plans", use_container_width=True,
                        type="primary" if current_page == 'plans' else "secondary"):
                st.session_state.page = 'plans'
                st.session_state.plans_items_to_show = 12
                st.rerun()
    
    # 페이지별 설명과 이용 방법
    current_page = st.session_state.get('page', 'news')
    if current_page == 'news':
        st.markdown("### 부산시 최신 보도자료를 알려드립니다")
        
        # 🔧 사용 안내 추가
        st.info("""
        **📖 이용 방법**
        - 왼쪽 사이드바에서 **분야를 선택**하면 해당 분야의 보도자료를 확인할 수 있습니다
        - **검색어**를 입력하여 원하는 내용을 빠르게 찾아보세요 **(검색어 모두 지우신 후 엔터 치면 전체보기 가능)**
        - 각 카드를 클릭하면 **상세 내용**을 볼 수 있습니다 (보도자료 원문 링크 포함)
        - (주의) AI 요약이라 세부내용, 부서 연락처 오류가 있을 수 있으니 정확한 정보는 원문링크 참고하세요!
        """)
    else:
        st.markdown("### 2025년 부산시 각 부서별 주요 업무계획을 확인하세요")
        
        # 업무계획용 이용 방법
        st.info("""
        **📋 이용 방법**
        - 왼쪽 사이드바에서 **부서별 분류**를 선택하여 원하는 분야의 업무계획을 확인할 수 있습니다
        - **검색어**를 입력하여 특정 부서나 사업명을 빠르게 찾아보세요
        - 각 카드를 클릭하면 **상세 업무계획**을 볼 수 있습니다 (기본현황, 추진과제, 예산 등)
        - 2025년 부산시 각 부서의 주요 정책과 사업을 한눈에 파악하실 수 있습니다!
        """)

def render_news_sidebar(portal: BusanNewsPortal):
    """보도자료 전용 사이드바"""
    st.sidebar.header("🔍 필터 및 검색")
    
    # 검색어 입력
    search_query = st.sidebar.text_input(
        "🔎 검색어",
        placeholder="제목이나 내용 검색",
        help="보도자료 제목이나 내용에서 검색합니다.",
        key="news_search_input"
    )
    
    # 태그 선택 버튼들
    sidebar_tags = [
        ("🏠 전체", "전체"),
        ("👨‍🎓 청년·교육", "청년·교육"),
        ("💼 일자리·경제", "일자리·경제"), 
        ("❤️ 복지·건강", "복지·건강"),
        ("🚌 교통·주거", "교통·주거"),
        ("🎭 문화·관광", "문화·관광"),
        ("🛡️ 안전·환경", "안전·환경"),
        ("🏛️ 행정·소식", "행정·소식")
    ]
    
    # 태그별 통계 계산
    tag_stats = portal.get_tag_stats()
    total_count = len(portal.news_data)
    tag_stats["전체"] = total_count
    
    st.sidebar.subheader("🏷️ 분야 선택")
    
    # 세션 상태에서 선택된 태그 관리
    if 'selected_news_tag' not in st.session_state:
        st.session_state.selected_news_tag = "전체"
    
    selected_tags = []
    
    for display_name, tag_value in sidebar_tags:
        count = tag_stats.get(tag_value, 0)
        is_selected = st.session_state.selected_news_tag == tag_value
        button_type = "primary" if is_selected else "secondary"
        
        if st.sidebar.button(
            f"{display_name} ({count}개)", 
            key=f"news_tag_{tag_value}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_news_tag = tag_value
            st.session_state.items_to_show = 12
            st.rerun()
    
    selected_tags = [st.session_state.selected_news_tag] if st.session_state.selected_news_tag != "전체" else ["전체"]
    
    # 날짜 범위 선택
    st.sidebar.subheader("📅 날짜 범위")
    date_filter = st.sidebar.radio(
        "기간 선택",
        ["전체", "최근 7일", "최근 30일", "사용자 정의"],
        key="news_date_filter"
    )
    
    date_range = None
    if date_filter == "최근 7일":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        date_range = (start_date, end_date)
    elif date_filter == "최근 30일":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        date_range = (start_date, end_date)
    elif date_filter == "사용자 정의":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.sidebar.date_input("시작일", key="news_start_date")
        with col2:
            end_date = st.sidebar.date_input("종료일", key="news_end_date")
        if start_date and end_date:
            date_range = (start_date, end_date)
    
    # 통계 정보
    st.sidebar.divider()
    st.sidebar.subheader("📊 선택된 분야")
    stats = portal.get_recent_stats()
    
    if st.session_state.selected_news_tag == "전체":
        st.sidebar.success(f"🏠 **전체 보도자료**: {stats['total']}개")
    else:
        selected_count = tag_stats.get(st.session_state.selected_news_tag, 0)
        emoji_tag = next((display for display, tag in sidebar_tags if tag == st.session_state.selected_news_tag), st.session_state.selected_news_tag)
        st.sidebar.success(f"**{emoji_tag}**: {selected_count}개")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("전체", stats['total'])
    with col2:
        st.metric("최근 7일", stats['recent'])
    
    return search_query, selected_tags, date_range

def render_plans_sidebar(plans_portal: BusanPlansPortal):
    """업무계획 전용 사이드바"""
    st.sidebar.header("📋 업무계획 필터")
    
    # 검색어 입력
    search_query = st.sidebar.text_input(
        "🔎 검색어",
        placeholder="부서명이나 내용 검색",
        help="업무계획 제목, 부서명, 내용에서 검색합니다.",
        key="plans_search_input"
    )
    
    # 부서별 분류 선택
    st.sidebar.subheader("🏛️ 부서별 분류")
    
    # 분류별 통계 계산
    dept_stats = {}
    for plan in plans_portal.plans_data:
        category = plans_portal.get_department_category(plan.get('department', ''))
        dept_stats[category] = dept_stats.get(category, 0) + 1
    
    total_count = len(plans_portal.plans_data)
    dept_stats["전체"] = total_count
    
    # 세션 상태에서 선택된 분류 관리
    if 'selected_plans_category' not in st.session_state:
        st.session_state.selected_plans_category = "전체"
    
    selected_categories = []
    
    for display_name, dept_list in PLAN_DEPARTMENTS:
        category = display_name.split(' ', 1)[1] if ' ' in display_name else display_name
        count = dept_stats.get(category, 0)
        is_selected = st.session_state.selected_plans_category == category
        button_type = "primary" if is_selected else "secondary"
        
        if st.sidebar.button(
            f"{display_name} ({count}개)", 
            key=f"plans_dept_{category}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_plans_category = category
            st.session_state.plans_items_to_show = 12
            st.rerun()
    
    selected_categories = [st.session_state.selected_plans_category] if st.session_state.selected_plans_category != "전체" else ["전체"]
    
    # 통계 정보
    st.sidebar.divider()
    st.sidebar.subheader("📊 선택된 분류")
    
    if st.session_state.selected_plans_category == "전체":
        st.sidebar.success(f"🏠 **전체 업무계획**: {total_count}개")
    else:
        selected_count = dept_stats.get(st.session_state.selected_plans_category, 0)
        emoji_category = next((display for display, dept in PLAN_DEPARTMENTS if display.endswith(st.session_state.selected_plans_category)), st.session_state.selected_plans_category)
        st.sidebar.success(f"**{emoji_category}**: {selected_count}개")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("전체", total_count)
    with col2:
        dept_count = len(set(plan.get('department', '') for plan in plans_portal.plans_data))
        st.metric("부서 수", dept_count)
    
    return search_query, selected_categories

def render_news_card_aligned(news_item: Dict):
    """보도자료 카드 렌더링"""
    with st.container():
        # 태그와 날짜 표시
        col_tag, col_date = st.columns(2)
        
        with col_tag:
            if news_item['tags']:
                main_tag = news_item['tags'][0]
                tag_color = TAG_COLORS.get(main_tag, "#6B7280")
                st.markdown(
                    f"""
                    <div style="
                        background-color: {tag_color}; 
                        color: white; 
                        padding: 8px 12px; 
                        border-radius: 12px; 
                        font-size: 16px; 
                        font-weight: bold;
                        display: inline-block;
                        margin-bottom: 8px;
                    ">
                        🏷️ #{main_tag}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                main_tag = "전체"
                tag_color = "#6B7280"
        
        with col_date:
            st.markdown(
                f"""
                <div style="
                    text-align: right; 
                    background-color: rgba(0,0,0,0.1); 
                    color: #333; 
                    padding: 8px 12px; 
                    border-radius: 12px; 
                    font-size: 16px; 
                    font-weight: bold;
                    margin-bottom: 8px;
                    width: fit-content;
                    margin-left: auto;
                ">
                    📅 {news_item['date']}
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        # 태그별 파스텔 색상 매핑
        pastel_colors = {
            "#6B7280": "#E5E7EB",   # 회색 → 연한 회색
            "#3B82F6": "#DBEAFE",   # 파란색 → 연한 파란색
            "#10B981": "#D1FAE5",   # 초록색 → 연한 초록색
            "#EF4444": "#FEE2E2",   # 빨간색 → 연한 빨간색
            "#8B5CF6": "#EDE9FE",   # 보라색 → 연한 보라색
            "#F59E0B": "#FEF3C7",   # 주황색 → 연한 주황색
            "#06B6D4": "#CFFAFE",   # 청록색 → 연한 청록색
            "#84CC16": "#ECFCCB",   # 라임색 → 연한 라임색
            "#EC4899": "#FCE7F3"    # 핑크색 → 연한 핑크색
        }
        
        pastel_color = pastel_colors.get(tag_color, "#F3F4F6")
        
        def smart_line_break(title, max_chars_per_line=15):
            """한글 어절 단위로 자연스러운 줄바꿈"""
            words = title.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                
                if len(test_line) <= max_chars_per_line:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        lines.append(word[:max_chars_per_line])
                        current_line = word[max_chars_per_line:] if len(word) > max_chars_per_line else ""
            
            if current_line:
                lines.append(current_line)
            
            return "<br>".join(lines[:4])
        
        formatted_title = smart_line_break(news_item['title'])
        
        # 제목 박스
        st.markdown(
            f"""
            <div style="
                background-color: {pastel_color};
                color: #374151;
                padding: 15px;
                border-radius: 12px;
                margin: 10px 0;
                height: 140px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 2px solid {tag_color}40;
                text-align: center;
                box-sizing: border-box;
            ">
                <div style="
                    width: 100%;
                    font-size: 20px; 
                    font-weight: bold; 
                    color: #1F2937;
                    line-height: 1.4;
                    text-align: center;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100%;
                ">
                    <span style="display: block; width: 100%;">{formatted_title}</span>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # 요약 텍스트
        summary = news_item.get('detailed_summary', news_item.get('thumbnail_summary', ''))
        if len(summary) > 120:
            summary = summary[:120] + "..."
        
        st.markdown(
            f"""
            <div style="
                margin: 0rem 0 0.5rem 0;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #dee2e6;
                line-height: 1.6;
                height: 100px;
                overflow: hidden;
                display: flex;
                align-items: flex-start;
                font-size: 14px;
                color: #495057;
            ">
                {summary}
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # 클릭 버튼 (간격 줄이고 글자 크게)
        if st.button(
            "📄 클릭하여 내용 보기",
            key=f"news_detail_btn_{hash(news_item['file_path'])}",
            use_container_width=True,
        ):
            st.session_state.selected_news = news_item
            st.session_state.show_detail = True
            st.session_state.scroll_to_top = True
            st.rerun()
        
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

def render_plans_card(plan_item: Dict):
    """업무계획 카드 렌더링"""
    with st.container():
        # 부서명과 분류 표시
        col_dept, col_category = st.columns(2)
        
        with col_dept:
            department = plan_item.get('department', '미분류')
            st.markdown(
                f"""
                <div style="
                    background-color: #4A148C; 
                    color: white; 
                    padding: 8px 12px; 
                    border-radius: 12px; 
                    font-size: 16px; 
                    font-weight: bold;
                    display: inline-block;
                    margin-bottom: 8px;
                ">
                    🏛️ {department}
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        with col_category:
            category = plan_item.get('tags', ['전체'])[0] if plan_item.get('tags') else '전체'
            category_color = PLAN_TAG_COLORS.get(category, "#6B7280")
            st.markdown(
                f"""
                <div style="
                    text-align: right; 
                    background-color: {category_color}; 
                    color: white; 
                    padding: 8px 12px; 
                    border-radius: 12px; 
                    font-size: 16px; 
                    font-weight: bold;
                    margin-bottom: 8px;
                    width: fit-content;
                    margin-left: auto;
                ">
                    📋 {category}
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        # 분류별 파스텔 색상 매핑
        pastel_colors = {
            "#6B7280": "#E5E7EB",   # 전체 - 회색
            "#8B5CF6": "#EDE9FE",   # 기획감사 - 보라색
            "#EF4444": "#FEE2E2",   # 복지안전 - 빨간색
            "#F59E0B": "#FEF3C7",   # 건설교통 - 주황색
            "#10B981": "#D1FAE5",   # 도시환경 - 초록색
            "#06B6D4": "#CFFAFE",   # 경제산업 - 청록색
            "#3B82F6": "#DBEAFE"    # 문화교육 - 파란색
        }
        
        pastel_color = pastel_colors.get(category_color, "#F3F4F6")
        
        def smart_line_break(title, max_chars_per_line=15):
            """한글 어절 단위로 자연스러운 줄바꿈"""
            words = title.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                
                if len(test_line) <= max_chars_per_line:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        lines.append(word[:max_chars_per_line])
                        current_line = word[max_chars_per_line:] if len(word) > max_chars_per_line else ""
            
            if current_line:
                lines.append(current_line)
            
            return "<br>".join(lines[:4])
        
        formatted_title = smart_line_break(plan_item['title'])
        
        # 제목 박스
        st.markdown(
            f"""
            <div style="
                background-color: {pastel_color};
                color: #374151;
                padding: 15px;
                border-radius: 12px;
                margin: 10px 0;
                height: 140px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 2px solid {category_color}40;
                text-align: center;
                box-sizing: border-box;
            ">
                <div style="
                    width: 100%;
                    font-size: 20px; 
                    font-weight: bold; 
                    color: #1F2937;
                    line-height: 1.4;
                    text-align: center;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100%;
                ">
                    <span style="display: block; width: 100%;">{formatted_title}</span>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # 요약 텍스트 (thumbnail_summary만 간단하게)
        summary = plan_item.get('thumbnail_summary', '')
        if not summary:
            summary = "2025년 주요업무계획"
        
        st.markdown(
            f"""
            <div style="
                margin: 0rem 0 0.5rem 0;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
                text-align: center;
                height: 80px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                font-weight: 600;
                color: #495057;
                border-left: 4px solid #dee2e6;
            ">
                {summary}
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # 클릭 버튼 (간격 줄이고 글자 크게)
        if st.button(
            "📋 클릭하여 계획 보기",
            key=f"plans_detail_btn_{hash(plan_item['file_path'])}",
            use_container_width=True,
        ):
            st.session_state.selected_plan = plan_item
            st.session_state.show_plan_detail = True
            st.session_state.scroll_to_top = True
            st.rerun()
        
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

def render_news_grid_with_scroll(news_list: List[Dict]):
    """보도자료 그리드 렌더링"""
    if not news_list:
        st.info("🔍 조건에 맞는 보도자료가 없습니다.")
        return
    
    if 'items_to_show' not in st.session_state:
        st.session_state.items_to_show = 12
    
    st.success(f"📊 총 **{len(news_list)}개**의 보도자료")
    
    current_news = news_list[:st.session_state.items_to_show]
    
    # 4열 그리드
    for i in range(0, len(current_news), 4):
        cols = st.columns(4, gap="small")
        
        for j in range(4):
            if i + j < len(current_news):
                with cols[j]:
                    render_news_card_aligned(current_news[i + j])
            else:
                with cols[j]:
                    st.markdown("<div style='height: 400px; visibility: hidden;'></div>", unsafe_allow_html=True)
    
    # 더 보기 버튼
    if st.session_state.items_to_show < len(news_list):
        remaining = len(news_list) - st.session_state.items_to_show
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(f"📄 더 보기 ({remaining}개 남음)", use_container_width=True, type="primary"):
                st.session_state.items_to_show += 12
                st.rerun()

def render_plans_grid_with_scroll(plans_list: List[Dict]):
    """업무계획 그리드 렌더링"""
    if not plans_list:
        st.info("🔍 조건에 맞는 업무계획이 없습니다.")
        return
    
    if 'plans_items_to_show' not in st.session_state:
        st.session_state.plans_items_to_show = 12
    
    st.success(f"📊 총 **{len(plans_list)}개**의 업무계획")
    
    current_plans = plans_list[:st.session_state.plans_items_to_show]
    
    # 4열 그리드
    for i in range(0, len(current_plans), 4):
        cols = st.columns(4, gap="small")
        
        for j in range(4):
            if i + j < len(current_plans):
                with cols[j]:
                    render_plans_card(current_plans[i + j])
            else:
                with cols[j]:
                    st.markdown("<div style='height: 400px; visibility: hidden;'></div>", unsafe_allow_html=True)
    
    # 더 보기 버튼
    if st.session_state.plans_items_to_show < len(plans_list):
        remaining = len(plans_list) - st.session_state.plans_items_to_show
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(f"📋 더 보기 ({remaining}개 남음)", use_container_width=True, type="primary", key="plans_load_more"):
                st.session_state.plans_items_to_show += 12
                st.rerun()

def render_news_detail(news_item: Dict):
    """보도자료 상세 페이지"""
    if st.session_state.get('scroll_to_top'):
        scroll_to_here(0, key='news_detail_top')
        st.session_state.scroll_to_top = False
    
    # 🔧 상단 네비게이션 버튼 추가 (일관된 크기와 스타일)
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        if st.button("← 뒤로가기", key="news_back_top", use_container_width=True, type="secondary"):
            st.session_state.show_detail = False
            st.session_state.selected_news = None
            st.rerun()
    
    with col3:
        if news_item.get('source_url'):
            if st.button("🏛️ 부산시청 원문", key="news_original_top", use_container_width=True, type="primary"):
                # 새 탭에서 링크 열기를 위한 JavaScript
                st.markdown(f'<script>window.open("{news_item["source_url"]}", "_blank");</script>', unsafe_allow_html=True)
                # 또는 직접 링크로 이동
                st.markdown(f'<meta http-equiv="refresh" content="0; url={news_item["source_url"]}">', unsafe_allow_html=True)
    
    st.markdown('<div class="detail-page">', unsafe_allow_html=True)
    
    st.markdown(f'<h1>{news_item["title"]}</h1>', unsafe_allow_html=True)
    
    # 메타 정보 (4개 컬럼)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<p style="font-size: 18px;"><strong>📅 게시일</strong>: {news_item["date"]}</p>', unsafe_allow_html=True)
    with col2:
        if news_item['tags']:
            main_tag = news_item['tags'][0]
            st.markdown(f'<p style="font-size: 18px;"><strong>🏷️ 분야</strong>: #{main_tag}</p>', unsafe_allow_html=True)
    
    # 연락처 정보 추가 (col3)
    with col3:
        contact_info = "담당 부서 (부산시청 원문참고)"
        try:
            with open(news_item['file_path'], 'r', encoding='utf-8') as f:
                md_content = f.read()
            contact_info = extract_contact_from_content(md_content)
            if not contact_info or not contact_info.strip():
                contact_info = "담당 부서 (부산시청 원문참고)"
        except Exception:
            contact_info = "문의처 정보 오류"
        st.markdown(f'<p style="font-size: 18px;"><strong>📞 문의</strong>: {contact_info}</p>', unsafe_allow_html=True)
    
    # 원문 링크 추가 (col4)
    with col4:
        if news_item.get('source_url'):
            st.markdown(
                f'<p style="font-size: 18px;"><strong>🔗 <a href="{news_item["source_url"]}" target="_blank" style="color: #4A148C; text-decoration: none;">부산시청 원문</a></strong></p>',
                unsafe_allow_html=True
            )
    
    st.divider()
    
    # MD 파일 내용 표시
    try:
        with open(news_item['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        if md_content.startswith('---'):
            frontmatter_end = md_content.find('---', 3)
            if frontmatter_end > 0:
                md_content = md_content[frontmatter_end + 3:].strip()
        
        st.markdown(md_content)
        
    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # 하단 버튼 (목록으로 돌아가기만, 가로 길이 늘림)
    if st.button("⬅️ 목록으로 돌아가기", use_container_width=True, key="news_back_btn2"):
        st.session_state.show_detail = False
        st.session_state.selected_news = None
        st.rerun()

def render_plans_detail(plan_item: Dict):
    """업무계획 상세 페이지"""
    if st.session_state.get('scroll_to_top'):
        scroll_to_here(0, key='plans_detail_top')
        st.session_state.scroll_to_top = False
    
    # 🔧 상단 네비게이션 버튼 추가 (일관된 크기와 스타일)
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        if st.button("← 뒤로가기", key="plans_back_top", use_container_width=True, type="secondary"):
            st.session_state.show_plan_detail = False
            st.session_state.selected_plan = None
            st.rerun()
    
    with col3:
        if st.button("🏛️ 부산시청 원문", key="plans_original_top", use_container_width=True, type="primary"):
            # 새 탭에서 링크 열기를 위한 JavaScript
            st.markdown('<script>window.open("https://www.busan.go.kr/gbplan", "_blank");</script>', unsafe_allow_html=True)
            # 또는 직접 링크로 이동  
            st.markdown('<meta http-equiv="refresh" content="0; url=https://www.busan.go.kr/gbplan">', unsafe_allow_html=True)
    
    st.markdown('<div class="detail-page">', unsafe_allow_html=True)
    
    st.markdown(f'<h1>{plan_item["title"]}</h1>', unsafe_allow_html=True)
    
    # 메타 정보
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<p style="font-size: 18px;"><strong>🏛️ 담당부서</strong>: {plan_item.get("department", "미분류")}</p>', unsafe_allow_html=True)
    with col2:
        category = plan_item.get('tags', ['전체'])[0] if plan_item.get('tags') else '전체'
        st.markdown(f'<p style="font-size: 18px;"><strong>📋 분류</strong>: {category}</p>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<p style="font-size: 18px;"><strong>📅 기준년도</strong>: 2025년</p>', unsafe_allow_html=True)
    with col4:
        st.markdown(
            f'<p style="font-size: 18px;"><strong>🔗 <a href="https://www.busan.go.kr/gbplan" target="_blank" style="color: #4A148C; text-decoration: none;">부산시청 원문</a></strong></p>',
            unsafe_allow_html=True
        )
    
    st.divider()
    
    # MD 파일 내용 표시
    try:
        with open(plan_item['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        if md_content.startswith('---'):
            frontmatter_end = md_content.find('---', 3)
            if frontmatter_end > 0:
                md_content = md_content[frontmatter_end + 3:].strip()
        
        st.markdown(md_content)
        
    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    if st.button("⬅️ 목록으로 돌아가기", use_container_width=True, key="plans_back_btn2"):
        st.session_state.show_plan_detail = False
        st.session_state.selected_plan = None
        st.rerun()

def main():
    """메인 앱 실행"""
    # 세션 상태 초기화
    if 'show_detail' not in st.session_state:
        st.session_state.show_detail = False
    if 'selected_news' not in st.session_state:
        st.session_state.selected_news = None
    if 'show_plan_detail' not in st.session_state:
        st.session_state.show_plan_detail = False
    if 'selected_plan' not in st.session_state:
        st.session_state.selected_plan = None
    if 'page' not in st.session_state:
        st.session_state.page = 'news'
    
    try:
        # 상세 페이지 표시 여부 확인
        if st.session_state.show_detail and st.session_state.selected_news:
            render_news_detail(st.session_state.selected_news)
        elif st.session_state.show_plan_detail and st.session_state.selected_plan:
            render_plans_detail(st.session_state.selected_plan)
        else:
            # 메인 페이지
            render_header()
            
            if st.session_state.page == 'news':
                # 보도자료 페이지
                portal = BusanNewsPortal()
                search_query, selected_tags, date_range = render_news_sidebar(portal)
                filtered_news = portal.filter_news(selected_tags, search_query, date_range)
                
                if portal.news_data:
                    render_news_grid_with_scroll(filtered_news)
                else:
                    st.info("📢 보도자료 데이터를 로드하는 중입니다...")
                    
            elif st.session_state.page == 'plans':
                # 업무계획 페이지
                plans_portal = BusanPlansPortal()
                search_query, selected_categories = render_plans_sidebar(plans_portal)
                filtered_plans = plans_portal.filter_plans(selected_categories, search_query)
                
                if plans_portal.plans_data:
                    render_plans_grid_with_scroll(filtered_plans)
                else:
                    st.info("📋 업무계획 데이터를 로드하는 중입니다...")
                
                # 제작자 정보
                st.markdown(
                    """
                    <div style="
                        text-align: center; 
                        margin: 20px 0; 
                        padding: 15px; 
                        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 50%, #f8f9fa 100%);
                        border-radius: 10px;
                    ">
                        <p style="margin: 0; color: #495057; font-size: 14px;">
                            🏛️ <strong>Made by 부산시청 매니저</strong> | 
                            ⭐ <strong>즐겨찾기: Ctrl+D (Windows) / Cmd+D (Mac)</strong> | 
                            🌐 <strong><a href="https://www.busan.go.kr" target="_blank" style="color: #0d6efd; text-decoration: none;">부산시청 바로가기</a></strong>
                        </p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            # 보도자료 페이지에도 제작자 정보 추가
            if st.session_state.page == 'news':
                st.markdown(
                    """
                    <div style="
                        text-align: center; 
                        margin: 20px 0; 
                        padding: 15px; 
                        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 50%, #f8f9fa 100%);
                        border-radius: 10px;
                    ">
                        <p style="margin: 0; color: #495057; font-size: 14px;">
                            🏛️ <strong>Made by 부산시청 매니저</strong> | 
                            ⭐ <strong>즐겨찾기: Ctrl+D (Windows) / Cmd+D (Mac)</strong> | 
                            🌐 <strong><a href="https://www.busan.go.kr" target="_blank" style="color: #0d6efd; text-decoration: none;">부산시청 바로가기</a></strong>
                        </p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
    except Exception as e:
        st.error(f"❌ 앱 실행 중 오류: {e}")
        st.info("**해결 방법**: 데이터 파일을 확인하거나 페이지를 새로고침해주세요.")

if __name__ == "__main__":
    main()