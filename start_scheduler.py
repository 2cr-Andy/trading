#!/usr/bin/env python3
"""스케줄러 기반 자동 트레이딩 시스템"""

import os
import time
import schedule
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

def update_portfolio_prices():
    """포트폴리오 가격 업데이트"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 포트폴리오 가격 업데이트...")
    os.system("python3 realtime_portfolio_updater.py > /dev/null 2>&1 &")

def scan_market():
    """시장 스캔 및 감시종목 업데이트"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 시장 스캔 시작...")
    os.system("python3 market_scanner.py > /dev/null 2>&1 &")

def check_trading_signals():
    """매매 신호 체크"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 매매 신호 체크...")
    # 간단한 체크 로직만
    pass

def main():
    print("=" * 50)
    print("⏰ KIS 자동 스케줄러 시작")
    print("=" * 50)

    # 스케줄 설정
    schedule.every(30).seconds.do(update_portfolio_prices)  # 30초마다 가격 업데이트
    schedule.every(5).minutes.do(scan_market)  # 5분마다 시장 스캔
    schedule.every(1).minutes.do(check_trading_signals)  # 1분마다 매매 신호 체크

    print("📅 스케줄 설정 완료:")
    print("  - 포트폴리오 업데이트: 30초마다")
    print("  - 시장 스캔: 5분마다")
    print("  - 매매 신호: 1분마다")
    print("\n실행 중... (Ctrl+C로 종료)")

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 스케줄러 종료")
            break

if __name__ == "__main__":
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)

    # 장시간 체크
    if now.weekday() >= 5:  # 주말
        print("⚠️ 주말에는 거래가 없습니다.")
    elif now.hour < 9 or now.hour >= 16:  # 장시간 외
        print("⚠️ 현재는 장시간이 아닙니다. (09:00-15:30)")

    main()