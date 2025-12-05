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
    def __init__(self, app_key: str, app_secret: str, token_provider=None):
        """시장 스캐너 초기화"""
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://openapivts.koreainvestment.com:29443"
        self.token_provider = token_provider  # 외부 토큰 제공자
        self.access_token = None
        self.token_expires_at = 0
        self.last_token_attempt = 0

    def get_access_token(self) -> str:
        """접속 토큰 발급 (외부 token_provider 사용 우선)"""
        # 외부 토큰 제공자가 있으면 사용
        if self.token_provider:
            return self.token_provider()

        # 외부 토큰 제공자가 없으면 자체 토큰 관리
        current_time = time.time()

        if self.access_token and current_time < self.token_expires_at:
            return self.access_token

        # 1분 제한 체크 (마지막 시도로부터 60초 경과 확인)
        time_since_last_attempt = current_time - self.last_token_attempt
        if time_since_last_attempt < 60:
            wait_time = 60 - time_since_last_attempt
            print(f"⏳ MarketScanner 토큰 발급 제한: {wait_time:.0f}초 후 재시도 가능")
            return None

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        # 토큰 시도 시간 기록
        self.last_token_attempt = current_time

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
            "FID_TRGT_CLS_CODE": "",         # 빈 문자열로 변경
            "FID_TRGT_EXLS_CLS_CODE": "",    # 빈 문자열로 변경
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": ""           # 날짜 필드 추가
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            print(f"🔍 거래량 조회 응답: rt_cd={data.get('rt_cd')}, msg_cd={data.get('msg_cd')}, msg1={data.get('msg1')}")

            # rt_cd가 "0" 또는 빈 문자열인 경우 모두 처리
            if data.get("rt_cd") in ["0", ""]:
                output = data.get("output", [])
                print(f"📋 응답 데이터 개수: {len(output)}")
                if len(output) == 0:
                    print(f"⚠️ 빈 응답 - 전체 응답: {data}")

                stock_codes = []
                for item in output[:30]:  # 상위 30개
                    # 거래량 API는 mksc_shrn_iscd 필드 사용
                    code = item.get("mksc_shrn_iscd")
                    if code and len(code) == 6:
                        stock_codes.append(code)

                print(f"📊 거래량 상위 {len(stock_codes)}개 종목 발견")
                return stock_codes
            else:
                print(f"❌ API 에러 응답: {data}")

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
            if data.get("rt_cd") in ["0", ""]:  # 빈 문자열도 처리
                output = data.get("output", [])

                # API 응답이 리스트인 경우 (일별 데이터)
                if isinstance(output, list) and len(output) > 0:
                    foreign_net_buy = 0
                    institution_net_buy = 0

                    # 최근 5일간 데이터 합산 (최대 5개)
                    for item in output[:5]:
                        # 각 일자별 외국인/기관 순매수량
                        foreign_net_buy += float(item.get("frgn_ntby_qty", 0))
                        institution_net_buy += float(item.get("orgn_ntby_qty", 0))

                # API 응답이 딕셔너리인 경우 (단일 데이터)
                elif isinstance(output, dict):
                    # 당일 데이터만 사용
                    foreign_net_buy = float(output.get("frgn_ntby_qty", 0))
                    institution_net_buy = float(output.get("orgn_ntby_qty", 0))
                else:
                    # 데이터가 없는 경우 기본값 반환
                    foreign_net_buy = 0
                    institution_net_buy = 0

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
        start_date = (datetime.now() - timedelta(days=150)).strftime('%Y%m%d')

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
        df['MA5'] = df['close'].rolling(window=5).mean()  # 5일 이평선 추가
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
            "ma5": latest['MA5'],  # 5일 이평선 추가
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
            "prev_ma5": prev['MA5'] if len(df) > 1 else latest['MA5'],  # 전일 5일 이평선
            "bb_position": (latest['close'] - latest['BB_lower']) / (latest['BB_upper'] - latest['BB_lower'])
        }

    def check_universe_filter(self, indicators: Dict, smart_money: Dict) -> bool:
        """종목 필터링 조건 확인 - 눌림목 매매 전략 (추세는 필수 + 나머지 1개)"""
        if not indicators or not smart_money:
            return False

        # 1. Trend Strength (추세 강도) - 필수 조건, 완화됨
        # ADX 20 이상이고, 20일선 또는 60일선 위에 있으면 OK
        trend_ok = (indicators['adx'] > 20 and
                   (indicators['current_price'] > indicators['ma20'] or
                    indicators['current_price'] > indicators['ma60']))

        # 추세 조건이 없으면 즉시 False 반환
        if not trend_ok:
            return False

        # 나머지 조건들 체크 (최소 1개 이상 만족 필요)
        other_conditions = 0

        # 2. Smart Money (수급) - 완화됨
        # 외국인이나 기관 중 하나라도 순매수면 OK
        foreign_buy = smart_money.get('foreign_net_buy_5d', 0)
        institution_buy = smart_money.get('institution_net_buy_5d', 0)
        smart_money_ok = (foreign_buy > 0 or institution_buy > 0 or
                         (foreign_buy + institution_buy) > 0)
        if smart_money_ok:
            other_conditions += 1

        # 3. Accumulation (매집)
        accumulation_ok = indicators['obv'] > indicators['obv_ma20']
        if accumulation_ok:
            other_conditions += 1

        # 4. Fundamentals (가격 필터 - 500원으로 완화)
        fundamentals_ok = indicators['current_price'] >= 500
        if fundamentals_ok:
            other_conditions += 1

        # 추세 조건 만족 + 나머지 중 최소 1개 만족
        return other_conditions >= 1

    def check_buy_signal(self, indicators: Dict) -> Tuple[bool, str]:
        """매수 신호 확인 - 눌림목 매매 (반등의 기미 포착)"""
        if not indicators:
            return False, ""

        reasons = []

        # 1. MFI 과매도 - 기준 완화 (20 → 30)
        if indicators['mfi'] < 30:
            reasons.append("MFI 과매도 (<30)")

        # 2. RSI 과매도 신호 추가
        if indicators['rsi'] < 35:
            reasons.append("RSI 과매도 (<35)")

        # 3. Stochastic Golden Cross - 범위 확대 (20 → 40)
        if (indicators['prev_stoch_slow_k'] <= indicators['prev_stoch_slow_d'] and
            indicators['stoch_slow_k'] > indicators['stoch_slow_d']):
            if indicators['stoch_slow_k'] < 40:  # 20 → 40으로 완화
                reasons.append("스토캐스틱 골든크로스(눌림목)")
            else:
                reasons.append("스토캐스틱 골든크로스")

        # 4. BB Re-entry (볼린저밴드 재진입)
        if (indicators['prev_close'] < indicators['bb_lower'] and
            indicators['current_price'] > indicators['bb_lower'] and
            indicators['current_price'] > indicators['prev_close']):
            reasons.append("볼린저밴드 하단 반등")

        # 5. 5일 이평선 돌파 신호 추가 (중요!)
        if (indicators.get('prev_close', 0) < indicators.get('prev_ma5', 0) and
            indicators['current_price'] > indicators.get('ma5', 0)):
            reasons.append("5일선 돌파 (단기 반등)")

        # 6. 5일선 지지 확인 (추가 신호)
        if (abs(indicators['current_price'] - indicators.get('ma5', 0)) / indicators['current_price'] < 0.01 and
            indicators['current_price'] > indicators.get('prev_close', 0)):
            reasons.append("5일선 지지 후 상승")

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