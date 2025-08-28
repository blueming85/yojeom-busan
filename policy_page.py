"""
부산 정책지도 페이지 - policy_page.py
=========================================
정책 정보를 지도와 카드 형태로 표시하고 필터링/검색 기능 제공
"""

import streamlit as st
from pathlib import Path
import logging
from typing import List, Dict

from config import (
    AVAILABLE_POLICY_REGIONS, POLICY_CATEGORIES,
    POLICY_REGION_COLORS, POLICY_CATEGORY_COLORS
)
from policy_portal import BusanPolicyPortal, get_policy_portal_stats

logger = logging.getLogger(__name__)

# 수동 좌표 매핑 (필요시 추가)
MANUAL_POLICY_COORDS = {
    "부산항": (35.1028, 129.0403),
    "해운대": (35.1631, 129.1640),
    "송도": (35.0758, 129.0128),
    "북항재개발1단계": (35.1184, 129.0494),  # 정확한 제목 매칭
    "북항": (35.1184, 129.0494),  # 부분 매칭용
    "사상드림스마트시티": (35.1490, 128.9770),
    "사상드림": (35.1490, 128.9770)  # 부분 매칭용
}

def show_policy_page():
    """정책지도 메인 페이지"""
    try:
        st.markdown("# 🗺️ 부산 정책지도")
        st.markdown("---")
        
        # 정책 포털 초기화
        portal = BusanPolicyPortal()
        
        if not portal.policy_data:
            st.warning("⚠️ 정책 데이터가 없습니다. 정책 MD 파일을 추가해주세요.")
            st.info(f"📁 정책 파일 위치: {portal.md_dir}")
            return
        
        # 사이드바 필터링
        show_policy_filters(portal)
        
        # 메인 콘텐츠
        if 'policy_filters' not in st.session_state:
            st.session_state.policy_filters = {
                'regions': ["전체"],
                'categories': ["전체"],
                'search': ""
            }
        
        # 필터링된 정책 데이터 가져오기
        filtered_policies = portal.filter_policies(
            selected_regions=st.session_state.policy_filters['regions'],
            selected_categories=st.session_state.policy_filters['categories'],
            search_query=st.session_state.policy_filters['search']
        )
        
        # 결과 표시
        show_policy_results(filtered_policies)
        
        # 통계 정보 (하단)
        show_policy_statistics(portal)
        
    except Exception as e:
        logger.error(f"❌ 정책지도 페이지 오류: {e}")
        st.error("정책지도 페이지 로드 중 오류가 발생했습니다.")

def show_policy_filters(portal: BusanPolicyPortal):
    """사이드바 필터링 UI"""
    with st.sidebar:
        st.markdown("## 🔍 필터 및 검색")
        
        # 검색어 입력
        search_query = st.text_input(
            "검색어", 
            value=st.session_state.policy_filters.get('search', ''),
            placeholder="정책명, 지역, 카테고리 검색...",
            key="policy_search_input"
        )
        st.session_state.policy_filters['search'] = search_query
        
        st.markdown("---")
        
        # 지역별 필터 (멀티셀렉트)
        st.markdown("### 🗺️ 지역별")
        selected_regions = st.multiselect(
            "지역 선택",
            AVAILABLE_POLICY_REGIONS,
            default=st.session_state.policy_filters.get('regions', ["전체"]),
            key="policy_region_filter"
        )
        if not selected_regions:
            selected_regions = ["전체"]
        st.session_state.policy_filters['regions'] = selected_regions
        
        # 지역별 통계 표시
        region_stats = portal.get_region_stats()
        for region in selected_regions:
            if region in region_stats:
                count = region_stats[region]
                color = POLICY_REGION_COLORS.get(region, "#6B7280")
                st.markdown(
                    f'<div class="news-date" style="background-color: {color}; color: white; '
                    f'text-align: center; padding: 5px; border-radius: 5px; margin: 2px 0;">'
                    f'{region}: {count}개</div>',
                    unsafe_allow_html=True
                )
        
        st.markdown("---")
        
        # 카테고리별 필터
        st.markdown("### 🏷️ 카테고리")
        selected_categories = st.multiselect(
            "카테고리 선택",
            POLICY_CATEGORIES,
            default=st.session_state.policy_filters.get('categories', ["전체"]),
            key="policy_category_filter"
        )
        if not selected_categories:
            selected_categories = ["전체"]
        st.session_state.policy_filters['categories'] = selected_categories
        
        # 카테고리별 통계 표시
        category_stats = portal.get_category_stats()
        for category in selected_categories:
            if category in category_stats:
                count = category_stats[category]
                color = POLICY_CATEGORY_COLORS.get(category, "#6B7280")
                st.markdown(
                    f'<div class="news-date" style="background-color: {color}; color: white; '
                    f'text-align: center; padding: 5px; border-radius: 5px; margin: 2px 0;">'
                    f'{category}: {count}개</div>',
                    unsafe_allow_html=True
                )
        
        st.markdown("---")
        
        # 필터 초기화 버튼
        if st.button("🔄 필터 초기화", key="reset_policy_filters"):
            st.session_state.policy_filters = {
                'regions': ["전체"],
                'categories': ["전체"],
                'search': ""
            }
            st.rerun()

