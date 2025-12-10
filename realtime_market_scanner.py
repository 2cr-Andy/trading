#!/usr/bin/env python3
"""오늘 실시간 시장 스캔"""

import os
import json
import requests
import time
from datetime import datetime
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

def get_access_token():
    """토큰 가져오기"""
    try:
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            return token_data.get('token')
    except:
        return None

def get_volume_ranking():
    """실시간 거래량 순위 API로 조회"""
    token = get_access_token()
    if not token:
        return []

    print("📊 실시간 거래량 순위 조회 중...")

    url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/quotations/volume-rank"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": os.getenv('KIS_APP_KEY'),
        "appsecret": os.getenv('KIS_APP_SECRET'),
        "tr_id": "FHPST01710000"
    }

    params = {
        "FID_COND_MRKT_DIV_CODE": "J",  # 주식
        "FID_COND_SCR_DIV_CODE": "20171",  # 거래량순위
        "FID_INPUT_ISCD": "0000",  # 전체
        "FID_DIV_CLS_CODE": "0",  # 전체
        "FID_BLNG_CLS_CODE": "0",  # 평균거래량 구분
        "FID_TRGT_CLS_CODE": "111111111",  # 대상제외
        "FID_TRGT_EXLS_CLS_CODE": "0000000000",  # 제외코드
        "FID_INPUT_PRICE_1": "",  # 가격조건1
        "FID_INPUT_PRICE_2": "",  # 가격조건2
        "FID_VOL_CNT": ""  # 거래량
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('rt_cd') == '0':
                stocks = data.get('output', [])
                print(f"  ✅ {len(stocks)}개 종목 조회 성공")
                return stocks[:50]  # 상위 50개
            else:
                print(f"  ❌ API 오류: {data.get('msg1')}")
        else:
            print(f"  ❌ HTTP 오류: {response.status_code}")
    except Exception as e:
        print(f"  ❌ 요청 실패: {e}")

    return []

def get_stock_price_and_indicators(stock_code):
    """개별 종목의 현재가 및 지표 조회"""
    token = get_access_token()
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

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('rt_cd') == '0':
                output = data.get('output', {})

                current_price = float(output.get('stck_prpr', 0))
                change_rate = float(output.get('prdy_ctrt', 0))
                volume = int(output.get('acml_vol', 0))

                # 간단한 조건 체크
                has_signal = (
                    change_rate > 3.0 and  # 3% 이상 상승
                    volume > 100000 and    # 거래량 10만주 이상
                    current_price >= 1000  # 1000원 이상
                )

                return {
                    'code': stock_code,
                    'name': output.get('hts_kor_isnm', stock_code),
                    'current_price': current_price,
                    'change_rate': change_rate,
                    'volume': volume,
                    'buy_signal': has_signal,
                    'reason': f"상승률 {change_rate:.1f}%, 거래량 {volume:,}주" if has_signal else ""
                }
        else:
            print(f"  ⚠️ {stock_code}: HTTP {response.status_code}")
    except Exception as e:
        print(f"  ⚠️ {stock_code}: {e}")

    return None

def scan_realtime_market():
    """실시간 시장 스캔 실행"""
    print("🔥 오늘 실시간 시장 스캔 시작")
    print("=" * 50)

    # 1. 거래량 순위 조회
    volume_stocks = get_volume_ranking()
    if not volume_stocks:
        print("❌ 거래량 데이터 조회 실패")
        return

    print(f"📈 거래량 상위 {len(volume_stocks)}개 종목에서 조건 검색 중...")

    qualified_stocks = []

    # 2. 각 종목별 상세 정보 조회
    for i, stock in enumerate(volume_stocks[:20], 1):  # 상위 20개만
        stock_code = stock.get('mksc_shrn_iscd', '').zfill(6)
        if not stock_code or stock_code == '000000':
            continue

        print(f"  [{i:2d}/20] {stock_code} 분석 중...")

        stock_info = get_stock_price_and_indicators(stock_code)
        if stock_info and stock_info['buy_signal']:
            qualified_stocks.append(stock_info)
            print(f"    ✅ 조건 충족! {stock_info['name']} - {stock_info['reason']}")
        elif stock_info:
            print(f"    ⚪ {stock_info['name']}: 조건 미충족")
        else:
            print(f"    ❌ 데이터 조회 실패")

        time.sleep(0.2)  # API 호출 제한 준수

    print("\n" + "=" * 50)
    print(f"🎯 최종 결과: {len(qualified_stocks)}개 종목이 조건을 충족합니다")

    # 3. Firebase에 업데이트
    if qualified_stocks:
        # 기존 감시종목 삭제
        existing_docs = db.collection('watchlist').stream()
        for doc in existing_docs:
            doc.reference.delete()

        print("\n📤 Firebase 감시종목 업데이트 중...")
        for stock in qualified_stocks[:10]:  # 최대 10개
            db.collection('watchlist').document(stock['code']).set({
                'code': stock['code'],
                'name': stock['name'],
                'current_price': stock['current_price'],
                'change_rate': stock['change_rate'],
                'volume': stock['volume'],
                'buy_signal': stock['buy_signal'],
                'reason': stock['reason'],
                'scanned_at': firestore.SERVER_TIMESTAMP,
                'scan_date': datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
            })
            print(f"  ✅ {stock['name']}({stock['code']}): {stock['current_price']:,.0f}원 ({stock['change_rate']:+.1f}%)")

        print(f"\n🚀 {len(qualified_stocks)}개 실시간 종목이 감시목록에 추가되었습니다!")
    else:
        print("\n⚠️ 오늘 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    scan_realtime_market()