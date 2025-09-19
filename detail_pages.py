"""
부산시청 정보포털 - UI 컴포넌트 및 상세 페이지 모듈 (Plotly 지도 버전)
===============================================
헤더, 카드, 그리드, 상세 페이지, 맛집 지도 등 모든 UI 렌더링 함수들을 관리
"""

import streamlit as st
import re
from datetime import datetime
from typing import List, Dict
from streamlit_scroll_to_top import scroll_to_here

# Plotly 지도 관련 라이브러리
try:
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    PLOTLY_AVAILABLE = True
    # print 문 제거 또는 조건부로 변경
    # print("✅ Plotly 라이브러리 로드 성공")
except ImportError as e:
    PLOTLY_AVAILABLE = False
    # 이 부분을 주석 처리하거나 제거
    # print(f"⌒ Plotly 라이브러리 로드 실패: {e}")
    # st.warning("⚠️ 지도 기능을 사용하려면 다음 명령어를 실행해주세요:")
    # st.code("pip install plotly pandas")

# 카카오 API 및 requests 선택적 import
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    st.warning("⚠️ requests 라이브러리가 설치되지 않아 지도 기능을 사용할 수 없습니다.")

from config import (
    TAG_COLORS, PLAN_TAG_COLORS,
    RESTAURANT_REGION_COLORS, RESTAURANT_CATEGORY_COLORS,
    KAKAO_REST_API_KEY
)

# ------------------------------------------------------------
# 유틸
# ------------------------------------------------------------
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
                result = data['documents'][0]
                lat = float(result['y'])
                lon = float(result['x'])
                return lat, lon
        return None, None
    except Exception as e:
        st.error(f"카카오 API 오류: {e}")
        return None, None


def get_marker_style(category: str, michelin_grade: str = "") -> dict:
    """맛집 카테고리별 마커 스타일 반환(미사용 보조)"""
    styles = {
        "미쉐린가이드": {"color": "#FFD700", "symbol": "star", "size": 15},
        "부산의맛":     {"color": "#FF4444", "symbol": "circle", "size": 12},
        "현지인":       {"color": "#4A90E2", "symbol": "circle", "size": 10},
    }
    return styles.get(category, styles["현지인"])


