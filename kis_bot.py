import os
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class KISBot:
    def __init__(self):
        """KIS 자동매매 봇 초기화"""
        # Firebase 초기화
        cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()

        # KIS API 설정
        self.app_key = os.getenv('KIS_APP_KEY')
        self.app_secret = os.getenv('KIS_APP_SECRET')
        self.account_number = os.getenv('KIS_ACCOUNT_NUMBER')

        # API URL 설정 (모의투자)
        self.base_url = "https://openapivts.koreainvestment.com:29443"
        self.access_token = None
        self.token_expires_at = 0

        # 봇 상태
        self.is_running = False

        print("KIS Bot 초기화 완료")
        print(f"계좌번호: {self.account_number}")
        print(f"Firebase 프로젝트: {os.getenv('FIREBASE_PROJECT_NAME')}")

    def get_access_token(self) -> str:
        """접속 토큰 발급 또는 갱신"""
        current_time = time.time()

        # 토큰이 유효한 경우 재사용
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("access_token")
            # 토큰 만료 시간 설정 (보통 24시간이지만 안전하게 23시간으로 설정)
            self.token_expires_at = current_time + (23 * 60 * 60)

            print("✅ 접속 토큰 발급 성공")
            return self.access_token

        except Exception as e:
            print(f"❌ 토큰 발급 실패: {e}")
            return None

    def get_account_balance(self) -> Dict:
        """계좌 잔고 조회"""
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "VTTC8908R",  # 모의투자 매수 가능 조회
            "custtype": "P"
        }

        params = {
            "CANO": self.account_number[:8],
            "ACNT_PRDT_CD": "01",
            "PDNO": "005930",  # 삼성전자 (필수 파라미터)
            "ORD_UNPR": "",
            "ORD_DVSN": "01",
            "CMA_EVLU_AMT_ICLD_YN": "N",
            "OVRS_ICLD_YN": "N"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") == "0":
                output = data.get("output", {})
                balance = {
                    "cash": float(output.get("ord_psbl_cash", 0)),
                    "total_assets": float(output.get("psbl_qty", 0)),
                    "timestamp": datetime.now()
                }

                print(f"💰 예수금: {balance['cash']:,.0f}원")
                return balance
            else:
                print(f"❌ 잔고 조회 실패: {data.get('msg1')}")
                return None

        except Exception as e:
            print(f"❌ 잔고 조회 오류: {e}")
            return None

    def get_stock_price(self, stock_code: str) -> Dict:
        """주식 현재가 조회"""
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") == "0":
                output = data.get("output", {})
                return {
                    "code": stock_code,
                    "name": output.get("hts_kor_isnm", ""),
                    "currentPrice": float(output.get("stck_prpr", 0)),
                    "changePercent": float(output.get("prdy_ctrt", 0)),
                    "volume": float(output.get("acml_vol", 0)),
                    "high": float(output.get("stck_hgpr", 0)),
                    "low": float(output.get("stck_lwpr", 0)),
                    "timestamp": datetime.now()
                }
            return None

        except Exception as e:
            print(f"❌ 시세 조회 오류 ({stock_code}): {e}")
            return None

    def update_watchlist(self):
        """감시 종목 리스트 업데이트"""
        # 예시 종목들 (실제로는 조건검색 API 사용)
        watchlist = ["005930", "000660", "035720", "051910", "035420"]  # 삼성전자, SK하이닉스, 카카오, LG화학, NAVER

        for stock_code in watchlist:
            price_data = self.get_stock_price(stock_code)
            if price_data:
                # RSI, MFI는 실제로는 일봉 데이터로 계산해야 함
                price_data["rsi"] = 45 + (float(stock_code[-2:]) % 30)  # 임시 값
                price_data["mfi"] = 40 + (float(stock_code[-2:]) % 40)  # 임시 값
                price_data["volumeChange"] = 100 + (float(stock_code[-2:]) % 500)  # 임시 값
                price_data["nearBuySignal"] = price_data["rsi"] < 35

                # Firestore에 저장
                self.db.collection('watchlist').document(stock_code).set(price_data)
                print(f"📊 {price_data['name']} 업데이트: {price_data['currentPrice']:,.0f}원 ({price_data['changePercent']:+.2f}%)")

    def update_account_summary(self):
        """계좌 정보 업데이트"""
        balance = self.get_account_balance()
        if balance:
            # 계좌 요약 정보 저장
            self.db.collection('account').document('summary').set({
                "totalAssets": balance.get("total_assets", 0),
                "totalCash": balance.get("cash", 0),
                "todayPnL": 0,  # 실제로는 당일 손익 계산 필요
                "todayPnLPercent": 0,
                "timestamp": firestore.SERVER_TIMESTAMP
            })

    def update_bot_status(self):
        """봇 상태 업데이트 (Heartbeat)"""
        self.db.collection('bot_status').document('main').set({
            "running": self.is_running,
            "lastHeartbeat": firestore.SERVER_TIMESTAMP,
            "version": "1.0.0",
            "environment": "VIRTUAL"
        })
        print(f"💚 Heartbeat - 봇 상태: {'실행중' if self.is_running else '정지'}")

    def add_trade_log(self, log_type: str, message: str, **kwargs):
        """거래 로그 추가"""
        log_data = {
            "type": log_type,
            "message": message,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "stockCode": kwargs.get("stockCode", ""),
            "stockName": kwargs.get("stockName", ""),
            "price": kwargs.get("price"),
            "quantity": kwargs.get("quantity"),
            "reason": kwargs.get("reason")
        }

        self.db.collection('trade_logs').add(log_data)
        print(f"📝 [{log_type}] {message}")

    def start(self):
        """봇 시작"""
        self.is_running = True
        self.update_bot_status()
        self.add_trade_log("INFO", "KIS 자동매매 봇 시작 (모의투자)")

        print("\n🚀 KIS 자동매매 봇 시작")
        print("=" * 50)

        # 초기 데이터 업데이트
        self.update_account_summary()
        self.update_watchlist()

        # 메인 루프
        loop_count = 0
        while self.is_running:
            try:
                # 5초마다 감시 종목 업데이트
                if loop_count % 5 == 0:
                    self.update_watchlist()

                # 10초마다 계좌 정보 업데이트
                if loop_count % 10 == 0:
                    self.update_account_summary()

                # 30초마다 봇 상태 업데이트
                if loop_count % 30 == 0:
                    self.update_bot_status()

                # 명령 확인 (전량 매도, 수동 매도 등)
                self.check_commands()

                time.sleep(1)
                loop_count += 1

            except KeyboardInterrupt:
                print("\n⛔ 사용자에 의해 중단됨")
                self.stop()
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                self.add_trade_log("ERROR", f"봇 오류: {str(e)}")
                time.sleep(5)

    def check_commands(self):
        """Firestore에서 명령 확인 및 처리"""
        commands = self.db.collection('commands').where('status', '==', 'pending').stream()

        for cmd_doc in commands:
            cmd_data = cmd_doc.to_dict()
            cmd_type = cmd_data.get('type')

            if cmd_type == 'PANIC_SELL':
                self.add_trade_log("SELL", "전량 매도 명령 수신")
                # 실제 매도 로직 구현
            elif cmd_type == 'MANUAL_SELL':
                stock_code = cmd_data.get('stockCode')
                self.add_trade_log("SELL", f"수동 매도 명령 수신: {stock_code}")
                # 실제 매도 로직 구현

            # 명령 처리 완료 표시
            self.db.collection('commands').document(cmd_doc.id).update({'status': 'completed'})

    def stop(self):
        """봇 정지"""
        self.is_running = False
        self.update_bot_status()
        self.add_trade_log("INFO", "KIS 자동매매 봇 정지")
        print("🛑 봇이 정지되었습니다")

if __name__ == "__main__":
    bot = KISBot()
    bot.start()