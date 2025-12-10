#!/usr/bin/env python3
"""Firebase 모든 데이터 확인"""

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

def check_all_data():
    print("=== Firebase 전체 데이터 확인 ===\n")

    # 1. account 컬렉션 확인
    print("1. 📊 계좌 정보 (account 컬렉션):")
    try:
        account_docs = db.collection('account').get()
        if account_docs:
            for doc in account_docs:
                print(f"   - {doc.id}: {doc.to_dict()}")
        else:
            print("   ❌ account 컬렉션이 비어있음")
    except Exception as e:
        print(f"   ❌ account 조회 오류: {e}")

    # 2. bot_status 컬렉션 확인
    print("\n2. 🤖 봇 상태 (bot_status 컬렉션):")
    try:
        bot_docs = db.collection('bot_status').get()
        if bot_docs:
            for doc in bot_docs:
                print(f"   - {doc.id}: {doc.to_dict()}")
        else:
            print("   ❌ bot_status 컬렉션이 비어있음")
    except Exception as e:
        print(f"   ❌ bot_status 조회 오류: {e}")

    # 3. portfolio 컬렉션 상세 확인
    print("\n3. 💼 포트폴리오 상세 (portfolio 컬렉션):")
    try:
        portfolio_docs = db.collection('portfolio').get()
        if portfolio_docs:
            for doc in portfolio_docs:
                data = doc.to_dict()
                print(f"   종목: {doc.id}")
                for key, value in data.items():
                    print(f"     {key}: {value}")
                print()
        else:
            print("   ❌ portfolio 컬렉션이 비어있음")
    except Exception as e:
        print(f"   ❌ portfolio 조회 오류: {e}")

    # 4. market_scan 첫 번째 종목 상세 확인
    print("\n4. 📈 감시목록 첫 번째 종목 상세:")
    try:
        scan_doc = db.collection('market_scan').document('latest').get()
        if scan_doc.exists:
            data = scan_doc.to_dict()
            stocks = data.get('stocks', [])
            if stocks:
                first_stock = stocks[0]
                print(f"   첫 번째 종목: {first_stock.get('code')}")
                for key, value in first_stock.items():
                    print(f"     {key}: {value}")
            else:
                print("   ❌ stocks 배열이 비어있음")
        else:
            print("   ❌ market_scan/latest 문서가 없음")
    except Exception as e:
        print(f"   ❌ market_scan 조회 오류: {e}")

    # 5. 모든 컬렉션 목록 확인
    print("\n5. 📋 모든 컬렉션 목록:")
    try:
        collections = db.collections()
        for collection in collections:
            print(f"   - {collection.id}")
    except Exception as e:
        print(f"   ❌ 컬렉션 목록 조회 오류: {e}")

if __name__ == "__main__":
    check_all_data()