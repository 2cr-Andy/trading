"""거래량 순위 API 상세 테스트"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# 토큰 로드
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    token = token_data['token']

app_key = os.getenv('KIS_APP_KEY')
app_secret = os.getenv('KIS_APP_SECRET')
base_url = "https://openapivts.koreainvestment.com:29443"

print("🔍 거래량 순위 API 테스트")
print("="*60)

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
    "FID_COND_SCR_DIV_CODE": "20171",
    "FID_INPUT_ISCD": "0000",
    "FID_RANK_SORT_CLS_CODE": "0",
    "FID_INPUT_CNT_1": "0",
    "FID_PAGING_KEY_100": "",
    "FID_TRGT_CLS_CODE": "111111111",
    "FID_TRGT_EXLS_CLS_CODE": "000000",
    "FID_DIV_CLS_CODE": "0",
    "FID_BLNG_CLS_CODE": "0",
    "FID_INPUT_PRICE_1": "",
    "FID_INPUT_PRICE_2": "",
    "FID_VOL_CNT": ""
}

response = requests.get(url, headers=headers, params=params)
print(f"응답 코드: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"rt_cd: {data.get('rt_cd')}")
    print(f"msg_cd: {data.get('msg_cd')}")
    print(f"msg1: {data.get('msg1')}")

    output = data.get("output", [])
    print(f"\n종목 수: {len(output)}개")

    if output:
        print("\n상위 10개 종목:")
        print("-"*60)
        for i, stock in enumerate(output[:10], 1):
            code = stock.get("mksc_shrn_iscd", "")
            name = stock.get("hts_kor_isnm", "")
            volume = stock.get("acml_vol", "")
            price = stock.get("stck_prpr", "")
            change_rate = stock.get("prdy_ctrt", "")

            print(f"{i:2}. [{code}] {name}")
            print(f"    현재가: {price}원 | 등락률: {change_rate}%")
            print(f"    거래량: {volume:,}" if volume else f"    거래량: {volume}")
    else:
        print("\n⚠️ 데이터 없음 - 전체 응답:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
else:
    print(f"❌ 오류: {response.text[:200]}")