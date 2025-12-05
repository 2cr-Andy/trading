#!/usr/bin/env python3
"""
수정된 거래량 순위 API 테스트
"""

import sys
import os
import time
from market_scanner import MarketScanner
from dotenv import load_dotenv

load_dotenv()

def test_volume_api():
    print("=" * 60)
    print("수정된 거래량 순위 API 테스트")
    print("=" * 60)

    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")

    scanner = MarketScanner(app_key, app_secret)

    print(f"\n📋 환경 설정:")
    print(f"KIS_ENVIRONMENT: {os.getenv('KIS_ENVIRONMENT')}")
    print(f"Base URL: {scanner.base_url}")

    # 1분 대기 후 토큰 발급 시도 (이전 시도로부터 시간이 지났을 가능성)
    print(f"\n⏳ 토큰 발급 제한을 위해 잠시 대기...")
    time.sleep(5)

    print(f"\n1️⃣ 수정된 파라미터로 거래량 순위 조회")
    volume_stocks = scanner.get_volume_rank()

    print(f"\n📊 결과:")
    print(f"- 발견된 종목 수: {len(volume_stocks)}")

    if len(volume_stocks) == 0:
        print("⚠️ 여전히 빈 결과")

        print(f"\n2️⃣ 비교를 위해 등락률 순위 조회 (참고용)")
        time.sleep(1)
        price_stocks = scanner.get_price_change_rank()
        print(f"- 등락률 순위 결과: {len(price_stocks)}개")

        if len(price_stocks) > 0:
            print("✅ 등락률 API는 작동 중 - 거래량 API 파라미터 문제일 가능성")
        else:
            print("⚠️ 등락률 API도 빈 결과 - 시스템 전반 문제일 가능성")

    else:
        print("✅ 성공! 거래량 순위 조회 완료")
        for i, code in enumerate(volume_stocks[:5], 1):
            print(f"  {i}. {code}")

if __name__ == "__main__":
    test_volume_api()