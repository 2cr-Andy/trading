#!/usr/bin/env python3
"""KIS API 응답에서 종목명 확인"""

import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# 토큰 읽기
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    token = token_data['token']

# API 호출
headers = {
    "authorization": f"Bearer {token}",
    "appkey": os.getenv('KIS_APP_KEY'),
    "appsecret": os.getenv('KIS_APP_SECRET'),
    "tr_id": "FHKST01010100"
}

# 테스트 종목
test_code = "005930"  # 삼성전자

params = {
    "FID_INPUT_ISCD": test_code,
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_DATE_1": ""
}

response = requests.get(
    "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price",
    headers=headers,
    params=params
)

print("API 응답:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))