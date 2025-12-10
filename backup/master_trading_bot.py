#!/usr/bin/env python3
"""마스터 통합 실시간 트레이딩 봇"""

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

class MasterTradingBot:
    def __init__(self):
        self.running = False
        self.account_no = os.getenv('KIS_ACCOUNT_NUMBER')
        if '-' not in self.account_no:
            self.account_no = f"{self.account_no}-01"

        self.last_market_scan = datetime.now(kst) - timedelta(minutes=10)
        self.last_slack_notification = datetime.now(kst) - timedelta(minutes=30)

    def get_access_token(self):
        """토큰 가져오기 및 자동 갱신"""
        try:
            with open('kis_token.json', 'r') as f:
                token_data = json.load(f)

            exp_time = datetime.fromisoformat(token_data.get('expires_at', '2000-01-01T00:00:00'))
            if datetime.now() >= exp_time - timedelta(minutes=10):
                print("🔄 토큰 만료 임박, 새로 발급 중...")
                os.system("python3 get_saved_token.py > /dev/null 2>&1")
                time.sleep(3)
                with open('kis_token.json', 'r') as f:
                    token_data = json.load(f)

            return token_data.get('token')
        except Exception as e:
            print(f"❌ 토큰 로드 실패: {e}")
            return None

    def send_slack_notification(self, notification_type, message):
        """슬랙 알림 발송"""
        try:
            from slack_notifier import SlackNotifier
            notifier = SlackNotifier()

            # 알림 타입별 처리
            if notification_type == 'deploy':
                notifier.send_message(
                    title="🚀 배포 알림",
                    message=message,
                    color="good",
                    channel=notifier.channels.get('deploy')
                )
            elif notification_type == 'trading':
                notifier.send_message(
                    title="📊 트레이딩 알림",
                    message=message,
                    color="good",
                    channel=notifier.channels.get('trading')
                )
            elif notification_type == 'errors':
                notifier.send_message(
                    title="❌ 에러 알림",
                    message=message,
                    color="danger",
                    channel=notifier.channels.get('errors')
                )
            elif notification_type == 'summary':
                notifier.send_message(
                    title="📈 요약 알림",
                    message=message,
                    color="good",
                    channel=notifier.channels.get('summary')
                )
            else:
                notifier.send_message(
                    title="🔔 시스템 알림",
                    message=message,
                    color="good"
                )
            print(f"📩 슬랙 알림 발송: {notification_type}")
        except Exception as e:
            print(f"❌ 슬랙 알림 실패 (무시하고 계속): {e}")

    def get_stock_price(self, stock_code):
        """개별 종목 현재가 조회"""
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
                    print(f"🔄 {stock_code} 500 에러, 재시도...")
                    time.sleep(2**attempt)
                    continue
                else:
                    return None
            except Exception as e:
                print(f"❌ {stock_code} 조회 실패: {e}")
                time.sleep(1)
        return None

    def get_volume_ranking(self):
        """거래량 순위 조회"""
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

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    return data.get('output', [])[:30]
        except Exception as e:
            print(f"❌ 거래량 순위 조회 실패: {e}")
        return []

    def scan_market_opportunities(self):
        """실시간 시장 기회 스캔"""
        print(f"\n🔍 [{datetime.now(kst).strftime('%H:%M:%S')}] 실시간 시장 스캔...")

        volume_stocks = self.get_volume_ranking()
        if not volume_stocks:
            return

        qualified_stocks = []

        for i, stock in enumerate(volume_stocks[:15], 1):
            stock_code = stock.get('mksc_shrn_iscd', '').zfill(6)
            if not stock_code or stock_code == '000000':
                continue

            price_data = self.get_stock_price(stock_code)
            if price_data:
                # 매수 조건: 3% 이상 상승, 거래량 10만주 이상, 1000원 이상
                if (price_data['change_rate'] > 3.0 and
                    price_data['volume'] > 100000 and
                    price_data['current_price'] >= 1000):

                    qualified_stocks.append({
                        'code': stock_code,
                        'name': price_data['name'],
                        'current_price': price_data['current_price'],
                        'change_rate': price_data['change_rate'],
                        'volume': price_data['volume'],
                        'reason': f"상승률 {price_data['change_rate']:.1f}%, 거래량 {price_data['volume']:,}주"
                    })
                    print(f"  ✅ {price_data['name']}: {price_data['current_price']:,.0f}원 ({price_data['change_rate']:+.1f}%)")

            time.sleep(0.3)

        # Firebase 감시종목 업데이트
        if qualified_stocks:
            # 기존 감시종목 삭제
            existing_docs = db.collection('watchlist').stream()
            for doc in existing_docs:
                doc.reference.delete()

            # 새 감시종목 추가
            for stock in qualified_stocks[:10]:
                db.collection('watchlist').document(stock['code']).set({
                    'code': stock['code'],
                    'name': stock['name'],
                    'current_price': stock['current_price'],
                    'change_rate': stock['change_rate'],
                    'volume': stock['volume'],
                    'reason': stock['reason'],
                    'scanned_at': firestore.SERVER_TIMESTAMP,
                    'scan_date': datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                })

            # 슬랙 알림
            message = f"🎯 새로운 감시종목 {len(qualified_stocks)}개 발견!\n"
            for stock in qualified_stocks[:5]:
                message += f"• {stock['name']}: {stock['current_price']:,.0f}원 ({stock['change_rate']:+.1f}%)\n"
            self.send_slack_notification('trading', message)

            print(f"📈 {len(qualified_stocks)}개 감시종목 업데이트 완료")

        self.last_market_scan = datetime.now(kst)

    def update_portfolio_realtime(self):
        """포트폴리오 실시간 업데이트"""
        print(f"💼 [{datetime.now(kst).strftime('%H:%M:%S')}] 포트폴리오 업데이트...")

        try:
            portfolio_docs = db.collection('portfolio').stream()
            updated_count = 0
            loss_stocks = []

            for doc in portfolio_docs:
                data = doc.to_dict()
                stock_code = doc.id

                price_data = self.get_stock_price(stock_code)
                if price_data:
                    current_price = price_data['current_price']
                    buy_price = data.get('buy_price', current_price)
                    quantity = data.get('quantity', 0)

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

                    # 손실 종목 체크 (-3% 이하)
                    if profit_rate <= -3:
                        loss_stocks.append({
                            'code': stock_code,
                            'name': data.get('name', stock_code),
                            'profit_rate': profit_rate,
                            'doc_ref': doc.reference
                        })

                    updated_count += 1
                    status = "🟢" if profit_rate > 0 else "🔴"
                    print(f"  {status} {data.get('name', stock_code)}: {current_price:,.0f}원 ({profit_rate:+.2f}%)")

                time.sleep(0.2)

            # 손실 종목 자동 제거
            if loss_stocks:
                for stock in loss_stocks:
                    print(f"  🗑️ {stock['name']} 손실 제거 ({stock['profit_rate']:.2f}%)")
                    stock['doc_ref'].delete()

                # 슬랙 알림
                message = f"🔴 손실 종목 {len(loss_stocks)}개 자동 제거:\n"
                for stock in loss_stocks:
                    message += f"• {stock['name']}: {stock['profit_rate']:.2f}%\n"
                self.send_slack_notification('trading', message)

            print(f"  ✅ {updated_count}개 종목 업데이트 완료")

        except Exception as e:
            print(f"❌ 포트폴리오 업데이트 실패: {e}")

    def update_watchlist_realtime(self):
        """감시종목 실시간 업데이트"""
        try:
            watchlist_docs = db.collection('watchlist').stream()

            for doc in watchlist_docs:
                data = doc.to_dict()
                stock_code = doc.id

                price_data = self.get_stock_price(stock_code)
                if price_data:
                    doc.reference.update({
                        'current_price': price_data['current_price'],
                        'change_rate': price_data.get('change_rate', 0),
                        'volume': price_data.get('volume', 0),
                        'last_updated': firestore.SERVER_TIMESTAMP
                    })

                time.sleep(0.2)

        except Exception as e:
            print(f"❌ 감시종목 업데이트 실패: {e}")

    def send_periodic_status(self):
        """주기적 상태 리포트"""
        now = datetime.now(kst)
        if (now - self.last_slack_notification).total_seconds() < 1800:  # 30분 간격
            return

        try:
            # 포트폴리오 요약
            portfolio_docs = list(db.collection('portfolio').stream())
            watchlist_docs = list(db.collection('watchlist').stream())

            message = f"📊 시스템 상태 리포트 ({now.strftime('%H:%M')})\n"
            message += f"💼 포트폴리오: {len(portfolio_docs)}개 종목\n"
            message += f"🔍 감시종목: {len(watchlist_docs)}개\n"
            message += f"⏰ 마지막 스캔: {self.last_market_scan.strftime('%H:%M:%S')}\n"

            self.send_slack_notification('summary', message)
            self.last_slack_notification = now

        except Exception as e:
            print(f"❌ 상태 리포트 실패: {e}")

    def run_master_bot(self):
        """마스터 봇 메인 루프"""
        self.running = True
        print("🚀 마스터 통합 실시간 트레이딩 봇 시작")
        print("=" * 60)

        # 초기 슬랙 알림
        self.send_slack_notification('deploy', '🚀 마스터 트레이딩 봇이 시작되었습니다!')

        cycle_count = 0

        while self.running:
            try:
                start_time = time.time()
                cycle_count += 1

                print(f"\n🔄 [{datetime.now(kst).strftime('%H:%M:%S')}] 사이클 #{cycle_count}")

                # 1. 포트폴리오 업데이트 (매번)
                self.update_portfolio_realtime()

                # 2. 감시종목 업데이트 (매번)
                self.update_watchlist_realtime()

                # 3. 시장 스캔 (5분마다)
                if (datetime.now(kst) - self.last_market_scan).total_seconds() > 300:
                    self.scan_market_opportunities()

                # 4. 상태 리포트 (30분마다)
                self.send_periodic_status()

                # 5. 시스템 상태 업데이트
                db.collection('system').document('status').set({
                    'last_update': firestore.SERVER_TIMESTAMP,
                    'status': 'running',
                    'cycle_count': cycle_count,
                    'version': '3.0'
                }, merge=True)

                # 처리 시간 계산 및 대기
                elapsed = time.time() - start_time
                sleep_time = max(0, 30 - elapsed)  # 30초 간격

                if sleep_time > 0:
                    print(f"⏰ {sleep_time:.1f}초 대기...")
                    time.sleep(sleep_time)

            except KeyboardInterrupt:
                print("\n🛑 마스터 봇 종료")
                self.send_slack_notification('deploy', '🛑 마스터 트레이딩 봇이 종료되었습니다.')
                self.running = False
                break
            except Exception as e:
                print(f"❌ 메인 루프 오류: {e}")
                self.send_slack_notification('errors', f'❌ 시스템 오류: {str(e)}')
                time.sleep(10)

def main():
    bot = MasterTradingBot()
    bot.run_master_bot()

if __name__ == "__main__":
    main()