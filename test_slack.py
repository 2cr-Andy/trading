#!/usr/bin/env python3
"""
Slack 알림 테스트 스크립트
"""
import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# slack_notifier 임포트
from slack_notifier import SlackNotifier

def main():
    print("=" * 50)
    print("🧪 Slack 알림 테스트 시작")
    print("=" * 50)

    # Slack 알림 초기화
    notifier = SlackNotifier()

    # 각 채널별 테스트 메시지 발송
    test_cases = [
        ("봇 시작 알림", lambda: notifier.notify_bot_start()),
        ("봇 정지 알림", lambda: notifier.notify_bot_stop()),
        ("매매 성공", lambda: notifier.notify_trade_success(
            "BUY", "005930", 75000, 10, "테스트 매수"
        )),
        ("매매 신호", lambda: notifier.notify_trade_signal(
            "BUY", "005930", {"RSI": 30, "MACD": "Golden Cross", "Volume": "상승"}
        )),
        ("에러 알림", lambda: notifier.notify_error(
            "시스템 오류", "테스트 에러 메시지입니다", "005930"
        )),
        ("배포 성공", lambda: notifier.notify_deploy_success(
            "테스트 배포 커밋", "Test User"
        )),
        ("배포 실패", lambda: notifier.notify_deploy_failure(
            "SSH 연결 실패"
        )),
        ("포트폴리오 업데이트", lambda: notifier.notify_portfolio_update(
            10000000, 150000, 1.5
        )),
        ("시장 스캔 결과", lambda: notifier.notify_market_scan_result(
            5, 100, ["삼성전자", "SK하이닉스", "NAVER"]
        )),
        ("장 마감 알림", lambda: notifier.notify_market_closed()),
        ("시스템 알림", lambda: notifier.notify_system_alert(
            "WARNING", "메모리 사용량 80% 초과"
        ))
    ]

    print("\n📤 테스트 메시지 발송 중...")
    for test_name, test_func in test_cases:
        print(f"\n✉️  {test_name} 테스트...")
        try:
            result = test_func()
            if result:
                print(f"   ✅ 성공")
            else:
                print(f"   ⚠️  실패 (결과: {result})")
        except Exception as e:
            print(f"   ❌ 에러: {e}")

    print("\n" + "=" * 50)
    print("🏁 테스트 완료!")
    print("=" * 50)
    print("\n💡 Slack에서 다음 채널을 확인하세요:")
    print("   • #kis-trading (매매 알림)")
    print("   • #kis-errors (에러 알림)")
    print("   • #kis-summary (일일 리포트)")
    print("   • #kis-deploy (배포 알림)")

if __name__ == "__main__":
    main()