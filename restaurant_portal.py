"""
부산 맛집 포털 - BusanRestaurantPortal (좌표 캐싱 최적화)
===================================
맛집 MD 파일들을 로드하고 필터링하는 전용 클래스

주요 기능:
- 맛집 MD 파일 로드
- 지역별/음식타입별/카테고리별 필터링
- 검색 기능
- 통계 정보 제공
- 🔧 좌표 캐싱 및 성능 최적화
"""

import json
import re
import os
import logging
import pickle
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 🔧 강제로 .env 파일 로드
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
                print(f"🔧 환경변수 설정: {key.strip()}")

# 기존 dotenv 로드도 유지
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ dotenv 로드 완료")
except ImportError:
    print("⚠️ python-dotenv 없음, 수동 로드 사용")

# API 키 확인
api_key = os.getenv('KAKAO_REST_API_KEY')
print(f"🔑 최종 API 키 확인: {'✅' if api_key else '❌'}")
if api_key:
    print(f"🔑 API 키: {api_key[:10]}...{api_key[-5:]}")

# 카카오 API 및 requests 선택적 import
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from config import (
   RESTAURANT_MD_DIR, RESTAURANT_REGIONS, AVAILABLE_RESTAURANT_REGIONS,
   RESTAURANT_FOOD_TYPES, AVAILABLE_RESTAURANT_CATEGORIES,
   RESTAURANT_REGION_COLORS, RESTAURANT_FOOD_TYPE_COLORS, RESTAURANT_CATEGORY_COLORS,
   KAKAO_REST_API_KEY
)

logger = logging.getLogger(__name__)

# 🔧 부산 구별 대표 좌표 (백업용/빠른 로딩용)
BUSAN_DISTRICT_COORDS = {
    "중구": [35.1040, 129.0364],
    "서구": [35.1370, 129.0569], 
    "동구": [35.0885, 129.0286],
    "영도구": [35.0919, 129.0678],
    "부산진구": [35.1630, 129.0530],
    "동래구": [35.2049, 129.0838],
    "남구": [35.1366, 129.0845],
    "북구": [35.1974, 129.0309],
    "해운대구": [35.1631, 129.1640],
    "사하구": [35.1044, 128.9746],
    "금정구": [35.2428, 129.0917],
    "강서구": [35.2123, 128.9810],
    "연제구": [35.1763, 129.0798],
    "수영구": [35.1456, 129.1136],
    "사상구": [35.1549, 128.9906],
    "기장군": [35.2447, 129.2224]
}

# 🔧 수동 좌표 설정 (문제 맛집들)
MANUAL_RESTAURANT_COORDINATES = {
    "배꼽시계": [35.2447, 129.2224],  # 기장군 일광읍
    "홍옥당": [35.1456, 129.1136],   # 수영구 남천동
    "1966정원": [35.028155, 128.815774], # 강서구 가덕도 (추정)
    "브리타니": [35.037541, 128.812863], # 강서구 가덕도
    "브레이크인커피": [35.3408, 129.1778], # 기장군 정관읍
    "웨이브온커피": [35.3223, 129.2698],   # 기장군 장안읍
    "이가네떡볶이": [35.0970, 129.0320],  # 부평1길 근처 정확한 좌표
}

# 🔧 구/군별 좌표 범위 (검증용) - 범위 더욱 확대
DISTRICT_COORDINATE_BOUNDS = {
    "중구": {"lat": [35.09, 35.12], "lng": [129.02, 129.05]},
    "서구": {"lat": [35.10, 35.16], "lng": [129.01, 129.08]},
    "동구": {"lat": [35.07, 35.13], "lng": [129.01, 129.06]},
    "영도구": {"lat": [35.06, 35.13], "lng": [129.03, 129.09]},
    "부산진구": {"lat": [35.14, 35.19], "lng": [129.03, 129.08]},
    "동래구": {"lat": [35.18, 35.23], "lng": [129.06, 129.11]},
    "남구": {"lat": [35.12, 35.16], "lng": [129.06, 129.11]},
    "북구": {"lat": [35.17, 35.22], "lng": [129.00, 129.06]},
    "해운대구": {"lat": [35.14, 35.20], "lng": [129.12, 129.20]},
    "사하구": {"lat": [35.08, 35.13], "lng": [128.95, 129.02]},
    "금정구": {"lat": [35.22, 35.28], "lng": [129.07, 129.13]},
    "강서구": {"lat": [35.09, 35.25], "lng": [128.90, 129.01]},  # lng 최소값 낮춤
    "연제구": {"lat": [35.16, 35.20], "lng": [129.06, 129.11]},
    "수영구": {"lat": [35.13, 35.17], "lng": [129.09, 129.15]},
    "사상구": {"lat": [35.13, 35.18], "lng": [128.97, 129.03]},
    "기장군": {"lat": [35.18, 35.35], "lng": [129.13, 129.35]}
}

