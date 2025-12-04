"""
KIS API를 사용한 동적 시장 스캐너
실시간으로 주도주를 발굴하는 시스템
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

class MarketScanner:
    def __init__(self, app_key: str, app_secret: str):
        """시장 스캐너 초기화"""
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://openapivts.koreainvestment.com:29443"
        self.access_token = None
        self.token_expires_at = 0

    def get_access_token(self) -> str:
        """접속 토큰 발급"""
        current_time = time.time()

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
            self.token_expires_at = current_time + (23 * 60 * 60)

            return self.access_token

        except Exception as e:
            print(f"❌ 토큰 발급 실패: {e}")
            return None

    def get_volume_rank(self) -> List[str]:
        """거래량 상위 종목 조회"""
        token = self.get_access_token()
        if not token:
            return []

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHPST01710000"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") == "0":
                output = data.get("output", [])
                stock_codes = []
                for item in output[:30]:  # 상위 30개
                    code = item.get("stck_shrn_iscd")
                    if code and len(code) == 6:
                        stock_codes.append(code)

                print(f"📊 거래량 상위 {len(stock_codes)}개 종목 발견")
                return stock_codes

        except Exception as e:
            print(f"❌ 거래량 순위 조회 실패: {e}")

        return []

    def get_price_change_rank(self) -> List[str]:
        """등락률 상위 종목 조회"""
        token = self.get_access_token()
        if not token:
            return []

        url = f"{self.base_url}/uapi/domestic-stock/v1/ranking/fluctuation"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHPST01700000"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20170",
            "FID_INPUT_ISCD": "0000",
            "FID_RANK_SORT_CLS_CODE": "0",
            "FID_INPUT_CNT_1": "0",
            "FID_PAGING_KEY_100": "",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_DIV_CLS_CODE": "0",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") == "0":
                output = data.get("output", [])
                stock_codes = []
                for item in output[:30]:  # 상위 30개
                    code = item.get("stck_shrn_iscd")
                    change_rate = float(item.get("prdy_ctrt", 0))
                    # 급등주 필터 (5% ~ 20% 상승)
                    if code and len(code) == 6 and 5 <= change_rate <= 20:
                        stock_codes.append(code)

                print(f"📈 등락률 상위 {len(stock_codes)}개 종목 발견")
                return stock_codes

        except Exception as e:
            print(f"❌ 등락률 순위 조회 실패: {e}")

        return []

    def get_foreign_institution_buy(self, stock_code: str) -> Dict:
        """외국인/기관 매매 동향 조회 (5일간)"""
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010900"
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

                # 5일 누적 매매 (외국인 + 기관 합산)
                foreign_net_buy = 0
                institution_net_buy = 0

                # 개인: prsn, 외국인: frgn, 기관: orgn
                for i in range(1, 6):  # 최근 5일
                    foreign_net_buy += float(output.get(f"frgn_ntby_qty", 0))
                    institution_net_buy += float(output.get(f"orgn_ntby_qty", 0))

                return {
                    "foreign_net_buy_5d": foreign_net_buy,
                    "institution_net_buy_5d": institution_net_buy,
                    "smart_money_net_buy_5d": foreign_net_buy + institution_net_buy
                }

        except Exception as e:
            print(f"⚠️ 투자자 동향 조회 실패 ({stock_code}): {e}")

        return None

    def get_daily_candles(self, stock_code: str, period: int = 150) -> pd.DataFrame:
        """일봉 데이터 조회"""
        token = self.get_access_token()
        if not token:
            return None

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

        except Exception as e:
            print(f"⚠️ 일봉 데이터 조회 실패 ({stock_code}): {e}")

        return None

    def calculate_advanced_technicals(self, df: pd.DataFrame) -> Dict:
        """고급 기술적 지표 계산"""
        if df is None or len(df) < 120:
            return None

        # 기본 이동평균선
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        df['MA120'] = df['close'].rolling(window=120).mean()

        # 볼린저밴드
        df['std'] = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['MA20'] + (df['std'] * 2)
        df['BB_lower'] = df['MA20'] - (df['std'] * 2)

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MFI
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        raw_money_flow = typical_price * df['volume']
        mf_delta = typical_price.diff()
        positive_mf = raw_money_flow.where(mf_delta > 0, 0).rolling(window=14).sum()
        negative_mf = raw_money_flow.where(mf_delta < 0, 0).rolling(window=14).sum()
        mf_ratio = positive_mf / negative_mf
        df['MFI'] = 100 - (100 / (1 + mf_ratio))

        # ADX (Average Directional Index)
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()
        df['plus_dm'] = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        df['minus_dm'] = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        df['atr'] = df['tr'].rolling(window=14).mean()
        df['plus_di'] = 100 * (df['plus_dm'].rolling(window=14).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(window=14).mean() / df['atr'])
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['ADX'] = df['dx'].rolling(window=14).mean()

        # OBV (On-Balance Volume)
        df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        df['OBV_MA20'] = df['OBV'].rolling(window=20).mean()

        # Stochastic Slow
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        df['stoch_slow_k'] = df['stoch_d']  # Slow %K = Fast %D
        df['stoch_slow_d'] = df['stoch_slow_k'].rolling(window=3).mean()

        # 최신 값 반환
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        return {
            "current_price": latest['close'],
            "ma20": latest['MA20'],
            "ma60": latest['MA60'],
            "ma120": latest['MA120'],
            "bb_upper": latest['BB_upper'],
            "bb_lower": latest['BB_lower'],
            "rsi": latest['RSI'],
            "mfi": latest['MFI'],
            "adx": latest['ADX'],
            "obv": latest['OBV'],
            "obv_ma20": latest['OBV_MA20'],
            "stoch_slow_k": latest['stoch_slow_k'],
            "stoch_slow_d": latest['stoch_slow_d'],
            "prev_stoch_slow_k": prev['stoch_slow_k'],
            "prev_stoch_slow_d": prev['stoch_slow_d'],
            "prev_close": prev['close'],
            "prev_low": prev['low'],
            "bb_position": (latest['close'] - latest['BB_lower']) / (latest['BB_upper'] - latest['BB_lower'])
        }

    def check_universe_filter(self, indicators: Dict, smart_money: Dict) -> bool:
        """종목 필터링 조건 확인 (4가지 조건 모두 만족)"""
        if not indicators or not smart_money:
            return False

        # 1. Trend Strength (추세 강도)
        trend_ok = (indicators['adx'] > 25 and
                   indicators['current_price'] > indicators['ma60'] and
                   indicators['current_price'] > indicators['ma120'])

        # 2. Smart Money (수급)
        smart_money_ok = smart_money.get('smart_money_net_buy_5d', 0) > 0

        # 3. Accumulation (매집)
        accumulation_ok = indicators['obv'] > indicators['obv_ma20']

        # 4. Fundamentals (시가총액은 별도 체크 필요)
        # 여기서는 가격 필터로 대체 (5,000원 이상)
        fundamentals_ok = indicators['current_price'] >= 5000

        return trend_ok and smart_money_ok and accumulation_ok and fundamentals_ok

    def check_buy_signal(self, indicators: Dict) -> Tuple[bool, str]:
        """매수 신호 확인 (하나라도 만족)"""
        if not indicators:
            return False, ""

        reasons = []

        # 1. MFI Divergence
        if indicators['mfi'] < 20:
            reasons.append("MFI 과매도")

        # 2. Stochastic Golden Cross
        if (indicators['prev_stoch_slow_k'] <= indicators['prev_stoch_slow_d'] and
            indicators['stoch_slow_k'] > indicators['stoch_slow_d']):
            if indicators['stoch_slow_k'] < 20:
                reasons.append("스토캐스틱 골든크로스(과매도권)")
            else:
                reasons.append("스토캐스틱 골든크로스")

        # 3. BB Re-entry (볼린저밴드 재진입)
        if (indicators['prev_close'] < indicators['bb_lower'] and
            indicators['current_price'] > indicators['bb_lower'] and
            indicators['current_price'] > indicators['prev_close']):
            reasons.append("볼린저밴드 하단 반등")

        return len(reasons) > 0, ", ".join(reasons)

    def scan_market(self) -> List[Dict]:
        """시장 스캔 및 주도주 발굴"""
        print("\n🔍 시장 스캔 시작...")

        # 1. 후보군 수집
        candidates = set()

        # 거래량 상위
        volume_leaders = self.get_volume_rank()
        candidates.update(volume_leaders)
        time.sleep(0.5)

        # 등락률 상위
        price_gainers = self.get_price_change_rank()
        candidates.update(price_gainers)
        time.sleep(0.5)

        print(f"\n📋 총 {len(candidates)}개 후보 종목 수집 완료")

        # 2. 상세 분석
        qualified_stocks = []

        for i, stock_code in enumerate(candidates, 1):
            print(f"\n분석 중... [{i}/{len(candidates)}] {stock_code}")

            try:
                # 일봉 데이터 가져오기
                df = self.get_daily_candles(stock_code)
                if df is None or len(df) < 120:
                    continue

                # 기술적 지표 계산
                indicators = self.calculate_advanced_technicals(df)
                if not indicators:
                    continue

                # 수급 데이터 가져오기
                smart_money = self.get_foreign_institution_buy(stock_code)

                # 필터 조건 확인
                if self.check_universe_filter(indicators, smart_money):
                    # 매수 신호 확인
                    buy_signal, buy_reason = self.check_buy_signal(indicators)

                    stock_info = {
                        "code": stock_code,
                        "price": indicators['current_price'],
                        "rsi": indicators['rsi'],
                        "mfi": indicators['mfi'],
                        "adx": indicators['adx'],
                        "ma120": indicators['ma120'],
                        "bb_upper": indicators['bb_upper'],
                        "bb_lower": indicators['bb_lower'],
                        "obv_signal": indicators['obv'] > indicators['obv_ma20'],
                        "foreign_net_buy": smart_money.get('foreign_net_buy_5d', 0) if smart_money else 0,
                        "institution_net_buy": smart_money.get('institution_net_buy_5d', 0) if smart_money else 0,
                        "buy_signal": buy_signal,
                        "buy_reason": buy_reason
                    }

                    qualified_stocks.append(stock_info)
                    print(f"  ✅ 조건 충족! RSI:{indicators['rsi']:.1f}, ADX:{indicators['adx']:.1f}, 매수신호:{buy_signal}")

                time.sleep(0.3)  # API 제한 고려

            except Exception as e:
                print(f"  ⚠️ 분석 실패: {e}")
                continue

        print(f"\n✨ 최종 선정: {len(qualified_stocks)}개 종목")

        # 매수 신호가 있는 종목을 우선 정렬
        qualified_stocks.sort(key=lambda x: (x['buy_signal'], -x['adx']), reverse=True)

        return qualified_stocks[:10]  # 최대 10개 종목