def extract_restaurant_info_from_md(file_path: str) -> dict:
    """
    MD 파일에서 이용안내(전화/주소/영업/휴무/대표메뉴/미쉐린 등급)만 추출하여 반환
    UI는 여기서 렌더링하지 않음
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        usage_section = re.search(r'## 🔍 이용안내\s*\n(.*?)(?=\n##|\n---|\n$)', md_content, re.DOTALL)

        info = {
            'phone': '',
            'address': '',
            'hours': '',
            'closed_days': '',
            'representative_menu': '',
            'michelin_grade': ''
        }

        if usage_section:
            u = usage_section.group(1)
            m = re.search(r'\*\*전화번호\*\*:\s*(.+)', u);         info['phone'] = (m.group(1).strip() if m else '')
            m = re.search(r'\*\*주소\*\*:\s*(.+)', u);             info['address'] = (m.group(1).strip() if m else '')
            m = re.search(r'\*\*영업시간\*\*:\s*(.+)', u);         info['hours'] = (m.group(1).strip() if m else '')
            m = re.search(r'\*\*휴무일\*\*:\s*(.+)', u);           info['closed_days'] = (m.group(1).strip() if m else '')
            m = re.search(r'\*\*미쉐린 등급\*\*:\s*(.+)', u);      info['michelin_grade'] = (m.group(1).strip().replace('⭐','').strip() if m else '')
            m = re.search(r'\*\*대표 메뉴\*\*\s*\n(.+?)(?=\n\n|\*\*|$)', u, re.DOTALL)
            if m:
                menu_text = m.group(1).strip()
                # 너무 길면 2줄만
                lines = [line.strip() for line in menu_text.split('\n') if line.strip()]
                if len(lines) > 2:
                    menu_text = '\n'.join(lines[:2]) + "..."
                info['representative_menu'] = menu_text

        # frontmatter에서 미쉐린 보완
        fm = re.search(r'---\s*\n(.*?)\n---', md_content, re.DOTALL)
        if fm and not info['michelin_grade']:
            mg = re.search(r'michelin_grade:\s*(.+)', fm.group(1))
            if mg:
                info['michelin_grade'] = mg.group(1).strip().strip("'\"")

        return info

    except Exception as e:
        print(f"❌ MD 파일 파싱 오류: {e}")
        return {
            'phone': '', 'address': '', 'hours': '',
            'closed_days': '', 'representative_menu': '',
            'michelin_grade': ''
        }


# 기존 create_hover_popup_content 전부 삭제하고 아래로 교체
def create_hover_popup_content(row, *args, **kwargs) -> str:
    r = row if isinstance(row, dict) else getattr(row, "to_dict", lambda: {})()
    title = (r.get('title') or '맛집').strip()
    file_path = (r.get('file_path') or "").strip()

    category = ""
    food_type = ""
    phone = ""
    rep_menu = ""

    def strip_prices(text: str) -> str:
        # ￦/₩ 금액, '원' 금액 제거
        text = re.sub(r'[￦₩]\s*\d[\d,]*', '', text)
        text = re.sub(r'\d[\d,]*\s*원', '', text)
        return re.sub(r'\s{2,}', ' ', text).strip()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            md = f.read()

        # 분류 정보
        m = re.search(r'\*\*카테고리\*\*:\s*([^\n]+)', md)
        if m: category = m.group(1).strip()
        m = re.search(r'\*\*음식 유형\*\*:\s*([^\n]+)', md)
        if m: food_type = m.group(1).strip()

        # 이용안내
        m = re.search(r'\*\*전화번호\*\*:\s*([^\n]+)', md)
        if m: phone = m.group(1).strip()

        # 대표 메뉴(가격 제거)
        m = re.search(r'\*\*대표 메뉴\*\*\s*\n(.+?)(?=\n\n|\*\*|$)', md, re.DOTALL)
        if m:
            raw = m.group(1).strip()
            lines = [strip_prices(l.lstrip('-').strip()) for l in raw.splitlines() if l.strip()]
            if len(lines) == 1:
                # 한 줄에 여러 메뉴가 붙어있을 때(예: "A ￦10,000 B ￦9,000")
                tokens = [t for t in re.split(r'\s{2,}', lines[0]) if t]
                if len(tokens) > 1:
                    lines = tokens
            rep_menu = ' · '.join([s for s in lines if s][:2])
    except Exception:
        pass

    # 없으면 원본 dict로 폴백 + 최종 정리
    category = (category or r.get('category') or '정보없음').strip()
    food_type = (food_type or r.get('food_type') or '정보없음').strip()
    phone = (phone or r.get('phone') or '').strip()
    rep_menu = strip_prices((rep_menu or (r.get('representative_menu') or '')).strip())
    rep_menu = re.sub(r'\n+', ' ', rep_menu)

    bits = [
        f"<b>{title}</b>",
        f"⭐ {category}",
        f"🍜 {food_type}",
    ]
    if rep_menu:
        bits.append(f"🍽️ {rep_menu}")
    if phone:
        bits.append(f"📞 {phone}")
    return "<br>".join(bits)

# ------------------------------------------------------------
# 지도 + 패널
# ------------------------------------------------------------
def render_restaurant_map_with_sidebar(restaurant_list: List[Dict]):
   """맛집 지도: 모바일+PC 자동스크롤 + 진한보라색 클릭 효과"""
   import pandas as pd
   import plotly.graph_objects as go
   from streamlit_js_eval import streamlit_js_eval
   
   # 상태값 초기화
   if 'show_restaurant_panel' not in st.session_state:
       st.session_state.show_restaurant_panel = False
   if 'selected_panel_restaurant' not in st.session_state:
       st.session_state.selected_panel_restaurant = None
   if 'selected_marker_index' not in st.session_state:
       st.session_state.selected_marker_index = None

   if not restaurant_list:
       st.info("🔍 조건에 맞는 맛집이 없습니다.")
       return

   # 화면 너비 감지 (모바일 판단)
   screen_width = streamlit_js_eval(
       js_expressions='window.innerWidth',
       want_output=True,
       key='screen_width'
   )

   # 모바일 기준: 768px 이하
   is_mobile = screen_width is not None and screen_width <= 768

   # 조건부 높이 설정
   map_height = 350 if is_mobile else 750  # 모바일: 300px, 웹: 700px

   # 🔧 모바일+PC 모두 자동 스크롤 JavaScript
   st.markdown("""
   <script>
   function scrollToPanel() {
       const panel = document.getElementById('restaurant-detail-panel');
       if (panel) {
           panel.scrollIntoView({ 
               behavior: 'smooth', 
               block: 'start',
               inline: 'nearest'
           });
       }
   }
   
   function delayedScroll() {
       setTimeout(scrollToPanel, 300);
   }
   </script>
   """, unsafe_allow_html=True)

   # 필터 변경 감지
   def _filter_signature():
       region = st.session_state.get('selected_restaurant_region', '전체')
       food   = st.session_state.get('selected_restaurant_food_type', '전체')
       cat    = st.session_state.get('selected_restaurant_category', '전체')
       query  = st.session_state.get('restaurant_search_input', '')
       key = (region, food, cat, query)
       import hashlib
       return hashlib.sha1(repr(key).encode()).hexdigest()

   cur_sig  = _filter_signature()
   prev_sig = st.session_state.get("_filter_sig", "")
   if cur_sig != prev_sig:
       st.session_state["_filter_sig"] = cur_sig
       st.session_state.show_restaurant_panel = False
       st.session_state.selected_panel_restaurant = None
       st.session_state.selected_marker_index = None

   # 마커 데이터 구성 (Plotly용)
   @st.cache_data(show_spinner=False, max_entries=64)
   def build_plotly_data(sig: str, base: List[Dict]):
       michelin = [r for r in base if r.get('category') == '미쉐린가이드']
       busan    = [r for r in base if r.get('category') == '부산의맛']
       local    = [r for r in base if r.get('category') == '현지인']
       prio = michelin + busan + local
       
       rows = []
       for idx, r in enumerate(prio):
           lat, lon = r.get('latitude'), r.get('longitude')
           if lat and lon:
               rows.append({
                   'lat': lat,
                   'lon': lon,
                   'title': r.get('title', '맛집'),
                   'category': r.get('category', '현지인'),
                   'hover_text': create_hover_popup_content(r),
                   'index': idx,
                   'file_path': r.get('file_path', ''),
                   'michelin_grade': r.get('michelin_grade', ''),
                   'district': r.get('district', ''),
                   'food_type': r.get('food_type', ''),
                   'address': r.get('address', ''),
                   'phone': r.get('phone', ''),
                   'representative_menu': r.get('representative_menu', ''),
                   'original_data': r  # 원본 데이터 포함
               })
       return rows

   plotly_data = build_plotly_data(cur_sig, restaurant_list)
   by_path = {r.get('file_path'): r for r in restaurant_list}

   col1, col2 = st.columns([7, 3])

   with col1:
       # Plotly 지도 렌더링
       if not plotly_data:
           st.warning("표시할 마커가 없습니다.")
       else:
           # DataFrame 준비
           df = pd.DataFrame(plotly_data)
           df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
           df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
           df = df.dropna(subset=["lat", "lon"])

           # 색/크기 매핑
           df["color"] = df["category"].map({
               "미쉐린가이드": "#FFD700",
               "부산의맛":     "#FF6B6B",
               "현지인":       "#4A90E2"
           }).fillna("#4A90E2")

           df["size"] = df["category"].map({
               "미쉐린가이드": 25,
               "부산의맛":     25,
               "현지인":       25
           }).fillna(12)

           # Figure 생성
           fig = go.Figure()

           # 카테고리별 트레이스
           for category in ["현지인", "부산의맛", "미쉐린가이드"]:
               cat_df = df[df["category"] == category]
               if cat_df.empty:
                   continue

               fig.add_trace(go.Scattermapbox(
                   lat=cat_df["lat"],
                   lon=cat_df["lon"],
                   mode="markers",
                   marker=dict(
                       size=int(cat_df["size"].iloc[0]),
                       color=str(cat_df["color"].iloc[0]),
                       opacity=0.95,
                       symbol="circle"
                   ),
                   text=cat_df["title"],
                   hovertext=cat_df["hover_text"],
                   hoverinfo="text",
                   customdata=cat_df[["index", "file_path"]],
                   name=category,
                   cluster=dict(
                       enabled=True,
                       maxzoom=12,
                       step=1
                   )
               ))

           # 🔧 클릭 시 진한보라색 변화, 다른 마커들은 그대로
           fig.update_traces(
               selected={
                   'marker': {
                       'opacity': 1.0, 
                       'color': '#6B46C1',  # 진한보라색
                       'size': 25           # 크기는 그대로
                   }
               },
               unselected={'marker': {'opacity': 0.95}},  # 다른 마커들 그대로
               selector=dict(type='scattermapbox')
           )

           # 레이아웃
           center_lat = float(df["lat"].mean()) if not df.empty else 35.1796
           center_lon = float(df["lon"].mean()) if not df.empty else 129.0756

           fig.update_layout(
               mapbox=dict(
                   style="open-street-map",
                   center=dict(lat=center_lat, lon=center_lon),
                   zoom=11
               ),
               height=map_height,  # 여기서 조건부 높이 적용
               margin={"r": 0, "t": 0, "l": 0, "b": 0},
               showlegend=True,
               legend=dict(
                   yanchor="top",
                   y=0.99,
                   xanchor="left",
                   x=0.01,
                   bgcolor="rgba(255,255,255,0.85)"
               ),
               hovermode="closest",
               uirevision="keep-zoom-pan"  # 줌/팬 유지
           )

           # 렌더링
           try:
               selected = st.plotly_chart(
                   fig,
                   use_container_width=True,
                   key="restaurant_map_plotly",
                   on_select="rerun",
                   selection_mode="points",
                   config={
                       "scrollZoom": True,
                       "displayModeBar": True,
                       "doubleClick": "reset"
                   }
               )
           except TypeError:
               # 구버전 폴백
               selected = st.plotly_chart(
                   fig,
                   use_container_width=True,
                   key="restaurant_map_plotly",
                   config={
                       "scrollZoom": True,
                       "displayModeBar": True,
                       "doubleClick": "reset"
                   }
               )
               selected = None

           # 포인트 선택 처리
           if selected:
               points = []
               try:
                   if isinstance(selected, dict):
                       points = selected.get("selection", {}).get("points", [])
                   else:
                       sel = getattr(selected, "selection", None)
                       if isinstance(sel, dict):
                           points = sel.get("points", [])
               except Exception:
                   points = []

               if points:
                   point = points[0]
                   customdata = point.get("customdata")
                   if isinstance(customdata, (list, tuple)) and len(customdata) > 0:
                       idx = customdata[0]
                       if idx != st.session_state.get("selected_marker_index"):
                           selected_restaurant = plotly_data[idx]["original_data"]
                           st.session_state.selected_panel_restaurant = selected_restaurant
                           st.session_state.show_restaurant_panel = True
                           st.session_state.selected_marker_index = idx
                           
                           # 🔧 자동 스크롤 JavaScript 실행
                           st.markdown("""
                           <script>
                           delayedScroll();
                           </script>
                           """, unsafe_allow_html=True)
                           
                           st.rerun()

   with col2:
       # 🔧 패널에 고유 ID 추가
       with st.container():
           st.markdown('<div id="restaurant-detail-panel">', unsafe_allow_html=True)
           
           if st.session_state.get("show_restaurant_panel"):
               render_restaurant_side_panel(st.session_state["selected_panel_restaurant"])
           else:
               st.markdown('<h3 style="color: white;">📍 맛집 상세정보</h3>', unsafe_allow_html=True)
            
               st.markdown("""
                <div style="
                    padding: 1rem;
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    border-left: 4px solid #17a2b8;
                    color: white;
                    font-size: 16px;
                    line-height: 1.5;
                    margin: 10px 0;
                    text-align: center;
                ">
                지도에서 마커를 클릭하면<br>
                상세정보가 여기에 표시됩니다
                </div>
                """, unsafe_allow_html=True)
           
           st.markdown('</div>', unsafe_allow_html=True)
   
   # 하단 설명/범례
   st.markdown("---")
   st.markdown("""
