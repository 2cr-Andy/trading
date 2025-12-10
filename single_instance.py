"""
단일 인스턴스 보장 모듈
중복 실행 방지를 위한 프로세스 관리
"""

import os
import sys
import psutil
import signal
import time

class SingleInstance:
    """봇의 단일 인스턴스를 보장하는 클래스"""

    def __init__(self, bot_name="kis_bot"):
        self.bot_name = bot_name
        self.pid_file = f"/tmp/{bot_name}.pid"

    def check_and_kill_existing(self):
        """기존 실행 중인 봇 프로세스를 찾아서 종료"""
        current_pid = os.getpid()
        killed_count = 0

        # 모든 파이썬 프로세스 검사
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 현재 프로세스는 제외
                if proc.info['pid'] == current_pid:
                    continue

                # 명령어 라인에 봇 이름이 포함된 경우
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any(self.bot_name in arg for arg in cmdline):
                    print(f"⚠️  기존 봇 프로세스 발견 (PID: {proc.info['pid']})")
                    proc.terminate()  # 정상 종료 시도

                    # 3초 대기
                    time.sleep(0.5)

                    # 여전히 실행 중이면 강제 종료
                    if proc.is_running():
                        proc.kill()

                    killed_count += 1
                    print(f"   ✅ PID {proc.info['pid']} 종료 완료")

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if killed_count > 0:
            print(f"🧹 총 {killed_count}개의 기존 봇 프로세스 정리 완료")
            time.sleep(1)  # 프로세스 정리 대기

        return killed_count

    def write_pid_file(self):
        """현재 프로세스 ID를 파일에 저장"""
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        print(f"📝 현재 프로세스 ID 저장: {os.getpid()}")

    def cleanup_pid_file(self):
        """PID 파일 삭제"""
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)

    def ensure_single_instance(self):
        """단일 인스턴스를 보장하는 메인 메소드"""
        print("\n🔍 단일 인스턴스 확인 중...")

        # 1. 기존 프로세스 정리
        self.check_and_kill_existing()

        # 2. PID 파일 확인
        if os.path.exists(self.pid_file):
            with open(self.pid_file, 'r') as f:
                old_pid = int(f.read())

            # 해당 PID 프로세스가 실제로 실행 중인지 확인
            try:
                os.kill(old_pid, 0)  # 프로세스 존재 확인
                print(f"⚠️  이미 실행 중인 봇이 있습니다 (PID: {old_pid})")
                sys.exit(1)
            except OSError:
                # 프로세스가 없으면 파일만 삭제
                print(f"   ℹ️  이전 PID 파일 정리 (PID: {old_pid})")
                os.remove(self.pid_file)

        # 3. 새 PID 파일 작성
        self.write_pid_file()

        # 4. 종료 시그널 핸들러 등록
        signal.signal(signal.SIGTERM, self._cleanup_handler)
        signal.signal(signal.SIGINT, self._cleanup_handler)

        print("✅ 단일 인스턴스 보장 완료\n")

    def _cleanup_handler(self, signum, frame):
        """종료 시그널 핸들러"""
        print("\n🛑 봇 종료 신호 수신...")
        self.cleanup_pid_file()
        sys.exit(0)