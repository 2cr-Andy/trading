#!/usr/bin/env python3
"""종목명 조회 API 테스트"""

import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

def get_stock_name_from_api(stock_code):
    """KIS API를 통한 종목명 조회"""

    # kis_token.json에서 토큰 읽기
    with open('kis_token.json', 'r') as f:
        token_data = json.load(f)
        access_token = token_data.get('token')

    # 주식 기본 정보 조회 API (상품기본조회)
    headers = {
        "authorization": f"Bearer {access_token}",
        "appkey": os.getenv('KIS_APP_KEY'),
        "appsecret": os.getenv('KIS_APP_SECRET'),
        "tr_id": "CTPF1002R",  # 주식/ETF 상품기본조회
        "custtype": "P"
    }

    params = {
        "PDNO": stock_code,  # 상품번호(종목코드)
        "PRDT_TYPE_CD": "300"  # 상품유형코드 (300: 주식)
    }

    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/search-stock-info"

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        if data.get('rt_cd') == '0':
            output = data.get('output', {})
            stock_name = output.get('prdt_abrv_name', '')  # 종목약명
            if not stock_name:
                stock_name = output.get('prdt_name', '')  # 종목명
            return stock_name

    return None

def test_all_stocks():
    """모든 보유 종목 테스트"""
    test_codes = [
        "090710",  # 휴림로봇
        "317830",  # 에스피시스템스
        "319400",  # 현대무벡스
        "007460",  # 에이프로젠
        "122630",  # KODEX 레버리지
    ]

    print("종목명 API 조회 테스트")
    print("=" * 50)

    for code in test_codes:
        name = get_stock_name_from_api(code)
        if name:
            print(f"✅ {code}: {name}")
        else:
            print(f"❌ {code}: 조회 실패")

if __name__ == "__main__":
    test_all_stocks()