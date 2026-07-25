from __future__ import annotations

from decimal import Decimal


def ema(prices: list[Decimal], period: int) -> Decimal:
    """EMA 계산. prices는 시간순(오래된→최신). 최신값 반환."""
    if not prices:
        return Decimal("0")
    if len(prices) < period:
        return prices[-1]
    k = Decimal(2) / Decimal(period + 1)
    result = sum(prices[:period]) / Decimal(period)
    for price in prices[period:]:
        result = price * k + result * (1 - k)
    return result


def rsi(prices: list[Decimal], period: int = 14) -> Decimal:
    """RSI 계산 (Wilder's smoothing). prices는 종가 리스트(오래된→최신)."""
    if len(prices) < period + 1:
        return Decimal("50")
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(c, Decimal("0")) for c in changes]
    losses = [abs(min(c, Decimal("0"))) for c in changes]
    avg_gain = sum(gains[:period]) / Decimal(period)
    avg_loss = sum(losses[:period]) / Decimal(period)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * Decimal(period - 1) + gains[i]) / Decimal(period)
        avg_loss = (avg_loss * Decimal(period - 1) + losses[i]) / Decimal(period)
    if avg_loss == Decimal("0"):
        return Decimal("100")
    rs = avg_gain / avg_loss
    return Decimal("100") - (Decimal("100") / (1 + rs))


def atr(highs: list[Decimal], lows: list[Decimal], closes: list[Decimal], period: int = 14) -> Decimal:
    """ATR 계산."""
    if len(highs) < 2:
        return Decimal("0")
    trs = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return trs[-1] if trs else Decimal("0")
    avg = sum(trs[:period]) / Decimal(period)
    for tr in trs[period:]:
        avg = (avg * Decimal(period - 1) + tr) / Decimal(period)
    return avg
