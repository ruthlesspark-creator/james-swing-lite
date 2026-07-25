from __future__ import annotations

from datetime import datetime, timezone

from .config import LiteConfig
from .domain import MarketSnapshot


class MarketStateEngine:
    def __init__(self, config: LiteConfig) -> None:
        self.config = config

    def evaluate(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        now = datetime.now(timezone.utc)
        missing = [tf for tf in self.config.timeframes if tf not in snapshot.candles]
        if missing:
            return MarketSnapshot(snapshot.symbol, snapshot.last_price, snapshot.candles, snapshot.updated_at, True, f"누락 시간봉: {', '.join(missing)}")
        age = (now - snapshot.updated_at).total_seconds()
        if age > self.config.data_stale_seconds:
            return MarketSnapshot(snapshot.symbol, snapshot.last_price, snapshot.candles, snapshot.updated_at, True, "데이터 지연")
        return snapshot
