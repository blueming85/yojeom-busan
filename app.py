"""
부산시청 정보포털 - Streamlit 앱 (보도자료 + 맛집정보 + 업무계획)
=================================================================
태그 색상 기반 카드형 UI로 보도자료, 맛집정보, 업무계획을 쉽게 검색하고 확인할 수 있는 통합 포털

실행 방법:
    streamlit run app.py
"""

import streamlit as st

# 페이지 설정 (반드시 첫 번째 Streamlit 명령이어야 함)
st.set_page_config(
    page_title="요즘 부산",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 나머지 imports들
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import streamlit.components.v1 as components
import time
from streamlit_scroll_to_top import scroll_to_here
import os

# 프로젝트 모듈 import
from config import (
    MD_DIR, AVAILABLE_TAGS, TAG_COLORS,
    PLANS_MD_DIR, PLAN_DEPARTMENTS, AVAILABLE_PLAN_TAGS, PLAN_TAG_COLORS,
    AVAILABLE_RESTAURANT_REGIONS, RESTAURANT_FOOD_TYPES, AVAILABLE_RESTAURANT_CATEGORIES,
    RESTAURANT_REGION_COLORS, RESTAURANT_FOOD_TYPE_COLORS, RESTAURANT_CATEGORY_COLORS,
    AVAILABLE_POLICY_REGIONS, POLICY_CATEGORIES, POLICY_CATEGORY_COLORS,
    IS_LOCAL, get_env_info, MESSAGES
)
from plans_portal import BusanPlansPortal
from restaurant_portal import BusanRestaurantPortal, get_restaurant_portal_stats
from policy_portal import BusanPolicyPortal, get_policy_portal_stats   # ✅ 정책포털
from policy_page import render_policy_map_with_sidebar
from detail_pages import (
    render_header, render_news_detail, render_restaurant_detail, render_plans_detail,
    render_news_grid_with_scroll, render_restaurant_grid_with_scroll, render_plans_grid_with_scroll,
    render_restaurant_map_with_sidebar,
    extract_contact_from_content
)

# 회색 그라데이션 배경만 적용
def apply_custom_styles():
    """회색 그라데이션 배경과 기본 텍스트 색상 적용"""
    st.markdown("""
    <style>
    /* Deploy 버튼만 숨기기 */
    .stDeployButton,
    button[title*="Deploy"],
    button[aria-label*="Deploy"],
    a[href*="deploy"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }

    /* 사이드바 초기 너비 350px로 설정 */
    section[data-testid="stSidebar"] {
        width: 350px !important;
        min-width: 350px !important;
        max-width: 350px !important;
        background: linear-gradient(180deg, #4b5563 0%, #6b7280 50%, #9ca3af 100%) !important;
    }

    /* 사이드바가 열릴 때 너비 유지 */
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 350px !important;
        min-width: 350px !important;
        max-width: 350px !important;
    }

    /* 메인 콘텐츠 영역 조정 */
    .main .block-container {
        padding-left: 370px !important;
    }

    /* 모바일에서는 기본값 사용 + 맛집지도 크기 조정 */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: auto !important;
            min-width: auto !important;
            max-width: auto !important;
        }
        .main .block-container {
            padding-left: 1rem !important;
        }
        
        /* 모바일 맛집지도 크기 축소 */
        .js-plotly-plot,
        .plotly-graph-div,
        [data-testid="stDeckGlJsonChart"] {
            height: 250px !important;
            max-height: 250px !important;
        }
        
        /* PyDeck 지도 컨테이너 크기 조정 */
        .deck-tooltip,
        .deck-canvas {
            height: 300px !important;
        }
    }


    /* Plotly 호버 툴팁 텍스트 색상 수정 - 모바일에서 잘 보이도록 검정색으로 */
    .js-plotly-plot .plotly .hovertext,
    .js-plotly-plot .plotly .hoverlayer .hovertext,
    .plotly-graph-div .hovertext,
    .plotly-graph-div .hoverlayer .hovertext,
    .hoverlayer .hovertext,
    .hovertext,
    .js-plotly-plot .hovertext *,
    .plotly-graph-div .hovertext *,
    .hoverlayer .hovertext *,
    .hovertext * {
        color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        border: 1px solid #cccccc !important;
        font-weight: 600 !important;
        text-shadow: none !important;
        -webkit-text-fill-color: #000000 !important;
    }

    /* Plotly 호버 툴팁 내부 요소들 강제 검정색 */
    .hoverlayer text,
    .hovertext text,
    .js-plotly-plot .hoverlayer text,
    .js-plotly-plot .hovertext text,
    .plotly-graph-div .hoverlayer text,
    .plotly-graph-div .hovertext text {
        fill: #000000 !important;
        color: #000000 !important;
        font-weight: 600 !important;
    }

    /* Plotly 마커 클릭 이벤트 보장 */
    .js-plotly-plot .plotly .scatterlayer,
    .js-plotly-plot .plotly .scatterlayer .trace,
    .plotly-graph-div .scatterlayer,
    .plotly-graph-div .scatterlayer .trace {
        pointer-events: auto !important;
    }

    /* 호버 툴팁은 클릭 이벤트 통과시키기 */
    .js-plotly-plot .plotly .hoverlayer,
    .plotly-graph-div .hoverlayer {
        pointer-events: none !important;
    }

    .js-plotly-plot .plotly .hovertext,
    .plotly-graph-div .hovertext {
        pointer-events: none !important;
    }

    /* 헤더 영역 색상 및 높이 조정 - 본페이지와 동일한 색상 */
    [data-testid="stHeader"],
    header[data-testid="stHeader"] {
        background: linear-gradient(180deg, #374151 0%, #4b5563 50%, #6b7280 100%) !important;
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        border-bottom: 1px solid #4b5563 !important;
    }
    
    /* 헤더 내부 요소들 높이 조정 */
    [data-testid="stHeader"] > div,
    [data-testid="stToolbar"] {
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        background: transparent !important;
    }

    /* 토글 버튼 (사이드바 열기/닫기) 스타일링 - 호버 효과 강화 */
    button[data-testid="collapsedControl"],
    button[aria-label*="sidebar"],
    button[title*="sidebar"],
    [data-testid="stHeader"] button {
        background: white !important;
        border: 2px solid #e5e7eb !important;
        color: #6b7280 !important;
        width: 50px !important;
        height: 35px !important;
        border-radius: 8px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 2px 8px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease !important;
    }
    
    button[data-testid="collapsedControl"]:hover,
    button[aria-label*="sidebar"]:hover,
    button[title*="sidebar"]:hover,
    [data-testid="stHeader"] button:hover,
    button[data-testid="collapsedControl"]:focus,
    button[data-testid="collapsedControl"]:active {
        background: #e5e7eb !important;
        border: 2px solid #e5e7eb !important;
        color: #6b7280 !important;
        transform: scale(1.05) !important;
        box-shadow: 0 4px 8px rgba(156, 163, 175, 0.3) !important;
    }

    /* 메인 배경 */
    .stApp { 
        background: linear-gradient(180deg, #374151 0%, #4b5563 50%, #6b7280 100%) !important; 
    }
    
    /* 사이드바 타이트한 줄간격 설정 */
    /* 사이드바 전체 줄간격 조정 */
    section[data-testid="stSidebar"] .stMarkdown {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        line-height: 1.1 !important;
    }
    
    /* 사이드바 제목 간격 조정 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4 {
        margin-top: 6px !important;
        margin-bottom: 8px !important;
        line-height: 1.1 !important;
        padding-top: 2px !important;
        padding-bottom: 1px !important;
    }
    
    /* 사이드바 텍스트 간격 조정 */
    section[data-testid="stSidebar"] p {
        margin-top: 1px !important;
        margin-bottom: 1px !important;
        line-height: 1.2 !important;
        padding-top: 1px !important;
        padding-bottom: 1px !important;
    }
    
    /* 사이드바 버튼 간격 조정 - 최대한 타이트하게 */
    section[data-testid="stSidebar"] button {
        margin-bottom: -4px !important;
        margin-top: -4px !important;
        padding: 1px 2px !important;
    }
    
    /* 사이드바 모든 element 간격 최소화 */
    section[data-testid="stSidebar"] .element-container {
        margin-bottom: -2px !important;
        margin-top: -2px !important;
        padding-bottom: 0px !important;
        padding-top: 0px !important;
    }
    
    /* 사이드바 버튼 컨테이너 간격 제거 */
    section[data-testid="stSidebar"] .stButton > div {
        margin-bottom: -2px !important;
        margin-top: -2px !important;
        padding-bottom: 0px !important;
        padding-top: 0px !important;
    }
    
    /* 사이드바 모든 div 간격 최소화 */
    section[data-testid="stSidebar"] > div > div > div {
        margin-bottom: -1px !important;
        margin-top: -1px !important;
        padding-bottom: 0px !important;
        padding-top: 0px !important;
    }
    
    /* 사이드바 divider 간격 조정 */
    section[data-testid="stSidebar"] hr {
        margin-top: 3px !important;
        margin-bottom: 3px !important;
    }
    
    /* 사이드바 metric 컴포넌트 간격 조정 */
    section[data-testid="stSidebar"] [data-testid="metric-container"] {
        margin-bottom: 2px !important;
        margin-top: 2px !important;
        padding-bottom: 1px !important;
    }
    
    /* 사이드바 입력창 간격 조정 */
    section[data-testid="stSidebar"] .stTextInput > div {
        margin-bottom: 4px !important;
        margin-top: 2px !important;
    }
    
    /* 사이드바 라디오 버튼 간격 조정 */
    section[data-testid="stSidebar"] .stRadio > div {
        margin-bottom: 2px !important;
        margin-top: 2px !important;
    }
    
    /* 사이드바 2열 버튼 간격 거의 완전히 제거 */
    section[data-testid="stSidebar"] [data-testid="column"] {
        padding-left: 0px !important;
        padding-right: 0px !important;
        margin-left: -1px !important;
        margin-right: -1px !important;
        gap: 0px !important;
    }

    /* 2열 버튼 컨테이너 간격 제거 */
    section[data-testid="stSidebar"] .stColumns {
        gap: 1px !important;
        margin-left: 0px !important;
        margin-right: 0px !important;
    }

    /* 2열 버튼 내부 간격 조정 */
    section[data-testid="stSidebar"] [data-testid="column"] > div {
        margin-left: 0px !important;
        margin-right: 0px !important;
        padding-left: 0px !important;
        padding-right: 0px !important;
    }

    /* 2열 버튼 자체 간격 최소화 */
    section[data-testid="stSidebar"] [data-testid="column"] button {
        margin-left: 0px !important;
        margin-right: 0px !important;
        width: 100% !important;
    }
    
    /* 사이드바 success/info/warning/error 메시지 간격 조정 + 하얀색 텍스트 */
    section[data-testid="stSidebar"] .stSuccess,
    section[data-testid="stSidebar"] .stInfo,
    section[data-testid="stSidebar"] .stWarning,
    section[data-testid="stSidebar"] .stError {
        margin-top: 2px !important;
        margin-bottom: 2px !important;
        padding: 4px 8px !important;
    }
    
    /* 사이드바 알림 메시지 텍스트 하얀색 강제 적용 */
    section[data-testid="stSidebar"] .stSuccess > div,
    section[data-testid="stSidebar"] .stInfo > div,
    section[data-testid="stSidebar"] .stWarning > div,
    section[data-testid="stSidebar"] .stError > div,
    section[data-testid="stSidebar"] .stSuccess p,
    section[data-testid="stSidebar"] .stInfo p,
    section[data-testid="stSidebar"] .stWarning p,
    section[data-testid="stSidebar"] .stError p,
    section[data-testid="stSidebar"] .stSuccess div,
    section[data-testid="stSidebar"] .stInfo div,
    section[data-testid="stSidebar"] .stWarning div,
    section[data-testid="stSidebar"] .stError div,
    section[data-testid="stSidebar"] .stSuccess *,
    section[data-testid="stSidebar"] .stInfo *,
    section[data-testid="stSidebar"] .stWarning *,
    section[data-testid="stSidebar"] .stError * {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }
    
    /* 사이드바 selectbox 간격 조정 */
    section[data-testid="stSidebar"] .stSelectbox > div {
        margin-bottom: 4px !important;
        margin-top: 2px !important;
    }
    
    /* 모든 텍스트 흰색 */
    .stApp > div, 
    .stMarkdown p, 
    .stMarkdown h1, 
    .stMarkdown h2, 
    .stMarkdown h3,
    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 { 
        color: #fff !important; 
    }

    /* 사이드바 텍스트 색상 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown * {
        color: white !important;
        font-size: 16px !important;
    }

    /* 사이드바 입력창 */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] select,
    section[data-testid="stSidebar"] .stSelectbox select,
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        color: black !important;
        background-color: white !important;
        font-size: 16px !important;
    }
    
    /* Selectbox 컨테이너 배경 투명하게 */
    section[data-testid="stSidebar"] .stSelectbox {
        background-color: transparent !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox > div {
        background-color: white !important;
        border: 1px solid #d1d5db !important;
        border-radius: 6px !important;
    }
    
    /* Selectbox 텍스트 색상 - 이모지는 유지하고 나머지는 하얀색 */
    section[data-testid="stSidebar"] .stSelectbox select,
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stSelectbox > div > div > div,
    section[data-testid="stSidebar"] .stSelectbox [role="combobox"],
    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] [data-baseweb="select"] [role="option"],
    section[data-testid="stSidebar"] [data-baseweb="select"] > div > div,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div > div,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] span,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] div[role="button"],
    section[data-testid="stSidebar"] .stSelectbox div,
    section[data-testid="stSidebar"] .stSelectbox span {
        color: white !important;
        background-color: transparent !important;
        font-size: 16px !important;
        text-shadow: none !important;
        -webkit-text-fill-color: white !important;
    }
    
    /* Selectbox 드롭다운 옵션들 - 하얀색 텍스트 */
    section[data-testid="stSidebar"] .stSelectbox option,
    section[data-testid="stSidebar"] [role="listbox"] [role="option"],
    section[data-testid="stSidebar"] [data-baseweb="menu"] [role="option"] {
        color: white !important;
        background-color: #6B7280 !important;
        -webkit-text-fill-color: white !important;
    }
    
    /* Selectbox hover 상태 - 하얀색 유지 */
    section[data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
        color: white !important;
        background-color: rgba(255,255,255,0.1) !important;
        -webkit-text-fill-color: white !important;
    }
    
    /* Selectbox 내부 텍스트 노드까지 강제 적용 */
    section[data-testid="stSidebar"] .stSelectbox * {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    /* 사이드바 버튼 secondary 스타일 - 최대한 타이트하게 */
    section[data-testid="stSidebar"] button[kind="secondary"] {
        background: #6B7280 !important;
        border: 2px solid #6B7280 !important;
        color: white !important;
        padding: 1px 2px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        margin-bottom: -1px !important;
        margin-top: -1px !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* 사이드바 버튼 primary 스타일 - 최대한 타이트하게 */
    section[data-testid="stSidebar"] button[kind="primary"] {
        background: #8B5CF6 !important;
        border: 2px solid #8B5CF6 !important;
        color: white !important;
        padding: 1px 2px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        margin-bottom: -1px !important;
        margin-top: -1px !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* 사이드바 버튼 호버 효과 */
    section[data-testid="stSidebar"] button[kind="secondary"]:hover {
        background: #8B5CF6 !important;
        border: 2px solid #8B5CF6 !important;
        color: white !important;
        outline: none !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        background: #7C3AED !important;
        border: 2px solid #7C3AED !important;
        color: white !important;
        outline: none !important;
        box-shadow: none !important;
    }
    
    /* 메인 영역 버튼들 - 흰배경에 마우스 올리면 보라색 */
    .stButton button {
        background: #fff !important;
        border: 2px solid #8B5CF6 !important;
        color: #6B46C1 !important;
        padding: 8px 12px !important;
        font-size: 16px !important;
        font-weight: 900 !important;
        border-radius: 8px !important;
    }
    .stButton button:hover {
        background: #8B5CF6 !important;
        color: white !important;
        border: 2px solid #8B5CF6 !important;
    }
    
    /* 카드 하단 "클릭하여 내용 보기" 버튼 - 흰배경에 마우스 올리면 보라색 */
    button[kind="secondary"] {
        background: #fff !important;
        border: 2px solid #8B5CF6 !important;
        color: #6B46C1 !important;
        font-size: 16px !important;
        font-weight: 900 !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
    }
    button[kind="secondary"]:hover {
        background: #8B5CF6 !important;
        color: white !important;
        border: 2px solid #8B5CF6 !important;
    }

    /* 네비게이션 버튼 (상단 보도자료, 맛집정보, 업무계획) - 흰배경에 마우스 올리면 보라색 */
    button[kind="primary"][data-testid*="nav_"] {
        background: #fff !important;
        color: #6B46C1 !important;
        border: 2px solid #8B5CF6 !important;
        font-weight: 900 !important;
        padding: 12px 16px !important;
        font-size: 16px !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    button[kind="primary"][data-testid*="nav_"]:hover {
        background: #8B5CF6 !important;
        color: white !important;
        border: 2px solid #8B5CF6 !important;
    }

    button[kind="secondary"][data-testid*="nav_"] {
        background: #fff !important;
        color: #6B46C1 !important;
        border: 2px solid #8B5CF6 !important;
        font-weight: 900 !important;
        padding: 12px 16px !important;
        font-size: 16px !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    button[kind="secondary"][data-testid*="nav_"]:hover {
        background: #8B5CF6 !important;
        color: white !important;
        border: 2px solid #8B5CF6 !important;
    }

    /* 상세 페이지 텍스트 */
    .detail-page *,
    .detail-page p,
    .detail-page div,
    .detail-page span,
    .detail-page li,
    .detail-page td,
    .detail-page th {
        font-size: 20px !important;
        line-height: 1.8 !important;
        color: white !important;
    }
    
    /* 링크 스타일 */
    .stApp a,
    .stApp a:link,
    .stApp a:visited {
        color: white !important;
        text-decoration: none !important;
    }
    .stApp a:hover,
    .stApp a:active {
        color: #ddd !important;
        text-decoration: underline !important;
    }

    .stMarkdown a,
    .stMarkdown a:link,
    .stMarkdown a:visited {
        color: white !important;
        text-decoration: none !important;
    }
    .stMarkdown a:hover,
    .stMarkdown a:active {
        color: #ddd !important;
        text-decoration: underline !important;
    }
    </style>
    """, unsafe_allow_html=True)

# CSS 스타일 적용
apply_custom_styles()


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
            st.error(f"마크다운 디렉토리가 없습니다: {self.md_dir}")
            return []
        
        md_files = list(self.md_dir.glob("*.md"))
        
        if not md_files:
            st.warning("마크다운 파일이 없습니다. 크롤링을 먼저 실행해주세요.")
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
        """본문에서 요약 추출 - 기사 첫 문장부터 추출, 반복 표현 정리"""
        lines = body.split('\n')
        summary_lines = []
        
        # 1. 먼저 "## 📋 주요 내용" 또는 "## 📋 핵심 내용" 섹션 찾기
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
        
        # 2. 주요 내용 섹션이 있으면 그것을 반환
        if summary_lines:
            summary = '\n'.join(summary_lines).strip()
            return self._clean_summary_text(summary)
        
        # 3. 주요 내용 섹션이 없으면 본문의 첫 번째 의미있는 문단들 추출
        meaningful_lines = []
        for line in lines:
            line = line.strip()
            # 헤더, 빈 줄, 특수 문자로 시작하는 줄 제외
            if (line and 
                not line.startswith('#') and 
                not line.startswith('---') and
                not line.startswith('![') and
                not line.startswith('[') and
                len(line) > 10):  # 너무 짧은 줄 제외
                meaningful_lines.append(line)
                
                # 충분한 내용이 모이면 중단 (약 200자 정도)
                if len('\n'.join(meaningful_lines)) > 150:
                    break
        
        # 4. 의미있는 내용이 있으면 반환, 없으면 처음 200자
        if meaningful_lines:
            summary = '\n'.join(meaningful_lines)
            return self._clean_summary_text(summary)
        else:
            # 마지막 fallback: 처음 200자
            clean_body = body.replace('#', '').replace('---', '').strip()
            fallback = clean_body[:200] + "..." if len(clean_body) > 200 else clean_body
            return self._clean_summary_text(fallback)
    
    def _clean_summary_text(self, text: str) -> str:
        """썸네일용 요약 텍스트 정리 - 반복 표현 제거 및 가독성 개선"""
        if not text:
            return ""
        
        # 1. 기본 정리
        text = text.strip()
        
        # 2. "부산시는" 반복 제거 및 다양한 표현으로 변경
        sentences = []
        for i, sentence in enumerate(text.split('.')):
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 첫 번째 문장은 그대로 유지
            if i == 0:
                sentences.append(sentence)
            else:
                # 두 번째 문장부터는 "부산시는" 제거하고 자연스럽게 연결
                if sentence.startswith('부산시는'):
                    sentence = sentence[4:].strip()  # "부산시는" 제거
                    if sentence:  # 빈 문장이 아니면 추가
                        sentences.append(sentence)
                elif sentence.startswith('부산시'):
                    sentence = sentence[3:].strip()  # "부산시" 제거
                    if sentence:
                        sentences.append(sentence)
                else:
                    sentences.append(sentence)
        
        # 3. 문장 재조합
        cleaned_text = '. '.join(sentences)
        if cleaned_text and not cleaned_text.endswith('.'):
            cleaned_text += '.'
        
        # 4. 길이 제한 (200자)
        if len(cleaned_text) > 200:
            # 마지막 완전한 문장까지만 포함
            truncated = cleaned_text[:200]
            last_period = truncated.rfind('.')
            if last_period > 100:  # 너무 짧지 않다면 마지막 온점까지
                cleaned_text = truncated[:last_period + 1]
            else:
                cleaned_text = truncated + "..."
        
        # 5. 최종 정리
        cleaned_text = cleaned_text.replace('  ', ' ')  # 이중 공백 제거
        cleaned_text = cleaned_text.replace('..', '.')   # 이중 마침표 제거
        
        return cleaned_text
    
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

def get_ai_recommendations(portal: BusanNewsPortal, situation: str, interest: str) -> List[Dict]:
    """
    상황(situation) + 관심분야(interest) 기반 AI 추천
    - 최근 1년 보도자료만 사용
    - 관심분야 → 내부 태그 매핑으로 1차 필터
    - 분야별 핵심 키워드로 2차 보정(옵션)
    - GPT는 최종 후보군만 받아서 선별(reason 포함)
    """
    import os, json, re
    from datetime import datetime, timedelta
    import streamlit as st

    # 0) 관심분야 → 내부 태그 매핑
    INTEREST_TO_TAGS = {
        "일자리/취업/창업": ["일자리·경제"],
        "주거/부동산": ["교통·주거"],
        "육아/교육": ["청년·교육"],
        "복지혜택/건강의료": ["복지·건강"],
        "문화/관광": ["문화·관광"],
        "교통/인프라": ["교통·주거"],      # ✅ 교통/인프라 → 교통·주거 우선
        "행정서비스": ["행정·소식"],
    }

    # (선택) 분야별 키워드 힌트로 추가 보정
    INTEREST_KEYWORDS = {
        "교통/인프라": ["교통", "인프라", "도로", "지하철", "철도", "BRT", "버스", "환승", "터널", "교차로", "보행", "주차", "주거", "주택", "재개발"],
        "주거/부동산": ["주거", "주택", "청약", "임대", "분양", "재개발", "정비", "도시공원"],
        "일자리/취업/창업": ["채용", "일자리", "취업", "고용", "창업", "스타트업", "보육", "자금", "컨설팅", "교육"],
        "육아/교육": ["육아", "보육", "어린이", "청소년", "교육", "장학", "돌봄"],
        "복지혜택/건강의료": ["복지", "건강", "의료", "지원금", "바우처", "장애", "노인", "임산부"],
        "문화/관광": ["축제", "전시", "공연", "관광", "행사", "박람회", "야간"],
        "행정서비스": ["민원", "서비스", "온라인", "시스템", "플랫폼", "행정"],
    }

    try:
        # 1) 최근 1년 보도자료만 확보
        cutoff = datetime.now() - timedelta(days=365)
        recent_news = []
        for news in portal.news_data:
            try:
                nd = datetime.strptime(news.get("date", ""), "%Y-%m-%d")
                if nd >= cutoff:
                    recent_news.append(news)
            except Exception:
                # 날짜 파싱 실패 시 포함하지 않음
                continue

        if not recent_news:
            return []

        # 2) 관심분야 매핑 태그로 1차 필터
        mapped_tags = INTEREST_TO_TAGS.get(interest, [])
        if mapped_tags:
            candidate_news = [
                n for n in recent_news
                if any(t in mapped_tags for t in n.get("tags", []))
            ]
            # 매핑 태그가 없어서 비면 전체로 폴백
            candidate_news = candidate_news or recent_news
        else:
            candidate_news = recent_news

        # 3) 키워드 힌트로 2차 보정(있을 때만, 너무 줄어들면 폴백)
        kw = INTEREST_KEYWORDS.get(interest, [])
        if kw:
            kw_lower = [k.lower() for k in kw]
            def hit(n):
                title = (n.get("title") or "").lower()
                body = (n.get("detailed_summary") or n.get("thumbnail_summary") or "").lower()
                return any(k in title or k in body for k in kw_lower)
            kw_filtered = [n for n in candidate_news if hit(n)]
            if kw_filtered:  # 키워드 매치가 있으면 그걸 우선 사용
                candidate_news = kw_filtered

        # 4) GPT에 보낼 요약 정보 구성(과도한 토큰 방지)
        news_info = []
        for i, n in enumerate(candidate_news[:200]):  # 안전상 한도
            summary = n.get("thumbnail_summary") or n.get("detailed_summary") or ""
            summary = summary[:60] if summary else ""
            tag_text = ", ".join(n.get("tags", [])[:2])
            news_info.append({
                "id": i,
                "title": n.get("title", "")[:100],
                "date": n.get("date", ""),
                "tags": tag_text,
                "summary": summary,
            })

        if not news_info:
            return []

        # 5) GPT 호출
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            st.error(f"OpenAI 클라이언트 로드 실패: {e}")
            return []

        if not os.getenv("OPENAI_API_KEY"):
            st.error("OpenAI API 키가 설정되지 않았습니다.")
            return []

        # 시스템/유저 프롬프트
        mapped_tags_text = ", ".join(mapped_tags) if mapped_tags else "해당없음"
        prompt = f"""
사용자 상황: {situation}
관심분야: {interest}
우선 고려 태그: {mapped_tags_text}

규칙:
- 사용자의 관심분야와 직접 연관된 항목만 추천
- {interest}가 "일자리/취업/창업, 주거/부동산, 육아/교육, 복지혜택/건강의료"면
  → 실제 신청/참여/접수/모집 가능한 사업·지원금·교육·컨설팅·박람회만 포함
  → 단순 행사/기념식/발대식/선포/시상식 등은 제외
- {interest}가 "문화/관광, 교통/인프라, 행정서비스"면
  → 시민에게 유용한 서비스·시설개선·안내도 포함 가능
  → 순수 홍보성/기념행사는 제외
- 최대 10개, 관련성 없으면 0개도 허용
- 이유는 구체적으로(대상·혜택·신청여부 등)

보도자료 후보:
{json.dumps(news_info, ensure_ascii=False)}

JSON으로만 응답:
{{"recommendations":[{{"id":번호,"reason":"구체적도움이유"}}]]}}
""".strip()

        models_to_try = [
            ("gpt-5-nano", {"max_tokens": 2000}),  # 일부 환경 호환
            ("gpt-4.1-nano-2025-04-14", {"max_tokens": 2000, "temperature": 0.0}),
        ]

        content = None
        for model_name, extra in models_to_try:
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "부산시민에게 실제로 도움이 되는 보도자료만 정확히 선별하는 추천 전문가."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    **extra
                )
                content = resp.choices[0].message.content
                if content and content.strip():
                    break
            except Exception:
                continue

        if not content:
            st.error("AI 추천 응답이 비어 있습니다.")
            return []

        # 6) 응답 파싱 및 원본 데이터 연결
        data = json.loads(content)
        recs = []
        for rec in data.get("recommendations", []):
            try:
                idx = int(rec.get("id"))
            except Exception:
                continue
            if 0 <= idx < len(candidate_news):
                item = dict(candidate_news[idx])  # copy
                item["ai_reason"] = rec.get("reason", "")
                recs.append(item)

        return recs[:10]

    except Exception as e:
        st.error(f"AI 추천 오류: {e}")
        return []