def show_policy_results(policies: list):
    """정책 검색 결과 표시"""
    st.markdown(f"## 🎯 검색 결과 ({len(policies)}개)")
    
    if not policies:
        st.info("🔍 검색 조건에 맞는 정책이 없습니다. 필터를 조정해보세요.")
        return
    
    # 탭으로 지도/카드 뷰 구분
    tab1, tab2 = st.tabs(["🗺️ 지도보기", "📋 카드보기"])
    
    with tab1:
        show_policy_map(policies)
    
    with tab2:
        show_policy_cards(policies)

def show_policy_map(policies: list):
    """정책 지도 표시"""
    import plotly.graph_objects as go
    import pandas as pd

    st.markdown("### 🗺️ 정책지도")

    if not policies:
        st.info("🔍 조건에 맞는 정책이 없습니다.")
        return

    # 좌표가 있는 것만 추출
    map_rows = []
    for p in policies:
        lat = p.get('latitude') or p.get('lat')
        lon = p.get('longitude') or p.get('lon')
        title = p.get("title", "정책사업")

        # 좌표가 없으면 수동 매핑 시도
        if not lat or not lon:
            for key, (plat, plon) in MANUAL_POLICY_COORDS.items():
                if key in title.replace(" ", ""):
                    lat, lon = plat, plon
                    break

        # 좌표가 확정되면 리스트에 추가
        if lat and lon:
            map_rows.append({
                "lat": lat,
                "lon": lon,
                "title": title,
                "category": p.get("category", "기타"),
                "hover_text": create_policy_hover_text(p),
                "_raw": p,
            })

    if not map_rows:
        st.warning("지도에 표시할 좌표 정보가 없습니다.")
        return

    df = pd.DataFrame(map_rows)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])

    # 카테고리 색상 매핑
    color_map = {
        "미래혁신": "#8B5CF6",
        "15분도시": "#10B981",
        "철도항만": "#3B82F6",
        "건설인프라": "#F59E0B",
    }
    df["color"] = df["category"].map(color_map).fillna("#6B7280")
    df["size"] = 15

    # 지도 생성
    fig = go.Figure()
    for cat, group in df.groupby("category"):
        fig.add_trace(go.Scattermapbox(
            lat=group["lat"],
            lon=group["lon"],
            mode="markers",
            marker=dict(size=int(group["size"].iloc[0]), color=str(group["color"].iloc[0]), opacity=0.85),
            text=group["title"],
            hovertext=group["hover_text"],
            hoverinfo="text",
            name=cat
        ))

    center_lat = float(df["lat"].mean()) if not df.empty else 35.1796
    center_lon = float(df["lon"].mean()) if not df.empty else 129.0756

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=10
        ),
        height=600,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.85)"
        ),
        uirevision="policy_map",
        dragmode="zoom",
    )

    # 지도 표시
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"scrollZoom": True, "displayModeBar": True, "doubleClick": "reset"}
    )

    # 범례 설명
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**🔮 미래혁신** (보라)")
    with col2:
        st.markdown("**🏙️ 15분도시** (초록)")
    with col3:
        st.markdown("**🚅 철도항만** (파랑)")
    with col4:
        st.markdown("**🏗️ 건설인프라** (주황)")

