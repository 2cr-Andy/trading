#!/bin/bash

echo "🚀 KIS 자동매매 봇 시작"
echo "========================="

# 1. 기존 프로세스 정리
echo "🔍 기존 프로세스 정리..."
pkill -f "python.*simple_auto_trader" 2>/dev/null
pkill -f "flutter run" 2>/dev/null
sleep 1

# 2. 토큰 확보 (최대 5번 시도)
echo "🔑 토큰 확보 중..."
rm -f kis_token.json 2>/dev/null

for i in {1..5}; do
    echo "  시도 $i/5..."
    python3 get_saved_token.py

    if [ -f "kis_token.json" ]; then
        echo "  ✅ 토큰 확보 성공!"
        break
    else
        echo "  ❌ 실패, 60초 대기..."
        sleep 60
    fi
done

# 토큰 확보 실패시 종료
if [ ! -f "kis_token.json" ]; then
    echo "❌ 토큰 확보 실패. 종료합니다."
    exit 1
fi

# 3. Flutter 대시보드 시작
echo "🌐 Flutter 대시보드 시작..."
cd kis_dashboard
flutter run -d web-server --web-hostname localhost --web-port 8080 --release &
FLUTTER_PID=$!
cd ..
sleep 3
echo "  ✅ 대시보드: http://localhost:8080"

# 4. 메인 자동매매 봇 시작
echo "🤖 자동매매 봇 시작..."
python3 main.py &
BOT_PID=$!

echo ""
echo "🎯 시스템 실행 중:"
echo "   📱 대시보드: http://localhost:8080"
echo "   🤖 자동매매: 5분 주기로 실행"
echo "   📋 매수조건: 3%↑ + 10만주↑ + 1000원↑"
echo "   📋 매수금액: 50만원씩"
echo "   📋 매도조건: -3% 손절, +5% 익절"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"

# 종료 처리
trap "echo '🛑 시스템 종료 중...'; kill $FLUTTER_PID $BOT_PID 2>/dev/null; exit" INT

# 대기
wait