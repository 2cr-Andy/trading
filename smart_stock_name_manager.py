#!/usr/bin/env python3
"""스마트 종목명 관리자 - 자동으로 종목명 수집 및 캐싱"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import time
import json

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

class SmartStockNameManager:
    def __init__(self):
        self.db = firestore.client()
        self.cache_file = "stock_names_cache.json"
        self.cache = self._load_cache()

    def _load_cache(self):
        """로컬 캐시 파일 로드"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        """로컬 캐시 파일 저장"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get_stock_name(self, stock_code):
        """종목명 조회 - 캐시 우선, 없으면 네이버에서 자동 조회"""

        # 1. 로컬 캐시 확인
        if stock_code in self.cache:
            return self.cache[stock_code]

        # 2. Firebase 캐시 확인
        try:
            doc = self.db.collection('stock_names').document(stock_code).get()
            if doc.exists:
                name = doc.to_dict().get('name')
                if name:
                    self.cache[stock_code] = name
                    self._save_cache()
                    return name
        except:
            pass

        # 3. 네이버 금융에서 자동 조회
        name = self._fetch_from_naver(stock_code)

        if name:
            # 캐시에 저장
            self.cache[stock_code] = name
            self._save_cache()

            # Firebase에도 저장
            try:
                self.db.collection('stock_names').document(stock_code).set({
                    'code': stock_code,
                    'name': name,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            except:
                pass

            print(f"✅ 새 종목 발견: {stock_code} → {name}")
            return name

        # 조회 실패시 코드 반환
        return stock_code

    def _fetch_from_naver(self, stock_code):
        """네이버 금융에서 종목명 자동 조회"""
        try:
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 종목명 추출 시도 1: h2 태그
                h2_tag = soup.select_one('div.wrap_company h2')
                if h2_tag:
                    return h2_tag.text.strip()

                # 종목명 추출 시도 2: title 태그
                title = soup.find('title')
                if title and ':' in title.text:
                    return title.text.split(':')[0].strip()

        except Exception as e:
            print(f"⚠️ 네이버 조회 실패 ({stock_code}): {e}")

        return None

    def update_all_stocks(self):
        """모든 종목의 이름 자동 업데이트"""
        print("🤖 스마트 종목명 업데이트 시작...")
        updated_count = 0

        # 1. 포트폴리오 종목
        portfolio_docs = self.db.collection('portfolio').get()
        for doc in portfolio_docs:
            stock_code = doc.id
            data = doc.to_dict()

            # 종목명이 없거나 코드와 같은 경우
            if not data.get('name') or data.get('name') == stock_code:
                name = self.get_stock_name(stock_code)
                if name != stock_code:
                    self.db.collection('portfolio').document(stock_code).update({
                        'name': name
                    })
                    updated_count += 1
                    time.sleep(0.5)  # 과도한 요청 방지

        # 2. market_scan 종목
        scan_doc = self.db.collection('market_scan').document('latest').get()
        if scan_doc.exists:
            data = scan_doc.to_dict()
            stocks = data.get('stocks', [])

            need_update = False
            for stock in stocks:
                stock_code = stock.get('code')
                if stock_code:
                    # 종목명이 없거나 코드와 같은 경우
                    if not stock.get('name') or stock.get('name') == stock_code:
                        name = self.get_stock_name(stock_code)
                        if name != stock_code:
                            stock['name'] = name
                            need_update = True
                            updated_count += 1
                            time.sleep(0.5)  # 과도한 요청 방지

            if need_update:
                self.db.collection('market_scan').document('latest').update({
                    'stocks': stocks
                })

        print(f"✅ 총 {updated_count}개 종목명 업데이트 완료!")
        return updated_count

    def preload_common_stocks(self):
        """주요 종목 미리 로드"""
        common_codes = [
            "005930", "000660", "035420", "035720", "051910",  # 대형주
            "006400", "005380", "000270", "068270", "105560",
            "055550", "086790", "003670", "028260", "012330"
        ]

        print("📦 주요 종목 사전 로드 중...")
        for code in common_codes:
            if code not in self.cache:
                name = self.get_stock_name(code)
                if name != code:
                    print(f"  {code}: {name}")
                time.sleep(0.3)

# 전역 인스턴스
_manager_instance = None

def get_manager():
    """싱글톤 매니저 반환"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SmartStockNameManager()
    return _manager_instance

def get_stock_name(stock_code):
    """간편 함수 - 종목명 조회"""
    return get_manager().get_stock_name(stock_code)

def update_all():
    """간편 함수 - 전체 업데이트"""
    return get_manager().update_all_stocks()

if __name__ == "__main__":
    manager = SmartStockNameManager()

    # 테스트
    print("🧪 테스트 시작")
    print("=" * 50)

    # 신규 종목 테스트
    test_codes = ["005930", "035720", "999999", "090710", "NEW123"]

    for code in test_codes:
        name = manager.get_stock_name(code)
        print(f"{code}: {name}")
        time.sleep(0.5)

    print("\n전체 업데이트 실행...")
    manager.update_all_stocks()