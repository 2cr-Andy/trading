#!/usr/bin/env python3
"""개선된 실시간 업데이트 시스템"""

import os
import json
import time
import requests
import threading
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()
kst = pytz.timezone('Asia/Seoul')

class EnhancedRealtimeSystem:
    def __init__(self):
        self.running = False
        self.last_update = datetime.now(kst)
        self.account_no = os.getenv('KIS_ACCOUNT_NUMBER')
        if '-' not in self.account_no:
            self.account_no = f"{self.account_no}-01"

    def get_access_token(self):
        """토큰 가져오기 (자동 갱신)"""
        try:
            with open('kis_token.json', 'r') as f:
                token_data = json.load(f)

            # 토큰 만료 체크
            exp_time = datetime.fromisoformat(token_data.get('expires_at', '2000-01-01T00:00:00'))
            if datetime.now() >= exp_time - timedelta(minutes=10):  # 10분 전 갱신
                print("🔄 토큰 만료 임박, 새로 발급 중...")
                os.system("python3 get_saved_token.py > /dev/null 2>&1")
                time.sleep(2)
                with open('kis_token.json', 'r') as f:
                    token_data = json.load(f)

            return token_data.get('token')
        except Exception as e:
            print(f"❌ 토큰 로드 실패: {e}")
            return None

    def get_stock_price(self, stock_code):
        """개별 종목 현재가 조회 (재시도 로직)"""
        token = self.get_access_token()
        if not token:
            return None

        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": os.getenv('KIS_APP_KEY'),
            "appsecret": os.getenv('KIS_APP_SECRET')
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        for attempt in range(3):  # 최대 3회 재시도
            try:
                response = requests.get(url, headers=headers, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('rt_cd') == '0':
                        output = data.get('output', {})
                        return {
                            'current_price': float(output.get('stck_prpr', 0)),
                            'change_rate': float(output.get('prdy_ctrt', 0)),
                            'volume': int(output.get('acml_vol', 0))
                        }
                    elif data.get('rt_cd') == '1':
                        print(f"  ⚠️ {stock_code} API 오류: {data.get('msg1')}")
                        return None
                elif response.status_code == 500:
                    print(f"  🔄 {stock_code} 500 에러, {2**attempt}초 후 재시도...")
                    time.sleep(2**attempt)
                    continue
                else:
                    print(f"  ❌ {stock_code} HTTP 에러: {response.status_code}")
                    return None
            except Exception as e:
                print(f"  ❌ {stock_code} 요청 실패: {e}")
                time.sleep(1)

        return None

    def update_portfolio_realtime(self):
        """포트폴리오 실시간 업데이트"""
        print(f"\n📊 [{datetime.now(kst).strftime('%H:%M:%S')}] 포트폴리오 업데이트 중...")

        try:
            portfolio_docs = db.collection('portfolio').stream()
            updated_count = 0

            for doc in portfolio_docs:
                data = doc.to_dict()
                stock_code = doc.id

                # 현재가 조회
                price_data = self.get_stock_price(stock_code)
                if price_data:
                    current_price = price_data['current_price']
                    buy_price = data.get('buy_price', current_price)
                    quantity = data.get('quantity', 0)

                    # 수익률 계산
                    profit_amount = (current_price - buy_price) * quantity
                    profit_rate = ((current_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0

                    # Firebase 업데이트
                    doc.reference.update({
                        'current_price': current_price,
                        'profit_amount': profit_amount,
                        'profit_rate': profit_rate,
                        'total_value': current_price * quantity,
                        'change_rate': price_data.get('change_rate', 0),
                        'last_updated': firestore.SERVER_TIMESTAMP
                    })

                    updated_count += 1
                    status = "🟢" if profit_rate > 0 else "🔴"
                    print(f"  {status} {data.get('name', stock_code)}: {current_price:,.0f}원 ({profit_rate:+.2f}%)")
                else:
                    print(f"  ⚠️ {data.get('name', stock_code)}: 가격 조회 실패")

                time.sleep(0.2)  # API 호출 간격

            print(f"  ✅ {updated_count}개 종목 업데이트 완료")

        except Exception as e:
            print(f"  ❌ 포트폴리오 업데이트 실패: {e}")

    def update_watchlist_realtime(self):
        """감시종목 실시간 업데이트"""
        print(f"\n🔍 [{datetime.now(kst).strftime('%H:%M:%S')}] 감시종목 업데이트 중...")

        try:
            watchlist_docs = db.collection('watchlist').stream()
            updated_count = 0

            for doc in watchlist_docs:
                data = doc.to_dict()
                stock_code = doc.id

                # 현재가 조회
                price_data = self.get_stock_price(stock_code)
                if price_data:
                    doc.reference.update({
                        'current_price': price_data['current_price'],
                        'change_rate': price_data.get('change_rate', 0),
                        'volume': price_data.get('volume', 0),
                        'last_updated': firestore.SERVER_TIMESTAMP
                    })

                    updated_count += 1
                    print(f"  📈 {data.get('name', stock_code)}: {price_data['current_price']:,.0f}원 ({price_data.get('change_rate', 0):+.2f}%)")
                else:
                    print(f"  ⚠️ {data.get('name', stock_code)}: 가격 조회 실패")

                time.sleep(0.2)

            print(f"  ✅ {updated_count}개 감시종목 업데이트 완료")

        except Exception as e:
            print(f"  ❌ 감시종목 업데이트 실패: {e}")

    def update_system_status(self):
        """시스템 상태 업데이트"""
        try:
            db.collection('system').document('status').set({
                'last_update': firestore.SERVER_TIMESTAMP,
                'status': 'running',
                'update_interval': 10,
                'version': '2.0'
            }, merge=True)
        except:
            pass

    def run_realtime_updates(self):
        """실시간 업데이트 메인 루프"""
        self.running = True
        print("🚀 개선된 실시간 업데이트 시스템 시작")
        print("-" * 50)

        while self.running:
            try:
                start_time = time.time()

                # 포트폴리오 업데이트 (매번)
                self.update_portfolio_realtime()

                # 감시종목 업데이트 (1분마다)
                if int(time.time()) % 60 < 10:  # 매 분의 첫 10초
                    self.update_watchlist_realtime()

                # 시스템 상태 업데이트
                self.update_system_status()

                # 처리 시간 계산
                elapsed = time.time() - start_time
                sleep_time = max(0, 10 - elapsed)  # 10초 간격 유지

                if sleep_time > 0:
                    print(f"⏰ {sleep_time:.1f}초 대기 중...")
                    time.sleep(sleep_time)

            except KeyboardInterrupt:
                print("\n🛑 시스템 종료")
                self.running = False
                break
            except Exception as e:
                print(f"❌ 메인 루프 오류: {e}")
                time.sleep(5)

    def force_sell_losses(self):
        """손실 종목 강제 매도 (대안 방법)"""
        print("\n🔴 손실 종목 강제 처리")
        print("-" * 30)

        # Firebase에서 직접 손실 종목 삭제 (실제 매도가 안되므로)
        try:
            portfolio_docs = db.collection('portfolio').stream()

            for doc in portfolio_docs:
                data = doc.to_dict()
                profit_rate = data.get('profit_rate', 0)

                if profit_rate <= -3:  # -3% 이하 손실
                    print(f"  🗑️ {data.get('name', doc.id)} 포트폴리오에서 제거 (손실: {profit_rate:.2f}%)")
                    doc.reference.delete()

            print("  ✅ 손실 종목 처리 완료")

        except Exception as e:
            print(f"  ❌ 손실 종목 처리 실패: {e}")

def main():
    system = EnhancedRealtimeSystem()

    print("선택하세요:")
    print("1. 실시간 업데이트 시작")
    print("2. 손실 종목 강제 제거")
    print("3. 둘 다")

    choice = input("선택 (1/2/3): ").strip()

    if choice in ['2', '3']:
        system.force_sell_losses()

    if choice in ['1', '3']:
        system.run_realtime_updates()

if __name__ == "__main__":
    main()