#!/usr/bin/env python3
"""실제 계좌 잔고 확인"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# 토큰 가져오기
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    token = token_data.get('token')

account_no = os.getenv('KIS_ACCOUNT_NUMBER')
if '-' not in account_no:
    account_no = f"{account_no}-01"

# 잔고 조회 API
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

response = requests.get(url, headers=headers, params=params)

print("=" * 60)
print("📊 실제 계좌 잔고 조회")
print("=" * 60)

if response.status_code == 200:
    data = response.json()
    if data.get('rt_cd') == '0':
        # 보유 주식 목록
        output1 = data.get('output1', [])
        output2 = data.get('output2', [{}])[0]

        print(f"\n💰 계좌 요약:")
        print(f"  예수금총액: {int(float(output2.get('dnca_tot_amt', 0))):,}원")
        print(f"  총평가금액: {int(float(output2.get('tot_evlu_amt', 0))):,}원")
        print(f"  총손익금액: {int(float(output2.get('evlu_pfls_smtl_amt', 0))):,}원")
        print(f"  총손익률: {float(output2.get('evlu_pfls_rt', 0)):.2f}%")

        print(f"\n📋 보유 종목 ({len(output1)}개):")
        for stock in output1:
            if float(stock.get('hldg_qty', 0)) > 0:  # 보유수량이 있는 것만
                code = stock.get('pdno')
                name = stock.get('prdt_name')
                quantity = int(float(stock.get('hldg_qty', 0)))
                buy_avg = int(float(stock.get('pchs_avg_pric', 0)))
                current = int(float(stock.get('prpr', 0)))
                profit_rate = float(stock.get('evlu_pfls_rt', 0))
                profit_amt = int(float(stock.get('evlu_pfls_amt', 0)))

                print(f"\n  [{code}] {name}")
                print(f"    보유수량: {quantity}주")
                print(f"    매수평균가: {buy_avg:,}원")
                print(f"    현재가: {current:,}원")
                print(f"    평가손익: {profit_amt:+,}원 ({profit_rate:+.2f}%)")
    else:
        print(f"오류: {data.get('msg1')}")
else:
    print(f"API 오류: {response.status_code}")

print("\n" + "=" * 60)