**🗺️ 부산 맛집 지도**

**🎯 이용 방법:**
- **마커에 마우스를 올리면** 상세 정보가 팝업으로 표시됩니다
- **마커를 클릭**하면 진한보라색으로 변하며 우측 패널에 상세정보가 나타납니다
- **클릭 시 자동으로** 상세정보 패널로 부드럽게 이동합니다

**지도 조작:**
- **확대/축소**: 마우스 휠 또는 +/- 버튼
- **이동**: 마우스 드래그
""")
   st.markdown("### 🏷️ 지도 범례")
   c1, c2 = st.columns(2)
   with c1:
       st.markdown("**🌟 미쉐린 가이드** (금색)")
   with c2:
       st.markdown("**🔴 부산의맛** / **🔵 현지인**")


def _render_plotly_map(marker_data: List[Dict]):
    """Plotly 지도 렌더링(동그라미 마커 + 클러스터 + 휠줌 유지)"""
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st

    if not marker_data:
        st.warning("표시할 마커가 없습니다.")
        return

    # 1) DataFrame 준비
    df = pd.DataFrame(marker_data)
    # 혹시 문자열이면 숫자로 변환
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])

    # 색/크기 매핑 (동그라미가 더 잘 보이도록 사이즈 업)
    df["color"] = df["category"].map({
        "미쉐린가이드": "#FFD700",  # 금색
        "부산의맛":     "#FF6B6B",  # 살짝 밝은 레드
        "현지인":       "#4A90E2"   # 블루
    }).fillna("#4A90E2")

    df["size"] = df["category"].map({
        "미쉐린가이드": 18,
        "부산의맛":     14,
        "현지인":       12
    }).fillna(12)

    # 2) Figure 생성
    fig = go.Figure()

    # 카테고리별 트레이스 + 클러스터 활성화
    for category in ["현지인", "부산의맛", "미쉐린가이드"]:
        cat_df = df[df["category"] == category]
        if cat_df.empty:
            continue

        fig.add_trace(go.Scattermapbox(
            lat=cat_df["lat"],
            lon=cat_df["lon"],
            mode="markers",
            marker=dict(
                # 클러스터 마커는 테두리 지정 불가 → 색/크기로 가독성 확보
                size=int(cat_df["size"].iloc[0]),
                color=str(cat_df["color"].iloc[0]),
                opacity=1.0,
                symbol="circle"
            ),
            text=cat_df["title"],
            hovertext=cat_df["hover_text"],
            hoverinfo="text",
            customdata=cat_df[["index", "file_path"]],
            name=category,
            cluster=dict(
                enabled=True,
                # 낮을수록 "덜 확대해도" 클러스터가 빨리 풀림
                maxzoom=12,
                step=1
            )
        ))

    # 3) 레이아웃(줌/팬 유지)
    center_lat = float(df["lat"].mean()) if not df["lat"].empty else 35.1796
    center_lon = float(df["lon"].mean()) if not df["lon"].empty else 129.0756

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=11
        ),
        height=700,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.85)"
        ),
        hovermode="closest",
        uirevision="keep-zoom-pan"  # 사용자가 바꾼 줌/팬 유지
    )

    # 4) 렌더링(휠줌/도구바 켜기) + 선택 이벤트(버전 호환)
    try:
        selected = st.plotly_chart(
            fig,
            use_container_width=True,
            key="restaurant_map_plotly",
            on_select="rerun",          # 지원 버전에서만 동작
            selection_mode="points",
            config={
                "scrollZoom": True,     # 마우스 휠 줌
                "displayModeBar": True, # 박스줌/이동/리셋 버튼 보이기
                "doubleClick": "reset"  # 더블클릭 시 보기 리셋
            }
        )
    except TypeError:
        # on_select/selection_mode 미지원 버전 폴백
        selected = st.plotly_chart(
            fig,
            use_container_width=True,
            key="restaurant_map_plotly",
            config={
                "scrollZoom": True,
                "displayModeBar": True,
                "doubleClick": "reset"
            }
        )
        # 여기에 여백 추가
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    # 5) 포인트 선택 처리(지원 버전에서만 값이 들어옴)
    points = []
    try:
        if isinstance(selected, dict):
            points = selected.get("selection", {}).get("points", [])
        else:
            sel = getattr(selected, "selection", None)
            if isinstance(sel, dict):
                points = sel.get("points", [])
    except Exception:
        points = []

    if points:
        point = points[0]
        customdata = point.get("customdata")
        if isinstance(customdata, (list, tuple)) and len(customdata) > 0:
            idx = customdata[0]
            if idx != st.session_state.get("selected_marker_index"):
                selected_restaurant = marker_data[idx]["original_data"]
                st.session_state.selected_panel_restaurant = selected_restaurant
                st.session_state.show_restaurant_panel = True
                st.session_state.selected_marker_index = idx
                st.rerun()

# ------------------------------------------------------------
# 공통 UI
# ------------------------------------------------------------
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
    return 4


def render_header():
    """헤더 렌더링 (4개 탭 네비게이션 포함)"""
    col1, col2 = st.columns([2, 3])

    with col1:
        st.title("🏢 요즘 부산")

    with col2:
        current_page = st.session_state.get('page', 'news')

        # ✅ 기존 3개 → 4개 탭
        tab_col1, tab_col2, tab_col3, tab_col4 = st.columns(4)

        with tab_col1:
            if st.button("📰 보도자료", key="nav_news", use_container_width=True,
                         type="primary" if current_page == 'news' else "secondary"):
                st.session_state.page = 'news'
                st.session_state.items_to_show = 12
                st.rerun()

        with tab_col2:
            if st.button("🍽️ 맛집지도", key="nav_restaurants", use_container_width=True,
                         type="primary" if current_page == 'restaurants' else "secondary"):
                st.session_state.page = 'restaurants'
                st.session_state.restaurant_items_to_show = 12
                st.rerun()

        with tab_col3:
            if st.button("🗺️ 정책지도", key="nav_policy", use_container_width=True,
                         type="primary" if current_page == 'policy' else "secondary"):
                st.session_state.page = 'policy'
                st.rerun()

        with tab_col4:
            if st.button("📋 업무계획", key="nav_plans", use_container_width=True,
                         type="primary" if current_page == 'plans' else "secondary"):
                st.session_state.page = 'plans'
                st.session_state.plans_items_to_show = 12
                st.rerun()

    current_page = st.session_state.get('page', 'news')

    if current_page == 'news':
        st.markdown("### 부산시 최신 보도자료를 알려드립니다")

    elif current_page == 'restaurants':
        st.markdown("### 부산 맛집 정보를 지도에서 확인하세요")

    elif current_page == 'policy':
        st.markdown("### 도시혁신균형실 정책사업을 지도에서 한눈에 확인하세요")
        st.markdown("""

