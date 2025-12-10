#!/usr/bin/env python3

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

# market_scan 데이터 확인
print("=== Firebase 데이터 확인 ===\n")

doc = db.collection('market_scan').document('latest').get()
if doc.exists:
    data = doc.to_dict()
    print(f'1. market_scan/latest')
    print(f'   - 총 종목 수: {len(data.get("stocks", []))}')
    if data.get('stocks'):
        stock = data['stocks'][0]
        print(f'   - 첫 번째 종목:')
        for key, value in stock.items():
            print(f'     {key}: {value}')

# portfolio 데이터 확인
print(f'\n2. portfolio')
portfolio_docs = db.collection('portfolio').get()
for doc in portfolio_docs:
    print(f'   - {doc.id}: {doc.to_dict()}')