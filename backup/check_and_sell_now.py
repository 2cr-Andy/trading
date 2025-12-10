#!/usr/bin/env python3
"""즉시 매도 체크 및 실행 스크립트"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import json
import requests
from datetime import datetime

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_access_token():
    """토큰 가져오기"""
    try:
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            return token_data.get('token')
    except:
        return None

def execute_sell(stock_code, quantity, reason):
    """매도 실행"""
    token = get_access_token()
    if not token:
        print(f"❌ 토큰이 없습니다")
        return False

    account_no = os.getenv('KIS_ACCOUNT_NUMBER')
    if not account_no:
        print(f"❌ 계좌번호가 없습니다")
        return False

    # 계좌번호 형식 처리 (8자리-2자리 형식으로 변환)
    if '-' not in account_no:
        account_no = f"{account_no}-01"  # 기본값 01 추가

    url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": os.getenv('KIS_APP_KEY'),
        "appsecret": os.getenv('KIS_APP_SECRET'),
        "tr_id": "VTTC0801U"  # 모의투자 매도
    }

    data = {
        "CANO": account_no.split('-')[0],
        "ACNT_PRDT_CD": account_no.split('-')[1],
        "PDNO": stock_code,
        "ORD_DVSN": "01",  # 시장가
        "ORD_QTY": str(quantity),
        "ORD_UNPR": "0"
    }

    print(f"📤 매도 주문 전송: {stock_code} {quantity}주")

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        if result.get('rt_cd') == '0':
            print(f"✅ 매도 주문 성공!")
            print(f"   주문번호: {result.get('output', {}).get('ODNO')}")
            return True
        else:
            print(f"❌ 매도 실패: {result.get('msg1')}")
            return False
    else:
        print(f"❌ API 오류: {response.status_code}")
        return False

def check_portfolio():
    """포트폴리오 체크 및 매도"""
    print("=" * 60)
    print("📊 포트폴리오 매도 조건 체크")
    print("=" * 60)

    # Firebase에서 포트폴리오 가져오기
    portfolio_docs = db.collection('portfolio').stream()

    for doc in portfolio_docs:
        stock_code = doc.id
        data = doc.to_dict()

        name = data.get('name', stock_code)
        buy_price = data.get('buy_price', 0)
        current_price = data.get('current_price', 0)
        quantity = data.get('quantity', 0)
        profit_rate = data.get('profit_rate', 0)

        print(f"\n종목: {name} ({stock_code})")
        print(f"  매수가: {buy_price:,.0f}원")
        print(f"  현재가: {current_price:,.0f}원")
        print(f"  수량: {quantity}주")
        print(f"  수익률: {profit_rate:+.2f}%")

        # 매도 조건 체크
        should_sell = False
        reason = ""

        # 1. 익절 조건 (5% 이상)
        if profit_rate >= 5.0:
            should_sell = True
            reason = f"익절 목표 달성 ({profit_rate:.2f}%)"

        # 2. 손절 조건 (-3% 이하)
        elif profit_rate <= -3.0:
            should_sell = True
            reason = f"손절 ({profit_rate:.2f}%)"

        # 3. 켐트로스 특별 처리 (10% 넘음)
        if stock_code == "220260" and profit_rate >= 10.0:
            should_sell = True
            reason = f"10% 초과 익절 ({profit_rate:.2f}%)"

        if should_sell:
            print(f"  🔴 매도 신호: {reason}")

            # 자동 매도 실행
            print(f"  ⏳ 자동 매도 실행 중...")
            if True:  # 자동 실행
                success = execute_sell(stock_code, quantity, reason)

                if success:
                    # Firebase에서 제거
                    db.collection('portfolio').document(stock_code).delete()
                    print(f"  ✅ Firebase에서 제거 완료")
        else:
            print(f"  ⚪ 보유 유지")

    print("\n" + "=" * 60)
    print("체크 완료!")

def main():
    """메인 실행"""
    print("🚀 매도 조건 체크 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    check_portfolio()

if __name__ == "__main__":
    main()