def render_news_sidebar(portal: BusanNewsPortal):
    """보도자료 전용 사이드바 - 상황+관심분야 기반 AI 추천"""
    st.sidebar.header("📰 필터 및 검색")
    
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
            st.session_state.items_to_show = 24
            # AI 추천 모드 해제
            st.session_state.ai_recommendations = None
    
    selected_tags = [st.session_state.selected_news_tag] if st.session_state.selected_news_tag != "전체" else ["전체"]
    
    # 🔎 AI 맞춤 추천 섹션
    st.sidebar.divider()
    st.sidebar.subheader("🔎 AI 맞춤 추천")
    
    # 드롭다운 옵션들 - 연령대 제거, 상황+관심분야
    situation_options = ["💼 상황을 선택하세요", "청년/학생", "직장인/구직자", "육아중/신혼부부", "창업준비", "은퇴/시니어", "일반시민"]
    interest_options = ["🎯 관심분야를 선택하세요", "일자리/취업/창업", "주거/부동산", "육아/교육", "복지혜택/건강의료", "문화/관광", "교통/인프라", "행정서비스"]
    
    # 세션 상태 초기화
    if 'ai_recommendations' not in st.session_state:
        st.session_state.ai_recommendations = None
    if 'ai_loading' not in st.session_state:
        st.session_state.ai_loading = False
    
    # 드롭다운들
    situation = st.sidebar.selectbox(
        "💼 상황",
        situation_options,
        key="ai_situation"
    )
    
    interest = st.sidebar.selectbox(
        "🎯 관심분야",
        interest_options,
        key="ai_interest"
    )
    
    # 추천받기 버튼
    both_selected = (
        not situation.startswith("💼") and 
        not interest.startswith("🎯")
    )
    
    if both_selected:
        if st.session_state.get('ai_loading', False):
            st.sidebar.button(
                "📄 추천 중...", 
                disabled=True,
                use_container_width=True,
                type="primary"
            )
        else:
            if st.sidebar.button(
                "✨ 추천받기", 
                use_container_width=True,
                type="primary",
                key="get_ai_recommendations"
            ):
                st.session_state.ai_loading = True
                try:
                    with st.spinner('AI가 맞춤 보도자료를 분석하는 중...'):
                        recommendations = get_ai_recommendations(portal, situation, interest)
                        if recommendations:
                            st.session_state.ai_recommendations = recommendations
                            st.session_state.selected_news_tag = "전체"  # 태그 선택 초기화
                            # st.success를 st.markdown으로 변경하여 하얀색 텍스트 적용
                            # st.sidebar.markdown(f"""
                            # <div style="
                            #     background-color: #10B981;
                            #     color: white !important;
                            #     padding: 8px 12px;
                            #     border-radius: 8px;
                            #     margin: 8px 0;
                            #     font-weight: bold;
                            # ">
                            #     🎯 {len(recommendations)}개의 맞춤 보도자료를 찾았습니다!
                            # </div>
                            # """, unsafe_allow_html=True)
                        else:
                            st.error("추천 결과를 가져올 수 없습니다. 다시 시도해주세요.")
                except Exception as e:
                    st.error(f"추천 중 오류 발생: {e}")
                finally:
                    st.session_state.ai_loading = False
    else:
        st.sidebar.button(
            "✨ 2개 항목을 모두 선택하세요", 
            disabled=True,
            use_container_width=True,
            type="secondary"
        )
    
    # AI 추천 결과가 있으면 표시
    if st.session_state.ai_recommendations:
        # st.success를 st.markdown으로 변경
        st.sidebar.markdown(f"""
        <div style="
            background-color: #10B981;
            color: white !important;
            padding: 8px 12px;
            border-radius: 8px;
            margin: 8px 0;
            font-weight: bold;
        ">
            🤖 AI 추천: {len(st.session_state.ai_recommendations)}개
        </div>
        """, unsafe_allow_html=True)
        
        if st.sidebar.button(
            "📄 일반 모드로 돌아가기",
            use_container_width=True,
            type="secondary",
            key="clear_ai_recommendations"
        ):
            st.session_state.ai_recommendations = None
    
    return search_query, selected_tags, None

