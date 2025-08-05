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
    """Deploy 버튼과 헤더 숨기기 CSS - 토글 버튼은 제외"""
    return """
    <style>
    /* Deploy 버튼과 세 줄 메뉴 숨기기 - 토글 버튼은 제외 */
    [data-testid="stToolbar"]:not(:has(button[data-testid="collapsedControl"])),
    [data-testid="stHeader"]:not(:has(button[data-testid="collapsedControl"])),
    header[data-testid="stHeader"]:not(:has(button[data-testid="collapsedControl"])),
    .stDeployButton,
    button[title*="Deploy"],
    button[aria-label*="Deploy"],
    a[href*="deploy"],
    button[kind="header"]:not([data-testid="collapsedControl"]),
    iframe[title="streamlit_app"],
    div[data-testid="stToolbar"]:not(:has(button[data-testid="collapsedControl"])),
    section[data-testid="stToolbar"]:not(:has(button[data-testid="collapsedControl"])) {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
        position: absolute !important;
        left: -9999px !important;
    }

    /* 토글 버튼만 보이도록 */
    button[data-testid="collapsedControl"],
    [data-testid="collapsedControl"],
    button[aria-label*="sidebar"],
    button[title*="sidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: relative !important;
        z-index: 999999 !important;
    }

    /* Deploy 관련 요소만 숨기기 */
    *[class*="deploy" i]:not([data-testid="collapsedControl"]),
    *[id*="deploy" i]:not([data-testid="collapsedControl"]),
    *[data-testid*="deploy" i]:not([data-testid="collapsedControl"]) {
        display: none !important;
    }
    </style>
    """

def get_base_button_css():
    """기본 버튼 스타일 및 호버 효과 CSS - 텍스트 크기 증가"""
    return """
    <style>
    /* 사이드바 토글 버튼 완전 활성화 - 모든 가능한 선택자 포함 */
    button[aria-label*="Open"],
    button[title*="Open"],
    button[aria-label*="sidebar"],
    button[title*="sidebar"],
    button[data-testid="collapsedControl"],
    button[aria-label="Collapse sidebar"],
    button[aria-label="Expand sidebar"],
    button[aria-label*="Close"],
    button[title*="Close"],
    .css-vk3wp9,
    .css-18ni7ap,
    [class*="collapsedControl"],
    [data-baseweb="button"][aria-label*="sidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        cursor: pointer !important;
        z-index: 999999 !important;
        position: relative !important;
    }

    /* 토글 버튼 아이콘 스타일 */
    [data-testid="collapsedControl"] svg,
    button[data-testid="collapsedControl"] svg,
    button[aria-label*="sidebar"] svg,
    [class*="collapsedControl"] svg {
        color: #4a5568 !important;
        width: 18px !important;
        height: 18px !important;
        display: block !important;
        visibility: visible !important;
    }

    /* 호버 효과 제거 */
    *, *:hover {
        transition: none !important;
    }

    /* 메인 콘텐츠 버튼 기본 스타일 - 텍스트만 크게, 패딩은 원래대로 */
    button, 
    .stButton button,
    div.stButton > button,
    [data-testid="baseButton-primary"],
    [data-testid="baseButton-secondary"],
    a[data-testid="stLinkButton"],
    .stLinkButton > a,
    button[key*="detail_btn"],
    button[key*="news_detail_btn"],
    button[key*="restaurant_detail_btn"],
    button[key*="plans_detail_btn"],
    button[key*="back_btn"],
    button[key*="load_more"] {
        height: auto !important;
        padding: 20px 18px !important;        /* 원래 패딩 유지 */
        font-size: 45px !important;           /* 30px → 45px (텍스트만 더 크게) */
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
    .stLinkButton > a:hover, .stLinkButton > a:focus,
    button[key*="detail_btn"]:hover, button[key*="detail_btn"]:focus,
    button[key*="news_detail_btn"]:hover, button[key*="news_detail_btn"]:focus,
    button[key*="restaurant_detail_btn"]:hover, button[key*="restaurant_detail_btn"]:focus,
    button[key*="plans_detail_btn"]:hover, button[key*="plans_detail_btn"]:focus,
    button[key*="back_btn"]:hover, button[key*="back_btn"]:focus,
    button[key*="load_more"]:hover, button[key*="load_more"]:focus {
        background: #4A148C !important;
        color: white !important;
        border: 2px solid #4A148C !important;
        outline: none !important;
        box-shadow: none !important;
    }
    </style>
    """

