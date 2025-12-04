# 🚀 GCP Compute Engine 배포 가이드

> **24시간 무중단 KIS 자동매매 봇 운영을 위한 완벽 가이드**

초보자도 따라할 수 있도록 **클릭 단위**로 상세하게 설명합니다. 예상 소요 시간: **30분**

---

## 📋 배포 개요

- **클라우드**: Google Cloud Platform (GCP)
- **서버**: Compute Engine e2-micro (무료 티어 / 월 $6 수준)
- **OS**: Ubuntu 22.04 LTS
- **실행 방식**: nohup 백그라운드 실행 (터미널 종료해도 봇 계속 실행)

---

## 🎯 1단계: GCP VM 인스턴스 생성

### A. GCP 콘솔 접속
1. **https://console.cloud.google.com** 접속
2. Firebase 프로젝트와 **동일한 Google 계정**으로 로그인
3. 왼쪽 메뉴에서 **"Compute Engine" → "VM 인스턴스"** 클릭

### B. VM 인스턴스 생성
1. **"인스턴스 만들기"** 버튼 클릭
2. 다음 설정으로 구성:

```
📝 기본 설정 (💰 무료 옵션 추천)
├── 인스턴스 이름: kis-auto-trader
├── 리전: us-central1 (아이오와) ⭐ 무료!
└── 영역: us-central1-a

💻 머신 구성
├── 머신 패밀리: 범용
├── 시리즈: E2
├── 머신 유형: e2-micro (1개 vCPU, 1GB 메모리)
└── 비용: 완전 무료! (Always Free 티어)

🌏 리전 선택 옵션:
├── 🥇 us-central1 (무료): $0/월 - 추천!
├── 🥈 asia-northeast3 (서울): ~$6/월 (빠른 속도)
└── 🥉 asia-southeast1 (싱가포르): ~$5/월 (절충안)```

🖥️ 부팅 디스크
├── 운영체제: Ubuntu
├── 버전: Ubuntu 22.04 LTS
├── 부팅 디스크 유형: 표준 영구 디스크
└── 크기: 10GB

🔒 방화벽
├── HTTP 트래픽 허용: 체크 안 함
└── HTTPS 트래픽 허용: 체크 안 함
```

3. **"만들기"** 버튼 클릭 (2-3분 대기)

---

## 🔌 2단계: VM 접속 및 환경 구성

### A. SSH 접속
1. VM 인스턴스 목록에서 **"SSH"** 버튼 클릭
2. 브라우저에서 터미널 창이 열림 (최대 1분 대기)

### B. 시스템 업데이트 및 Python 설치
SSH 터미널에서 다음 명령어를 **순서대로** 입력:

```bash
# 1. 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# 2. 필수 패키지 설치
sudo apt install python3-pip python3-venv git htop nano -y

# 3. Python 버전 확인 (3.10+ 필요)
python3 --version
```

### C. 프로젝트 다운로드

**방법 1: GitHub에서 클론 (추천)**
```bash
# GitHub 프로젝트 클론
git clone https://github.com/2cr-Andy/KIS-Auto-Trader.git
cd KIS-Auto-Trader
```

**방법 2: 로컬 파일 업로드**
```bash
# 빈 폴더 생성
mkdir KIS-Auto-Trader && cd KIS-Auto-Trader

# 로컬에서 파일 업로드 (SSH 창에서 파일 드래그앤드롭 또는 업로드 메뉴 사용)
```

---

## 🐍 3단계: Python 환경 구성

### A. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 프롬프트가 (venv)로 시작하면 성공
```

### B. 패키지 설치
```bash
# requirements.txt가 있는 경우
pip install -r requirements.txt

# 또는 수동 설치
pip install requests firebase-admin python-dotenv pandas numpy pytz
```

### C. 패키지 설치 확인
```bash
# 설치된 패키지 확인
pip list

# 주요 패키지 존재 여부 확인
python3 -c "import firebase_admin, requests, pandas; print('✅ 모든 패키지 정상 설치')"
```

