#!/usr/bin/env python3
"""개선된 트레이딩 봇 - 매도 조건 강화 & 자금 관리 개선"""

import os
from dotenv import load_dotenv
import time
from datetime import datetime
import pytz
import firebase_admin
from firebase_admin import credentials, firestore
from market_scanner import MarketScanner
from logger_system import TradingLogger
import requests
import json

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

class ImprovedTradingBot:
    def __init__(self):
        self.db = firestore.client()
        self.logger = TradingLogger()
        self.scanner = MarketScanner(
            app_key=os.getenv('KIS_APP_KEY'),
            app_secret=os.getenv('KIS_APP_SECRET')
        )

        # 트레이딩 설정 (개선된 값)
        self.max_positions = 4  # 최대 보유 종목
        self.position_size_ratio = 0.20  # 종목당 20% 투자
        self.min_buy_amount = 50000  # 최소 매수 금액 5만원

        # 매도 조건 (더 적극적)
        self.profit_targets = {
            'quick': 0.03,    # 3% 빠른 익절
            'normal': 0.05,   # 5% 일반 익절
            'greed': 0.10     # 10% 욕심 익절
        }
        self.stop_loss = -0.02  # 2% 손절 (더 타이트하게)
        self.trailing_stop = 0.02  # 2% 트레일링 스탑

        self.portfolio = {}
        self.kst_timezone = pytz.timezone('Asia/Seoul')
        self.account_no = os.getenv('KIS_ACCOUNT_NO')

    def get_access_token(self):
        """저장된 토큰 사용"""
        try:
            with open('kis_token.json', 'r') as f:
                token_data = json.load(f)
                return token_data.get('token')
        except:
            return None

    def get_account_balance(self):
        """계좌 잔고 조회"""
        token = self.get_access_token()
        if not token:
            return None

        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "TTTC8434R"
        }

        params = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get('rt_cd') == '0':
                output2 = data.get('output2', [{}])[0]
                return {
                    'total_cash': float(output2.get('dnca_tot_amt', 0)),  # 예수금총액
                    'available_cash': float(output2.get('nass_amt', 0)),  # 순자산금액
                    'total_assets': float(output2.get('tot_evlu_amt', 0))  # 총평가금액
                }
        return None

    def calculate_position_size(self, stock_price):
        """적절한 매수 수량 계산"""
        balance = self.get_account_balance()
        if not balance:
            return 0

        available_cash = balance['available_cash']

        # 이미 보유 종목이 있으면 남은 슬롯에 맞춰 계산
        remaining_slots = max(1, self.max_positions - len(self.portfolio))
        position_size = available_cash / remaining_slots

        # 최대 20% 제한
        position_size = min(position_size, available_cash * self.position_size_ratio)

        # 최소 매수 금액 체크
        if position_size < self.min_buy_amount:
            return 0

        quantity = int(position_size / stock_price)

        self.logger.info(f"포지션 계산", {
            "available_cash": available_cash,
            "position_size": position_size,
            "stock_price": stock_price,
            "quantity": quantity
        })

        return quantity

    def check_sell_conditions(self, stock_code):
        """매도 조건 체크 (개선된 로직)"""
        if stock_code not in self.portfolio:
            return False, None

        holding = self.portfolio[stock_code]

        # 현재가 조회
        current_price = self.get_current_price(stock_code)
        if not current_price:
            return False, None

        buy_price = holding['buy_price']
        high_price = holding.get('high_price', buy_price)
        profit_rate = (current_price - buy_price) / buy_price

        # 고점 대비 하락률
        drop_from_high = (high_price - current_price) / high_price if high_price > 0 else 0

        # 보유 시간
        buy_time = datetime.fromisoformat(holding['buy_time'])
        hold_hours = (datetime.now(self.kst_timezone) - buy_time).total_seconds() / 3600

        # 1. 손절 (2%)
        if profit_rate <= self.stop_loss:
            return True, f"손절 {profit_rate:.1%}"

        # 2. 빠른 익절 (3% 도달시)
        if profit_rate >= self.profit_targets['quick'] and hold_hours < 1:
            return True, f"빠른 익절 {profit_rate:.1%}"

        # 3. 일반 익절 (5% 도달시)
        if profit_rate >= self.profit_targets['normal']:
            return True, f"목표 익절 {profit_rate:.1%}"

        # 4. 트레일링 스탑 (고점 대비 2% 하락)
        if profit_rate > 0.02 and drop_from_high >= self.trailing_stop:
            return True, f"트레일링 스탑 (고점 대비 -{drop_from_high:.1%})"

        # 5. 시간 기반 청산 (장 마감 10분 전)
        now = datetime.now(self.kst_timezone)
        if now.hour == 15 and now.minute >= 10:
            if profit_rate > -0.01:  # 1% 이내 손실이면 청산
                return True, f"장마감 청산 {profit_rate:.1%}"

        # 고점 업데이트
        if current_price > high_price:
            holding['high_price'] = current_price
            self.update_portfolio_firebase(stock_code, {'high_price': current_price})

        return False, None

    def get_current_price(self, stock_code):
        """현재가 조회"""
        token = self.get_access_token()
        if not token:
            return None

        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "FHKST01010100"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get('rt_cd') == '0':
                return int(data.get('output', {}).get('stck_prpr', 0))
        return None

    def execute_sell(self, stock_code, reason):
        """매도 실행"""
        if stock_code not in self.portfolio:
            return False

        holding = self.portfolio[stock_code]
        quantity = holding['quantity']
        current_price = self.get_current_price(stock_code)

        token = self.get_access_token()
        if not token:
            return False

        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "TTTC0801U"
        }

        data = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            if result.get('rt_cd') == '0':
                # 수익률 계산
                profit_rate = (current_price - holding['buy_price']) / holding['buy_price']
                profit_amount = (current_price - holding['buy_price']) * quantity

                self.logger.trade(
                    "sell",
                    f"매도 체결: {holding['name']} {profit_rate:+.1%}",
                    stock_code=stock_code,
                    quantity=quantity,
                    price=current_price,
                    profit_rate=profit_rate,
                    profit_amount=profit_amount,
                    reason=reason
                )

                # 포트폴리오에서 제거
                del self.portfolio[stock_code]

                # Firebase에서 제거
                self.db.collection('portfolio').document(stock_code).delete()

                return True

        return False

    def update_portfolio_firebase(self, stock_code, update_data):
        """Firebase 포트폴리오 업데이트"""
        try:
            self.db.collection('portfolio').document(stock_code).update(update_data)
        except:
            pass

    def monitor_portfolio(self):
        """포트폴리오 모니터링 및 매도 체크"""
        for stock_code in list(self.portfolio.keys()):
            should_sell, reason = self.check_sell_conditions(stock_code)

            if should_sell:
                self.logger.info(f"매도 신호 감지: {stock_code} - {reason}")
                success = self.execute_sell(stock_code, reason)
                if success:
                    time.sleep(1)  # API 제한

    def run(self):
        """메인 실행"""
        self.logger.system("개선된 트레이딩 봇 시작")

        while True:
            try:
                # 장시간 체크
                if not self.is_trading_time():
                    time.sleep(60)
                    continue

                # 포트폴리오 모니터링 (매 10초)
                self.monitor_portfolio()

                # 잔고 확인 후 매수 가능 여부 체크
                if len(self.portfolio) < self.max_positions:
                    # 매수 로직...
                    pass

                time.sleep(10)

            except KeyboardInterrupt:
                self.logger.system("봇 종료")
                break
            except Exception as e:
                self.logger.error("메인 루프 오류", {"error": str(e)})
                time.sleep(30)

    def is_trading_time(self):
        """장시간 체크"""
        now = datetime.now(self.kst_timezone)
        if now.weekday() >= 5:
            return False
        current_time = now.time()
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("15:20", "%H:%M").time()
        return market_open <= current_time <= market_close

if __name__ == "__main__":
    bot = ImprovedTradingBot()
    bot.run()