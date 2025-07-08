"""
부산시청 보도자료 포털 - Streamlit 앱
=====================================
태그 색상 기반 카드형 UI로 보도자료를 쉽게 검색하고 확인할 수 있는 포털

실행 방법:
    streamlit run app.py
"""

import streamlit as st
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import streamlit.components.v1 as components

# 프로젝트 모듈 import
from config import (
    MD_DIR, AVAILABLE_TAGS, TAG_COLORS,
    IS_LOCAL, get_env_info, MESSAGES
)

# 페이지 설정
st.set_page_config(
    page_title="요즘 부산",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔧 정교한 CSS - Deploy 버튼만 숨기고 사이드바 토글은 보존
st.markdown("""
<style>
/* 🔧 Deploy 버튼만 정확히 타겟해서 숨기기 */
[data-testid="stToolbar"] > div > div > div > div:last-child {
    display: none !important;
}

/* 🔧 Streamlit 헤더에서 Deploy 버튼만 숨기기 */
header[data-testid="stHeader"] button[title*="Deploy"],
header[data-testid="stHeader"] button[aria-label*="Deploy"],
header[data-testid="stHeader"] a[href*="deploy"] {
    display: none !important;
}

/* 🔧 모든 Deploy 관련 요소 숨기기 (하지만 다른 버튼은 보존) */
button[kind="header"]:has-text("Deploy"),
a[href*="deploy.streamlit.io"] {
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

/* 🔧 Streamlit 앱 전체 헤더 숨기기 (토글 버튼 제외) */
.stApp > header:not(:has([data-testid="collapsedControl"])) {
    display: none !important;
}

/* 🔧 특정 iframe만 숨기기 */
iframe[title="streamlit_app"]:not([data-testid="collapsedControl"]) {
    display: none !important;
}

/* 🔧 모든 호버 효과 완전 제거 */
*, *:hover {
    transition: none !important;
}

/* 🔧 모든 버튼 기본 스타일 (찐한 보라색) */
button, 
.stButton button,
div.stButton > button,
[data-testid="baseButton-primary"],
[data-testid="baseButton-secondary"],
a[data-testid="stLinkButton"],
.stLinkButton > a {
    height: auto !important;
    padding: 25px 20px !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    background: #4A148C !important;
    background-color: #4A148C !important;
    color: white !important;
    border-radius: 15px !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    text-decoration: none !important;
    display: block !important;
    text-align: center !important;
}

/* 🔧 호버시에도 같은 색상 유지 */
button:hover, button:focus,
.stButton button:hover, .stButton button:focus,
div.stButton > button:hover, div.stButton > button:focus,
[data-testid="baseButton-primary"]:hover, [data-testid="baseButton-primary"]:focus,
[data-testid="baseButton-secondary"]:hover, [data-testid="baseButton-secondary"]:focus,
a[data-testid="stLinkButton"]:hover, a[data-testid="stLinkButton"]:focus,
.stLinkButton > a:hover, .stLinkButton > a:focus {
    outline: none !important;
    box-shadow: none !important;
    border: none !important;
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

def render_header():
    """헤더 렌더링 (사용 안내 포함)"""
    st.title("🏢 요즘 부산")
    st.markdown("### 부산시의 최신 보도자료를 한눈에 확인하세요")
    
    # 🔧 사용 안내 추가
    st.info("""
    **📖 이용 방법**
    - 왼쪽 사이드바에서 **분야를 선택**하면 해당 분야의 보도자료를 확인할 수 있습니다
    - **검색어**를 입력하여 원하는 내용을 빠르게 찾아보세요
    - 각 카드를 클릭하면 **상세 내용**을 볼 수 있습니다
    """)
    
    # 🔧 제작자 정보 추가
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
                🌐 <strong><a href="https://www.busan.go.kr" target="_blank" style="color: #0d6efd; text-decoration: none;">부산시청 바로가기</a></strong>
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )

def render_sidebar(portal: BusanNewsPortal):
    """사이드바 렌더링 (이모지 버튼 형태 + 자연스러운 검색)"""
    st.sidebar.header("🔍 필터 및 검색")
    
    # 검색어 입력 (간단하게)
    search_query = st.sidebar.text_input(
        "🔎 검색어",
        placeholder="제목이나 내용에서 검색... (지우면 전체보기)",
        help="보도자료 제목이나 내용에서 검색합니다. 검색어를 지우면 전체 목록이 표시됩니다.",
        key="search_input"
    )
    
    # 🔧 이모지 + 태그 버튼 정의
    sidebar_tags = [
        ("🏠 전체", "전체"),
        ("👨‍🎓 청년·교육", "청년·교육"),
        ("💼 일자리·경제", "일자리·경제"), 
        ("❤️ 복지·건강", "복지·건강"),
        ("🚌 교통·주거", "교통·주거"),
        ("🎭 문화·여가", "문화·여가"),
        ("🛡️ 안전·환경", "안전·환경"),
        ("🏛️ 행정·참여", "행정·참여"),
        ("🗺️ 관광·소식", "관광·소식")
    ]
    
    # 태그별 통계 계산
    tag_stats = portal.get_tag_stats()
    
    # 🔧 전체 개수 수정: 모든 뉴스 개수
    total_count = len(portal.news_data)
    tag_stats["전체"] = total_count
    
    # 태그 선택 버튼들
    st.sidebar.subheader("🏷️ 분야 선택")
    
    # 세션 상태에서 선택된 태그 관리
    if 'selected_tag' not in st.session_state:
        st.session_state.selected_tag = "전체"
    
    selected_tags = []
    
    # 🔧 1열로 버튼 배치 (글자 밀림 방지)
    for display_name, tag_value in sidebar_tags:
        count = tag_stats.get(tag_value, 0)
        
        # 현재 선택된 태그인지 확인
        is_selected = st.session_state.selected_tag == tag_value
        button_type = "primary" if is_selected else "secondary"
        
        if st.sidebar.button(
            f"{display_name} ({count}개)", 
            key=f"tag_{tag_value}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_tag = tag_value
            st.rerun()
    
    # 선택된 태그 반환
    if st.session_state.selected_tag == "전체":
        selected_tags = ["전체"]
    else:
        selected_tags = [st.session_state.selected_tag]
    
    # 날짜 범위 선택
    st.sidebar.subheader("📅 날짜 범위")
    date_filter = st.sidebar.radio(
        "기간 선택",
        ["전체", "최근 7일", "최근 30일", "사용자 정의"],
        help="보도자료 게시 날짜 기준"
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
            start_date = st.sidebar.date_input("시작일")
        with col2:
            end_date = st.sidebar.date_input("종료일")
        if start_date and end_date:
            date_range = (start_date, end_date)
    
    # 통계 정보
    st.sidebar.divider()
    st.sidebar.subheader("📊 현재 선택된 분야")
    
    stats = portal.get_recent_stats()
    
    # 선택된 태그 정보 표시
    if st.session_state.selected_tag == "전체":
        st.sidebar.success(f"🏠 **전체 보도자료**: {stats['total']}개")
    else:
        selected_count = tag_stats.get(st.session_state.selected_tag, 0)
        emoji_tag = next((display for display, tag in sidebar_tags if tag == st.session_state.selected_tag), st.session_state.selected_tag)
        st.sidebar.success(f"**{emoji_tag}**: {selected_count}개")
    
    # 최근 통계
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("전체", stats['total'])
    with col2:
        st.metric("최근 7일", stats['recent'])
    
    return search_query, selected_tags, date_range

def render_news_card_aligned(news_item: Dict):
    """🔧 개선된 뉴스 카드 (파스텔 색상, 고정 크기 제목박스)"""
    
    with st.container():
        # 1. 상단에 태그와 날짜 표시
        col_tag, col_date = st.columns(2)
        
        with col_tag:
            if news_item['tags']:
                main_tag = news_item['tags'][0]  # 첫 번째 태그만 사용
                tag_color = TAG_COLORS.get(main_tag, "#6B7280")
                st.markdown(
                    f"""
                    <div style="
                        background-color: {tag_color}; 
                        color: white; 
                        padding: 4px 8px; 
                        border-radius: 12px; 
                        font-size: 12px; 
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
                st.markdown(
                    """
                    <div style="
                        background-color: #6B7280; 
                        color: white; 
                        padding: 4px 8px; 
                        border-radius: 12px; 
                        font-size: 12px; 
                        font-weight: bold;
                        display: inline-block;
                        margin-bottom: 8px;
                    ">
                        🏷️ #일반
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        
        with col_date:
            # 날짜 정보
            st.markdown(
                f"""
                <div style="
                    text-align: right; 
                    background-color: rgba(0,0,0,0.1); 
                    color: #333; 
                    padding: 4px 8px; 
                    border-radius: 12px; 
                    font-size: 12px; 
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
        
        # 제목 줄바꿈 개선 함수
        def smart_line_break(title, max_chars_per_line=15):
            """한글 어절 단위로 자연스러운 줄바꿈"""
            words = title.split()  # 띄어쓰기 기준으로 분리
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
                        # 단어 자체가 너무 긴 경우
                        lines.append(word[:max_chars_per_line])
                        current_line = word[max_chars_per_line:] if len(word) > max_chars_per_line else ""
            
            if current_line:
                lines.append(current_line)
            
            return "<br>".join(lines[:4])  # 최대 4줄
        
        formatted_title = smart_line_break(news_item['title'])
        
        # 2. 태그 파스텔 색상 제목 박스 (완벽한 중앙 정렬)
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
        
        # 3. 요약 텍스트 (중간에 위치) - 고정 크기
        summary = news_item.get('detailed_summary', news_item.get('thumbnail_summary', ''))
        if len(summary) > 120:
            summary = summary[:120] + "..."
        
        st.markdown(
            f"""
            <div style="
                margin: 1rem 0;
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
        
        # 4. 클릭 버튼 (하단에 위치) - 호버 효과 제거
        if st.button(
            "📄 클릭하여 내용 보기",
            key=f"detail_btn_{hash(news_item['file_path'])}",
            use_container_width=True,
            help="이 보도자료의 자세한 내용을 확인하세요"
        ):
            st.session_state.selected_news = news_item
            st.session_state.show_detail = True
            st.rerun()
        
        # 카드 간격
        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

def render_news_detail(news_item: Dict):
    """뉴스 상세 페이지 렌더링 (글자 크기 확대 + 자동 스크롤 상단 + 문의처 추가)"""
    
    # 🔧 페이지 상단으로 자동 스크롤 (검증된 방법)
    scroll_js = '''
    <script>
    var body = window.parent.document.querySelector(".main");
    console.log("Scrolling to top...");
    body.scrollTop = 0;
    </script>
    '''
    components.html(scroll_js, height=0)
    
    # 상세 페이지 컨테이너 시작
    st.markdown('<div class="detail-page">', unsafe_allow_html=True)
    
    # 상단 네비게이션
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col1:
        if st.button("⬅️ 뒤로가기", use_container_width=True):
            st.session_state.show_detail = False
            st.session_state.selected_news = None
            st.rerun()
    
    with col3:
        if news_item.get('source_url'):
            st.link_button(
                "🏠 부산시청 원문", 
                news_item['source_url'], 
                use_container_width=True,
                type="primary"
            )
    
    # 제목 (더 큰 글자)
    st.markdown(f'<h1 style="font-size: 36px; line-height: 1.4; margin-bottom: 20px; color: #1F2937;">{news_item["title"]}</h1>', unsafe_allow_html=True)
    
    # 🔧 마크다운 내용에서 문의처 추출
    def extract_contact_from_content(content):
        import re
        patterns = [
            r'.*(?:문의|연락처|담당).*?([가-힣]{2,}(?:과|팀|실|국|본부|센터)).*?(051-[0-9-]+)',
            r'.*☎.*?([0-9-]+)',
            r'.*(051-[0-9-]+)',
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, content)
            if matches:
                if len(matches.groups()) == 2:
                    dept, phone = matches.groups()
                    return f"{dept.strip()} ({phone.strip()})"
                elif len(matches.groups()) == 1:
                    phone = matches.groups()[0]
                    return f"부산시청 ({phone.strip()})"
        
        return "부산시청 (051-888-1234)"
    
    # MD 파일에서 문의처 추출
    contact_info = "부산시청 (051-888-1234)"  # 기본값
    try:
        with open(news_item['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()
        contact_info = extract_contact_from_content(md_content)
    except:
        pass
    
    # 메타 정보 (4열: 게시일, 분야, 문의처, 원문링크)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<p style="font-size: 18px; font-weight: 600;">📅 <strong>게시일</strong>: {news_item["date"]}</p>', unsafe_allow_html=True)
    with col2:
        if news_item['tags']:
            main_tag = news_item['tags'][0]  # 첫 번째 태그만 표시
            st.markdown(f'<p style="font-size: 18px; font-weight: 600;">🏷️ <strong>분야</strong>: #{main_tag}</p>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<p style="font-size: 18px; font-weight: 600;">📞 <strong>문의</strong>: {contact_info}</p>', unsafe_allow_html=True)
    with col4:
        if news_item.get('source_url'):
            st.markdown(f'<p style="font-size: 18px; font-weight: 600;">🔗 <strong><a href="{news_item["source_url"]}" target="_blank" style="color: #0d6efd; text-decoration: none;">부산시청 원문</a></strong></p>', unsafe_allow_html=True)
    
    st.divider()
    
    # MD 파일 내용 표시
    try:
        if 'md_content' not in locals():
            with open(news_item['file_path'], 'r', encoding='utf-8') as f:
                md_content = f.read()
        
        # frontmatter 제거하고 본문만 표시
        if md_content.startswith('---'):
            frontmatter_end = md_content.find('---', 3)
            if frontmatter_end > 0:
                md_content = md_content[frontmatter_end + 3:].strip()
        
        # 마크다운 내용 표시 (큰 글자로)
        st.markdown(md_content)
        
    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다: {e}")
    
    # 상세 페이지 컨테이너 종료
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 하단 액션 버튼들
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⬅️ 목록으로 돌아가기", use_container_width=True):
            st.session_state.show_detail = False
            st.session_state.selected_news = None
            st.rerun()
    
    with col2:
        if news_item.get('source_url'):
            st.link_button(
                "🏠 부산시청 원문으로 이동", 
                news_item['source_url'], 
                use_container_width=True,
                type="primary"
            )

def render_news_grid_with_scroll(news_list: List[Dict]):
    """🔧 스크롤 방식 뉴스 그리드 (4열)"""
    if not news_list:
        st.info("🔍 조건에 맞는 보도자료가 없습니다.")
        return
    
    # 세션 상태에서 표시할 아이템 수 관리
    if 'items_to_show' not in st.session_state:
        st.session_state.items_to_show = 12  # 4x3 = 12개
    
    # 결과 정보
    st.success(f"📊 총 **{len(news_list)}개**의 보도자료")
    
    # 현재 표시할 뉴스들
    current_news = news_list[:st.session_state.items_to_show]
    
    # 4열 그리드로 뉴스 카드 표시
    for i in range(0, len(current_news), 4):  # 4개씩
        cols = st.columns(4, gap="small")
        
        # 각 행의 4개 카드를 동시에 렌더링
        for j in range(4):
            if i + j < len(current_news):
                with cols[j]:
                    render_news_card_aligned(current_news[i + j])
            else:
                # 빈 슬롯에는 투명한 플레이스홀더
                with cols[j]:
                    st.markdown(
                        """
                        <div style="height: 400px; visibility: hidden;"></div>
                        """, 
                        unsafe_allow_html=True
                    )
    
    # 더 보기 버튼 (남은 아이템이 있을 때만)
    if st.session_state.items_to_show < len(news_list):
        remaining = len(news_list) - st.session_state.items_to_show
        
        # 가운데 정렬을 위한 컬럼
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(f"📄 더 보기 ({remaining}개 남음)", use_container_width=True, type="primary"):
                st.session_state.items_to_show += 12  # 12개씩 추가 로드
                st.rerun()

def main():
    """메인 앱 실행"""
    # 세션 상태 초기화
    if 'show_detail' not in st.session_state:
        st.session_state.show_detail = False
    if 'selected_news' not in st.session_state:
        st.session_state.selected_news = None
    
    try:
        # 포털 인스턴스 생성
        portal = BusanNewsPortal()
        
        # 상세 페이지 표시 여부 확인
        if st.session_state.show_detail and st.session_state.selected_news:
            render_news_detail(st.session_state.selected_news)
        else:
            # 메인 페이지에서만 헤더 표시
            render_header()
            
            # 사이드바 렌더링
            search_query, selected_tags, date_range = render_sidebar(portal)
            
            # 뉴스 필터링
            filtered_news = portal.filter_news(selected_tags, search_query, date_range)
            
            # 메인 콘텐츠 렌더링
            if portal.news_data:
                render_news_grid_with_scroll(filtered_news)
            else:
                st.info("""
                📢 **포털 사용 방법**
                
                1. **데이터 생성**: `python local_main.py --test` 실행
                2. **포털 확인**: 브라우저 새로고침  
                3. **검색 및 필터**: 사이드바에서 원하는 조건 선택
                """)
                
                # 환경 정보 표시
                env_info = get_env_info()
                st.write(f"**환경 정보**: {env_info['environment']}")
                
    except Exception as e:
        st.error(f"❌ 앱 실행 중 오류: {e}")
        st.info("**해결 방법**: `python local_main.py --test`로 테스트 데이터를 먼저 생성해주세요.")

if __name__ == "__main__":
    main()