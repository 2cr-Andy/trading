import os
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from market_scanner import MarketScanner
import pytz
from slack_notifier import SlackNotifier
from logger_system import UnifiedLogger

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
        self.last_token_attempt = 0  # 마지막 토큰 발급 시도 시간

        # 봇 상태
        self.is_running = False

        # MarketScanner 초기화 (토큰 공유를 위해 self.get_access_token 전달)
        self.scanner = MarketScanner(self.app_key, self.app_secret, self.get_access_token)
        self.current_watchlist = []
        self.portfolio = {}  # 보유 종목 관리
        self.max_positions = 3  # 최대 보유 종목 수
        self.profit_target = 0.05  # 익절 목표 5%
        self.stop_loss = -0.03  # 손절 기준 -3%
        self.kst_timezone = pytz.timezone('Asia/Seoul')  # 한국 시간대
        self.last_market_closed_log = 0  # 마지막 장마감 로그 시간
        self.slack = SlackNotifier()  # Slack 알림 시스템

        # 통합 로거 초기화
        self.logger = UnifiedLogger(log_dir="logs", slack_enabled=True)

        self.logger.system("KIS Bot 초기화 완료", {
            "계좌번호": self.account_number,
            "Firebase 프로젝트": "trading-dcd8c",
            "최대 보유 종목": self.max_positions
        })

    def get_access_token(self) -> str:
        """접속 토큰 발급 또는 갱신"""
        current_time = time.time()

        # 토큰이 유효한 경우 재사용
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token

        # 1분 제한 체크 (마지막 시도로부터 60초 경과 확인)
        time_since_last_attempt = current_time - self.last_token_attempt
        if time_since_last_attempt < 60:
            wait_time = 60 - time_since_last_attempt
            self.logger.warning(f"토큰 발급 제한: {wait_time:.0f}초 후 재시도 가능")
            return None

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        self.logger.debug(f"토큰 발급 시도", {"url": url, "app_key_prefix": self.app_key[:10]})

        # 토큰 시도 시간 기록
        self.last_token_attempt = current_time

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))

            if response.status_code == 403:
                error_data = response.json() if response.text else {}
                error_code = error_data.get("error_code", "")

                self.logger.error(f"403 에러 발생", {"response": response.text, "error_code": error_code})

                if error_code == "EGW00133":  # 1분 제한 에러
                    self.logger.warning("토큰 발급 1분 제한 - 1분 후 재시도 필요")
                    return None

            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("access_token")
            # 토큰 만료 시간 설정 (보통 24시간이지만 안전하게 23시간으로 설정)
            self.token_expires_at = current_time + (23 * 60 * 60)

            self.logger.success("접속 토큰 발급 성공")
            return self.access_token

        except Exception as e:
            error_data = {"error": str(e)}
            if hasattr(e, 'response') and e.response is not None:
                error_data["status_code"] = e.response.status_code
                error_data["response"] = e.response.text
            self.logger.error("토큰 발급 실패", error_data)
            return None

    def get_account_balance(self) -> Dict:
        """계좌 잔고 조회 (주식잔고조회 API 사용)"""
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "VTTC8434R",  # 모의투자 주식잔고조회
            "custtype": "P"
        }

        params = {
            "CANO": self.account_number[:8],
            "ACNT_PRDT_CD": "01",
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") == "0":
                output2 = data.get("output2", [{}])[0]
                balance = {
                    "cash": float(output2.get("dnca_tot_amt", 0)),  # 예수금 총액
                    "total_assets": float(output2.get("tot_evlu_amt", 0)),  # 총 평가 금액
                    "stock_value": float(output2.get("scts_evlu_amt", 0)),  # 주식 평가 금액
                    "profit_loss": float(output2.get("evlu_pfls_amt", 0)),  # 평가 손익 금액
                    "profit_loss_rate": float(output2.get("evlu_pfls_rt", 0)),  # 평가 손익률
                    "timestamp": datetime.now()
                }

                print(f"💰 예수금: {balance['cash']:,.0f}원 | 총자산: {balance['total_assets']:,.0f}원")
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

    def buy_stock(self, stock_code: str, current_price: float, buy_reason: str = "") -> bool:
        """주식 매수 주문 실행 (The Three Kings Rule)"""
        # 1. 현재 보유 종목 수 확인
        if len(self.portfolio) >= self.max_positions:
            print(f"⚠️ 최대 보유 종목({self.max_positions}개) 초과로 매수 불가")
            return False

        # 2. 예수금 조회
        balance = self.get_account_balance()
        if not balance:
            print("❌ 잘고 조회 실패")
            return False

        available_cash = balance.get('cash', 0)
        if available_cash < 10000:  # 최소 매수 금액
            print(f"⚠️ 예수금 부족: {available_cash:,.0f}원")
            return False

        # 3. 자금 관리 (3등분 전략)
        target_buy_amount = available_cash / (self.max_positions - len(self.portfolio))
        target_buy_amount = min(target_buy_amount, available_cash * 0.33)  # 최대 33% 제한
        quantity = int(target_buy_amount / current_price)

        if quantity < 1:
            print(f"⚠️ 매수 수량 부족: {target_buy_amount:,.0f}원 / {current_price:,.0f}원")
            return False

        # 4. KIS API로 매수 주문 전송
        token = self.get_access_token()
        if not token:
            return False

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "VTTC0802U",  # 모의투자 매수
            "custtype": "P"
        }

        body = {
            "CANO": self.account_number[:8],
            "ACNT_PRDT_CD": "01",
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0",  # 시장가는 0
            "CTAC_TLNO": "",
            "SLL_BUY_DVSN_CD": "02",  # 매수
            "ALGO_NO": ""
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") == "0":
                # 5. 포트폴리오 추가
                self.portfolio[stock_code] = {
                    "buy_price": current_price,
                    "quantity": quantity,
                    "buy_time": datetime.now(),
                    "buy_reason": buy_reason
                }

                # 6. 거래 로그 기록
                self.add_trade_log(
                    "BUY",
                    f"매수 체결: {quantity}주 @ {current_price:,.0f}원",
                    stockCode=stock_code,
                    price=current_price,
                    quantity=quantity,
                    reason=buy_reason
                )

                # 7. 포트폴리오 Firestore 업데이트
                self.update_portfolio_to_firestore()

                print(f"🟢 매수 성공: {stock_code} {quantity}주 @ {current_price:,.0f}원")
                print(f"   투자금액: {quantity * current_price:,.0f}원 | 사유: {buy_reason}")
                return True
            else:
                print(f"❌ 매수 주문 실패: {data.get('msg1')}")
                return False

        except Exception as e:
            print(f"❌ 매수 주문 오류: {e}")
            return False

    def sell_stock(self, stock_code: str, current_price: float, sell_reason: str = "") -> bool:
        """주식 매도 주문 실행"""
        if stock_code not in self.portfolio:
            print(f"⚠️ {stock_code} 보유하고 있지 않음")
            return False

        holding = self.portfolio[stock_code]
        quantity = holding['quantity']

        # KIS API로 매도 주문 전송
        token = self.get_access_token()
        if not token:
            return False

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "VTTC0801U",  # 모의투자 매도
            "custtype": "P"
        }

        body = {
            "CANO": self.account_number[:8],
            "ACNT_PRDT_CD": "01",
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0",
            "CTAC_TLNO": "",
            "SLL_BUY_DVSN_CD": "01",  # 매도
            "ALGO_NO": ""
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") == "0":
                # 수익률 계산
                profit_rate = (current_price - holding['buy_price']) / holding['buy_price']
                profit_amount = (current_price - holding['buy_price']) * quantity

                # 포트폴리오에서 제거
                del self.portfolio[stock_code]

                # 거래 로그 기록
                self.add_trade_log(
                    "SELL",
                    f"매도 체결: {quantity}주 @ {current_price:,.0f}원 (수익률: {profit_rate:.2%})",
                    stockCode=stock_code,
                    price=current_price,
                    quantity=quantity,
                    reason=sell_reason
                )

                # 포트폴리오 Firestore 업데이트
                self.update_portfolio_to_firestore()

                emoji = "🔴" if profit_rate > 0 else "🔵"
                print(f"{emoji} 매도 성공: {stock_code} {quantity}주 @ {current_price:,.0f}원")
                print(f"   수익: {profit_amount:,.0f}원 ({profit_rate:+.2%}) | 사유: {sell_reason}")
                return True
            else:
                print(f"❌ 매도 주문 실패: {data.get('msg1')}")
                return False

        except Exception as e:
            print(f"❌ 매도 주문 오류: {e}")
            return False

    def check_portfolio_targets(self):
        """포트폴리오 종목들의 익절/손절 체크"""
        if not self.portfolio:
            return

        for stock_code, holding in list(self.portfolio.items()):
            # 현재가 조회
            price_data = self.get_stock_price(stock_code)
            if not price_data:
                continue

            current_price = price_data['currentPrice']
            buy_price = holding['buy_price']
            profit_rate = (current_price - buy_price) / buy_price

            # 익절/손절 체크
            if profit_rate >= self.profit_target:
                print(f"\n🎯 익절 신호: {stock_code} 수익률 {profit_rate:.2%}")
                self.sell_stock(stock_code, current_price, f"익절 {profit_rate:.2%}")
            elif profit_rate <= self.stop_loss:
                print(f"\n🚨 손절 신호: {stock_code} 손실률 {profit_rate:.2%}")
                self.sell_stock(stock_code, current_price, f"손절 {profit_rate:.2%}")

    def update_portfolio_to_firestore(self):
        """포트폴리오 정보를 Firestore에 업데이트"""
        for stock_code, holding in self.portfolio.items():
            self.db.collection('portfolio').document(stock_code).set({
                "code": stock_code,
                "buy_price": holding['buy_price'],
                "quantity": holding['quantity'],
                "buy_time": holding['buy_time'],
                "buy_reason": holding.get('buy_reason', ''),
                "timestamp": firestore.SERVER_TIMESTAMP
            })

        # 포트폴리오에 없는 종목 삭제
        portfolio_docs = self.db.collection('portfolio').stream()
        for doc in portfolio_docs:
            if doc.id not in self.portfolio:
                doc.reference.delete()

    def get_daily_candles(self, stock_code: str, period: int = 150) -> pd.DataFrame:
        """일봉 데이터 조회 (과거 N일)"""
        token = self.get_access_token()
        if not token:
            return None

        # 날짜 계산
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=period)).strftime('%Y%m%d')

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST03010100"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") == "0":
                output2 = data.get("output2", [])
                if not output2:
                    return None

                # DataFrame 생성
                df_data = []
                for row in output2:
                    df_data.append({
                        "date": pd.to_datetime(row.get("stck_bsop_date", "")),
                        "open": float(row.get("stck_oprc", 0)),
                        "high": float(row.get("stck_hgpr", 0)),
                        "low": float(row.get("stck_lwpr", 0)),
                        "close": float(row.get("stck_clpr", 0)),
                        "volume": float(row.get("acml_vol", 0)),
                        "amount": float(row.get("acml_tr_pbmn", 0))
                    })

                df = pd.DataFrame(df_data)
                df.sort_values('date', inplace=True)
                df.reset_index(drop=True, inplace=True)
                return df

            return None

        except Exception as e:
            print(f"❌ 일봉 데이터 조회 오류 ({stock_code}): {e}")
            return None

    def calculate_technicals(self, df: pd.DataFrame) -> Dict:
        """기술적 지표 계산 (MarketScanner의 고급 지표 활용)"""
        if df is None or len(df) < 120:
            return None

        # MarketScanner의 고급 지표 계산 메서드 활용
        return self.scanner.calculate_advanced_technicals(df)

    def scan_market_conditions(self) -> List[str]:
        """동적 시장 스캔 - MarketScanner 활용"""
        print("\n🚀 동적 시장 스캔 시작 (거래량/등락률/수급 분석)")

        # MarketScanner로 주도주 발굴
        qualified_stocks = self.scanner.scan_market()

        if not qualified_stocks:
            print("⚠️ 조건에 맞는 종목이 없습니다.")
            return []

        # 종목 코드만 추출
        stock_codes = [stock['code'] for stock in qualified_stocks]

        # 선정된 종목 정보 출력
        print(f"\n✨ 최종 선정 종목: {len(stock_codes)}개")
        for stock in qualified_stocks[:5]:  # 상위 5개만 표시
            signal_text = f"🔴 매수신호: {stock['buy_reason']}" if stock['buy_signal'] else "⚪ 대기"
            print(f"  📌 {stock['code']}: {stock['price']:,.0f}원 | RSI:{stock['rsi']:.1f} | ADX:{stock['adx']:.1f} | {signal_text}")

        return stock_codes[:5]  # 최대 5개 종목 감시

    def sync_watchlist_with_firestore(self, new_watchlist: List[str]):
        """감시 종목 리스트를 Firestore와 동기화 (좀비 데이터 삭제)"""
        # 1. 현재 Firestore에 있는 모든 종목 가져오기
        existing_docs = self.db.collection('watchlist').stream()
        existing_codes = set(doc.id for doc in existing_docs)

        # 2. 삭제해야 할 종목 식별 (기존 - 신규)
        codes_to_delete = existing_codes - set(new_watchlist)

        # 3. 조건에서 탈락한 종목 삭제
        for code in codes_to_delete:
            self.db.collection('watchlist').document(code).delete()
            print(f"🗑️ 감시 종목에서 제거: {code}")

        # 4. 현재 watchlist 업데이트
        self.current_watchlist = new_watchlist

    def update_watchlist(self, watchlist: List[str] = None):
        """감시 종목 리스트 업데이트 (실제 기술적 지표 계산)"""
        if watchlist is None:
            watchlist = self.current_watchlist if hasattr(self, 'current_watchlist') else []

        if not watchlist:
            print("⚠️ 감시 종목이 없습니다")
            return

        for stock_code in watchlist:
            try:
                # 현재가 조회
                price_data = self.get_stock_price(stock_code)
                if not price_data:
                    continue

                # 일봉 데이터와 고급 지표 계산
                df = self.scanner.get_daily_candles(stock_code)
                if df is not None and len(df) >= 120:
                    # MarketScanner의 고급 지표 계산
                    indicators = self.scanner.calculate_advanced_technicals(df)
                    if indicators:
                        # 수급 데이터 추가
                        smart_money = self.scanner.get_foreign_institution_buy(stock_code)

                        # 매수 신호 확인
                        buy_signal, buy_reason = self.scanner.check_buy_signal(indicators)

                        price_data["rsi"] = indicators['rsi']
                        price_data["mfi"] = indicators['mfi']
                        price_data["volumeChange"] = 0  # 별도 계산 필요
                        price_data["ma120"] = indicators['ma120']
                        price_data["ma20"] = indicators['ma20']
                        price_data["bb_upper"] = indicators['bb_upper']
                        price_data["bb_lower"] = indicators['bb_lower']
                        price_data["adx"] = indicators['adx']
                        price_data["obv_signal"] = indicators['obv'] > indicators['obv_ma20']
                        price_data["nearBuySignal"] = buy_signal
                        price_data["buyReason"] = buy_reason

                        if smart_money:
                            price_data["foreignNetBuy"] = smart_money.get('foreign_net_buy_5d', 0)
                            price_data["institutionNetBuy"] = smart_money.get('institution_net_buy_5d', 0)
                else:
                    # 데이터 부족 시 기본값
                    price_data["rsi"] = 50
                    price_data["mfi"] = 50
                    price_data["volumeChange"] = 0
                    price_data["nearBuySignal"] = False
                    price_data["buyReason"] = ""

                # Firestore에 저장
                self.db.collection('watchlist').document(stock_code).set(price_data)
                signal_text = f" 🔴 {price_data.get('buyReason', '')}" if price_data.get('nearBuySignal') else ""
                print(f"📊 {price_data['name']}: {price_data['currentPrice']:,.0f}원 ({price_data['changePercent']:+.2f}%) RSI:{price_data.get('rsi', 0):.1f}{signal_text}")

                # 매수 신호가 있고 포트폴리오에 없다면 매수 실행
                if price_data.get('nearBuySignal') and stock_code not in self.portfolio:
                    print(f"\n🔔 매수 신호 감지! {stock_code} 매수 주문 시도...")
                    self.buy_stock(
                        stock_code,
                        price_data['currentPrice'],
                        price_data.get('buyReason', '')
                    )

            except Exception as e:
                print(f"❌ {stock_code} 업데이트 오류: {e}")
                continue

    def update_account_summary(self):
        """계좌 정보 업데이트"""
        balance = self.get_account_balance()
        if balance:
            # 계좌 요약 정보 저장
            account_data = {
                "totalAssets": balance.get("total_assets", 0),
                "totalCash": balance.get("cash", 0),
                "todayPnL": balance.get("profit_loss", 0),  # 평가 손익
                "todayPnLPercent": balance.get("profit_loss_rate", 0),  # 평가 손익률
                "timestamp": firestore.SERVER_TIMESTAMP
            }
            print(f"📊 Firebase 계좌 업데이트: 총자산={account_data['totalAssets']:,.0f}원, 예수금={account_data['totalCash']:,.0f}원")
            self.db.collection('account').document('summary').set(account_data)

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
        self.add_trade_log("INFO", "KIS 자동매매 봇 시작 (실제 데이터 기반)")

        print("\n🚀 KIS 자동매매 봇 시작")
        print("=" * 50)

        # Slack 시작 알림
        self.slack.notify_bot_start()

        # 동적 시장 스캔으로 감시 종목 선정
        new_watchlist = self.scan_market_conditions()

        if new_watchlist:
            # Firestore 동기화 (조건 탈락 종목 삭제)
            self.sync_watchlist_with_firestore(new_watchlist)
        else:
            print("⚠️ 조건에 맞는 종목이 없습니다. 재스캔 예정...")
            self.current_watchlist = []

        # 초기 데이터 업데이트
        self.update_account_summary()
        self.update_watchlist(self.current_watchlist)

        # 메인 루프
        loop_count = 0
        while self.is_running:
            try:
                # 장 운영 시간 체크
                if not self.is_trading_time():
                    current_time = time.time()
                    # 1시간에 한 번만 로그 출력
                    if current_time - self.last_market_closed_log > 3600:
                        now = datetime.now(self.kst_timezone)
                        print(f"🚫 장 마감: 대기 중... ({now.strftime('%Y-%m-%d %H:%M:%S')} KST)")
                        self.last_market_closed_log = current_time
                    time.sleep(60)  # 60초 대기
                    continue

                # 장 운영 시간 내에만 아래 로직 실행
                # 10초마다 감시 종목 업데이트 (API 부하 고려)
                if loop_count % 10 == 0:
                    self.update_watchlist(self.current_watchlist)

                # 20초마다 포트폴리오 익절/손절 체크
                if loop_count % 20 == 0 and self.portfolio:
                    self.check_portfolio_targets()

                # 30초마다 계좌 정보 업데이트
                if loop_count % 30 == 0:
                    self.update_account_summary()

                # 300초(5분)마다 시장 조건 재스캔
                if loop_count % 300 == 0 and loop_count > 0:
                    print("\n🔄 동적 시장 재스캔...")
                    new_watchlist = self.scan_market_conditions()
                    if new_watchlist:
                        # Firestore 동기화 (조건 탈락 종목 삭제)
                        self.sync_watchlist_with_firestore(new_watchlist)
                        self.add_trade_log("INFO", f"감시 종목 업데이트: {len(new_watchlist)}개")

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
                # 포트폴리오 전체 매도
                for stock_code in list(self.portfolio.keys()):
                    price_data = self.get_stock_price(stock_code)
                    if price_data:
                        self.sell_stock(stock_code, price_data['currentPrice'], "전량 매도 명령")
            elif cmd_type == 'MANUAL_SELL':
                stock_code = cmd_data.get('stockCode')
                self.add_trade_log("SELL", f"수동 매도 명령 수신: {stock_code}")
                if stock_code in self.portfolio:
                    price_data = self.get_stock_price(stock_code)
                    if price_data:
                        self.sell_stock(stock_code, price_data['currentPrice'], "수동 매도 명령")

            # 명령 처리 완료 표시
            self.db.collection('commands').document(cmd_doc.id).update({'status': 'completed'})

    def is_trading_time(self) -> bool:
        """현재 시간이 장 운영 시간인지 확인 (08:00 ~ 18:00)"""
        now = datetime.now(self.kst_timezone)
        current_time = now.time()
        weekday = now.weekday()

        # 주말 체크 (0=월요일, 6=일요일)
        if weekday >= 5:  # 토요일(5), 일요일(6)
            return False

        # 장 운영 시간 체크
        market_start = datetime.strptime("08:00:00", "%H:%M:%S").time()
        market_end = datetime.strptime("18:00:00", "%H:%M:%S").time()

        return market_start <= current_time <= market_end

    def stop(self):
        """봇 정지"""
        self.is_running = False
        self.update_bot_status()
        self.add_trade_log("INFO", "KIS 자동매매 봇 정지")
        print("🛑 봇이 정지되었습니다")

if __name__ == "__main__":
    bot = KISBot()
    bot.start()