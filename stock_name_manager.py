#!/usr/bin/env python3
"""종목명 관리 모듈 - 웹 크롤링 + Firebase 캐싱"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import time

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

class StockNameManager:
    def __init__(self):
        self.db = firestore.client()
        # Firebase에 stock_names 컬렉션 사용 (종목명 캐싱)
        self.cache_collection = 'stock_names'

    def get_stock_name(self, stock_code):
        """종목명 조회 - 캐시 우선, 없으면 웹에서 조회"""

        # 1. Firebase 캐시에서 먼저 확인
        cached_name = self._get_cached_name(stock_code)
        if cached_name:
            return cached_name

        # 2. 웹에서 종목명 조회
        stock_name = self._fetch_name_from_web(stock_code)

        # 3. 조회 성공시 캐시에 저장
        if stock_name:
            self._cache_name(stock_code, stock_name)

        return stock_name

    def _get_cached_name(self, stock_code):
        """Firebase에서 캐시된 종목명 조회"""
        try:
            doc = self.db.collection(self.cache_collection).document(stock_code).get()
            if doc.exists:
                return doc.to_dict().get('name')
        except Exception as e:
            print(f"캐시 조회 오류: {e}")
        return None

    def _cache_name(self, stock_code, stock_name):
        """Firebase에 종목명 캐싱"""
        try:
            self.db.collection(self.cache_collection).document(stock_code).set({
                'code': stock_code,
                'name': stock_name,
                'cached_at': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"캐시 저장 오류: {e}")

    def _fetch_name_from_web(self, stock_code):
        """네이버 금융에서 종목명 조회"""
        try:
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 종목명 추출 (여러 방법 시도)
                # 방법 1: wrap_company h2 태그
                name_tag = soup.find('div', {'class': 'wrap_company'})
                if name_tag:
                    h2_tag = name_tag.find('h2')
                    if h2_tag:
                        return h2_tag.text.strip()

                # 방법 2: title 태그에서 추출
                title_tag = soup.find('title')
                if title_tag and ':' in title_tag.text:
                    return title_tag.text.split(':')[0].strip()

        except Exception as e:
            print(f"웹 조회 오류 ({stock_code}): {e}")

        return None

    def update_all_stock_names(self):
        """모든 포트폴리오와 감시 종목의 이름 업데이트"""
        updated = []

        # 포트폴리오 종목
        portfolio_docs = self.db.collection('portfolio').get()
        for doc in portfolio_docs:
            stock_code = doc.id
            stock_name = self.get_stock_name(stock_code)
            if stock_name:
                self.db.collection('portfolio').document(stock_code).update({
                    'name': stock_name
                })
                updated.append((stock_code, stock_name))
                time.sleep(0.5)  # 과도한 요청 방지

        # market_scan 종목
        scan_doc = self.db.collection('market_scan').document('latest').get()
        if scan_doc.exists:
            data = scan_doc.to_dict()
            stocks = data.get('stocks', [])

            for stock in stocks:
                stock_code = stock.get('code')
                if stock_code:
                    stock_name = self.get_stock_name(stock_code)
                    if stock_name:
                        stock['name'] = stock_name
                        updated.append((stock_code, stock_name))
                        time.sleep(0.5)  # 과도한 요청 방지

            self.db.collection('market_scan').document('latest').update({
                'stocks': stocks
            })

        return updated

# 사용 예제
if __name__ == "__main__":
    manager = StockNameManager()

    # 테스트
    test_codes = ["090710", "317830", "319400", "005930"]

    print("종목명 조회 테스트")
    print("=" * 50)

    for code in test_codes:
        name = manager.get_stock_name(code)
        if name:
            print(f"✅ {code}: {name}")
        else:
            print(f"❌ {code}: 조회 실패")