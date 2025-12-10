#!/usr/bin/env python3
"""포트폴리오 업데이트 테스트"""

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
    try:
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            return token_data.get('token')
    except:
        return None

def test_update():
    print("🧪 포트폴리오 업데이트 테스트 시작...")

    token = get_access_token()
    if not token:
        print("❌ 토큰이 없습니다")
        return

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
        print("📡 KIS API 잔고 조회 중...")
        response = requests.get(url, headers=headers, params=params, timeout=10)

        print(f"📊 응답 상태: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"📋 API 응답: {data.get('rt_cd')} - {data.get('msg1')}")

            if data.get('rt_cd') == '0':
                output1 = data.get('output1', [])
                print(f"📈 보유 종목 수: {len(output1)}")

                for stock in output1[:3]:  # 처음 3개만
                    code = stock.get('pdno')
                    quantity = int(float(stock.get('hldg_qty', 0)))
                    current_price = float(stock.get('prpr', 0))
                    profit_rate = float(stock.get('evlu_pfls_rt', 0))

                    if quantity > 0:
                        print(f"  📌 {code}: {quantity}주, {current_price:,.0f}원, {profit_rate:+.2f}%")

                        # Firebase 업데이트
                        try:
                            db.collection('portfolio').document(code).update({
                                'current_price': current_price,
                                'profit_rate': profit_rate,
                                'last_updated': firestore.SERVER_TIMESTAMP
                            })
                            print(f"    ✅ Firebase 업데이트 완료")
                        except Exception as e:
                            print(f"    ❌ Firebase 업데이트 실패: {e}")

            else:
                print(f"❌ API 오류: {data.get('msg1')}")
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
            print(f"응답 내용: {response.text[:200]}")

    except Exception as e:
        print(f"❌ 요청 실패: {e}")

if __name__ == "__main__":
    test_update()
    print("\n✅ 테스트 완료")