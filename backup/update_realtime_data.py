#!/usr/bin/env python3
"""실시간 데이터를 Firebase에 정확하게 업데이트"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
from market_scanner import MarketScanner
import time

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# MarketScanner 초기화
scanner = MarketScanner(
    app_key=os.getenv('KIS_APP_KEY'),
    app_secret=os.getenv('KIS_APP_SECRET')
)

def update_stock_with_realtime_data(stock_code):
    """개별 종목의 실시간 데이터 업데이트"""
    print(f"📊 {stock_code} 실시간 데이터 수집 중...")

    try:
        # 현재가 조회
        current_price_data = scanner.get_current_price(stock_code)
        if not current_price_data:
            print(f"❌ {stock_code}: 현재가 조회 실패")
            return None

        current_price = current_price_data['현재가']
        change_rate = current_price_data.get('등락률', 0)
        volume = current_price_data.get('거래량', 0)

        # 기술적 지표 계산
        indicators = scanner.calculate_technical_indicators(stock_code)
        if not indicators:
            print(f"❌ {stock_code}: 기술적 지표 계산 실패")
            return None

        rsi = indicators.get('rsi', 50)
        mfi = indicators.get('mfi', 50)

        # 종목명 가져오기 (이미 업데이트된 것 사용)
        doc = db.collection('market_scan').document('latest').get()
        stock_name = stock_code  # 기본값
        if doc.exists:
            data = doc.to_dict()
            stocks = data.get('stocks', [])
            for stock in stocks:
                if stock.get('code') == stock_code:
                    stock_name = stock.get('name', stock_code)
                    break

        # 실시간 데이터 구성
        updated_data = {
            'code': stock_code,
            'name': stock_name,
            'current_price': current_price,
            'change_rate': change_rate,
            'volume': volume,
            'rsi': rsi,
            'mfi': mfi,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'buy_signal': False,  # 일단 False로 설정
            'score': 0  # 기본 점수
        }

        print(f"✅ {stock_code} ({stock_name}): {current_price:,.0f}원, {change_rate:+.2f}%, RSI:{rsi:.1f}, MFI:{mfi:.1f}")
        return updated_data

    except Exception as e:
        print(f"❌ {stock_code} 데이터 수집 오류: {e}")
        return None

def update_all_realtime():
    """모든 감시 종목의 실시간 데이터 업데이트"""
    print("🔄 실시간 데이터 업데이트 시작...")

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
            updated_data = update_stock_with_realtime_data(stock_code)
            if updated_data:
                updated_stocks.append(updated_data)
            else:
                # 기존 데이터 유지
                updated_stocks.append(stock)

            time.sleep(0.2)  # API 제한 방지

    # Firebase에 업데이트
    db.collection('market_scan').document('latest').update({
        'stocks': updated_stocks,
        'last_updated': firestore.SERVER_TIMESTAMP
    })

    print(f"\n✅ {len(updated_stocks)}개 종목 실시간 데이터 업데이트 완료!")

if __name__ == "__main__":
    update_all_realtime()