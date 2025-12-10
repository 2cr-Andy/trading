#!/usr/bin/env python3
"""자동으로 데이터를 업데이트하고 웹 대시보드와 동기화"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import time
import schedule
from datetime import datetime
import subprocess
import sys

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def run_sync_script():
    """Firebase 데이터 동기화 스크립트 실행"""
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 데이터 동기화 시작...")
        result = subprocess.run(
            ['python3', 'sync_firebase_data.py'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 동기화 완료")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 동기화 실패: {result.stderr}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 동기화 오류: {e}")

def update_heartbeat():
    """봇 상태 하트비트 업데이트"""
    try:
        db.collection('bot_status').document('main').update({
            'lastHeartbeat': firestore.SERVER_TIMESTAMP,
            'running': True
        })
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 💓 하트비트 업데이트")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 하트비트 오류: {e}")

def check_and_update_prices():
    """토큰이 있으면 가격 업데이트 시도"""
    try:
        # 토큰 파일 확인
        if os.path.exists('kis_token.json'):
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 💰 가격 업데이트 시도...")
            result = subprocess.run(
                ['python3', 'fix_realtime_data.py'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if "액세스 토큰이 없습니다" in result.stdout:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ 토큰 재발급 필요")
                # 토큰 재발급 시도
                subprocess.run(
                    ['python3', 'get_token_manual.py'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            elif result.returncode == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 가격 업데이트 완료")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ 토큰 파일 없음")
    except subprocess.TimeoutExpired:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️ 가격 업데이트 타임아웃")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 가격 업데이트 오류: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 자동 데이터 업데이트 시작")
    print("=" * 50)
    print("📋 스케줄:")
    print("  - 매 30초: 하트비트 업데이트")
    print("  - 매 1분: Firebase 데이터 동기화")
    print("  - 매 5분: 실시간 가격 업데이트")
    print("=" * 50)

    # 초기 실행
    run_sync_script()
    update_heartbeat()

    # 스케줄 설정
    schedule.every(30).seconds.do(update_heartbeat)
    schedule.every(1).minutes.do(run_sync_script)
    schedule.every(5).minutes.do(check_and_update_prices)

    print("\n⏰ 스케줄러 실행 중... (Ctrl+C로 종료)")

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 자동 업데이트 종료")
        # 종료 시 봇 상태 업데이트
        db.collection('bot_status').document('main').update({
            'running': False,
            'message': '자동 업데이트 종료'
        })

if __name__ == "__main__":
    main()