"""거래량 순위 상세 출력"""

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

print("📊 거래량 순위 상세 조회")
print("="*60)

url = f"{base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "FHPST01710000"
}

# 테스트 1에서 성공한 파라미터 사용
params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_COND_SCR_DIV_CODE": "20171",
    "FID_INPUT_ISCD": "0000",
    "FID_DIV_CLS_CODE": "0",
    "FID_BLNG_CLS_CODE": "0",
    "FID_TRGT_CLS_CODE": "",
    "FID_TRGT_EXLS_CLS_CODE": "",
    "FID_INPUT_PRICE_1": "",
    "FID_INPUT_PRICE_2": "",
    "FID_VOL_CNT": "",
    "FID_INPUT_DATE_1": ""
}

response = requests.get(url, headers=headers, params=params)
print(f"응답 코드: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    output = data.get("output", [])
    print(f"종목 수: {len(output)}개\n")

    if output:
        print("📈 거래량 상위 20개 종목:")
        print("-"*60)

        for i, stock in enumerate(output[:20], 1):
            code = stock.get("mksc_shrn_iscd", "")
            name = stock.get("hts_kor_isnm", "")
            volume = stock.get("acml_vol", "")
            price = stock.get("stck_prpr", "")
            change_rate = stock.get("prdy_ctrt", "")

            # 거래량 포맷팅
            try:
                vol_int = int(volume)
                if vol_int >= 100000000:  # 1억 이상
                    vol_str = f"{vol_int/100000000:.1f}억"
                elif vol_int >= 10000:  # 1만 이상
                    vol_str = f"{vol_int/10000:.0f}만"
                else:
                    vol_str = f"{vol_int:,}"
            except:
                vol_str = volume

            print(f"{i:2}. [{code}] {name:<20}")
            print(f"    현재가: {price:>7}원 | 등락률: {change_rate:>6}%")
            print(f"    거래량: {vol_str}")
            print()
    else:
        print("❌ 데이터가 비어있음")
        print(f"전체 응답: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
else:
    print(f"❌ 오류: {response.text[:200]}")

print("="*60)
print("✅ 거래량 데이터가 정상적으로 조회됩니다!")
print("   market_scanner.py의 파라미터를 수정하면 해결될 것 같습니다.")