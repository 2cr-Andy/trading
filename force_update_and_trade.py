#!/usr/bin/env python3
"""강제 업데이트 및 매매 실행"""

import os
import sys
import json
import time
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()
kst = pytz.timezone('Asia/Seoul')

def get_access_token():
    """토큰 가져오기"""
    try:
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            return token_data.get('token')
    except:
        return None

def execute_sell_orders():
    """손실 종목 즉시 매도"""
    print("\n📉 손실 종목 매도 실행")
    print("-" * 50)

    token = get_access_token()
    if not token:
        print("❌ 토큰이 없습니다")
        return

    account_no = os.getenv('KIS_ACCOUNT_NUMBER')
    if '-' not in account_no:
        account_no = f"{account_no}-01"

    # 매도 대상 종목
    sell_targets = [
        {'code': '220260', 'name': '켐트로스', 'profit_rate': -4.41},
        {'code': '317830', 'name': '에스피시스템스', 'profit_rate': -7.03}
    ]

    for target in sell_targets:
        print(f"\n🔴 {target['name']} 매도 시도 (손실률: {target['profit_rate']:.2f}%)")

        # Firebase에서 수량 확인
        doc = db.collection('portfolio').document(target['code']).get()
        if not doc.exists:
            print(f"  ⚠️ 포트폴리오에 없음")
            continue

        data = doc.to_dict()
        quantity = data.get('quantity', 0)

        if quantity <= 0:
            print(f"  ⚠️ 보유 수량 없음")
            continue

        # 매도 주문
        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "VTTC0801U"  # 모의투자 매도
        }

        body = {
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "PDNO": target['code'],
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('rt_cd') == '0':
                    print(f"  ✅ 매도 주문 성공: {quantity}주")
                    # Firebase 삭제
                    db.collection('portfolio').document(target['code']).delete()
                else:
                    print(f"  ❌ 매도 실패: {result.get('msg1')}")
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 매도 오류: {e}")

        time.sleep(1)

def update_watchlist():
    """감시 종목 강제 업데이트"""
    print("\n📊 감시 종목 업데이트")
    print("-" * 50)

    # 기존 감시 종목 전체 삭제
    watchlist_docs = db.collection('watchlist').stream()
    for doc in watchlist_docs:
        doc.reference.delete()
    print("✅ 기존 감시 종목 삭제 완료")

    # 새로운 감시 종목 (시장 변화 반영)
    new_watchlist = [
        {'code': '005930', 'name': '삼성전자'},
        {'code': '000660', 'name': 'SK하이닉스'},
        {'code': '035720', 'name': '카카오'},
        {'code': '035420', 'name': 'NAVER'},
        {'code': '051910', 'name': 'LG화학'}
    ]

    for stock in new_watchlist:
        db.collection('watchlist').document(stock['code']).set({
            'code': stock['code'],
            'name': stock['name'],
            'added_at': firestore.SERVER_TIMESTAMP,
            'status': 'active'
        })
        print(f"  ✅ {stock['name']} 추가")

def check_current_portfolio():
    """현재 포트폴리오 상태 확인"""
    print("\n📋 현재 포트폴리오 상태")
    print("-" * 50)

    portfolio_docs = db.collection('portfolio').stream()
    total = 0

    for doc in portfolio_docs:
        data = doc.to_dict()
        total += 1
        profit_rate = data.get('profit_rate', 0)
        status = "🟢" if profit_rate > 0 else "🔴"
        print(f"  {status} {data.get('name', doc.id)}: {profit_rate:+.2f}%")

    if total == 0:
        print("  ⚠️ 보유 종목 없음")

    return total

def restart_trading_bot():
    """트레이딩 봇 재시작"""
    print("\n🔄 트레이딩 봇 재시작")
    print("-" * 50)

    # 기존 프로세스 종료
    os.system("pkill -f 'python.*integrated_trading_bot'")
    time.sleep(2)

    print("✅ 기존 봇 종료 완료")
    print("📌 새로운 봇을 시작하려면 다음 명령어를 실행하세요:")
    print("   python3 integrated_trading_bot.py")

def main():
    print("=" * 50)
    print("🚨 강제 업데이트 및 매매 실행")
    print("=" * 50)

    # 1. 손실 종목 매도
    execute_sell_orders()

    # 2. 포트폴리오 확인
    portfolio_count = check_current_portfolio()

    # 3. 감시 종목 업데이트
    update_watchlist()

    # 4. 봇 재시작
    restart_trading_bot()

    print("\n" + "=" * 50)
    print("✅ 작업 완료!")
    print(f"📊 현재 보유 종목: {portfolio_count}개")
    print("🔍 감시 종목이 업데이트되었습니다")
    print("=" * 50)

if __name__ == "__main__":
    main()