"""
부산시청 정보포털 - CSS 스타일 관리 모듈
==========================================
앱의 모든 CSS 스타일을 기능별로 분리하여 관리
"""

import streamlit as st

def apply_all_styles():
    """모든 CSS 스타일을 한 번에 적용"""
    st.markdown(get_deploy_hide_css(), unsafe_allow_html=True)
    st.markdown(get_base_button_css(), unsafe_allow_html=True)
    st.markdown(get_navigation_css(), unsafe_allow_html=True)
    st.markdown(get_sidebar_css(), unsafe_allow_html=True)
    st.markdown(get_responsive_css(), unsafe_allow_html=True)
    st.markdown(get_card_styles_css(), unsafe_allow_html=True)
    st.markdown(get_detail_page_css(), unsafe_allow_html=True)

def get_deploy_hide_css():
    """Deploy 버튼과 헤더 숨기기 CSS"""
    return """
    <style>
    /* Deploy 버튼과 세 줄 메뉴 숨기기 */
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

    .stApp > header {
        display: none !important;
    }

    *[class*="deploy" i],
    *[id*="deploy" i],
    *[data-testid*="deploy" i] {
        display: none !important;
    }
    </style>
    """

def get_base_button_css():
    """기본 버튼 스타일 및 호버 효과 CSS"""
    return """
    <style>
    /* 사이드바 토글 버튼 활성화 */
    button[aria-label*="Open"],
    button[title*="Open"],
    button[aria-label*="sidebar"],
    button[title*="sidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    [data-testid="collapsedControl"] svg,
    button[data-testid="collapsedControl"] svg {
        color: #4a5568 !important;
        width: 18px !important;
        height: 18px !important;
    }

    /* 호버 효과 제거 */
    *, *:hover {
        transition: none !important;
    }

    /* 메인 콘텐츠 버튼 기본 스타일 */
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
        color: #4A148C !important;
        border: 2px solid #4A148C !important;
        border-radius: 15px !important;
        outline: none !important;
        box-shadow: none !important;
        text-decoration: none !important;
        display: block !important;
        text-align: center !important;
    }

    /* 메인 콘텐츠 버튼 호버 효과 */
    button:hover, button:focus,
    .stButton button:hover, .stButton button:focus,
    div.stButton > button:hover, div.stButton > button:focus,
    [data-testid="baseButton-primary"]:hover, [data-testid="baseButton-primary"]:focus,
    [data-testid="baseButton-secondary"]:hover, [data-testid="baseButton-secondary"]:focus,
    a[data-testid="stLinkButton"]:hover, a[data-testid="stLinkButton"]:focus,
    .stLinkButton > a:hover, .stLinkButton > a:focus {
        background: #4A148C !important;
        color: white !important;
        border: 2px solid #4A148C !important;
        outline: none !important;
        box-shadow: none !important;
    }
    </style>
    """

def get_navigation_css():
    """네비게이션 버튼 스타일 CSS"""
    return """
    <style>
    /* 네비게이션 버튼 - primary(활성) 스타일 */
    button[kind="primary"][data-testid*="nav_"] {
        background: #4A148C !important;
        color: white !important;
        border: 2px solid #4A148C !important;
        font-weight: 700 !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    /* 네비게이션 버튼 - primary 호버 효과 */
    button[kind="primary"][data-testid*="nav_"]:hover {
        background: #6B21A8 !important;
        color: white !important;
        border: 2px solid #6B21A8 !important;
        box-shadow: none !important;
    }

    /* 네비게이션 버튼 - secondary(비활성) 스타일 */
    button[kind="secondary"][data-testid*="nav_"] {
        background: #fff !important;
        color: #4A148C !important;
        border: 2px solid #4A148C !important;
        font-weight: 700 !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    /* 네비게이션 버튼 - secondary 호버 효과 */
    button[kind="secondary"][data-testid*="nav_"]:hover {
        background: #4A148C !important;
        color: white !important;
        border: 2px solid #4A148C !important;
        box-shadow: none !important;
    }
    </style>
    """