---

## 🔑 4단계: 환경 변수 및 인증 설정

### A. 환경 변수 파일 생성
```bash
# .env 파일 생성
nano .env
```

다음 내용을 입력 후 **Ctrl+X → Y → Enter**로 저장:
```env
# KIS API 키 (한국투자증권에서 발급)
KIS_APP_KEY=여기에_앱키_입력
KIS_APP_SECRET=여기에_앱시크릿_입력
KIS_ACCOUNT_NUMBER=계좌번호

# Firebase Admin SDK
FIREBASE_ADMIN_KEY_PATH=./serviceAccountKey.json
```

### B. Firebase 서비스 계정 키 설정

**방법 1: 로컬 파일 업로드**
```bash
# SSH 창에서 파일 업로드 메뉴를 통해 serviceAccountKey.json 업로드
# 또는 nano 에디터로 직접 내용 붙여넣기
nano serviceAccountKey.json
```

**방법 2: 파일 내용 직접 생성**
```bash
# Firebase 콘솔에서 서비스 계정 키 JSON 내용을 복사해서 붙여넣기
nano serviceAccountKey.json
```

### C. 파일 권한 설정
```bash
# 민감한 파일 권한 설정
chmod 600 .env serviceAccountKey.json

# 파일 존재 확인
ls -la .env serviceAccountKey.json
```

---

## 🚀 5단계: 봇 실행 및 테스트

### A. 수동 실행 테스트
```bash
# 가상환경 활성화 확인
source venv/bin/activate

# 봇 수동 실행 (테스트)
python3 kis_bot.py
```

정상 실행되면 다음과 같은 로그가 출력됩니다:
```
KIS Bot 초기화 완료
계좌번호: 50154573
Firebase 프로젝트: trading
🚀 KIS 자동매매 봇 시작
✅ 접속 토큰 발급 성공
💰 예수금: 9,946,145원
```

**Ctrl+C**로 봇을 종료하고 다음 단계로 진행합니다.

### B. 24시간 백그라운드 실행
```bash
# nohup으로 백그라운드 실행
nohup python3 kis_bot.py > bot.log 2>&1 &

# 프로세스 확인
ps -ef | grep python

# 로그 실시간 확인
tail -f bot.log
```

### C. 실행 상태 확인 명령어
```bash
# 봇 프로세스 확인
ps -ef | grep kis_bot

# 로그 확인 (최근 50줄)
tail -50 bot.log

# 로그 실시간 모니터링 (Ctrl+C로 종료)
tail -f bot.log

# 시스템 리소스 확인
htop
```

---

## 🛠️ 6단계: 봇 관리 명령어

### A. 봇 종료
```bash
# 1. 프로세스 ID 확인
ps -ef | grep kis_bot

# 2. 프로세스 종료 (PID는 위에서 확인한 번호)
kill 프로세스ID

# 3. 강제 종료 (필요시)
pkill -f kis_bot.py
```

### B. 봇 재시작
```bash
# 기존 봇 종료
pkill -f kis_bot.py

# 새로운 봇 시작
cd ~/KIS-Auto-Trader
source venv/bin/activate
nohup python3 kis_bot.py > bot.log 2>&1 &
```

### C. 자동 재시작 스크립트 생성
```bash
# restart_bot.sh 스크립트 생성
nano restart_bot.sh
```

다음 내용을 입력:
```bash
#!/bin/bash
cd /home/사용자명/KIS-Auto-Trader
pkill -f kis_bot.py
sleep 5
source venv/bin/activate
nohup python3 kis_bot.py > bot.log 2>&1 &
echo "봇이 재시작되었습니다."
```

실행 권한 부여:
```bash
chmod +x restart_bot.sh
```

---

## 🔍 7단계: 모니터링 및 유지보수

### A. 일일 점검 항목
```bash
# 1. 봇 실행 상태 확인
ps -ef | grep kis_bot

# 2. 최근 로그 확인
tail -20 bot.log

# 3. 디스크 사용량 확인
df -h

# 4. 메모리 사용량 확인
free -h
```

