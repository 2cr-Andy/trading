# 🔔 Slack 워크스페이스 및 웹훅 설정 가이드

> **KIS 자동매매 봇의 거래 알림, 배포 알림, 에러 알림을 위한 Slack 연동 설정**

5분 안에 완료할 수 있는 간단한 설정 가이드입니다.

---

## 📋 목표

- KIS 봇의 매매 신호, 거래 체결, 에러 등을 실시간으로 Slack으로 받기
- GitHub Actions 자동 배포 완료/실패 알림
- 포트폴리오 일일 요약 알림

---

## 🚀 1단계: Slack 워크스페이스 생성

### A. 새 워크스페이스 생성 (또는 기존 워크스페이스 사용)

1. **https://slack.com** 접속
2. **"워크스페이스 생성하기"** 클릭
3. 다음 정보로 생성:

```
📋 워크스페이스 정보
├── 워크스페이스 이름: KIS-Trading-Bot (또는 원하는 이름)
├── 채널 이름: #kis-bot
└── 이메일: 본인 이메일 주소
```

---

## 🔗 2단계: Incoming Webhook 생성

### A. Slack App 생성 및 설정

1. **https://api.slack.com/apps** 접속
2. **"Create New App"** 클릭
3. **"From scratch"** 선택
4. App 정보 입력:

```
📝 App 정보
├── App Name: KIS Auto Trader Bot
├── Pick a workspace: [위에서 생성한 워크스페이스 선택]
└── Create App 클릭
```

### B. Incoming Webhooks 활성화

1. 좌측 메뉴에서 **"Incoming Webhooks"** 클릭
2. **"Activate Incoming Webhooks"** 토글을 **ON**으로 변경
3. 페이지 하단의 **"Add New Webhook to Workspace"** 클릭
4. 채널 선택에서 **#kis-bot** 선택 후 **"허용"** 클릭

### C. Webhook URL 복사

생성된 Webhook URL은 다음과 같은 형태입니다:
```
https://hooks.slack.com/services/[TEAM_ID]/[CHANNEL_ID]/[TOKEN]


```

이 URL을 복사해서 **안전한 곳에 보관**하세요.

---

## 🔧 3단계: 환경 변수 설정

### A. 로컬 개발 환경 (.env 파일)

```bash
# .env 파일에 추가
SLACK_WEBHOOK_URL=[여기에_실제_웹훅_URL_입력]
SLACK_CHANNEL=#kis-bot
```

### B. GitHub Secrets 설정 (자동 배포용)

1. GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions**
2. **"New repository secret"** 클릭
3. 다음 Secret 추가:

```
📋 GitHub Secrets
├── Name: SLACK_WEBHOOK
├── Value: [위에서 복사한 Webhook URL]
└── Add secret 클릭
```

### C. GCP VM 환경 변수 설정 (배포 환경)

SSH로 GCP VM에 접속한 후:

```bash
# KIS-Auto-Trader 디렉토리로 이동
cd ~/KIS-Auto-Trader

# .env 파일 편집
nano .env

# 다음 줄 추가 (실제 웹훅 URL로 교체 필요)
SLACK_WEBHOOK_URL=[여기에_실제_웹훅_URL_입력]
SLACK_CHANNEL=#kis-bot

# Ctrl+X → Y → Enter로 저장
```

---

## 📱 4단계: 테스트

### A. 로컬에서 Slack 알림 테스트

```bash
# 가상환경 활성화
source venv/bin/activate

# Python 테스트 스크립트 실행
python3 -c "
from slack_notifier import SlackNotifier
slack = SlackNotifier()
slack.notify_system_alert('info', '🧪 KIS Bot Slack 연동 테스트 성공!')
print('✅ Slack 테스트 완료 - 채널을 확인하세요!')
"
```

### B. 봇 실행하여 시작 알림 확인

```bash
# 봇 시작 (시작 알림이 Slack으로 전송됨)
python3 kis_bot.py
```

---

## 📊 5단계: 알림 종류 확인

설정이 완료되면 다음과 같은 알림을 받을 수 있습니다:

