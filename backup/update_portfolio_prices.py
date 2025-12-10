#!/usr/bin/env python3
"""포트폴리오 실시간 가격 업데이트 스크립트"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import requests
import time
from datetime import datetime
import json

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_access_token():
    """KIS API 액세스 토큰 발급 또는 기존 토큰 사용"""
    token_file = "kis_token.json"

    # 기존 토큰 파일 확인
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                token = token_data.get('token')
                expires_at = token_data.get('expires_at', 0)

                # 토큰 유효성 확인 (현재 시간보다 1시간 이상 남았는지)
                if token and time.time() < expires_at - 3600:
                    print("✅ 기존 토큰 사용")
                    return token
        except Exception as e:
            print(f"토큰 파일 읽기 오류: {e}")

    # 새 토큰 발급
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    data = {
        "grant_type": "client_credentials",
        "appkey": os.getenv('KIS_APP_KEY'),
        "appsecret": os.getenv('KIS_APP_SECRET')
    }

    print(f"새 토큰 발급 요청 중...")
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        if access_token:
            # 토큰 파일에 저장
            save_data = {
                'token': access_token,
                'expires_at': time.time() + 86400,  # 24시간 후 만료
                'created_at': time.time()
            }
            with open(token_file, 'w') as f:
                json.dump(save_data, f, indent=2)
            print("✅ 새 토큰 발급 성공")
            return access_token
    else:
        print(f"❌ 토큰 발급 실패: {response.status_code}")
        print(f"Response: {response.text}")
    return None

def get_current_price(stock_code, access_token):
    """현재가 조회"""
    try:
        headers = {
            "authorization": f"Bearer {access_token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "FHKST01010100"
        }

        params = {
            "FID_INPUT_ISCD": stock_code,
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_DATE_1": ""
        }

        base_url = "https://openapi.koreainvestment.com:9443"
        response = requests.get(
            f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('rt_cd') == '0':
                output = data.get('output', {})
                return {
                    'current_price': float(output.get('stck_prpr', 0)),  # 현재가
                    'change_rate': float(output.get('prdy_ctrt', 0)),    # 등락률
                    'change_price': float(output.get('prdy_vrss', 0)),   # 전일대비
                    'volume': float(output.get('acml_vol', 0)),          # 거래량
                    'high_price': float(output.get('stck_hgpr', 0)),     # 고가
                    'low_price': float(output.get('stck_lwpr', 0))       # 저가
                }
    except Exception as e:
        print(f"Error getting price for {stock_code}: {e}")

    return None

def update_portfolio_prices():
    """포트폴리오 가격 정보 업데이트"""
    print("포트폴리오 가격 업데이트 시작...")

    # 액세스 토큰 발급
    access_token = get_access_token()
    if not access_token:
        print("액세스 토큰 발급 실패")
        return

    # 포트폴리오 조회
    portfolio_docs = db.collection('portfolio').get()

    for doc in portfolio_docs:
        stock_code = doc.id
        stock_data = doc.to_dict()

        # 현재가 조회
        price_info = get_current_price(stock_code, access_token)

        if price_info:
            current_price = price_info['current_price']
            buy_price = stock_data.get('buy_price', 0)
            quantity = stock_data.get('quantity', 1)

            # 수익률 계산
            if buy_price > 0:
                profit_rate = ((current_price - buy_price) / buy_price) * 100
                profit_amount = (current_price - buy_price) * quantity
            else:
                profit_rate = 0
                profit_amount = 0

            # Firebase 업데이트
            update_data = {
                'current_price': current_price,
                'change_rate': price_info['change_rate'],
                'change_price': price_info['change_price'],
                'profit_rate': profit_rate,
                'profit_amount': profit_amount,
                'total_value': current_price * quantity,
                'high_price': price_info['high_price'],
                'low_price': price_info['low_price'],
                'volume': price_info['volume'],
                'last_updated': datetime.now().isoformat()
            }

            db.collection('portfolio').document(stock_code).update(update_data)

            print(f"✅ {stock_data.get('name', stock_code)}: "
                  f"현재가 {current_price:,.0f}원, "
                  f"수익률 {profit_rate:+.2f}%, "
                  f"평가손익 {profit_amount:+,.0f}원")

            # API 호출 제한 방지
            time.sleep(0.1)

    print("\n포트폴리오 가격 업데이트 완료!")

if __name__ == "__main__":
    update_portfolio_prices()