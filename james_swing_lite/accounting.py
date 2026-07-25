from __future__ import annotations

from decimal import Decimal

from .domain import AccountingSnapshot, Position


class AccountingEngine:
    def __init__(self, initial_equity: Decimal) -> None:
        self.initial_equity = initial_equity
        self.realized_pnl = Decimal("0")
        self.fees_paid = Decimal("0")
        self.funding_paid = Decimal("0")

    def taker_fee(self, notional: Decimal, fee_rate: Decimal) -> Decimal:
        return (notional * fee_rate).quantize(Decimal("0.00000001"))

    def unrealized_pnl(self, position: Position | None, mark_price: Decimal) -> Decimal:
        if position is None or not position.is_open:
            return Decimal("0")
        direction = Decimal("1") if position.side == "LONG" else Decimal("-1")
        return (mark_price - position.average_entry) * position.quantity * direction

    def apply_fill(self, pnl: Decimal, fee: Decimal) -> None:
        """매매 결과(PnL, 수수료)를 accounting에 반영."""
        self.realized_pnl += pnl
        self.fees_paid += fee

    def snapshot(self, position: Position | None, mark_price: Decimal, margin_used: Decimal) -> AccountingSnapshot:
        unrealized = self.unrealized_pnl(position, mark_price)
        equity = self.initial_equity + self.realized_pnl + unrealized - self.fees_paid - self.funding_paid
        return AccountingSnapshot(
            equity=equity,
            available_equity=equity - margin_used,
            margin_used=margin_used,
            unrealized_pnl=unrealized,
            realized_pnl=self.realized_pnl,
            fees_paid=self.fees_paid,
            funding_paid=self.funding_paid,
        )
