"""토큰 발급 및 API 테스트"""

import os
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

app_key = os.getenv('KIS_APP_KEY')
app_secret = os.getenv('KIS_APP_SECRET')
base_url = "https://openapivts.koreainvestment.com:29443"

def get_token():
    """토큰 발급"""
    url = f"{base_url}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        print(f"토큰 발급 응답: {response.status_code}")

        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            print(f"✅ 토큰 발급 성공!")
            return token
        else:
            print(f"❌ 토큰 발급 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 토큰 발급 에러: {e}")
        return None

def test_volume_api(token):
    """거래량 API 테스트"""
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

    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"\n거래량 API 응답: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            output = data.get("output", [])
            print(f"✅ 종목 수: {len(output)}")

            if output:
                print("\n상위 5개 종목:")
                for i, stock in enumerate(output[:5], 1):
                    code = stock.get("mksc_shrn_iscd", "")
                    name = stock.get("hts_kor_isnm", "")
                    volume = stock.get("acml_vol", "")
                    print(f"{i}. {code} {name} - 거래량: {volume}")
        else:
            print(f"❌ API 실패: {response.text}")

    except Exception as e:
        print(f"❌ API 에러: {e}")

if __name__ == "__main__":
    print("=== KIS API 토큰 및 거래량 테스트 ===\n")

    # 1차 시도
    print("1차 토큰 발급 시도...")
    token = get_token()

    if token:
        print("\n거래량 API 테스트...")
        test_volume_api(token)

        # 재사용 테스트
        print("\n\n=== 토큰 재사용 테스트 (5초 후) ===")
        time.sleep(5)
        print("동일 토큰으로 API 재호출...")
        test_volume_api(token)
    else:
        print("\n60초 대기 후 재시도...")
        time.sleep(60)

        print("\n2차 토큰 발급 시도...")
        token = get_token()

        if token:
            print("\n거래량 API 테스트...")
            test_volume_api(token)