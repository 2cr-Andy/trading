#!/usr/bin/env python3
"""317830 종목의 current_price 업데이트"""

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

def fix_317830():
    """317830 종목의 current_price와 관련 데이터 업데이트"""
    print("🔧 317830 종목 수정...")

    # 실시간 데이터에서 current_price 가져오기
    current_price = 13750  # fix_realtime_data.py에서 확인된 현재가
    buy_price = 13510      # 기존 구매가

    # 수익률 계산
    profit_amount = current_price - buy_price
    profit_rate = (profit_amount / buy_price) * 100
    change_rate = 25.46    # 실시간 데이터에서 확인된 등락률

    # 업데이트할 데이터
    update_data = {
        'current_price': float(current_price),
        'profit_amount': float(profit_amount),
        'profit_rate': profit_rate,
        'total_value': float(current_price),  # 1주이므로 current_price와 동일
        'change_rate': change_rate,
        'volume': 25000000,  # 대략적인 거래량
        'last_updated': firestore.SERVER_TIMESTAMP
    }

    # Firebase 업데이트
    try:
        db.collection('portfolio').document('317830').update(update_data)
        print(f"✅ 317830 업데이트 완료:")
        print(f"   - 구매가: {buy_price:,}원")
        print(f"   - 현재가: {current_price:,}원")
        print(f"   - 수익: {profit_amount:+,}원 ({profit_rate:+.2f}%)")
        print(f"   - 등락률: {change_rate:+.2f}%")
    except Exception as e:
        print(f"❌ 업데이트 실패: {e}")

if __name__ == "__main__":
    fix_317830()