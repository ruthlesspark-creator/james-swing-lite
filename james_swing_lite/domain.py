from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


UTC = timezone.utc


class EngineMode(str, Enum):
    PAPER = "PAPER"


class PositionStage(str, Enum):
    NONE = "NONE"
    ENTRY_1 = "ENTRY_1"
    ENTRY_2 = "ENTRY_2"
    ENTRY_3 = "ENTRY_3"
    ENTRY_4 = "ENTRY_4"
    EXIT_75 = "EXIT_75"
    RUNNER_25 = "RUNNER_25"
    CLOSED = "CLOSED"


class DecisionAction(str, Enum):
    NO_DECISION = "NO_DECISION"
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    ADD_LONG = "ADD_LONG"
    ADD_SHORT = "ADD_SHORT"
    EXIT_PARTIAL = "EXIT_PARTIAL"
    EXIT_ALL = "EXIT_ALL"
    HOLD = "HOLD"


class MarketBias(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    open_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class SentimentData:
    oi_change_pct: Decimal          # OI 변화율 (%)
    top_ls_ratio: Decimal           # Top Trader L/S 비율
    global_ls_ratio: Decimal        # 전체 계좌 L/S 비율
    taker_buy_ratio: Decimal        # Taker 매수 비율 (0~1)
    funding_rate: Decimal           # 최근 펀딩비
    oi_volume_ratio: Decimal        # OI/거래량 비율


@dataclass(frozen=True)
class TechnicalData:
    ema20_4h: Decimal
    ema50_4h: Decimal
    ema200_4h: Decimal
    ema20_1h: Decimal
    ema50_1h: Decimal
    rsi14_1h: Decimal
    rsi14_15m: Decimal
    atr14_1h: Decimal
    close_15m: Decimal
    high_15m: Decimal
    low_15m: Decimal


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    last_price: Decimal
    candles: dict[str, Candle]
    updated_at: datetime
    stale: bool
    reason: str = ""
    sentiment: SentimentData | None = None
    technical: TechnicalData | None = None


@dataclass(frozen=True)
class StrategyDecision:
    symbol: str
    action: DecisionAction
    reason: str
    order_generation_allowed: bool = False
    market_bias: MarketBias = MarketBias.NEUTRAL


@dataclass(frozen=True)
class Position:
    symbol: str
    side: str
    quantity: Decimal
    average_entry: Decimal
    stage: PositionStage
    realized_pnl: Decimal = Decimal("0")

    @property
    def is_open(self) -> bool:
        return self.quantity > 0 and self.stage not in {PositionStage.NONE, PositionStage.CLOSED}


@dataclass(frozen=True)
class AccountingSnapshot:
    equity: Decimal
    available_equity: Decimal
    margin_used: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal
    funding_paid: Decimal


@dataclass(frozen=True)
class RiskPlan:
    symbol: str
    leverage: int
    max_account_risk_pct: Decimal
    max_total_margin_pct: Decimal
    structural_stop: Decimal | None
    hard_blocks: list[str]


@dataclass(frozen=True)
class HealthState:
    status: str
    live_blocked: bool
    private_orders_blocked: bool
    legacy_loaded: bool
    research_loaded: bool
    order_count: int
    errors: list[str]
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