### B. 로그 관리 (용량 절약)
```bash
# 로그 파일 크기 확인
ls -lh bot.log

# 오래된 로그 백업 후 삭제 (1주일 단위)
cp bot.log bot_$(date +%Y%m%d).log
> bot.log

# 7일 이상된 백업 로그 삭제
find . -name "bot_*.log" -mtime +7 -delete
```

### C. 정기적인 업데이트
```bash
# 1. 코드 업데이트 (GitHub 사용시)
cd ~/KIS-Auto-Trader
git pull origin main

# 2. 봇 재시작
./restart_bot.sh
```

---

## ⚠️ 트러블슈팅

### 자주 발생하는 문제들

#### 1. "Module not found" 에러
```bash
# 해결: 가상환경 활성화 확인
source venv/bin/activate
pip install 누락된패키지명
```

#### 2. Firebase 연결 에러
```bash
# 해결: 서비스 계정 키 파일 확인
ls -la serviceAccountKey.json
cat .env | grep FIREBASE
```

#### 3. KIS API 500 에러
```bash
# 해결: 일시적 API 서버 문제, 5분 후 재시도
./restart_bot.sh
```

#### 4. VM 메모리 부족
```bash
# 해결: 스왑 파일 생성 (1GB)
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 비상 상황 대응

#### VM 재부팅 후 봇 자동 시작
```bash
# 1. crontab 설정
crontab -e

# 2. 다음 줄 추가
@reboot cd /home/사용자명/KIS-Auto-Trader && source venv/bin/activate && nohup python3 kis_bot.py > bot.log 2>&1 &
```

---

## 💰 비용 관리

### 💰 리전별 예상 월 비용

#### 🥇 미국 리전 (추천 - 완전 무료!)
- **e2-micro 인스턴스**: $0 (Always Free 티어)
- **30GB 표준 디스크**: $0 (무료 티어)
- **네트워크**: $0 (무료)
- **총 비용**: **완전 무료!** 🎉

#### 🥈 아시아 리전 (서울/싱가포르)
- **e2-micro 인스턴스**: $5-6/월 (7,000-8,000원)
- **10GB 표준 디스크**: $0.4/월 (500원)
- **네트워크**: 거의 무료
- **총 예상 비용**: 월 7,500-8,500원

### 🌍 리전 선택 가이드

#### 미국 리전을 선택해야 하는 이유:
1. **완전 무료**: Always Free 티어로 영구 무료
2. **Firebase 연동 문제없음**: 글로벌 서비스라 어디서든 동일
3. **KIS API는 어차피 한국**: 미국에서도 한국 KIS 서버에 접속
4. **지연시간 영향 미미**: 주식봇은 초단타가 아니므로 200ms 차이 무관

#### 한국 리전이 필요한 경우:
- 극도로 빠른 응답속도가 필요한 경우
- 월 8,000원 정도 지출이 부담되지 않는 경우

---

## ✅ 배포 완료 체크리스트

- [ ] GCP VM 인스턴스 생성 완료
- [ ] SSH 접속 및 환경 구성 완료
- [ ] Python 가상환경 및 패키지 설치 완료
- [ ] .env 파일 및 Firebase 키 설정 완료
- [ ] 봇 수동 실행 테스트 성공
- [ ] nohup 백그라운드 실행 설정 완료
- [ ] 로그 모니터링 확인 완료
- [ ] 재시작 스크립트 생성 완료

🎉 **축하합니다! KIS 자동매매 봇이 클라우드에서 24시간 실행 중입니다.**

---

## 📞 지원 및 문의

문제 발생시:
1. **로그 확인**: `tail -50 bot.log`
2. **GitHub Issues**: 프로젝트 저장소의 Issues 탭
3. **Discord/Slack**: 개발팀 채널 문의

**Happy Trading! 🚀📈**