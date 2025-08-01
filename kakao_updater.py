import requests
import yaml
import re
import time
import os
from pathlib import Path
from typing import Dict, List, Optional

class KakaoRestaurantUpdater:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        self.headers = {"Authorization": f"KakaoAK {api_key}"}
        
    def search_restaurant(self, restaurant_name: str, address: str = "") -> Optional[Dict]:
        """카카오 API로 음식점 정보 검색"""
        # 검색 쿼리 구성 (음식점명 + 주소의 구 정보)
        if address:
            # 주소에서 구 정보 추출 (예: "해운대구")
            district_match = re.search(r'(\w+구)', address)
            district = district_match.group(1) if district_match else ""
            query = f"{restaurant_name} {district}"
        else:
            query = restaurant_name
            
        params = {
            "query": query,
            "category_group_code": "FD6",  # 음식점 카테고리
            "size": 5  # 검색 결과 개수
        }
        
        try:
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data['documents']:
                # 가장 관련성 높은 결과 반환
                return self.select_best_match(data['documents'], restaurant_name)
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"API 요청 실패: {e}")
            return None
    
    def select_best_match(self, results: List[Dict], restaurant_name: str) -> Dict:
        """검색 결과 중 가장 적합한 결과 선택"""
        # 음식점명이 정확히 일치하는 것 우선
        for result in results:
            if restaurant_name in result['place_name'] or result['place_name'] in restaurant_name:
                return result
        
        # 없으면 첫 번째 결과 반환
        return results[0]
    
    def extract_restaurant_info(self, kakao_data: Dict) -> Dict:
        """카카오 API 데이터에서 필요한 정보 추출"""
        info = {
            'phone': kakao_data.get('phone', ''),
            'address': kakao_data.get('address_name', ''),
            'road_address': kakao_data.get('road_address_name', ''),
            'place_name': kakao_data.get('place_name', ''),
            'place_url': kakao_data.get('place_url', ''),
            'category_name': kakao_data.get('category_name', '')
        }
        
        # 전화번호 형식 정리 (051-xxx-xxxx 형식)
        if info['phone']:
            phone = info['phone'].replace('-', '').replace(' ', '')
            if phone.startswith('051') and len(phone) >= 10:
                info['formatted_phone'] = phone[:3] + '-' + phone[3:6] + '-' + phone[6:]
                info['display_phone'] = phone[:3] + '-' + phone[3:6] + '-' + phone[6:]
            else:
                # 다른 지역번호도 하이픈 형식으로 처리
                if len(phone) >= 10:
                    if phone.startswith(('02', '031', '032', '033', '041', '042', '043', '044', '052', '053', '054', '055', '061', '062', '063', '064')):
                        if phone.startswith('02'):
                            info['formatted_phone'] = phone[:2] + '-' + phone[2:5] + '-' + phone[5:]
                            info['display_phone'] = phone[:2] + '-' + phone[2:5] + '-' + phone[5:]
                        else:
                            info['formatted_phone'] = phone[:3] + '-' + phone[3:6] + '-' + phone[6:]
                            info['display_phone'] = phone[:3] + '-' + phone[3:6] + '-' + phone[6:]
                    else:
                        info['formatted_phone'] = info['phone']
                        info['display_phone'] = info['phone']
                else:
                    info['formatted_phone'] = info['phone']
                    info['display_phone'] = info['phone']
        
        return info

