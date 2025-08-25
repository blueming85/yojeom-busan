import os
import requests

# API 키 확인
api_key = os.getenv('KAKAO_REST_API_KEY')
print(f'API키: {api_key}')

if api_key:
    # 카카오 API 테스트
    url = 'https://dapi.kakao.com/v2/local/search/address.json'
    headers = {'Authorization': f'KakaoAK {api_key}'}
    params = {'query': '부산 해운대구'}
    
    try:
        print('🔍 카카오 API 호출 중...')
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f'API 응답 코드: {response.status_code}')
        
        if response.status_code == 200:
            print('✅ API 정상 작동!')
            data = response.json()
            documents = data.get('documents', [])
            print(f'검색 결과: {len(documents)}개')
            
            if documents:
                first = documents[0]
                print(f'첫 번째 결과: {first.get("address_name")}')
                print(f'좌표: {first.get("x")}, {first.get("y")}')
        else:
            print(f'❌ API 오류: {response.status_code}')
            print(f'응답 내용: {response.text}')
            
    except requests.exceptions.Timeout:
        print('❌ 타임아웃 오류: API 응답이 너무 느립니다')
    except requests.exceptions.ConnectionError:
        print('❌ 연결 오류: 네트워크를 확인해주세요')
    except Exception as e:
        print(f'❌ 예상치 못한 오류: {e}')
else:
    print('❌ API 키가 없습니다!')

# 특정 식당 주소로도 테스트
print('\n' + '='*50)
print('🍴 실제 식당 주소 테스트')

test_addresses = [
    '부산 수영구 무학로33번길 54',  # 피리피리
    '부산 수영구 민락본동로19번길 30-5',  # 야키토리 해공
    '부산 해운대구 해운대해변로 296'  # 일반적인 주소
]

for addr in test_addresses:
    if api_key:
        try:
            params = {'query': addr}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get('documents', [])
                if docs:
                    print(f'✅ {addr} → 좌표 찾음')
                else:
                    print(f'❌ {addr} → 좌표 못찾음')
            else:
                print(f'❌ {addr} → API 오류')
        except:
            print(f'❌ {addr} → 네트워크 오류')