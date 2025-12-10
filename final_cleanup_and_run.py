#!/usr/bin/env python3
"""최종 정리 및 실행"""

import os
import json
import time
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

def cleanup_loss_positions():
    """손실 포지션 정리"""
    print("🔴 손실 포지션 정리 중...")

    try:
        portfolio_docs = db.collection('portfolio').stream()
        removed_count = 0

        for doc in portfolio_docs:
            data = doc.to_dict()
            profit_rate = data.get('profit_rate', 0)

            if profit_rate <= -3:  # -3% 이하 손실
                print(f"  🗑️ {data.get('name', doc.id)} 제거 (손실: {profit_rate:.2f}%)")
                doc.reference.delete()
                removed_count += 1

        print(f"✅ {removed_count}개 손실 종목 정리 완료")

    except Exception as e:
        print(f"❌ 정리 실패: {e}")

def update_system_metadata():
    """시스템 메타데이터 업데이트"""
    try:
        # 시스템 상태
        db.collection('system').document('status').set({
            'last_update': firestore.SERVER_TIMESTAMP,
            'status': 'active',
            'version': '2.1',
            'update_mode': 'realtime',
            'features': ['auto_refresh', 'loss_cleanup', 'token_management']
        }, merge=True)

        # 감시 종목 메타데이터
        db.collection('system').document('watchlist_meta').set({
            'last_updated': firestore.SERVER_TIMESTAMP,
            'auto_refresh': True,
            'update_interval': 60  # 1분
        }, merge=True)

        print("✅ 시스템 메타데이터 업데이트 완료")

    except Exception as e:
        print(f"❌ 메타데이터 업데이트 실패: {e}")

def start_background_updater():
    """백그라운드 업데이터 시작"""
    print("🚀 백그라운드 업데이터 시작...")

    # 기존 업데이터 종료
    os.system("pkill -f 'enhanced_realtime_system' > /dev/null 2>&1")
    time.sleep(1)

    # 새로운 업데이터 시작
    os.system("source venv/bin/activate && python3 realtime_portfolio_updater.py > /dev/null 2>&1 &")

    print("✅ 백그라운드 업데이터 시작 완료")

def show_current_status():
    """현재 상태 표시"""
    print("\n" + "="*50)
    print("📊 현재 시스템 상태")
    print("="*50)

    # 포트폴리오 확인
    try:
        portfolio_docs = list(db.collection('portfolio').stream())
        print(f"💼 포트폴리오: {len(portfolio_docs)}개 종목")

        for doc in portfolio_docs:
            data = doc.to_dict()
            profit_rate = data.get('profit_rate', 0)
            status = "🟢" if profit_rate > 0 else "🔴"
            print(f"    {status} {data.get('name', doc.id)}: {profit_rate:+.2f}%")
    except:
        print("❌ 포트폴리오 조회 실패")

    # 감시 종목 확인
    try:
        watchlist_docs = list(db.collection('watchlist').stream())
        print(f"🔍 감시 종목: {len(watchlist_docs)}개")

        for doc in watchlist_docs:
            data = doc.to_dict()
            print(f"    📈 {data.get('name', doc.id)}")
    except:
        print("❌ 감시 종목 조회 실패")

    print("\n✅ 실시간 자동 갱신이 활성화되었습니다.")
    print("🌐 웹 페이지: http://localhost:8080")
    print("📱 Flutter 대시보드가 자동으로 데이터를 갱신합니다.")

def main():
    print("🔧 KIS 트레이딩 시스템 최종 정리")
    print("-" * 50)

    # 1. 손실 포지션 정리
    cleanup_loss_positions()

    # 2. 시스템 메타데이터 업데이트
    update_system_metadata()

    # 3. 백그라운드 업데이터 시작
    start_background_updater()

    # 4. 현재 상태 표시
    show_current_status()

if __name__ == "__main__":
    main()