""", unsafe_allow_html=True)

    else:
        st.markdown("### 2025년 부산시 부서별 주요 업무계획을 확인하세요")
        st.markdown("""
<div class="howto-box" style="
    background-color:#374151;
    border-left:4px solid #6b7280;
    border-radius:8px;
    padding:16px;
    line-height:1.6;
">
<p><strong>📋 이용 방법</strong></p>
<ul>
    <li>왼쪽 사이드바에서 <strong>부서별 분류</strong>를 선택하여 원하는 분야의 업무계획을 확인할 수 있습니다</li>
    <li><strong>검색어</strong>를 입력하여 특정 부서나 사업명을 빠르게 찾아보세요</li>
</ul>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 카드/그리드
# ------------------------------------------------------------
def render_news_card_aligned(news_item: Dict, idx: int):
    """보도자료 카드 렌더링 (idx 기반 고유 key 적용)"""
    with st.container():
        # 태그 색상
        if news_item['tags']:
            main_tag = news_item['tags'][0]
            tag_color = TAG_COLORS.get(main_tag, "#6B7280")
        else:
            main_tag = "전체"
            tag_color = "#6B7280"

        # 태그, 날짜 표시
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

        # 제목 박스 색상
        pastel_colors = {
            "#6B7280": "#E5E7EB",
            "#3B82F6": "#DBEAFE",
            "#10B981": "#D1FAE5",
            "#EF4444": "#FEE2E2",
            "#8B5CF6": "#EDE9FE",
            "#F59E0B": "#FEF3C7",
            "#06B6D4": "#CFFAFE",
            "#84CC16": "#ECFCCB",
            "#EC4899": "#FCE7F3"
        }
        pastel_color = pastel_colors.get(tag_color, "#F3F4F6")
        formatted_title = smart_line_break(news_item['title'])

        # 제목 출력
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
                ">
                    <span style="display: block; width: 100%; color: #000000;">{formatted_title}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # summary = news_item.get('detailed_summary', news_item.get('thumbnail_summary', ''))
        # if len(summary) > 120:
        #     summary = summary[:120] + "..."

        # st.markdown(
        #     f"""
        #     <div class="news-summary" style="
        #         margin: 0rem 0 0.5rem 0;
        #         padding: 15px;
        #         background-color: #f8f9fa;
        #         border-radius: 8px;
        #         border-left: 4px solid #dee2e6;
        #         line-height: 1.6;
        #         height: 100px;
        #         overflow: hidden;
        #         display: flex;
        #         align-items: flex-start;
        #         font-size: 14px;
        #         color: #495057;
        #     ">
        #         {summary}
        #     </div>
        #     """,
        #     unsafe_allow_html=True
        # )

        # 상세보기 버튼 (idx 기반 key 보장)
        if st.button(
            "📄 클릭하여 내용 보기",
            key=f"news_detail_btn_{idx}",
            use_container_width=True,
        ):
            st.session_state.selected_news = news_item
            st.session_state.show_detail = True
            st.session_state.scroll_to_top = True
            st.rerun()

        # 카드 간격
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)