def render_restaurant_sidebar(restaurant_portal: BusanRestaurantPortal):
    """맛집정보 전용 사이드바 - 🔧 스크롤 탑 + 줄바꿈 수정"""
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
    
    # 1. 카테고리별 필터 (제일 상단) - 1열 배치 - 🔧 스크롤 탑 추가
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
        st.session_state.restaurant_items_to_show = 24
        # 🔧 스크롤 탑 추가
        st.session_state.scroll_to_top = True
        st.session_state["_filter_sig"] = ""
        st.rerun()
    
    # 나머지 카테고리 버튼들 (1열 배치) - 🔧 스크롤 탑 추가
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
            # 🔧 스크롤 탑 추가
            st.session_state.scroll_to_top = True
            st.session_state["_filter_sig"] = ""
            st.rerun()
    
    # 2. 지역별 필터 - 4개 권역 버튼 (1열 배치) - 🔧 줄바꿈 + 스크롤 탑 수정
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
        # 🔧 스크롤 탑 추가
        st.session_state.scroll_to_top = True
        st.session_state["_filter_sig"] = ""
        st.rerun()
    
    # 🔧 4개 권역 버튼: 간단한 버튼으로 수정 + 스크롤 탑
    regions_display = [
        ("원도심권", "중구·동구·영도구·서구"),
        ("동부산권", "해운대구·수영구·남구·기장군"),
        ("서부산권", "사하구·강서구·사상구"),
        ("북부산권", "북구·금정구·동래구·연제구·부산진구")
    ]
    
    for i in range(0, len(regions_display), 2):
        cols = st.sidebar.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(regions_display):
                region_key, district_names = regions_display[idx]
                is_sel = st.session_state.selected_restaurant_region == region_key
                btn_type = "primary" if is_sel else "secondary"
                
                # 🔧 간단한 제목만 표시, help로 상세정보
                if col.button(
                    f"📍 {region_key}",
                    key=f"restaurant_region_{region_key}",
                    use_container_width=True,
                    type=btn_type,
                    help=district_names  # 툴팁에 구별 정보
                ):
                    st.session_state.selected_restaurant_region = region_key
                    st.session_state.restaurant_items_to_show = 12
                    # 🔧 스크롤 탑 추가
                    st.session_state.scroll_to_top = True
                    st.session_state["_filter_sig"] = ""
                    st.rerun()
    
    # 3. 음식종류별 필터 - 전체 1줄, 나머지 2줄 배치 - 🔧 스크롤 탑 추가
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
        # 🔧 스크롤 탑 추가
        st.session_state.scroll_to_top = True
        st.session_state["_filter_sig"] = ""
        st.rerun()

    # 2) 나머지 음식종류: 2열로 묶어서 반복 - 🔧 스크롤 탑 추가
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
                    # 🔧 스크롤 탑 추가
                    st.session_state.scroll_to_top = True
                    st.session_state["_filter_sig"] = ""
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
        # st.success를 st.markdown으로 변경
        st.sidebar.markdown(f"""
        <div style="
            background-color: #10B981;
            color: white !important;
            padding: 8px 12px;
            border-radius: 8px;
            margin: 8px 0;
            font-weight: bold;
        ">
            🏠 **전체 맛집**: {total_count}개
        </div>
        """, unsafe_allow_html=True)
    
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

