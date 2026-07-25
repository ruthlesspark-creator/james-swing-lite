"""
JAMES Swing Lite — Telegram 알림 모듈
진입 신호, 익절, 손절, 시장 리포트를 Telegram으로 발송합니다.
"""
from __future__ import annotations

import asyncio
import urllib.request
import json
from decimal import Decimal
from datetime import datetime, timezone


BOT_TOKEN = "8928869687:AAFmzjs61E827lTfG_qe3o-9rY_SJEatkpA"
CHAT_ID   = "1923269844"
API_BASE  = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _send(text: str) -> None:
    """동기 전송."""
    try:
        payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"{API_BASE}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


async def send(text: str) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send, text)


async def notify_startup(symbol: str) -> None:
    await send(
        f"🚀 <b>JAMES 스윙 Lite 시작</b>\n"
        f"종목: <b>{symbol}</b>\n"
        f"모드: 모의투자 전용\n"
        f"시각: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )


async def notify_signal(action: str, symbol: str, price: Decimal,
                        reason: str, allocs: tuple) -> None:
    icons = {
        "ENTER_LONG":   "🟢 롱 진입 신호",
        "ENTER_SHORT":  "🔴 숏 진입 신호",
        "ADD_LONG":     "🟡 롱 분할매수",
        "ADD_SHORT":    "🟡 숏 분할매수",
        "EXIT_PARTIAL": "🟠 75% 익절 신호",
        "EXIT_ALL":     "🔴 전량 청산 신호",
    }
    label = icons.get(action, action)

    plan = ""
    if action == "ENTER_LONG" and allocs:
        pts = [price, price*Decimal("0.992"), price*Decimal("0.984"), price*Decimal("0.976")]
        lines = [f"  {s}차: {p:,.1f} ({float(a)*100:.0f}%)"
                 for s, p, a in zip(range(1,5), pts, allocs)]
        stop = price * Decimal("0.95")
        tp1  = price * Decimal("1.03")
        tp2  = price * Decimal("1.05")
        plan = ("\n📌 <b>거미줄 진입 계획:</b>\n" + "\n".join(lines) +
                f"\n\n🛡 손절: {stop:,.1f}\n🎯 1차익절: {tp1:,.1f}\n🎯 2차익절: {tp2:,.1f}")
    elif action == "ENTER_SHORT" and allocs:
        pts = [price, price*Decimal("1.008"), price*Decimal("1.016"), price*Decimal("1.024")]
        lines = [f"  {s}차: {p:,.1f} ({float(a)*100:.0f}%)"
                 for s, p, a in zip(range(1,5), pts, allocs)]
        stop = price * Decimal("1.05")
        tp1  = price * Decimal("0.97")
        tp2  = price * Decimal("0.95")
        plan = ("\n📌 <b>거미줄 진입 계획:</b>\n" + "\n".join(lines) +
                f"\n\n🛡 손절: {stop:,.1f}\n🎯 1차익절: {tp1:,.1f}\n🎯 2차익절: {tp2:,.1f}")

    await send(
        f"{'━'*22}\n⚡ <b>JAMES 스윙 Lite</b>\n{'━'*22}\n"
        f"{label}\n\n"
        f"종목: <b>{symbol}</b>\n"
        f"현재가: <b>{price:,}</b> USDT\n"
        f"근거: {reason}{plan}"
    )


async def notify_fill(action: str, symbol: str, fill_price: Decimal,
                      qty: Decimal, pnl: Decimal, fee: Decimal) -> None:
    pnl_str = f"+{pnl:.4f}" if pnl >= 0 else f"{pnl:.4f}"
    icons = {"ENTER_LONG":"🟢","ENTER_SHORT":"🔴",
             "ADD_LONG":"🟡","ADD_SHORT":"🟡",
             "EXIT_PARTIAL":"🟠","EXIT_ALL":"✅"}
    icon = icons.get(action, "📋")
    await send(
        f"{icon} <b>체결 완료</b>\n"
        f"종목: {symbol} | 체결가: {fill_price:,}\n"
        f"수량: {qty:.4f} | 수수료: {fee:.4f}\n"
        f"손익: <b>{pnl_str} USDT</b>"
    )


async def notify_report(snapshot: dict) -> None:
    m = snapshot.get("market", {})
    t = snapshot.get("technical", {})
    s = snapshot.get("sentiment", {})
    p = snapshot.get("position", {})
    a = snapshot.get("accounting", {})
    bias = snapshot.get("bias", "NEUTRAL")
    bias_icon = {"LONG":"🟢 롱","SHORT":"🔴 숏","NEUTRAL":"⬜ 중립"}.get(bias, bias)
    side = p.get("side", "-")
    side_str = "🟢 롱" if side=="LONG" else "🔴 숏" if side=="SHORT" else "없음"
    equity = float(a.get("equity", 0))
    rpnl   = float(a.get("realized_pnl", 0))
    upnl   = float(a.get("unrealized_pnl", 0))
    await send(
        f"📊 <b>JAMES 30분 리포트</b>  {datetime.now(timezone.utc).strftime('%H:%M UTC')}\n"
        f"{'━'*22}\n"
        f"종목: <b>{m.get('symbol','?')}</b>  현재가: <b>{m.get('last_price','?')}</b>\n"
        f"바이어스: {bias_icon}\n\n"
        f"📈 EMA20: {t.get('ema20_4h','-')} / EMA50: {t.get('ema50_4h','-')}\n"
        f"   RSI(1H): {t.get('rsi14_1h','-')} / RSI(15M): {t.get('rsi14_15m','-')}\n\n"
        f"🧠 OI: {s.get('oi_change_pct','-')} | 펀딩: {s.get('funding_rate','-')}\n"
        f"   고래L/S: {s.get('top_ls_ratio','-')} | 전체L/S: {s.get('global_ls_ratio','-')}\n\n"
        f"📌 포지션: {side_str}  단계: {p.get('stage','-')}\n"
        f"💰 자산: <b>{equity:,.2f}</b> | 실현: {rpnl:+.4f} | 미실현: {upnl:+.4f}"
    )


async def notify_error(error: str) -> None:
    await send(f"⚠️ <b>JAMES 오류</b>\n{error}")
