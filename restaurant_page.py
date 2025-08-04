"""
부산 맛집 정보 페이지 - restaurant_page.py
=========================================
맛집 정보를 카드 형태로 표시하고 필터링/검색 기능 제공
"""

import streamlit as st
from pathlib import Path
import logging

from config import (
   AVAILABLE_RESTAURANT_REGIONS, RESTAURANT_FOOD_TYPES, AVAILABLE_RESTAURANT_CATEGORIES,
   RESTAURANT_REGION_COLORS, RESTAURANT_FOOD_TYPE_COLORS, RESTAURANT_CATEGORY_COLORS
)
from restaurant_portal import BusanRestaurantPortal, get_restaurant_portal_stats

logger = logging.getLogger(__name__)

def show_restaurant_page():
   """맛집 정보 메인 페이지"""
   try:
       st.markdown("# 🍽️ 부산 맛집 정보")
       st.markdown("---")
       
       # 맛집 포털 초기화
       portal = BusanRestaurantPortal()
       
       if not portal.restaurants_data:
           st.warning("⚠️ 맛집 데이터가 없습니다. 맛집 MD 파일을 추가해주세요.")
           st.info(f"📁 맛집 파일 위치: {portal.md_dir}")
           return
       
       # 사이드바 필터링
       show_restaurant_filters(portal)
       
       # 메인 콘텐츠
       if 'restaurant_filters' not in st.session_state:
           st.session_state.restaurant_filters = {
               'regions': ["전체"],
               'food_types': ["전체"], 
               'categories': ["전체"],
               'search': ""
           }
       
       # 필터링된 맛집 데이터 가져오기
       filtered_restaurants = portal.filter_restaurants(
           selected_regions=st.session_state.restaurant_filters['regions'],
           selected_food_types=st.session_state.restaurant_filters['food_types'],
           selected_categories=st.session_state.restaurant_filters['categories'],
           search_query=st.session_state.restaurant_filters['search']
       )
       
       # 결과 표시
       show_restaurant_results(filtered_restaurants)
       
       # 통계 정보 (하단)
       show_restaurant_statistics(portal)
       
   except Exception as e:
       logger.error(f"❌ 맛집 페이지 오류: {e}")
       st.error("맛집 페이지 로드 중 오류가 발생했습니다.")

def show_restaurant_filters(portal: BusanRestaurantPortal):
   """사이드바 필터링 UI"""
   with st.sidebar:
       st.markdown("## 🔍 필터 및 검색")
       
       # 검색어 입력
       search_query = st.text_input(
           "검색어", 
           value=st.session_state.restaurant_filters.get('search', ''),
           placeholder="맛집명, 지역, 음식종류 검색...",
           key="restaurant_search_input"
       )
       st.session_state.restaurant_filters['search'] = search_query
       
       st.markdown("---")
       
       # 지역별 필터 (멀티셀렉트)
       st.markdown("### 🗺️ 지역별")
       selected_regions = st.multiselect(
           "지역 선택",
           AVAILABLE_RESTAURANT_REGIONS,
           default=st.session_state.restaurant_filters.get('regions', ["전체"]),
           key="restaurant_region_filter"
       )
       if not selected_regions:
           selected_regions = ["전체"]
       st.session_state.restaurant_filters['regions'] = selected_regions
       
       # 지역별 통계 표시
       region_stats = portal.get_region_stats()
       for region in selected_regions:
           if region in region_stats:
               count = region_stats[region]
               color = RESTAURANT_REGION_COLORS.get(region, "#6B7280")
               st.markdown(
                   f'<div class="news-date" style="background-color: {color}; color: white; '
                   f'text-align: center; padding: 5px; border-radius: 5px; margin: 2px 0;">'
                   f'{region}: {count}개</div>',
                   unsafe_allow_html=True
               )
       
       st.markdown("---")
       
       # 음식타입별 필터
       st.markdown("### 🍜 음식종류")
       selected_food_types = st.multiselect(
           "음식종류 선택",
           RESTAURANT_FOOD_TYPES,
           default=st.session_state.restaurant_filters.get('food_types', ["전체"]),
           key="restaurant_food_type_filter"
       )
       if not selected_food_types:
           selected_food_types = ["전체"]
       st.session_state.restaurant_filters['food_types'] = selected_food_types
       
       # 음식타입별 통계 표시
       food_type_stats = portal.get_food_type_stats()
       for food_type in selected_food_types:
           if food_type in food_type_stats:
               count = food_type_stats[food_type]
               color = RESTAURANT_FOOD_TYPE_COLORS.get(food_type, "#6B7280")
               st.markdown(
                   f'<div class="news-date" style="background-color: {color}; color: white; '
                   f'text-align: center; padding: 5px; border-radius: 5px; margin: 2px 0;">'
                   f'{food_type}: {count}개</div>',
                   unsafe_allow_html=True
               )
       
       st.markdown("---")
       
       # 카테고리별 필터
       st.markdown("### ⭐ 카테고리")
       selected_categories = st.multiselect(
           "카테고리 선택",
           AVAILABLE_RESTAURANT_CATEGORIES,
           default=st.session_state.restaurant_filters.get('categories', ["전체"]),
           key="restaurant_category_filter"
       )
       if not selected_categories:
           selected_categories = ["전체"]
       st.session_state.restaurant_filters['categories'] = selected_categories
       
       # 카테고리별 통계 표시
       category_stats = portal.get_category_stats()
       for category in selected_categories:
           if category in category_stats:
               count = category_stats[category]
               color = RESTAURANT_CATEGORY_COLORS.get(category, "#6B7280")
               st.markdown(
                   f'<div class="news-date" style="background-color: {color}; color: white; '
                   f'text-align: center; padding: 5px; border-radius: 5px; margin: 2px 0;">'
                   f'{category}: {count}개</div>',
                   unsafe_allow_html=True
               )
       
       st.markdown("---")
       
       # 필터 초기화 버튼
       if st.button("🔄 필터 초기화", key="reset_restaurant_filters"):
           st.session_state.restaurant_filters = {
               'regions': ["전체"],
               'food_types': ["전체"],
               'categories': ["전체"],
               'search': ""
           }
           st.rerun()