def render_policy_sidebar(policy_portal: BusanPolicyPortal):
    """정책지도 전용 사이드바 — 버튼형(맛집 페이지와 동일 UX)"""
    st.sidebar.header("🗺️ 정책 필터")

    # 세션 기본값
    if 'selected_policy_category' not in st.session_state:
        st.session_state.selected_policy_category = "전체"
    if 'selected_policy_region' not in st.session_state:
        st.session_state.selected_policy_region = "전체"

    # 검색어
    search_query = st.sidebar.text_input(
        "🔎 검색어",
        placeholder="정책명, 지역, 카테고리 검색",
        key="policy_search_input"
    )

    # --- 카테고리 버튼 ---
    st.sidebar.subheader("🏷️ 카테고리")
    category_stats = policy_portal.get_category_stats()

    # "전체" 1번만
    category_options = ["전체"] + [c for c in POLICY_CATEGORIES if c != "전체"]
    for category in category_options:
        count = category_stats.get(category, 0)
        is_selected = (st.session_state.selected_policy_category == category)
        btn_type = "primary" if is_selected else "secondary"

        # 고유 key (중복 방지)
        key = f"policy_catbtn_{category}".replace(" ", "_")
        if st.sidebar.button(f"{category} ({count}개)", key=key, use_container_width=True, type=btn_type):
            st.session_state.selected_policy_category = category
            # 필터 바뀔 때 현재 선택된 항목 초기화
            st.session_state.selected_policy_idx = None
            st.session_state.scroll_to_top = True
            st.rerun()

    # --- 지역 버튼 ---
    st.sidebar.subheader("📍 지역별")
    region_stats = policy_portal.get_region_stats()
    region_options = ["전체"] + [r for r in AVAILABLE_POLICY_REGIONS if r != "전체"]

    for region in region_options:
        count = region_stats.get(region, 0)
        is_selected = (st.session_state.selected_policy_region == region)
        btn_type = "primary" if is_selected else "secondary"

        key = f"policy_regionbtn_{region}".replace(" ", "_")
        if st.sidebar.button(f"{region} ({count}개)", key=key, use_container_width=True, type=btn_type):
            st.session_state.selected_policy_region = region
            st.session_state.selected_policy_idx = None
            st.session_state.scroll_to_top = True
            st.rerun()

    # 반환(기존 인터페이스 유지)
    selected_regions = (
        [st.session_state.selected_policy_region]
        if st.session_state.selected_policy_region != "전체" else ["전체"]
    )
    selected_categories = (
        [st.session_state.selected_policy_category]
        if st.session_state.selected_policy_category != "전체" else ["전체"]
    )
    return search_query, selected_regions, selected_categories

