from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .domain import AccountingSnapshot, HealthState, MarketSnapshot, Position, RiskPlan


SCHEMA = (
    "CREATE TABLE IF NOT EXISTS lite_market_candles (id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT, open_time_ms INTEGER, open TEXT, high TEXT, low TEXT, close TEXT, volume TEXT, received_at TEXT);",
    "CREATE TABLE IF NOT EXISTS lite_system_state (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL, updated_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS lite_positions (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT, updated_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS lite_position_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS lite_fills (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, created_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS lite_accounting_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, created_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS lite_risk_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, created_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS lite_config_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, created_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS lite_errors (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS lite_trade_history (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, action TEXT NOT NULL, side TEXT, fill_price TEXT, quantity TEXT, fee TEXT, pnl TEXT, stage TEXT, reason TEXT, created_at TEXT NOT NULL);",
)


class LiteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        for statement in SCHEMA:
            self.conn.execute(statement)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _json(self, payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    def save_market(self, snapshot: MarketSnapshot) -> None:
        for candle in snapshot.candles.values():
            self.conn.execute(
                "INSERT INTO lite_market_candles(symbol,timeframe,open_time_ms,open,high,low,close,volume,received_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (candle.symbol, candle.timeframe, candle.open_time_ms, str(candle.open), str(candle.high), str(candle.low), str(candle.close), str(candle.volume), candle.received_at.isoformat()),
            )
        self.conn.commit()

    def save_system_state(self, health: HealthState) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO lite_system_state(id,payload,updated_at) VALUES(1,?,?)",
            (self._json(health.__dict__), datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def save_position(self, position: Position | None) -> None:
        payload = None if position is None else self._json(position.__dict__)
        self.conn.execute(
            "INSERT OR REPLACE INTO lite_positions(id,payload,updated_at) VALUES(1,?,?)",
            (payload, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def load_position_payload(self) -> dict[str, str] | None:
        row = self.conn.execute("SELECT payload FROM lite_positions WHERE id=1").fetchone()
        if not row or not row[0]:
            return None
        return json.loads(row[0])

    def save_accounting(self, snapshot: AccountingSnapshot) -> None:
        self.conn.execute(
            "INSERT INTO lite_accounting_snapshots(payload,created_at) VALUES(?,?)",
            (self._json(snapshot.__dict__), datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def save_risk_plan(self, plan: RiskPlan) -> None:
        self.conn.execute(
            "INSERT INTO lite_risk_plans(payload,created_at) VALUES(?,?)",
            (self._json(plan.__dict__), datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def save_error(self, code: str, payload: dict[str, object]) -> None:
        self.conn.execute(
            "INSERT INTO lite_errors(code,payload,created_at) VALUES(?,?,?)",
            (code, self._json(payload), datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def save_trade_history(self, symbol: str, result: object) -> None:
        """매매 실행 이력 저장 (추후 전략 분석용)."""
        self.conn.execute(
            "INSERT INTO lite_trade_history(symbol,action,side,fill_price,quantity,fee,pnl,stage,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                symbol,
                getattr(result, "action", ""),
                "",
                str(getattr(result, "fill_price", "")),
                str(getattr(result, "quantity", "")),
                str(getattr(result, "fee", "")),
                str(getattr(result, "pnl", "")),
                result.stage.value if getattr(result, "stage", None) else "",
                getattr(result, "reason", ""),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()

    def table_names(self) -> list[str]:
        rows = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'lite_%' ORDER BY name").fetchall()
        return [row[0] for row in rows]
