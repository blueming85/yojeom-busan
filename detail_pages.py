"""
부산시청 정보포털 - UI 컴포넌트 및 상세 페이지 모듈
===============================================
헤더, 카드, 그리드, 상세 페이지 등 모든 UI 렌더링 함수들을 관리
"""

import streamlit as st
import re
from datetime import datetime
from typing import List, Dict
from streamlit_scroll_to_top import scroll_to_here

# 카카오 API 및 requests 선택적 import
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    st.warning("⚠️ requests 라이브러리가 설치되지 않아 지도 기능을 사용할 수 없습니다. 'pip install requests'로 설치해주세요.")

from config import TAG_COLORS, PLAN_TAG_COLORS, RESTAURANT_REGION_COLORS, RESTAURANT_CATEGORY_COLORS, KAKAO_REST_API_KEY

def get_kakao_coordinates(address: str) -> tuple:
    """카카오 Local API를 사용하여 주소를 좌표로 변환"""
    if not KAKAO_REST_API_KEY:
        return None, None
    
    try:
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
        params = {"query": address}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['documents']:
                # 첫 번째 결과 사용
                result = data['documents'][0]
                lat = float(result['y'])
                lon = float(result['x'])
                return lat, lon
        return None, None
    except Exception as e:
        st.error(f"카카오 API 오류: {e}")
        return None, None

def render_kakao_map(address: str, restaurant_name: str) -> None:
    """카카오 API로 좌표 추출 후 카카오맵으로 표시 (예쁜 디자인)"""
    lat, lon = get_kakao_coordinates(address)
    
    if lat and lon:
        # 카카오맵 embed URL 생성 (예쁜 디자인, 한국 최적화)
        import urllib.parse
        encoded_name = urllib.parse.quote(restaurant_name)
        kakao_map_url = f"https://map.kakao.com/link/map/{encoded_name},{lat},{lon}"
        
        # 좌표 정보 표시
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FEE500 0%, #FFCD00 100%); 
                    color: black; padding: 15px; border-radius: 10px; margin: 15px 0; text-align: center;">
            📍 <strong>{restaurant_name}</strong><br>
            📍 정확한 위치: 위도 {lat:.6f}, 경도 {lon:.6f}
        </div>
        """, unsafe_allow_html=True)
        
        # 카카오맵 iframe 삽입 (예쁜 디자인)
        st.markdown(f"""
        <div style="width: 100%; text-align: center; margin: 20px 0;">
            <iframe 
                src="{kakao_map_url}" 
                width="100%" 
                height="500" 
                frameborder="0" 
                scrolling="no"
                style="border-radius: 15px; box-shadow: 0 8px 16px rgba(0,0,0,0.15); border: none;">
            </iframe>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.markdown("""
        <div style="color: #F59E0B; font-size: 26px; margin: 15px 0;">
            ⚠️ 주소를 지도에서 찾을 수 없습니다. 아래 카카오맵 링크를 이용해주세요.
        </div>
        """, unsafe_allow_html=True)

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

def get_responsive_columns():
    """화면 크기에 따른 컬럼 수 결정"""
    return 4  # 기본 4열, CSS에서 반응형으로 조정

def render_header():
    """헤더 렌더링 (3개 탭 네비게이션 포함)"""
    # 왼쪽 제목 영역보다 오른쪽 네비 영역에 더 많은 공간 할당
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.title("🏢 요즘 부산")
    
    with col2:
        # 3개 탭 스타일 네비게이션
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
    
    # 페이지별 설명과 이용 방법
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
    """맛집 카드 렌더링 (미슐랭 등급 포함)"""
    with st.container():
        # 지역과 카테고리를 한 줄에 배치
        region = restaurant_item.get('region', '기타')
        district = restaurant_item.get('district', '')
        category = restaurant_item.get('category', '현지인')
        food_type = restaurant_item.get('food_type', '한식')
        michelin_grade = restaurant_item.get('michelin_grade', '')
        
        region_color = RESTAURANT_REGION_COLORS.get(region, "#6B7280")
        # 미슐랭가이드 주황색으로 변경
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
        
        # 요약정보에 MD 파일의 상세정보 표시 (높이 반으로 줄임)
        summary_text = ""
        try:
            # MD 파일에서 상세정보 추출
            with open(restaurant_item['file_path'], 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # "## 📝 상세 정보" 섹션 찾기
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
    """맛집 그리드 렌더링 (반응형 개선)"""
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
    
    # MD 파일 내용 표시 - 글자 크기 20px 적용
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
    """맛집 상세 페이지 - 구글맵 포함"""
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
        
        # 이용안내 섹션에서 정보 추출 (frontmatter 대신)
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
        
        # 3. 🗺️ 위치 (카카오맵 iframe) - 새로 추가된 섹션
        st.markdown(f"""
        <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
            <h3 style="color: #FEE500; font-size: 34px; margin-bottom: 15px;">🗺️ 위치</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # 카카오맵 iframe으로 지도 표시
        if address and KAKAO_REST_API_KEY and REQUESTS_AVAILABLE:
            render_kakao_map(address, restaurant_item['title'])
        elif address and not KAKAO_REST_API_KEY:
            st.markdown(f"""
            <div style="color: #9CA3AF; font-size: 26px; margin: 15px 0; padding: 20px; background-color: #374151; border-radius: 10px;">
                📍 <strong>주소:</strong> {address}<br><br>
                🗺️ <strong>카카오맵을 보려면:</strong><br>
                • .env 파일에 KAKAO_REST_API_KEY를 설정하거나<br>
                • 아래 카카오맵 링크를 이용해주세요
            </div>
            """, unsafe_allow_html=True)
        elif address and not REQUESTS_AVAILABLE:
            st.markdown(f"""
            <div style="color: #9CA3AF; font-size: 26px; margin: 15px 0; padding: 20px; background-color: #374151; border-radius: 10px;">
                📍 <strong>주소:</strong> {address}<br><br>
                🗺️ <strong>지도를 보려면:</strong><br>
                • 'pip install requests'로 requests 라이브러리를 설치하거나<br>
                • 아래 카카오맵 링크를 이용해주세요
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="color: #9CA3AF; font-size: 26px; margin: 15px 0;">
                📍 주소 정보가 없어 지도를 표시할 수 없습니다.
            </div>
            """, unsafe_allow_html=True)
        
        # 4. 대표메뉴 (30px = 24px + 6px, 34px = 28px + 6px, 26px = 20px + 6px)
        if representative_menu:
            st.markdown(f"""
            <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
                <h3 style="color: #10B981; font-size: 34px; margin-bottom: 15px;">🍽️ 대표메뉴</h3>
                <div style="margin-left: 20px; font-size: 26px;">
                    {representative_menu}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # 5. 추가정보 (원래 내용 - "## 📝 상세 정보" 섹션)
        detail_match = re.search(r'## 📝 상세 정보\s*\n\n(.+?)(?=\n---|\n##|\n$)', md_content, re.DOTALL)
        if detail_match:
            detail_content = detail_match.group(1).strip()
            st.markdown(f"""
            <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
                <h3 style="color: #F59E0B; font-size: 34px; margin-bottom: 15px;">📝 추가정보</h3>
                <div style="margin-left: 20px; font-size: 26px; line-height: 1.8;">
                    {detail_content}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # 6. 분류정보 (30px = 24px + 6px, 34px = 28px + 6px, 26px = 20px + 6px)
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
        
        # 7. 카카오맵 정보확인 (34px = 28px + 6px, 26px = 20px + 6px, 24px = 18px + 6px)
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
    
    # MD 파일 내용 표시 - 글자 크기 20px 적용
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