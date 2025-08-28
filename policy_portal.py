"""
부산 정책지도 포털 - BusanPolicyPortal (좌표 캐싱 최적화)
===================================
정책 MD 파일들을 로드하고 필터링하는 전용 클래스

주요 기능:
- 정책 MD 파일 로드
- 지역별/카테고리별 필터링
- 검색 기능
- 통계 정보 제공
- 좌표 캐싱 및 성능 최적화
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

# 강제로 .env 파일 로드
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# 기존 dotenv 로드도 유지
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API 키 확인
api_key = os.getenv('KAKAO_REST_API_KEY')
if api_key:
    print(f"API 키: {api_key[:10]}...{api_key[-5:]}")

# 카카오 API 및 requests 선택적 import
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from config import (
    POLICY_MD_DIR, POLICY_REGIONS, AVAILABLE_POLICY_REGIONS,
    POLICY_CATEGORIES, POLICY_CATEGORY_COLORS, POLICY_REGION_COLORS,
    KAKAO_REST_API_KEY
)

logger = logging.getLogger(__name__)

# 부산 구별 대표 좌표 (백업용/빠른 로딩용)
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

# 수동 좌표 설정 (문제 정책사업들) - 최우선 적용
MANUAL_POLICY_COORDINATES = {
    "광무워터프론트파크": [35.1491, 129.0608],  # 부산진구 전포동
    "남부 운전면허시험장 이전 타당성조사": [35.1155, 129.0837],  # 남구 용호동
    "북항재개발1단계": [35.1184, 129.0494],  # 중앙동 육지 쪽
    "사상드림스마트시티": [35.1490, 128.9770]  # 사상구 학장동
}

# 부산 좌표 범위 (좌표 검증용)
BUSAN_BOUNDS = {
    'lat_min': 35.0,
    'lat_max': 35.4,
    'lng_min': 128.8,
    'lng_max': 129.4
}

class BusanPolicyPortal:
    """부산 정책지도 포털 클래스 (성능 최적화)"""
    
    def __init__(self):
        self.md_dir = POLICY_MD_DIR
        self.policy_data = []
        self.coordinates_cache = {}
        self.cache_file = Path("policy_coords_cache.pkl")
        
        # API 키 확인 로그 추가
        api_key = os.getenv('KAKAO_REST_API_KEY')
        print(f"API 키 로드됨: {'✅' if api_key else '❌'}")
        
        # 좌표 캐시 로드
        self._load_coordinates_cache()
        
        # 정책 데이터 로드
        self.load_policy_data()
    
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
        """부산 범위 내 좌표인지 검증"""
        return (BUSAN_BOUNDS['lat_min'] <= lat <= BUSAN_BOUNDS['lat_max'] and 
                BUSAN_BOUNDS['lng_min'] <= lon <= BUSAN_BOUNDS['lng_max'])
    
    def _clean_address(self, address: str) -> str:
        """주소에서 호수/건물명 정보 제거"""
        import re
        # 호수 정보 제거
        cleaned = re.sub(r'\s*\d+,?\d*호.*', '', address)
        # 괄호 안 정보 제거
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)
        return cleaned.strip()
    
    def _get_coordinates_from_kakao(self, name: str, location: str) -> tuple:
        """카카오 API로 좌표 추출 (주소 우선 검색)"""
        api_key = os.getenv('KAKAO_REST_API_KEY')
        
        if not api_key or not REQUESTS_AVAILABLE:
            print(f"❌ API 호출 불가: {name}")
            return (35.1, 129.065)  # 기본 좌표
        
        try:
            # 주소 정제: 호수/건물명 제거
            cleaned_location = self._clean_address(location)
            print(f"🧹 주소 정제: {location} → {cleaned_location}")
            
            # 1차: 정제된 주소로 검색 (더 정확함)
            url = "https://dapi.kakao.com/v2/local/search/address.json"
            headers = {"Authorization": f"KakaoAK {api_key}"}
            params = {"query": cleaned_location}
            
            print(f"📍 주소 검색: {cleaned_location}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    result = data['documents'][0]
                    lat = float(result['y'])
                    lon = float(result['x'])
                    
                    # 부산 범위 검증
                    if self._is_valid_busan_coordinate(lat, lon):
                        print(f"✅ 주소로 좌표 찾음: {name} → ({lat}, {lon})")
                        return (lat, lon)
                    else:
                        print(f"⚠️ 부산 범위 밖 좌표: {name} → ({lat}, {lon})")
            
            # 2차: 정책명+정제된주소 키워드 검색 (백업)
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            query = f"{name} {cleaned_location}"
            params = {"query": query}
            
            print(f"🔍 키워드 검색: {query}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    result = data['documents'][0]
                    lat = float(result['y'])
                    lon = float(result['x'])
                    
                    # 부산 범위 검증
                    if self._is_valid_busan_coordinate(lat, lon):
                        print(f"✅ 키워드로 좌표 찾음: {name} → ({lat}, {lon})")
                        return (lat, lon)
                    else:
                        print(f"⚠️ 부산 범위 밖 좌표: {name} → ({lat}, {lon})")
            
            print(f"❌ 좌표 못찾음: {name}")
            return (35.1, 129.065)  # 기본 좌표
            
        except Exception as e:
            print(f"❌ API 오류 {name}: {e}")
            return (35.1, 129.065)  # 기본 좌표
    
    def get_policy_coordinates(self, name: str, location: str) -> tuple:
        """정책사업 좌표 가져오기 (MD 파일 좌표 우선, 수동 좌표, 캐시, API, 구별 좌표 순)"""
        print(f"DEBUG - 정책: {name}")
        print(f"DEBUG - 주소: {location}")
        
        # 0순위: MD 파일에서 이미 좌표가 있는지 확인 (최우선)
        # 이 부분은 실제로는 _parse_markdown_file에서 처리되므로 여기서는 체크하지 않음
        
        # 1순위: 수동 좌표 체크 (최우선)
        if name in MANUAL_POLICY_COORDINATES:
            manual_coords = MANUAL_POLICY_COORDINATES[name]
            print(f"📌 수동 좌표 사용: {name} → ({manual_coords[0]}, {manual_coords[1]})")
            return manual_coords[0], manual_coords[1]
        
        if not location:
            # 주소가 없으면 부산진구 대표 좌표 사용
            default_coords = BUSAN_DISTRICT_COORDS.get("부산진구", [35.1630, 129.0530])
            print(f"🏢 기본 좌표 사용: {name} → 부산진구 ({default_coords[0]}, {default_coords[1]})")
            return default_coords[0], default_coords[1]
        
        # 캐시 키를 name + location 조합으로 변경
        cache_key = f"{name}_{location}"
        address_hash = self._get_address_hash(cache_key)
        
        # 캐시 검증: 부산 범위 내인지 확인 (북항재개발은 캐시 무시)
        if address_hash in self.coordinates_cache and name != "북항재개발 1단계":
            cached_coords = self.coordinates_cache[address_hash]
            lat, lon = cached_coords[0], cached_coords[1]
            
            # 캐시된 좌표가 부산 범위 내인지 확인
            if self._is_valid_busan_coordinate(lat, lon):
                print(f"💾 캐시 좌표 사용: {name} → ({lat}, {lon})")
                return lat, lon
            else:
                # 잘못된 캐시 삭제
                print(f"🗑️ 잘못된 캐시 삭제: {name} ({lat}, {lon})")
                del self.coordinates_cache[address_hash]
        
        # 카카오 API로 좌표 추출
        lat, lon = self._get_coordinates_from_kakao(name, location)
        
        # 유효한 좌표인지 확인
        if self._is_valid_busan_coordinate(lat, lon):
            # 캐시에 저장
            self.coordinates_cache[address_hash] = [lat, lon]
            print(f"✅ API 좌표 사용: {name} → ({lat}, {lon})")
            return lat, lon
        else:
            # API 실패 시 구별 대표 좌표 사용
            # location에서 구 이름 추출
            district = None
            for dist_name in BUSAN_DISTRICT_COORDS.keys():
                if dist_name in location:
                    district = dist_name
                    break
            
            district_coords = BUSAN_DISTRICT_COORDS.get(district or "부산진구", [35.1630, 129.0530])
            print(f"🏢 구별 대표 좌표 사용: {name} → {district or '부산진구'} ({district_coords[0]}, {district_coords[1]})")
            # 구별 좌표도 캐시에 저장 (다음에 더 빠르게)
            self.coordinates_cache[address_hash] = district_coords
            return district_coords[0], district_coords[1]
    
    def load_policy_data(self) -> List[Dict]:
        """정책 MD 파일들에서 데이터 로드 (좌표 포함)"""
        policy_list = []
        
        if not self.md_dir.exists():
            logger.error(f"📁 정책 디렉토리가 없습니다: {self.md_dir}")
            return []
        
        md_files = list(self.md_dir.glob("*.md"))
        
        if not md_files:
            logger.warning("📄 정책 MD 파일이 없습니다.")
            return []
        
        # 성능 개선: 처리 진행률 표시
        logger.info(f"📊 정책 데이터 로딩 시작: {len(md_files)}개 파일")
        
        coords_updated = False
        
        for idx, md_file in enumerate(md_files):
            try:
                policy_item = self._parse_markdown_file(md_file)
                if policy_item:
                    # 좌표 추가 (name, location 모두 전달)
                    name = policy_item.get('title', '')
                    location = policy_item.get('location', '')
                    
                    lat, lon = self.get_policy_coordinates(name, location)
                    policy_item['latitude'] = lat
                    policy_item['longitude'] = lon
                    
                    policy_list.append(policy_item)
                    coords_updated = True
                
                # 100개마다 진행률 로그
                if (idx + 1) % 100 == 0:
                    logger.info(f"⏳ 진행률: {idx + 1}/{len(md_files)} ({(idx + 1)/len(md_files)*100:.1f}%)")
                    
            except Exception as e:
                logger.error(f"정책 파일 파싱 오류 {md_file.name}: {e}")
                continue
        
        # 좌표 캐시 저장 (업데이트된 경우에만)
        if coords_updated:
            self._save_coordinates_cache()
        
        self.policy_data = policy_list
        
        logger.info(f"✅ 정책 {len(policy_list)}개 로드 완료 (좌표 포함)")
        return policy_list
    
    def _parse_markdown_file(self, md_file: Path) -> Optional[Dict]:
        """정책 MD 파일에서 메타데이터와 내용 추출"""
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
            
            # YAML 스타일 메타데이터 추출
            metadata = {}
            
            for line in frontmatter.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # 일반 키:값 처리
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    metadata[key] = value
            
            # 좌표 필드 변환 추가
            if 'lat' in metadata:
                try:
                    metadata['latitude'] = float(metadata['lat'])
                except:
                    pass

            if 'lon' in metadata:
                try:
                    metadata['longitude'] = float(metadata['lon'])
                except:
                    pass
            
            # 필수 필드 검증
            required_fields = ['title', 'location', 'category']
            for field in required_fields:
                if field not in metadata:
                    logger.warning(f"필수 필드 누락: {field} in {md_file.name}")
                    return None
            
            # 지역권 자동 설정 (location에서 구/군 추출)
            location = metadata.get('location', '')
            region = self._get_region_from_location(location)
            
            # 상세 정보 추출
            detailed_info = self._extract_detailed_info_from_body(body)
            
            return {
                'title': metadata.get('title', '정책사업'),
                'location': location,
                'region': region,
                'area': metadata.get('area', ''),
                'period': metadata.get('period', ''),
                'budget': metadata.get('budget', ''),
                'category': metadata.get('category', '기타'),
                'date': metadata.get('date', datetime.now().strftime("%Y-%m-%d")),
                'detailed_info': detailed_info,
                'file_path': str(md_file),
                'lat': metadata.get('latitude'),
                'lon': metadata.get('longitude')
            }
            
        except Exception as e:
            logger.error(f"정책 MD 파싱 오류: {e}")
            return None
    
    def _get_region_from_location(self, location: str) -> str:
        """location에서 지역권 찾기"""
        for region, districts in POLICY_REGIONS.items():
            for district in districts:
                if district in location:
                    return region
        return "기타"
    
    def _extract_detailed_info_from_body(self, body: str) -> str:
        """본문에서 상세 정보 추출"""
        lines = body.split('\n')
        info_lines = []
        
        # "## 🛠️ 주요내용" 또는 "## 🔍 추진상황" 부분 찾기
        target_sections = ['## 🛠️ 주요내용', '## 🔍 추진상황', '## 📈 향후계획']
        
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
        
        for policy in self.policy_data:
            region = policy.get('region', '기타')
            region_counts[region] = region_counts.get(region, 0) + 1
        
        # 전체 개수 추가
        region_counts["전체"] = len(self.policy_data)
        
        return region_counts
    
    def get_category_stats(self) -> Dict:
        """카테고리별 통계 계산"""
        category_counts = {}
        
        for policy in self.policy_data:
            category = policy.get('category', '기타')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 전체 개수 추가
        category_counts["전체"] = len(self.policy_data)
        
        return category_counts
    
    def filter_policies(self, selected_regions: List[str] = None,
                       selected_categories: List[str] = None,
                       search_query: str = "") -> List[Dict]:
        """정책 필터링"""
        filtered_policies = self.policy_data.copy()
        
        # 지역별 필터링
        if selected_regions and "전체" not in selected_regions:
            filtered_policies = [
                policy for policy in filtered_policies
                if policy.get('region') in selected_regions
            ]
        
        # 카테고리별 필터링
        if selected_categories and "전체" not in selected_categories:
            filtered_policies = [
                policy for policy in filtered_policies
                if policy.get('category') in selected_categories
            ]
        
        # 검색어 필터링
        if search_query:
            search_query = search_query.lower()
            filtered_policies = [
                policy for policy in filtered_policies
                if (search_query in policy.get('title', '').lower() or 
                    search_query in policy.get('location', '').lower() or
                    search_query in policy.get('category', '').lower() or
                    search_query in policy.get('detailed_info', '').lower())
            ]
        
        return filtered_policies
    
    def get_policies_by_region(self, region: str) -> List[Dict]:
        """특정 지역의 정책들 반환"""
        if region == "전체":
            return self.policy_data
        
        return [
            policy for policy in self.policy_data
            if policy.get('region') == region
        ]
    
    def get_policies_by_category(self, category: str) -> List[Dict]:
        """특정 카테고리의 정책들 반환"""
        if category == "전체":
            return self.policy_data
        
        return [
            policy for policy in self.policy_data
            if policy.get('category') == category
        ]
    
    def search_policies(self, query: str) -> List[Dict]:
        """정책 검색"""
        if not query:
            return self.policy_data
        
        query_lower = query.lower()
        results = []
        
        for policy in self.policy_data:
            score = 0
            
            # 제목 매칭 (가중치 3)
            if query_lower in policy.get('title', '').lower():
                score += 3
            
            # 카테고리 매칭 (가중치 2)
            if query_lower in policy.get('category', '').lower():
                score += 2
            
            # 지역/주소 매칭 (가중치 2)
            if (query_lower in policy.get('location', '').lower() or 
                query_lower in policy.get('region', '').lower()):
                score += 2
            
            # 내용 매칭 (가중치 1)
            if query_lower in policy.get('detailed_info', '').lower():
                score += 1
            
            if score > 0:
                policy_with_score = policy.copy()
                policy_with_score['search_score'] = score
                results.append(policy_with_score)
        
        # 점수순 정렬
        results.sort(key=lambda x: x.get('search_score', 0), reverse=True)
        return results


# 유틸리티 함수들

def get_policy_portal_stats(portal: BusanPolicyPortal) -> Dict:
    """정책 포털 통계 정보"""
    region_stats = portal.get_region_stats()
    category_stats = portal.get_category_stats()
    
    return {
        'total_policies': len(portal.policy_data),
        'region_count': len(region_stats) - 1,  # 전체 제외
        'category_count': len(category_stats) - 1,  # 전체 제외
        'region_distribution': region_stats,
        'category_distribution': category_stats,
        'cached_coordinates': len(portal.coordinates_cache),  # 캐시된 좌표 수
        'most_popular_region': max(
            [(k, v) for k, v in region_stats.items() if k != "전체"], 
            key=lambda x: x[1]
        ) if region_stats else ("없음", 0),
        'most_popular_category': max(
            [(k, v) for k, v in category_stats.items() if k != "전체"], 
            key=lambda x: x[1]
        ) if category_stats else ("없음", 0)
    }

def validate_coordinates_cache(self):
    """좌표 캐시 검증 및 정리"""
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

# BusanPolicyPortal 클래스에 메서드 추가
BusanPolicyPortal.validate_coordinates_cache = validate_coordinates_cache


if __name__ == "__main__":
    portal = BusanPolicyPortal()
    print(f"정책 데이터 {len(portal.policy_data)}개 로드됨")