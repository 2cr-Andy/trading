#!/usr/bin/env python3
"""
거래량 순위 API 테스트 스크립트
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def get_access_token():
    """접속 토큰 발급"""
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    base_url = "https://openapivts.koreainvestment.com:29443"

    url = f"{base_url}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except Exception as e:
        print(f"❌ 토큰 발급 실패: {e}")
        return None

def test_volume_rank_api():
    """거래량 순위 API 테스트"""
    token = get_access_token()
    if not token:
        return

    print(f"✅ 토큰 발급 성공: {token[:20]}...")

    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    base_url = "https://openapivts.koreainvestment.com:29443"

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHPST01710000"
    }

    # 수정된 파라미터 (등락률 API와 동일한 필드 추가)
    current_params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000",
        "FID_RANK_SORT_CLS_CODE": "0",  # 추가
        "FID_INPUT_CNT_1": "0",         # 추가
        "FID_PAGING_KEY_100": "",       # 추가
        "FID_TRGT_CLS_CODE": "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000",
        "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "0",
        "FID_INPUT_PRICE_1": "",
        "FID_INPUT_PRICE_2": "",
        "FID_VOL_CNT": "",
        "FID_INPUT_DATE_1": ""
    }

    print(f"\n🔍 API 호출 정보:")
    print(f"URL: {url}")
    print(f"TR_ID: FHPST01710000")
    print(f"파라미터: {json.dumps(current_params, indent=2, ensure_ascii=False)}")

    try:
        response = requests.get(url, headers=headers, params=current_params)
        print(f"\n📡 HTTP 응답:")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        response.raise_for_status()
        data = response.json()

        print(f"\n📋 API 응답 분석:")
        print(f"rt_cd: {data.get('rt_cd')} (성공=0)")
        print(f"msg_cd: {data.get('msg_cd')}")
        print(f"msg1: {data.get('msg1')}")
        print(f"msg2: {data.get('msg2', 'N/A')}")

        output = data.get("output", [])
        print(f"output 배열 길이: {len(output)}")

        if len(output) == 0:
            print(f"\n⚠️ 빈 응답 - 전체 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\n✅ 데이터 발견! 첫 번째 항목:")
            print(json.dumps(output[0], indent=2, ensure_ascii=False))

            # 모든 항목의 종목 코드만 추출
            codes = []
            for item in output[:10]:  # 상위 10개만
                code = item.get("stck_shrn_iscd", "N/A")
                name = item.get("hts_kor_isnm", "N/A")
                volume = item.get("acml_vol", "N/A")
                print(f"  {code} ({name}): 거래량 {volume}")
                codes.append(code)

    except Exception as e:
        print(f"❌ API 호출 실패: {e}")

def test_alternative_params():
    """대안 파라미터로 테스트"""
    token = get_access_token()
    if not token:
        return

    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    base_url = "https://openapivts.koreainvestment.com:29443"

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHPST01710000"
    }

    # 대안 파라미터들
    alternative_params_list = [
        {
            "name": "기본 파라미터 (최소한)",
            "params": {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "",
                "FID_DIV_CLS_CODE": "",
                "FID_BLNG_CLS_CODE": "",
                "FID_TRGT_CLS_CODE": "",
                "FID_TRGT_EXLS_CLS_CODE": ""
            }
        },
        {
            "name": "코스닥 포함",
            "params": {
                "FID_COND_MRKT_DIV_CODE": "N",  # 코스닥
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": "0",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "000000"
            }
        },
        {
            "name": "전체 시장",
            "params": {
                "FID_COND_MRKT_DIV_CODE": "",  # 전체
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": "0",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "000000"
            }
        }
    ]

    for test in alternative_params_list:
        print(f"\n🧪 테스트: {test['name']}")
        print(f"파라미터: {json.dumps(test['params'], indent=2, ensure_ascii=False)}")

        try:
            response = requests.get(url, headers=headers, params=test['params'])
            data = response.json()

            output = data.get("output", [])
            print(f"결과: rt_cd={data.get('rt_cd')}, output 길이={len(output)}")

            if len(output) > 0:
                print(f"✅ 성공! 첫 번째 항목: {output[0].get('hts_kor_isnm', 'N/A')}")
                return  # 성공하면 중단

        except Exception as e:
            print(f"❌ 실패: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("한국투자증권 거래량 순위 API 테스트")
    print("=" * 60)

    print("\n1️⃣ 현재 파라미터로 테스트")
    test_volume_rank_api()

    print("\n2️⃣ 대안 파라미터로 테스트")
    test_alternative_params()

    print("\n테스트 완료!")