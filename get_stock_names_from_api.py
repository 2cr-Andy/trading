#!/usr/bin/env python3
"""KIS API에서 종목명 조회 - 다른 방법들 시도"""

import json
import requests
import os
from dotenv import load_dotenv
import hashlib
import time

load_dotenv()

# 토큰 읽기
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    token = token_data['token']

def make_hash_key(app_secret):
    """해시키 생성"""
    return hashlib.sha256(app_secret.encode()).hexdigest()

# 테스트 종목
test_code = "005930"

print("=" * 60)
print("KIS API 종목명 조회 테스트")
print("=" * 60)

# 1. 주식 일별 시세 조회 - 종목명 포함 가능성
headers = {
    "authorization": f"Bearer {token}",
    "appkey": os.getenv('KIS_APP_KEY'),
    "appsecret": os.getenv('KIS_APP_SECRET'),
    "tr_id": "FHKST01010400"
}

params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_ISCD": test_code,
    "FID_PERIOD_DIV_CODE": "D",
    "FID_ORG_ADJ_PRC": "1"
}

print("\n1. 일별 시세 API 테스트:")
response = requests.get(
    "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-price",
    headers=headers,
    params=params
)

if response.status_code == 200:
    data = response.json()
    print(f"응답 코드: {data.get('rt_cd')}")
    if data.get('rt_cd') == '0':
        # output 필드 확인
        if 'output' in data and len(data['output']) > 0:
            first_item = data['output'][0]
            print("첫 번째 항목 필드들:")
            for key, value in list(first_item.items())[:15]:
                print(f"  {key}: {value}")

# 2. 호가 조회 API
print("\n2. 호가 조회 API 테스트:")
headers2 = {
    "authorization": f"Bearer {token}",
    "appkey": os.getenv('KIS_APP_KEY'),
    "appsecret": os.getenv('KIS_APP_SECRET'),
    "tr_id": "FHKST01010200"
}

params2 = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_ISCD": test_code
}

response2 = requests.get(
    "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
    headers=headers2,
    params=params2
)

if response2.status_code == 200:
    data = response2.json()
    print(f"응답 코드: {data.get('rt_cd')}")
    if data.get('rt_cd') == '0' and 'output1' in data:
        output1 = data['output1']
        print("Output1 필드들 (처음 10개):")
        for key, value in list(output1.items())[:10]:
            print(f"  {key}: {value}")

# 3. 체결 조회 API
print("\n3. 체결 조회 API 테스트:")
headers3 = {
    "authorization": f"Bearer {token}",
    "appkey": os.getenv('KIS_APP_KEY'),
    "appsecret": os.getenv('KIS_APP_SECRET'),
    "tr_id": "FHKST01010300"
}

params3 = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_ISCD": test_code
}

response3 = requests.get(
    "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-ccnl",
    headers=headers3,
    params=params3
)

if response3.status_code == 200:
    data = response3.json()
    print(f"응답 코드: {data.get('rt_cd')}")
    if data.get('rt_cd') == '0' and 'output' in data:
        if len(data['output']) > 0:
            print("첫 번째 체결 데이터:")
            for key, value in list(data['output'][0].items())[:10]:
                print(f"  {key}: {value}")

print("\n" + "=" * 60)
print("결론: KIS API의 시세 조회 API들은 종목명을 제공하지 않습니다.")
print("해결 방법:")
print("1. 종목 마스터 파일 다운로드 (별도 제공)")
print("2. 잔고 조회 API 사용 (보유 종목만)")
print("3. 종목명 매핑 테이블 직접 구축")
print("=" * 60)