class MarkdownUpdater:
    def __init__(self):
        pass
    
    def parse_md_file(self, file_path: str) -> Dict:
        """MD 파일을 파싱하여 YAML frontmatter와 본문 분리"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # YAML frontmatter 추출
        yaml_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if yaml_match:
            yaml_content = yaml_match.group(1)
            markdown_content = yaml_match.group(2)
            
            # YAML 파싱
            try:
                yaml_data = yaml.safe_load(yaml_content)
                return {
                    'yaml': yaml_data,
                    'markdown': markdown_content,
                    'original': content
                }
            except yaml.YAMLError as e:
                print(f"YAML 파싱 오류: {e}")
                return None
        else:
            print("YAML frontmatter를 찾을 수 없습니다.")
            return None
    
    def update_yaml_info(self, yaml_data: Dict, kakao_info: Dict) -> Dict:
        """YAML frontmatter 정보 업데이트"""
        if kakao_info.get('display_phone'):
            yaml_data['phone'] = kakao_info['display_phone']
        
        if kakao_info.get('road_address'):
            yaml_data['address'] = kakao_info['road_address']
        elif kakao_info.get('address'):
            yaml_data['address'] = kakao_info['address']
            
        return yaml_data
    
    def update_markdown_content(self, markdown_content: str, kakao_info: Dict) -> str:
        """마크다운 본문 내용 업데이트"""
        updated_content = markdown_content
        
        # 전화번호 업데이트
        if kakao_info.get('display_phone'):
            phone_pattern = r'\*\*전화번호\*\*:\s*[0-9\-\s]+'
            replacement = f"**전화번호**: {kakao_info['display_phone']}"
            updated_content = re.sub(phone_pattern, replacement, updated_content)
        
        # 주소 업데이트
        if kakao_info.get('road_address'):
            address_pattern = r'\*\*주소\*\*:\s*.*?(?=\n|$)'
            replacement = f"**주소**: {kakao_info['road_address']}"
            updated_content = re.sub(address_pattern, replacement, updated_content)
        elif kakao_info.get('address'):
            address_pattern = r'\*\*주소\*\*:\s*.*?(?=\n|$)'
            replacement = f"**주소**: {kakao_info['address']}"
            updated_content = re.sub(address_pattern, replacement, updated_content)
        
        # 카카오맵 링크 업데이트 (place_url이 있는 경우)
        if kakao_info.get('place_url'):
            kakao_map_pattern = r'- \*\*카카오맵\*\*: \[지도에서 보기\]\(.*?\)'
            replacement = f"- **카카오맵**: [지도에서 보기]({kakao_info['place_url']})"
            updated_content = re.sub(kakao_map_pattern, replacement, updated_content)
        
        return updated_content
    
    def save_updated_file(self, file_path: str, yaml_data: Dict, markdown_content: str):
        """업데이트된 내용을 파일로 저장"""
        # YAML frontmatter 재구성
        yaml_str = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True)
        
        # 전체 내용 조합
        updated_content = f"---\n{yaml_str}---\n{markdown_content}"
        
        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"파일 업데이트 완료: {file_path}")

def process_restaurants_batch(md_files: List[str], api_key: str, batch_size: int = 50):
    """배치 단위로 음식점 정보 업데이트"""
    updater = KakaoRestaurantUpdater(api_key)
    md_updater = MarkdownUpdater()
    
    total_files = len(md_files)
    processed = 0
    
    for i in range(0, total_files, batch_size):
        batch_files = md_files[i:i + batch_size]
        print(f"\n배치 {i//batch_size + 1} 처리 중... ({len(batch_files)}개 파일)")
        
        for file_path in batch_files:
            try:
                print(f"처리 중: {os.path.basename(file_path)}")
                
                # MD 파일 파싱
                parsed_data = md_updater.parse_md_file(file_path)
                if not parsed_data:
                    print(f"파일 파싱 실패: {file_path}")
                    continue
                
                # 음식점명 추출
                restaurant_name = parsed_data['yaml'].get('title', '')
                current_address = parsed_data['yaml'].get('address', '')
                
                if not restaurant_name:
                    print(f"음식점명을 찾을 수 없습니다: {file_path}")
                    continue
                
                # 카카오 API로 검색
                kakao_info = updater.search_restaurant(restaurant_name, current_address)
                if not kakao_info:
                    print(f"검색 결과가 없습니다: {restaurant_name}")
                    continue
                
                # 정보 추출
                extracted_info = updater.extract_restaurant_info(kakao_info)
                print(f"검색된 정보: {extracted_info['place_name']}")
                
                # YAML 및 마크다운 업데이트
                updated_yaml = md_updater.update_yaml_info(parsed_data['yaml'], extracted_info)
                updated_markdown = md_updater.update_markdown_content(parsed_data['markdown'], extracted_info)
                
                # 파일 저장
                md_updater.save_updated_file(file_path, updated_yaml, updated_markdown)
                
                processed += 1
                
                # API 호출 제한을 위한 딜레이
                time.sleep(0.1)  # 100ms 딜레이
                
            except Exception as e:
                print(f"오류 발생 ({file_path}): {e}")
                continue
        
        # 배치 간 딜레이
        if i + batch_size < total_files:
            print(f"배치 완료. 5초 대기 중...")
            time.sleep(5)
    
    print(f"\n전체 처리 완료: {processed}/{total_files}개 파일")

# 사용 예시
if __name__ == "__main__":
    # 설정
    API_KEY = "9ac74f0720d81fa56b594abe8c32649f"
    MD_FILES_DIR = "./data/restaurants/md"  # MD 파일들이 있는 디렉토리
    BATCH_SIZE = 50
    
    # MD 파일 목록 가져오기
    md_files = list(Path(MD_FILES_DIR).glob("*.md"))
    
    if not md_files:
        print("MD 파일을 찾을 수 없습니다.")
    else:
        print(f"총 {len(md_files)}개의 MD 파일을 찾았습니다.")
        
        # 테스트를 위해 첫 번째 파일만 처리
        #test_file = [str(md_files[0])]
        #print(f"테스트 실행: {os.path.basename(test_file[0])}")
        
        #process_restaurants_batch(test_file, API_KEY, 1)
        
        # 전체 파일 처리를 원한다면 아래 주석 해제
        process_restaurants_batch([str(f) for f in md_files], API_KEY, BATCH_SIZE)