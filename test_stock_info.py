#!/usr/bin/env python3
"""KIS API 종목 기본정보 조회 - 종목명 포함 확인"""

import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# 토큰 읽기
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    token = token_data['token']

# 종목 기본정보 조회 API (다른 엔드포인트)
headers = {
    "authorization": f"Bearer {token}",
    "appkey": os.getenv('KIS_APP_KEY'),
    "appsecret": os.getenv('KIS_APP_SECRET'),
    "tr_id": "CTPF1002R"  # 종목 기본정보 조회
}

test_code = "005930"

params = {
    "PDNO": test_code,
    "PRDT_TYPE_CD": "300"  # 주식
}

response = requests.get(
    "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/search-stock-info",
    headers=headers,
    params=params
)

print("종목 기본정보 API 응답:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))