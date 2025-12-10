#!/usr/bin/env python3
"""종목명 데이터베이스 - 하드코딩된 주요 종목들"""

# 자주 사용되는 종목들의 종목명 매핑
STOCK_NAME_MAP = {
    # 대형주
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "035720": "카카오",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "005380": "현대차",
    "000270": "기아",
    "068270": "셀트리온",
    "105560": "KB금융",
    "055550": "신한지주",
    "086790": "하나금융지주",
    "003670": "포스코퓨처엠",
    "028260": "삼성물산",
    "012330": "현대모비스",

    # 중소형주 (실제 사용 종목)
    "007460": "에이프로젠",
    "043260": "성호전자",
    "013360": "일성건설",
    "220260": "켐트로스",
    "090710": "휴림로봇",
    "317830": "에스피시스템스",
    "319400": "현대무벡스",
    "101170": "우림피티에스",
    "092200": "디아이씨",
    "424870": "티엘엠티",

    # 추가 종목들
    "007480": "에이프로젠",
    "013360": "일성건설",
    "317530": "캐리소프트",
    "004720": "팜스코",
    "145020": "휴젤",
    "214150": "클래시스",
    "033250": "체시스",
    "047560": "이스트소프트",
    "138070": "신진에스엠",
    "036830": "솔브레인홀딩스",
    "001380": "SG글로벌",
    "009160": "SIMPAC",
    "032850": "비트컴퓨터",
    "131370": "알서포트",
    "298050": "효성첨단소재",
    "281740": "레이크머티리얼즈",
    "180640": "한진칼",
    "003550": "LG",
    "207940": "삼성바이오로직스",
    "005490": "POSCO홀딩스",
    "373220": "LG에너지솔루션",
    "247540": "에코프로비엠",
    "086520": "에코프로",
    "022100": "포스코DX",
    "091990": "셀트리온헬스케어",
    "196170": "알테오젠",
    "145020": "휴젤",
    "128940": "한미약품",
    "326030": "SK바이오팜",
    "302440": "SK바이오사이언스",
}

def get_stock_name(stock_code):
    """종목 코드로 종목명 조회"""
    return STOCK_NAME_MAP.get(stock_code, stock_code)

def add_stock_name(stock_code, stock_name):
    """새로운 종목명 추가"""
    STOCK_NAME_MAP[stock_code] = stock_name

def update_stock_names_in_firebase():
    """Firebase의 모든 종목에 종목명 업데이트"""
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

    print("📝 종목명 업데이트 시작...")

    # 1. 포트폴리오 업데이트
    portfolio_docs = db.collection('portfolio').get()
    for doc in portfolio_docs:
        stock_code = doc.id
        stock_name = get_stock_name(stock_code)
        if stock_name != stock_code:  # 종목명이 있는 경우
            db.collection('portfolio').document(stock_code).update({
                'name': stock_name
            })
            print(f"✅ 포트폴리오: {stock_code} → {stock_name}")

    # 2. market_scan 업데이트
    scan_doc = db.collection('market_scan').document('latest').get()
    if scan_doc.exists:
        data = scan_doc.to_dict()
        stocks = data.get('stocks', [])

        updated = False
        for stock in stocks:
            stock_code = stock.get('code')
            if stock_code:
                stock_name = get_stock_name(stock_code)
                if stock_name != stock_code:
                    stock['name'] = stock_name
                    updated = True
                    print(f"✅ 감시종목: {stock_code} → {stock_name}")

        if updated:
            db.collection('market_scan').document('latest').update({
                'stocks': stocks
            })

    print("✅ 종목명 업데이트 완료!")

if __name__ == "__main__":
    update_stock_names_in_firebase()