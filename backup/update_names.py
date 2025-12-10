#!/usr/bin/env python3
"""Firebase 종목명 업데이트 스크립트"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 종목명 매핑 (임시)
stock_names = {
    "090710": "휴림로봇",
    "317830": "에스피시스템스",
    "319400": "현대무벡스",
    "007460": "에이프로젠",
    "030530": "원익홀딩스",
    "215600": "신라젠",
    "042940": "광전자",
    "043260": "성호전자",
    "101170": "우림피티에스",
    "049630": "재영솔루텍",
    "001360": "삼성제약",
    "380540": "디오스텍",
    "424870": "티엠티",
    "092200": "디아이씨",
    "462330": "이지트로닉스",
    "450140": "케이피에스",
    "122630": "KODEX 레버리지",
    "004310": "현대약품",
    "220260": "켐트로스",  # 추가된 종목
}

# Portfolio 업데이트
print("포트폴리오 종목명 업데이트 중...")
portfolio_docs = db.collection('portfolio').get()
for doc in portfolio_docs:
    code = doc.id
    if code in stock_names:
        db.collection('portfolio').document(code).update({
            'name': stock_names[code]
        })
        print(f"  - {code}: {stock_names[code]} 업데이트 완료")

# market_scan 업데이트
print("\n감시 종목 업데이트 중...")
scan_doc = db.collection('market_scan').document('latest').get()
if scan_doc.exists:
    data = scan_doc.to_dict()
    stocks = data.get('stocks', [])

    updated_count = 0
    for stock in stocks:
        code = stock.get('code')
        if code in stock_names:
            stock['name'] = stock_names[code]
            print(f"  - {code}: {stock_names[code]} 업데이트")
            updated_count += 1
        else:
            # 매핑에 없는 종목은 코드를 그대로 유지
            print(f"  - {code}: 종목명 매핑 없음 (코드 유지)")

    db.collection('market_scan').document('latest').update({
        'stocks': stocks
    })
    print(f"  - 총 {updated_count}/{len(stocks)}개 종목 업데이트 완료")

print("\n✅ 모든 업데이트 완료!")