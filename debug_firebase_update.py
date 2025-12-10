#!/usr/bin/env python3
"""Firebase 업데이트 디버깅"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def debug_firebase_update():
    print("🔍 Firebase 업데이트 디버깅...")

    # 현재 데이터 읽기
    doc = db.collection('market_scan').document('latest').get()
    if not doc.exists:
        print("❌ 감시 종목 데이터가 없습니다.")
        return

    data = doc.to_dict()
    stocks = data.get('stocks', [])

    print(f"📊 현재 종목 수: {len(stocks)}")

    if len(stocks) > 0:
        first_stock = stocks[0]
        print(f"첫 번째 종목 현재 상태:")
        print(f"  - code: {first_stock.get('code')}")
        print(f"  - change_rate: {first_stock.get('change_rate')}")
        print(f"  - volume: {first_stock.get('volume')}")

        # 테스트 업데이트
        print("\n🔄 테스트 업데이트 실행...")
        first_stock['change_rate'] = 999.99  # 테스트 값
        first_stock['volume'] = 999999        # 테스트 값
        first_stock['test_timestamp'] = firestore.SERVER_TIMESTAMP

        # Firebase 업데이트
        try:
            db.collection('market_scan').document('latest').update({
                'stocks': stocks,
                'debug_updated': firestore.SERVER_TIMESTAMP
            })
            print("✅ Firebase 업데이트 성공")

            # 업데이트 확인
            updated_doc = db.collection('market_scan').document('latest').get()
            updated_data = updated_doc.to_dict()
            updated_first = updated_data['stocks'][0]
            print(f"업데이트 후 첫 번째 종목:")
            print(f"  - change_rate: {updated_first.get('change_rate')}")
            print(f"  - volume: {updated_first.get('volume')}")

        except Exception as e:
            print(f"❌ Firebase 업데이트 실패: {e}")

if __name__ == "__main__":
    debug_firebase_update()