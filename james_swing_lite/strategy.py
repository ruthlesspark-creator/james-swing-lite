from __future__ import annotations

from decimal import Decimal

from .domain import (
    DecisionAction,
    MarketBias,
    MarketSnapshot,
    PositionStage,
    StrategyDecision,
)
from .sentiment import SentimentAnalyzer


class StrategyEngine:
    """EMA + RSI + 감성지표 기반 멀티타임프레임 스윙 전략."""

    version = "swing_ema_rsi_sentiment_v1"
    _sentiment = SentimentAnalyzer()

    def decide(self, market: MarketSnapshot, position=None) -> StrategyDecision:
        """
        시장 바이어스 결정 → 신규 진입 / 분할매수 / 청산 판단.
        포지션 인자: Position 또는 None.
        """
        # 데이터 부족 시 대기
        if market.stale or market.technical is None or market.sentiment is None:
            return StrategyDecision(
                symbol=market.symbol,
                action=DecisionAction.NO_DECISION,
                reason=f"데이터 대기: {market.reason}",
                order_generation_allowed=False,
            )

        tech = market.technical
        bias, bias_reason = self._sentiment.analyze(market.sentiment)

        # 포지션 있는 경우 → 관리 로직
        if position and position.is_open:
            return self._manage_position(market, position, tech, bias, bias_reason)

        # 포지션 없는 경우 → 신규 진입 판단
        return self._check_entry(market, tech, bias, bias_reason)

    def _manage_position(self, market, position, tech, bias, bias_reason) -> StrategyDecision:
        price = market.last_price

        # ── 손절: 진입가 대비 -5% ──────────────────────────────────
        if position.side == "LONG":
            stop_price = position.average_entry * Decimal("0.95")
            if price <= stop_price:
                return StrategyDecision(
                    symbol=market.symbol,
                    action=DecisionAction.EXIT_ALL,
                    reason=f"손절: 현재가 {price} ≤ 손절가 {stop_price:.2f}",
                    order_generation_allowed=True,
                    market_bias=bias,
                )
        else:
            stop_price = position.average_entry * Decimal("1.05")
            if price >= stop_price:
                return StrategyDecision(
                    symbol=market.symbol,
                    action=DecisionAction.EXIT_ALL,
                    reason=f"손절(숏): 현재가 {price} ≥ 손절가 {stop_price:.2f}",
                    order_generation_allowed=True,
                    market_bias=bias,
                )

        # ── 바이어스 전환 → 즉시 전량 청산 ───────────────────────────
        if position.side == "LONG" and bias == MarketBias.SHORT:
            return StrategyDecision(
                symbol=market.symbol,
                action=DecisionAction.EXIT_ALL,
                reason=f"바이어스 전환(롱→숏) 청산: {bias_reason}",
                order_generation_allowed=True,
                market_bias=bias,
            )
        if position.side == "SHORT" and bias == MarketBias.LONG:
            return StrategyDecision(
                symbol=market.symbol,
                action=DecisionAction.EXIT_ALL,
                reason=f"바이어스 전환(숏→롱) 청산: {bias_reason}",
                order_generation_allowed=True,
                market_bias=bias,
            )

        # ── 1차 익절: 진입가 +3% (롱) / -3% (숏) ────────────────────
        active_stages = (
            PositionStage.ENTRY_1,
            PositionStage.ENTRY_2,
            PositionStage.ENTRY_3,
            PositionStage.ENTRY_4,
        )
        if position.stage in active_stages:
            if position.side == "LONG":
                target = position.average_entry * Decimal("1.03")
                if price >= target:
                    return StrategyDecision(
                        symbol=market.symbol,
                        action=DecisionAction.EXIT_PARTIAL,
                        reason=f"1차익절(75%): 현재가 {price} ≥ 목표 {target:.2f}",
                        order_generation_allowed=True,
                        market_bias=bias,
                    )
            else:
                target = position.average_entry * Decimal("0.97")
                if price <= target:
                    return StrategyDecision(
                        symbol=market.symbol,
                        action=DecisionAction.EXIT_PARTIAL,
                        reason=f"1차익절(숏75%): 현재가 {price} ≤ 목표 {target:.2f}",
                        order_generation_allowed=True,
                        market_bias=bias,
                    )

        # ── 러너 트레일링 손절 (RUNNER_25 단계) ─────────────────────
        if position.stage == PositionStage.RUNNER_25:
            if position.side == "LONG":
                trail_stop = position.average_entry * Decimal("1.015")
                if price <= trail_stop:
                    return StrategyDecision(
                        symbol=market.symbol,
                        action=DecisionAction.EXIT_ALL,
                        reason=f"러너 트레일링 손절: {price} ≤ {trail_stop:.2f}",
                        order_generation_allowed=True,
                        market_bias=bias,
                    )
            else:
                trail_stop = position.average_entry * Decimal("0.985")
                if price >= trail_stop:
                    return StrategyDecision(
                        symbol=market.symbol,
                        action=DecisionAction.EXIT_ALL,
                        reason=f"러너 트레일링 손절(숏): {price} ≥ {trail_stop:.2f}",
                        order_generation_allowed=True,
                        market_bias=bias,
                    )

        # ── 분할 추가 매수 (RSI 눌림 회복 조건) ─────────────────────
        add_stages = {
            PositionStage.ENTRY_1,
            PositionStage.ENTRY_2,
            PositionStage.ENTRY_3,
        }
        if position.stage in add_stages:
            if position.side == "LONG" and tech.rsi14_1h < Decimal("42") and tech.rsi14_15m > Decimal("40"):
                return StrategyDecision(
                    symbol=market.symbol,
                    action=DecisionAction.ADD_LONG,
                    reason=f"분할매수: RSI 눌림 회복 1h={tech.rsi14_1h:.1f} → 15m={tech.rsi14_15m:.1f}",
                    order_generation_allowed=True,
                    market_bias=bias,
                )
            if position.side == "SHORT" and tech.rsi14_1h > Decimal("58") and tech.rsi14_15m < Decimal("60"):
                return StrategyDecision(
                    symbol=market.symbol,
                    action=DecisionAction.ADD_SHORT,
                    reason=f"분할매수(숏): RSI 반등 진정 1h={tech.rsi14_1h:.1f} → 15m={tech.rsi14_15m:.1f}",
                    order_generation_allowed=True,
                    market_bias=bias,
                )

        return StrategyDecision(
            symbol=market.symbol,
            action=DecisionAction.HOLD,
            reason=f"포지션 유지 중 | {bias_reason}",
            order_generation_allowed=False,
            market_bias=bias,
        )

    def _check_entry(self, market, tech, bias, bias_reason) -> StrategyDecision:
        """포지션 없을 때 신규 진입 조건 판단."""

        # LONG 진입: EMA 정배열 + RSI 45~65 + 바이어스 LONG
        if bias == MarketBias.LONG:
            ema_ok = tech.ema20_4h > tech.ema50_4h
            rsi_ok = Decimal("45") <= tech.rsi14_1h <= Decimal("65")
            if ema_ok and rsi_ok:
                return StrategyDecision(
                    symbol=market.symbol,
                    action=DecisionAction.ENTER_LONG,
                    reason=(
                        f"롱 진입: EMA 정배열 ({tech.ema20_4h:.0f} > {tech.ema50_4h:.0f})"
                        f" RSI={tech.rsi14_1h:.1f} | {bias_reason}"
                    ),
                    order_generation_allowed=True,
                    market_bias=bias,
                )

        # SHORT 진입: EMA 역배열 + RSI 35~55 + 바이어스 SHORT
        if bias == MarketBias.SHORT:
            ema_ok = tech.ema20_4h < tech.ema50_4h
            rsi_ok = Decimal("35") <= tech.rsi14_1h <= Decimal("55")
            if ema_ok and rsi_ok:
                return StrategyDecision(
                    symbol=market.symbol,
                    action=DecisionAction.ENTER_SHORT,
                    reason=(
                        f"숏 진입: EMA 역배열 ({tech.ema20_4h:.0f} < {tech.ema50_4h:.0f})"
                        f" RSI={tech.rsi14_1h:.1f} | {bias_reason}"
                    ),
                    order_generation_allowed=True,
                    market_bias=bias,
                )

        return StrategyDecision(
            symbol=market.symbol,
            action=DecisionAction.NO_DECISION,
            reason=f"진입 조건 미충족 | {bias_reason}",
            order_generation_allowed=False,
            market_bias=bias,
        )
