#!/usr/bin/env python3
"""
KIS 자동매매 봇 - 완전체 버전
- MVVM 패턴 + RSI/MACD 지표 계산 + Firebase 실시간 동기화
"""

import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from typing import Optional, List, Dict, Tuple

# Firebase 및 커스텀 모듈
import firebase_admin
from firebase_admin import credentials, firestore
from token_manager import TokenManager
from logger_system import UnifiedLogger
from stock_master import StockMaster

load_dotenv()


class KISApiClient:
    """KIS API 호출 담당 (Model) - 일봉 데이터 조회 추가"""

    def __init__(self, token_manager: TokenManager, account_no: str):
        self.token_manager = token_manager
        self.account_no = account_no
        self.app_key = os.getenv('KIS_APP_KEY')
        self.app_secret = os.getenv('KIS_APP_SECRET')
        self.base_url = "https://openapivts.koreainvestment.com:29443"

    def _get_headers(self, tr_id: str) -> Dict:
        """API 호출용 헤더 생성"""
        token = self.token_manager.get_token()
        if not token:
            raise Exception("토큰 획득 실패")

        return {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }

    def get_daily_price_history(self, stock_code: str, days: int = 30) -> Optional[pd.DataFrame]:
        """일봉 데이터 조회 (RSI/MACD 계산용) - 에러 상세 출력 추가"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        headers = self._get_headers("FHKST03010100")

        # 날짜 범위 설정
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0' and data.get('output2'):
                    # DataFrame 변환
                    df = pd.DataFrame(data['output2'])
                    df['date'] = pd.to_datetime(df['stck_bsop_date'])
                    df['close'] = df['stck_clpr'].astype(float)
                    df['high'] = df['stck_hgpr'].astype(float)
                    df['low'] = df['stck_lwpr'].astype(float)
                    df['volume'] = df['acml_vol'].astype(float)
                    df = df.sort_values('date')
                    return df[['date', 'close', 'high', 'low', 'volume']]
                else:
                    # API 에러 코드 상세 출력
                    print(f"❌ 일봉 API 에러 [{stock_code}]: {data.get('msg1', 'Unknown error')}")
            else:
                print(f"❌ HTTP {response.status_code} 에러 [{stock_code}]")
        except Exception as e:
            print(f"❌ 일봉 데이터 조회 예외 ({stock_code}): {e}")
        return None

    def get_stock_price(self, stock_code: str) -> Optional[Dict]:
        """개별 종목 현재가 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self._get_headers("FHKST01010100")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('rt_cd') == '0':
                        output = data.get('output', {})
                        return {
                            'code': stock_code,
                            'name': output.get('hts_kor_isnm', stock_code),
                            'current_price': float(output.get('stck_prpr', 0)),
                            'change_rate': float(output.get('prdy_ctrt', 0)),
                            'volume': int(output.get('acml_vol', 0))
                        }
                elif response.status_code == 500:
                    time.sleep(2 ** attempt)
                    continue
            except Exception as e:
                if attempt == 2:
                    print(f"❌ {stock_code} 조회 최종 실패: {e}")
                time.sleep(1)
        return None

    def get_volume_ranking(self) -> List[Dict]:
        """거래량 상위 종목 조회 (확장: 30개)"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
        headers = self._get_headers("FHPST01710000")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "0000000000",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": ""
        }

        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('rt_cd') == '0':
                        return data.get('output', [])[:30]  # 30개로 확장
                elif response.status_code == 500:
                    time.sleep(3)
                    continue
            except Exception as e:
                if attempt == 2:
                    print(f"❌ 거래량 순위 조회 최종 실패: {e}")
                time.sleep(2)
        return []

    def get_price_change_ranking(self) -> List[Dict]:
        """등락률 상위 종목 조회 (신규)"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
        headers = self._get_headers("FHPST01710000")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20172",  # 등락률 순위
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "0000000000",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": ""
        }

        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('rt_cd') == '0':
                        return data.get('output', [])[:30]  # 상위 30개
                elif response.status_code == 500:
                    time.sleep(3)
                    continue
            except Exception as e:
                if attempt == 2:
                    print(f"❌ 등락률 순위 조회 최종 실패: {e}")
                time.sleep(2)
        return []

    def get_portfolio(self) -> Tuple[List[Dict], float, float]:
        """포트폴리오 및 계좌 정보 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self._get_headers("VTTC8434R")
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
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    holdings = []
                    for item in data.get('output1', []):
                        if int(float(item.get('hldg_qty', 0))) > 0:
                            holdings.append({
                                'stock_code': item.get('pdno'),
                                'stock_name': item.get('prdt_name'),
                                'quantity': int(float(item.get('hldg_qty', 0))),
                                'buy_price': float(item.get('pchs_avg_pric', 0)),
                                'current_price': float(item.get('prpr', 0)),
                                'profit_loss': float(item.get('evlu_pfls_amt', 0)),
                                'profit_rate': float(item.get('evlu_pfls_rt', 0))
                            })

                    # 계좌 정보 추출
                    output2 = data.get('output2', [{}])[0]
                    cash = float(output2.get('dnca_tot_amt', 0))
                    total_assets = float(output2.get('tot_evlu_amt', 0))

                    return holdings, cash, total_assets
        except Exception as e:
            print(f"❌ 포트폴리오 조회 실패: {e}")
        return [], 0, 0

    def buy_stock(self, stock_code: str, quantity: int) -> bool:
        """매수 주문 (시장가)"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = self._get_headers("VTTC0802U")
        headers["content-type"] = "application/json; charset=utf-8"

        body = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('rt_cd') == '0'
        except Exception as e:
            print(f"❌ 매수 주문 실패: {e}")
        return False

    def sell_stock(self, stock_code: str, quantity: int) -> bool:
        """매도 주문 (시장가)"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = self._get_headers("VTTC0801U")
        headers["content-type"] = "application/json; charset=utf-8"

        body = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('rt_cd') == '0'
        except Exception as e:
            print(f"❌ 매도 주문 실패: {e}")
        return False


class TechnicalAnalyzer:
    """기술적 지표 계산 클래스"""

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
        """RSI (Relative Strength Index) 계산"""
        if df is None or len(df) < period + 1:
            print(f"  ⚠️ RSI 계산 불가: 데이터 부족 (받은 데이터: {len(df) if df is not None else 0}행)")
            return 50.0  # 기본값

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

    @staticmethod
    def calculate_macd(df: pd.DataFrame) -> Dict[str, float]:
        """MACD (Moving Average Convergence Divergence) 계산"""
        if df is None or len(df) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0}

        # 12일, 26일 EMA 계산
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()

        # MACD = 12일 EMA - 26일 EMA
        macd = ema12 - ema26

        # Signal = MACD의 9일 EMA
        signal = macd.ewm(span=9).mean()

        # Histogram = MACD - Signal
        histogram = macd - signal

        return {
            'macd': float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0,
            'signal': float(signal.iloc[-1]) if not pd.isna(signal.iloc[-1]) else 0,
            'histogram': float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0
        }

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20) -> Dict[str, float]:
        """볼린저 밴드 계산"""
        if df is None or len(df) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0}

        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        upper = sma + (std * 2)
        lower = sma - (std * 2)

        return {
            'upper': float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else 0,
            'middle': float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else 0,
            'lower': float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else 0
        }

    @staticmethod
    def calculate_mfi(df: pd.DataFrame, period: int = 14) -> float:
        """MFI (Money Flow Index) 계산"""
        if df is None or len(df) < period + 1:
            return 50.0

        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']

        # 상승/하락 판단
        positive_flow = pd.Series(0, index=df.index)
        negative_flow = pd.Series(0, index=df.index)

        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.iloc[i] = money_flow.iloc[i]
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                negative_flow.iloc[i] = money_flow.iloc[i]

        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()

        mfi_ratio = positive_mf / negative_mf
        mfi = 100 - (100 / (1 + mfi_ratio))

        return float(mfi.iloc[-1]) if not pd.isna(mfi.iloc[-1]) else 50.0


class TradingEngine:
    """트레이딩 로직 담당 (ViewModel 역할)"""

    def __init__(self):
        # 설정 로드
        self.kst = pytz.timezone('Asia/Seoul')
        self.logger = UnifiedLogger()

        # Firebase 초기화
        if not firebase_admin._apps:
            cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

        # 계좌 정보
        account_no = os.getenv('KIS_ACCOUNT_NUMBER')
        if '-' not in account_no:
            account_no = f"{account_no}-01"

        # 컴포넌트 초기화
        app_key = os.getenv('KIS_APP_KEY')
        app_secret = os.getenv('KIS_APP_SECRET')

        self.token_manager = TokenManager(app_key, app_secret)
        self.api_client = KISApiClient(self.token_manager, account_no)
        self.analyzer = TechnicalAnalyzer()
        self.stock_master = StockMaster()  # 종목명 마스터 추가

        # 트레이딩 설정
        self.buy_amount = 500000  # 종목당 50만원
        self.stop_loss_rate = -3.0  # 손절 -3%
        self.take_profit_rate = 5.0  # 익절 +5%

        # RSI 기준값
        self.rsi_oversold = 30  # 과매도
        self.rsi_overbought = 70  # 과매수

    def sync_portfolio_to_firebase(self, portfolio: List[Dict]):
        """포트폴리오를 Firebase에 동기화"""
        try:
            batch = self.db.batch()

            # 기존 포트폴리오 삭제
            existing_docs = self.db.collection('portfolio').stream()
            for doc in existing_docs:
                batch.delete(doc.reference)

            # 새 포트폴리오 추가
            for item in portfolio:
                doc_ref = self.db.collection('portfolio').document(item['stock_code'])
                data = {
                    'code': item['stock_code'],
                    'name': item['stock_name'],
                    'quantity': item['quantity'],
                    'buy_price': item['buy_price'],
                    'current_price': item['current_price'],
                    'profit_rate': item['profit_rate'],
                    'profit_amount': item.get('profit_loss', 0),
                    'total_value': item['current_price'] * item['quantity'],
                    'last_updated': firestore.SERVER_TIMESTAMP
                }
                batch.set(doc_ref, data)

            batch.commit()
            print("✅ 포트폴리오 Firebase 동기화 완료")
        except Exception as e:
            print(f"⚠️ Firebase 포트폴리오 동기화 실패: {e}")

    def sync_watchlist_to_firebase(self, watchlist: List[Dict]):
        """감시종목을 Firebase에 동기화 (RSI/MFI 포함)"""
        try:
            # market_scan/latest 업데이트
            doc_ref = self.db.collection('market_scan').document('latest')
            doc_ref.set({
                'stocks': watchlist,
                'scan_time': firestore.SERVER_TIMESTAMP,
                'last_updated': datetime.now(self.kst).isoformat()
            })

            # watchlist 컬렉션 업데이트
            batch = self.db.batch()

            existing_docs = self.db.collection('watchlist').stream()
            for doc in existing_docs:
                batch.delete(doc.reference)

            for item in watchlist:
                doc_ref = self.db.collection('watchlist').document(item['code'])
                batch.set(doc_ref, {
                    **item,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })

            batch.commit()
            print(f"✅ 감시종목 {len(watchlist)}개 Firebase 동기화 완료 (RSI 포함)")
        except Exception as e:
            print(f"⚠️ Firebase 감시종목 동기화 실패: {e}")

    def sync_account_to_firebase(self, cash_balance: float, total_assets: float):
        """계좌 정보를 Firebase에 동기화"""
        try:
            doc_ref = self.db.collection('account').document('summary')
            doc_ref.set({
                'cash_balance': cash_balance,
                'total_assets': total_assets,
                'last_updated': firestore.SERVER_TIMESTAMP
            }, merge=True)
            print(f"✅ 계좌 정보 동기화: 현금 {cash_balance:,.0f}원, 총자산 {total_assets:,.0f}원")
        except Exception as e:
            print(f"⚠️ Firebase 계좌 동기화 실패: {e}")

    def analyze_stock_with_indicators(self, stock_code: str, stock_info: Dict) -> Dict:
        """종목에 대한 기술적 지표 계산"""
        # 일봉 데이터 조회
        df = self.api_client.get_daily_price_history(stock_code)

        # 기술적 지표 계산
        rsi = self.analyzer.calculate_rsi(df)
        mfi = self.analyzer.calculate_mfi(df)
        macd = self.analyzer.calculate_macd(df)
        bollinger = self.analyzer.calculate_bollinger_bands(df)

        # 매수 신호 판단
        buy_signal = False
        signal_reasons = []

        # RSI 과매도 구간 (30 이하)
        if rsi < self.rsi_oversold:
            buy_signal = True
            signal_reasons.append(f"RSI 과매도({rsi:.1f})")

        # MACD 골든크로스
        if macd['histogram'] > 0 and macd['macd'] > macd['signal']:
            buy_signal = True
            signal_reasons.append("MACD 골든크로스")

        # 볼린저 밴드 하단 돌파
        if stock_info['current_price'] < bollinger['lower']:
            buy_signal = True
            signal_reasons.append("볼린저 하단 돌파")

        # 거래량 급증 + 상승
        if stock_info['change_rate'] > 3.0 and stock_info['volume'] > 100000:
            if rsi < self.rsi_overbought:  # RSI 과매수 구간이 아닐 때만
                buy_signal = True
                signal_reasons.append(f"거래량 급증({stock_info['volume']:,})")

        return {
            **stock_info,
            'rsi': rsi,
            'mfi': mfi,
            'macd': macd['macd'],
            'macd_signal': macd['signal'],
            'macd_histogram': macd['histogram'],
            'bollinger_upper': bollinger['upper'],
            'bollinger_middle': bollinger['middle'],
            'bollinger_lower': bollinger['lower'],
            'buy_signal': buy_signal,
            'signal_reasons': ', '.join(signal_reasons) if signal_reasons else '없음'
        }

    def find_buy_opportunities(self) -> List[Dict]:
        """매수 기회 탐색 - Funnel Strategy 적용"""
        print("\n🔍 확장된 매수 기회 탐색 (Funnel Strategy)...")
        print("  📊 1단계: 후보군 수집 (거래량 + 등락률)")

        # 1단계: 넓게 후보군 수집
        volume_stocks = self.api_client.get_volume_ranking()  # 거래량 상위 30개
        price_change_stocks = self.api_client.get_price_change_ranking()  # 등락률 상위 30개

        # 종목 코드 중복 제거를 위한 dict 사용
        candidates = {}

        # 거래량 상위 종목 추가
        for stock in volume_stocks:
            code = stock.get('mksc_shrn_iscd', '').zfill(6)
            if code and code != '000000':
                candidates[code] = {
                    'code': code,
                    'name': self.stock_master.get_name(code),  # 마스터에서 종목명 100% 보장
                    'from': 'volume'
                }

        # 등락률 상위 종목 추가 (중복 제거)
        for stock in price_change_stocks:
            code = stock.get('mksc_shrn_iscd', '').zfill(6)
            if code and code != '000000':
                if code not in candidates:
                    candidates[code] = {
                        'code': code,
                        'name': self.stock_master.get_name(code),
                        'from': 'price_change'
                    }
                else:
                    candidates[code]['from'] = 'both'  # 양쪽 모두 포함

        print(f"  ✅ 1차 후보군: {len(candidates)}개 종목 수집")

        # 2단계: 메모리 내 빠른 필터링
        print("  🔨 2단계: 기본 필터링 (가격/거래량)")
        filtered_candidates = []

        for code, info in candidates.items():
            # 현재가 조회
            price_data = self.api_client.get_stock_price(code)
            if not price_data:
                continue

            # 기본 필터 조건
            if price_data['current_price'] < 1000:  # 1000원 미만 제외
                continue
            if price_data['volume'] < 10000:  # 거래량 10000주 미만 제외
                continue
            if abs(price_data['change_rate']) > 29:  # 상한가/하한가 제외
                continue

            # 필터 통과한 종목 저장
            filtered_candidates.append({
                **info,
                **price_data
            })

            # API 부하 방지
            time.sleep(0.1)

        print(f"  ✅ 2차 필터 통과: {len(filtered_candidates)}개 종목")

        # 3단계: 기술적 지표 분석 (RSI/MACD 등)
        print("  📈 3단계: 기술적 지표 분석 (RSI/MACD/MFI)")
        opportunities = []

        # 최대 20개 종목만 상세 분석 (API 부하 고려)
        for i, candidate in enumerate(filtered_candidates[:20], 1):
            print(f"    [{i}/{min(20, len(filtered_candidates))}] {candidate['name']} 분석 중...")

            # 기술적 지표 계산
            analyzed_data = self.analyze_stock_with_indicators(candidate['code'], candidate)

            # 모든 분석 데이터 추가 (매수 신호 여부와 관계없이)
            analyzed_data['from_source'] = candidate['from']
            opportunities.append(analyzed_data)

            if analyzed_data['buy_signal']:
                print(f"      💡 매수 신호! RSI: {analyzed_data['rsi']:.1f}, 이유: {analyzed_data['signal_reasons']}")
            else:
                print(f"      ⚪ 신호 없음 (RSI: {analyzed_data['rsi']:.1f})")

            time.sleep(0.2)  # API 부하 방지

        # 매수 신호가 있는 종목 우선 정렬
        opportunities.sort(key=lambda x: (x['buy_signal'], x.get('rsi', 50)), reverse=False)

        buy_signals = [x for x in opportunities if x['buy_signal']]
        print(f"\n📊 분석 완료: {len(buy_signals)}개 매수 신호 / {len(opportunities)}개 분석")

        return opportunities

    def check_sell_conditions(self, portfolio: List[Dict]) -> List[Dict]:
        """매도 조건 체크 (RSI 포함)"""
        print("📊 포트폴리오 매도 조건 체크 중...")

        sell_list = []

        for holding in portfolio:
            stock_code = holding['stock_code']
            profit_rate = holding['profit_rate']

            # 일봉 데이터로 RSI 계산
            df = self.api_client.get_daily_price_history(stock_code)
            rsi = self.analyzer.calculate_rsi(df)

            print(f"  📈 {holding['stock_name']}: 수익률 {profit_rate:+.2f}%, RSI {rsi:.1f}")

            sell_reason = None

            # 손절 조건
            if profit_rate <= self.stop_loss_rate:
                sell_reason = f'손절 ({profit_rate:.2f}%)'
                print(f"    🔴 손절 대상")

            # 익절 조건
            elif profit_rate >= self.take_profit_rate:
                sell_reason = f'익절 ({profit_rate:.2f}%)'
                print(f"    🟢 익절 대상")

            # RSI 과매수 구간에서 추가 매도 검토
            elif rsi > self.rsi_overbought and profit_rate > 0:
                sell_reason = f'RSI 과매수 익절 ({rsi:.1f})'
                print(f"    🟡 RSI 과매수 매도 대상")

            if sell_reason:
                holding['reason'] = sell_reason
                holding['rsi'] = rsi
                sell_list.append(holding)

        return sell_list

    def execute_trades(self):
        """매매 실행 및 Firebase 동기화"""
        now = datetime.now(self.kst)
        print(f"\n{'='*60}")
        print(f"🤖 자동매매 실행 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        try:
            # 1. 포트폴리오 조회 및 Firebase 동기화
            portfolio, cash, total_assets = self.api_client.get_portfolio()
            if portfolio:
                self.sync_portfolio_to_firebase(portfolio)
            self.sync_account_to_firebase(cash, total_assets)

            # 2. 매도 조건 체크 및 실행
            sell_opportunities = self.check_sell_conditions(portfolio)
            for item in sell_opportunities:
                print(f"\n💰 {item['reason']} 매도: {item['stock_name']}")
                success = self.api_client.sell_stock(
                    item['stock_code'],
                    item['quantity']
                )
                if success:
                    print(f"  ✅ 매도 완료: {item['quantity']}주")
                    self.logger.trade(f"매도 완료: {item['stock_name']}", item)
                else:
                    print(f"  ❌ 매도 실패")
                time.sleep(1)

            # 3. 매수 기회 탐색 및 Firebase 동기화
            buy_opportunities = self.find_buy_opportunities()

            # 데이터가 없어도 강제로 Firebase 동기화 (3일 전 데이터 제거)
            self.sync_watchlist_to_firebase(buy_opportunities if buy_opportunities else [])
        except Exception as e:
            self.logger.error(f"매매 실행 중 오류: {e}")
            # 오류가 나도 빈 데이터로 Firebase 동기화 (화석 데이터 제거)
            self.sync_watchlist_to_firebase([])

        # 4. 매수 실행
        portfolio_codes = [p['stock_code'] for p in portfolio]

        # 매수 신호가 있는 종목만 필터링
        buy_signals = [x for x in buy_opportunities if x['buy_signal']]

        for item in buy_signals[:2]:  # 최대 2종목
            # 이미 보유 중인 종목은 제외
            if item['code'] in portfolio_codes:
                continue

            # 잔고 확인
            if cash < self.buy_amount:
                print(f"⚠️ 잔고 부족: {cash:,.0f}원 < {self.buy_amount:,.0f}원")
                break

            quantity = int(self.buy_amount / item['current_price'])
            if quantity > 0:
                print(f"\n💸 매수 실행: {item['name']} - {quantity}주")
                print(f"   출처: {item.get('from_source', 'unknown')}")
                print(f"   RSI: {item['rsi']:.1f}, MFI: {item['mfi']:.1f}")
                print(f"   신호: {item['signal_reasons']}")

                success = self.api_client.buy_stock(
                    item['code'],
                    quantity
                )
                if success:
                    print(f"  ✅ 매수 완료: {quantity}주 @ {item['current_price']:,.0f}원")
                    cash -= self.buy_amount  # 잔고 차감
                    self.logger.trade(f"매수 완료: {item['name']}", {
                        'code': item['code'],
                        'quantity': quantity,
                        'price': item['current_price'],
                        'rsi': item['rsi'],
                        'signal': item['signal_reasons'],
                        'source': item.get('from_source')
                    })
                else:
                    print(f"  ❌ 매수 실패")
                time.sleep(1)

        print(f"\n✅ 매매 사이클 완료")

    def run(self):
        """메인 실행 루프"""
        self.logger.system("🚀 자동매매 봇 시작 (Funnel Strategy + RSI/MFI)")
        print("📋 스캔 전략: 거래량 상위 30 + 등락률 상위 30 → 기술적 분석")
        print("📋 매수 조건: RSI < 30 또는 MACD 골든크로스 또는 거래량 급증")
        print("📋 매도 조건: 손절 -3%, 익절 +5%, RSI > 70")
        print("-" * 60)

        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                print(f"\n🔄 사이클 #{cycle_count}")

                self.execute_trades()

                # 5분 대기
                print("⏰ 5분 대기 중...")
                time.sleep(300)

            except KeyboardInterrupt:
                print("\n🛑 자동매매 봇 종료")
                self.logger.system("봇 정상 종료")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                self.logger.error(f"치명적 오류: {e}")
                time.sleep(60)


def main():
    """엔트리 포인트"""
    engine = TradingEngine()
    engine.run()


if __name__ == "__main__":
    main()