# 🔧 부산 좌표 범위 (좌표 검증용) - 가덕도와 정관/장안읍 포함 대폭 확대
BUSAN_BOUNDS = {
    'lat_min': 35.0,   # 가덕도 포함
    'lat_max': 35.4,   # 기장군 정관/장안읍 포함 (기존 35.3 → 35.4로 확대)
    'lng_min': 128.8,  # 가덕도 포함 (기존 128.9 → 128.8로 확대)
    'lng_max': 129.4   # 기장군 동부 포함 (기존 129.3 → 129.4로 확대)
}

class BusanRestaurantPortal:
    """부산 맛집 포털 클래스 (성능 최적화)"""
    
    def __init__(self):
        self.md_dir = RESTAURANT_MD_DIR
        self.restaurants_data = []
        self.coordinates_cache = {}
        self.cache_file = Path("restaurant_coords_cache.pkl")
        
        # API 키 확인 로그 추가
        api_key = os.getenv('KAKAO_REST_API_KEY')
        print(f"🔑 API 키 로드됨: {'✅' if api_key else '❌'}")
        
        # 🔧 좌표 캐시 로드
        self._load_coordinates_cache()
        
        # 맛집 데이터 로드
        self.load_restaurants_data()
    
    def _load_coordinates_cache(self):
        """좌표 캐시 파일 로드"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'rb') as f:
                    self.coordinates_cache = pickle.load(f)
                logger.info(f"✅ 좌표 캐시 로드 완료: {len(self.coordinates_cache)}개")
            else:
                self.coordinates_cache = {}
                logger.info("🆕 새로운 좌표 캐시 파일 생성")
        except Exception as e:
            logger.error(f"❌ 좌표 캐시 로드 오류: {e}")
            self.coordinates_cache = {}
    
    def _save_coordinates_cache(self):
        """좌표 캐시 파일 저장"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.coordinates_cache, f)
            logger.info(f"💾 좌표 캐시 저장 완료: {len(self.coordinates_cache)}개")
        except Exception as e:
            logger.error(f"❌ 좌표 캐시 저장 오류: {e}")
    
    def _get_address_hash(self, cache_key: str) -> str:
        """캐시 키의 해시값 생성"""
        return hashlib.md5(cache_key.encode('utf-8')).hexdigest()
    
    def _is_valid_busan_coordinate(self, lat: float, lon: float) -> bool:
        """🔧 부산 범위 내 좌표인지 검증"""
        return (BUSAN_BOUNDS['lat_min'] <= lat <= BUSAN_BOUNDS['lat_max'] and 
                BUSAN_BOUNDS['lng_min'] <= lon <= BUSAN_BOUNDS['lng_max'])
    
    def _is_valid_district_coordinate(self, lat: float, lon: float, district: str) -> bool:
        """🔧 특정 구/군 범위 내 좌표인지 검증 - 부산 전체 범위만 체크"""
        # 🔧 구/군 세부 범위 체크 비활성화, 부산 전체 범위만 체크
        return self._is_valid_busan_coordinate(lat, lon)
    
    def _clean_address(self, address: str) -> str:
        """주소에서 호수/건물명 정보 제거"""
        import re
        # 호수 정보 제거 (1072,1073호 등)
        cleaned = re.sub(r'\s*\d+,?\d*호.*', '', address)
        # 괄호 안 정보 제거 (용호동, 더블유)
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)
        return cleaned.strip()
    
    def _get_coordinates_from_kakao(self, name: str, address: str, district: str = "") -> tuple:
        """🔧 카카오 API로 좌표 추출 (주소 우선 검색)"""
        api_key = os.getenv('KAKAO_REST_API_KEY')
        
        if not api_key or not REQUESTS_AVAILABLE:
            print(f"❌ API 호출 불가: {name}")
            return (35.1, 129.065)  # 기본 좌표
        
        try:
            # 🔧 주소 정제: 호수/건물명 제거
            cleaned_address = self._clean_address(address)
            print(f"🧹 주소 정제: {address} → {cleaned_address}")
            
            # 🔧 1차: 정제된 주소로 검색 (더 정확함)
            url = "https://dapi.kakao.com/v2/local/search/address.json"
            headers = {"Authorization": f"KakaoAK {api_key}"}
            params = {"query": cleaned_address}
            
            print(f"🔍 주소 검색: {cleaned_address}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    result = data['documents'][0]
                    lat = float(result['y'])
                    lon = float(result['x'])
                    
                    # 🔧 구/군 범위 검증
                    if self._is_valid_district_coordinate(lat, lon, district):
                        print(f"✅ 주소로 좌표 찾음: {name} → ({lat}, {lon})")
                        return (lat, lon)
                    else:
                        print(f"⚠️ 구/군 범위 밖 좌표: {name} → ({lat}, {lon}) (기대: {district})")
            
            # 🔧 2차: 식당명+정제된주소 키워드 검색 (백업)
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            query = f"{name} {cleaned_address}"
            params = {"query": query, "category_group_code": "FD6"}  # 음식점 카테고리
            
            print(f"🔍 키워드 검색: {query}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    result = data['documents'][0]
                    lat = float(result['y'])
                    lon = float(result['x'])
                    
                    # 🔧 구/군 범위 검증
                    if self._is_valid_district_coordinate(lat, lon, district):
                        print(f"✅ 키워드로 좌표 찾음: {name} → ({lat}, {lon})")
                        return (lat, lon)
                    else:
                        print(f"⚠️ 구/군 범위 밖 좌표: {name} → ({lat}, {lon}) (기대: {district})")
            
            print(f"❌ 좌표 못찾음: {name}")
            return (35.1, 129.065)  # 기본 좌표
            
        except Exception as e:
            print(f"❌ API 오류 {name}: {e}")
            return (35.1, 129.065)  # 기본 좌표
    
    def get_restaurant_coordinates(self, name: str, address: str, district: str = "") -> tuple:
        """🔧 맛집 좌표 가져오기 (수동 좌표 우선, 캐시, API, 구별 좌표 순)"""
        # 🔧 1순위: 수동 좌표 체크
        if name in MANUAL_RESTAURANT_COORDINATES:
            manual_coords = MANUAL_RESTAURANT_COORDINATES[name]
            print(f"📌 수동 좌표 사용: {name} → ({manual_coords[0]}, {manual_coords[1]})")
            return manual_coords[0], manual_coords[1]
        
        if not address:
            # 주소가 없으면 구별 대표 좌표 사용
            district_coords = BUSAN_DISTRICT_COORDS.get(district, [35.1796, 129.0756])
            return district_coords[0], district_coords[1]
        
        # 캐시 키를 name + address 조합으로 변경
        cache_key = f"{name}_{address}"
        address_hash = self._get_address_hash(cache_key)
        
        # 🔧 캐시 검증: 구/군 범위 내인지 확인
        if address_hash in self.coordinates_cache:
            cached_coords = self.coordinates_cache[address_hash]
            lat, lon = cached_coords[0], cached_coords[1]
            
            # 캐시된 좌표가 해당 구/군 범위 내인지 확인
            if self._is_valid_district_coordinate(lat, lon, district):
                return lat, lon
            else:
                # 잘못된 캐시 삭제
                print(f"🗑️ 잘못된 캐시 삭제: {name} ({lat}, {lon}) - 기대 구/군: {district}")
                del self.coordinates_cache[address_hash]
        
        # 🔧 카카오 API로 좌표 추출 (district 정보 추가 전달)
        lat, lon = self._get_coordinates_from_kakao(name, address, district)
        
        # 유효한 좌표인지 확인
        if self._is_valid_district_coordinate(lat, lon, district):
            # 캐시에 저장
            self.coordinates_cache[address_hash] = [lat, lon]
            return lat, lon
        else:
            # API 실패 시 구별 대표 좌표 사용
            district_coords = BUSAN_DISTRICT_COORDS.get(district, [35.1796, 129.0756])
            print(f"🏢 구별 대표 좌표 사용: {name} → {district} ({district_coords[0]}, {district_coords[1]})")
            # 구별 좌표도 캐시에 저장 (다음에 더 빠르게)
            self.coordinates_cache[address_hash] = district_coords
            return district_coords[0], district_coords[1]
    
    def load_restaurants_data(self) -> List[Dict]:
        """맛집 MD 파일들에서 데이터 로드 (좌표 포함)"""
        restaurants_list = []
        
        if not self.md_dir.exists():
            logger.error(f"📁 맛집 디렉토리가 없습니다: {self.md_dir}")
            return []
        
        md_files = list(self.md_dir.glob("*.md"))
        
        if not md_files:
            logger.warning("📄 맛집 MD 파일이 없습니다.")
            return []
        
        # 🔧 성능 개선: 처리 진행률 표시
        logger.info(f"📊 맛집 데이터 로딩 시작: {len(md_files)}개 파일")
        
        coords_updated = False
        
        for idx, md_file in enumerate(md_files):
            try:
                restaurant_item = self._parse_markdown_file(md_file)
                if restaurant_item:
                    # 🔧 좌표 추가 (name, address, district 모두 전달)
                    name = restaurant_item.get('title', '')
                    address = restaurant_item.get('address', '')
                    district = restaurant_item.get('district', '')
                    
                    lat, lon = self.get_restaurant_coordinates(name, address, district)
                    restaurant_item['latitude'] = lat
                    restaurant_item['longitude'] = lon
                    
                    restaurants_list.append(restaurant_item)
                    coords_updated = True
                
                # 100개마다 진행률 로그
                if (idx + 1) % 100 == 0:
                    logger.info(f"⏳ 진행률: {idx + 1}/{len(md_files)} ({(idx + 1)/len(md_files)*100:.1f}%)")
                    
            except Exception as e:
                logger.error(f"맛집 파일 파싱 오류 {md_file.name}: {e}")
                continue
        
        # 🔧 좌표 캐시 저장 (업데이트된 경우에만)
        if coords_updated:
            self._save_coordinates_cache()
        
        # 카테고리별 우선순위로 정렬 (미슐랭 > 부산의맛 > 현지인)
        def get_priority(restaurant):
            category = restaurant.get('category', '현지인')
            priority_order = {"미쉐린가이드": 1, "부산의맛": 2, "현지인": 3}  # 🔧 수정: 미쉘린 → 미쉐린
            return priority_order.get(category, 4)

        restaurants_list.sort(key=get_priority)
        self.restaurants_data = restaurants_list
        
        logger.info(f"✅ 맛집 {len(restaurants_list)}개 로드 완료 (좌표 포함)")
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
            # 깅서구 → 강서구 자동 수정
            if district == "깅서구":
                district = "강서구"
                metadata['district'] = district
                
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
                'michelin_grade': metadata.get('michelin_grade', ''),  # 🔧 미슐랭 등급 추가
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
    
    def get_restaurants_by_priority(self, restaurants: List[Dict] = None) -> Dict[str, List[Dict]]:
        """🔧 우선순위별 맛집 그룹화 (점진적 로딩용)"""
        if restaurants is None:
            restaurants = self.restaurants_data
        
        grouped = {
            'michelin': [],      # 미슐랭 (최우선)
            'busan_taste': [],   # 부산의맛
            'local': []          # 현지인
        }
        
        for restaurant in self.restaurants_data:
            category = restaurant.get('category', '현지인')
            if category == '미쉐린가이드':  # 🔧 수정: 미쉘린 → 미쉐린
                grouped['michelin'].append(restaurant)
            elif category == '부산의맛':
                grouped['busan_taste'].append(restaurant)
            else:
                grouped['local'].append(restaurant)
        
        return grouped
    
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
        michelin_restaurants = [r for r in self.restaurants_data if r.get('category') == '미쉐린가이드']  # 🔧 수정
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
    
    def clear_coordinates_cache(self):
        """🔧 좌표 캐시 초기화 (개발/디버깅용)"""
        self.coordinates_cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("🗑️ 좌표 캐시 초기화 완료")
    
    def validate_coordinates_cache(self):
        """🔧 좌표 캐시 검증 및 정리"""
        invalid_keys = []
        
        for key, coords in self.coordinates_cache.items():
            lat, lon = coords[0], coords[1]
            if not self._is_valid_busan_coordinate(lat, lon):
                invalid_keys.append(key)
        
        # 잘못된 캐시 삭제
        for key in invalid_keys:
            del self.coordinates_cache[key]
            
        if invalid_keys:
            logger.info(f"🧹 잘못된 좌표 캐시 {len(invalid_keys)}개 삭제")
            self._save_coordinates_cache()
        
        return len(invalid_keys)


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
        'cached_coordinates': len(portal.coordinates_cache),  # 🔧 캐시된 좌표 수
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
        
        # 🔧 좌표 체크
        lat, lon = restaurant.get('latitude'), restaurant.get('longitude')
        if not lat or not lon:
            issues.append(f"맛집 {i+1}: 좌표 누락")
        elif not portal._is_valid_busan_coordinate(lat, lon):
            issues.append(f"맛집 {i+1}: 부산 범위 밖 좌표 ({lat}, {lon})")
        
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

def cleanup_invalid_coordinates(portal: BusanRestaurantPortal):
    """🔧 잘못된 좌표 데이터 정리"""
    print("🧹 좌표 데이터 정리 시작...")
    
    # 캐시 검증 및 정리
    invalid_count = portal.validate_coordinates_cache()
    
    # 맛집 데이터 좌표 재검증
    updated_count = 0
    for restaurant in portal.restaurants_data:
        lat, lon = restaurant.get('latitude'), restaurant.get('longitude')
        if lat and lon and not portal._is_valid_busan_coordinate(lat, lon):
            # 잘못된 좌표 발견 - 구별 대표 좌표로 교체
            district = restaurant.get('district', '')
            district_coords = BUSAN_DISTRICT_COORDS.get(district, [35.1796, 129.0756])
            restaurant['latitude'] = district_coords[0]
            restaurant['longitude'] = district_coords[1]
            updated_count += 1
            print(f"🔧 좌표 수정: {restaurant.get('title')} → {district_coords}")
    
    if updated_count > 0:
        print(f"✅ {updated_count}개 맛집 좌표 수정 완료")
    
    print(f"✅ 좌표 정리 완료: 캐시 {invalid_count}개, 데이터 {updated_count}개 수정")

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
        print(f"  - 캐시된 좌표: {stats['cached_coordinates']}개")
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
        
        # 🔧 우선순위별 그룹 테스트
        grouped = portal.get_restaurants_by_priority()
        print(f"📋 미슐랭: {len(grouped['michelin'])}개, 부산의맛: {len(grouped['busan_taste'])}개, 현지인: {len(grouped['local'])}개")
        
        # 🔧 좌표 체크
        coords_count = sum(1 for r in portal.restaurants_data if r.get('latitude') and r.get('longitude'))
        valid_coords_count = sum(1 for r in portal.restaurants_data 
                               if r.get('latitude') and r.get('longitude') and 
                               portal._is_valid_busan_coordinate(r.get('latitude'), r.get('longitude')))
        print(f"🗺️ 좌표 설정된 맛집: {coords_count}/{len(portal.restaurants_data)}개")
        print(f"🎯 부산 범위 내 좌표: {valid_coords_count}/{coords_count}개")
        
        # 🔧 representative_menu 리스트 처리 테스트
        if portal.restaurants_data:
            sample = portal.restaurants_data[0]
            print(f"📋 샘플 대표메뉴: {sample.get('representative_menu', 'N/A')}")
            print(f"📍 샘플 좌표: {sample.get('latitude', 'N/A')}, {sample.get('longitude', 'N/A')}")
        
        # 🔧 좌표 캐시 검증
        invalid_count = portal.validate_coordinates_cache()
        print(f"🧹 캐시 검증: {invalid_count}개 잘못된 좌표 발견")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

def test_coordinate_cleanup():
    """🔧 좌표 정리 테스트"""
    print("🧪 좌표 정리 테스트 시작...")
    
    try:
        portal = BusanRestaurantPortal()
        cleanup_invalid_coordinates(portal)
        print("✅ 좌표 정리 테스트 완료")
    except Exception as e:
        print(f"❌ 좌표 정리 테스트 실패: {e}")


if __name__ == "__main__":
    test_restaurant_portal()
    print("-" * 50)
    test_coordinate_cleanup()