def render_restaurant_card(restaurant_item: Dict):
    """맛집 카드 렌더링"""
    with st.container():
        region = restaurant_item.get('region', '기타')
        district = restaurant_item.get('district', '')
        category = restaurant_item.get('category', '현지인')
        food_type = restaurant_item.get('food_type', '한식')
        michelin_grade = restaurant_item.get('michelin_grade', '')

        region_color = RESTAURANT_REGION_COLORS.get(region, "#6B7280")
        category_color = "#FF8C00" if category == "미쉐린가이드" else RESTAURANT_CATEGORY_COLORS.get(category, "#6B7280")

        michelin_emoji = ""
        if michelin_grade == "1스타":       michelin_emoji = " ⭐"
        elif michelin_grade == "빕구르망":  michelin_emoji = " 🍽️"
        elif michelin_grade == "셀렉티드":  michelin_emoji = " ✨"

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

        pastel_colors = {
            "#6B7280": "#E5E7EB",
            "#FF8C00": "#FFE4B5",
            "#EF4444": "#FEE2E2",
            "#10B981": "#D1FAE5",
        }
        pastel_color = pastel_colors.get(category_color, "#F3F4F6")
        formatted_title = smart_line_break(restaurant_item['title'])

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
                ">
                    <span style="display: block; width: 100%; color: #000000;">{formatted_title}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        summary_text = ""
        try:
            with open(restaurant_item['file_path'], 'r', encoding='utf-8') as f:
                md_content = f.read()
            detail_match = re.search(r'## 📍 상세 정보\s*\n(.+?)(?=\n---|\n##|\n$)', md_content, re.DOTALL)
            if detail_match:
                detail_text = detail_match.group(1).strip()
                if len(detail_text) > 120:
                    detail_text = detail_text[:120] + "..."
                summary_text = detail_text
            else:
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
    """업무계획 카드 렌더링"""
    with st.container():
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

        pastel_colors = {
            "#6B7280": "#E5E7EB",
            "#8B5CF6": "#EDE9FE",
            "#EF4444": "#FEE2E2",
            "#F59E0B": "#FEF3C7",
            "#10B981": "#D1FAE5",
            "#06B6D4": "#CFFAFE",
            "#3B82F6": "#DBEAFE"
        }
        pastel_color = pastel_colors.get(category_color, "#F3F4F6")
        formatted_title = smart_line_break(plan_item['title'])

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
                ">
                    <span style="display: block; width: 100%; color: #000000;">{formatted_title}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        summary = plan_item.get('thumbnail_summary', '') or "2025년 주요업무계획"
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
        st.session_state.items_to_show = 24

    current_news = news_list[:st.session_state.items_to_show]
    cols_per_row = get_responsive_columns()

    for i in range(0, len(current_news), cols_per_row):
        cols = st.columns(cols_per_row, gap="small")
        for j in range(cols_per_row):
            if i + j < len(current_news):
                with cols[j]:
                    render_news_card_aligned(current_news[i + j], idx=i+j)
            else:
                with cols[j]:
                    st.markdown("<div style='height: 400px; visibility: hidden;'></div>", unsafe_allow_html=True)

    if st.session_state.items_to_show < len(news_list):
        remaining = len(news_list) - st.session_state.items_to_show
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(f"📄 더 보기 ({remaining}개 남음)", use_container_width=True, type="primary"):
                st.session_state.items_to_show += 24
                st.rerun()


