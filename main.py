#!/usr/bin/env python3
"""
KIS 자동매매 봇 - MVVM 패턴 적용
- Model: TokenManager, KISApiClient (데이터 및 API)
- ViewModel: TradingEngine (매매 로직 판단)
- View: Logger, Firebase (상태 표시)
"""

import os
import time
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
from typing import Optional, List, Dict

# 기존 모듈들 재사용 (중복 제거!)
from token_manager import TokenManager
from logger_system import UnifiedLogger

load_dotenv()


class KISApiClient:
    """KIS API 호출 담당 (Model 역할) - 단일 책임 원칙"""

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

    def get_stock_price(self, stock_code: str) -> Optional[Dict]:
        """개별 종목 현재가 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self._get_headers("FHKST01010100")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        # 재시도 로직 (3회)
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
                    time.sleep(2 ** attempt)  # 지수 백오프
                    continue
            except Exception as e:
                if attempt == 2:
                    print(f"❌ {stock_code} 조회 최종 실패: {e}")
                time.sleep(1)
        return None

    def get_volume_ranking(self) -> List[Dict]:
        """거래량 상위 종목 조회"""
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
                        return data.get('output', [])[:20]
                elif response.status_code == 500:
                    time.sleep(3)
                    continue
            except Exception as e:
                if attempt == 2:
                    print(f"❌ 거래량 순위 조회 최종 실패: {e}")
                time.sleep(2)
        return []

    def get_portfolio(self) -> List[Dict]:
        """포트폴리오 조회"""
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
                    return holdings
        except Exception as e:
            print(f"❌ 포트폴리오 조회 실패: {e}")
        return []

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


class TradingEngine:
    """트레이딩 로직 담당 (ViewModel 역할)"""

    def __init__(self):
        # 설정 로드
        self.kst = pytz.timezone('Asia/Seoul')
        self.logger = UnifiedLogger()

        # 계좌 정보
        account_no = os.getenv('KIS_ACCOUNT_NUMBER')
        if '-' not in account_no:
            account_no = f"{account_no}-01"

        # 컴포넌트 초기화 (의존성 주입)
        app_key = os.getenv('KIS_APP_KEY')
        app_secret = os.getenv('KIS_APP_SECRET')

        # TokenManager 사용! (파일 직접 접근 X)
        self.token_manager = TokenManager(app_key, app_secret)

        # API 클라이언트 생성
        self.api_client = KISApiClient(self.token_manager, account_no)

        # 트레이딩 설정
        self.buy_amount = 500000  # 종목당 50만원
        self.stop_loss_rate = -3.0  # 손절 -3%
        self.take_profit_rate = 5.0  # 익절 +5%

    def find_buy_opportunities(self) -> List[Dict]:
        """매수 기회 탐색"""
        print("🔍 매수 기회 탐색 중...")

        # 거래량 상위 종목 조회
        volume_stocks = self.api_client.get_volume_ranking()
        if not volume_stocks:
            print("❌ 거래량 데이터 없음")
            return []

        opportunities = []
        for stock in volume_stocks[:10]:  # TOP 10만 체크
            stock_code = stock.get('mksc_shrn_iscd', '').zfill(6)
            if not stock_code or stock_code == '000000':
                continue

            # 현재가 조회
            price_data = self.api_client.get_stock_price(stock_code)
            if price_data:
                # 매수 조건: 3%+ 상승, 10만주+ 거래, 1000원+ 가격
                if (price_data['change_rate'] > 3.0 and
                    price_data['volume'] > 100000 and
                    price_data['current_price'] >= 1000):

                    opportunities.append(price_data)
                    print(f"  💡 발견: {price_data['name']} - "
                          f"{price_data['change_rate']:+.1f}%, "
                          f"{price_data['volume']:,}주")

            time.sleep(0.2)  # API 부하 방지

        return opportunities

    def check_sell_conditions(self) -> List[Dict]:
        """매도 조건 체크"""
        print("📊 포트폴리오 체크 중...")

        portfolio = self.api_client.get_portfolio()
        sell_list = []

        for holding in portfolio:
            profit_rate = holding['profit_rate']
            print(f"  📈 {holding['stock_name']}: {profit_rate:+.2f}%")

            # 손절 조건
            if profit_rate <= self.stop_loss_rate:
                holding['reason'] = f'손절 ({profit_rate:.2f}%)'
                sell_list.append(holding)
                print(f"    🔴 손절 대상")

            # 익절 조건
            elif profit_rate >= self.take_profit_rate:
                holding['reason'] = f'익절 ({profit_rate:.2f}%)'
                sell_list.append(holding)
                print(f"    🟢 익절 대상")

        return sell_list

    def execute_trades(self):
        """매매 실행"""
        now = datetime.now(self.kst)
        print(f"\n{'='*60}")
        print(f"🤖 자동매매 실행 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # 1. 매도 먼저 실행
        sell_opportunities = self.check_sell_conditions()
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

        # 2. 매수 실행
        buy_opportunities = self.find_buy_opportunities()
        for item in buy_opportunities[:2]:  # 최대 2종목
            quantity = int(self.buy_amount / item['current_price'])
            if quantity > 0:
                print(f"\n💸 매수 실행: {item['name']} - {quantity}주")
                success = self.api_client.buy_stock(
                    item['code'],
                    quantity
                )
                if success:
                    print(f"  ✅ 매수 완료: {quantity}주 @ {item['current_price']:,.0f}원")
                    self.logger.trade(f"매수 완료: {item['name']}", {
                        'code': item['code'],
                        'quantity': quantity,
                        'price': item['current_price']
                    })
                else:
                    print(f"  ❌ 매수 실패")
                time.sleep(1)

        print(f"\n✅ 매매 사이클 완료")

    def run(self):
        """메인 실행 루프"""
        self.logger.system("🚀 자동매매 봇 시작 (MVVM 패턴)")
        print("📋 매수 조건: 3%+ 상승, 10만주+ 거래, 1000원+ 가격")
        print("📋 매도 조건: 손절 -3%, 익절 +5%")
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