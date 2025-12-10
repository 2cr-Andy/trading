#!/usr/bin/env python3
"""Firebase 실시간 업데이트 테스트"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import time
from datetime import datetime

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

print("🔄 Firebase 실시간 업데이트 테스트")
print("=" * 50)

# 1. 현재 데이터 확인
doc = db.collection('market_scan').document('latest').get()
if doc.exists:
    data = doc.to_dict()
    stocks = data.get('stocks', [])

    print(f"현재 종목 수: {len(stocks)}")
    if stocks:
        first = stocks[0]
        print(f"첫 번째 종목:")
        print(f"  - 코드: {first.get('code')}")
        print(f"  - 이름: {first.get('name')}")
        print(f"  - 현재가: {first.get('current_price')}")
        print(f"  - RSI: {first.get('rsi')}")
        print(f"  - MFI: {first.get('mfi')}")
        print(f"  - 거래량: {first.get('volume')}")

# 2. 테스트 업데이트
print("\n📝 테스트 업데이트 시작...")
test_timestamp = datetime.now().strftime('%H:%M:%S')

# 첫 번째 종목 데이터 수정
if stocks:
    stocks[0]['test_update'] = f"테스트 {test_timestamp}"
    stocks[0]['current_price'] = 999999  # 테스트 가격

    # Firebase 업데이트
    db.collection('market_scan').document('latest').update({
        'stocks': stocks,
        'test_timestamp': test_timestamp,
        'last_updated': firestore.SERVER_TIMESTAMP
    })

    print(f"✅ 업데이트 완료: {test_timestamp}")
    print("⚠️ 웹 대시보드를 확인하세요:")
    print("  - 첫 번째 종목의 현재가가 999,999원으로 변경되어야 함")
    print("  - 실시간으로 자동 업데이트되어야 함")

    # 10초 후 원상복구
    print("\n⏰ 10초 후 원상복구...")
    time.sleep(10)

    # 원래 가격으로 복구
    stocks[0]['current_price'] = first.get('current_price', 0)
    if 'test_update' in stocks[0]:
        del stocks[0]['test_update']

    db.collection('market_scan').document('latest').update({
        'stocks': stocks,
        'last_updated': firestore.SERVER_TIMESTAMP
    })

    print("✅ 원상복구 완료")
else:
    print("❌ 종목 데이터가 없습니다")