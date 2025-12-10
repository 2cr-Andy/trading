#!/usr/bin/env python3
"""KIS API 종목 마스터 조회 - 종목명 포함 확인"""

import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# 토큰 읽기
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    token = token_data['token']

# 테스트할 종목 코드들
test_codes = ["005930", "090710", "220260"]

print("=" * 60)
print("KIS API 종목 마스터 정보 조회 테스트")
print("=" * 60)

# 1. 주식 종목 조회 API (CTPF1002R) - 종목 기본정보
headers1 = {
    "authorization": f"Bearer {token}",
    "appkey": os.getenv('KIS_APP_KEY'),
    "appsecret": os.getenv('KIS_APP_SECRET'),
    "tr_id": "CTPF1002R"
}

params1 = {
    "PDNO": test_codes[0],
    "PRDT_TYPE_CD": "300"
}

print("\n1. 종목 기본정보 API (CTPF1002R):")
response = requests.get(
    "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/search-stock-info",
    headers=headers1,
    params=params1
)

if response.status_code == 200:
    data = response.json()
    print(f"응답 코드: {data.get('rt_cd')}")
    if 'output' in data:
        print("Output 필드들:")
        for key in list(data['output'].keys())[:10]:
            print(f"  - {key}: {data['output'][key]}")
else:
    print(f"오류: {response.status_code}")

# 2. 주식 잔고 조회 API - 종목명이 있을 가능성
headers2 = {
    "authorization": f"Bearer {token}",
    "appkey": os.getenv('KIS_APP_KEY'),
    "appsecret": os.getenv('KIS_APP_SECRET'),
    "tr_id": "TTTC8434R"
}

params2 = {
    "CANO": os.getenv('KIS_ACCOUNT_NO', '').split('-')[0],
    "ACNT_PRDT_CD": os.getenv('KIS_ACCOUNT_NO', '').split('-')[1] if '-' in os.getenv('KIS_ACCOUNT_NO', '') else "01",
    "AFHR_FLPR_YN": "N",
    "OFL_YN": "N",
    "INQR_DVSN": "01",
    "UNPR_DVSN": "01",
    "FUND_STTL_ICLD_YN": "N",
    "FNCG_AMT_AUTO_RDPT_YN": "N",
    "PRCS_DVSN": "01",
    "CTX_AREA_FK100": "",
    "CTX_AREA_NK100": ""
}

print("\n2. 주식 잔고 조회 API (TTTC8434R):")
response2 = requests.get(
    "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance",
    headers=headers2,
    params=params2
)

if response2.status_code == 200:
    data = response2.json()
    print(f"응답 코드: {data.get('rt_cd')}")
    if 'output1' in data and len(data['output1']) > 0:
        print("첫 번째 종목:")
        stock = data['output1'][0]
        for key in ['pdno', 'prdt_name', 'hldg_qty', 'pchs_avg_pric']:
            if key in stock:
                print(f"  - {key}: {stock[key]}")
else:
    print(f"오류: {response2.status_code}")

# 3. 매수가능 조회 API
headers3 = {
    "authorization": f"Bearer {token}",
    "appkey": os.getenv('KIS_APP_KEY'),
    "appsecret": os.getenv('KIS_APP_SECRET'),
    "tr_id": "TTTC8908R"
}

params3 = {
    "CANO": os.getenv('KIS_ACCOUNT_NO', '').split('-')[0],
    "ACNT_PRDT_CD": os.getenv('KIS_ACCOUNT_NO', '').split('-')[1] if '-' in os.getenv('KIS_ACCOUNT_NO', '') else "01",
    "PDNO": test_codes[0],
    "ORD_UNPR": "100000",
    "ORD_DVSN": "01",
    "CMA_EVLU_AMT_ICLD_YN": "N",
    "OVRS_ICLD_YN": "N"
}

print("\n3. 매수가능 조회 API (TTTC8908R):")
response3 = requests.get(
    "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-psbl-order",
    headers=headers3,
    params=params3
)

if response3.status_code == 200:
    data = response3.json()
    print(f"응답 코드: {data.get('rt_cd')}")
    if 'output' in data:
        print("Output 필드들:")
        for key in list(data['output'].keys())[:10]:
            print(f"  - {key}: {data['output'][key]}")
else:
    print(f"오류: {response3.status_code}")