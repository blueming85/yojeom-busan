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
from styles import apply_all_styles
from detail_pages import (
    render_header, render_news_detail, render_restaurant_detail, render_plans_detail,
    render_news_grid_with_scroll, render_restaurant_grid_with_scroll, render_plans_grid_with_scroll,
    extract_contact_from_content
)

# 페이지 설정
st.set_page_config(
    page_title="요즘 부산",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 적용
apply_all_styles()

# 추가 CSS - 사이드바 버튼 보라색 스타일
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
    
    # 1열로 버튼 배치
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
    """맛집정보 전용 사이드바"""
    st.sidebar.header("🍽️ 맛집 필터")
    
    # 세션 변수 초기화
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
    
    # 1. 카테고리별 필터 (제일 상단) - 1열 배치
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
    
    # 2. 지역별 필터 - 4개 권역 버튼 (1열 배치)
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
    
    # 4개 권역 버튼: 2열로 묶어서 배치
    regions_display = [
        ("원도심권", "중구 동구 영도구\n서구"),
        ("동부산권", "해운대구 수영구\n남구 기장군"),
        ("서부산권", "사하구 강서구\n사상구"),
        ("북부산권", "북구 금정구 동래구 연제구 부산진구")
    ]
    for i in range(0, len(regions_display), 2):
        cols = st.sidebar.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(regions_display):
                region_key, district_names = regions_display[idx]
                is_sel = st.session_state.selected_restaurant_region == region_key
                btn_type = "primary" if is_sel else "secondary"
                if col.button(
                    f"{district_names}",
                    key=f"restaurant_region_{region_key}",
                    use_container_width=True,
                    type=btn_type
                ):
                    st.session_state.selected_restaurant_region = region_key
                    st.session_state.restaurant_items_to_show = 12
                    st.rerun()
    
    # 3. 음식종류별 필터 - 전체 1줄, 나머지 2줄 배치
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
    
    # 1열로 버튼 배치
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

def main():
    """메인 앱 실행 (3페이지 통합)"""
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
                # 맛집정보 페이지
                restaurant_portal = BusanRestaurantPortal()
                search_query, selected_regions, selected_food_types, selected_categories = render_restaurant_sidebar(restaurant_portal)
                filtered_restaurants = restaurant_portal.filter_restaurants(
                    selected_regions, selected_food_types, selected_categories, search_query
                )
                
                # 미슐랭 맛집 우선 정렬 적용
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
            
            # 제작자 정보 (공통) - 하단 배경을 검은색으로 수정
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