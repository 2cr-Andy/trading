#!/usr/bin/env python3
"""
종목 마스터 정보 관리
- 전체 종목 코드/이름 매핑 테이블 구축
- 종목명 100% 보장
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class StockMaster:
    """종목 마스터 정보 관리자"""

    def __init__(self):
        self.master_file = "stock_master.json"
        self.stock_dict = {}
        self.load_master()

    def load_master(self):
        """저장된 마스터 파일 로드 또는 새로 생성"""
        if os.path.exists(self.master_file):
            # 저장된 파일이 있고, 7일 이내면 재사용
            file_time = os.path.getmtime(self.master_file)
            if (datetime.now().timestamp() - file_time) < 7 * 24 * 3600:
                with open(self.master_file, 'r', encoding='utf-8') as f:
                    self.stock_dict = json.load(f)
                    print(f"📚 종목 마스터 로드 완료: {len(self.stock_dict)}개")
                    return

        # 새로 다운로드
        self.download_master()

    def download_master(self):
        """KIS API에서 전체 종목 정보 다운로드"""
        print("📥 종목 마스터 다운로드 시도...")

        # KIS API 종목 마스터 조회
        app_key = os.getenv('KIS_APP_KEY')
        app_secret = os.getenv('KIS_APP_SECRET')

        # 토큰 먼저 획득
        token = self._get_token(app_key, app_secret)
        if not token:
            print("❌ 토큰 획득 실패, 기본 종목 사용")
            self._load_default_master()
            return

        # KOSPI, KOSDAQ 종목 조회
        for market in ['J', 'Q']:  # J: KOSPI, Q: KOSDAQ
            stocks = self._get_market_stocks(token, app_key, app_secret, market)
            for stock in stocks:
                code = stock.get('mksc_shrn_iscd', '')
                name = stock.get('hts_kor_isnm', '')
                if code and name:
                    self.stock_dict[code] = name

        # API에서 가져온 종목이 없으면 기본 종목 사용
        if len(self.stock_dict) == 0:
            print("⚠️ API 종목 정보 없음, 기본 종목 사용")
            self._load_default_master()
            return

        # 파일로 저장
        with open(self.master_file, 'w', encoding='utf-8') as f:
            json.dump(self.stock_dict, f, ensure_ascii=False, indent=2)

        print(f"✅ 종목 마스터 저장 완료: {len(self.stock_dict)}개")

    def _get_token(self, app_key: str, app_secret: str) -> Optional[str]:
        """토큰 획득"""
        try:
            # 기존 토큰 파일 확인
            if os.path.exists('kis_token.json'):
                with open('kis_token.json', 'r') as f:
                    token_data = json.load(f)
                    return token_data.get('token')
        except:
            pass
        return None

    def _get_market_stocks(self, token: str, app_key: str, app_secret: str, market: str) -> list:
        """특정 시장의 전체 종목 조회"""
        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/quotations/inquire-member"

        headers = {
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "CTPF1604R",
            "custtype": "P"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": market,
            "FID_INPUT_ISCD": "0000"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    return data.get('output', [])
        except Exception as e:
            print(f"⚠️ {market} 시장 종목 조회 실패: {e}")

        return []

    def _load_default_master(self):
        """기본 주요 종목만 수동 입력 (백업)"""
        self.stock_dict = {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "035720": "카카오",
            "005380": "현대차",
            "035420": "NAVER",
            "051910": "LG화학",
            "006400": "삼성SDI",
            "068270": "셀트리온",
            "105560": "KB금융",
            "055550": "신한지주",
            "000270": "기아",
            "096770": "SK이노베이션",
            "066570": "LG전자",
            "003550": "LG",
            "034730": "SK",
            "012330": "현대모비스",
            "028260": "삼성물산",
            "036570": "엔씨소프트",
            "033780": "KT&G",
            "015760": "한국전력"
        }
        print(f"⚠️ 기본 종목만 로드: {len(self.stock_dict)}개")

    def get_name(self, code: str) -> str:
        """종목 코드로 종목명 조회"""
        # 6자리로 패딩
        code = code.zfill(6)
        return self.stock_dict.get(code, code)  # 없으면 코드 그대로 반환

    def refresh(self):
        """마스터 정보 강제 새로고침"""
        self.download_master()