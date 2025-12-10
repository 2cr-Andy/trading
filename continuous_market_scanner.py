#!/usr/bin/env python3
"""지속적인 시장 스캔 및 업데이트 - 매수/매도 조건 실시간 모니터링"""

import schedule
import time
from datetime import datetime
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

class ContinuousMarketScanner:
    def __init__(self):
        self.last_token_request = 0
        self.update_count = 0

    def check_market_hours(self):
        """장 시간 확인 (09:00 ~ 15:30)"""
        now = datetime.now()
        weekday = now.weekday()

        # 주말 제외
        if weekday >= 5:
            return False

        # 장 시간 확인
        current_time = now.strftime('%H%M')
        if '0900' <= current_time <= '1530':
            return True

        return False

    def get_token(self):
        """토큰 발급 (1분 제한 체크)"""
        current_time = time.time()

        # 1분 제한 체크
        if current_time - self.last_token_request < 60:
            print(f"⏳ 토큰 요청 대기 ({60 - (current_time - self.last_token_request):.0f}초)")
            return False

        try:
            result = subprocess.run(
                ['python3', 'get_saved_token.py'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            if "✅" in result.stdout:
                self.last_token_request = current_time
                print("✅ 토큰 획득/재사용 성공")
                return True
            else:
                print("❌ 토큰 획득 실패")
                return False

        except Exception as e:
            print(f"❌ 토큰 획득 오류: {e}")
            return False

    def run_market_scan(self):
        """시장 스캔 실행 (새로운 매수 신호 탐색)"""
        if not self.check_market_hours():
            print(f"[{datetime.now().strftime('%H:%M')}] 🌙 장시간 외")
            return

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 시장 스캔 시작...")

        try:
            # market_scanner.py 실행 (새로운 종목 탐색)
            result = subprocess.run(
                ['python3', 'market_scanner.py'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            if result.returncode == 0:
                # 매수 신호 카운트
                buy_signals = result.stdout.count('🔴 매수 신호')
                print(f"✅ 시장 스캔 완료 (매수 신호: {buy_signals}개)")
            else:
                print("❌ 시장 스캔 실패")

        except subprocess.TimeoutExpired:
            print("⏱️ 시장 스캔 타임아웃")
        except Exception as e:
            print(f"❌ 시장 스캔 오류: {e}")

    def update_realtime_data(self):
        """실시간 데이터 업데이트 (기존 종목 가격/지표 업데이트)"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 실시간 데이터 업데이트...")

        try:
            # realtime_market_update.py 실행
            result = subprocess.run(
                ['python3', 'realtime_market_update.py'],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            if result.returncode == 0:
                self.update_count += 1
                print(f"✅ 업데이트 완료 (총 {self.update_count}회)")
            else:
                print("❌ 업데이트 실패")

        except subprocess.TimeoutExpired:
            print("⏱️ 업데이트 타임아웃")
        except Exception as e:
            print(f"❌ 업데이트 오류: {e}")

    def sync_firebase(self):
        """Firebase 동기화"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Firebase 동기화...")

        try:
            result = subprocess.run(
                ['python3', 'sync_firebase_data.py'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            if result.returncode == 0:
                print("✅ 동기화 완료")
            else:
                print("❌ 동기화 실패")

        except Exception as e:
            print(f"❌ 동기화 오류: {e}")

    def start_continuous_scan(self):
        """지속적인 스캔 시작"""
        print("🚀 지속적인 시장 스캔 시작")
        print("=" * 60)
        print("📋 스케줄:")
        print("  - 매 5분: 새로운 매수 신호 탐색 (market_scanner)")
        print("  - 매 2분: 기존 종목 실시간 업데이트")
        print("  - 매 1분: Firebase 동기화")
        print("=" * 60)

        # 초기 토큰 획득
        if not self.get_token():
            print("⚠️ 초기 토큰 획득 실패. 1분 후 재시도...")
            time.sleep(60)
            self.get_token()

        # 초기 실행
        self.run_market_scan()
        self.update_realtime_data()
        self.sync_firebase()

        # 스케줄 설정
        schedule.every(5).minutes.do(self.run_market_scan)  # 새로운 종목 탐색
        schedule.every(2).minutes.do(self.update_realtime_data)  # 실시간 업데이트
        schedule.every(1).minutes.do(self.sync_firebase)  # Firebase 동기화

        # 토큰 갱신 (1시간마다)
        schedule.every(1).hours.do(self.get_token)

        print("\n⏰ 스케줄러 실행 중... (Ctrl+C로 종료)")
        print("=" * 60)

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n👋 시장 스캔 종료")
            print(f"📊 총 업데이트 횟수: {self.update_count}회")

def main():
    scanner = ContinuousMarketScanner()
    scanner.start_continuous_scan()

if __name__ == "__main__":
    main()