def render_restaurant_grid_with_scroll(restaurant_list: List[Dict]):
    """맛집 그리드 렌더링"""
    if not restaurant_list:
        st.info("🔍 조건에 맞는 맛집이 없습니다.")
        return

    if 'restaurant_items_to_show' not in st.session_state:
        st.session_state.restaurant_items_to_show = 12

    current_restaurants = restaurant_list[:st.session_state.restaurant_items_to_show]
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

    if st.session_state.restaurant_items_to_show < len(restaurant_list):
        remaining = len(restaurant_list) - st.session_state.restaurant_items_to_show
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(f"🍽️ 더 보기 ({remaining}개 남음)", use_container_width=True, type="primary", key="restaurant_load_more"):
                st.session_state.restaurant_items_to_show += 12
                st.rerun()


def render_plans_grid_with_scroll(plans_list: List[Dict]):
    """업무계획 그리드 렌더링"""
    if not plans_list:
        st.info("🔍 조건에 맞는 업무계획이 없습니다.")
        return

    if 'plans_items_to_show' not in st.session_state:
        st.session_state.plans_items_to_show = 12

    current_plans = plans_list[:st.session_state.plans_items_to_show]
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

    if st.session_state.plans_items_to_show < len(plans_list):
        remaining = len(plans_list) - st.session_state.plans_items_to_show
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(f"📋 더 보기 ({remaining}개 남음)", use_container_width=True, type="primary", key="plans_load_more"):
                st.session_state.plans_items_to_show += 12
                st.rerun()

# ------------------------------------------------------------
# 상세 페이지
# ------------------------------------------------------------
def extract_contact_from_content(md_content: str) -> str:
    """마크다운 내용에서 연락처 정보 추출"""
    try:
        contact_pattern = r'## 📞 세부문의\s*\n([^\n#]+)'
        match = re.search(contact_pattern, md_content)
        if match:
            return match.group(1).strip()

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
    except Exception:
        return "문의처 정보 오류"


