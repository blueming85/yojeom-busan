"""
부산 맛집 포털 - BusanRestaurantPortal
===================================
맛집 MD 파일들을 로드하고 필터링하는 전용 클래스

주요 기능:
- 맛집 MD 파일 로드
- 지역별/음식타입별/카테고리별 필터링
- 검색 기능
- 통계 정보 제공
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import logging

from config import (
   RESTAURANT_MD_DIR, RESTAURANT_REGIONS, AVAILABLE_RESTAURANT_REGIONS,
   RESTAURANT_FOOD_TYPES, AVAILABLE_RESTAURANT_CATEGORIES,
   RESTAURANT_REGION_COLORS, RESTAURANT_FOOD_TYPE_COLORS, RESTAURANT_CATEGORY_COLORS
)

logger = logging.getLogger(__name__)

class BusanRestaurantPortal:
   """부산 맛집 포털 클래스"""
   
   def __init__(self):
       self.md_dir = RESTAURANT_MD_DIR
       self.restaurants_data = []
       self.load_restaurants_data()
   
   def load_restaurants_data(self) -> List[Dict]:
       """맛집 MD 파일들에서 데이터 로드"""
       restaurants_list = []
       
       if not self.md_dir.exists():
           logger.error(f"📁 맛집 디렉토리가 없습니다: {self.md_dir}")
           return []
       
       md_files = list(self.md_dir.glob("*.md"))
       
       if not md_files:
           logger.warning("📄 맛집 MD 파일이 없습니다.")
           return []
       
       for md_file in md_files:
           try:
               restaurant_item = self._parse_markdown_file(md_file)
               if restaurant_item:
                   restaurants_list.append(restaurant_item)
           except Exception as e:
               logger.error(f"맛집 파일 파싱 오류 {md_file.name}: {e}")
               continue
       
       # 카테고리별 우선순위로 정렬 (미슐랭 > 부산의맛 > 현지인)
       def get_priority(restaurant):
           category = restaurant.get('category', '현지인')
           priority_order = {"미슐랭": 1, "부산의맛": 2, "현지인": 3}
           return priority_order.get(category, 4)

       restaurants_list.sort(key=get_priority)
       self.restaurants_data = restaurants_list
       
       logger.info(f"✅ 맛집 {len(restaurants_list)}개 로드 완료")
       return restaurants_list
   
   def _parse_markdown_file(self, md_file: Path) -> Optional[Dict]:
       """🔧 맛집 MD 파일에서 메타데이터와 내용 추출 (YAML 리스트 처리 포함)"""
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
           
           # 🔧 YAML 스타일 메타데이터 추출 (리스트 처리 포함)
           metadata = {}
           current_key = None
           current_list = []
           
           for line in frontmatter.split('\n'):
               line = line.strip()
               if not line:
                   continue
                   
               # 리스트 아이템 처리
               if line.startswith('- '):
                   if current_key:
                       current_list.append(line[2:].strip())
                   continue
               
               # 이전 리스트 완료 처리
               if current_key and current_list:
                   metadata[current_key] = current_list
                   current_key = None
                   current_list = []
               
               # 일반 키:값 처리
               if ':' in line:
                   key, value = line.split(':', 1)
                   key = key.strip()
                   value = value.strip().strip('"\'')
                   
                   if not value:  # 값이 없으면 리스트 시작
                       current_key = key
                       current_list = []
                   else:
                       metadata[key] = value
           
           # 마지막 리스트 처리
           if current_key and current_list:
               metadata[current_key] = current_list
           
           # 필수 필드 검증
           required_fields = ['title', 'region', 'district', 'category', 'food_type']
           for field in required_fields:
               if field not in metadata:
                   logger.warning(f"⚠️ 필수 필드 누락: {field} in {md_file.name}")
                   return None
           
           # 지역권 검증 (구/군으로부터 자동 설정)
           district = metadata.get('district', '')
           region = self._get_region_from_district(district)
           if region != metadata.get('region'):
               logger.warning(f"⚠️ 지역권 불일치: {metadata.get('region')} → {region} ({district})")
               metadata['region'] = region
           
           # 🔧 representative_menu 리스트 처리
           representative_menu = metadata.get('representative_menu', [])
           if isinstance(representative_menu, list):
               representative_menu = ', '.join(representative_menu)
           
           # 상세 정보 추출
           detailed_info = self._extract_detailed_info_from_body(body)
           
           return {
               'title': metadata.get('title', '맛집'),
               'region': metadata.get('region', '기타'),
               'district': metadata.get('district', ''),
               'category': metadata.get('category', '현지인'),
               'food_type': metadata.get('food_type', '한식'),
               'representative_menu': representative_menu,  # 🔧 리스트 → 문자열 변환
               'phone': metadata.get('phone', ''),
               'address': metadata.get('address', ''),
               'hours': metadata.get('hours', ''),
               'closed_days': metadata.get('closed_days', ''),
               'date': metadata.get('date', datetime.now().strftime("%Y-%m-%d")),
               'uc_seq': metadata.get('uc_seq', ''),  # 🔧 추가
               'source_url': metadata.get('source_url', ''),  # 🔧 추가
               'extraction_date': metadata.get('extraction_date', ''),  # 🔧 추가
               'detailed_info': detailed_info,
               'file_path': str(md_file)
           }
           
       except Exception as e:
           logger.error(f"맛집 MD 파싱 오류: {e}")
           return None
   
   def _get_region_from_district(self, district: str) -> str:
       """구/군으로부터 지역권 찾기"""
       for region, districts in RESTAURANT_REGIONS.items():
           if district in districts:
               return region
       return "기타"
   
   def _extract_detailed_info_from_body(self, body: str) -> str:
       """본문에서 상세 정보 추출"""
       lines = body.split('\n')
       info_lines = []
       
       # "## 📍 이용안내" 또는 "## 🍽️ 메뉴 정보" 부분 찾기
       target_sections = ['## 📍 이용안내', '## 🍽️ 메뉴', '## 📞 연락처', '## 📝 상세']
       
       for section in target_sections:
           in_target_section = False
           section_lines = []
           
           for line in lines:
               line = line.strip()
               if section in line:
                   in_target_section = True
                   continue
               elif line.startswith('##') and in_target_section:
                   break
               elif in_target_section and line and not line.startswith('#'):
                   section_lines.append(line)
           
           if section_lines:
               info_lines.extend(section_lines[:2])  # 각 섹션에서 2줄까지
       
       if info_lines:
           return '\n'.join(info_lines)
       
       # 대안: 전체 본문에서 처음 150자
       return body[:150] + "..." if len(body) > 150 else body
   
   def get_region_stats(self) -> Dict:
       """지역별 통계 계산"""
       region_counts = {}
       
       for restaurant in self.restaurants_data:
           region = restaurant.get('region', '기타')
           region_counts[region] = region_counts.get(region, 0) + 1
       
       # 전체 개수 추가
       region_counts["전체"] = len(self.restaurants_data)
       
       return region_counts
   
   def get_food_type_stats(self) -> Dict:
       """음식타입별 통계 계산"""
       food_type_counts = {}
       
       for restaurant in self.restaurants_data:
           food_type = restaurant.get('food_type', '한식')
           food_type_counts[food_type] = food_type_counts.get(food_type, 0) + 1
       
       # 전체 개수 추가
       food_type_counts["전체"] = len(self.restaurants_data)
       
       return food_type_counts
   
   def get_category_stats(self) -> Dict:
       """카테고리별 통계 계산"""
       category_counts = {}
       
       for restaurant in self.restaurants_data:
           category = restaurant.get('category', '현지인')
           category_counts[category] = category_counts.get(category, 0) + 1
       
       # 전체 개수 추가
       category_counts["전체"] = len(self.restaurants_data)
       
       return category_counts
   
   def get_district_stats(self) -> Dict:
       """구/군별 통계 계산"""
       district_counts = {}
       
       for restaurant in self.restaurants_data:
           district = restaurant.get('district', '기타')
           district_counts[district] = district_counts.get(district, 0) + 1
       
       return district_counts
   
   def filter_restaurants(self, selected_regions: List[str] = None,
                        selected_food_types: List[str] = None,
                        selected_categories: List[str] = None,
                        search_query: str = "") -> List[Dict]:
       """맛집 필터링"""
       filtered_restaurants = self.restaurants_data.copy()
       
       # 지역별 필터링
       if selected_regions and "전체" not in selected_regions:
           filtered_restaurants = [
               restaurant for restaurant in filtered_restaurants
               if restaurant.get('region') in selected_regions
           ]
       
       # 음식타입별 필터링
       if selected_food_types and "전체" not in selected_food_types:
           filtered_restaurants = [
               restaurant for restaurant in filtered_restaurants
               if restaurant.get('food_type') in selected_food_types
           ]
       
       # 카테고리별 필터링
       if selected_categories and "전체" not in selected_categories:
           filtered_restaurants = [
               restaurant for restaurant in filtered_restaurants
               if restaurant.get('category') in selected_categories
           ]
       
       # 검색어 필터링
       if search_query:
           search_query = search_query.lower()
           filtered_restaurants = [
               restaurant for restaurant in filtered_restaurants
               if (search_query in restaurant.get('title', '').lower() or 
                   search_query in restaurant.get('district', '').lower() or
                   search_query in restaurant.get('food_type', '').lower() or
                   search_query in restaurant.get('address', '').lower() or
                   search_query in restaurant.get('representative_menu', '').lower() or
                   search_query in restaurant.get('detailed_info', '').lower())
           ]
       
       return filtered_restaurants
   
   def get_restaurants_by_region(self, region: str) -> List[Dict]:
       """특정 지역의 맛집들 반환"""
       if region == "전체":
           return self.restaurants_data
       
       return [
           restaurant for restaurant in self.restaurants_data
           if restaurant.get('region') == region
       ]
   
   def get_restaurants_by_food_type(self, food_type: str) -> List[Dict]:
       """특정 음식타입의 맛집들 반환"""
       if food_type == "전체":
           return self.restaurants_data
       
       return [
           restaurant for restaurant in self.restaurants_data
           if restaurant.get('food_type') == food_type
       ]
   
   def get_restaurants_by_category(self, category: str) -> List[Dict]:
       """특정 카테고리의 맛집들 반환"""
       if category == "전체":
           return self.restaurants_data
       
       return [
           restaurant for restaurant in self.restaurants_data
           if restaurant.get('category') == category
       ]
   
   def search_restaurants(self, query: str) -> List[Dict]:
       """맛집 검색"""
       if not query:
           return self.restaurants_data
       
       query_lower = query.lower()
       results = []
       
       for restaurant in self.restaurants_data:
           score = 0
           
           # 제목 매칭 (가중치 3)
           if query_lower in restaurant.get('title', '').lower():
               score += 3
           
           # 음식타입 매칭 (가중치 2)
           if query_lower in restaurant.get('food_type', '').lower():
               score += 2
           
           # 지역/주소 매칭 (가중치 2)
           if (query_lower in restaurant.get('district', '').lower() or 
               query_lower in restaurant.get('address', '').lower()):
               score += 2
           
           # 대표메뉴 매칭 (가중치 2) - 🔧 추가
           if query_lower in restaurant.get('representative_menu', '').lower():
               score += 2
           
           # 내용 매칭 (가중치 1)
           if query_lower in restaurant.get('detailed_info', '').lower():
               score += 1
           
           if score > 0:
               restaurant_with_score = restaurant.copy()
               restaurant_with_score['search_score'] = score
               results.append(restaurant_with_score)
       
       # 점수순 정렬
       results.sort(key=lambda x: x.get('search_score', 0), reverse=True)
       return results
   
   def get_featured_restaurants(self, count: int = 6) -> List[Dict]:
       """추천 맛집 (미슐랭, 부산의맛 우선)"""
       featured = []
       
       # 미슐랭 맛집 우선
       michelin_restaurants = [r for r in self.restaurants_data if r.get('category') == '미슐랭']
       featured.extend(michelin_restaurants[:count//2])
       
       # 부산의맛 맛집
       busan_restaurants = [r for r in self.restaurants_data if r.get('category') == '부산의맛']
       remaining_count = count - len(featured)
       featured.extend(busan_restaurants[:remaining_count])
       
       # 부족하면 현지인 맛집으로 채움
       if len(featured) < count:
           local_restaurants = [r for r in self.restaurants_data if r.get('category') == '현지인']
           remaining_count = count - len(featured)
           featured.extend(local_restaurants[:remaining_count])
       
       return featured[:count]
   
   def get_restaurants_by_district(self, district: str) -> List[Dict]:
       """특정 구/군의 맛집들 반환"""
       return [
           restaurant for restaurant in self.restaurants_data
           if restaurant.get('district') == district
       ]


# 유틸리티 함수들

def get_restaurant_portal_stats(portal: BusanRestaurantPortal) -> Dict:
   """맛집 포털 통계 정보"""
   region_stats = portal.get_region_stats()
   food_type_stats = portal.get_food_type_stats()
   category_stats = portal.get_category_stats()
   district_stats = portal.get_district_stats()
   
   return {
       'total_restaurants': len(portal.restaurants_data),
       'region_count': len(region_stats) - 1,  # 전체 제외
       'food_type_count': len(food_type_stats) - 1,  # 전체 제외
       'category_count': len(category_stats) - 1,  # 전체 제외
       'district_count': len(district_stats),
       'region_distribution': region_stats,
       'food_type_distribution': food_type_stats,
       'category_distribution': category_stats,
       'most_popular_region': max(
           [(k, v) for k, v in region_stats.items() if k != "전체"], 
           key=lambda x: x[1]
       ) if region_stats else ("없음", 0),
       'most_popular_food_type': max(
           [(k, v) for k, v in food_type_stats.items() if k != "전체"], 
           key=lambda x: x[1]
       ) if food_type_stats else ("없음", 0)
   }

def validate_restaurant_data(portal: BusanRestaurantPortal) -> Dict:
   """맛집 데이터 유효성 검사"""
   issues = []
   
   if not portal.restaurants_data:
       issues.append("맛집 데이터가 없습니다")
       return {"valid": False, "issues": issues}
   
   # 필수 필드 체크
   for i, restaurant in enumerate(portal.restaurants_data):
       required_fields = ['title', 'region', 'district', 'category', 'food_type']
       for field in required_fields:
           if not restaurant.get(field):
               issues.append(f"맛집 {i+1}: {field} 누락")
       
       # 지역권-구/군 일치성 체크
       region = restaurant.get('region')
       district = restaurant.get('district')
       if region and district:
           expected_region = portal._get_region_from_district(district)
           if region != expected_region and expected_region != "기타":
               issues.append(f"맛집 {i+1}: 지역권 불일치 ({district} → {expected_region})")
   
   # 중복 체크
   titles = [restaurant.get('title', '') for restaurant in portal.restaurants_data]
   duplicates = [title for title in set(titles) if titles.count(title) > 1]
   if duplicates:
       issues.append(f"중복 맛집명 발견: {', '.join(duplicates)}")
   
   # 카테고리 유효성 체크
   valid_categories = AVAILABLE_RESTAURANT_CATEGORIES[1:]  # 전체 제외
   invalid_categories = []
   for restaurant in portal.restaurants_data:
       category = restaurant.get('category')
       if category and category not in valid_categories:
           invalid_categories.append(category)
   
   if invalid_categories:
       unique_invalid = list(set(invalid_categories))
       issues.append(f"유효하지 않은 카테고리: {', '.join(unique_invalid)}")
   
   return {
       "valid": len(issues) == 0,
       "issues": issues,
       "total_checked": len(portal.restaurants_data)
   }


# 테스트 함수
def test_restaurant_portal():
   """맛집 포털 테스트"""
   print("🧪 맛집 포털 테스트 시작...")
   
   try:
       portal = BusanRestaurantPortal()
       stats = get_restaurant_portal_stats(portal)
       validation = validate_restaurant_data(portal)
       
       print(f"📊 통계:")
       print(f"  - 총 맛집: {stats['total_restaurants']}개")
       print(f"  - 지역 수: {stats['region_count']}개")
       print(f"  - 음식타입 수: {stats['food_type_count']}개")
       print(f"  - 카테고리 수: {stats['category_count']}개")
       print(f"  - 구/군 수: {stats['district_count']}개")
       print(f"  - 인기 지역: {stats['most_popular_region'][0]} ({stats['most_popular_region'][1]}개)")
       print(f"  - 인기 음식: {stats['most_popular_food_type'][0]} ({stats['most_popular_food_type'][1]}개)")
       
       print(f"✅ 유효성 검사: {'통과' if validation['valid'] else '실패'}")
       if validation['issues']:
           for issue in validation['issues'][:3]:
               print(f"  - {issue}")
       
       # 검색 테스트
       search_results = portal.search_restaurants("해운대")
       print(f"🔍 '해운대' 검색 결과: {len(search_results)}개")
       
       # 필터링 테스트
       filtered = portal.filter_restaurants(
           selected_regions=["동부산권"], 
           selected_food_types=["양식"]
       )
       print(f"🏷️ 동부산권 양식 필터링: {len(filtered)}개")
       
       # 추천 맛집 테스트
       featured = portal.get_featured_restaurants(6)
       print(f"⭐ 추천 맛집: {len(featured)}개")
       
       # 🔧 representative_menu 리스트 처리 테스트
       if portal.restaurants_data:
           sample = portal.restaurants_data[0]
           print(f"📋 샘플 대표메뉴: {sample.get('representative_menu', 'N/A')}")
       
   except Exception as e:
       print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
   test_restaurant_portal()