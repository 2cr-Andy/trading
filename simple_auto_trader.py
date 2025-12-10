#!/usr/bin/env python3
"""진짜 자동매매 봇 - 조건 맞으면 사고팔기"""

import os
import json
import requests
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

class SimpleAutoTrader:
    def __init__(self):
        self.account_no = os.getenv('KIS_ACCOUNT_NUMBER')
        if '-' not in self.account_no:
            self.account_no = f"{self.account_no}-01"

    def get_access_token(self):
        """토큰 가져오기"""
        try:
            with open('kis_token.json', 'r') as f:
                token_data = json.load(f)
            return token_data.get('token')
        except:
            return None

    def get_stock_price(self, stock_code):
        """개별 종목 현재가 조회 (재시도 로직 포함)"""
        token = self.get_access_token()
        if not token:
            return None

        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "FHKST01010100",
            "custtype": "P"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        # 3번까지 재시도
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('rt_cd') == '0':
                        output = data.get('output', {})
                        return {
                            'name': output.get('hts_kor_isnm', stock_code),
                            'current_price': float(output.get('stck_prpr', 0)),
                            'change_rate': float(output.get('prdy_ctrt', 0)),
                            'volume': int(output.get('acml_vol', 0))
                        }
                elif response.status_code == 500:
                    print(f"  ⚠️ {stock_code} 서버 오류, 재시도 {attempt+1}/3")
                    time.sleep(2 ** attempt)  # 지수 백오프: 1초, 2초, 4초
                    continue
            except Exception as e:
                print(f"  ⚠️ {stock_code} 조회 실패 ({attempt+1}/3): {e}")
                time.sleep(1)
        return None

    def get_volume_ranking(self):
        """거래량 순위 TOP 20 조회 (재시도 로직 포함)"""
        token = self.get_access_token()
        if not token:
            return []

        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/quotations/volume-rank"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "FHPST01710000"
        }
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

        # 3번까지 재시도
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('rt_cd') == '0':
                        return data.get('output', [])[:20]  # TOP 20
                elif response.status_code == 500:
                    print(f"  ⚠️ 거래량 서버 오류, 재시도 {attempt+1}/3")
                    time.sleep(3)  # 3초 대기
                    continue
            except Exception as e:
                print(f"  ⚠️ 거래량 순위 조회 실패 ({attempt+1}/3): {e}")
                time.sleep(2)
        return []

    def buy_stock(self, stock_code, price, quantity):
        """매수 주문"""
        token = self.get_access_token()
        if not token:
            return False

        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "VTTC0802U",  # 매수
            "content-type": "application/json; charset=utf-8"
        }

        body = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"  # 시장가일 때 0
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('rt_cd') == '0'
        except Exception as e:
            print(f"매수 주문 실패: {e}")
        return False

    def sell_stock(self, stock_code, price, quantity):
        """매도 주문"""
        token = self.get_access_token()
        if not token:
            return False

        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET'),
            "tr_id": "VTTC0801U",  # 매도
            "content-type": "application/json; charset=utf-8"
        }

        body = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"  # 시장가일 때 0
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('rt_cd') == '0'
        except Exception as e:
            print(f"매도 주문 실패: {e}")
        return False

    def get_my_portfolio(self):
        """내 포트폴리오 조회"""
        token = self.get_access_token()
        if not token:
            return []

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
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    holdings = []
                    for item in data.get('output1', []):
                        if int(float(item.get('hldg_qty', 0))) > 0:  # 보유수량이 0보다 큰 것만
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
            print(f"포트폴리오 조회 실패: {e}")
        return []

    def find_buy_opportunities(self):
        """매수 기회 찾기"""
        print("🔍 매수 기회 탐색 중...")

        volume_stocks = self.get_volume_ranking()
        if not volume_stocks:
            print("❌ 거래량 데이터 없음")
            return []

        opportunities = []
        for stock in volume_stocks[:10]:  # TOP 10만 체크
            stock_code = stock.get('mksc_shrn_iscd', '').zfill(6)
            if not stock_code or stock_code == '000000':
                continue

            price_data = self.get_stock_price(stock_code)
            if price_data:
                # 매수 조건: 3% 이상 상승 + 거래량 10만주 이상 + 가격 1000원 이상
                if (price_data['change_rate'] > 3.0 and
                    price_data['volume'] > 100000 and
                    price_data['current_price'] >= 1000):

                    opportunities.append({
                        'stock_code': stock_code,
                        'name': price_data['name'],
                        'current_price': price_data['current_price'],
                        'change_rate': price_data['change_rate'],
                        'volume': price_data['volume']
                    })
                    print(f"  💡 발견: {price_data['name']} - {price_data['change_rate']:+.1f}%, {price_data['volume']:,}주")

            time.sleep(0.2)

        return opportunities

    def check_sell_conditions(self):
        """매도 조건 체크"""
        print("📊 포트폴리오 수익/손실 체크 중...")

        portfolio = self.get_my_portfolio()
        sell_list = []

        for holding in portfolio:
            stock_code = holding['stock_code']
            stock_name = holding['stock_name']
            profit_rate = holding['profit_rate']
            quantity = holding['quantity']
            current_price = holding['current_price']

            print(f"  📈 {stock_name}: {profit_rate:+.2f}%")

            # 손절: -3% 이하
            if profit_rate <= -3.0:
                sell_list.append({
                    'stock_code': stock_code,
                    'name': stock_name,
                    'quantity': quantity,
                    'current_price': current_price,
                    'reason': f'손절 ({profit_rate:.2f}%)'
                })
                print(f"    🔴 손절 대상: {profit_rate:.2f}%")

            # 익절: +5% 이상
            elif profit_rate >= 5.0:
                sell_list.append({
                    'stock_code': stock_code,
                    'name': stock_name,
                    'quantity': quantity,
                    'current_price': current_price,
                    'reason': f'익절 ({profit_rate:.2f}%)'
                })
                print(f"    🟢 익절 대상: {profit_rate:.2f}%")

        return sell_list

    def run_trading_cycle(self):
        """매매 사이클 실행"""
        now = datetime.now(pytz.timezone('Asia/Seoul'))
        print(f"\n{'='*60}")
        print(f"🤖 자동매매 실행 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # 1. 매도 조건 체크 (먼저 정리)
        sell_opportunities = self.check_sell_conditions()
        for sell_item in sell_opportunities:
            print(f"\n💰 {sell_item['reason']} 매도 실행: {sell_item['name']}")
            success = self.sell_stock(
                sell_item['stock_code'],
                sell_item['current_price'],
                sell_item['quantity']
            )
            if success:
                print(f"  ✅ 매도 완료: {sell_item['quantity']}주")
            else:
                print(f"  ❌ 매도 실패")
            time.sleep(1)

        # 2. 매수 기회 찾기
        buy_opportunities = self.find_buy_opportunities()
        for buy_item in buy_opportunities[:2]:  # 최대 2개만 매수
            # 50만원어치 매수 (수량 계산)
            buy_amount = 500000  # 50만원
            quantity = int(buy_amount / buy_item['current_price'])

            if quantity > 0:
                print(f"\n💸 매수 실행: {buy_item['name']} - {quantity}주")
                success = self.buy_stock(
                    buy_item['stock_code'],
                    buy_item['current_price'],
                    quantity
                )
                if success:
                    print(f"  ✅ 매수 완료: {quantity}주 @ {buy_item['current_price']:,.0f}원")
                else:
                    print(f"  ❌ 매수 실패")
                time.sleep(1)

        print(f"\n✅ 매매 사이클 완료 - 다음 실행까지 대기...")

def main():
    trader = SimpleAutoTrader()

    print("🚀 간단한 자동매매 봇 시작")
    print("📋 매수 조건: 3% 이상 상승 + 거래량 10만주 + 1000원 이상")
    print("📋 매도 조건: 손절 -5%, 익절 +10%")
    print("-" * 60)

    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            print(f"\n🔄 사이클 #{cycle_count}")

            trader.run_trading_cycle()

            # 5분 대기
            print("⏰ 5분 대기 중...")
            time.sleep(300)

        except KeyboardInterrupt:
            print("\n🛑 자동매매 봇 종료")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()