def show_restaurant_results(restaurants: list):
   """맛집 검색 결과 표시"""
   st.markdown(f"## 🎯 검색 결과 ({len(restaurants)}개)")
   
   if not restaurants:
       st.info("🔍 검색 조건에 맞는 맛집이 없습니다. 필터를 조정해보세요.")
       return
   
   # 페이지네이션 설정
   items_per_page = 12
   total_pages = (len(restaurants) + items_per_page - 1) // items_per_page
   
   if 'restaurant_page' not in st.session_state:
       st.session_state.restaurant_page = 1
   
   # 페이지 선택
   if total_pages > 1:
       col1, col2, col3 = st.columns([1, 2, 1])
       with col2:
           page = st.selectbox(
               "페이지 선택",
               range(1, total_pages + 1),
               index=st.session_state.restaurant_page - 1,
               key="restaurant_page_selector"
           )
           st.session_state.restaurant_page = page
   
   # 현재 페이지 데이터
   start_idx = (st.session_state.restaurant_page - 1) * items_per_page
   end_idx = start_idx + items_per_page
   current_restaurants = restaurants[start_idx:end_idx]
   
   # 맛집 카드 표시 (3열)
   cols = st.columns(3)
   for idx, restaurant in enumerate(current_restaurants):
       col = cols[idx % 3]
       with col:
           show_restaurant_card(restaurant)

def show_restaurant_card(restaurant: dict):
   """🔧 개별 맛집 카드 표시 (미슐랭 등급 포함)"""
   try:
       title = restaurant.get('title', '맛집')
       region = restaurant.get('region', '기타')
       district = restaurant.get('district', '')
       category = restaurant.get('category', '현지인')
       food_type = restaurant.get('food_type', '한식')
       representative_menu = restaurant.get('representative_menu', '')
       address = restaurant.get('address', '')
       phone = restaurant.get('phone', '')
       hours = restaurant.get('hours', '')
       michelin_grade = restaurant.get('michelin_grade', '')  # 🔧 추가
       
       # 카테고리별 색상
       category_color = RESTAURANT_CATEGORY_COLORS.get(category, "#6B7280")
       
       # 🔧 미슐랭 등급별 이모지 추가
       michelin_emoji = ""
       if michelin_grade:
           if michelin_grade == "1스타":
               michelin_emoji = " ⭐"
           elif michelin_grade == "빕구르망":
               michelin_emoji = " 🍽️"
           elif michelin_grade == "셀렉티드":
               michelin_emoji = " ✨"
       
       # 맛집 제목 박스
       st.markdown(
           f'<div class="news-title-box" style="background-color: {category_color}; color: white; '
           f'padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px;">'
           f'<div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">{title}{michelin_emoji}</div>'
           f'<div style="font-size: 14px; opacity: 0.9;">{district} · {food_type}</div>'
           f'</div>',
           unsafe_allow_html=True
       )
       
       # 🔧 미슐랭 등급 표시
       if michelin_grade:
           if michelin_grade == "1스타":
               st.markdown("**⭐ 미슐랭 1스타**")
           elif michelin_grade == "빕구르망":
               st.markdown("**🍽️ 미슐랭 빕구르망**")
           elif michelin_grade == "셀렉티드":
               st.markdown("**✨ 미슐랭 셀렉티드**")
       
       # 대표메뉴
       if representative_menu:
           # 🔧 리스트 형태로 들어온 경우 처리
           if isinstance(representative_menu, list):
               representative_menu = ', '.join(representative_menu)
           st.markdown(f"**🍽️ 대표메뉴:** {representative_menu}")
       
       # 주소
       if address:
           st.markdown(f"**📍 주소:** {address}")
       
       # 연락처
       if phone:
           st.markdown(f"**📞 전화:** {phone}")
       
       # 영업시간
       if hours:
           st.markdown(f"**🕐 영업시간:** {hours}")
       
       # 카테고리 태그
       st.markdown(
           f'<div style="text-align: center; margin-top: 10px;">'
           f'<span style="background-color: {category_color}; color: white; '
           f'padding: 3px 8px; border-radius: 12px; font-size: 12px;">{category}</span>'
           f'</div>',
           unsafe_allow_html=True
       )
       
       # 상세보기 버튼
       if st.button(f"상세보기", key=f"detail_{restaurant.get('file_path', '')}", use_container_width=True):
           show_restaurant_detail(restaurant)
       
       st.markdown("---")
       
   except Exception as e:
       logger.error(f"❌ 맛집 카드 표시 오류: {e}")
       st.error("맛집 정보 표시 중 오류가 발생했습니다.")

