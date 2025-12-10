#!/usr/bin/env python3
"""모든 종목명을 StockNameManager로 올바르게 업데이트"""

from stock_name_manager import StockNameManager
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import time

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()
manager = StockNameManager()

print("모든 종목명을 올바르게 업데이트 중...")

# 1. 포트폴리오 종목명 업데이트
print("\n=== 포트폴리오 업데이트 ===")
portfolio_docs = db.collection('portfolio').get()
for doc in portfolio_docs:
    stock_code = doc.id
    print(f"처리 중: {stock_code}")

    # StockNameManager로 올바른 종목명 가져오기
    correct_name = manager.get_stock_name(stock_code)

    if correct_name:
        db.collection('portfolio').document(stock_code).update({
            'name': correct_name
        })
        print(f"  ✅ {stock_code}: {correct_name}")
    else:
        print(f"  ❌ {stock_code}: 종목명 조회 실패")

    time.sleep(0.5)  # API 호출 제한

# 2. market_scan 종목명 업데이트
print("\n=== 감시목록 업데이트 ===")
scan_doc = db.collection('market_scan').document('latest').get()
if scan_doc.exists:
    data = scan_doc.to_dict()
    stocks = data.get('stocks', [])

    updated_stocks = []
    for stock in stocks:
        stock_code = stock.get('code')
        if stock_code:
            print(f"처리 중: {stock_code}")

            # StockNameManager로 올바른 종목명 가져오기
            correct_name = manager.get_stock_name(stock_code)

            if correct_name:
                stock['name'] = correct_name
                print(f"  ✅ {stock_code}: {correct_name}")
            else:
                print(f"  ❌ {stock_code}: 종목명 조회 실패 (코드 유지)")

            updated_stocks.append(stock)
            time.sleep(0.5)  # API 호출 제한

    # 업데이트된 데이터 저장
    db.collection('market_scan').document('latest').update({
        'stocks': updated_stocks
    })

print("\n✅ 모든 종목명 업데이트 완료!")