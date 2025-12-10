#!/usr/bin/env python3
"""Firebase를 실제 KIS API 데이터와 동기화"""

import os
import json
import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_access_token():
    """토큰 가져오기"""
    try:
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            return token_data.get('token')
    except:
        return None

def get_real_balance():
    """실제 KIS 잔고 조회"""
    token = get_access_token()
    if not token:
        return None

    account_no = os.getenv('KIS_ACCOUNT_NUMBER')
    if '-' not in account_no:
        account_no = f"{account_no}-01"

    url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": os.getenv('KIS_APP_KEY'),
        "appsecret": os.getenv('KIS_APP_SECRET'),
        "tr_id": "VTTC8434R"
    }

    params = {
        "CANO": account_no.split('-')[0],
        "ACNT_PRDT_CD": account_no.split('-')[1],
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
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"잔고 조회 실패: {e}")

    return None

def get_stock_name(stock_code):
    """종목명 조회"""
    names = {
        "090710": "휴림로봇",
        "220260": "켐트로스",
        "317830": "에스피시스템스",
        "319400": "현대무벡스"
    }
    return names.get(stock_code, stock_code)

def sync_to_firebase():
    """Firebase와 실제 잔고 동기화"""
    print("🔄 Firebase 동기화 시작...")

    # 실제 잔고 조회
    balance_data = get_real_balance()
    if not balance_data or balance_data.get('rt_cd') != '0':
        print("❌ 잔고 조회 실패")
        return

    output1 = balance_data.get('output1', [])
    output2 = balance_data.get('output2', [{}])[0]

    # 기존 Firebase 포트폴리오 삭제
    portfolio_docs = db.collection('portfolio').stream()
    for doc in portfolio_docs:
        doc.reference.delete()

    print("🗑️ 기존 포트폴리오 데이터 삭제 완료")

    # 실제 보유 종목만 Firebase에 추가
    for stock in output1:
        quantity = int(float(stock.get('hldg_qty', 0)))
        if quantity > 0:
            code = stock.get('pdno')
            name = get_stock_name(code)
            buy_avg = float(stock.get('pchs_avg_pric', 0))
            current = float(stock.get('prpr', 0))
            profit_amt = float(stock.get('evlu_pfls_amt', 0))
            profit_rate = float(stock.get('evlu_pfls_rt', 0))

            portfolio_data = {
                'code': code,
                'name': name,
                'quantity': quantity,
                'buy_price': buy_avg,
                'current_price': current,
                'profit_amount': profit_amt,
                'profit_rate': profit_rate,
                'total_value': current * quantity,
                'status': 'holding',
                'last_updated': firestore.SERVER_TIMESTAMP
            }

            db.collection('portfolio').document(code).set(portfolio_data)
            print(f"✅ {name}({code}) 업데이트: {quantity}주, {profit_rate:+.2f}%")

    # 계좌 요약 업데이트
    total_cash = float(output2.get('dnca_tot_amt', 0))
    total_value = float(output2.get('tot_evlu_amt', 0))
    total_profit = float(output2.get('evlu_pfls_smtl_amt', 0))

    account_summary = {
        'total_cash': total_cash,
        'total_value': total_value,
        'total_profit': total_profit,
        'profit_rate': (total_profit / total_value * 100) if total_value > 0 else 0,
        'last_updated': firestore.SERVER_TIMESTAMP
    }

    db.collection('account').document('summary').set(account_summary)
    print(f"✅ 계좌 요약 업데이트: 총자산 {total_value:,.0f}원, 수익 {total_profit:+,.0f}원")

    print("🎉 Firebase 동기화 완료!")

if __name__ == "__main__":
    sync_to_firebase()