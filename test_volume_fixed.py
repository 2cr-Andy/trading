"""거래량 순위 API 수정 테스트 - 장마감 후"""

import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# 토큰 로드
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    token = token_data['token']

app_key = os.getenv('KIS_APP_KEY')
app_secret = os.getenv('KIS_APP_SECRET')
base_url = "https://openapivts.koreainvestment.com:29443"

print("🔍 거래량 순위 API 수정 테스트")
print("="*60)

# 테스트 1: 기본 거래량 순위 (FID_COND_SCR_DIV_CODE를 20171로)
print("\n[테스트 1] 기본 거래량 순위")
url = f"{base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "FHPST01710000"
}

params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_COND_SCR_DIV_CODE": "20171",  # 거래량 순위
    "FID_INPUT_ISCD": "0000",
    "FID_DIV_CLS_CODE": "0",
    "FID_BLNG_CLS_CODE": "0",
    "FID_TRGT_CLS_CODE": "",  # 비워보기
    "FID_TRGT_EXLS_CLS_CODE": "",
    "FID_INPUT_PRICE_1": "",
    "FID_INPUT_PRICE_2": "",
    "FID_VOL_CNT": "",
    "FID_INPUT_DATE_1": ""  # 날짜 추가
}

response = requests.get(url, headers=headers, params=params)
print(f"응답 코드: {response.status_code}")
data = response.json()
output = data.get("output", [])
print(f"종목 수: {len(output)}개")

if not output:
    print("데이터 없음")

# 테스트 2: 거래대금 순위로 시도
print("\n[테스트 2] 거래대금 순위")
params["FID_COND_SCR_DIV_CODE"] = "20172"  # 거래대금 순위

response = requests.get(url, headers=headers, params=params)
print(f"응답 코드: {response.status_code}")
data = response.json()
output = data.get("output", [])
print(f"종목 수: {len(output)}개")

if output:
    print("\n상위 5개 종목:")
    for i, stock in enumerate(output[:5], 1):
        code = stock.get("mksc_shrn_iscd", "")
        name = stock.get("hts_kor_isnm", "")
        volume = stock.get("acml_vol", "")
        amount = stock.get("acml_tr_pbmn", "")
        print(f"{i}. [{code}] {name}")
        print(f"   거래량: {volume}, 거래대금: {amount}")

# 테스트 3: 상승률 순위 (20170)
print("\n[테스트 3] 상승률 순위")
url = f"{base_url}/uapi/domestic-stock/v1/ranking/fluctuation"
headers["tr_id"] = "FHPST01700000"
headers["custtype"] = "P"

params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_COND_SCR_DIV_CODE": "20170",  # 상승률
    "FID_INPUT_ISCD": "0000",
    "FID_RANK_SORT_CLS_CODE": "0",
    "FID_INPUT_CNT_1": "30",  # 30개 요청
    "FID_PAGING_KEY_100": "",
    "FID_INPUT_PRICE_1": "",
    "FID_INPUT_PRICE_2": "",
    "FID_VOL_CNT": "",
    "FID_DIV_CLS_CODE": "0",
    "FID_BLNG_CLS_CODE": "1",  # 코스피
    "FID_TRGT_CLS_CODE": "",
    "FID_TRGT_EXLS_CLS_CODE": "",
    "FID_INPUT_DATE_1": ""
}

response = requests.get(url, headers=headers, params=params)
print(f"응답 코드: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    output = data.get("output", [])
    print(f"종목 수: {len(output)}개")

    if output:
        print("\n상위 5개 종목:")
        for i, stock in enumerate(output[:5], 1):
            code = stock.get("stck_shrn_iscd", "")
            name = stock.get("hts_kor_isnm", "")
            rate = stock.get("prdy_ctrt", "")
            volume = stock.get("acml_vol", "")
            print(f"{i}. [{code}] {name}: {rate}%")
            print(f"   거래량: {volume}")
else:
    print(f"오류: {response.text[:200]}")

# 테스트 4: 실시간 API 대신 일별 시세 조회
print("\n[테스트 4] 개별 종목 일별 시세로 거래량 확인 (삼성전자)")
url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
headers["tr_id"] = "FHKST01010400"
del headers["custtype"]  # custtype 제거

params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_ISCD": "005930",
    "FID_PERIOD_DIV_CODE": "D",
    "FID_ORG_ADJ_PRC": "0"
}

response = requests.get(url, headers=headers, params=params)
print(f"응답 코드: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    output = data.get("output", [])
    if output and len(output) > 0:
        latest = output[0]
        print(f"삼성전자 오늘 거래량: {latest.get('acml_vol', 'N/A')}")
        print(f"거래대금: {latest.get('acml_tr_pbmn', 'N/A')}")