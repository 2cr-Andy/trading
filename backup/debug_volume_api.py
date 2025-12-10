"""
거래량 순위 API 상세 디버깅 - 원시 응답 확인
"""

import os
import json
import requests
from dotenv import load_dotenv
import time

load_dotenv()

def debug_volume_api():
    """거래량 API 원시 응답 확인"""

    app_key = os.getenv('KIS_APP_KEY')
    app_secret = os.getenv('KIS_APP_SECRET')
    base_url = "https://openapivts.koreainvestment.com:29443"

    # 1. 토큰 발급
    print("=" * 60)
    print("1. 토큰 발급")
    print("=" * 60)

    url = f"{base_url}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))
    print(f"토큰 응답: {response.status_code}")

    if response.status_code != 200:
        print(f"에러: {response.text}")
        time.sleep(65)  # 1분 대기 후 재시도
        response = requests.post(url, headers=headers, data=json.dumps(body))
        if response.status_code != 200:
            return

    token_data = response.json()
    access_token = token_data.get("access_token")
    print(f"✅ 토큰: {access_token[:30]}...")

    # 2. 거래량 순위 API - 여러 파라미터 조합 테스트
    print("\n" + "=" * 60)
    print("2. 거래량 순위 API 테스트")
    print("=" * 60)

    test_cases = [
        {
            "name": "수정된 파라미터 (현재 사용중)",
            "params": {
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
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": ""
            }
        },
        {
            "name": "최소 파라미터",
            "params": {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000"
            }
        },
        {
            "name": "코스닥 시장",
            "params": {
                "FID_COND_MRKT_DIV_CODE": "Q",  # 코스닥
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_RANK_SORT_CLS_CODE": "0",
                "FID_INPUT_CNT_1": "0",
                "FID_PAGING_KEY_100": ""
            }
        }
    ]

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/volume-rank"

    for test in test_cases:
        print(f"\n테스트: {test['name']}")
        print("-" * 40)

        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {access_token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "FHPST01710000"
        }

        response = requests.get(url, headers=headers, params=test['params'])
        print(f"HTTP: {response.status_code}")

        # 원시 응답 확인
        raw_text = response.text
        print(f"원시 응답 길이: {len(raw_text)}")
        print(f"처음 200자: {raw_text[:200]}")

        # 응답이 비어있는지 확인
        if not raw_text or raw_text == "{}":
            print("⚠️ 완전히 빈 응답")
            continue

        try:
            data = response.json()

            # 키 존재 여부 확인
            print(f"응답 키들: {list(data.keys())}")
            print(f"rt_cd: '{data.get('rt_cd')}'")
            print(f"msg_cd: '{data.get('msg_cd')}'")
            print(f"msg1: '{data.get('msg1')}'")

            output = data.get('output', [])
            print(f"output 길이: {len(output)}")

            if output:
                print(f"✅ 데이터 발견!")
                print(f"첫 종목: {output[0]}")
                break
            else:
                print("❌ output이 비어있음")

        except Exception as e:
            print(f"파싱 에러: {e}")

    # 3. 실시간 시세 API 테스트 (검증용)
    print("\n" + "=" * 60)
    print("3. 실시간 시세 API (검증)")
    print("=" * 60)

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers["tr_id"] = "FHKST01010100"

    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": "005930"
    }

    response = requests.get(url, headers=headers, params=params)
    print(f"시세 API 상태: {response.status_code}")

    if response.text:
        data = response.json()
        if data.get('rt_cd') == '0' and data.get('output'):
            print(f"✅ 시세 API 정상: 삼성전자 {data['output'].get('stck_prpr')}원")
        else:
            print(f"시세 API 응답: {data}")

if __name__ == "__main__":
    debug_volume_api()