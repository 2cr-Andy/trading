#!/usr/bin/env python3
"""통합 트레이딩 시스템 정리 및 실행"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
import pytz

def fix_token_file():
    """토큰 파일에 timestamp 추가"""
    with open('kis_token.json', 'r') as f:
        token_data = json.load(f)

    kst = pytz.timezone('Asia/Seoul')
    token_data['timestamp'] = datetime.now(kst).isoformat()

    with open('kis_token.json', 'w') as f:
        json.dump(token_data, f, indent=2)

    print("✅ 토큰 파일 수정 완료")

def check_portfolio():
    """포트폴리오에서 손실 종목 확인 및 매도"""
    import firebase_admin
    from firebase_admin import credentials, firestore

    # Firebase 초기화
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    # 포트폴리오 확인
    portfolio_docs = db.collection('portfolio').stream()
    sell_targets = []

    for doc in portfolio_docs:
        data = doc.to_dict()
        stock_code = doc.id
        profit_rate = data.get('profit_rate', 0)

        # -3% 이하 손실 종목 찾기
        if profit_rate <= -3:
            sell_targets.append({
                'code': stock_code,
                'name': data.get('name', stock_code),
                'profit_rate': profit_rate,
                'quantity': data.get('quantity', 0)
            })
            print(f"🔴 매도 대상: {data.get('name', stock_code)} ({profit_rate:.2f}%)")

    return sell_targets

def main():
    print("=" * 50)
    print("🔧 KIS 트레이딩 시스템 정리 및 실행")
    print("=" * 50)

    # 1. 모든 기존 프로세스 종료
    print("\n1️⃣ 기존 프로세스 정리 중...")
    subprocess.run("pkill -f 'python.*kis_bot'", shell=True)
    subprocess.run("pkill -f 'python.*integrated_trading'", shell=True)
    subprocess.run("pkill -f 'python.*realtime_portfolio'", shell=True)
    subprocess.run("pkill -f 'python.*update_portfolio'", shell=True)
    time.sleep(2)
    print("✅ 기존 프로세스 정리 완료")

    # 2. 토큰 파일 수정
    print("\n2️⃣ 토큰 파일 수정...")
    fix_token_file()

    # 3. 손실 종목 확인
    print("\n3️⃣ 포트폴리오 손실 종목 확인...")
    sell_targets = check_portfolio()

    if sell_targets:
        print(f"\n⚠️ 총 {len(sell_targets)}개 종목이 손절 기준(-3%)을 충족합니다.")
        print("integrated_trading_bot.py를 실행하면 자동으로 매도됩니다.")

    # 4. 통합 봇 실행
    print("\n4️⃣ 통합 트레이딩 봇 시작...")
    print("-" * 50)

    try:
        subprocess.run([sys.executable, "integrated_trading_bot.py"])
    except KeyboardInterrupt:
        print("\n🛑 봇 종료")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()