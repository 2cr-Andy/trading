#!/usr/bin/env python3
"""통합 트레이딩 봇 - 매수/매도/모니터링 모두 포함"""

import os
import sys
import time
import json
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore

from market_scanner import MarketScanner
from logger_system import UnifiedLogger as TradingLogger
from smart_stock_name_manager import SmartStockNameManager

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

class IntegratedTradingBot:
    def __init__(self):
        self.db = firestore.client()
        self.logger = TradingLogger()
        self.scanner = MarketScanner(
            app_key=os.getenv('KIS_APP_KEY'),
            app_secret=os.getenv('KIS_APP_SECRET')
        )
        self.name_manager = SmartStockNameManager()

        # 계좌 정보
        self.account_no = os.getenv('KIS_ACCOUNT_NUMBER')
        if '-' not in self.account_no:
            self.account_no = f"{self.account_no}-01"

        # 트레이딩 설정
        self.max_positions = 5  # 최대 5종목
        self.profit_target = 0.05  # 익절 5%
        self.stop_loss = -0.03  # 손절 -3%

        # 상태 관리
        self.portfolio = {}
        self.kst_timezone = pytz.timezone('Asia/Seoul')
        self.is_running = False

    def get_access_token(self):
        """토큰 가져오기"""
        try:
            with open('kis_token.json', 'r') as f:
                token_data = json.load(f)
                return token_data.get('token')
        except:
            self.logger.error("토큰 파일을 찾을 수 없습니다")
            return None

    def load_portfolio(self):
        """Firebase에서 포트폴리오 로드"""
        try:
            portfolio_docs = self.db.collection('portfolio').stream()
            self.portfolio = {}

            for doc in portfolio_docs:
                stock_code = doc.id
                data = doc.to_dict()
                self.portfolio[stock_code] = data

            self.logger.info(f"포트폴리오 로드 완료: {len(self.portfolio)}개 보유")
        except Exception as e:
            self.logger.error(f"포트폴리오 로드 실패: {e}")

    def get_account_balance(self):
        """계좌 잔고 조회"""
        token = self.get_access_token()
        if not token:
            return None

        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "VTTC8434R"
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

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    output2 = data.get('output2', [{}])[0]
                    return {
                        'total_cash': float(output2.get('dnca_tot_amt', 0)),
                        'available_cash': float(output2.get('nass_amt', 0))
                    }
        except Exception as e:
            self.logger.error(f"잔고 조회 실패: {e}")

        return None

    def check_sell_conditions(self):
        """매도 조건 체크 및 실행"""
        for stock_code, holding in list(self.portfolio.items()):
            try:
                # 수익률 체크
                profit_rate = holding.get('profit_rate', 0) / 100  # 퍼센트를 비율로 변환

                should_sell = False
                reason = ""

                # 익절 조건 (5%)
                if profit_rate >= self.profit_target:
                    should_sell = True
                    reason = f"익절 {profit_rate*100:.1f}%"

                # 손절 조건 (-3%)
                elif profit_rate <= self.stop_loss:
                    should_sell = True
                    reason = f"손절 {profit_rate*100:.1f}%"

                # 특별 케이스: 10% 이상
                elif profit_rate >= 0.10:
                    should_sell = True
                    reason = f"10% 초과 익절 {profit_rate*100:.1f}%"

                if should_sell:
                    self.logger.info(f"매도 신호: {holding.get('name', stock_code)} - {reason}")
                    self.execute_sell(stock_code, holding, reason)
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"매도 체크 오류 ({stock_code}): {e}")

    def execute_sell(self, stock_code, holding, reason):
        """매도 실행"""
        token = self.get_access_token()
        if not token:
            return False

        quantity = holding.get('quantity', 0)
        if quantity <= 0:
            return False

        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "VTTC0801U"  # 모의투자 매도
        }

        data = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                if result.get('rt_cd') == '0':
                    self.logger.trade(
                        "sell",
                        f"매도 체결: {holding.get('name', stock_code)}",
                        stock_code=stock_code,
                        quantity=quantity,
                        reason=reason
                    )

                    # 포트폴리오에서 제거
                    del self.portfolio[stock_code]
                    self.db.collection('portfolio').document(stock_code).delete()

                    return True
                else:
                    self.logger.error(f"매도 실패: {result.get('msg1')}")
        except Exception as e:
            self.logger.error(f"매도 주문 오류: {e}")

        return False

    def calculate_buy_quantity(self, stock_price):
        """매수 수량 계산 (균형있게)"""
        balance = self.get_account_balance()
        if not balance:
            return 0

        available_cash = balance['available_cash']

        # 남은 슬롯에 맞춰 균등 분배
        remaining_slots = max(1, self.max_positions - len(self.portfolio))
        position_size = available_cash / remaining_slots

        # 최소 5만원, 최대 전체의 30%
        position_size = max(50000, min(position_size, available_cash * 0.3))

        quantity = int(position_size / stock_price)

        return max(1, quantity)  # 최소 1주

    def execute_buy(self, stock_code, stock_name, stock_price):
        """매수 실행"""
        # 이미 보유 중이면 스킵
        if stock_code in self.portfolio:
            return False

        # 매수 수량 계산
        quantity = self.calculate_buy_quantity(stock_price)
        if quantity < 1:
            return False

        token = self.get_access_token()
        if not token:
            return False

        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "VTTC0802U"  # 모의투자 매수
        }

        data = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                if result.get('rt_cd') == '0':
                    self.logger.trade(
                        "buy",
                        f"매수 체결: {stock_name} {quantity}주",
                        stock_code=stock_code,
                        quantity=quantity,
                        price=stock_price
                    )

                    # 포트폴리오에 추가
                    self.portfolio[stock_code] = {
                        'code': stock_code,
                        'name': stock_name,
                        'quantity': quantity,
                        'buy_price': stock_price,
                        'buy_time': datetime.now(self.kst_timezone).isoformat(),
                        'status': 'holding'
                    }

                    # Firebase에 저장
                    self.db.collection('portfolio').document(stock_code).set(
                        self.portfolio[stock_code]
                    )

                    return True
        except Exception as e:
            self.logger.error(f"매수 주문 오류: {e}")

        return False

    def scan_and_buy(self):
        """시장 스캔 및 매수"""
        if len(self.portfolio) >= self.max_positions:
            return

        # 시장 스캔
        watchlist = self.scanner.scan_market()

        for stock in watchlist[:10]:  # 상위 10개만
            if len(self.portfolio) >= self.max_positions:
                break

            if stock.get('buy_signal') and stock['code'] not in self.portfolio:
                stock_name = self.name_manager.get_stock_name(stock['code'])
                self.logger.info(f"매수 시도: {stock_name}")

                success = self.execute_buy(
                    stock['code'],
                    stock_name,
                    stock.get('current_price', 0)
                )

                if success:
                    time.sleep(2)

    def update_portfolio_prices(self):
        """포트폴리오 가격 업데이트"""
        for stock_code in self.portfolio:
            try:
                # 현재가 조회 (간단 버전)
                # 실제로는 API 호출해서 업데이트
                pass
            except:
                pass

    def run(self):
        """메인 실행 루프"""
        self.is_running = True
        self.logger.system("🚀 통합 트레이딩 봇 시작")

        # 초기 포트폴리오 로드
        self.load_portfolio()

        last_scan_time = 0
        last_sell_check = 0

        while self.is_running:
            try:
                now = time.time()

                # 장시간 체크
                if not self.is_trading_time():
                    time.sleep(60)
                    continue

                # 매도 체크 (30초마다)
                if now - last_sell_check > 30:
                    self.check_sell_conditions()
                    last_sell_check = now

                # 시장 스캔 및 매수 (5분마다)
                if now - last_scan_time > 300:
                    self.scan_and_buy()
                    last_scan_time = now

                # 포트폴리오 가격 업데이트 (1분마다)
                if int(now) % 60 == 0:
                    self.update_portfolio_prices()

                time.sleep(10)

            except KeyboardInterrupt:
                self.logger.system("봇 종료")
                break
            except Exception as e:
                self.logger.error(f"메인 루프 오류: {e}")
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
    bot = IntegratedTradingBot()
    bot.run()