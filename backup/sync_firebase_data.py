#!/usr/bin/env python3
"""Firebase 데이터 동기화 및 웹 대시보드 연동 수정"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import json

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def sync_portfolio_data():
    """포트폴리오 데이터를 정확한 필드명으로 동기화"""
    print("📊 포트폴리오 데이터 동기화 중...")

    # 포트폴리오 컬렉션 가져오기
    portfolio_docs = db.collection('portfolio').stream()

    for doc in portfolio_docs:
        data = doc.to_dict()
        stock_code = doc.id

        # 필수 필드 확인 및 수정
        updated_data = {}

        # 현재가가 0이면 buy_price 사용
        if data.get('current_price', 0) == 0 and data.get('buy_price', 0) > 0:
            updated_data['current_price'] = data['buy_price']

        # profit_rate 계산
        buy_price = data.get('buy_price', 0)
        current_price = data.get('current_price', buy_price)
        if buy_price > 0:
            profit_rate = ((current_price - buy_price) / buy_price) * 100
            updated_data['profit_rate'] = round(profit_rate, 2)

        # profit_amount 계산
        quantity = data.get('quantity', 0)
        if quantity > 0:
            profit_amount = (current_price - buy_price) * quantity
            updated_data['profit_amount'] = profit_amount
            updated_data['total_value'] = current_price * quantity

        # 필수 필드 기본값 설정
        if 'volume' not in data:
            updated_data['volume'] = 0
        if 'change_rate' not in data:
            updated_data['change_rate'] = 0
        if 'change_price' not in data:
            updated_data['change_price'] = 0

        # 업데이트가 필요한 경우에만 실행
        if updated_data:
            db.collection('portfolio').document(stock_code).update(updated_data)
            print(f"✅ {stock_code} 포트폴리오 데이터 수정됨")

def sync_watchlist_data():
    """감시 종목 데이터 동기화"""
    print("📊 감시 종목 데이터 동기화 중...")

    # market_scan/latest 문서 가져오기
    doc = db.collection('market_scan').document('latest').get()

    if doc.exists:
        data = doc.to_dict()
        stocks = data.get('stocks', [])

        # 각 종목의 필수 필드 확인
        for i, stock in enumerate(stocks):
            updated = False

            # 필수 필드 기본값 설정
            if 'current_price' not in stock or stock['current_price'] == 0:
                stock['current_price'] = 0
                updated = True

            if 'volume' not in stock:
                stock['volume'] = 0
                updated = True

            if 'change_rate' not in stock:
                stock['change_rate'] = 0
                updated = True

            if 'rsi' not in stock:
                stock['rsi'] = 50
                updated = True

            if 'mfi' not in stock:
                stock['mfi'] = 50
                updated = True

            if updated:
                print(f"✅ {stock.get('code')} 감시 종목 데이터 수정됨")

        # 전체 업데이트
        db.collection('market_scan').document('latest').update({
            'stocks': stocks,
            'last_updated': firestore.SERVER_TIMESTAMP
        })

def update_account_summary():
    """계좌 요약 정보 업데이트"""
    print("💰 계좌 요약 정보 업데이트 중...")

    # 포트폴리오 전체 가치 계산
    portfolio_docs = db.collection('portfolio').stream()
    total_value = 0
    total_profit = 0

    for doc in portfolio_docs:
        data = doc.to_dict()
        total_value += data.get('total_value', 0)
        total_profit += data.get('profit_amount', 0)

    # 기본 현금 잔액 (실제 값이 없으면 천만원으로 가정)
    cash_balance = 10000000 - total_value  # 초기 자금에서 투자금 차감

    # 계좌 요약 업데이트
    account_data = {
        'totalAssets': total_value + cash_balance,
        'totalCash': cash_balance,
        'todayPnL': total_profit,
        'todayPnLPercent': (total_profit / 10000000) * 100 if total_profit != 0 else 0,
        'lastUpdated': firestore.SERVER_TIMESTAMP
    }

    db.collection('account').document('summary').set(account_data, merge=True)
    print(f"✅ 계좌 요약: 총자산 {account_data['totalAssets']:,.0f}원, 수익 {total_profit:+,.0f}원")

def update_bot_status():
    """봇 상태 업데이트"""
    print("🤖 봇 상태 업데이트 중...")

    bot_status = {
        'running': True,
        'lastHeartbeat': firestore.SERVER_TIMESTAMP,
        'message': 'Firebase 데이터 동기화 중'
    }

    db.collection('bot_status').document('main').set(bot_status, merge=True)
    print("✅ 봇 상태 업데이트 완료")

def main():
    """메인 실행 함수"""
    print("🔄 Firebase 데이터 동기화 시작...")
    print("=" * 50)

    try:
        # 1. 포트폴리오 데이터 동기화
        sync_portfolio_data()
        print()

        # 2. 감시 종목 데이터 동기화
        sync_watchlist_data()
        print()

        # 3. 계좌 요약 정보 업데이트
        update_account_summary()
        print()

        # 4. 봇 상태 업데이트
        update_bot_status()
        print()

        print("=" * 50)
        print("✅ 모든 데이터 동기화 완료!")
        print("🌐 웹 대시보드: http://localhost:8080")

    except Exception as e:
        print(f"❌ 동기화 중 오류 발생: {e}")

if __name__ == "__main__":
    main()