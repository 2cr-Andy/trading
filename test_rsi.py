#!/usr/bin/env python3
"""RSI 계산 테스트 스크립트"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# main.py의 클래스들 import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import KISApiClient, TechnicalAnalyzer, TradingEngine
from token_manager import TokenManager

load_dotenv()

def test_rsi_calculation():
    """RSI 계산 기능 테스트"""
    print("🔬 RSI 계산 테스트 시작")
    print("="*50)

    # 토큰 매니저 및 API 클라이언트 초기화
    app_key = os.getenv('KIS_APP_KEY')
    app_secret = os.getenv('KIS_APP_SECRET')
    account_no = os.getenv('KIS_ACCOUNT_NUMBER')
    if '-' not in account_no:
        account_no = f"{account_no}-01"

    token_manager = TokenManager(app_key, app_secret)
    api_client = KISApiClient(token_manager, account_no)
    analyzer = TechnicalAnalyzer()

    # 테스트할 종목 코드들
    test_stocks = [
        ('005930', '삼성전자'),
        ('000660', 'SK하이닉스'),
        ('035720', '카카오')
    ]

    print("\n📊 종목별 RSI 계산 결과:")
    print("-"*50)

    for code, name in test_stocks:
        print(f"\n🔍 {name} ({code}) 분석 중...")

        # 1. 현재가 조회
        price_data = api_client.get_stock_price(code)
        if price_data:
            print(f"  현재가: {price_data['current_price']:,.0f}원")
            print(f"  등락률: {price_data['change_rate']:+.2f}%")
            print(f"  거래량: {price_data['volume']:,}주")

        # 2. 일봉 데이터 조회
        df = api_client.get_daily_price_history(code, days=30)
        if df is not None:
            print(f"  일봉 데이터: {len(df)}개 (최근 30일)")

            # 3. RSI 계산
            rsi = analyzer.calculate_rsi(df)
            print(f"  📈 RSI: {rsi:.2f}")

            # RSI 해석
            if rsi < 30:
                print(f"     ⚡ 과매도 구간 (매수 신호)")
            elif rsi > 70:
                print(f"     🔥 과매수 구간 (매도 신호)")
            else:
                print(f"     ⚪ 중립 구간")

            # 4. MFI 계산
            mfi = analyzer.calculate_mfi(df)
            print(f"  💰 MFI: {mfi:.2f}")

            # 5. MACD 계산
            macd = analyzer.calculate_macd(df)
            print(f"  📉 MACD: {macd['macd']:.2f}")
            print(f"     Signal: {macd['signal']:.2f}")
            print(f"     Histogram: {macd['histogram']:.2f}")

            # 6. 볼린저 밴드 계산
            bb = analyzer.calculate_bollinger_bands(df)
            print(f"  📊 볼린저 밴드:")
            print(f"     상단: {bb['upper']:,.0f}원")
            print(f"     중간: {bb['middle']:,.0f}원")
            print(f"     하단: {bb['lower']:,.0f}원")

            # 현재가와 볼린저 밴드 비교
            if price_data:
                current = price_data['current_price']
                if current < bb['lower']:
                    print(f"     💡 현재가가 하단 밴드 아래 (과매도)")
                elif current > bb['upper']:
                    print(f"     ⚠️ 현재가가 상단 밴드 위 (과매수)")
        else:
            print(f"  ❌ 일봉 데이터 조회 실패")

    print("\n" + "="*50)
    print("✅ RSI 계산 테스트 완료!")
    print("\n💡 결론:")
    print("- RSI가 30 이하면 과매도 → 매수 고려")
    print("- RSI가 70 이상이면 과매수 → 매도 고려")
    print("- MFI는 거래량을 고려한 지표")
    print("- MACD는 추세 전환 신호 파악")
    print("- 볼린저 밴드는 변동성과 지지/저항 확인")

if __name__ == "__main__":
    test_rsi_calculation()