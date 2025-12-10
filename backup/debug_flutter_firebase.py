#!/usr/bin/env python3
"""Flutter Firebase 연결 디버깅"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def debug_firebase_structure():
    """Firebase 데이터 구조 상세 분석"""
    print("🔍 Firebase 데이터 구조 상세 분석")
    print("=" * 60)

    # 1. market_scan/latest 구조 분석
    print("\n1. 📊 market_scan/latest 구조:")
    try:
        doc = db.collection('market_scan').document('latest').get()
        if doc.exists:
            data = doc.to_dict()
            print(f"   ✅ 문서 존재: {len(data.keys())} 개 필드")
            print(f"   📋 필드 목록: {list(data.keys())}")

            stocks = data.get('stocks', [])
            print(f"   📈 stocks 배열 크기: {len(stocks)}")

            if len(stocks) > 0:
                first_stock = stocks[0]
                print(f"   🔍 첫 번째 종목 구조:")
                for key, value in first_stock.items():
                    print(f"       {key}: {value} ({type(value).__name__})")
        else:
            print("   ❌ market_scan/latest 문서 없음")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 2. portfolio 구조 분석
    print("\n2. 💼 portfolio 구조:")
    try:
        docs = db.collection('portfolio').limit(1).get()
        if docs:
            doc = docs[0]
            data = doc.to_dict()
            print(f"   ✅ 문서 ID: {doc.id}")
            print(f"   📋 필드 구조:")
            for key, value in data.items():
                print(f"       {key}: {value} ({type(value).__name__})")
        else:
            print("   ❌ portfolio 컬렉션 비어있음")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 3. account 구조 분석
    print("\n3. 📊 account 구조:")
    try:
        doc = db.collection('account').document('summary').get()
        if doc.exists:
            data = doc.to_dict()
            print(f"   ✅ account/summary 존재")
            for key, value in data.items():
                print(f"       {key}: {value} ({type(value).__name__})")
        else:
            print("   ❌ account/summary 문서 없음")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

def check_firebase_permissions():
    """Firebase 권한 확인"""
    print("\n🔑 Firebase 권한 확인")
    print("=" * 30)

    try:
        # 읽기 권한 테스트
        collections = ['market_scan', 'portfolio', 'account', 'bot_status']
        for collection_name in collections:
            try:
                docs = db.collection(collection_name).limit(1).get()
                print(f"   ✅ {collection_name}: 읽기 권한 OK")
            except Exception as e:
                print(f"   ❌ {collection_name}: 읽기 권한 오류 - {e}")

    except Exception as e:
        print(f"   ❌ 전체 권한 오류: {e}")

def simulate_flutter_data_read():
    """Flutter가 읽는 방식으로 데이터 시뮬레이션"""
    print("\n🎯 Flutter 데이터 읽기 시뮬레이션")
    print("=" * 40)

    try:
        # market_scan 시뮬레이션
        print("1. market_scan 읽기 시뮬레이션:")
        doc = db.collection('market_scan').document('latest').get()
        if doc.exists:
            data = doc.to_dict()
            stocks = data.get('stocks', [])

            print(f"   stocks 배열에서 처음 3개 종목:")
            for i, stock in enumerate(stocks[:3]):
                print(f"   종목 {i+1}:")
                print(f"     code: {stock.get('code', 'N/A')}")
                print(f"     name: {stock.get('name', 'N/A')}")
                print(f"     current_price: {stock.get('current_price', 0)}")
                print(f"     change_rate: {stock.get('change_rate', 0)}")
                print(f"     volume: {stock.get('volume', 0)}")
                print(f"     rsi: {stock.get('rsi', 50)}")
                print(f"     mfi: {stock.get('mfi', 50)}")
                print(f"     buy_signal: {stock.get('buy_signal', False)}")
                print()

        # portfolio 시뮬레이션
        print("2. portfolio 읽기 시뮬레이션:")
        docs = db.collection('portfolio').limit(3).get()
        for doc in docs:
            data = doc.to_dict()
            print(f"   종목 {doc.id}:")
            print(f"     name: {data.get('name', 'N/A')}")
            print(f"     buy_price: {data.get('buy_price', 0)}")
            print(f"     current_price: {data.get('current_price', 0)}")
            print(f"     quantity: {data.get('quantity', 0)}")
            print(f"     profit_amount: {data.get('profit_amount', 0)}")
            print()

    except Exception as e:
        print(f"   ❌ 시뮬레이션 오류: {e}")

if __name__ == "__main__":
    debug_firebase_structure()
    check_firebase_permissions()
    simulate_flutter_data_read()