"""
통합 로깅 시스템
파일과 슬랙, 콘솔에 동시에 로그를 기록하고 전송
"""

import os
import sys
import json
from datetime import datetime
import pytz
from typing import Optional
from slack_notifier import SlackNotifier

class UnifiedLogger:
    def __init__(self, log_dir: str = "logs", slack_enabled: bool = True):
        """통합 로거 초기화"""
        # 로그 디렉토리 생성
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 한국 시간대
        self.kst = pytz.timezone('Asia/Seoul')

        # 오늘 날짜로 로그 파일 생성
        today = datetime.now(self.kst).strftime('%Y%m%d')
        self.log_file = os.path.join(log_dir, f'kis_bot_{today}.log')
        self.json_log_file = os.path.join(log_dir, f'kis_bot_{today}.json')

        # 슬랙 알림 설정
        self.slack_enabled = slack_enabled
        if slack_enabled:
            try:
                self.slack = SlackNotifier()
            except:
                self.slack = None
                self.slack_enabled = False

        # 로그 레벨 정의
        self.levels = {
            'DEBUG': '🔍',
            'INFO': '📋',
            'SUCCESS': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'TRADE': '💰',
            'MARKET': '📊',
            'SYSTEM': '⚙️'
        }

        self.info("통합 로깅 시스템 초기화 완료")

    def _get_timestamp(self) -> str:
        """KST 타임스탬프 생성"""
        return datetime.now(self.kst).strftime('[%Y-%m-%d %H:%M:%S KST]')

    def _write_to_file(self, level: str, message: str, data: Optional[dict] = None):
        """파일에 로그 기록"""
        timestamp = self._get_timestamp()

        # 텍스트 로그 파일
        with open(self.log_file, 'a', encoding='utf-8') as f:
            log_entry = f"{timestamp} [{level}] {message}"
            if data:
                log_entry += f" | DATA: {json.dumps(data, ensure_ascii=False)}"
            f.write(log_entry + '\n')

        # JSON 로그 파일
        with open(self.json_log_file, 'a', encoding='utf-8') as f:
            json_entry = {
                'timestamp': timestamp,
                'level': level,
                'message': message,
                'data': data
            }
            f.write(json.dumps(json_entry, ensure_ascii=False) + '\n')

    def _send_to_slack(self, level: str, message: str, data: Optional[dict] = None):
        """슬랙에 중요 로그 전송"""
        if not self.slack_enabled or not self.slack:
            return

        # 중요한 레벨만 슬랙에 전송
        # SYSTEM 레벨 추가 - 봇 시작/종료 알림 받기 위해
        important_levels = ['SUCCESS', 'WARNING', 'ERROR', 'TRADE', 'MARKET', 'SYSTEM']
        if level not in important_levels:
            return

        try:
            emoji = self.levels.get(level, '📝')
            slack_message = f"{emoji} *[{level}]* {message}"

            if data:
                slack_message += f"\n```{json.dumps(data, indent=2, ensure_ascii=False)}```"

            # send_message는 title과 message가 필요함
            self.slack.send_message(
                title=f"{level} Alert",
                message=message,
                color="danger" if level == "ERROR" else "warning" if level == "WARNING" else "good",
                fields=[{"title": "Data", "value": json.dumps(data, ensure_ascii=False), "short": False}] if data else None
            )
        except Exception as e:
            print(f"슬랙 전송 실패: {e}")

    def _print_to_console(self, level: str, message: str, data: Optional[dict] = None):
        """콘솔에 출력"""
        timestamp = self._get_timestamp()
        emoji = self.levels.get(level, '📝')

        console_msg = f"{timestamp} {emoji} [{level}] {message}"
        if data:
            console_msg += f"\n   DATA: {json.dumps(data, ensure_ascii=False, indent=2)}"

        print(console_msg)

    def log(self, level: str, message: str, data: Optional[dict] = None):
        """통합 로그 기록"""
        # 콘솔 출력
        self._print_to_console(level, message, data)

        # 파일 기록
        self._write_to_file(level, message, data)

        # 슬랙 전송
        self._send_to_slack(level, message, data)

    # 편의 메서드들
    def debug(self, message: str, data: Optional[dict] = None):
        self.log('DEBUG', message, data)

    def info(self, message: str, data: Optional[dict] = None):
        self.log('INFO', message, data)

    def success(self, message: str, data: Optional[dict] = None):
        self.log('SUCCESS', message, data)

    def warning(self, message: str, data: Optional[dict] = None):
        self.log('WARNING', message, data)

    def error(self, message: str, data: Optional[dict] = None):
        self.log('ERROR', message, data)

    def trade(self, message: str, data: Optional[dict] = None):
        self.log('TRADE', message, data)

    def market(self, message: str, data: Optional[dict] = None):
        self.log('MARKET', message, data)

    def system(self, message: str, data: Optional[dict] = None):
        self.log('SYSTEM', message, data)

    def get_log_file_path(self) -> str:
        """현재 로그 파일 경로 반환"""
        return self.log_file

    def get_logs_summary(self) -> dict:
        """로그 요약 정보 반환"""
        try:
            with open(self.json_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            level_counts = {}
            recent_logs = []

            for line in lines:
                try:
                    entry = json.loads(line.strip())
                    level = entry.get('level', 'UNKNOWN')
                    level_counts[level] = level_counts.get(level, 0) + 1
                    recent_logs.append(entry)
                except:
                    continue

            return {
                'total_logs': len(lines),
                'level_counts': level_counts,
                'recent_logs': recent_logs[-10:],  # 최근 10개
                'log_file': self.log_file
            }
        except Exception as e:
            return {'error': str(e)}