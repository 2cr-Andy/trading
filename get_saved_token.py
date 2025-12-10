#!/usr/bin/env python3
"""저장된 토큰 재사용 또는 필요시 새로 발급"""

import json
import os
import time
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = "kis_token.json"
LAST_REQUEST_FILE = ".last_token_request"

def can_request_new_token():
    """새 토큰 요청 가능 여부 확인 (1분 제한)"""
    if os.path.exists(LAST_REQUEST_FILE):
        with open(LAST_REQUEST_FILE, 'r') as f:
            last_request = float(f.read())
            if time.time() - last_request < 60:
                return False, int(60 - (time.time() - last_request))
    return True, 0

def save_last_request_time():
    """마지막 토큰 요청 시간 저장"""
    with open(LAST_REQUEST_FILE, 'w') as f:
        f.write(str(time.time()))

def get_or_create_token():
    """저장된 토큰 사용 또는 새로 발급"""

    # 1. 기존 토큰 파일 확인
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)

            token = token_data.get('token')
            expires_at = token_data.get('expires_at', 0)

            # 토큰 유효성 확인 (만료 1시간 전까지 사용)
            if token and time.time() < expires_at - 3600:
                remaining_hours = (expires_at - time.time()) / 3600
                print(f"✅ 기존 토큰 사용 (남은 시간: {remaining_hours:.1f}시간)")
                return token
            else:
                print("⏰ 토큰 만료 임박 또는 만료됨")

        except Exception as e:
            print(f"⚠️ 토큰 파일 읽기 오류: {e}")

    # 2. 새 토큰 발급 필요
    can_request, wait_time = can_request_new_token()

    if not can_request:
        print(f"⏳ 토큰 요청 제한: {wait_time}초 후 재시도 가능")
        return None

    # 3. 새 토큰 발급
    print("🔄 새 토큰 발급 요청...")

    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    data = {
        "grant_type": "client_credentials",
        "appkey": os.getenv('KIS_APP_KEY'),
        "appsecret": os.getenv('KIS_APP_SECRET')
    }

    try:
        save_last_request_time()  # 요청 시간 저장
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            token = result.get('access_token')
            expires_in = int(result.get('expires_in', 86400))  # 기본 24시간

            if token:
                # 토큰 저장
                token_data = {
                    'token': token,
                    'expires_at': time.time() + expires_in,
                    'created_at': datetime.now().isoformat()
                }

                with open(TOKEN_FILE, 'w') as f:
                    json.dump(token_data, f, indent=2)

                print(f"✅ 새 토큰 발급 완료 (유효기간: {expires_in/3600:.1f}시간)")
                return token
        else:
            print(f"❌ 토큰 발급 실패: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ 토큰 발급 오류: {e}")

    return None

def main():
    """메인 실행"""
    token = get_or_create_token()

    if token:
        print(f"\n📌 토큰: {token[:20]}...")
        print("✅ 토큰을 다른 스크립트에서 재사용할 수 있습니다.")
    else:
        print("\n❌ 토큰 획득 실패")
        print("💡 잠시 후 다시 시도하거나 기존 토큰을 확인하세요.")

if __name__ == "__main__":
    main()