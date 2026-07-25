from __future__ import annotations

import asyncio
from pathlib import Path
import socket
import sys
import webbrowser

import uvicorn

from james_swing_lite.app import LiteSupervisor
from james_swing_lite.dashboard import create_dashboard
from james_swing_lite.updater import check_and_update


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
    raise RuntimeError("No available Lite dashboard port found")


async def open_browser(url: str) -> None:
    await asyncio.sleep(1.5)
    webbrowser.open(url, new=2)


async def main() -> None:
    # 자동 업데이트 확인 (.exe 모드에서만 동작)
    if check_and_update():
        sys.exit(0)  # 업데이트 후 재시작

    supervisor = LiteSupervisor(bundled_path("config/swing_lite.yaml"))
    app = create_dashboard(supervisor)
    port = find_available_port()
    url = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False))
    print(f"[정상] JAMES 스윙 Lite v1.0.0 모의투자가 시작되었습니다: {url}")
    await asyncio.gather(supervisor.start(), server.serve(), open_browser(url))


if __name__ == "__main__":
    asyncio.run(main())
