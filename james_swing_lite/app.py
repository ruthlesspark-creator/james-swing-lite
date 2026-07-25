from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .accounting import AccountingEngine
from .config import LiteConfig, load_config
from .domain import MarketBias, MarketSnapshot
from .health import HealthMonitor
from .market_data import BinancePublicMarketData
from .market_state import MarketStateEngine
from .paper_execution import PaperExecutionEngine
from .position import PositionManager
from .risk import RiskEngine
from .storage import LiteDatabase
from .strategy import StrategyEngine


class LiteSupervisor:
    def __init__(self, config_path: Path) -> None:
        self.config: LiteConfig = load_config(config_path)
        self.db = LiteDatabase(self.config.database_path)
        self.market_data = BinancePublicMarketData(self.config)
        self.market_state = MarketStateEngine(self.config)
        self.accounting = AccountingEngine(self.config.initial_equity)
        self.positions = PositionManager()
        self.positions.restore(PositionManager.deserialize(self.db.load_position_payload()))
        self.risk = RiskEngine(self.config)
        self.execution = PaperExecutionEngine(config=self.config)
        self.strategy = StrategyEngine()
        self.health = HealthMonitor()
        self.latest_market = MarketSnapshot(
            self.config.symbol, Decimal("0"), {}, datetime.now(timezone.utc), True, "시장 데이터 수신 전"
        )
        self.latest_decision = self.strategy.decide(self.latest_market)
        self.latest_accounting = self.accounting.snapshot(None, Decimal("0"), Decimal("0"))
        self.latest_risk = self.risk.plan(self.latest_accounting, Decimal("0"))
        self._stop = asyncio.Event()

    async def start(self) -> None:
        while not self._stop.is_set():
            await self.step()
            await asyncio.sleep(30)

    def stop(self) -> None:
        self._stop.set()

    async def step(self) -> None:
        try:
            market = await self.market_data.refresh_once()
            self.latest_market = self.market_state.evaluate(market)
            position = self.positions.current()
            margin = self.positions.margin_used(self.config.leverage)
            self.latest_accounting = self.accounting.snapshot(
                position, self.latest_market.last_price, margin
            )
            self.latest_risk = self.risk.plan(self.latest_accounting, self.latest_market.last_price)
            self.latest_decision = self.strategy.decide(self.latest_market, position)

            # Paper 실행: 주문 생성 허용된 경우에만
            if self.latest_decision.order_generation_allowed:
                result = self.execution.execute(
                    self.latest_decision,
                    self.positions,
                    self.latest_accounting,
                    self.latest_market,
                )
                if result.accepted:
                    self.accounting.apply_fill(result.pnl, result.fee)
                    self.db.save_trade_history(self.config.symbol, result)
                    # accounting 재계산 (fill 반영 후)
                    position = self.positions.current()
                    margin = self.positions.margin_used(self.config.leverage)
                    self.latest_accounting = self.accounting.snapshot(
                        position, self.latest_market.last_price, margin
                    )

            self.db.save_market(self.latest_market)
            self.db.save_accounting(self.latest_accounting)
            self.db.save_risk_plan(self.latest_risk)
            self.db.save_position(self.positions.current())
            self.db.save_system_state(self.health.state(self.execution.generated_orders))
        except Exception as exc:
            self.health.errors.append(str(exc))
            self.db.save_error("LITE_STEP_ERROR", {"error": str(exc), "type": type(exc).__name__})

    def change_symbol(self, symbol: str) -> None:
        """실시간 종목 전환. config yaml도 업데이트."""
        import yaml
        from pathlib import Path
        allowed = {"BTCUSDT", "ADAUSDT"}
        if symbol not in allowed:
            raise ValueError(f"지원 종목: {allowed}")
        # config yaml 업데이트
        config_path = Path(__file__).resolve().parent.parent / "config" / "swing_lite.yaml"
        if config_path.exists():
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            raw.setdefault("market", {})["symbols"] = [symbol]
            config_path.write_text(
                yaml.dump(raw, allow_unicode=True, default_flow_style=False),
                encoding="utf-8"
            )
        # 런타임 재구성
        from .config import load_config
        self.config = load_config(config_path)
        self.market_data = BinancePublicMarketData(self.config)
        self.market_state = MarketStateEngine(self.config)
        self.positions = PositionManager()
        self.positions.restore(PositionManager.deserialize(self.db.load_position_payload()))
        self.risk = RiskEngine(self.config)
        self.execution = PaperExecutionEngine(config=self.config)
        self.latest_market = MarketSnapshot(
            self.config.symbol, Decimal("0"), {}, datetime.now(timezone.utc), True, "종목 전환됨"
        )
        self.latest_decision = self.strategy.decide(self.latest_market)

    def snapshot(self) -> dict[str, object]:
        position = self.positions.serialize() or {
            "stage": "포지션 없음", "quantity": "0", "average_entry": "-", "side": "-"
        }
        tech = self.latest_market.technical
        sent = self.latest_market.sentiment
        return {
            "identity": {
                "engine": "JAMES_SWING_LITE",
                "version": "0.2.0-PAPER-KO",
                "paper_only": True,
                "live_enabled": False,
                "strategy": self.strategy.version,
                "symbol": self.config.symbol,
                "database_path": str(self.config.database_path),
            },
            "health": self.health.state(self.execution.generated_orders).__dict__,
            "market": {
                "symbol": self.config.symbol,
                "last_price": str(self.latest_market.last_price),
                "timeframes": list(self.latest_market.candles),
                "stale": self.latest_market.stale,
                "reason": self.latest_market.reason,
            },
            "bias": self.latest_decision.market_bias.value,
            "decision": {
                "action": self.latest_decision.action.value,
                "reason": self.latest_decision.reason,
                "order_generation_allowed": self.latest_decision.order_generation_allowed,
            },
            "technical": {
                "ema20_4h": f"{tech.ema20_4h:.2f}" if tech else "-",
                "ema50_4h": f"{tech.ema50_4h:.2f}" if tech else "-",
                "ema200_4h": f"{tech.ema200_4h:.2f}" if tech else "-",
                "rsi14_1h": f"{tech.rsi14_1h:.1f}" if tech else "-",
                "rsi14_15m": f"{tech.rsi14_15m:.1f}" if tech else "-",
                "atr14_1h": f"{tech.atr14_1h:.2f}" if tech else "-",
            } if tech else {},
            "sentiment": {
                "oi_change_pct": f"{sent.oi_change_pct:.2f}%" if sent else "-",
                "top_ls_ratio": f"{sent.top_ls_ratio:.3f}" if sent else "-",
                "global_ls_ratio": f"{sent.global_ls_ratio:.3f}" if sent else "-",
                "taker_buy_ratio": f"{sent.taker_buy_ratio:.3f}" if sent else "-",
                "funding_rate": f"{sent.funding_rate:.5f}" if sent else "-",
            } if sent else {},
            "position": position,
            "accounting": {key: str(value) for key, value in self.latest_accounting.__dict__.items()},
            "risk": {
                "leverage": self.latest_risk.leverage,
                "structural_stop": (
                    None if self.latest_risk.structural_stop is None
                    else str(self.latest_risk.structural_stop)
                ),
                "hard_blocks": self.latest_risk.hard_blocks,
            },
        }