def get_navigation_css():
    """네비게이션 버튼 스타일 CSS - 텍스트 크기 증가"""
    return """
    <style>
    /* 네비게이션 버튼 - 모든 경우에 대해 강력하게 적용 */
    button[data-testid="nav_news"],
    button[data-testid="nav_restaurants"], 
    button[data-testid="nav_plans"],
    button[key="nav_news"],
    button[key="nav_restaurants"],
    button[key="nav_plans"],
    button[kind="primary"][data-testid*="nav_"],
    button[kind="secondary"][data-testid*="nav_"] {
        background: #4A148C !important;
        color: white !important;
        border: 2px solid #4A148C !important;
        font-weight: 700 !important;
        padding: 16px 24px !important;
        font-size: 45px !important;          /* 강력하게 45px 적용 */
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    /* 네비게이션 버튼 - primary(활성) 스타일 - 텍스트만 크게, 패딩은 원래대로 */
    button[kind="primary"][data-testid*="nav_"] {
        background: #4A148C !important;
        color: white !important;
        border: 2px solid #4A148C !important;
        font-weight: 700 !important;
        padding: 16px 24px !important;       /* 원래 패딩 유지 */
        font-size: 45px !important;          /* 32px → 45px (텍스트만 더 크게) */
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    /* 네비게이션 버튼 - primary 호버 효과 */
    button[kind="primary"][data-testid*="nav_"]:hover,
    button[data-testid="nav_news"]:hover,
    button[data-testid="nav_restaurants"]:hover,
    button[data-testid="nav_plans"]:hover {
        background: #6B21A8 !important;
        color: white !important;
        border: 2px solid #6B21A8 !important;
        box-shadow: none !important;
    }

    /* 네비게이션 버튼 - secondary(비활성) 스타일 - 텍스트만 크게, 패딩은 원래대로 */
    button[kind="secondary"][data-testid*="nav_"] {
        background: #fff !important;
        color: #4A148C !important;
        border: 2px solid #4A148C !important;
        font-weight: 700 !important;
        padding: 16px 24px !important;       /* 원래 패딩 유지 */
        font-size: 45px !important;          /* 32px → 45px (텍스트만 더 크게) */
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
    """사이드바 스타일 CSS - 회색 기본, 보라색 호버 및 선택, 텍스트 크기 증가, 간격 극도로 타이트하게, 토글 버튼 활성화"""
    return """
    <style>
    /* 사이드바 입력창 텍스트 */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] textarea {
        color: black !important;
        background-color: white !important;
        font-size: 18px !important;          /* 입력창 텍스트도 증가 */
    }

    /* 사이드바 최상단 패딩 제거 */
    section[data-testid="stSidebar"] {
        padding-top: 0 !important;
    }

    section[data-testid="stSidebar"] > div {
        background-color: transparent !important;
        padding: 0 8px 8px 8px !important;   /* 상단 패딩 완전 제거, 좌우하단만 최소 패딩 */
        margin-top: 0 !important;
    }

    /* 사이드바 첫 번째 요소 상단 마진 제거 */
    section[data-testid="stSidebar"] > div > div:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* 사이드바 버튼 기본 상태 - 회색, 텍스트만 크게, 패딩은 원래대로, 간격 극극극도로 타이트하게 */
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] .stButton button {
        background: #6B7280 !important;
        border: 2px solid #6B7280 !important;
        color: white !important;
        padding: 2px 4px !important;         /* 패딩 4px → 2px로 더 줄임 */
        font-size: 32px !important;          /* 20px → 32px (텍스트만 더 크게) */
        font-weight: 1000 !important;
        border-radius: 6px !important;       /* 둥근 모서리도 줄임 8px → 6px */
        margin-bottom: 0px !important;       /* 버튼 간격 완전 제거 (1px → 0px) */
        margin-top: 0 !important;
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
        margin-bottom: 0px !important;       /* 선택된 버튼도 간격 완전 제거 */
    }

    /* 선택된 사이드바 버튼 호버 효과 */
    section[data-testid="stSidebar"] button[kind="primary"]:hover,
    section[data-testid="stSidebar"] button[kind="primary"]:focus {
        background: #7C3AED !important;
        border: 2px solid #7C3AED !important;
        color: white !important;
    }

    /* 맛집 음식종류 버튼만 2열 유지 - 텍스트만 크게, 패딩은 원래대로, 간격 완전 제거 */
    section[data-testid="stSidebar"] button[data-testid*="restaurant_food_"] {
        font-size: 16px !important;          /* 18px → 16px (조금 더 줄임) */
        padding: 2px 2px !important;         /* 패딩 더 줄임 */
        zoom: 0.8 !important;                /* 줌은 원래대로 */
        margin-bottom: 0px !important;       /* 음식종류 버튼 간격 완전 제거 */
    }

    /* 긴 텍스트 버튼만 더 작게 - 텍스트만 크게, 패딩은 원래대로, 간격 완전 제거 */
    section[data-testid="stSidebar"] button[data-testid*="restaurant_food_아시아분식"],
    section[data-testid="stSidebar"] button[data-testid*="restaurant_food_베이커리"] {
        font-size: 14px !important;          /* 16px → 14px (조금 더 줄임) */
        zoom: 0.7 !important;                /* 줌은 원래대로 */
        padding: 1px 1px !important;         /* 패딩 더 줄임 */
        margin-bottom: 0px !important;       /* 간격 완전 제거 */
    }

    /* 사이드바 섹션 간격 더욱 줄이기 */
    section[data-testid="stSidebar"] .stMarkdown {
        margin-bottom: 2px !important;       /* 4px → 2px (더욱 줄임) */
        margin-top: 2px !important;          /* 4px → 2px (더욱 줄임) */
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* 사이드바 제목들 간격 더욱 줄이기 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        margin-bottom: 4px !important;       /* 8px → 4px (더욱 줄임) */
        margin-top: 3px !important;          /* 6px → 3px (더욱 줄임) */
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        line-height: 1.1 !important;         /* 줄간격도 더 줄임 */
    }

    /* 첫 번째 제목은 상단 마진 완전 제거 */
    section[data-testid="stSidebar"] h1:first-child,
    section[data-testid="stSidebar"] h2:first-child,
    section[data-testid="stSidebar"] h3:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* 사이드바 텍스트 색상 및 크기 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown * {
        color: white !important;
        font-size: 18px !important;          /* 사이드바 일반 텍스트도 증가 */
        margin-top: 0 !important;
        margin-bottom: 1px !important;       /* 텍스트 간격도 더 줄임 */
    }

    /* 사이드바 제목들 더 크게 */
    section[data-testid="stSidebar"] h1 {
        font-size: 24px !important;         /* 26px → 24px (조금 더 줄임) */
    }

    section[data-testid="stSidebar"] h2 {
        font-size: 20px !important;         /* 22px → 20px (조금 더 줄임) */
    }

    section[data-testid="stSidebar"] h3 {
        font-size: 18px !important;         /* 20px → 18px (조금 더 줄임) */
    }

    /* 사이드바 컬럼 간격 극도로 줄이기 (2열 배치용) */
    section[data-testid="stSidebar"] .stColumn {
        min-width: unset !important;
        width: 50% !important;
        padding: 0 0.5px !important;         /* 1px → 0.5px (더 줄임) */
        margin: 0 !important;
    }

    /* 입력창과 첫 번째 섹션 사이 간격 줄이기 */
    section[data-testid="stSidebar"] .stTextInput {
        margin-bottom: 4px !important;      /* 입력창 하단 간격 더 줄임 */
    }

    /* 사이드바 배경 그라데이션 */
    section[data-testid="stSidebar"],
    .css-1d391kg,
    .css-1lcbmhc {
        background: linear-gradient(180deg, #4b5563 0%, #6b7280 50%, #9ca3af 100%) !important;
        width: 400px !important;
        min-width: 400px !important;
        max-width: 400px !important;
    }

    /* 토글 버튼 강제 활성화 - 추가 CSS */
    .stApp [data-testid="collapsedControl"],
    .stApp button[aria-label*="sidebar"],
    .stApp button[title*="sidebar"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: relative !important;
        z-index: 999999 !important;
    }

    /* 토글 버튼이 숨겨지는 것을 방지 */
    .stApp header button,
    .stApp [data-testid="stHeader"] button {
        display: block !important;
        visibility: visible !important;
        pointer-events: auto !important;
    }

    /* 네비 영역을 화면 전체 너비의 70%로 확장 */
    section[data-testid="stToolbar"] + div > div:first-child > div:nth-child(2) {
        flex: 0 0 70% !important;
        max-width: 70% !important;
    }

    /* 접힌 상태에서 Open sidebar 버튼 뒤의 모든 요소 숨기기 */
    section[data-testid="stSidebar"] > button[aria-label*="Open sidebar"] ~ * {
        display: none !important;
    }

    /* 버튼 안에서 '\n'이 개행으로 보이도록 */
    section[data-testid="stSidebar"] button {
        white-space: pre-line !important;
        min-height: 2.5rem !important;      /* 최소 높이 조금 줄임 */
        padding: 0.25rem 0.5rem !important; /* 위아래·좌우 패딩 더 줄임 */
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
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
        
        /* 태블릿에서 버튼 텍스트만 크게 */
        button, .stButton button {
            font-size: 40px !important;
        }
        
        section[data-testid="stSidebar"] button {
            font-size: 28px !important;
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
        
        /* 모바일에서 버튼 텍스트만 크게 */
        button, .stButton button {
            font-size: 35px !important;
        }
        
        section[data-testid="stSidebar"] button {
            font-size: 24px !important;
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
        
        /* 작은 모바일에서 버튼 텍스트만 크게 */
        button, .stButton button {
            font-size: 30px !important;
        }
        
        section[data-testid="stSidebar"] button {
            font-size: 20px !important;
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