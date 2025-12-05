"""
KIS 자동매매 봇 - 로깅 개선 버전
BrokenPipeError 해결 및 실시간 슬랙 알림
"""

import os
import sys
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from market_scanner import MarketScanner
import pytz
from slack_notifier import SlackNotifier
from logger_system import UnifiedLogger
from token_manager import TokenManager
import warnings

# Firebase 경고 무시
warnings.filterwarnings('ignore', category=UserWarning, module='google.cloud.firestore')

# stdout 버퍼 비활성화로 BrokenPipe 방지
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)

# 환경 변수 로드
load_dotenv()

class KISBot:
    def __init__(self):
        """KIS 자동매매 봇 초기화"""
        # 통합 로거를 가장 먼저 초기화
        self.logger = UnifiedLogger(log_dir="logs", slack_enabled=True)

        try:
            # Firebase 초기화
            cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY_PATH'))
            firebase_admin.initialize_app(cred)
            self.db = firestore.client()

            # KIS API 설정
            self.app_key = os.getenv('KIS_APP_KEY')
            self.app_secret = os.getenv('KIS_APP_SECRET')
            self.account_number = os.getenv('KIS_ACCOUNT_NUMBER')

            # API URL 설정 (모의투자)
            self.base_url = "https://openapivts.koreainvestment.com:29443"

            # TokenManager로 토큰 관리
            self.token_manager = TokenManager(self.app_key, self.app_secret)

            # 봇 상태
            self.is_running = False

            # MarketScanner 초기화
            self.scanner = MarketScanner(self.app_key, self.app_secret, self.get_access_token)
            self.current_watchlist = []
            self.portfolio = {}
            self.max_positions = 3
            self.profit_target = 0.05
            self.stop_loss = -0.03
            self.kst_timezone = pytz.timezone('Asia/Seoul')
            self.last_market_closed_log = 0
            self.slack = SlackNotifier()

            # 초기 토큰 확인
            self.logger.info("토큰 확인 중...")
            token = self.token_manager.get_token()
            if token:
                self.logger.success("토큰 준비 완료")
            else:
                self.logger.warning("토큰 획득 실패 - 재시도 예정")

            self.logger.success("KIS Bot 초기화 완료", {
                "계좌번호": self.account_number,
                "Firebase": "trading-dcd8c",
                "최대 보유": self.max_positions
            })

        except Exception as e:
            self.logger.error(f"봇 초기화 실패", {"error": str(e)})
            raise

    def get_access_token(self) -> str:
        """TokenManager를 통한 토큰 획득"""
        return self.token_manager.get_token()

    def scan_market_conditions(self) -> List[str]:
        """시장 조건에 따른 감시 종목 선정"""
        try:
            self.logger.info("시장 스캔 시작")
            candidates = self.scanner.scan_market()

            if candidates:
                watchlist = []
                firebase_data = []

                for stock in candidates[:10]:  # 상위 10개 종목
                    watchlist.append({
                        "code": stock['code'],
                        "buy_signal": stock.get('buy_signal', False),
                        "reason": stock.get('buy_reason', '')
                    })

                    # Firebase용 데이터 준비
                    firebase_data.append({
                        "code": stock['code'],
                        "name": stock.get('name', ''),
                        "current_price": stock.get('current_price', 0),
                        "change_rate": stock.get('change_rate', 0),
                        "volume": stock.get('volume', 0),
                        "buy_signal": stock.get('buy_signal', False),
                        "buy_reason": stock.get('buy_reason', ''),
                        "score": stock.get('score', 0),
                        "timestamp": datetime.now(self.kst_timezone).isoformat()
                    })

                    self.logger.market(f"종목 선정: {stock['code']}", {
                        "매수신호": stock.get('buy_signal'),
                        "이유": stock.get('buy_reason')
                    })

                # Firebase에 저장
                try:
                    doc_ref = self.db.collection('market_scan').document('latest')
                    doc_ref.set({
                        'stocks': firebase_data,
                        'scan_time': datetime.now(self.kst_timezone).isoformat(),
                        'total_candidates': len(candidates)
                    })
                    self.logger.success(f"Firebase에 {len(firebase_data)}개 종목 저장")
                except Exception as e:
                    self.logger.error(f"Firebase 저장 실패", {"error": str(e)})

                self.current_watchlist = watchlist
                return watchlist
            else:
                self.logger.warning("조건 충족 종목 없음")
                # Firebase에 빈 데이터 저장
                try:
                    doc_ref = self.db.collection('market_scan').document('latest')
                    doc_ref.set({
                        'stocks': [],
                        'scan_time': datetime.now(self.kst_timezone).isoformat(),
                        'total_candidates': 0
                    })
                except:
                    pass
                return []

        except Exception as e:
            self.logger.error("시장 스캔 실패", {"error": str(e)})
            return []

    def is_trading_time(self) -> bool:
        """장 운영 시간 체크 (평일 9:00-15:20)"""
        now = datetime.now(self.kst_timezone)

        # 주말 체크
        if now.weekday() >= 5:
            return False

        # 시간 체크 (9:00 ~ 15:20)
        current_time = now.time()
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("15:20", "%H:%M").time()

        return market_open <= current_time <= market_close

    def run(self):
        """메인 실행 루프"""
        self.is_running = True
        self.logger.system("봇 시작")

        # 초기 시장 스캔
        self.scan_market_conditions()

        loop_count = 1  # 0이 아닌 1로 시작해서 중복 스캔 방지
        error_count = 0
        max_errors = 10

        while self.is_running:
            try:
                # 장시간 체크
                if not self.is_trading_time():
                    current_time = time.time()
                    if current_time - self.last_market_closed_log > 3600:
                        now = datetime.now(self.kst_timezone)
                        self.logger.debug(f"장마감 대기 중 ({now.strftime('%H:%M')})")
                        self.last_market_closed_log = current_time
                    time.sleep(60)
                    continue

                # 5분마다 시장 스캔
                if loop_count % 300 == 0:
                    self.scan_market_conditions()

                # 에러 카운트 초기화
                error_count = 0

                time.sleep(1)
                loop_count += 1

            except KeyboardInterrupt:
                self.logger.info("사용자 중단")
                break

            except Exception as e:
                error_count += 1
                self.logger.error(f"메인 루프 에러 ({error_count}/{max_errors})", {
                    "error": str(e),
                    "type": type(e).__name__
                })

                if error_count >= max_errors:
                    self.logger.error("최대 에러 횟수 초과 - 봇 종료")
                    break

                time.sleep(5)

        self.is_running = False
        self.logger.system("봇 종료")

if __name__ == "__main__":
    try:
        bot = KISBot()
        bot.run()
    except Exception as e:
        logger = UnifiedLogger()
        logger.error("봇 시작 실패", {"error": str(e), "type": type(e).__name__})
        sys.exit(1)