def show_restaurant_detail(restaurant: dict):
   """맛집 상세 정보 모달"""
   try:
       title = restaurant.get('title', '맛집')
       michelin_grade = restaurant.get('michelin_grade', '')
       
       # 🔧 미슐랭 등급 포함한 제목
       detail_title = f"📍 {title}"
       if michelin_grade:
           if michelin_grade == "1스타":
               detail_title += " ⭐"
           elif michelin_grade == "빕구르망":
               detail_title += " 🍽️"
           elif michelin_grade == "셀렉티드":
               detail_title += " ✨"
       
       # 상세 정보 표시를 위한 새로운 컨테이너
       with st.expander(f"{detail_title} 상세 정보", expanded=True):
           # 파일에서 전체 내용 읽기
           file_path = restaurant.get('file_path')
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
               st.markdown(f"**🏪 맛집명:** {restaurant.get('title', '')}")
               
               # 🔧 미슐랭 등급 표시
               if michelin_grade:
                   st.markdown(f"**⭐ 미슐랭 등급:** {michelin_grade}")
               
               st.markdown(f"**🗺️ 지역:** {restaurant.get('region', '')} > {restaurant.get('district', '')}")
               st.markdown(f"**🍜 음식종류:** {restaurant.get('food_type', '')}")
               st.markdown(f"**⭐ 카테고리:** {restaurant.get('category', '')}")
               
               representative_menu = restaurant.get('representative_menu', '')
               if isinstance(representative_menu, list):
                   representative_menu = ', '.join(representative_menu)
               if representative_menu:
                   st.markdown(f"**🍽️ 대표메뉴:** {representative_menu}")
               
               if restaurant.get('address'):
                   st.markdown(f"**📍 주소:** {restaurant.get('address')}")
               if restaurant.get('phone'):
                   st.markdown(f"**📞 전화:** {restaurant.get('phone')}")
               if restaurant.get('hours'):
                   st.markdown(f"**🕐 영업시간:** {restaurant.get('hours')}")
               if restaurant.get('closed_days'):
                   st.markdown(f"**🚫 휴무일:** {restaurant.get('closed_days')}")
               
               st.info("📄 상세 정보 파일이 없습니다.")
               
   except Exception as e:
       logger.error(f"❌ 맛집 상세 정보 표시 오류: {e}")
       st.error("상세 정보 표시 중 오류가 발생했습니다.")