def render_news_detail(news_item: Dict):
    """보도자료 상세 페이지"""
    if st.session_state.get('scroll_to_top'):
        scroll_to_here(-500, key='news_detail_top')
        st.session_state.scroll_to_top = False

    col1, col2, col3 = st.columns([2, 4, 2])
    with col1:
        if st.button("← 뒤로가기", key="news_back_top", use_container_width=True, type="secondary"):
            st.session_state.show_detail = False
            st.session_state.selected_news = None
            st.rerun()

    st.markdown(f'<h1>{news_item["title"]}</h1>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<p style="font-size: 18px;"><strong>📅 게시일</strong>: {news_item["date"]}</p>', unsafe_allow_html=True)
    with col2:
        if news_item['tags']:
            main_tag = news_item['tags'][0]
            st.markdown(f'<p style="font-size: 18px;"><strong>🏷️ 분야</strong>: #{main_tag}</p>', unsafe_allow_html=True)

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

    with col4:
        if news_item.get('source_url'):
            st.markdown(
                f'<p style="font-size: 18px;"><strong>🔗 <a href="{news_item["source_url"]}" target="_blank" style="color: #white; text-decoration: none;">부산시청 원문</a></strong></p>',
                unsafe_allow_html=True
            )

    st.divider()

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
    if st.button("⬅️ 목록으로 돌아가기", use_container_width=True, key="news_back_btn2"):
        st.session_state.show_detail = False
        st.session_state.selected_news = None
        st.rerun()


