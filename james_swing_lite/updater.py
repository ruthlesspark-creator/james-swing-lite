"""
JAMES Swing Lite — 자동 업데이트 모듈
실행 시마다 GitHub에서 최신 버전을 확인하고 자동으로 업데이트합니다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

GITHUB_OWNER = "ruthlesspark-creator"
GITHUB_REPO = "james-swing-lite"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/version.json"
RELEASE_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest/download/JAMES_스윙_Lite.exe"

# 현재 버전 (빌드 시 자동 갱신)
CURRENT_VERSION = "1.0.0"


def get_local_version() -> str:
    """현재 실행 중인 버전 반환."""
    version_file = Path(__file__).parent / "version.json"
    if version_file.exists():
        try:
            data = json.loads(version_file.read_text(encoding="utf-8"))
            return data.get("version", CURRENT_VERSION)
        except Exception:
            pass
    return CURRENT_VERSION


def get_remote_version() -> tuple[str, str] | None:
    """GitHub에서 최신 버전 정보 가져오기. (version, download_url) 반환."""
    try:
        req = urllib.request.Request(VERSION_URL, headers={"User-Agent": "JAMES-Swing-Lite"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("version"), data.get("download_url", RELEASE_URL)
    except Exception:
        return None


def check_and_update() -> bool:
    """
    업데이트 확인 후 필요 시 자동 업데이트.
    .exe 모드일 때만 실제 업데이트 진행.
    반환값: True = 업데이트 후 재시작 필요, False = 계속 실행
    """
    # 개발 환경(소스 실행)에서는 건너뜀
    if not getattr(sys, "frozen", False):
        return False

    result = get_remote_version()
    if result is None:
        return False  # 네트워크 없음 → 그냥 실행

    remote_ver, download_url = result
    local_ver = get_local_version()

    if remote_ver == local_ver:
        return False  # 최신 버전

    print(f"[업데이트] 새 버전 발견: {local_ver} → {remote_ver}")
    print("[업데이트] 다운로드 중...")

    try:
        exe_path = Path(sys.executable)
        tmp_path = exe_path.parent / f"JAMES_update_{remote_ver}.exe"

        # 새 버전 다운로드
        req = urllib.request.Request(download_url, headers={"User-Agent": "JAMES-Swing-Lite"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            tmp_path.write_bytes(resp.read())

        print("[업데이트] 다운로드 완료. 업데이트 적용 중...")

        # 배치 파일로 교체 (실행 중인 .exe는 직접 교체 불가)
        bat = tempfile.NamedTemporaryFile(suffix=".bat", delete=False, mode="w", encoding="utf-8")
        bat.write(f"""@echo off
timeout /t 2 /nobreak > nul
move /y "{tmp_path}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
""")
        bat.close()
        subprocess.Popen(["cmd.exe", "/c", bat.name], creationflags=0x08000000)
        return True  # 재시작 필요

    except Exception as e:
        print(f"[업데이트] 실패 (계속 실행): {e}")
        return False
