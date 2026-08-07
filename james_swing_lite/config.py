from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import os
from pathlib import Path
import sys
from typing import Any

import yaml


# ──────────────────────────────────────────────────────────────────────────────
# 배포 환경 데이터 루트 결정
# PyInstaller --windowed EXE, 개발환경 모두에서 안전하게 동작하는
# 사용자 쓰기 가능 영구 경로를 반환한다.
#
# 우선순위:
#  1. %LOCALAPPDATA%\JAMES_SWING_LITE  (Windows 권장 — Program Files에서도 쓰기 가능)
#  2. ~/JAMES_SWING_LITE               (Linux/macOS 폴백)
#  3. ./JAMES_SWING_LITE               (환경변수 없을 때 최후 폴백)
#
# sys._MEIPASS 는 읽기 전용 번들 리소스 경로이므로
# DB/로그 등 쓰기 데이터 저장에 절대 사용하지 않는다.
# ──────────────────────────────────────────────────────────────────────────────

APP_NAME = "JAMES_SWING_LITE"


def _resolve_app_data_root() -> Path:
    """어느 Windows PC에서 실행해도 쓰기 가능한 앱 데이터 루트 경로 반환."""
    # Windows: %LOCALAPPDATA%\JAMES_SWING_LITE
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME
    # macOS/Linux: ~/JAMES_SWING_LITE
    home = Path.home()
    if home != Path("/"):
        return home / APP_NAME
    # 최후 폴백: 현재 작업 디렉터리
    return Path.cwd() / APP_NAME


def _ensure_app_dirs(root: Path) -> None:
    """앱 데이터 하위 폴더 자동 생성 (data/, logs/, config/)."""
    for sub in ("data", "logs", "config"):
        (root / sub).mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class LiteConfig:
    symbol: str
    timeframes: tuple[str, ...]
    data_stale_seconds: int
    rest_base_url: str
    websocket_base_url: str
    initial_equity: Decimal
    currency: str
    leverage: int
    max_account_risk_pct: Decimal
    max_total_margin_pct: Decimal
    min_liquidation_distance_pct: Decimal
    entry_allocations: tuple[Decimal, ...]
    first_exit_ratio: Decimal
    runner_ratio: Decimal
    max_open_positions: int
    maker_fee_rate: Decimal
    taker_fee_rate: Decimal
    funding_mode: str
    database_path: Path
    dashboard_language: str
    dashboard_host: str
    dashboard_port: int
    paper_only: bool
    live_enabled: bool
    order_generation_enabled: bool


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"Field={field_name} Value={value!r} Type={type(value).__name__}") from exc


def load_config(path: Path) -> LiteConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    engine = raw.get("engine", {})
    market = raw.get("market", {})
    account = raw.get("account", {})
    risk = raw.get("risk", {})
    position = raw.get("position", {})
    fees = raw.get("fees", {})
    funding = raw.get("funding", {})
    storage = raw.get("storage", {})
    dashboard = raw.get("dashboard", {})

    symbols = tuple(str(item).upper() for item in market.get("symbols", ["BTCUSDT"]))
    ALLOWED_SYMBOLS = {"BTCUSDT", "ADAUSDT"}
    if symbols[0] not in ALLOWED_SYMBOLS:
        raise ValueError(f"지원 종목: {ALLOWED_SYMBOLS} (현재값: {symbols[0]})")
    if bool(engine.get("live_enabled", False)):
        raise ValueError("실거래(LIVE)는 비활성 상태를 유지해야 합니다")
    # 모의투자(paper_only=true) 모드에서는 order_generation_enabled 허용

    db_path_raw = str(storage.get("database_path", ""))

    if db_path_raw and Path(db_path_raw).is_absolute():
        # YAML에 절대경로가 명시된 경우 그대로 사용 (개발환경 커스텀 경로 지원)
        db_path = Path(db_path_raw)
    else:
        # 배포 환경: %LOCALAPPDATA%\JAMES_SWING_LITE\data\james_swing_lite.db
        app_root = _resolve_app_data_root()
        _ensure_app_dirs(app_root)
        db_path = app_root / "data" / "james_swing_lite.db"

    return LiteConfig(
        symbol=symbols[0],
        timeframes=tuple(str(item) for item in market.get("timeframes", ["4h", "1h", "15m"])),
        data_stale_seconds=int(market.get("data_stale_seconds", 1800)),
        rest_base_url=str(market.get("rest_base_url", "https://fapi.binance.com")),
        websocket_base_url=str(market.get("websocket_base_url", "wss://fstream.binance.com/ws")),
        initial_equity=_decimal(account.get("initial_equity", "1000"), "account.initial_equity"),
        currency=str(account.get("currency", "USDT")),
        leverage=int(risk.get("leverage", 20)),
        max_account_risk_pct=_decimal(risk.get("max_account_risk_pct", "0.025"), "risk.max_account_risk_pct"),
        max_total_margin_pct=_decimal(risk.get("max_total_margin_pct", "0.43"), "risk.max_total_margin_pct"),
        min_liquidation_distance_pct=_decimal(
            risk.get("min_liquidation_distance_pct", "0.05"), "risk.min_liquidation_distance_pct"
        ),
        entry_allocations=tuple(_decimal(item, "position.entry_allocations") for item in position.get("entry_allocations", [])),
        first_exit_ratio=_decimal(position.get("first_exit_ratio", "0.75"), "position.first_exit_ratio"),
        runner_ratio=_decimal(position.get("runner_ratio", "0.25"), "position.runner_ratio"),
        max_open_positions=int(position.get("max_open_positions", 1)),
        maker_fee_rate=_decimal(fees.get("maker_fee_rate", "0.0002"), "fees.maker_fee_rate"),
        taker_fee_rate=_decimal(fees.get("taker_fee_rate", "0.0004"), "fees.taker_fee_rate"),
        funding_mode=str(funding.get("mode", "REAL_MARKET_FUNDING")),
        database_path=db_path,
        dashboard_language=str(dashboard.get("language", "ko")),
        dashboard_host=str(dashboard.get("host", "127.0.0.1")),
        dashboard_port=int(dashboard.get("port", 8780)),
        paper_only=bool(engine.get("paper_only", True)),
        live_enabled=bool(engine.get("live_enabled", False)),
        order_generation_enabled=bool(engine.get("order_generation_enabled", False)),
    )
