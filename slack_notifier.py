"""
KIS Auto Trader Slack 알림 시스템
"""

import os
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any


class SlackNotifier:
    def __init__(self):
        """Slack 알림 시스템 초기화"""
        self.webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.channel = os.getenv('SLACK_CHANNEL', '#kis-bot')
        self.username = 'KIS Auto Trader Bot'
        # Bot Token이 있으면 Bot Token 우선 사용 (Webhook 무시)
        self.use_bot_token = bool(self.bot_token)
        if self.use_bot_token:
            self.webhook_url = None  # Bot Token 사용시 Webhook 비활성화
        self.enabled = bool(self.webhook_url or self.bot_token)

        # 채널별 설정 (Bot Token용 # 추가)
        self.channels = {
            'trading': '#kis-bot-trading',
            'deploy': '#kis-bot-deploy',
            'errors': '#kis-bot-errors',
            'summary': '#kis-bot-summary'
        }

        if not self.enabled:
            print("⚠️ Slack 토큰이 설정되지 않았습니다. Slack 알림이 비활성화됩니다.")
        else:
            method = "Bot Token" if self.use_bot_token else "Webhook"
            print(f"✅ Slack 알림 시스템 활성화됨 ({method})")

    def send_message(self,
                    title: str,
                    message: str,
                    color: str = "good",
                    emoji: str = ":robot_face:",
                    fields: Optional[list] = None,
                    channel: str = None,
                    use_fallback: bool = True) -> bool:
        """
        Slack으로 메시지 전송

        Args:
            title: 메시지 제목
            message: 메시지 내용
            color: 메시지 색상 (good, warning, danger)
            emoji: 아이콘 이모지
            fields: 추가 필드 정보
            channel: 채널 (기본값 사용시 None)
        """
        if not self.enabled:
            return False

        try:
            target_channel = channel or self.channel

            if self.use_bot_token:
                # Bot Token 방식 (chat.postMessage API)
                payload = {
                    "channel": target_channel,
                    "text": f"*{title}*\n{message}",
                    "attachments": [{
                        "color": color,
                        "fields": fields or []
                    }]
                }

                headers = {
                    'Authorization': f'Bearer {self.bot_token}',
                    'Content-Type': 'application/json'
                }

                response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=10
                )
            else:
                # Webhook 방식
                payload = {
                    "channel": target_channel,
                    "username": self.username,
                    "icon_emoji": emoji,
                    "attachments": [{
                        "color": color,
                        "title": title,
                        "text": message,
                        "footer": "KIS Auto Trader",
                        "ts": int(datetime.now().timestamp()),
                        "fields": fields or []
                    }]
                }

                response = requests.post(
                    self.webhook_url,
                    data=json.dumps(payload),
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

            if self.use_bot_token:
                # Bot Token 응답 처리
                result = response.json()
                if result.get('ok'):
                    print(f"✅ Slack 알림 전송 성공: {title}")
                    return True
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"❌ Slack Bot API 실패: {error_msg}")
                    # 채널 분리 실패시 기본 채널로 폴백
                    if use_fallback and channel and channel != self.channel:
                        print(f"🔄 기본 채널로 재전송 시도: {self.channel}")
                        return self.send_message(title, message, color, emoji, fields, None, False)
                    return False
            else:
                # Webhook 응답 처리
                if response.status_code == 200:
                    print(f"✅ Slack 알림 전송 성공: {title}")
                    return True
                else:
                    print(f"❌ Slack 알림 전송 실패: {response.status_code}")
                    # 채널 분리 실패시 기본 채널로 폴백
                    if use_fallback and channel and channel != self.channel:
                        print(f"🔄 기본 채널로 재전송 시도: {self.channel}")
                        return self.send_message(title, message, color, emoji, fields, None, False)
                    return False

        except Exception as e:
            print(f"❌ Slack 알림 전송 중 오류: {e}")
            return False

    def notify_bot_start(self):
        """봇 시작 알림"""
        return self.send_message(
            title="🚀 KIS Bot Started",
            message="자동매매 봇이 성공적으로 시작되었습니다.",
            color="good",
            emoji=":rocket:",
            channel=self.channels.get('trading')
        )

    def notify_bot_stop(self):
        """봇 종료 알림"""
        self.send_message(
            title="🛑 KIS Bot Stopped",
            message="자동매매 봇이 종료되었습니다.",
            color="warning",
            emoji=":octagonal_sign:",
            channel=self.channels.get('trading')
        )

    def notify_trade_success(self, action: str, stock_code: str, price: int, quantity: int, reason: str = ""):
        """거래 성공 알림"""
        action_emoji = "📈" if action == "매수" else "📉"
        action_color = "good" if action == "매수" else "#ff9500"

        fields = [
            {
                "title": "종목",
                "value": stock_code,
                "short": True
            },
            {
                "title": "가격",
                "value": f"{price:,}원",
                "short": True
            },
            {
                "title": "수량",
                "value": f"{quantity}주",
                "short": True
            }
        ]

        if reason:
            fields.append({
                "title": "사유",
                "value": reason,
                "short": False
            })

        self.send_message(
            title=f"{action_emoji} {action} 체결 완료",
            message=f"**{stock_code}** {action}가 성공적으로 체결되었습니다.",
            color=action_color,
            emoji=action_emoji,
            fields=fields,
            channel=self.channels.get('trading')
        )

    def notify_trade_signal(self, signal_type: str, stock_code: str, indicators: Dict[str, Any]):
        """매매 신호 알림"""
        signal_emoji = "🎯" if signal_type == "매수신호" else "⚠️"

        fields = [
            {
                "title": "RSI",
                "value": f"{indicators.get('rsi', 0):.1f}",
                "short": True
            },
            {
                "title": "MFI",
                "value": f"{indicators.get('mfi', 0):.1f}",
                "short": True
            },
            {
                "title": "ADX",
                "value": f"{indicators.get('adx', 0):.1f}",
                "short": True
            },
            {
                "title": "현재가",
                "value": f"{indicators.get('current_price', 0):,}원",
                "short": True
            }
        ]

        self.send_message(
            title=f"{signal_emoji} {signal_type} 발생",
            message=f"**{stock_code}**에서 {signal_type}가 감지되었습니다.",
            color="warning",
            emoji=signal_emoji,
            fields=fields,
            channel=self.channels.get('trading')
        )

    def notify_error(self, error_type: str, error_message: str, stock_code: str = ""):
        """에러 알림"""
        fields = [
            {
                "title": "에러 타입",
                "value": error_type,
                "short": True
            }
        ]

        if stock_code:
            fields.append({
                "title": "종목",
                "value": stock_code,
                "short": True
            })

        fields.append({
            "title": "에러 메시지",
            "value": error_message,
            "short": False
        })

        self.send_message(
            title="❌ 오류 발생",
            message="시스템에서 오류가 발생했습니다. 확인이 필요합니다.",
            color="danger",
            emoji=":exclamation:",
            fields=fields,
            channel=self.channels.get('errors')
        )

    def notify_deploy_success(self, commit_message: str = "", author: str = ""):
        """배포 성공 알림"""
        fields = []
        if commit_message:
            fields.append({
                "title": "커밋 메시지",
                "value": commit_message,
                "short": False
            })
        if author:
            fields.append({
                "title": "배포자",
                "value": author,
                "short": True
            })

        self.send_message(
            title="✅ 배포 성공",
            message="KIS 봇이 성공적으로 배포되어 재시작되었습니다.",
            color="good",
            emoji=":rocket:",
            fields=fields,
            channel=self.channels.get('deploy')
        )

    def notify_deploy_failure(self, error_message: str = ""):
        """배포 실패 알림"""
        fields = []
        if error_message:
            fields.append({
                "title": "에러 메시지",
                "value": error_message,
                "short": False
            })

        self.send_message(
            title="❌ 배포 실패",
            message="KIS 봇 배포 중 오류가 발생했습니다. 확인이 필요합니다.",
            color="danger",
            emoji=":warning:",
            fields=fields,
            channel=self.channels.get('deploy')
        )

    def notify_portfolio_update(self, total_assets: float, total_pnl: float, pnl_percent: float):
        """포트폴리오 업데이트 알림 (일일 요약)"""
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        pnl_color = "good" if total_pnl >= 0 else "danger"

        fields = [
            {
                "title": "총 자산",
                "value": f"{total_assets:,.0f}원",
                "short": True
            },
            {
                "title": "오늘 손익",
                "value": f"{total_pnl:+.0f}원 ({pnl_percent:+.2f}%)",
                "short": True
            }
        ]

        self.send_message(
            title=f"{pnl_emoji} 일일 포트폴리오 요약",
            message="오늘의 거래 결과입니다.",
            color=pnl_color,
            emoji=pnl_emoji,
            fields=fields,
            channel=self.channels.get('summary')
        )

    def notify_market_scan_result(self, qualified_count: int, total_scanned: int, top_picks: list):
        """시장 스캔 결과 알림"""
        fields = [
            {
                "title": "스캔한 종목 수",
                "value": f"{total_scanned}개",
                "short": True
            },
            {
                "title": "조건 만족 종목",
                "value": f"{qualified_count}개",
                "short": True
            }
        ]

        if top_picks:
            picks_text = "\n".join([f"• {pick}" for pick in top_picks[:5]])
            fields.append({
                "title": "상위 후보",
                "value": picks_text,
                "short": False
            })

        self.send_message(
            title="🔍 시장 스캔 완료",
            message=f"새로운 투자 기회를 발견했습니다.",
            color="good",
            emoji=":mag:",
            fields=fields,
            channel=self.channels.get('trading')
        )

    def notify_market_closed(self):
        """장 마감 알림"""
        self.send_message(
            title="🏁 장 마감",
            message="오늘 거래가 종료되었습니다. 봇은 대기 모드로 전환됩니다.",
            color="#ffd700",
            emoji=":checkered_flag:",
            channel=self.channels.get('summary')
        )

    def notify_system_alert(self, alert_type: str, message: str):
        """시스템 알림 (일반)"""
        emoji_map = {
            "info": ":information_source:",
            "warning": ":warning:",
            "critical": ":rotating_light:"
        }

        color_map = {
            "info": "good",
            "warning": "warning",
            "critical": "danger"
        }

        target_channel = self.channels.get('errors') if alert_type in ['warning', 'critical'] else None

        self.send_message(
            title=f"🔔 시스템 알림",
            message=message,
            color=color_map.get(alert_type, "good"),
            emoji=emoji_map.get(alert_type, ":bell:"),
            channel=target_channel
        )