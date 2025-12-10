#!/usr/bin/env python3
"""계좌 정보 수동 업데이트"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def update_account_manual():
    """계좌 정보 수동 업데이트"""
    print("🔧 계좌 정보 수동 업데이트")

    # 실제 값으로 업데이트 - 스크린샷에 보인 값들을 참고
    account_data = {
        'totalAssets': 10050000.0,  # 실제 총자산
        'totalCash': 200000.0,      # 실제 예수금
        'todayPnL': 50000.0,        # 오늘 손익
        'todayPnLPercent': 0.5,     # 오늘 손익률
        'timestamp': firestore.SERVER_TIMESTAMP,
        'lastSync': datetime.now().isoformat()
    }

    db.collection('account').document('summary').set(account_data)
    print(f"✅ 계좌 정보 업데이트 완료")
    print(f"   - 총자산: {account_data['totalAssets']:,.0f}원")
    print(f"   - 예수금: {account_data['totalCash']:,.0f}원")
    print(f"   - 오늘손익: {account_data['todayPnL']:+,.0f}원")

def update_portfolio_manual():
    """포트폴리오 수동 업데이트 - 보유수량 조정"""
    print("\n🔧 포트폴리오 수동 업데이트")

    # 실제 보유 종목 데이터로 업데이트
    portfolio_updates = {
        '090710': {  # 휴림로봇
            'quantity': 10,  # 실제 보유수량으로 변경
            'buy_price': 5740.0,
            'current_price': 5780.0,
            'name': '휴림로봇',
            'total_value': 57800.0,  # 10주 * 5780원
            'profit_amount': 400.0,   # (5780-5740) * 10
            'profit_rate': 0.70,      # (400/57400) * 100
            'status': 'holding',
            'last_updated': firestore.SERVER_TIMESTAMP
        },
        '220260': {  # 켐트로스
            'quantity': 5,   # 실제 보유수량으로 변경
            'buy_price': 6120.0,
            'current_price': 6220.0,
            'name': '켐트로스',
            'total_value': 31100.0,  # 5주 * 6220원
            'profit_amount': 500.0,   # (6220-6120) * 5
            'profit_rate': 1.63,      # (500/30600) * 100
            'status': 'holding',
            'last_updated': firestore.SERVER_TIMESTAMP
        },
        '317830': {  # 에스피시스템스
            'quantity': 2,   # 실제 보유수량으로 변경
            'buy_price': 13510.0,
            'current_price': 13750.0,
            'name': '에스피시스템스',
            'total_value': 27500.0,  # 2주 * 13750원
            'profit_amount': 480.0,   # (13750-13510) * 2
            'profit_rate': 1.78,      # (480/27020) * 100
            'status': 'holding',
            'last_updated': firestore.SERVER_TIMESTAMP
        }
    }

    for code, data in portfolio_updates.items():
        db.collection('portfolio').document(code).update(data)
        print(f"✅ {data['name']}({code}): {data['quantity']}주, "
              f"수익 {data['profit_amount']:+,.0f}원 ({data['profit_rate']:+.2f}%)")

if __name__ == "__main__":
    update_account_manual()
    update_portfolio_manual()
    print(f"\n✨ 수동 업데이트 완료 - {datetime.now().strftime('%H:%M:%S')}")