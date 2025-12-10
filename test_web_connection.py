#!/usr/bin/env python3
"""웹페이지 데이터 연결 테스트"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def test_firebase_data():
    """Firebase 데이터 확인"""
    print("🔍 Firebase 데이터 연결 테스트")
    print("=" * 50)

    # 1. 계좌 정보
    print("\n1. 📊 계좌 정보:")
    try:
        account_doc = db.collection('account').document('summary').get()
        if account_doc.exists:
            data = account_doc.to_dict()
            print(f"   ✅ totalAssets: {data.get('totalAssets'):,}원")
            print(f"   ✅ totalCash: {data.get('totalCash'):,}원")
            print(f"   ✅ todayPnL: {data.get('todayPnL')}원")
        else:
            print("   ❌ 계좌 정보 없음")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 2. 봇 상태
    print("\n2. 🤖 봇 상태:")
    try:
        bot_doc = db.collection('bot_status').document('main').get()
        if bot_doc.exists:
            data = bot_doc.to_dict()
            print(f"   ✅ 실행 상태: {'실행 중' if data.get('running') else '정지'}")
            print(f"   ✅ 마지막 활동: {data.get('lastHeartbeat')}")
        else:
            print("   ❌ 봇 상태 정보 없음")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 3. 감시 종목 (처음 3개)
    print("\n3. 📈 감시 종목 (처음 3개):")
    try:
        market_doc = db.collection('market_scan').document('latest').get()
        if market_doc.exists:
            data = market_doc.to_dict()
            stocks = data.get('stocks', [])
            for i, stock in enumerate(stocks[:3]):
                print(f"   ✅ {stock.get('code')} ({stock.get('name', 'N/A')}):")
                print(f"       현재가: {stock.get('current_price', 0):,.0f}원")
                print(f"       등락률: {stock.get('change_rate', 0):+.2f}%")
                print(f"       거래량: {stock.get('volume', 0):,.0f}")
                print(f"       RSI: {stock.get('rsi', 0):.1f}")
                print(f"       MFI: {stock.get('mfi', 0):.1f}")
        else:
            print("   ❌ 감시 종목 정보 없음")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 4. 포트폴리오 (처음 2개)
    print("\n4. 💼 포트폴리오 (처음 2개):")
    try:
        portfolio_docs = db.collection('portfolio').limit(2).get()
        for doc in portfolio_docs:
            data = doc.to_dict()
            print(f"   ✅ {doc.id} ({data.get('name', 'N/A')}):")
            print(f"       구매가: {data.get('buy_price', 0):,.0f}원")
            print(f"       현재가: {data.get('current_price', 0):,.0f}원")
            print(f"       수량: {data.get('quantity', 0)}주")
            print(f"       수익: {data.get('profit_amount', 0):+,.0f}원 ({data.get('profit_rate', 0):+.2f}%)")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

def test_web_access():
    """웹페이지 접근 테스트"""
    print(f"\n🌐 웹페이지 접근 테스트")
    print("=" * 50)

    try:
        response = requests.get('http://localhost:8080', timeout=5)
        if response.status_code == 200:
            print("   ✅ 웹페이지 접근 성공")
            print(f"   ✅ 응답 크기: {len(response.content)} bytes")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 연결 실패: {e}")

if __name__ == "__main__":
    test_firebase_data()
    test_web_access()
    print(f"\n✨ 테스트 완료 - {datetime.now().strftime('%H:%M:%S')}")