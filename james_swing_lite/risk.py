from __future__ import annotations

from decimal import Decimal

from .config import LiteConfig
from .domain import AccountingSnapshot, RiskPlan


class RiskEngine:
    def __init__(self, config: LiteConfig) -> None:
        self.config = config

    def structural_stop(self, last_price: Decimal) -> Decimal:
        return (last_price * Decimal("0.95")).quantize(Decimal("0.01"))

    def plan(self, accounting: AccountingSnapshot, last_price: Decimal) -> RiskPlan:
        hard_blocks: list[str] = []
        stop = self.structural_stop(last_price) if last_price > 0 else None

        # 실거래 차단 (항상 유지)
        if not self.config.paper_only:
            hard_blocks.append("PAPER_MODE_REQUIRED")
        if self.config.live_enabled:
            hard_blocks.append("LIVE_BLOCKED")

        # 주문 생성이 비활성화된 경우에만 차단 표시
        if not self.config.order_generation_enabled:
            hard_blocks.append("ORDER_GENERATION_BLOCKED")

        if last_price <= 0:
            hard_blocks.append("INVALID_PRICE")
        if accounting.margin_used > accounting.equity * self.config.max_total_margin_pct:
            hard_blocks.append("MAX_TOTAL_MARGIN_EXCEEDED")
        if stop is None or stop <= 0 or stop >= last_price:
            hard_blocks.append("INVALID_STRUCTURAL_STOP")
        return RiskPlan(
            symbol=self.config.symbol,
            leverage=self.config.leverage,
            max_account_risk_pct=self.config.max_account_risk_pct,
            max_total_margin_pct=self.config.max_total_margin_pct,
            structural_stop=stop,
            hard_blocks=hard_blocks,
        )
