"""토큰 수동 발급 및 저장"""

import os
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

app_key = os.getenv('KIS_APP_KEY')
app_secret = os.getenv('KIS_APP_SECRET')
base_url = "https://openapivts.koreainvestment.com:29443"

def get_and_save_token():
    """토큰 발급 및 파일 저장"""
    url = f"{base_url}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }

    print("토큰 발급 요청 중...")
    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        token_data = response.json()
        token = token_data.get("access_token")

        # 파일에 저장
        save_data = {
            "token": token,
            "expires_at": time.time() + (23 * 60 * 60),
            "created_at": time.time()
        }

        with open("kis_token.json", 'w') as f:
            json.dump(save_data, f, indent=2)

        print("✅ 토큰 파일 생성 완료: kis_token.json")
        print(f"토큰: {token[:20]}...")
        return True
    else:
        print(f"❌ 실패: {response.text}")
        return False

if __name__ == "__main__":
    success = get_and_save_token()
    if not success:
        print("\n30초 후 재시도...")
        time.sleep(30)
        get_and_save_token()