def render_policy_map_with_sidebar(policies: list):
    """정책 지도: 모바일+PC 자동스크롤 + 진한보라색 클릭 효과"""
    import pandas as pd
    import plotly.graph_objects as go
    
    # 상태값 초기화
    if 'show_policy_panel' not in st.session_state:
        st.session_state.show_policy_panel = False
    if 'selected_panel_policy' not in st.session_state:
        st.session_state.selected_panel_policy = None
    if 'selected_policy_marker_index' not in st.session_state:
        st.session_state.selected_policy_marker_index = None

    if not policies:
        st.info("🔍 조건에 맞는 정책이 없습니다.")
        return

    # 자동 스크롤 JavaScript
    st.markdown("""
    <script>
    function scrollToPolicyPanel() {
        const panel = document.getElementById('policy-detail-panel');
        if (panel) {
            panel.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start',
                inline: 'nearest'
            });
        }
    }
    
    function delayedPolicyScroll() {
        setTimeout(scrollToPolicyPanel, 300);
    }
    </script>
    """, unsafe_allow_html=True)

    # 필터 변경 감지
    def _filter_signature():
        region = st.session_state.get('selected_policy_region', '전체')
        cat = st.session_state.get('selected_policy_category', '전체')
        query = st.session_state.get('policy_search_input', '')
        key = (region, cat, query)
        import hashlib
        return hashlib.sha1(repr(key).encode()).hexdigest()

    cur_sig = _filter_signature()
    prev_sig = st.session_state.get("_policy_filter_sig", "")
    if cur_sig != prev_sig:
        st.session_state["_policy_filter_sig"] = cur_sig
        st.session_state.show_policy_panel = False
        st.session_state.selected_panel_policy = None
        st.session_state.selected_policy_marker_index = None

    # 마커 데이터 구성 (Plotly용)
    @st.cache_data(show_spinner=False, max_entries=64)
    def build_plotly_policy_data(sig: str, base: List[Dict]):
        rows = []
        for idx, p in enumerate(base):
            lat, lon = p.get('latitude') or p.get('lat'), p.get('longitude') or p.get('lon')
            if lat and lon:
                rows.append({
                    'lat': lat,
                    'lon': lon,
                    'title': p.get('title', '정책사업'),
                    'category': p.get('category', '기타'),
                    'hover_text': create_policy_hover_text(p),
                    'index': idx,
                    'file_path': p.get('file_path', ''),
                    'location': p.get('location', ''),
                    'period': p.get('period', ''),
                    'budget': p.get('budget', ''),
                    'original_data': p
                })
        return rows

    plotly_data = build_plotly_policy_data(cur_sig, policies)

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
                "미래혁신": "#8B5CF6",
                "15분도시": "#10B981",
                "철도항만": "#3B82F6",
                "건설인프라": "#F59E0B",
            }).fillna("#6B7280")

            df["size"] = 20

            # Figure 생성
            fig = go.Figure()

            # 카테고리별 트레이스
            for category in ["미래혁신", "15분도시", "철도항만", "건설인프라"]:
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
                    name=category
                ))

            # 클릭 시 진한보라색 변화
            fig.update_traces(
                selected={
                    'marker': {
                        'opacity': 1.0, 
                        'color': '#6B46C1',
                        'size': 25
                    }
                },
                unselected={'marker': {'opacity': 0.95}},
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
                uirevision="keep-policy-zoom-pan"
            )

            # 렌더링
            try:
                selected = st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key="policy_map_plotly",
                    on_select="rerun",
                    selection_mode="points",
                    config={
                        "scrollZoom": True,
                        "displayModeBar": True,
                        "doubleClick": "reset"
                    }
                )
            except TypeError:
                selected = st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key="policy_map_plotly",
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
                        if idx != st.session_state.get("selected_policy_marker_index"):
                            selected_policy = plotly_data[idx]["original_data"]
                            st.session_state.selected_panel_policy = selected_policy
                            st.session_state.show_policy_panel = True
                            st.session_state.selected_policy_marker_index = idx
                            
                            # 자동 스크롤 JavaScript 실행
                            st.markdown("""
                            <script>
                            delayedPolicyScroll();
                            </script>
                            """, unsafe_allow_html=True)
                            
                            st.rerun()

    with col2:
        # 패널에 고유 ID 추가
        with st.container():
            st.markdown('<div id="policy-detail-panel">', unsafe_allow_html=True)
            
            if st.session_state.get("show_policy_panel"):
                render_policy_side_panel(st.session_state["selected_panel_policy"])
            else:
                st.markdown('<h3 style="color: white;">🗺️ 정책 상세정보</h3>', unsafe_allow_html=True)
             
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
    st.markdown("### 🏷️ 지도 범례")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown("**🔮 미래혁신** (보라)")
    c2.markdown("**🏙️ 15분도시** (초록)")
    c3.markdown("**🚅 철도항만** (파랑)")
    c4.markdown("**🏗️ 건설인프라** (주황)")

