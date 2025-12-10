#!/usr/bin/env python3
"""실제 KIS 계좌 정보와 포트폴리오 동기화"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
from datetime import datetime
from token_manager import TokenManager
import requests
import time

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

class KISClient:
    def __init__(self):
        self.app_key = "PSGUOx5PHEI72XtZBwKF1KJdLTkQJDrOZGBZ"
        self.app_secret = "E1LXIeWzPWkkO9TFYHCfaBF3AzlXVKcTkPNxe23p1q3vCRKP8Fc7G0XWZX0rwqR4ZR3hqYODdtq0NTZHPQgZjQKP+IcD2OBRWg8KKy9LLMOYfZqpYl9z/QyIr5qKAmKwK2Q7ORJKoIz8nrWKKUk8/Gfay4owJrS8g8W5xKZdOJPF3dBFFFs="
        self.account_num = "50067635"
        self.account_code = "01"
        self.token_manager = TokenManager(self.app_key, self.app_secret)
        self.access_token = self.token_manager.get_token()
        print(f"✅ KIS API 토큰 획득 성공")

    def get_account_balance(self):
        """계좌 잔고 조회"""
        if not self.access_token:
            return None

        url = f"https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC8434R",  # 주식잔고조회
            "custtype": "P"
        }

        params = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_code,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 계좌 조회 실패: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"❌ 계좌 조회 오류: {e}")
            return None

    def get_portfolio(self):
        """실제 보유종목 조회"""
        if not self.access_token:
            return None

        url = f"https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC8434R",
            "custtype": "P"
        }

        params = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_code,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 포트폴리오 조회 실패: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"❌ 포트폴리오 조회 오류: {e}")
            return None

def update_account_info(kis_client):
    """계좌 정보 업데이트"""
    print("\n📊 계좌 정보 동기화 중...")

    balance_data = kis_client.get_account_balance()
    if not balance_data:
        print("❌ 계좌 정보 조회 실패")
        return

    try:
        output2 = balance_data.get('output2', [{}])[0]

        # 계좌 정보 추출
        total_assets = float(output2.get('tot_evlu_amt', 0))  # 총평가금액
        total_cash = float(output2.get('nxdy_excc_amt', 0))  # 익일정산금액(가용현금)
        today_pnl = float(output2.get('dnca_tot_amt', 0))   # 당일총손익
        today_pnl_percent = float(output2.get('tot_evlu_pfls_rt', 0))  # 총평가손익율

        # Firebase 업데이트
        account_data = {
            'totalAssets': total_assets,
            'totalCash': total_cash,
            'todayPnL': today_pnl,
            'todayPnLPercent': today_pnl_percent,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'lastSync': datetime.now().isoformat()
        }

        db.collection('account').document('summary').set(account_data)

        print(f"✅ 계좌 정보 업데이트 완료:")
        print(f"   - 총자산: {total_assets:,.0f}원")
        print(f"   - 예수금: {total_cash:,.0f}원")
        print(f"   - 당일손익: {today_pnl:+,.0f}원 ({today_pnl_percent:+.2f}%)")

    except Exception as e:
        print(f"❌ 계좌 정보 업데이트 실패: {e}")

def update_portfolio(kis_client):
    """포트폴리오 동기화"""
    print("\n💼 포트폴리오 동기화 중...")

    portfolio_data = kis_client.get_portfolio()
    if not portfolio_data:
        print("❌ 포트폴리오 조회 실패")
        return

    try:
        # 기존 포트폴리오 문서 삭제
        portfolio_docs = db.collection('portfolio').get()
        for doc in portfolio_docs:
            doc.reference.delete()
        print("🗑️ 기존 포트폴리오 데이터 삭제")

        output1 = portfolio_data.get('output1', [])

        for stock in output1:
            stock_code = stock.get('pdno', '')  # 상품번호(종목코드)
            stock_name = stock.get('prdt_name', '')  # 상품명
            quantity = int(stock.get('hldg_qty', 0))  # 보유수량

            # 보유수량이 0인 종목은 제외
            if quantity <= 0:
                continue

            avg_price = float(stock.get('pchs_avg_pric', 0))  # 매입평균가격
            current_price = float(stock.get('prpr', 0))  # 현재가
            total_value = current_price * quantity  # 평가금액
            profit_amount = float(stock.get('evlu_pfls_amt', 0))  # 평가손익금액
            profit_rate = float(stock.get('evlu_pfls_rt', 0))  # 평가손익율

            # Firebase에 저장할 데이터
            stock_data = {
                'code': stock_code,
                'name': stock_name,
                'quantity': quantity,
                'buy_price': avg_price,
                'current_price': current_price,
                'total_value': total_value,
                'profit_amount': profit_amount,
                'profit_rate': profit_rate,
                'status': 'holding',
                'last_updated': firestore.SERVER_TIMESTAMP,
                'buy_time': datetime.now().isoformat(),
                'change_rate': 0.0,  # 별도로 현재가 API에서 가져와야 함
                'volume': 0.0,       # 별도로 현재가 API에서 가져와야 함
            }

            # Firebase에 저장
            db.collection('portfolio').document(stock_code).set(stock_data)

            print(f"✅ {stock_name}({stock_code}): {quantity}주, 평균가 {avg_price:,.0f}원, "
                  f"수익 {profit_amount:+,.0f}원 ({profit_rate:+.2f}%)")

        print(f"✅ 포트폴리오 동기화 완료 ({len([s for s in output1 if int(s.get('hldg_qty', 0)) > 0])}개 종목)")

    except Exception as e:
        print(f"❌ 포트폴리오 업데이트 실패: {e}")

def main():
    print("🔄 KIS 실계좌 데이터 동기화 시작")
    print("=" * 50)

    # KIS 클라이언트 초기화
    kis_client = KISClient()

    if not kis_client.access_token:
        print("❌ KIS API 연결 실패")
        return

    # 1. 계좌 정보 동기화
    update_account_info(kis_client)

    time.sleep(1)  # API 호출 제한 고려

    # 2. 포트폴리오 동기화
    update_portfolio(kis_client)

    print(f"\n✨ 동기화 완료 - {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()