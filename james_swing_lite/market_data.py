from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import aiohttp

from .config import LiteConfig
from .domain import Candle, MarketSnapshot, SentimentData, TechnicalData
from .indicators import atr, ema, rsi


class BinancePublicMarketData:
    """바이낸스 공개 REST API 데이터 수집기 (기술지표 + 감성지표)."""

    BASE = "https://fapi.binance.com"
    FUTURES_DATA = "https://fapi.binance.com/futures/data"

    def __init__(self, config: LiteConfig) -> None:
        self.config = config
        self.latest: MarketSnapshot | None = None

    async def refresh_once(self) -> MarketSnapshot:
        symbol = self.config.symbol
        try:
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # 캔들 수집 (EMA200 계산을 위해 210개)
                candles_4h = await self._klines(session, symbol, "4h", 210)
                candles_1h = await self._klines(session, symbol, "1h", 210)
                candles_15m = await self._klines(session, symbol, "15m", 50)

                # 감성 지표 수집
                sentiment = await self._fetch_sentiment(session, symbol)

                # 기술 지표 계산
                technical = self._calc_technical(candles_4h, candles_1h, candles_15m)

                # 현재가 (15m 최신 종가)
                last_price = candles_15m[-1].close if candles_15m else Decimal("0")

                # Candle dict (최신 1개씩)
                candle_dict: dict[str, Candle] = {}
                if candles_4h:
                    candle_dict["4h"] = candles_4h[-1]
                if candles_1h:
                    candle_dict["1h"] = candles_1h[-1]
                if candles_15m:
                    candle_dict["15m"] = candles_15m[-1]

                self.latest = MarketSnapshot(
                    symbol=symbol,
                    last_price=last_price,
                    candles=candle_dict,
                    updated_at=datetime.now(timezone.utc),
                    stale=False,
                    sentiment=sentiment,
                    technical=technical,
                )
        except Exception as exc:
            err = f"데이터수집오류: {exc}"
            if self.latest is None:
                self.latest = MarketSnapshot(
                    symbol, Decimal("0"), {}, datetime.now(timezone.utc), True, err
                )
            else:
                # 이전 데이터 유지, stale 표시
                self.latest = MarketSnapshot(
                    symbol=self.latest.symbol,
                    last_price=self.latest.last_price,
                    candles=self.latest.candles,
                    updated_at=self.latest.updated_at,
                    stale=True,
                    reason=err,
                    sentiment=self.latest.sentiment,
                    technical=self.latest.technical,
                )
        return self.latest

    async def _klines(
        self, session: aiohttp.ClientSession, symbol: str, interval: str, limit: int
    ) -> list[Candle]:
        try:
            data = await self._get(
                session,
                f"{self.BASE}/fapi/v1/klines",
                {"symbol": symbol, "interval": interval, "limit": limit},
            )
            return [
                Candle(
                    symbol=symbol,
                    timeframe=interval,
                    open_time_ms=int(r[0]),
                    open=Decimal(str(r[1])),
                    high=Decimal(str(r[2])),
                    low=Decimal(str(r[3])),
                    close=Decimal(str(r[4])),
                    volume=Decimal(str(r[5])),
                )
                for r in (data or [])
            ]
        except Exception:
            return []

    async def _fetch_sentiment(
        self, session: aiohttp.ClientSession, symbol: str
    ) -> SentimentData:
        """감성 지표 수집. 개별 API 실패 시 기본값으로 처리."""
        vals: dict[str, Decimal] = {
            "oi_change_pct": Decimal("0"),
            "top_ls_ratio": Decimal("1"),
            "global_ls_ratio": Decimal("1"),
            "taker_buy_ratio": Decimal("0.5"),
            "funding_rate": Decimal("0"),
            "oi_volume_ratio": Decimal("0"),
        }

        # OI 히스토리 (변화율 계산)
        try:
            oi_data = await self._get(
                session,
                f"{self.FUTURES_DATA}/openInterestHist",
                {"symbol": symbol, "period": "15m", "limit": 5},
            )
            if oi_data and len(oi_data) >= 2:
                oi_new = Decimal(str(oi_data[-1]["sumOpenInterest"]))
                oi_old = Decimal(str(oi_data[0]["sumOpenInterest"]))
                if oi_old > 0:
                    vals["oi_change_pct"] = (
                        (oi_new - oi_old) / oi_old * 100
                    ).quantize(Decimal("0.01"))
                oi_usd = Decimal(str(oi_data[-1].get("sumOpenInterestValue", "0")))
                if oi_usd > 0:
                    vals["oi_volume_ratio"] = oi_usd
        except Exception:
            pass

        # Top Trader L/S 비율
        try:
            top_data = await self._get(
                session,
                f"{self.FUTURES_DATA}/topLongShortPositionRatio",
                {"symbol": symbol, "period": "15m", "limit": 1},
            )
            if top_data:
                vals["top_ls_ratio"] = Decimal(str(top_data[-1]["longShortRatio"]))
        except Exception:
            pass

        # Global L/S 비율
        try:
            global_data = await self._get(
                session,
                f"{self.FUTURES_DATA}/globalLongShortAccountRatio",
                {"symbol": symbol, "period": "15m", "limit": 1},
            )
            if global_data:
                vals["global_ls_ratio"] = Decimal(str(global_data[-1]["longShortRatio"]))
        except Exception:
            pass

        # Taker 매수/매도 볼륨
        try:
            taker_data = await self._get(
                session,
                f"{self.FUTURES_DATA}/takerbBuySellVol",
                {"symbol": symbol, "period": "15m", "limit": 1},
            )
            if taker_data:
                ratio = Decimal(str(taker_data[-1]["buySellRatio"]))
                # buySellRatio = buy/sell, 매수비율 = ratio/(ratio+1)
                vals["taker_buy_ratio"] = (ratio / (ratio + 1)).quantize(Decimal("0.0001"))
        except Exception:
            pass

        # 펀딩비
        try:
            funding_data = await self._get(
                session,
                f"{self.BASE}/fapi/v1/fundingRate",
                {"symbol": symbol, "limit": 1},
            )
            if funding_data:
                vals["funding_rate"] = Decimal(str(funding_data[-1]["fundingRate"]))
        except Exception:
            pass

        return SentimentData(**vals)

    def _calc_technical(
        self,
        c4h: list[Candle],
        c1h: list[Candle],
        c15m: list[Candle],
    ) -> TechnicalData | None:
        if not c4h or not c1h or not c15m:
            return None
        try:
            closes_4h = [c.close for c in c4h]
            closes_1h = [c.close for c in c1h]
            closes_15m = [c.close for c in c15m]
            highs_1h = [c.high for c in c1h]
            lows_1h = [c.low for c in c1h]
            return TechnicalData(
                ema20_4h=ema(closes_4h, 20),
                ema50_4h=ema(closes_4h, 50),
                ema200_4h=ema(closes_4h, 200),
                ema20_1h=ema(closes_1h, 20),
                ema50_1h=ema(closes_1h, 50),
                rsi14_1h=rsi(closes_1h, 14),
                rsi14_15m=rsi(closes_15m, 14),
                atr14_1h=atr(highs_1h, lows_1h, closes_1h, 14),
                close_15m=closes_15m[-1],
                high_15m=c15m[-1].high,
                low_15m=c15m[-1].low,
            )
        except Exception:
            return None

    async def _get(
        self, session: aiohttp.ClientSession, url: str, params: dict
    ) -> Any:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def loop(self, interval_seconds: float = 30.0) -> None:
        while True:
            await self.refresh_once()
            await asyncio.sleep(interval_seconds)