def create_policy_hover_text(policy: dict) -> str:
    """정책 호버 텍스트 생성"""
    title = policy.get('title', '정책사업')
    category = policy.get('category', '기타')
    location = policy.get('location', '')
    period = policy.get('period', '')
    budget = policy.get('budget', '')
    
    hover_lines = [f"<b>{title}</b>"]
    hover_lines.append(f"🏷️ {category}")
    
    if location:
        hover_lines.append(f"📍 {location}")
    if period:
        hover_lines.append(f"📅 {period}")
    if budget:
        hover_lines.append(f"💰 {budget}")
    
    return "<br>".join(hover_lines)

def show_policy_cards(policies: list):
    """정책 카드 표시"""
    # 페이지네이션 설정
    items_per_page = 12
    total_pages = (len(policies) + items_per_page - 1) // items_per_page
    
    if 'policy_page' not in st.session_state:
        st.session_state.policy_page = 1
    
    # 페이지 선택
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            page = st.selectbox(
                "페이지 선택",
                range(1, total_pages + 1),
                index=st.session_state.policy_page - 1,
                key="policy_page_selector"
            )
            st.session_state.policy_page = page
    
    # 현재 페이지 데이터
    start_idx = (st.session_state.policy_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_policies = policies[start_idx:end_idx]
    
    # 정책 카드 표시 (3열)
    cols = st.columns(3)
    for idx, policy in enumerate(current_policies):
        col = cols[idx % 3]
        with col:
            show_policy_card(policy)

def show_policy_card(policy: dict):
    """개별 정책 카드 표시"""
    try:
        title = policy.get('title', '정책사업')
        location = policy.get('location', '위치 미상')
        category = policy.get('category', '기타')
        area = policy.get('area', '')
        period = policy.get('period', '')
        budget = policy.get('budget', '')
        lat = policy.get('lat') or policy.get('latitude')
        lon = policy.get('lon') or policy.get('longitude')
        
        # 카테고리별 색상
        category_color = POLICY_CATEGORY_COLORS.get(category, "#6B7280")
        
        # 카테고리별 이모지
        category_emoji = {
            "미래혁신": "🔮",
            "15분도시": "🏙️", 
            "철도항만": "🚅",
            "건설인프라": "🏗️"
        }.get(category, "📋")
        
        # 정책 제목 박스
        st.markdown(
            f'<div class="news-title-box" style="background-color: {category_color}; color: white; '
            f'padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px;">'
            f'<div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">{title}</div>'
            f'<div style="font-size: 14px; opacity: 0.9;">{category_emoji} {category}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # 기본 정보 표시 순서 개선
        if location and location != '위치 미상':
            st.markdown(f"**📍 위치:** {location}")
        
        if area:
            st.markdown(f"**📏 면적:** {area}")
        
        if period:
            # 기간 정보를 더 읽기 좋게 표시
            period_display = period.replace('~', ' ~ ')
            st.markdown(f"**📅 기간:** {period_display}")
        
        if budget:
            # 예산 정보 표시 개선
            budget_display = budget
            if '억' in budget or '조' in budget:
                # 이미 한국어 단위가 있는 경우 그대로 표시
                pass
            elif budget.replace(',', '').replace('.', '').isdigit():
                # 숫자만 있는 경우 억 단위로 변환
                try:
                    amount = int(budget.replace(',', ''))
                    budget_display = f"{amount:,}원"
                except:
                    pass
            st.markdown(f"**💰 예산:** {budget_display}")
        
        # 좌표 정보가 있으면 표시 (개발 단계에서만)
        if lat and lon:
            st.markdown(f"**📍 좌표:** {lat}, {lon}", help="지도에서 위치를 확인할 수 있습니다")
        
        # 카테고리 태그
        st.markdown(
            f'<div style="text-align: center; margin-top: 10px;">'
            f'<span style="background-color: {category_color}; color: white; '
            f'padding: 3px 8px; border-radius: 12px; font-size: 12px;">{category}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # 상세보기 버튼
        if st.button(f"상세보기", key=f"detail_{policy.get('file_path', '')}", use_container_width=True):
            show_policy_detail(policy)
        
        st.markdown("---")
        
    except Exception as e:
        logger.error(f"❌ 정책 카드 표시 오류: {e}")
        st.error("정책 정보 표시 중 오류가 발생했습니다.")

def show_policy_detail(policy: dict):
    """정책 상세 정보 모달"""
    try:
        title = policy.get('title', '정책사업')
        category = policy.get('category', '기타')
        category_emoji = {
            "미래혁신": "🔮",
            "15분도시": "🏙️", 
            "철도항만": "🚅",
            "건설인프라": "🏗️"
        }.get(category, "📋")
        
        # 상세 정보 표시를 위한 새로운 컨테이너
        with st.expander(f"📍 {title} {category_emoji} 상세 정보", expanded=True):
            # 파일에서 전체 내용 읽기
            file_path = policy.get('file_path')
            if file_path and Path(file_path).exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # frontmatter 제거하고 본문만 표시
                    if content.startswith('---'):
                        frontmatter_end = content.find('---', 3)
                        if frontmatter_end > 0:
                            body = content[frontmatter_end + 3:].strip()
                            st.markdown(
                                f'<div class="detail-page">{body}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(content)
                    else:
                        st.markdown(content)
                        
                except Exception as e:
                    logger.error(f"❌ 파일 읽기 오류: {e}")
                    st.error("상세 정보를 불러올 수 없습니다.")
            else:
                # 파일이 없으면 기본 정보만 표시
                st.markdown(f"**📋 정책명:** {title}")
                st.markdown(f"**🏷️ 카테고리:** {category_emoji} {category}")
                
                location = policy.get('location', '')
                if location:
                    st.markdown(f"**📍 위치:** {location}")
                
                area = policy.get('area', '')
                if area:
                    st.markdown(f"**📏 면적:** {area}")
                
                period = policy.get('period', '')
                if period:
                    st.markdown(f"**📅 추진기간:** {period}")
                
                budget = policy.get('budget', '')
                if budget:
                    st.markdown(f"**💰 예산:** {budget}")
                
                detailed_info = policy.get('detailed_info', '')
                if detailed_info:
                    st.markdown(f"**📝 상세내용:**")
                    st.markdown(detailed_info)
                
                st.info("📄 상세 정보 파일이 없습니다.")
                
    except Exception as e:
        logger.error(f"❌ 정책 상세 정보 표시 오류: {e}")
        st.error("상세 정보 표시 중 오류가 발생했습니다.")

def show_policy_statistics(portal: BusanPolicyPortal):
    """정책 통계 정보 표시"""
    try:
        st.markdown("---")
        st.markdown("## 📊 부산 정책지도 통계")
        
        stats = get_policy_portal_stats(portal)
        
        # 기본 통계
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("전체 정책", f"{stats['total_policies']}개")
        
        with col2:
            st.metric("지역 수", f"{stats['region_count']}곳")
        
        with col3:
            st.metric("카테고리", f"{stats['category_count']}가지")
        
        with col4:
            st.metric("구/군 수", f"{len(AVAILABLE_POLICY_REGIONS)-1}곳")
        
        st.markdown("---")
        
        # 상세 통계 (접을 수 있는 형태)
        with st.expander("📈 상세 통계 보기"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🗺️ 지역별 분포")
                region_stats = stats['region_distribution']
                for region, count in region_stats.items():
                    if region != "전체":
                        color = POLICY_REGION_COLORS.get(region, "#6B7280")
                        percentage = (count / stats['total_policies'] * 100) if stats['total_policies'] > 0 else 0
                        st.markdown(
                            f'<div style="display: flex; justify-content: space-between; '
                            f'background-color: {color}; color: white; padding: 5px 10px; '
                            f'border-radius: 5px; margin: 2px 0;">'
                            f'<span>{region}</span>'
                            f'<span>{count}개 ({percentage:.1f}%)</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                
                # 인기 정보
                st.markdown("### 🏆 인기 순위")
                st.info(f"**인기 지역:** {stats['most_popular_region'][0]} ({stats['most_popular_region'][1]}개)")
                st.info(f"**인기 카테고리:** {stats['most_popular_category'][0]} ({stats['most_popular_category'][1]}개)")
            
            with col2:
                st.markdown("### 🏷️ 카테고리별 분포")
                category_stats = stats['category_distribution']
                for category, count in category_stats.items():
                    if category != "전체":
                        color = POLICY_CATEGORY_COLORS.get(category, "#6B7280")
                        percentage = (count / stats['total_policies'] * 100) if stats['total_policies'] > 0 else 0
                        emoji = {
                            "미래혁신": "🔮",
                            "15분도시": "🏙️", 
                            "철도항만": "🚅",
                            "건설인프라": "🏗️"
                        }.get(category, "📋")
                        
                        st.markdown(
                            f'<div style="display: flex; justify-content: space-between; '
                            f'background-color: {color}; color: white; padding: 5px 10px; '
                            f'border-radius: 5px; margin: 2px 0;">'
                            f'<span>{emoji} {category}</span>'
                            f'<span>{count}개 ({percentage:.1f}%)</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
       
    except Exception as e:
        logger.error(f"❌ 정책 통계 표시 오류: {e}")
        st.error("통계 정보 표시 중 오류가 발생했습니다.")

def show_featured_policies(portal: BusanPolicyPortal):
    """추천 정책 섹션"""
    try:
        st.markdown("## ⭐ 추천 정책")
        
        # 최신 정책 6개 추천
        featured = portal.policy_data[:6] if len(portal.policy_data) >= 6 else portal.policy_data
        
        if not featured:
            st.info("추천할 정책이 없습니다.")
            return
        
        # 추천 정책 카드 (2열)
        cols = st.columns(2)
        for idx, policy in enumerate(featured):
            col = cols[idx % 2]
            with col:
                show_policy_card(policy)
                
    except Exception as e:
        logger.error(f"❌ 추천 정책 표시 오류: {e}")
        st.error("추천 정책 표시 중 오류가 발생했습니다.")


def render_policy_side_panel(policy: Dict):
    """사이드 패널: 정책 주요 정보와 상세보기"""
    import re

    title = policy.get('title', '정책사업')
    st.markdown(f"### 🗺️ {title}")
    
    try:
        # 기본 정보 표시
        location = policy.get('location', '')
        if location:
            st.markdown(f"**📍 위치**\n{location}")
        
        category = policy.get('category', '기타')
        if category:
            category_emoji = {
                "미래혁신": "🔮",
                "15분도시": "🏙️", 
                "철도항만": "🚅",
                "건설인프라": "🏗️"
            }.get(category, "📋")
            st.markdown(f"**🏷️ 카테고리**\n{category_emoji} {category}")
        
        area = policy.get('area', '')
        if area:
            st.markdown(f"**📏 면적**\n{area}")
        
        period = policy.get('period', '')
        if period:
            st.markdown(f"**📅 추진기간**\n{period}")
        
        budget = policy.get('budget', '')
        if budget:
            st.markdown(f"**💰 예산**\n{budget}")
        
        # 파일에서 상세 내용 읽기
        file_path = policy.get('file_path')
        if file_path and Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # frontmatter 제거하고 본문만 표시
                if content.startswith('---'):
                    frontmatter_end = content.find('---', 3)
                    if frontmatter_end > 0:
                        body = content[frontmatter_end + 3:].strip()
                        
                        # 주요내용 섹션
                        main_content = re.search(r'## 🛠️ 주요내용\s*\n(.*?)(?=\n##|\n---|\n$)', body, re.DOTALL)
                        if main_content:
                            st.markdown("**🛠️ 주요내용**")
                            content_text = main_content.group(1).strip()
                            st.markdown(content_text)
                        
                        # 추진상황 섹션
                        status_content = re.search(r'## 🔍 추진상황\s*\n(.*?)(?=\n##|\n---|\n$)', body, re.DOTALL)
                        if status_content:
                            st.markdown("**🔍 추진상황**")
                            status_text = status_content.group(1).strip()
                            st.markdown(status_text)
                        
                        # 향후계획 섹션 (다양한 패턴 검색)
                        future_patterns = [
                            r'## 📈 향후계획\s*\n(.*?)(?=\n##|\n---|\Z)',
                            r'## 📈향후계획\s*\n(.*?)(?=\n##|\n---|\Z)',
                            r'##📈 향후계획\s*\n(.*?)(?=\n##|\n---|\Z)',
                            r'## 향후계획\s*\n(.*?)(?=\n##|\n---|\Z)',
                            r'##향후계획\s*\n(.*?)(?=\n##|\n---|\Z)',
                            r'## 📈 향후 계획\s*\n(.*?)(?=\n##|\n---|\Z)',
                            r'## 향후 계획\s*\n(.*?)(?=\n##|\n---|\Z)'
                        ]
        
                        future_content = None
                        for pattern in future_patterns:
                            future_content = re.search(pattern, body, re.DOTALL)
                            if future_content:
                                break
                        
                        if future_content:
                            st.markdown("**📈 향후계획**")
                            future_text = future_content.group(1).strip()
                            st.markdown(future_text)
                        
                        # 디버깅을 위해 섹션 헤더들 확인
                        section_headers = re.findall(r'^##\s*.*$', body, re.MULTILINE)
                        if not future_content:
                            st.markdown("**🔍 디버깅 정보**")
                            st.write("파일에서 발견된 섹션 헤더들:")
                            for header in section_headers:
                                st.write(f"- {header}")
                        
            except Exception as e:
                st.error(f"정보 로딩 실패: {e}")
        
    except Exception as e:
        st.error(f"정보 로딩 실패: {e}")


# 테스트 함수
def test_policy_page():
    """정책지도 페이지 테스트"""
    print("🧪 정책지도 페이지 테스트 시작...")
    try:
        show_policy_page()
        print("✅ 정책지도 페이지 테스트 완료")
    except Exception as e:
        print(f"❌ 정책지도 페이지 테스트 실패: {e}")


if __name__ == "__main__":
    test_policy_page()