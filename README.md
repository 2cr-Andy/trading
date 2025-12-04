# KIS Auto Trader

한국투자증권 Open API를 활용한 주식 자동매매 시스템

## 🚀 시스템 구성

### Backend (Python Bot)
- KIS REST API & WebSocket 연동
- Firebase Firestore 실시간 데이터 저장
- 5개 감시 종목 실시간 가격 추적
- 계좌 정보 자동 업데이트

### Frontend (Flutter Web)
- Dark Mode HTS 스타일 대시보드
- 실시간 데이터 동기화 (StreamBuilder)
- 포트폴리오 관리 및 수동 매도 기능
- 실시간 매매 로그 콘솔

### Database (Firebase)
- Firestore NoSQL 데이터베이스
- 실시간 동기화
- 무료 Spark Plan 사용

## 📦 설치 및 실행

### 1. 환경 설정
```bash
# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env` 파일 생성:
```
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NUMBER=your_account
FIREBASE_ADMIN_KEY_PATH=/path/to/serviceAccountKey.json
```

### 3. Firebase 설정
- Firebase 프로젝트 생성
- Firestore Database 활성화
- serviceAccountKey.json 다운로드

### 4. 실행
```bash
# Python 봇 실행
python kis_bot.py

# Flutter Web 대시보드 실행
cd kis_dashboard
flutter run -d chrome --web-port 8080
```

## 📊 기능

### 감시 종목 (Watchlist)
- 실시간 가격, 등락률, 거래량 표시
- RSI, MFI 지표 (개발 예정)
- 매수 신호 임박 시 하이라이트

### 포트폴리오
- 보유 종목 카드 형태 표시
- 실시간 수익률 계산
- 수동 매도 기능

### 실시간 로그
- 봇 동작 상태 모니터링
- 매수/매도 신호 및 체결 내역
- 에러 로그

## 🔒 보안

- API 키는 `.env` 파일로 관리 (.gitignore에 포함)
- Firebase Admin SDK 인증 사용
- 실시간 데이터는 Firebase Security Rules로 보호

## 📝 라이선스

MIT License

## 👨‍💻 개발

KIS Auto Trader Team
- Python Bot & Flutter Dashboard
- Firebase Integration