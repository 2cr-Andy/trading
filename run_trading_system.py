#!/usr/bin/env python3
"""통합 트레이딩 시스템 실행 스크립트 - 토큰 재사용 버전"""

import os
import sys
import time
import json
import signal
import subprocess
from datetime import datetime, timedelta
import pytz

def kill_existing_processes():
    """기존 프로세스 종료"""
    processes_to_kill = [
        "kis_bot.py",
        "integrated_trading_bot.py",
        "realtime_portfolio_updater.py",
        "update_portfolio_prices.py"
    ]

    for process in processes_to_kill:
        try:
            subprocess.run(f"pkill -f {process}", shell=True, capture_output=True)
        except:
            pass

    print("✅ 기존 프로세스 종료 완료")
    time.sleep(2)

def check_and_reuse_token():
    """기존 토큰 확인 및 재사용"""
    token_file = 'kis_token.json'

    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)

            # 토큰 발급 시간 확인
            if 'timestamp' in token_data:
                token_time = datetime.fromisoformat(token_data['timestamp'])
                kst = pytz.timezone('Asia/Seoul')
                now = datetime.now(kst)

                # 토큰이 24시간 이내면 재사용
                if now - token_time < timedelta(hours=24):
                    print(f"✅ 기존 토큰 재사용 (발급: {token_time.strftime('%Y-%m-%d %H:%M:%S')})")
                    return True
        except:
            pass

    print("⚠️ 유효한 토큰이 없습니다. 새로 발급이 필요합니다.")
    return False

def run_integrated_bot():
    """통합 봇 실행"""
    print("\n🚀 통합 트레이딩 봇 실행 중...")

    # 토큰 확인
    if not check_and_reuse_token():
        print("❌ 토큰이 없습니다. get_saved_token.py를 먼저 실행하세요.")
        return

    try:
        # 통합 봇만 실행
        subprocess.run([
            sys.executable,
            "integrated_trading_bot.py"
        ])
    except KeyboardInterrupt:
        print("\n🛑 봇 종료")
    except Exception as e:
        print(f"❌ 실행 오류: {e}")

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("🤖 KIS 통합 트레이딩 시스템")
    print("=" * 50)

    # 1. 기존 프로세스 정리
    kill_existing_processes()

    # 2. 통합 봇 실행
    run_integrated_bot()

if __name__ == "__main__":
    main()