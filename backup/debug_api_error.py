#!/usr/bin/env python3
"""API 500 에러 디버깅"""

import os
import json
import requests
from dotenv import load_dotenv
import hashlib

load_dotenv()

print("=" * 60)
print("🔍 KIS API 500 에러 원인 분석")
print("=" * 60)

# 1. 환경변수 확인
print("\n1. 환경변수 확인:")
app_key = os.getenv('KIS_APP_KEY')
app_secret = os.getenv('KIS_APP_SECRET')
account_no = os.getenv('KIS_ACCOUNT_NUMBER')

print(f"  APP_KEY: {app_key[:10]}..." if app_key else "  APP_KEY: 없음")
print(f"  APP_SECRET: {app_secret[:10]}..." if app_secret else "  APP_SECRET: 없음")
print(f"  계좌번호: {account_no}" if account_no else "  계좌번호: 없음")

# 2. 토큰 확인
print("\n2. 토큰 상태:")
try:
    with open('kis_token.json', 'r') as f:
        token_data = json.load(f)
        token = token_data.get('token')
        expires_at = token_data.get('expires_at')
        created_at = token_data.get('created_at')

        print(f"  토큰: {token[:20]}..." if token else "  토큰: 없음")
        print(f"  생성시간: {created_at}")
        print(f"  만료시간: {expires_at}")

        # 토큰 유효성 체크
        import time
        if expires_at and time.time() > expires_at:
            print("  ⚠️ 토큰이 만료되었습니다!")
except Exception as e:
    print(f"  ❌ 토큰 파일 오류: {e}")

# 3. 해시키 생성
print("\n3. 해시키 생성 방식:")
if app_secret:
    # 방법 1: SHA256 (새로운 방식)
    hash_key_sha256 = hashlib.sha256(app_secret.encode()).hexdigest()
    print(f"  SHA256: {hash_key_sha256[:20]}...")

    # 방법 2: SHA512 (구 방식)
    hash_key_sha512 = hashlib.sha512(app_secret.encode()).hexdigest()
    print(f"  SHA512: {hash_key_sha512[:20]}...")

# 4. 계좌번호 형식
print("\n4. 계좌번호 형식 테스트:")
if account_no:
    print(f"  원본: {account_no}")

    if '-' in account_no:
        parts = account_no.split('-')
        print(f"  분리: CANO={parts[0]}, ACNT_PRDT_CD={parts[1]}")
    else:
        print(f"  분리: CANO={account_no}, ACNT_PRDT_CD=01 (기본값)")
        account_no = f"{account_no}-01"

# 5. API 테스트 (간단한 조회)
print("\n5. API 테스트:")

# 5-1. 현재가 조회 (단순 조회)
print("\n  [현재가 조회 테스트]")
url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price"
headers = {
    "authorization": f"Bearer {token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "FHKST01010100"
}
params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_ISCD": "005930"  # 삼성전자
}

try:
    response = requests.get(url, headers=headers, params=params)
    print(f"    상태코드: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"    응답: {data.get('rt_cd')} - {data.get('msg1')}")
    else:
        print(f"    에러: {response.text[:200]}")
except Exception as e:
    print(f"    예외: {e}")

# 5-2. 잔고 조회 (인증 필요)
print("\n  [잔고 조회 테스트]")

# hashkey 생성 (잔고 조회는 hashkey 필요)
def make_hashkey(data):
    """POST 요청용 hashkey 생성"""
    datas = json.dumps(data)
    h = hashlib.sha256(datas.encode()).digest()
    return h.hex()

# GET 요청은 hashkey 불필요하지만, 파라미터 확인
url2 = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance"
headers2 = {
    "authorization": f"Bearer {token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "VTTC8434R"
}

if '-' in account_no:
    cano = account_no.split('-')[0]
    acnt_prdt_cd = account_no.split('-')[1]
else:
    cano = account_no
    acnt_prdt_cd = "01"

params2 = {
    "CANO": cano,
    "ACNT_PRDT_CD": acnt_prdt_cd,
    "AFHR_FLPR_YN": "N",
    "OFL_YN": "",
    "INQR_DVSN": "02",
    "UNPR_DVSN": "01",
    "FUND_STTL_ICLD_YN": "N",
    "FNCG_AMT_AUTO_RDPT_YN": "N",
    "PRCS_DVSN": "00",
    "CTX_AREA_FK100": "",
    "CTX_AREA_NK100": ""
}

print(f"    계좌: CANO={cano}, ACNT_PRDT_CD={acnt_prdt_cd}")

try:
    response2 = requests.get(url2, headers=headers2, params=params2)
    print(f"    상태코드: {response2.status_code}")

    if response2.status_code == 200:
        data = response2.json()
        print(f"    응답: {data.get('rt_cd')} - {data.get('msg1')}")
    elif response2.status_code == 500:
        print(f"    ❌ 500 에러 발생!")
        print(f"    응답 헤더: {dict(response2.headers)}")
        print(f"    응답 내용: {response2.text[:500]}")
    else:
        print(f"    에러 응답: {response2.text[:200]}")

except Exception as e:
    print(f"    예외: {e}")

print("\n" + "=" * 60)
print("분석 완료")
print("=" * 60)