def show_restaurant_statistics(portal: BusanRestaurantPortal):
   """맛집 통계 정보 표시"""
   try:
       st.markdown("---")
       st.markdown("## 📊 부산 맛집 통계")
       
       stats = get_restaurant_portal_stats(portal)
       
       # 기본 통계
       col1, col2, col3, col4 = st.columns(4)
       
       with col1:
           st.metric("전체 맛집", f"{stats['total_restaurants']}개")
       
       with col2:
           st.metric("지역 수", f"{stats['region_count']}곳")
       
       with col3:
           st.metric("음식종류", f"{stats['food_type_count']}가지")
       
       with col4:
           st.metric("구/군 수", f"{stats['district_count']}곳")
       
       st.markdown("---")
       
       # 상세 통계 (접을 수 있는 형태)
       with st.expander("📈 상세 통계 보기"):
           col1, col2 = st.columns(2)
           
           with col1:
               st.markdown("### 🗺️ 지역별 분포")
               region_stats = stats['region_distribution']
               for region, count in region_stats.items():
                   if region != "전체":
                       color = RESTAURANT_REGION_COLORS.get(region, "#6B7280")
                       percentage = (count / stats['total_restaurants'] * 100) if stats['total_restaurants'] > 0 else 0
                       st.markdown(
                           f'<div style="display: flex; justify-content: space-between; '
                           f'background-color: {color}; color: white; padding: 5px 10px; '
                           f'border-radius: 5px; margin: 2px 0;">'
                           f'<span>{region}</span>'
                           f'<span>{count}개 ({percentage:.1f}%)</span>'
                           f'</div>',
                           unsafe_allow_html=True
                       )
               
               st.markdown("### ⭐ 카테고리별 분포")
               category_stats = stats['category_distribution']
               for category, count in category_stats.items():
                   if category != "전체":
                       color = RESTAURANT_CATEGORY_COLORS.get(category, "#6B7280")
                       percentage = (count / stats['total_restaurants'] * 100) if stats['total_restaurants'] > 0 else 0
                       st.markdown(
                           f'<div style="display: flex; justify-content: space-between; '
                           f'background-color: {color}; color: white; padding: 5px 10px; '
                           f'border-radius: 5px; margin: 2px 0;">'
                           f'<span>{category}</span>'
                           f'<span>{count}개 ({percentage:.1f}%)</span>'
                           f'</div>',
                           unsafe_allow_html=True
                       )
           
           with col2:
               st.markdown("### 🍜 음식종류별 분포")
               food_type_stats = stats['food_type_distribution']
               for food_type, count in food_type_stats.items():
                   if food_type != "전체":
                       color = RESTAURANT_FOOD_TYPE_COLORS.get(food_type, "#6B7280")
                       percentage = (count / stats['total_restaurants'] * 100) if stats['total_restaurants'] > 0 else 0
                       st.markdown(
                           f'<div style="display: flex; justify-content: space-between; '
                           f'background-color: {color}; color: white; padding: 5px 10px; '
                           f'border-radius: 5px; margin: 2px 0;">'
                           f'<span>{food_type}</span>'
                           f'<span>{count}개 ({percentage:.1f}%)</span>'
                           f'</div>',
                           unsafe_allow_html=True
                       )
               
               # 🔧 미슐랭 맛집 통계 추가
               michelin_count = len([r for r in portal.restaurants_data if r.get('category') == '미쉐린가이드'])
               if michelin_count > 0:
                   st.markdown("### ⭐ 미슐랭 등급별 분포")
                   
                   # 등급별 카운트
                   michelin_stats = {}
                   for restaurant in portal.restaurants_data:
                       if restaurant.get('category') == '미쉐린가이드':
                           grade = restaurant.get('michelin_grade', '기타')
                           michelin_stats[grade] = michelin_stats.get(grade, 0) + 1
                   
                   for grade, count in michelin_stats.items():
                       emoji = ""
                       if grade == "1스타":
                           emoji = "⭐"
                       elif grade == "빕구르망":
                           emoji = "🍽️"
                       elif grade == "셀렉티드":
                           emoji = "✨"
                       
                       st.markdown(
                           f'<div style="display: flex; justify-content: space-between; '
                           f'background-color: #FFD700; color: black; padding: 5px 10px; '
                           f'border-radius: 5px; margin: 2px 0;">'
                           f'<span>{emoji} {grade}</span>'
                           f'<span>{count}개</span>'
                           f'</div>',
                           unsafe_allow_html=True
                       )
               
               # 인기 정보
               st.markdown("### 🏆 인기 순위")
               st.info(f"**인기 지역:** {stats['most_popular_region'][0]} ({stats['most_popular_region'][1]}개)")
               st.info(f"**인기 음식:** {stats['most_popular_food_type'][0]} ({stats['most_popular_food_type'][1]}개)")
       
   except Exception as e:
       logger.error(f"❌ 맛집 통계 표시 오류: {e}")
       st.error("통계 정보 표시 중 오류가 발생했습니다.")

def show_featured_restaurants(portal: BusanRestaurantPortal):
   """추천 맛집 섹션"""
   try:
       st.markdown("## ⭐ 추천 맛집")
       
       featured = portal.get_featured_restaurants(6)
       
       if not featured:
           st.info("추천할 맛집이 없습니다.")
           return
       
       # 추천 맛집 카드 (2열)
       cols = st.columns(2)
       for idx, restaurant in enumerate(featured):
           col = cols[idx % 2]
           with col:
               show_restaurant_card(restaurant)
               
   except Exception as e:
       logger.error(f"❌ 추천 맛집 표시 오류: {e}")
       st.error("추천 맛집 표시 중 오류가 발생했습니다.")


# 테스트 함수
def test_restaurant_page():
   """맛집 페이지 테스트"""
   print("🧪 맛집 페이지 테스트 시작...")
   try:
       show_restaurant_page()
       print("✅ 맛집 페이지 테스트 완료")
   except Exception as e:
       print(f"❌ 맛집 페이지 테스트 실패: {e}")


if __name__ == "__main__":
   test_restaurant_page()