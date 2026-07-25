from __future__ import annotations

from decimal import Decimal

from .domain import Position, PositionStage


class PositionManager:
    def __init__(self) -> None:
        self.position: Position | None = None

    def current(self) -> Position | None:
        return self.position

    def restore(self, position: Position | None) -> None:
        self.position = position

    def margin_used(self, leverage: int) -> Decimal:
        if self.position is None or not self.position.is_open:
            return Decimal("0")
        return (self.position.quantity * self.position.average_entry / Decimal(leverage)).quantize(Decimal("0.00000001"))

    def serialize(self) -> dict[str, str] | None:
        if self.position is None:
            return None
        return {
            "symbol": self.position.symbol,
            "side": self.position.side,
            "quantity": str(self.position.quantity),
            "average_entry": str(self.position.average_entry),
            "stage": self.position.stage.value,
            "realized_pnl": str(self.position.realized_pnl),
        }

    @staticmethod
    def deserialize(payload: dict[str, str] | None) -> Position | None:
        if not payload:
            return None
        return Position(
            symbol=payload["symbol"],
            side=payload["side"],
            quantity=Decimal(payload["quantity"]),
            average_entry=Decimal(payload["average_entry"]),
            stage=PositionStage(payload["stage"]),
            realized_pnl=Decimal(payload.get("realized_pnl", "0")),
        )