### 🤖 봇 운영 알림
- **봇 시작/종료**: 봇이 시작되거나 종료될 때
- **시장 마감**: 거래 종료 시
- **시스템 에러**: API 오류, 연결 문제 등

### 📈 거래 알림
- **매수/매도 신호**: RSI, MFI, ADX 지표와 함께
- **거래 체결**: 매수/매도 완료 시 가격, 수량, 수익률 정보
- **포트폴리오 요약**: 일일 손익 요약

### 🚀 배포 알림 (GitHub Actions)
- **배포 성공**: 코드 업데이트 및 봇 재시작 성공
- **배포 실패**: 배포 중 오류 발생 시

---

## 🎨 알림 커스터마이징

### A. 채널 분리 (선택사항)

다른 용도의 채널을 만들어 알림을 분리할 수 있습니다:

```
📋 채널 구성 예시
├── #kis-bot-trading: 매매 관련 알림만
├── #kis-bot-deploy: 배포 관련 알림만
├── #kis-bot-errors: 에러 알림만
└── #kis-bot-summary: 일일 요약 알림만
```

채널별로 별도의 Webhook URL을 생성하여 `slack_notifier.py`에서 용도별로 다른 웹훅을 사용할 수 있습니다.

### B. 알림 시간 제한 (선택사항)

특정 시간에만 알림을 받고 싶다면 `slack_notifier.py`에 시간 체크 로직을 추가:

```python
from datetime import datetime
import pytz

def should_send_notification(self):
    """한국 시간 08:00-18:00에만 알림 전송"""
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    return 8 <= now.hour <= 18
```

---

## ⚠️ 보안 및 주의사항

### 🔒 Webhook URL 보안
- **Webhook URL을 GitHub에 절대 올리지 마세요**
- .env 파일이 .gitignore에 포함되어 있는지 확인
- URL이 노출되면 즉시 재생성

### 🔔 알림 빈도 제한
현재 설정으로는 다음과 같은 빈도로 알림이 전송됩니다:
- **매수/매도 신호**: 신호 발생 시마다
- **거래 체결**: 체결 시마다
- **에러 알림**: 에러 발생 시마다
- **포트폴리오 요약**: 일 1회

과도한 알림이 부담스러우면 `slack_notifier.py`에서 알림 빈도를 조절할 수 있습니다.

---

## 🛠️ 문제 해결

### 1. 알림이 오지 않는 경우

```bash
# 환경변수 확인
cat .env | grep SLACK

# 수동 테스트
python3 -c "
from slack_notifier import SlackNotifier
slack = SlackNotifier()
print('Slack enabled:', slack.enabled)
"
```

### 2. 웹훅 URL 오류

- Webhook URL이 정확한지 확인
- 워크스페이스에서 App이 제거되지 않았는지 확인
- #kis-bot 채널이 존재하는지 확인

### 3. GitHub Actions 알림 오류

- GitHub Repository Secrets에 `SLACK_WEBHOOK`가 올바르게 설정되었는지 확인
- `.github/workflows/deploy.yml`에서 Slack 관련 설정 확인

---

## ✅ 설정 완료 체크리스트

- [ ] Slack 워크스페이스 및 #kis-bot 채널 생성
- [ ] Slack App 및 Incoming Webhook 생성
- [ ] 로컬 .env 파일에 SLACK_WEBHOOK_URL 추가
- [ ] GitHub Secrets에 SLACK_WEBHOOK 추가
- [ ] GCP VM .env 파일에 웹훅 URL 추가
- [ ] 로컬에서 Slack 알림 테스트 성공
- [ ] 봇 시작 시 Slack 시작 알림 확인

🎉 **설정 완료! 이제 KIS 봇의 모든 활동을 Slack으로 실시간 모니터링할 수 있습니다.**

---

## 📞 지원

문제 발생 시:
1. **환경변수 체크**: `echo $SLACK_WEBHOOK_URL`
2. **로그 확인**: `tail -f bot.log`
3. **GitHub Issues**: 프로젝트 저장소에 이슈 등록

**Happy Trading with Slack! 🚀📊**