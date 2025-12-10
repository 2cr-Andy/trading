#!/usr/bin/env python3
"""실시간 시장 데이터 업데이트 및 매수/매도 신호 생성"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import time
import json
import requests
from datetime import datetime
from smart_stock_name_manager import SmartStockNameManager

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

class RealtimeMarketUpdater:
    def __init__(self):
        self.db = db
        self.name_manager = SmartStockNameManager()
        self.token = None
        self.base_url = "https://openapi.koreainvestment.com:9443"

    def get_access_token(self):
        """저장된 토큰 사용 또는 새로 발급"""
        token_file = "kis_token.json"

        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    token_data = json.load(f)
                    self.token = token_data.get('token')
                    expires_at = token_data.get('expires_at', 0)

                    if self.token and time.time() < expires_at - 3600:
                        return True
            except Exception as e:
                print(f"토큰 파일 읽기 오류: {e}")

        print("❌ 유효한 토큰이 없습니다")
        return False

    def get_current_price(self, stock_code):
        """현재가 및 거래 데이터 조회"""
        if not self.token:
            return None

        try:
            headers = {
                "authorization": f"Bearer {self.token}",
                "appkey": os.getenv('KIS_APP_KEY'),
                "appsecret": os.getenv('KIS_APP_SECRET'),
                "tr_id": "FHKST01010100"
            }

            params = {
                "FID_INPUT_ISCD": stock_code,
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_DATE_1": ""
            }

            response = requests.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
                headers=headers,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    output = data.get('output', {})
                    return {
                        'current_price': int(float(output.get('stck_prpr', 0))),
                        'change_rate': float(output.get('prdy_ctrt', 0)),
                        'change_price': int(float(output.get('prdy_vrss', 0))),
                        'volume': int(float(output.get('acml_vol', 0))),
                        'high_price': int(float(output.get('stck_hgpr', 0))),
                        'low_price': int(float(output.get('stck_lwpr', 0))),
                        'open_price': int(float(output.get('stck_oprc', 0)))
                    }
        except Exception as e:
            print(f"Error getting price for {stock_code}: {e}")

        return None

    def calculate_technical_indicators(self, stock_code, price_data):
        """기술적 지표 계산 (RSI, MFI)"""
        # 단순화된 계산 (실제로는 과거 데이터 필요)
        change_rate = price_data.get('change_rate', 0)
        volume = price_data.get('volume', 0)
        current_price = price_data.get('current_price', 0)
        high_price = price_data.get('high_price', current_price)
        low_price = price_data.get('low_price', current_price)

        # RSI 근사치 계산 (정확한 계산은 14일 데이터 필요)
        rsi = 50 + (change_rate * 5)  # 단순화된 계산
        rsi = max(0, min(100, rsi))

        # MFI 근사치 계산 (정확한 계산은 14일 데이터 필요)
        if high_price > low_price:
            money_flow = volume * (high_price + low_price + current_price) / 3
            mfi = 50 + (change_rate * 3)  # 단순화된 계산
        else:
            mfi = 50

        mfi = max(0, min(100, mfi))

        return {
            'rsi': round(rsi, 2),
            'mfi': round(mfi, 2)
        }

    def analyze_buy_signal(self, stock_data):
        """매수 신호 분석"""
        rsi = stock_data.get('rsi', 50)
        mfi = stock_data.get('mfi', 50)
        change_rate = stock_data.get('change_rate', 0)
        volume = stock_data.get('volume', 0)

        buy_signal = False
        buy_reason = ""
        score = 0

        # RSI 과매도 신호
        if rsi < 30:
            buy_signal = True
            buy_reason = "RSI 과매도 구간"
            score += 30
        elif rsi < 40:
            buy_reason = "RSI 하단 접근"
            score += 20

        # MFI 신호
        if mfi < 30:
            if buy_signal:
                buy_reason += " + MFI 과매도"
            else:
                buy_signal = True
                buy_reason = "MFI 과매도 구간"
            score += 25

        # 급등 신호
        if change_rate > 5:
            if not buy_signal:
                buy_signal = True
                buy_reason = "급등주 (5% 이상)"
            score += change_rate * 2

        # 거래량 증가
        if volume > 1000000:
            score += 10

        # 점수 기반 최종 판단
        if score > 40 and not buy_signal:
            buy_signal = True
            buy_reason = "종합 매수 신호"

        return {
            'buy_signal': buy_signal,
            'buy_reason': buy_reason,
            'score': round(score, 2)
        }

    def update_watchlist(self):
        """감시 종목 업데이트"""
        print("📊 감시 종목 실시간 업데이트 시작...")

        # 현재 감시 종목 가져오기
        doc = self.db.collection('market_scan').document('latest').get()
        if not doc.exists:
            print("❌ 감시 종목이 없습니다")
            return

        data = doc.to_dict()
        stocks = data.get('stocks', [])
        updated_stocks = []

        for stock in stocks:
            stock_code = stock.get('code')
            if not stock_code:
                continue

            # 종목명 확인 및 업데이트
            if not stock.get('name') or stock.get('name') == stock_code:
                stock_name = self.name_manager.get_stock_name(stock_code)
                if stock_name:
                    stock['name'] = stock_name
                else:
                    stock['name'] = stock_code

            # 현재가 조회
            price_data = self.get_current_price(stock_code)
            if price_data:
                # 기술적 지표 계산
                indicators = self.calculate_technical_indicators(stock_code, price_data)

                # 데이터 업데이트
                stock['current_price'] = price_data['current_price']
                stock['change_rate'] = price_data['change_rate']
                stock['change_price'] = price_data['change_price']
                stock['volume'] = price_data['volume']
                stock['rsi'] = indicators['rsi']
                stock['mfi'] = indicators['mfi']

                # 매수 신호 분석
                signal_data = self.analyze_buy_signal(stock)
                stock['buy_signal'] = signal_data['buy_signal']
                stock['buy_reason'] = signal_data['buy_reason']
                stock['score'] = signal_data['score']

                print(f"✅ {stock_code} ({stock['name']}): {price_data['current_price']:,}원, "
                      f"등락률: {price_data['change_rate']:+.2f}%, "
                      f"RSI: {indicators['rsi']:.1f}, MFI: {indicators['mfi']:.1f}, "
                      f"신호: {'🔴 매수' if signal_data['buy_signal'] else '⚪ 대기'}")

            updated_stocks.append(stock)
            time.sleep(0.1)  # API 제한 방지

        # Firebase 업데이트
        self.db.collection('market_scan').document('latest').update({
            'stocks': updated_stocks,
            'last_updated': firestore.SERVER_TIMESTAMP,
            'update_count': firestore.Increment(1)
        })

        print(f"✅ {len(updated_stocks)}개 종목 업데이트 완료")

    def update_portfolio(self):
        """포트폴리오 실시간 업데이트"""
        print("💼 포트폴리오 실시간 업데이트 시작...")

        portfolio_docs = self.db.collection('portfolio').stream()
        updated_count = 0

        for doc in portfolio_docs:
            stock_code = doc.id
            data = doc.to_dict()

            # 종목명 확인 및 업데이트
            if not data.get('name') or data.get('name') == stock_code:
                stock_name = self.name_manager.get_stock_name(stock_code)
                if stock_name:
                    data['name'] = stock_name

            # 현재가 조회
            price_data = self.get_current_price(stock_code)
            if price_data:
                buy_price = data.get('buy_price', 0)
                quantity = data.get('quantity', 0)

                # 수익률 계산
                if buy_price > 0:
                    profit_rate = ((price_data['current_price'] - buy_price) / buy_price) * 100
                    profit_amount = (price_data['current_price'] - buy_price) * quantity
                else:
                    profit_rate = 0
                    profit_amount = 0

                # 업데이트 데이터
                update_data = {
                    'name': data.get('name', stock_code),
                    'current_price': price_data['current_price'],
                    'change_rate': price_data['change_rate'],
                    'change_price': price_data['change_price'],
                    'volume': price_data['volume'],
                    'high_price': price_data['high_price'],
                    'low_price': price_data['low_price'],
                    'profit_rate': round(profit_rate, 2),
                    'profit_amount': profit_amount,
                    'total_value': price_data['current_price'] * quantity,
                    'last_updated': firestore.SERVER_TIMESTAMP
                }

                self.db.collection('portfolio').document(stock_code).update(update_data)

                print(f"✅ {stock_code} ({data.get('name', stock_code)}): "
                      f"{price_data['current_price']:,}원, "
                      f"수익률: {profit_rate:+.2f}%")

                updated_count += 1
                time.sleep(0.1)  # API 제한 방지

        print(f"✅ {updated_count}개 포트폴리오 종목 업데이트 완료")

    def run_update(self):
        """전체 업데이트 실행"""
        if not self.get_access_token():
            print("❌ 토큰이 없어 업데이트할 수 없습니다")
            return False

        print(f"\n🔄 실시간 시장 데이터 업데이트 시작 - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)

        # 감시 종목 업데이트
        self.update_watchlist()
        print()

        # 포트폴리오 업데이트
        self.update_portfolio()
        print()

        print("=" * 60)
        print("✅ 실시간 업데이트 완료\n")
        return True

def main():
    """메인 실행"""
    updater = RealtimeMarketUpdater()

    # 단일 실행
    updater.run_update()

if __name__ == "__main__":
    main()