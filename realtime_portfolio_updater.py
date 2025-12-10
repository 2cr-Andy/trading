#!/usr/bin/env python3
"""실시간 포트폴리오 가격 업데이트 (안정적 버전)"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

class RealtimePortfolioUpdater:
    def __init__(self):
        self.account_no = os.getenv('KIS_ACCOUNT_NUMBER')
        if '-' not in self.account_no:
            self.account_no = f"{self.account_no}-01"

        # 종목명 매핑
        self.stock_names = {
            "090710": "휴림로봇",
            "220260": "켐트로스",
            "317830": "에스피시스템스",
            "319400": "현대무벡스"
        }

    def get_access_token(self):
        """토큰 가져오기"""
        try:
            with open('kis_token.json', 'r') as f:
                token_data = json.load(f)
                return token_data.get('token')
        except:
            print("❌ 토큰 파일을 찾을 수 없습니다")
            return None

    def get_portfolio_balance(self):
        """안정적인 포트폴리오 잔고 조회"""
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
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    return data
                else:
                    print(f"API 오류: {data.get('msg1')}")
            else:
                print(f"HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"요청 실패: {e}")

        return None

    def update_firebase_portfolio(self):
        """Firebase 포트폴리오 실시간 업데이트"""
        print(f"🔄 {datetime.now().strftime('%H:%M:%S')} - 포트폴리오 업데이트 중...")

        balance_data = self.get_portfolio_balance()
        if not balance_data:
            print("❌ 잔고 조회 실패")
            return False

        output1 = balance_data.get('output1', [])
        output2 = balance_data.get('output2', [{}])[0]

        updated_count = 0

        # 실제 보유 종목만 업데이트
        for stock in output1:
            quantity = int(float(stock.get('hldg_qty', 0)))
            if quantity > 0:
                code = stock.get('pdno')
                name = self.stock_names.get(code, code)
                buy_avg = float(stock.get('pchs_avg_pric', 0))
                current = float(stock.get('prpr', 0))
                profit_amt = float(stock.get('evlu_pfls_amt', 0))
                profit_rate = float(stock.get('evlu_pfls_rt', 0))

                # Firebase 업데이트 (기존 필드 유지하면서 현재 가격만 업데이트)
                try:
                    doc_ref = db.collection('portfolio').document(code)
                    doc_ref.update({
                        'current_price': current,
                        'profit_amount': profit_amt,
                        'profit_rate': profit_rate,
                        'total_value': current * quantity,
                        'last_updated': firestore.SERVER_TIMESTAMP
                    })
                    updated_count += 1
                    print(f"  ✅ {name}: {current:,.0f}원 ({profit_rate:+.2f}%)")
                except Exception as e:
                    print(f"  ❌ {name} 업데이트 실패: {e}")

        # 계좌 요약 업데이트
        try:
            total_cash = float(output2.get('dnca_tot_amt', 0))
            total_value = float(output2.get('tot_evlu_amt', 0))
            total_profit = float(output2.get('evlu_pfls_smtl_amt', 0))

            db.collection('account').document('summary').update({
                'total_cash': total_cash,
                'total_value': total_value,
                'total_profit': total_profit,
                'profit_rate': (total_profit / total_value * 100) if total_value > 0 else 0,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            print(f"  📊 계좌요약: 총자산 {total_value:,.0f}원, 손익 {total_profit:+,.0f}원")
        except Exception as e:
            print(f"  ❌ 계좌요약 업데이트 실패: {e}")

        return updated_count > 0

    def run_continuous_update(self, interval_seconds=30):
        """지속적인 업데이트 실행"""
        print(f"🚀 실시간 포트폴리오 업데이터 시작 (간격: {interval_seconds}초)")

        while True:
            try:
                success = self.update_firebase_portfolio()
                if success:
                    print("✅ 업데이트 완료")
                else:
                    print("⚠️ 업데이트 실패")

                print(f"⏰ {interval_seconds}초 대기 중...\n")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n🛑 업데이터 종료")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                time.sleep(5)  # 오류 시 5초 대기

if __name__ == "__main__":
    updater = RealtimePortfolioUpdater()
    updater.run_continuous_update(30)  # 30초마다 업데이트