"""
부산시청 정보포털 - Streamlit 앱 (보도자료 + 맛집정보 + 업무계획)
=================================================================
태그 색상 기반 카드형 UI로 보도자료, 맛집정보, 업무계획을 쉽게 검색하고 확인할 수 있는 통합 포털

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
    AVAILABLE_RESTAURANT_REGIONS, RESTAURANT_FOOD_TYPES, AVAILABLE_RESTAURANT_CATEGORIES,
    RESTAURANT_REGION_COLORS, RESTAURANT_FOOD_TYPE_COLORS, RESTAURANT_CATEGORY_COLORS,
    IS_LOCAL, get_env_info, MESSAGES
)
from plans_portal import BusanPlansPortal
from restaurant_portal import BusanRestaurantPortal, get_restaurant_portal_stats
from styles import apply_all_styles  # 🔧 CSS 모듈 import

# 페이지 설정
st.set_page_config(
    page_title="요즘 부산",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔧 CSS 스타일 적용 (기존 길었던 CSS 코드가 한 줄로!)
apply_all_styles()

# 🔧 추가 CSS - 사이드바 버튼 보라색 스타일
st.markdown("""
<style>
.stSidebar button[kind="primary"] {
    background-color: #8B5CF6 !important;
    border-color: #8B5CF6 !important;
    color: white !important;
}

.stSidebar button[kind="primary"]:hover {
    background-color: #7C3AED !important;
    border-color: #7C3AED !important;
}

.stSidebar button[kind="secondary"] {
    background-color: #E5E7EB !important;
    border-color: #D1D5DB !important;
    color: #374151 !important;
}

