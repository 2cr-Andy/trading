#!/usr/bin/env python3
"""실시간 데이터를 Firebase에 정확하게 업데이트 (간단 버전)"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import requests
import time
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

                # 토큰 유효성 확인
                if token and time.time() < expires_at - 3600:
                    return token
        except Exception as e:
            print(f"토큰 파일 읽기 오류: {e}")

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
                    'current_price': float(output.get('stck_prpr', 0)),
                    'change_rate': float(output.get('prdy_ctrt', 0)),
                    'change_price': float(output.get('prdy_vrss', 0)),
                    'volume': float(output.get('acml_vol', 0)),
                    'high_price': float(output.get('stck_hgpr', 0)),
                    'low_price': float(output.get('stck_lwpr', 0))
                }
    except Exception as e:
        print(f"Error getting price for {stock_code}: {e}")

    return None

def update_realtime_data():
    """실시간 데이터 업데이트"""
    print("🔄 실시간 데이터 업데이트 시작...")

    # 액세스 토큰 발급
    access_token = get_access_token()
    if not access_token:
        print("❌ 액세스 토큰이 없습니다. update_portfolio_prices.py를 먼저 실행하세요.")
        return

    # 현재 감시 종목 목록 가져오기
    doc = db.collection('market_scan').document('latest').get()
    if not doc.exists:
        print("❌ 감시 종목 데이터가 없습니다.")
        return

    data = doc.to_dict()
    stocks = data.get('stocks', [])

    updated_stocks = []
    for stock in stocks:
        stock_code = stock.get('code')
        if stock_code:
            print(f"📊 {stock_code} 실시간 데이터 수집 중...")

            # 현재가 조회
            price_info = get_current_price(stock_code, access_token)

            if price_info:
                # 기존 데이터 업데이트
                stock['current_price'] = price_info['current_price']
                stock['change_rate'] = price_info['change_rate']
                stock['volume'] = price_info['volume']
                # RSI, MFI는 기존 값 유지 (계산이 복잡함)
                if 'rsi' not in stock:
                    stock['rsi'] = 50 + (price_info['change_rate'] * 2)  # 대략적 추정
                if 'mfi' not in stock:
                    stock['mfi'] = 50 + (price_info['change_rate'] * 1.5)  # 대략적 추정

                # 범위 제한
                stock['rsi'] = max(0, min(100, stock['rsi']))
                stock['mfi'] = max(0, min(100, stock['mfi']))

                print(f"✅ {stock_code} ({stock.get('name', '')}): {price_info['current_price']:,.0f}원, {price_info['change_rate']:+.2f}%")
            else:
                print(f"❌ {stock_code}: 현재가 조회 실패")

            updated_stocks.append(stock)
            time.sleep(0.1)  # API 제한 방지

    # Firebase에 업데이트
    db.collection('market_scan').document('latest').update({
        'stocks': updated_stocks,
        'last_updated': firestore.SERVER_TIMESTAMP
    })

    print(f"\n✅ {len(updated_stocks)}개 종목 실시간 데이터 업데이트 완료!")

if __name__ == "__main__":
    update_realtime_data()