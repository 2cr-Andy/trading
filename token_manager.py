"""
KIS API 토큰 관리자 - 파일 기반 토큰 재사용
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Optional, Dict

class TokenManager:
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://openapivts.koreainvestment.com:29443"
        self.token_file = "kis_token.json"
        self.token_lock_file = "kis_token.lock"

    def _read_token_from_file(self) -> Optional[Dict]:
        """파일에서 토큰 정보 읽기"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None

    def _write_token_to_file(self, token: str, expires_at: float):
        """파일에 토큰 정보 저장"""
        data = {
            "token": token,
            "expires_at": expires_at,
            "created_at": time.time()
        }
        with open(self.token_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _is_token_valid(self, token_data: Dict) -> bool:
        """토큰 유효성 검증"""
        if not token_data:
            return False

        expires_at = token_data.get("expires_at", 0)
        current_time = time.time()

        # 토큰이 만료되기 1시간 전에 갱신
        return current_time < (expires_at - 3600)

    def _request_new_token(self) -> Optional[str]:
        """새 토큰 발급 요청"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))

            if response.status_code == 200:
                token_data = response.json()
                token = token_data.get("access_token")

                if token:
                    # 23시간 유효
                    expires_at = time.time() + (23 * 60 * 60)
                    self._write_token_to_file(token, expires_at)
                    print(f"✅ 새 토큰 발급 성공 (유효기간: 23시간)")
                    return token

            elif response.status_code == 403:
                error_data = response.json()
                if error_data.get("error_code") == "EGW00133":
                    print("⏳ 토큰 발급 1분 제한 - 기존 토큰 재사용 시도")
                    # 1분 제한에 걸렸을 때도 기존 토큰 반환
                    token_data = self._read_token_from_file()
                    if token_data:
                        return token_data.get("token")

            print(f"❌ 토큰 발급 실패: {response.text[:200]}")

        except Exception as e:
            print(f"❌ 토큰 발급 에러: {e}")

        return None

    def get_token(self) -> Optional[str]:
        """토큰 획득 (파일 캐시 우선 사용)"""

        # 1. 파일에서 토큰 읽기 시도
        token_data = self._read_token_from_file()

        # 2. 토큰이 유효하면 재사용
        if self._is_token_valid(token_data):
            created_time = datetime.fromtimestamp(token_data.get("created_at", 0))
            print(f"♻️ 기존 토큰 재사용 (생성시간: {created_time.strftime('%Y-%m-%d %H:%M:%S')})")
            return token_data.get("token")

        # 3. 토큰이 없거나 만료되었으면 새로 발급
        print("🔄 토큰 갱신 필요 - 새 토큰 발급 시도")
        new_token = self._request_new_token()

        # 4. 새 토큰 발급 실패 시 기존 토큰이라도 사용
        if not new_token and token_data:
            print("⚠️ 새 토큰 발급 실패 - 기존 토큰 재사용")
            return token_data.get("token")

        return new_token

    def clear_token(self):
        """토큰 파일 삭제"""
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
            print("🗑️ 토큰 파일 삭제됨")