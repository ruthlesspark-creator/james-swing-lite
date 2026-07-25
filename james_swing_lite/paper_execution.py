from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .config import LiteConfig
from .domain import (
    AccountingSnapshot,
    DecisionAction,
    MarketSnapshot,
    Position,
    PositionStage,
    StrategyDecision,
)
from .position import PositionManager

SLIPPAGE = Decimal("0.0005")  # 0.05% 슬리피지


@dataclass
class ExecutionResult:
    accepted: bool
    action: str
    fill_price: Decimal
    quantity: Decimal
    fee: Decimal
    pnl: Decimal
    stage: PositionStage | None
    reason: str


class PaperExecutionEngine:
    """Paper 모드 주문 실행 엔진. 슬리피지·Taker 수수료 적용."""

    def __init__(self, config: LiteConfig) -> None:
        self.config = config
        self.generated_orders: int = 0

    def _fill_price(self, price: Decimal, buying: bool) -> Decimal:
        """슬리피지 적용 체결가."""
        if buying:
            return (price * (1 + SLIPPAGE)).quantize(Decimal("0.00001"))
        return (price * (1 - SLIPPAGE)).quantize(Decimal("0.00001"))

    def _qty(self, equity: Decimal, alloc: Decimal, price: Decimal) -> Decimal:
        """할당 비율 + 레버리지로 수량 계산."""
        notional = equity * alloc * Decimal(self.config.leverage)
        return (notional / price).quantize(Decimal("0.001"))

    def execute(
        self,
        decision: StrategyDecision,
        pos_mgr: PositionManager,
        accounting: AccountingSnapshot,
        market: MarketSnapshot,
    ) -> ExecutionResult:
        action = decision.action
        price = market.last_price
        equity = accounting.equity
        allocs = self.config.entry_allocations
        alloc_map = {
            PositionStage.ENTRY_1: allocs[0] if len(allocs) > 0 else Decimal("0.15"),
            PositionStage.ENTRY_2: allocs[1] if len(allocs) > 1 else Decimal("0.10"),
            PositionStage.ENTRY_3: allocs[2] if len(allocs) > 2 else Decimal("0.10"),
            PositionStage.ENTRY_4: allocs[3] if len(allocs) > 3 else Decimal("0.08"),
        }
        pos = pos_mgr.current()

        # ── 신규 진입 ───────────────────────────────────────────────
        if action in (DecisionAction.ENTER_LONG, DecisionAction.ENTER_SHORT):
            if pos and pos.is_open:
                return ExecutionResult(
                    False, action.value, Decimal("0"), Decimal("0"),
                    Decimal("0"), Decimal("0"), None, "이미 포지션 존재",
                )
            side = "LONG" if action == DecisionAction.ENTER_LONG else "SHORT"
            fill = self._fill_price(price, side == "LONG")
            qty = self._qty(equity, alloc_map[PositionStage.ENTRY_1], fill)
            if qty <= 0:
                return ExecutionResult(
                    False, action.value, fill, qty,
                    Decimal("0"), Decimal("0"), None, "수량 부족",
                )
            fee = (qty * fill * self.config.taker_fee_rate).quantize(Decimal("0.00000001"))
            new_pos = Position(
                symbol=market.symbol, side=side, quantity=qty,
                average_entry=fill, stage=PositionStage.ENTRY_1,
                realized_pnl=Decimal("0"),
            )
            pos_mgr.restore(new_pos)
            self.generated_orders += 1
            return ExecutionResult(
                True, action.value, fill, qty, fee, Decimal("0"),
                PositionStage.ENTRY_1,
                f"{side} 1차 진입 {qty:.3f}@{fill}",
            )

        # ── 분할 추가 매수 ──────────────────────────────────────────
        if action in (DecisionAction.ADD_LONG, DecisionAction.ADD_SHORT):
            if not pos or not pos.is_open:
                return ExecutionResult(
                    False, action.value, Decimal("0"), Decimal("0"),
                    Decimal("0"), Decimal("0"), None, "포지션 없음",
                )
            stage_seq = [
                PositionStage.ENTRY_1, PositionStage.ENTRY_2,
                PositionStage.ENTRY_3, PositionStage.ENTRY_4,
            ]
            if pos.stage not in stage_seq:
                return ExecutionResult(
                    False, action.value, Decimal("0"), Decimal("0"),
                    Decimal("0"), Decimal("0"), None, "분할 불가 단계",
                )
            idx = stage_seq.index(pos.stage)
            if idx >= len(stage_seq) - 1:
                return ExecutionResult(
                    False, action.value, Decimal("0"), Decimal("0"),
                    Decimal("0"), Decimal("0"), None, "마지막 분할 완료",
                )
            next_stage = stage_seq[idx + 1]
            fill = self._fill_price(price, pos.side == "LONG")
            add_qty = self._qty(equity, alloc_map[next_stage], fill)
            fee = (add_qty * fill * self.config.taker_fee_rate).quantize(Decimal("0.00000001"))
            total_qty = pos.quantity + add_qty
            new_avg = (pos.quantity * pos.average_entry + add_qty * fill) / total_qty
            new_pos = Position(
                symbol=pos.symbol, side=pos.side, quantity=total_qty,
                average_entry=new_avg.quantize(Decimal("0.00001")),
                stage=next_stage, realized_pnl=pos.realized_pnl,
            )
            pos_mgr.restore(new_pos)
            self.generated_orders += 1
            return ExecutionResult(
                True, action.value, fill, add_qty, fee, Decimal("0"),
                next_stage,
                f"분할매수 {idx + 2}차 {add_qty:.3f}@{fill}",
            )

        # ── 부분 청산 (75%) ─────────────────────────────────────────
        if action == DecisionAction.EXIT_PARTIAL:
            if not pos or not pos.is_open:
                return ExecutionResult(
                    False, action.value, Decimal("0"), Decimal("0"),
                    Decimal("0"), Decimal("0"), None, "포지션 없음",
                )
            exit_qty = (pos.quantity * Decimal("0.75")).quantize(Decimal("0.001"))
            fill = self._fill_price(price, pos.side == "SHORT")
            direction = Decimal("1") if pos.side == "LONG" else Decimal("-1")
            pnl = (fill - pos.average_entry) * exit_qty * direction
            fee = (exit_qty * fill * self.config.taker_fee_rate).quantize(Decimal("0.00000001"))
            remain = pos.quantity - exit_qty
            new_pos = Position(
                symbol=pos.symbol, side=pos.side, quantity=remain,
                average_entry=pos.average_entry, stage=PositionStage.RUNNER_25,
                realized_pnl=pos.realized_pnl + pnl,
            )
            pos_mgr.restore(new_pos)
            self.generated_orders += 1
            return ExecutionResult(
                True, action.value, fill, exit_qty, fee, pnl,
                PositionStage.RUNNER_25,
                f"75% 익절 PnL={pnl:.4f} USDT",
            )

        # ── 전량 청산 ────────────────────────────────────────────────
        if action == DecisionAction.EXIT_ALL:
            if not pos or not pos.is_open:
                return ExecutionResult(
                    False, action.value, Decimal("0"), Decimal("0"),
                    Decimal("0"), Decimal("0"), None, "포지션 없음",
                )
            fill = self._fill_price(price, pos.side == "SHORT")
            direction = Decimal("1") if pos.side == "LONG" else Decimal("-1")
            pnl = (fill - pos.average_entry) * pos.quantity * direction
            fee = (pos.quantity * fill * self.config.taker_fee_rate).quantize(Decimal("0.00000001"))
            new_pos = Position(
                symbol=pos.symbol, side=pos.side, quantity=Decimal("0"),
                average_entry=pos.average_entry, stage=PositionStage.CLOSED,
                realized_pnl=pos.realized_pnl + pnl,
            )
            pos_mgr.restore(new_pos)
            self.generated_orders += 1
            return ExecutionResult(
                True, action.value, fill, pos.quantity, fee, pnl,
                PositionStage.CLOSED,
                f"전량 청산 PnL={pnl:.4f} USDT",
            )

        return ExecutionResult(
            False, action.value, Decimal("0"), Decimal("0"),
            Decimal("0"), Decimal("0"), None, "처리되지 않은 액션",
        )
