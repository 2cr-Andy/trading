#!/usr/bin/env python3
"""KIS API 500 에러 디버깅"""

import os
import json
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

def get_access_token():
    """토큰 가져오기"""
    try:
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            return token_data.get('token')
    except:
        return None

def test_apis():
    """각 API 엔드포인트 테스트"""
    token = get_access_token()
    if not token:
        print("❌ 토큰이 없습니다")
        return

    account_no = os.getenv('KIS_ACCOUNT_NUMBER')
    if '-' not in account_no:
        account_no = f"{account_no}-01"

    print("=" * 60)
    print("🔍 KIS API 테스트 시작")
    print("=" * 60)

    # 공통 헤더
    base_headers = {
        "authorization": f"Bearer {token}",
        "appkey": os.getenv('KIS_APP_KEY'),
        "appsecret": os.getenv('KIS_APP_SECRET'),
        "content-type": "application/json; charset=utf-8"
    }

    # 1. 시세 조회 테스트
    print("\n1️⃣ 현재가 조회 테스트")
    print("-" * 40)

    stock_codes = ['005930', '000660', '220260']  # 삼성전자, SK하이닉스, 켐트로스

    for stock_code in stock_codes:
        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        try:
            response = requests.get(url, headers=base_headers, params=params, timeout=10)
            print(f"  📊 {stock_code}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"     ✅ rt_cd: {data.get('rt_cd')}, msg: {data.get('msg1')}")
            else:
                print(f"     ❌ 에러: {response.text[:100]}...")

        except Exception as e:
            print(f"     ❌ 예외: {e}")

    # 2. 잔고 조회 테스트
    print("\n2️⃣ 계좌 잔고 조회 테스트")
    print("-" * 40)

    url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {**base_headers, "tr_id": "VTTC8434R"}
    params = {
        "CANO": account_no.split('-')[0],
        "ACNT_PRDT_CD": account_no.split('-')[1],
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "N",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"  💰 잔고 조회: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"     ✅ rt_cd: {data.get('rt_cd')}, msg: {data.get('msg1')}")
            if data.get('output1'):
                print(f"     📈 보유 종목 수: {len([x for x in data['output1'] if int(float(x.get('hldg_qty', 0))) > 0])}")
        else:
            print(f"     ❌ 에러: {response.text[:100]}...")

    except Exception as e:
        print(f"     ❌ 예외: {e}")

    # 3. 매도 테스트 (시뮬레이션)
    print("\n3️⃣ 매도 주문 테스트 (시뮬레이션)")
    print("-" * 40)

    url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
    headers = {**base_headers, "tr_id": "VTTC0801U"}

    # 실제 주문은 하지 않고 헤더와 요청 형식만 검증
    test_body = {
        "CANO": account_no.split('-')[0],
        "ACNT_PRDT_CD": account_no.split('-')[1],
        "PDNO": "005930",  # 삼성전자 테스트
        "ORD_DVSN": "01",  # 시장가
        "ORD_QTY": "0",    # 수량 0으로 테스트
        "ORD_UNPR": "0"
    }

    print(f"  📤 매도 요청 형식 검증:")
    print(f"     URL: {url}")
    print(f"     Headers: tr_id={headers.get('tr_id')}")
    print(f"     Body: {json.dumps(test_body, ensure_ascii=False)}")

    # 실제 요청은 수량이 0이므로 안전
    try:
        response = requests.post(url, headers=headers, json=test_body, timeout=10)
        print(f"  📤 매도 요청: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"     ✅ rt_cd: {data.get('rt_cd')}, msg: {data.get('msg1')}")
        else:
            print(f"     ❌ 에러: {response.text[:100]}...")

    except Exception as e:
        print(f"     ❌ 예외: {e}")

    # 4. 토큰 상태 확인
    print("\n4️⃣ 토큰 상태 확인")
    print("-" * 40)

    import jwt
    try:
        # JWT 토큰 디코딩 (검증 없이)
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get('exp', 0)
        exp_datetime = datetime.fromtimestamp(exp, tz=pytz.timezone('Asia/Seoul'))
        now = datetime.now(pytz.timezone('Asia/Seoul'))

        print(f"  🔑 토큰 만료: {exp_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  ⏰ 현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  ✅ 유효 시간: {exp_datetime - now}")

    except Exception as e:
        print(f"  ❌ 토큰 디코딩 실패: {e}")

    print("\n" + "=" * 60)
    print("✅ API 테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_apis()