def render_restaurant_detail(restaurant_item: Dict):
    """맛집 상세 페이지"""
    if st.session_state.get('scroll_to_top'):
        scroll_to_here(0, key='restaurant_detail_top')
        st.session_state.scroll_to_top = False

    col1, col2, col3 = st.columns([2, 4, 2])
    with col1:
        if st.button("← 뒤로가기", key="restaurant_back_top", use_container_width=True, type="secondary"):
            st.session_state.show_restaurant_detail = False
            st.session_state.selected_restaurant = None
            st.session_state.scroll_to_top = True
            st.rerun()

    title = restaurant_item["title"]
    st.markdown('<div class="detail-page">', unsafe_allow_html=True)
    st.markdown(f'<h1 style="color: white; font-size: 42px; margin-bottom: 30px;">{title}</h1>', unsafe_allow_html=True)

    try:
        with open(restaurant_item['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()

        usage_section = re.search(r'## 🔍 이용안내\s*\n(.*?)(?=\n##|\n---|\n$)', md_content, re.DOTALL)

        phone = address = hours = closed_days = michelin_grade = representative_menu = ""

        if usage_section:
            usage_content = usage_section.group(1)
            m = re.search(r'\*\*전화번호\*\*:\s*(.+)', usage_content);  phone = (m.group(1).strip() if m else '')
            m = re.search(r'\*\*주소\*\*:\s*(.+)', usage_content);      address = (m.group(1).strip() if m else '')
            m = re.search(r'\*\*영업시간\*\*:\s*(.+)', usage_content);  hours = (m.group(1).strip() if m else '')
            m = re.search(r'\*\*휴무일\*\*:\s*(.+)', usage_content);    closed_days = (m.group(1).strip() if m else '')
            m = re.search(r'\*\*미쉐린 등급\*\*:\s*(.+)', usage_content)
            michelin_grade = (m.group(1).strip().replace('⭐','').strip() if m else '')
            m = re.search(r'\*\*대표 메뉴\*\*\s*\n(.+?)(?=\n\n|\*\*|$)', usage_content, re.DOTALL)
            representative_menu = (m.group(1).strip() if m else '')

        frontmatter_match = re.search(r'---\s*\n(.*?)\n---', md_content, re.DOTALL)
        if frontmatter_match and not michelin_grade:
            fm = frontmatter_match.group(1)
            m = re.search(r'michelin_grade:\s*(.+)', fm)
            if m:
                michelin_grade = m.group(1).strip().strip("'\"")

        if michelin_grade:
            grade_emoji = {"1스타": "🌟", "빕구르망": "🍽️", "셀렉티드": "✨"}.get(michelin_grade, "⭐")
            st.markdown(f"""
            <h2 style="color: #FFD700; font-size: 38px; margin: 30px 0 20px 0;">
                {grade_emoji} 미쉐린 등급: {michelin_grade}
            </h2>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
            <h3 style="color: #8B5CF6; font-size: 34px; margin-bottom: 20px;">📍 상세정보</h3>
            <div style="font-family: monospace; margin-left: 20px; font-size: 26px;">
                📍 상세정보<br>
                ├─ 📍 주소 : {address or '정보 없음'}<br>
                ├─ 📞 전화번호 : {phone or '정보 없음'}<br>
                ├─ 🕐 영업시간 : {hours or '정보 없음'}<br>
                └─ 🚫 휴무일 : {closed_days or '정보 없음'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if representative_menu:
            st.markdown(f"""
            <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
                <h3 style="color: #10B981; font-size: 34px; margin-bottom: 15px;">🍽️ 대표메뉴</h3>
                <div style="margin-left: 20px; font-size: 26px;">
                    {representative_menu}
                </div>
            </div>
            """, unsafe_allow_html=True)

        detail_patterns = [
            r'## 📍 상세 정보\s*\n\n(.+?)(?=\n---|\n##|\n$)',
            r'## 📍 상세 정보\s*\n(.+?)(?=\n---|\n##|\n$)'
        ]
        detail_content = None
        for pattern in detail_patterns:
            dm = re.search(pattern, md_content, re.DOTALL)
            if dm:
                detail_content = dm.group(1).strip()
                break

        if detail_content:
            st.markdown(f"""
            <div style="color: white; font-size: 30px; line-height: 1.8; margin: 30px 0;">
                <h3 style="color: #F59E0B; font-size: 34px; margin-bottom: 15px;">📍 상세정보</h3>
                <div style="margin-left: 20px; font-size: 26px; line-height: 1.8;">
                    {detail_content}
                </div>
            </div>
            """, unsafe_allow_html=True)

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
                • <strong>미쉐린 등급:</strong> {michelin_grade or '일반'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        kakao_link = ""
        kakao_match = re.search(r'\*\*카카오맵\*\*:\s*\[([^\]]+)\]\(([^)]+)\)', md_content)
        if kakao_match:
            kakao_link = kakao_match.group(2)

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
                * 식당의 정확한 메뉴가격과 고객 후기는 카카오맵에서 확인하실 수 있습니다
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
        st.session_state.scroll_to_top = True
        st.rerun()


def render_plans_detail(plan_item: Dict):
    """업무계획 상세 페이지"""
    if st.session_state.get('scroll_to_top'):
        scroll_to_here(0, key='plans_detail_top')
        st.session_state.scroll_to_top = False

    col1, col2, col3 = st.columns([2, 4, 2])
    with col1:
        if st.button("← 뒤로가기", key="plans_back_top", use_container_width=True, type="secondary"):
            st.session_state.show_plan_detail = False
            st.session_state.selected_plan = None
            st.rerun()

    st.markdown('<div class="detail-page">', unsafe_allow_html=True)
    st.markdown(f'<h1>{plan_item["title"]}</h1>', unsafe_allow_html=True)

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

    try:
        with open(plan_item['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()

        if md_content.startswith('---'):
            frontmatter_end = md_content.find('---', 3)
            if frontmatter_end > 0:
                md_content = md_content[frontmatter_end + 3:].strip()

        st.markdown(md_content, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다: {e}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()

    if st.button("⬅️ 목록으로 돌아가기", use_container_width=True, key="plans_back_btn2"):
        st.session_state.show_plan_detail = False
        st.session_state.selected_plan = None
        st.rerun()


def render_restaurant_side_panel(restaurant: Dict):
    """사이드 패널: 맛집 주요 정보와 카카오맵 버튼"""
    import re

    title = restaurant.get('title', '맛집')
    st.markdown(f"### 🍽️ {title}")
    
    try:
        with open(restaurant['file_path'], 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # 이용안내 섹션 추출
        usage_section = re.search(r'## 📍 이용안내\s*\n(.*?)(?=\n##|\n---|\n$)', md_content, re.DOTALL)
        
        phone = address = hours = closed_days = michelin_grade = representative_menu = ""
        
        if usage_section:
            usage_content = usage_section.group(1)
            
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
        
        # 미쉐린 등급
        if michelin_grade:
            grade_emoji = {"1스타": "🌟", "빕구르망": "🍽️", "셀렉티드": "✨"}.get(michelin_grade, "⭐")
            st.markdown(f"**{grade_emoji} 미슐랭**: {michelin_grade}")
        
        # 기본 정보
        if address:
            st.markdown(f"**📍 주소**\n{address}")
        if phone:
            st.markdown(f"**📞 전화**\n{phone}")
        if hours:
            st.markdown(f"**🕐 영업시간**\n{hours}")
        if closed_days:
            st.markdown(f"**🚫 휴무일**\n{closed_days}")
        
        # 대표메뉴
        if representative_menu:
            st.markdown(f"**🍽️ 대표메뉴**\n{representative_menu}")
        
        # 상세정보 섹션
        detail_patterns = [
            r'## 📝 상세 정보\s*\n\n(.+?)(?=\n---|\n##|\n$)',
            r'## 📝 상세 정보\s*\n(.+?)(?=\n---|\n##|\n$)',
            r'## 📍 상세 정보\s*\n\n(.+?)(?=\n---|\n##|\n$)',
            r'## 📍 상세 정보\s*\n(.+?)(?=\n---|\n##|\n$)'
        ]
        
        detail_content = None
        for pattern in detail_patterns:
            detail_match = re.search(pattern, md_content, re.DOTALL)
            if detail_match:
                detail_content = detail_match.group(1).strip()
                break
        
        if detail_content:
            st.divider()
            st.markdown("**📝 상세정보**")
            st.markdown("")
            st.markdown(detail_content)
        
        # 카카오맵 버튼
        kakao_link = ""
        kakao_match = re.search(r'\*\*카카오맵\*\*:\s*\[([^\]]+)\]\(([^)]+)\)', md_content)
        if kakao_match:
            kakao_link = kakao_match.group(2)
        
        if kakao_link:
            st.divider()
            st.markdown(
                f"""
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{kakao_link}" target="_blank" style="
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #4A148C;
                        color: white;
                        font-size: 16px;
                        font-weight: bold;
                        border-radius: 8px;
                        text-decoration: none;
                        transition: background-color 0.3s ease;
                    " onmouseover="this.style.backgroundColor='#6A1B9A'" 
                      onmouseout="this.style.backgroundColor='#4A148C'">
                        🗺️ 카카오맵에서 보기
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )
        
    except Exception as e:
        st.error(f"정보 로딩 실패: {e}")