.stSidebar button[kind="secondary"]:hover {
    background-color: #D1D5DB !important;
    border-color: #9CA3AF !important;
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
    """🔧 헤더 렌더링 (3개 탭 네비게이션 포함)"""
    # 왼쪽 제목 영역보다 오른쪽 네비 영역에 더 많은 공간 할당
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.title("🏢 요즘 부산")
    
    with col2:
        # 🔧 3개 탭 스타일 네비게이션
        current_page = st.session_state.get('page', 'news')
        
        # 3개 컬럼으로 탭 버튼 배치
        tab_col1, tab_col2, tab_col3 = st.columns(3)
        
        with tab_col1:
            if st.button("📰 보도자료", key="nav_news", use_container_width=True, 
                        type="primary" if current_page == 'news' else "secondary"):
                st.session_state.page = 'news'
                st.session_state.items_to_show = 12
                st.rerun()
        
        with tab_col2:
            if st.button("🍽️ 맛집정보", key="nav_restaurants", use_container_width=True,
                        type="primary" if current_page == 'restaurants' else "secondary"):
                st.session_state.page = 'restaurants'
                st.session_state.restaurant_items_to_show = 12
                st.rerun()
        
        with tab_col3:
            if st.button("📋 업무계획", key="nav_plans", use_container_width=True,
                        type="primary" if current_page == 'plans' else "secondary"):
                st.session_state.page = 'plans'
                st.session_state.plans_items_to_show = 12
                st.rerun()
    
    # 🔧 페이지별 설명과 이용 방법
    current_page = st.session_state.get('page', 'news')
    if current_page == 'news':
        st.markdown("### 부산시 최신 보도자료를 알려드립니다")
        
        st.info("""
        **📖 이용 방법**
        - 왼쪽 사이드바에서 **분야를 선택**하면 해당 분야의 보도자료를 확인할 수 있습니다
        - **검색어**를 입력하여 원하는 내용을 빠르게 찾아보세요 **(검색어 모두 지우신 후 엔터 치면 전체보기 가능)**
        - 각 카드를 클릭하면 **상세 내용**을 볼 수 있습니다 (보도자료 원문 링크 포함)
        - (주의) AI 요약이라 세부내용, 부서 연락처 오류가 있을 수 있으니 정확한 정보는 원문링크 참고하세요!
        """)
    elif current_page == 'restaurants':
        st.markdown("### 부산 맛집 정보를 확인하세요")
        
        st.info("""
        **🍽️ 이용 방법**
        - 왼쪽 사이드바에서 **지역, 음식종류, 카테고리**를 선택하여 원하는 맛집을 찾아보세요
        - **미슐랭 가이드** 맛집도 포함되어 있습니다 (⭐1스타, 🍽️빕구르망, ✨셀렉티드)
        - **검색어**를 입력하여 맛집명이나 메뉴를 빠르게 찾아보세요
        - 각 카드를 클릭하면 **상세 정보**를 볼 수 있습니다 (주소, 전화번호, 영업시간 등)
        """)
    else:
        st.markdown("### 2025년 부산시 각 부서별 주요 업무계획을 확인하세요")
        
        # 업무계획용 이용 방법
        st.info("""
        **📋 이용 방법**
        - 왼쪽 사이드바에서 **부서별 분류**를 선택하여 원하는 분야의 업무계획을 확인할 수 있습니다
        - **검색어**를 입력하여 특정 부서나 사업명을 빠르게 찾아보세요
        - 각 카드를 클릭하면 **상세 업무계획**을 볼 수 있습니다 (기본현황, 추진과제, 예산 등)
        - (주의) AI 요약이라 세부내용 오류가 있을 수 있으니 정확한 정보는 원문링크 참고하세요!
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
    
    # 🔧 1열로 버튼 배치 (기존 2열에서 변경)
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

def render_restaurant_sidebar(restaurant_portal: BusanRestaurantPortal):
    """🔧 맛집정보 전용 사이드바"""
    st.sidebar.header("🍽️ 맛집 필터")
    
    # 🔧 세션 변수 초기화 (함수 최상단에 추가)
    if 'selected_restaurant_category' not in st.session_state:
        st.session_state.selected_restaurant_category = "전체"
    if 'selected_restaurant_region' not in st.session_state:
        st.session_state.selected_restaurant_region = "전체"
    if 'selected_restaurant_food_type' not in st.session_state:
        st.session_state.selected_restaurant_food_type = "전체"
    
    # 검색어 입력
    search_query = st.sidebar.text_input(
        "🔎 검색어",
        placeholder="맛집명, 지역, 음식종류 검색",
        help="맛집명, 지역, 음식종류, 메뉴에서 검색합니다.",
        key="restaurant_search_input"
    )
    
    # 🔧 1. 카테고리별 필터 (제일 상단) - 1열 배치
    st.sidebar.subheader("⭐ 카테고리")
    category_stats = restaurant_portal.get_category_stats()
    
    # 전체 버튼 (전체 너비)
    is_selected = st.session_state.selected_restaurant_category == "전체"
    button_type = "primary" if is_selected else "secondary"
    
    if st.sidebar.button(
        f"🏠 전체 ({category_stats.get('전체', 0)}개)", 
        key="restaurant_category_all",
        use_container_width=True,
        type=button_type
    ):
        st.session_state.selected_restaurant_category = "전체"
        st.session_state.restaurant_items_to_show = 12
        st.rerun()
    
    # 나머지 카테고리 버튼들 (1열 배치)
    other_categories = [cat for cat in AVAILABLE_RESTAURANT_CATEGORIES if cat != "전체"]
    for category in other_categories:
        count = category_stats.get(category, 0)
        is_selected = st.session_state.selected_restaurant_category == category
        button_type = "primary" if is_selected else "secondary"
        
        emoji = ""
        if category == "미쉐린가이드":
            emoji = "⭐"
        elif category == "부산의맛":
            emoji = "🍽️"
        elif category == "현지인":
            emoji = "👥"
        
        if st.sidebar.button(
            f"{emoji} {category} ({count}개)", 
            key=f"restaurant_category_{category.replace(' ', '_')}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_restaurant_category = category
            st.session_state.restaurant_items_to_show = 12
            st.rerun()
    
    # 🔧 2. 지역별 필터 - 4개 권역 버튼 (1열 배치)
    st.sidebar.subheader("🗺️ 지역별")
    region_stats = restaurant_portal.get_region_stats()
    
    # 전체 버튼 (전체 너비)
    is_selected = st.session_state.selected_restaurant_region == "전체"
    button_type = "primary" if is_selected else "secondary"
    
    if st.sidebar.button(
        f"🏠 전체 ({region_stats.get('전체', 0)}개)", 
        key="restaurant_region_all",
        use_container_width=True,
        type=button_type
    ):
        st.session_state.selected_restaurant_region = "전체"
        st.session_state.restaurant_items_to_show = 12
        st.rerun()
    
    # 🔧 4개 권역 버튼 (구 이름만 표시, 이모지 제거)
    regions_display = [
        ("원도심권", "중구 동구 영도구 서구"),
        ("동부산권", "해운대구 수영구 남구 기장군"),
        ("서부산권", "사하구 강서구 사상구"),
        ("북부산권", "북구 금정구 동래구 연제구 부산진구")
    ]
    
    for region_key, district_names in regions_display:
        is_selected = st.session_state.selected_restaurant_region == region_key
        button_type = "primary" if is_selected else "secondary"
        
        if st.sidebar.button(
            f"{district_names}", 
            key=f"restaurant_region_{region_key}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_restaurant_region = region_key
            st.session_state.restaurant_items_to_show = 12
            st.rerun()
    
    # 🔧 3. 음식종류별 필터 - 전체 1줄, 나머지 2줄 배치 (들여쓰기 수정)
    st.sidebar.subheader("🍜 음식종류")
    food_type_stats = restaurant_portal.get_food_type_stats()

    # 1) 전체 버튼: 한 줄 꽉 채우기
    is_selected = st.session_state.selected_restaurant_food_type == "전체"
    button_type = "primary" if is_selected else "secondary"
    if st.sidebar.button(
        f"🏠 전체 ({food_type_stats.get('전체', 0)}개)",
        key="restaurant_food_all",
        use_container_width=True,
        type=button_type
    ):
        st.session_state.selected_restaurant_food_type = "전체"
        st.session_state.restaurant_items_to_show = 12
        st.rerun()

    # 2) 나머지 음식종류: 2열로 묶어서 반복
    other_food_types = [ft for ft in RESTAURANT_FOOD_TYPES if ft != "전체"]
    for i in range(0, len(other_food_types), 2):
        cols = st.sidebar.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(other_food_types):
                ft = other_food_types[idx]
                count = food_type_stats.get(ft, 0)
                is_sel = st.session_state.selected_restaurant_food_type == ft
                btn_type = "primary" if is_sel else "secondary"
                if col.button(
                    f"{ft} ({count}개)",
                    key=f"food_{ft.replace(' ', '_')}",
                    use_container_width=True,
                    type=btn_type
                ):
                    st.session_state.selected_restaurant_food_type = ft
                    st.session_state.restaurant_items_to_show = 12
                    st.rerun()
    
    # 통계 정보
    st.sidebar.divider()
    st.sidebar.subheader("📊 선택된 필터")
    
    total_count = len(restaurant_portal.restaurants_data)
    
    # 현재 필터 상태 표시
    current_filters = []
    if st.session_state.selected_restaurant_region != "전체":
        current_filters.append(f"지역: {st.session_state.selected_restaurant_region}")
    if st.session_state.selected_restaurant_food_type != "전체":
        current_filters.append(f"음식: {st.session_state.selected_restaurant_food_type}")
    if st.session_state.selected_restaurant_category != "전체":
        current_filters.append(f"카테고리: {st.session_state.selected_restaurant_category}")
    
    if current_filters:
        for filter_text in current_filters:
            st.sidebar.info(f"🔍 {filter_text}")
    else:
        st.sidebar.success(f"🏠 **전체 맛집**: {total_count}개")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("전체", total_count)
    with col2:
        michelin_count = len([r for r in restaurant_portal.restaurants_data if r.get('category') == '미쉐린가이드'])
        st.metric("미슐랭", michelin_count)
    
    # 선택된 필터 반환
    selected_regions = [st.session_state.selected_restaurant_region] if st.session_state.selected_restaurant_region != "전체" else ["전체"]
    selected_food_types = [st.session_state.selected_restaurant_food_type] if st.session_state.selected_restaurant_food_type != "전체" else ["전체"]
    selected_categories = [st.session_state.selected_restaurant_category] if st.session_state.selected_restaurant_category != "전체" else ["전체"]
    
    return search_query, selected_regions, selected_food_types, selected_categories

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
    
    # 🔧 1열로 버튼 배치 (기존 2열에서 변경)
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

def get_responsive_columns():
    """화면 크기에 따른 컬럼 수 결정"""
    return 4  # 기본 4열, CSS에서 반응형으로 조정

def render_news_card_aligned(news_item: Dict):
    """보도자료 카드 렌더링 (반응형 개선)"""
    with st.container():
        # 태그와 날짜를 한 줄에 배치
        if news_item['tags']:
            main_tag = news_item['tags'][0]
            tag_color = TAG_COLORS.get(main_tag, "#6B7280")
        else:
            main_tag = "전체"
            tag_color = "#6B7280"
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 8px;">
            <div style="
                background-color: {tag_color}; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 12px; 
                font-size: 16px; 
                font-weight: bold;
                flex-shrink: 0;
            ">
                🏷️ #{main_tag}
            </div>
            <div style="
                background-color: #6b7280; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 12px; 
                font-size: 16px; 
                font-weight: bold;
                border: 1px solid #9ca3af;
                flex-shrink: 0;
            ">
                📅 {news_item['date']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
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
            <div class="news-title-box" style="
                background-color: {pastel_color};
                color: #000000;
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
                    font-size: 22px; 
                    font-weight: bold; 
                    color: #000000;
                    line-height: 1.4;
                    text-align: center;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100%;
                ">
                    <span style="display: block; width: 100%; color: #000000;">{formatted_title}</span>
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
            <div class="news-summary" style="
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
        
        # 클릭 버튼
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

def render_restaurant_card(restaurant_item: Dict):
    """🔧 맛집 카드 렌더링 (미슐랭 등급 포함)"""
    with st.container():
        # 지역과 카테고리를 한 줄에 배치
        region = restaurant_item.get('region', '기타')
        district = restaurant_item.get('district', '')
        category = restaurant_item.get('category', '현지인')
        food_type = restaurant_item.get('food_type', '한식')
        michelin_grade = restaurant_item.get('michelin_grade', '')
        
        region_color = RESTAURANT_REGION_COLORS.get(region, "#6B7280")
        # 🔧 미슐랭가이드 주황색으로 변경
        if category == "미쉐린가이드":
            category_color = "#FF8C00"  # 주황색
        else:
            category_color = RESTAURANT_CATEGORY_COLORS.get(category, "#6B7280")
        
        # 미슐랭 등급 이모지
        michelin_emoji = ""
        if michelin_grade:
            if michelin_grade == "1스타":
                michelin_emoji = " ⭐"
            elif michelin_grade == "빕구르망":
                michelin_emoji = " 🍽️"
            elif michelin_grade == "셀렉티드":
                michelin_emoji = " ✨"
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 8px;">
            <div style="
                background-color: {region_color}; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 12px; 
                font-size: 16px; 
                font-weight: bold;
                flex-shrink: 0;
            ">
                🗺️ {district}
            </div>
            <div style="
                background-color: {category_color}; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 12px; 
                font-size: 16px; 
                font-weight: bold;
                flex-shrink: 0;
            ">
                ⭐ {category}{michelin_emoji}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 카테고리별 파스텔 색상 매핑 - 미슐랭가이드 주황색으로 변경
        pastel_colors = {
            "#6B7280": "#E5E7EB",   # 현지인 - 회색
            "#FF8C00": "#FFE4B5",   # 미쉐린가이드 - 주황색 (변경)
            "#EF4444": "#FEE2E2",   # 부산의맛 - 빨간색
            "#10B981": "#D1FAE5",   # 기타 - 초록색
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
        
        formatted_title = smart_line_break(restaurant_item['title'])
        
        # 제목 박스
        st.markdown(
            f"""
            <div class="news-title-box" style="
                background-color: {pastel_color};
                color: #000000;
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
                    font-size: 22px; 
                    font-weight: bold; 
                    color: #000000;
                    line-height: 1.4;
                    text-align: center;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100%;
                ">
                    <span style="display: block; width: 100%; color: #000000;">{formatted_title}</span>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # 🔧 요약정보에 MD 파일의 상세정보 표시 (높이 반으로 줄임)
        summary_text = ""
        try:
            # MD 파일에서 상세정보 추출
            with open(restaurant_item['file_path'], 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # "## 📝 상세 정보" 섹션 찾기
            import re
            detail_match = re.search(r'## 📝 상세 정보\s*\n\n(.+?)(?=\n---|\n##|\n$)', md_content, re.DOTALL)
            if detail_match:
                detail_text = detail_match.group(1).strip()
                # 길이 제한
                if len(detail_text) > 120:
                    detail_text = detail_text[:120] + "..."
                summary_text = detail_text
            else:
                # 대체 텍스트
                summary_text = f"🍜 {food_type} 전문점"
        except:
            summary_text = f"🍜 {food_type} 전문점"
        
        st.markdown(
            f"""
            <div class="news-summary" style="
                margin: 0rem 0 0.5rem 0;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #dee2e6;
                line-height: 1.6;
                height: 80px;
                overflow: visible;
                word-wrap: break-word;
                display: flex;
                align-items: flex-start;
                justify-content: flex-start;
                font-size: 14px;
                color: #495057;
                text-align: left;
                padding-top: 10px;
            ">
                {summary_text}
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # 클릭 버튼
        if st.button(
            "🍽️ 클릭하여 맛집 보기",
            key=f"restaurant_detail_btn_{hash(restaurant_item['file_path'])}",
            use_container_width=True,
        ):
            st.session_state.selected_restaurant = restaurant_item
            st.session_state.show_restaurant_detail = True
            st.session_state.scroll_to_top = True
            st.rerun()
        
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

def render_plans_card(plan_item: Dict):
    """업무계획 카드 렌더링 (반응형 개선)"""
    with st.container():
        # 부서명과 분류를 한 줄에 배치
        department = plan_item.get('department', '미분류')
        category = plan_item.get('tags', ['전체'])[0] if plan_item.get('tags') else '전체'
        category_color = PLAN_TAG_COLORS.get(category, "#6B7280")
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 8px;">
            <div style="
                background-color: #4A148C; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 12px; 
                font-size: 16px; 
                font-weight: bold;
                flex-shrink: 0;
            ">
                🏛️ {department}
            </div>
            <div style="
                background-color: {category_color}; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 12px; 
                font-size: 16px; 
                font-weight: bold;
                flex-shrink: 0;
            ">
                📋 {category}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
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
            <div class="news-title-box" style="
                background-color: {pastel_color};
                color: #000000;
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
                    font-size: 22px; 
                    font-weight: bold; 
                    color: #000000;
                    line-height: 1.4;
                    text-align: center;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100%;
                ">
                    <span style="display: block; width: 100%; color: #000000;">{formatted_title}</span>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # 요약 텍스트
        summary = plan_item.get('thumbnail_summary', '')
        if not summary:
            summary = "2025년 주요업무계획"
        
        st.markdown(
            f"""
            <div class="news-summary" style="
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
        
        # 클릭 버튼
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
    """보도자료 그리드 렌더링 (반응형 개선)"""
    if not news_list:
        st.info("🔍 조건에 맞는 보도자료가 없습니다.")
        return
    
    if 'items_to_show' not in st.session_state:
        st.session_state.items_to_show = 12
    
    current_news = news_list[:st.session_state.items_to_show]
    
    # 반응형 그리드 - 기본 4열, CSS에서 자동 조정
    cols_per_row = get_responsive_columns()
    
    for i in range(0, len(current_news), cols_per_row):
        cols = st.columns(cols_per_row, gap="small")
        
        for j in range(cols_per_row):
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

def render_restaurant_grid_with_scroll(restaurant_list: List[Dict]):
    """🔧 맛집 그리드 렌더링 (반응형 개선)"""
    if not restaurant_list:
        st.info("🔍 조건에 맞는 맛집이 없습니다.")
        return
    
    if 'restaurant_items_to_show' not in st.session_state:
        st.session_state.restaurant_items_to_show = 12
    
    current_restaurants = restaurant_list[:st.session_state.restaurant_items_to_show]
    
    # 반응형 그리드 - 기본 4열, CSS에서 자동 조정
    cols_per_row = get_responsive_columns()
    
    for i in range(0, len(current_restaurants), cols_per_row):
        cols = st.columns(cols_per_row, gap="small")
        
        for j in range(cols_per_row):
            if i + j < len(current_restaurants):
                with cols[j]:
                    render_restaurant_card(current_restaurants[i + j])
            else:
                with cols[j]:
                    st.markdown("<div style='height: 400px; visibility: hidden;'></div>", unsafe_allow_html=True)
    
    # 더 보기 버튼
    if st.session_state.restaurant_items_to_show < len(restaurant_list):
        remaining = len(restaurant_list) - st.session_state.restaurant_items_to_show
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(f"🍽️ 더 보기 ({remaining}개 남음)", use_container_width=True, type="primary", key="restaurant_load_more"):
                st.session_state.restaurant_items_to_show += 12
                st.rerun()

def render_plans_grid_with_scroll(plans_list: List[Dict]):
    """업무계획 그리드 렌더링 (반응형 개선)"""
    if not plans_list:
        st.info("🔍 조건에 맞는 업무계획이 없습니다.")
        return
    
    if 'plans_items_to_show' not in st.session_state:
        st.session_state.plans_items_to_show = 12
    
    current_plans = plans_list[:st.session_state.plans_items_to_show]
    
    # 반응형 그리드 - 기본 4열, CSS에서 자동 조정
    cols_per_row = get_responsive_columns()
    
    for i in range(0, len(current_plans), cols_per_row):
        cols = st.columns(cols_per_row, gap="small")
        
        for j in range(cols_per_row):
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
    
    # 상단 네비게이션 버튼 (뒤로가기만)
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        if st.button("← 뒤로가기", key="news_back_top", use_container_width=True, type="secondary"):
            st.session_state.show_detail = False
            st.session_state.selected_news = None
            st.rerun()
        
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
                f'<p style="font-size: 18px;"><strong>🔗 <a href="{news_item["source_url"]}" target="_blank" style="color: #white; text-decoration: none;">부산시청 원문</a></strong></p>',
                unsafe_allow_html=True
            )
    
    st.divider()
    
    # 🔧 MD 파일 내용 표시 - 글자 크기 20px 적용
    try:
        with open(news_item['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()
    
        if md_content.startswith('---'):
            frontmatter_end = md_content.find('---', 3)
            if frontmatter_end > 0:
                md_content = md_content[frontmatter_end + 3:].strip()
    
        st.markdown(f'<div style="font-size: 20px; line-height: 1.8;">{md_content}</div>', unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다: {e}")
    
    st.divider()
    
    # 하단 버튼 (목록으로 돌아가기만, 가로 길이 늘림)
    if st.button("⬅️ 목록으로 돌아가기", use_container_width=True, key="news_back_btn2"):
        st.session_state.show_detail = False
        st.session_state.selected_news = None
        st.rerun()

def render_restaurant_detail(restaurant_item: Dict):
    """🔧 맛집 상세 페이지 - 폰트 크기 조정 (기존 + 6px)"""
    if st.session_state.get('scroll_to_top'):
        scroll_to_here(0, key='restaurant_detail_top')
        st.session_state.scroll_to_top = False
    
    # 상단 네비게이션 버튼 (뒤로가기만)
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        if st.button("← 뒤로가기", key="restaurant_back_top", use_container_width=True, type="secondary"):
            st.session_state.show_restaurant_detail = False
            st.session_state.selected_restaurant = None
            st.rerun()
    
    # 제목 (42px = 36px + 6px)
    title = restaurant_item["title"]
    st.markdown('<div class="detail-page">', unsafe_allow_html=True)
    st.markdown(f'<h1 style="color: white; font-size: 42px; margin-bottom: 30px;">{title}</h1>', unsafe_allow_html=True)
    
    # MD 파일 내용 가져오기
    try:
        with open(restaurant_item['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # 🔧 이용안내 섹션에서 정보 추출 (frontmatter 대신)
        import re
        
        # 이용안내 섹션 추출
        usage_section = re.search(r'## 📍 이용안내\s*\n(.*?)(?=\n##|\n---|\n$)', md_content, re.DOTALL)
        
        phone = address = hours = closed_days = michelin_grade = representative_menu = ""
        
        if usage_section:
            usage_content = usage_section.group(1)
            
            # 각 정보 추출
            phone_match = re.search(r'\*\*전화번호\*\*:\s*(.+)', usage_content)
            address_match = re.search(r'\*\*주소\*\*:\s*(.+)', usage_content)
            hours_match = re.search(r'\*\*영업시간\*\*:\s*(.+)', usage_content)
            closed_match = re.search(r'\*\*휴무일\*\*:\s*(.+)', usage_content)
            michelin_match = re.search(r'\*\*미쉐린 등급\*\*:\s*(.+)', usage_content)
            menu_match = re.search(r'\*\*대표 메뉴\*\*\s*\n(.+?)(?=\n\n|\*\*|$)', usage_content, re.DOTALL)
            
            if phone_match:
                phone = phone_match.group(1).strip()
            if address_match:
                address = address_match.group(1).strip()
            if hours_match:
                hours = hours_match.group(1).strip()
            if closed_match:
                closed_days = closed_match.group(1).strip()
            if michelin_match:
                michelin_grade = michelin_match.group(1).strip().replace('⭐', '').strip()
            if menu_match:
                representative_menu = menu_match.group(1).strip()
        
        # frontmatter에서 보완 정보 추출
        frontmatter_match = re.search(r'---\s*\n(.*?)\n---', md_content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            if not michelin_grade:
                michelin_fm = re.search(r'michelin_grade:\s*(.+)', frontmatter)
                if michelin_fm:
                    michelin_grade = michelin_fm.group(1).strip().strip("'\"")
        
        # 1. 미슐랭 등급 (38px = 32px + 6px)
        if michelin_grade:
            grade_emoji = {"1스타": "🌟", "빕구르망": "🍽️", "셀렉티드": "✨"}.get(michelin_grade, "⭐")
            st.markdown(f"""
            <h2 style="color: #FFD700; font-size: 38px; margin: 30px 0 20px 0;">
                {grade_emoji} 미슐랭 등급: {michelin_grade}
            </h2>
            """, unsafe_allow_html=True)
        
        # 2. 상세정보 (30px = 24px + 6px, 34px = 28px + 6px, 26px = 20px + 6px)
        st.markdown(f"""
        <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
            <h3 style="color: #8B5CF6; font-size: 34px; margin-bottom: 20px;">📍 상세정보</h3>
            <div style="font-family: monospace; margin-left: 20px; font-size: 26px;">
                📍 상세정보<br>
                ├─ 📍 주소: {address or '정보 없음'}<br>
                ├─ 📞 전화번호: {phone or '정보 없음'}<br>
                ├─ 🕐 영업시간: {hours or '정보 없음'}<br>
                └─ 🚫 휴무일: {closed_days or '정보 없음'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. 대표메뉴 (30px = 24px + 6px, 34px = 28px + 6px, 26px = 20px + 6px)
        if representative_menu:
            st.markdown(f"""
            <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
                <h3 style="color: #10B981; font-size: 34px; margin-bottom: 15px;">🍽️ 대표메뉴</h3>
                <div style="margin-left: 20px; font-size: 26px;">
                    {representative_menu}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # 4. 상세정보 (원래 내용 - "## 📝 상세 정보" 섹션)
        detail_match = re.search(r'## 📝 상세 정보\s*\n\n(.+?)(?=\n---|\n##|\n$)', md_content, re.DOTALL)
        if detail_match:
            detail_content = detail_match.group(1).strip()
            st.markdown(f"""
            <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
                <h3 style="color: #F59E0B; font-size: 34px; margin-bottom: 15px;">📝 상세정보</h3>
                <div style="margin-left: 20px; font-size: 26px; line-height: 1.8;">
                    {detail_content}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # 5. 분류정보 (30px = 24px + 6px, 34px = 28px + 6px, 26px = 20px + 6px)
        region = restaurant_item.get('region', '')
        district = restaurant_item.get('district', '')
        food_type = restaurant_item.get('food_type', '')
        category = restaurant_item.get('category', '')
        
        st.markdown(f"""
        <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
            <h3 style="color: #3B82F6; font-size: 34px; margin-bottom: 15px;">🏷️ 분류정보</h3>
            <div style="margin-left: 20px; font-size: 26px;">
                • <strong>지역:</strong> {region} ({district})<br>
                • <strong>음식 유형:</strong> {food_type}<br>
                • <strong>카테고리:</strong> {category}<br>
                • <strong>미슐랭 등급:</strong> {michelin_grade or '일반'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # MD 파일에서 카카오맵 링크 추출
        kakao_link = ""
        kakao_match = re.search(r'\*\*카카오맵\*\*:\s*\[([^\]]+)\]\(([^)]+)\)', md_content)
        if kakao_match:
            kakao_link = kakao_match.group(2)
        
        # 6. 카카오맵 정보확인 (34px = 28px + 6px, 26px = 20px + 6px, 24px = 18px + 6px)
        st.markdown(f"""
        <div style="
            text-align: center; 
            margin: 40px 0;
            padding: 30px;
            background: linear-gradient(135deg, #1F2937 0%, #111827 100%);
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            border: 2px solid #374151;
        ">
            <h3 style="color: #9CA3AF; font-size: 34px; margin-bottom: 20px;">🗺️ 카카오맵 정보확인</h3>
            <a href="{kakao_link or '#'}" target="_blank" style="
                background: #374151;
                color: white;
                padding: 20px 40px;
                border-radius: 15px;
                text-decoration: none;
                font-size: 26px;
                font-weight: bold;
                display: inline-block;
                box-shadow: 0 4px 8px rgba(0,0,0,0.4);
                transition: all 0.3s ease;
                border: 2px solid #4B5563;
            " onmouseover="this.style.background='#4B5563'" onmouseout="this.style.background='#374151'">
                🗺️ 카카오맵 확인
            </a>
            <p style="font-size: 24px; color: #9CA3AF; margin-top: 20px; line-height: 1.6;">
                * 식당의 정확한 위치와 고객 후기는 카카오맵에서 확인하실 수 있습니다
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
    
    if st.button("⬅️ 목록으로 돌아가기", use_container_width=True, key="restaurant_back_btn2"):
        st.session_state.show_restaurant_detail = False
        st.session_state.selected_restaurant = None
        st.rerun()

def render_plans_detail(plan_item: Dict):
    """업무계획 상세 페이지"""
    if st.session_state.get('scroll_to_top'):
        scroll_to_here(0, key='plans_detail_top')
        st.session_state.scroll_to_top = False
    
    # 상단 네비게이션 버튼 (뒤로가기만)
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        if st.button("← 뒤로가기", key="plans_back_top", use_container_width=True, type="secondary"):
            st.session_state.show_plan_detail = False
            st.session_state.selected_plan = None
            st.rerun()
    
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
            f'<p style="font-size: 18px;"><strong>🔗 <a href="https://www.busan.go.kr/gbplan" target="_blank" style="color: #white; text-decoration: none;">부산시청 원문</a></strong></p>',
            unsafe_allow_html=True
        )
    
    st.divider()
    
    # 🔧 MD 파일 내용 표시 - 글자 크기 20px 적용
    try:
        with open(plan_item['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        if md_content.startswith('---'):
            frontmatter_end = md_content.find('---', 3)
            if frontmatter_end > 0:
                md_content = md_content[frontmatter_end + 3:].strip()
        
        st.markdown(f'<div style="font-size: 20px; line-height: 1.8;">{md_content}</div>', unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    if st.button("⬅️ 목록으로 돌아가기", use_container_width=True, key="plans_back_btn2"):
        st.session_state.show_plan_detail = False
        st.session_state.selected_plan = None
        st.rerun()

def main():
    """🔧 메인 앱 실행 (3페이지 통합)"""
    # 세션 상태 초기화
    if 'show_detail' not in st.session_state:
        st.session_state.show_detail = False
    if 'selected_news' not in st.session_state:
        st.session_state.selected_news = None
    if 'show_restaurant_detail' not in st.session_state:
        st.session_state.show_restaurant_detail = False
    if 'selected_restaurant' not in st.session_state:
        st.session_state.selected_restaurant = None
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
        elif st.session_state.show_restaurant_detail and st.session_state.selected_restaurant:
            render_restaurant_detail(st.session_state.selected_restaurant)
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
                    
            elif st.session_state.page == 'restaurants':
                # 🔧 맛집정보 페이지
                restaurant_portal = BusanRestaurantPortal()
                search_query, selected_regions, selected_food_types, selected_categories = render_restaurant_sidebar(restaurant_portal)
                filtered_restaurants = restaurant_portal.filter_restaurants(
                    selected_regions, selected_food_types, selected_categories, search_query
                )
                
                # 🔧 미슐랭 맛집 우선 정렬 적용
                def sort_restaurants_michelin_first(restaurants):
                    """미슐랭 맛집을 맨 앞으로 정렬"""
                    michelin_restaurants = [r for r in restaurants if r.get('category') == '미쉐린가이드']
                    other_restaurants = [r for r in restaurants if r.get('category') != '미쉐린가이드']
                    return michelin_restaurants + other_restaurants
                
                # 미슐랭 우선 정렬 적용
                filtered_restaurants = sort_restaurants_michelin_first(filtered_restaurants)
                
                if restaurant_portal.restaurants_data:
                    render_restaurant_grid_with_scroll(filtered_restaurants)
                else:
                    st.info("🍽️ 맛집 데이터를 로드하는 중입니다...")
                    
            elif st.session_state.page == 'plans':
                # 업무계획 페이지
                plans_portal = BusanPlansPortal()
                search_query, selected_categories = render_plans_sidebar(plans_portal)
                filtered_plans = plans_portal.filter_plans(selected_categories, search_query)
                
                if plans_portal.plans_data:
                    render_plans_grid_with_scroll(filtered_plans)
                else:
                    st.info("📋 업무계획 데이터를 로드하는 중입니다...")
            
            # 제작자 정보 (공통) - 🔧 하단 배경을 검은색으로 수정
            st.markdown(
                """
                <div style="
                    text-align: center; 
                    margin: 20px 0; 
                    padding: 15px; 
                    background-color: #000000;
                    border-radius: 10px;
                ">
                    <p style="margin: 0; color: white !important; font-size: 14px;">
                        🏛️ <strong style="color: white !important;">Made by 부산시청 매니저</strong> | 
                        ⭐ <strong style="color: white !important;">즐겨찾기: Ctrl+D (Windows) / Cmd+D (Mac)</strong> | 
                        🌐 <strong style="color: white !important;"><a href="https://www.busan.go.kr" target="_blank" style="color: #0d6efd !important; text-decoration: none;">부산시청 바로가기</a></strong>
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