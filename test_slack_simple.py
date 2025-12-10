#!/usr/bin/env python3
"""
간단한 Slack 채널 테스트
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def test_channel_access():
    bot_token = os.getenv('SLACK_BOT_TOKEN')

    # 채널별 테스트 메시지
    test_channels = [
        '#kis-bot',          # 기본 채널
        '#kis-bot-trading',  # 매매 전용
        '#kis-bot-errors',   # 에러 전용
        '#kis-bot-summary',  # 요약 전용
        '#kis-bot-deploy'    # 배포 전용
    ]

    for channel in test_channels:
        print(f"\n📤 {channel} 채널 테스트 중...")

        payload = {
            "channel": channel,
            "text": f"🧪 채널 테스트: {channel}",
            "attachments": [{
                "color": "good",
                "text": "이 메시지가 올바른 채널에 도착했는지 확인해주세요."
            }]
        }

        headers = {
            'Authorization': f'Bearer {bot_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(
                'https://slack.com/api/chat.postMessage',
                data=json.dumps(payload),
                headers=headers,
                timeout=10
            )

            result = response.json()
            if result.get('ok'):
                print(f"✅ {channel} 전송 성공!")
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ {channel} 전송 실패: {error}")

        except Exception as e:
            print(f"❌ {channel} 요청 실패: {e}")

if __name__ == "__main__":
    print("🔍 Slack 채널 접근 테스트 시작...")
    test_channel_access()
    print("\n✅ 테스트 완료!")