def get_sidebar_css():
    """사이드바 스타일 CSS - 회색 기본, 보라색 호버 및 선택"""
    return """
    <style>
    /* 사이드바 입력창 텍스트 */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] textarea {
        color: black !important;
        background-color: white !important;
    }

    /* 사이드바 버튼 기본 상태 - 회색 */
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] .stButton button {
        background: #6B7280 !important;
        border: 2px solid #6B7280 !important;
        color: white !important;
        padding: 10px 15px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        width: 100% !important;
        display: block !important;
        margin-bottom: 5px !important;
    }

    /* 사이드바 버튼 호버 효과 - 보라색 */
    section[data-testid="stSidebar"] button:hover,
    section[data-testid="stSidebar"] button:focus {
        background: #8B5CF6 !important;
        border: 2px solid #8B5CF6 !important;
        color: white !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* 선택된 사이드바 버튼 (primary) - 보라색 */
    section[data-testid="stSidebar"] button[kind="primary"] {
        background: #8B5CF6 !important;
        border: 2px solid #8B5CF6 !important;
        color: white !important;
        font-weight: 700 !important;
    }

    /* 선택된 사이드바 버튼 호버 효과 */
    section[data-testid="stSidebar"] button[kind="primary"]:hover,
    section[data-testid="stSidebar"] button[kind="primary"]:focus {
        background: #7C3AED !important;
        border: 2px solid #7C3AED !important;
        color: white !important;
    }

    /* 맛집 음식종류 버튼만 2열 유지 - 작은 크기 */
    section[data-testid="stSidebar"] button[data-testid*="restaurant_food_"] {
        font-size: 11px !important;
        padding: 6px 4px !important;
        zoom: 0.8 !important;
        width: 45% !important;
        display: inline-block !important;
        margin: 2px 1% !important;
        box-sizing: border-box !important;
    }

    /* 음식종류 컨테이너 2열 강제 */
    section[data-testid="stSidebar"] div:has(button[data-testid*="restaurant_food_"]) {
        display: flex !important;
        flex-wrap: wrap !important;
        justify-content: space-between !important;
    }

    /* 긴 텍스트 버튼만 더 작게 */
    section[data-testid="stSidebar"] button[data-testid*="restaurant_food_아시아분식"],
    section[data-testid="stSidebar"] button[data-testid*="restaurant_food_베이커리"] {
        font-size: 8px !important;
        zoom: 0.7 !important;
        padding: 4px 2px !important;
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
    }

    /* 사이드바 배경 그라데이션 */
    section[data-testid="stSidebar"],
    .css-1d391kg,
    .css-1lcbmhc {
        background: linear-gradient(180deg, #4b5563 0%, #6b7280 50%, #9ca3af 100%) !important;
        width: 350px;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: relative !important;
        left: 0 !important;
        transform: translateX(0) !important;
    }

    /* 사이드바 강제 표시 */
    .css-1544g2n,
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"],
    .stSidebar,
    div[class*="sidebar"],
    div[class*="Sidebar"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: relative !important;
        left: 0 !important;
        transform: translateX(0) !important;
    }

    /* 사이드바 컨테이너 강제 표시 */
    .css-1d391kg,
    .css-1lcbmhc,
    div[class*="css-1d391kg"],
    div[class*="css-1lcbmhc"] {
        min-width: 350px !important;
        max-width: 350px !important;
        width: 350px !important;
        display: block !important;
    }

    /* 모든 가능한 사이드바 클래스 강제 표시 */
    *[class*="sidebar" i],
    *[data-testid*="sidebar" i] {
        display: block !important;
        visibility: visible !important;
    }

    /* 사이드바 내부 요소 배경 투명 */
    section[data-testid="stSidebar"] > div {
        background-color: transparent !important;
    }
    </style>
    """

