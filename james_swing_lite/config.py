from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any

import yaml


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

    db_path = Path(str(storage.get("database_path", "outputs/data/james_swing_lite.sqlite3")))
    if not db_path.is_absolute():
        if getattr(sys, "frozen", False):
            db_path = Path(sys.executable).resolve().parents[3] / db_path
        else:
            db_path = Path.cwd() / db_path

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
