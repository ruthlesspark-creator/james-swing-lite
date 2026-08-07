from __future__ import annotations

import asyncio
import io
import logging
import logging.handlers
import os
from pathlib import Path
import socket
import sys
import webbrowser

import uvicorn

from james_swing_lite.app import LiteSupervisor
from james_swing_lite.dashboard import create_dashboard
from james_swing_lite.updater import check_and_update


# ──────────────────────────────────────────────────────────────────────────────
# PyInstaller --windowed 환경 대응
# windowed 모드에서는 sys.stdout / sys.stderr 가 None 이므로
# uvicorn 기본 log_config 가 StreamHandler(sys.stdout) 을 생성할 때
# NoneType.isatty() → AttributeError / ValueError 발생.
# → sys.stdout/stderr 를 안전한 NullWriter 로 교체하고
#   uvicorn 로그는 파일 + 메모리 핸들러로만 라우팅한다.
# ──────────────────────────────────────────────────────────────────────────────

class _NullWriter(io.RawIOBase):
    """콘솔이 없는 환경에서 sys.stdout / sys.stderr 대체용 더미 writer."""

    def write(self, b):  # noqa: ANN001, ANN201
        return len(b) if isinstance(b, (bytes, bytearray)) else 0

    def writelines(self, lines):  # noqa: ANN001, ANN201
        pass

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False


def _patch_stdio() -> None:
    """sys.stdout/stderr 가 None 이면 _NullWriter 로 교체."""
    null = _NullWriter()
    text_null = io.TextIOWrapper(null, encoding="utf-8", errors="replace")
    if sys.stdout is None:
        sys.stdout = text_null
    if sys.stderr is None:
        sys.stderr = text_null


def _resolve_log_dir() -> Path:
    """로그 디렉터리 결정: EXE 옆 logs/ 또는 %APPDATA%/JAMES_Swing_Lite/logs/."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        log_dir = exe_dir / "logs"
    else:
        log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _build_uvicorn_log_config(log_path: Path) -> dict:
    """
    uvicorn 에 전달할 커스텀 log_config dict.
    StreamHandler 를 완전히 제거하고 RotatingFileHandler 만 사용.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "logging.Formatter",
                "fmt": "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_path),
                "maxBytes": 5 * 1024 * 1024,   # 5 MB
                "backupCount": 3,
                "encoding": "utf-8",
                "formatter": "default",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["file"], "level": "WARNING", "propagate": False},
            "uvicorn.error": {"handlers": ["file"], "level": "WARNING", "propagate": False},
            "uvicorn.access": {"handlers": ["file"], "level": "WARNING", "propagate": False},
        },
    }


def _setup_app_logger(log_path: Path) -> logging.Logger:
    """애플리케이션 전체 파일 로거 설정."""
    logger = logging.getLogger("james_swing_lite")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(fh)
    return logger


# ──────────────────────────────────────────────────────────────────────────────

def bundled_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidate = root / relative
    if candidate.exists():
        return candidate
    return Path(relative)


def find_available_port(preferred: int = 8780) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("사용 가능한 포트를 찾을 수 없습니다 (8780~8799)")


async def open_browser(url: str) -> None:
    await asyncio.sleep(1.5)
    webbrowser.open(url, new=2)


async def main() -> None:
    # 1. stdio 패치 (windowed EXE 환경 대응)
    _patch_stdio()

    # 2. 로그 파일 설정
    log_dir = _resolve_log_dir()
    log_path = log_dir / "james_swing_lite.log"
    logger = _setup_app_logger(log_path)
    logger.info("JAMES 스윙 Lite 시작 중...")

    # 3. 자동 업데이트 확인 (.exe 모드에서만 동작)
    try:
        if check_and_update():
            sys.exit(0)
    except Exception as exc:
        logger.warning("자동 업데이트 확인 실패 (무시하고 계속): %s", exc)

    # 4. 서버 기동
    supervisor = LiteSupervisor(bundled_path("config/swing_lite.yaml"))
    app = create_dashboard(supervisor)
    port = find_available_port()
    url = f"http://127.0.0.1:{port}"

    uvicorn_log_config = _build_uvicorn_log_config(log_dir / "uvicorn.log")

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        log_config=uvicorn_log_config,
    )
    server = uvicorn.Server(config)

    logger.info("대시보드 URL: %s", url)

    await asyncio.gather(
        supervisor.start(),
        server.serve(),
        open_browser(url),
    )


if __name__ == "__main__":
    asyncio.run(main())