def render_plans_sidebar(plans_portal: BusanPlansPortal):
    """업무계획 전용 사이드바 - rerun 제거"""
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
    
    # 1열로 버튼 배치 - 🔧 rerun 제거
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
            # 🔧 st.rerun() 제거
    
    selected_categories = [st.session_state.selected_plans_category] if st.session_state.selected_plans_category != "전체" else ["전체"]
    
    # 통계 정보
    st.sidebar.divider()
    st.sidebar.subheader("📊 선택된 분류")
    
    if st.session_state.selected_plans_category == "전체":
        # st.success를 st.markdown으로 변경
        st.sidebar.markdown(f"""
        <div style="
            background-color: #10B981;
            color: white !important;
            padding: 8px 12px;
            border-radius: 8px;
            margin: 8px 0;
            font-weight: bold;
        ">
            🏠 **전체 업무계획**: {total_count}개
        </div>
        """, unsafe_allow_html=True)
    else:
        selected_count = dept_stats.get(st.session_state.selected_plans_category, 0)
        emoji_category = next((display for display, dept in PLAN_DEPARTMENTS if display.endswith(st.session_state.selected_plans_category)), st.session_state.selected_plans_category)
        # st.success를 st.markdown으로 변경
        st.sidebar.markdown(f"""
        <div style="
            background-color: #10B981;
            color: white !important;
            padding: 8px 12px;
            border-radius: 8px;
            margin: 8px 0;
            font-weight: bold;
        ">
            **{emoji_category}**: {selected_count}개
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("전체", total_count)
    with col2:
        dept_count = len(set(plan.get('department', '') for plan in plans_portal.plans_data))
        st.metric("부서 수", dept_count)
    
    return search_query, selected_categories

def main():
    """메인 앱 실행 (4페이지 통합: 보도자료/맛집/정책지도/업무계획)"""
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
        # 🔧 스크롤 탑 처리 (모든 페이지 공통)
        if st.session_state.get('scroll_to_top'):
            scroll_to_here(0, key='main_page_top')
            st.session_state.scroll_to_top = False
        
        # 상세 페이지 우선 체크
        if st.session_state.show_detail and st.session_state.selected_news:
            render_news_detail(st.session_state.selected_news)
            return
        elif st.session_state.show_restaurant_detail and st.session_state.selected_restaurant:
            render_restaurant_detail(st.session_state.selected_restaurant)
            return
        elif st.session_state.show_plan_detail and st.session_state.selected_plan:
            render_plans_detail(st.session_state.selected_plan)
            return
        
        # 메인 페이지 렌더링
        render_header()
        
        if st.session_state.page == 'news':
            # 보도자료 페이지
            portal = BusanNewsPortal()
            search_query, selected_tags, date_range = render_news_sidebar(portal)
            
            if st.session_state.get('ai_recommendations'):
                filtered_news = st.session_state.ai_recommendations
            else:
                filtered_news = portal.filter_news(selected_tags, search_query, date_range)
            
            if portal.news_data:
                render_news_grid_with_scroll(filtered_news)
            else:
                st.info("📢 보도자료 데이터를 로드하는 중입니다...")
                
        elif st.session_state.page == 'restaurants':
            # 맛집 페이지
            restaurant_portal = BusanRestaurantPortal()
            
            # URL 파라미터 → 상세페이지 이동
            try:
                params = st.query_params
                if 'restaurant_detail' in params:
                    import urllib.parse
                    file_path = urllib.parse.unquote(params['restaurant_detail'])
                    for restaurant in restaurant_portal.restaurants_data:
                        if restaurant.get('file_path') == file_path:
                            st.session_state.selected_restaurant = restaurant
                            st.session_state.show_restaurant_detail = True
                            st.query_params.clear()
                            st.rerun()
                            break
            except Exception:
                pass
            
            if st.session_state.get('show_restaurant_detail') and st.session_state.get('selected_restaurant'):
                render_restaurant_detail(st.session_state.selected_restaurant)
                return
            
            search_query, selected_regions, selected_food_types, selected_categories = render_restaurant_sidebar(restaurant_portal)
            filtered_restaurants = restaurant_portal.filter_restaurants(
                selected_regions, selected_food_types, selected_categories, search_query
            )
            
            def sort_restaurants_michelin_first(restaurants):
                michelin = [r for r in restaurants if r.get('category') == '미쉐린가이드']
                others = [r for r in restaurants if r.get('category') != '미쉐린가이드']
                return michelin + others
            
            filtered_restaurants = sort_restaurants_michelin_first(filtered_restaurants)
            
            if restaurant_portal.restaurants_data:
                render_restaurant_map_with_sidebar(filtered_restaurants)
            else:
                st.info("🍽️ 맛집 데이터를 로드하는 중입니다...")
        
        elif st.session_state.page == 'policy':
            # 정책지도 페이지
            policy_portal = BusanPolicyPortal()
            search_query, selected_regions, selected_categories = render_policy_sidebar(policy_portal)
            filtered_policies = policy_portal.filter_policies(
                selected_regions, selected_categories, search_query
            )

            if policy_portal.policy_data:
                render_policy_map_with_sidebar(filtered_policies)
            else:
                st.info("🗺️ 정책 데이터를 로드하는 중입니다...")
                
        elif st.session_state.page == 'plans':
            # 업무계획 페이지
            if st.session_state.get('show_plan_detail') and st.session_state.get('selected_plan'):
                render_plans_detail(st.session_state.selected_plan)
                return
            
            plans_portal = BusanPlansPortal()
            search_query, selected_categories = render_plans_sidebar(plans_portal)
            filtered_plans = plans_portal.filter_plans(selected_categories, search_query)
            
            if plans_portal.plans_data:
                render_plans_grid_with_scroll(filtered_plans)
            else:
                st.info("📋 업무계획 데이터를 로드하는 중입니다...")
        
        # 제작자 정보 (공통)
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
        st.error(f"⚠️ 앱 실행 중 오류: {e}")
        st.info("**해결 방법**: 데이터 파일을 확인하거나 페이지를 새로고침해주세요.")

if __name__ == "__main__":
    main()