def get_responsive_css():
    """반응형 디자인 CSS"""
    return """
    <style>
    /* 데스크톱 기본 */
    .stColumn {
        padding: 0 0.3rem;
        min-width: 250px;
    }

    /* 태블릿 */
    @media (max-width: 1024px) {
        .stColumn {
            min-width: 300px;
            padding: 0 0.5rem;
        }
    }

    /* 모바일 */
    @media (max-width: 768px) {
        .stColumn {
            min-width: 100% !important;
            padding: 0 1rem;
            margin-bottom: 1rem;
        }
        
        .news-title-box {
            min-height: 80px !important;
            font-size: 16px !important;
        }
        
        .news-summary {
            height: 60px !important;
            font-size: 12px !important;
        }
    }

    /* 작은 모바일 */
    @media (max-width: 480px) {
        .news-title-box {
            min-height: 60px !important;
            font-size: 14px !important;
            padding: 10px !important;
        }
        
        .news-summary {
            height: 50px !important;
            font-size: 11px !important;
            padding: 10px !important;
        }
    }

    .stColumn > div {
        height: 100%;
    }
    </style>
    """

def get_card_styles_css():
    """카드 스타일 CSS"""
    return """
    <style>
    /* 메인 페이지 다크모드 배경 */
    .stApp {
        background: linear-gradient(180deg, #374151 0%, #4b5563 50%, #6b7280 100%) !important;
    }
    
    /* 상단 여백 줄이기 */
    .stApp > div:first-child {
        padding-top: 1rem !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 일반 텍스트 흰색 */
    .stApp > div, 
    .stMarkdown p, 
    .stMarkdown h1, 
    .stMarkdown h2, 
    .stMarkdown h3 {
        color: white !important;
    }
    
    /* 이용방법 박스 흰색 텍스트 */
    [data-testid="stAlert"] {
        display: block !important;
        visibility: visible !important;
    }
    
    [data-testid="stAlert"] p, 
    [data-testid="stAlert"] div, 
    [data-testid="stAlert"] * {
        color: white !important;
    }
    
    /* 제목 박스 스타일 */
    .news-title-box {
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        text-align: center;
        font-weight: bold;
        min-height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* 제목박스 내 텍스트 검은색 */
    .news-title-box span, 
    .news-title-box div, 
    .news-title-box * {
        color: #000000 !important;
        font-size: 22px !important;
        font-weight: bold !important;
    }

    /* 요약 박스 스타일 */
    .news-summary {
        margin: 1rem 0;
        padding: 15px;
        background-color: #374151 !important;
        color: white !important;
        border-radius: 8px;
        border-left: 4px solid #6b7280 !important;
        line-height: 1.6;
    }
    </style>
    """

def get_detail_page_css():
    """상세 페이지 전용 CSS"""
    return """
    <style>
    /* 상세 페이지 다크모드 배경 */
    .detail-page {
        background: linear-gradient(180deg, #374151 0%, #4b5563 50%, #6b7280 100%) !important;
        color: white !important;
        font-size: 20px !important;
        line-height: 1.8 !important;
        padding: 20px !important;
        border-radius: 10px !important;
    }
    
    /* 상세 페이지 내 모든 텍스트 20px */
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
    
    .detail-page h1 {
        color: white !important;
        font-size: 36px !important;
        line-height: 1.4 !important;
        margin-bottom: 20px !important;
    }
    
    .detail-page h2 {
        color: white !important;
        font-size: 28px !important;
        line-height: 1.5 !important;
        margin: 25px 0 15px 0 !important;
    }
    
    .detail-page h3 {
        color: white !important;
        font-size: 24px !important;
        line-height: 1.5 !important;
        margin: 20px 0 10px 0 !important;
    }
    
    .detail-page strong, 
    .detail-page b {
        color: white !important;
        font-size: 20px !important;
        font-weight: 700 !important;
    }
    
    /* 일반 마크다운도 20px */
    div[style*="font-size: 20px"] {
        font-size: 20px !important;
        line-height: 1.8 !important;
        color: white !important;
    }
    
    div[style*="font-size: 20px"] * {
        font-size: 20px !important;
        line-height: 1.8 !important;
        color: white !important;
    }
    
    div[style*="font-size: 20px"] h1 {
        font-size: 36px !important;
        line-height: 1.4 !important;
    }
    
    div[style*="font-size: 20px"] h2 {
        font-size: 28px !important;
        line-height: 1.5 !important;
    }
    
    div[style*="font-size: 20px"] h3 {
        font-size: 24px !important;
        line-height: 1.5 !important;
    }
    </style>
    """