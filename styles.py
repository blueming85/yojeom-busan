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
    </style>
    """

def get_base_button_css():
    """기본 버튼 스타일 및 호버 효과 CSS"""
    return """
    <style>
    /* 🔧 사이드바 토글 버튼 활성화 */
    button[aria-label*="Open"],
    button[title*="Open"],
    button[aria-label*="sidebar"],
    button[title*="sidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    /* 🔧 사이드바 토글 버튼 아이콘 스타일 */
    [data-testid="collapsedControl"] svg,
    button[data-testid="collapsedControl"] svg {
        color: #4a5568 !important;
        width: 18px !important;
        height: 18px !important;
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
    </style>
    """

def get_navigation_css():
    """네비게이션 버튼 스타일 CSS"""
    return """
    <style>
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
    </style>
    """

def get_sidebar_css():
    """사이드바 스타일 CSS"""
    return """
    <style>
    /* 🔧 사이드바 완전 개선 - 진한 회색 버튼에 흰 글자, 흰 테두리 */
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] .stButton button,
    section[data-testid="stSidebar"] div.stButton > button {
        background: #374151 !important;
        background-color: #374151 !important;
        border: 1px solid white !important;
        color: white !important;
        padding: 10px 15px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
    }

    /* 사이드바 버튼 호버 효과 */
    section[data-testid="stSidebar"] button:hover,
    section[data-testid="stSidebar"] button:focus,
    section[data-testid="stSidebar"] .stButton button:hover,
    section[data-testid="stSidebar"] .stButton button:focus,
    section[data-testid="stSidebar"] div.stButton > button:hover,
    section[data-testid="stSidebar"] div.stButton > button:focus {
        background: #4b5563 !important;
        background-color: #4b5563 !important;
        border: 1px solid white !important;
        color: white !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* 선택된 사이드바 버튼 (primary) - 더 진한 회색, 흰 테두리 */
    section[data-testid="stSidebar"] button[kind="primary"],
    section[data-testid="stSidebar"] .stButton button[kind="primary"],
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background: #1f2937 !important;
        background-color: #1f2937 !important;
        border: 2px solid white !important;
        color: white !important;
    }

    /* 사이드바 모든 텍스트 흰색 */
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] .stMarkdown h4,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] .stText,
    [data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {
        color: white !important;
    }

    /* 🔧 사이드바 배경색 멋진 그라데이션으로 설정 */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"],
    .css-1d391kg,
    .css-1lcbmhc {
        background: linear-gradient(180deg, #4b5563 0%, #6b7280 50%, #9ca3af 100%) !important;
    }

    /* 사이드바 내부 요소들도 배경 투명하게 */
    section[data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div {
        background-color: transparent !important;
    }

    /* 사이드바 넓이 증가 */
    .css-1d391kg {
        width: 300px;
        background: linear-gradient(180deg, #4b5563 0%, #6b7280 50%, #9ca3af 100%) !important;
    }
    .css-1lcbmhc {
        width: 300px;
        background: linear-gradient(180deg, #4b5563 0%, #6b7280 50%, #9ca3af 100%) !important;
    }

    /* 🔧 날짜 박스 완전 개선 - 연한 회색 배경에 흰 글자 */
    .news-date, .plans-date {
        background-color: #6b7280 !important;
        color: white !important;
        border: 1px solid #9ca3af !important;
    }

    /* 날짜 관련 모든 요소들 강제 적용 */
    div[style*="text-align: right"],
    div[style*="background-color: rgba(0,0,0,0.1)"],
    div[style*="color: #333"] {
        background-color: #6b7280 !important;
        color: white !important;
        border: 1px solid #9ca3af !important;
    }
    </style>
    """

def get_responsive_css():
    """반응형 디자인 CSS"""
    return """
    <style>
    /* 🔧 반응형 디자인 개선 */
    /* 데스크톱 (기본) */
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
        
        /* 모바일에서 카드 높이 조정 */
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
    /* 🔧 메인 페이지 다크모드 배경 */
    .stApp {
        background: linear-gradient(180deg, #374151 0%, #4b5563 50%, #6b7280 100%) !important;
    }
    
    /* 🔧 상단 여백 줄이기 */
    .stApp > div:first-child {
        padding-top: 1rem !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 일반 텍스트만 흰색 (버튼, 제목박스 제외) */
    .stApp > div, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: white !important;
    }
    
    /* 🔧 이용방법 박스 다시 표시하고 흰색 텍스트 */
    [data-testid="stAlert"] {
        display: block !important;
        visibility: visible !important;
    }
    
    [data-testid="stAlert"] p, 
    [data-testid="stAlert"] div, 
    [data-testid="stAlert"] * {
        color: white !important;
    }
    
    /* 태그 색상 기반 제목 박스 스타일 (원래 색상 유지) */
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

    /* 제목박스 내 텍스트는 원래 색상 유지 */
    .news-title-box span, .news-title-box div {
        color: inherit !important;
    }

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
    /* 🔧 상세 페이지 다크모드 배경 */
    .detail-page {
        background: linear-gradient(180deg, #374151 0%, #4b5563 50%, #6b7280 100%) !important;
        color: white !important;
        font-size: 22px !important;
        line-height: 1.8 !important;
        padding: 20px !important;
        border-radius: 10px !important;
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
    .detail-page p {
        color: white !important;
        font-size: 22px !important;
        line-height: 1.8 !important;
        margin-bottom: 15px !important;
    }
    .detail-page li {
        color: white !important;
        font-size: 22px !important;
        line-height: 1.8 !important;
        margin-bottom: 8px !important;
    }
    .detail-page strong, .detail-page b {
        color: white !important;
        font-size: 22px !important;
        font-weight: 700 !important;
    }
    </style>
    """