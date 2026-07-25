"""
JAMES AI 어시스턴트 — 텔레그램 봇 v2
- qwen2.5:7b 로컬 AI 분석
- 텔레그램 명령으로 직접 진입/청산 실행
"""
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime, timezone

# ── 설정 ──────────────────────────────────────────────────────
BOT_TOKEN  = "8928869687:AAFmzjs61E827lTfG_qe3o-9rY_SJEatkpA"
CHAT_ID    = "1923269844"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "qwen2.5:7b"
JAMES_API  = "http://127.0.0.1:8780/api"

SYSTEM_PROMPT = """당신은 JAMES 스윙 트레이딩 AI 어시스턴트입니다.
규칙:
- 반드시 한국어로만 대답하세요. 영어 절대 사용 금지.
- 암호화폐 선물 트레이딩 전문가입니다
- 간결하고 실용적으로 답변하세요 (5줄 이내)
- 진입 계획은 항상 구체적인 가격과 비율을 제시하세요
- 레버리지 20x, 모의투자 기준으로 분석하세요"""

HELP_TEXT = """🤖 <b>JAMES AI 어시스턴트</b>
━━━━━━━━━━━━━━━━━━━━
<b>📌 직접 실행 명령어</b>
롱 진입 — 현재가 롱 1차 진입
숏 진입 — 현재가 숏 1차 진입
롱 [가격] — 지정가 롱 진입 (예: 롱 63000)
숏 [가격] — 지정가 숏 진입 (예: 숏 65000)
익절 — 75% 부분 익절
청산 — 전량 청산

<b>🔄 종목 변경</b>
BTC — BTCUSDT로 전환
ADA — ADAUSDT로 전환

<b>📊 조회 명령어</b>
/현황 — 현재 시장 + 포지션 조회
/분석 — AI 시장 분석
/계획 — 거미줄 진입 계획 수립
/도움말 — 이 메시지

<b>💬 자유 대화</b>
그냥 메시지 보내면 AI가 답합니다
예: 지금 BTC 어때? / 손절 어디에 놓지?"""


# ── 텔레그램 ─────────────────────────────────────────────────
def tg_send(text: str) -> None:
    try:
        payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"텔레그램 오류: {e}")


# ── JAMES API 호출 ────────────────────────────────────────────
def james_get() -> tuple[str, dict]:
    """현황 조회. (요약문, raw_dict) 반환"""
    try:
        req = urllib.request.Request(f"{JAMES_API}/status", headers={"User-Agent": "JAMES-Bot"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read().decode())
        m = d.get("market", {})
        t = d.get("technical", {})
        s = d.get("sentiment", {})
        p = d.get("position", {})
        a = d.get("accounting", {})
        bias = d.get("bias", "NEUTRAL")
        bias_icon = {"LONG": "🟢 롱", "SHORT": "🔴 숏", "NEUTRAL": "⬜ 중립"}.get(bias, bias)
        side = p.get("side", "-")
        side_str = "🟢 롱" if side == "LONG" else "🔴 숏" if side == "SHORT" else "없음"
        equity = float(a.get("equity", 0))
        rpnl = float(a.get("realized_pnl", 0))
        upnl = float(a.get("unrealized_pnl", 0))

        context = (
            f"종목:{m.get('symbol','?')} 현재가:{m.get('last_price','?')} 바이어스:{bias}\n"
            f"EMA20:{t.get('ema20_4h','-')} EMA50:{t.get('ema50_4h','-')} EMA200:{t.get('ema200_4h','-')}\n"
            f"RSI(1H):{t.get('rsi14_1h','-')} RSI(15M):{t.get('rsi14_15m','-')} ATR:{t.get('atr14_1h','-')}\n"
            f"OI:{s.get('oi_change_pct','-')} 고래L/S:{s.get('top_ls_ratio','-')} "
            f"전체L/S:{s.get('global_ls_ratio','-')} 펀딩:{s.get('funding_rate','-')}\n"
            f"포지션:{side} 단계:{p.get('stage','-')} 수량:{p.get('quantity','0')} "
            f"진입가:{p.get('average_entry','-')}\n"
            f"자산:{equity:.2f} 실현:{rpnl:+.4f} 미실현:{upnl:+.4f}"
        )
        summary = (
            f"📊 <b>JAMES 현황</b>  {datetime.now(timezone.utc).strftime('%H:%M UTC')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"종목: <b>{m.get('symbol','?')}</b>  현재가: <b>{m.get('last_price','?')}</b>\n"
            f"바이어스: {bias_icon}\n\n"
            f"📈 EMA20: {t.get('ema20_4h','-')} / EMA50: {t.get('ema50_4h','-')}\n"
            f"   RSI(1H): {t.get('rsi14_1h','-')} / RSI(15M): {t.get('rsi14_15m','-')}\n\n"
            f"🧠 OI: {s.get('oi_change_pct','-')} / 펀딩: {s.get('funding_rate','-')}\n"
            f"   고래L/S: {s.get('top_ls_ratio','-')} / 전체L/S: {s.get('global_ls_ratio','-')}\n\n"
            f"📌 포지션: {side_str}  단계: {p.get('stage','-')}\n"
            f"💰 자산: <b>{equity:,.2f}</b>  실현: {rpnl:+.4f}  미실현: {upnl:+.4f}"
        )
        return summary, context, d
    except Exception as e:
        return f"⚠️ JAMES 연결 실패: {e}", "", {}


def james_set_symbol(symbol: str) -> str:
    """종목 변경 API 호출"""
    try:
        payload = json.dumps({"symbol": symbol}).encode()
        req = urllib.request.Request(
            f"{JAMES_API}/set_symbol",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read().decode())
        return "성공" if d.get("ok") else d.get("error", "실패")
    except Exception as e:
        return f"오류: {e}"



    """JAMES 프로그램에 직접 실행 명령 전달"""
    try:
        payload = json.dumps({"action": action, "price": price}).encode()
        req = urllib.request.Request(
            f"{JAMES_API}/execute",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read().decode())
        return d.get("message", "완료")
    except Exception as e:
        return f"실행 오류: {e}"


# ── Ollama AI ─────────────────────────────────────────────────
def ask_ai(question: str, context: str = "") -> str:
    prompt = SYSTEM_PROMPT
    if context:
        prompt += f"\n\n[현재 시장 데이터]\n{context}"
    prompt += f"\n\n[질문]\n{question}\n\n[답변 (한국어로만, 5줄 이내)]:"
    try:
        payload = json.dumps({
            "model": MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.5, "num_predict": 300}
        }).encode()
        req = urllib.request.Request(
            OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode()).get("response", "응답 없음").strip()
    except Exception as e:
        return f"AI 오류: {e}"


# ── 메시지 처리 ───────────────────────────────────────────────
def handle(text: str) -> None:
    text = text.strip()
    low = text.lower()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

    # ── 종목 변경 ─────────────────────────────────────────────
    if text.upper() in ("BTC", "BTCUSDT", "BTC 변경", "BTC로변경"):
        msg = james_set_symbol("BTCUSDT")
        tg_send(f"🔄 <b>종목 변경: BTCUSDT</b>\n결과: {msg}\n다음 데이터 수신까지 30초 대기")
        return

    if text.upper() in ("ADA", "ADAUSDT", "ADA 변경", "ADA로변경"):
        msg = james_set_symbol("ADAUSDT")
        tg_send(f"🔄 <b>종목 변경: ADAUSDT</b>\n결과: {msg}\n다음 데이터 수신까지 30초 대기")
        return

    # ── 직접 실행 명령어 ──────────────────────────────────────
    # "롱 진입" or "롱진입"
    if re.match(r'^롱\s*진입$', text):
        _, ctx, d = james_get()
        price = float(d.get("market", {}).get("last_price", 0))
        msg = james_execute("ENTER_LONG", price)
        tg_send(f"🟢 <b>롱 진입 명령 실행</b>\n현재가: {price:,}\n결과: {msg}")
        return

    if re.match(r'^숏\s*진입$', text):
        _, ctx, d = james_get()
        price = float(d.get("market", {}).get("last_price", 0))
        msg = james_execute("ENTER_SHORT", price)
        tg_send(f"🔴 <b>숏 진입 명령 실행</b>\n현재가: {price:,}\n결과: {msg}")
        return

    # "롱 63000" or "롱63000"
    m = re.match(r'^롱\s*([\d,\.]+)$', text)
    if m:
        price = float(m.group(1).replace(",", ""))
        msg = james_execute("ENTER_LONG", price)
        tg_send(f"🟢 <b>롱 지정가 진입</b>\n목표가: {price:,}\n결과: {msg}")
        return

    m = re.match(r'^숏\s*([\d,\.]+)$', text)
    if m:
        price = float(m.group(1).replace(",", ""))
        msg = james_execute("ENTER_SHORT", price)
        tg_send(f"🔴 <b>숏 지정가 진입</b>\n목표가: {price:,}\n결과: {msg}")
        return

    if text in ("익절", "부분익절", "75%익절"):
        msg = james_execute("EXIT_PARTIAL")
        tg_send(f"🟠 <b>75% 익절 실행</b>\n결과: {msg}")
        return

    if text in ("청산", "전량청산", "전체청산"):
        msg = james_execute("EXIT_ALL")
        tg_send(f"✅ <b>전량 청산 실행</b>\n결과: {msg}")
        return

    # ── 조회 명령어 ───────────────────────────────────────────
    if text in ("/현황", "현황"):
        summary, _, _ = james_get()
        tg_send(summary)
        return

    if text in ("/도움말", "/help", "/start", "도움말"):
        tg_send(HELP_TEXT)
        return

    if text in ("/분석", "분석"):
        tg_send("🤔 AI 분석 중...")
        _, ctx, _ = james_get()
        ans = ask_ai("현재 시장 상황을 분석하고 매매 관점을 알려줘. 진입해야 하나 관망해야 하나?", ctx)
        tg_send(f"🤖 <b>AI 분석</b>\n━━━━━━━━━━━━━━━━━━━━\n{ans}")
        return

    if text in ("/계획", "계획"):
        tg_send("📐 진입 계획 수립 중...")
        _, ctx, _ = james_get()
        ans = ask_ai(
            "거미줄 분할 진입 계획을 짜줘. "
            "1~4차 진입가격, 비율, 손절가, 1차익절, 2차익절을 구체적 숫자로.", ctx
        )
        tg_send(f"📐 <b>진입 계획</b>\n━━━━━━━━━━━━━━━━━━━━\n{ans}")
        return

    # ── 자유 대화 → AI ────────────────────────────────────────
    tg_send("🤔 생각 중...")
    _, ctx, _ = james_get()
    ans = ask_ai(text, ctx)
    tg_send(f"🤖 {ans}")


# ── 메인 루프 ─────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  JAMES AI 어시스턴트 v2")
    print(f"  모델: {MODEL}")
    print("=" * 50)

    tg_send(
        "🤖 <b>JAMES AI 어시스턴트 v2 시작</b>\n"
        "텔레그램에서 자유롭게 명령하세요!\n\n"
        "예시:\n"
        "  롱 진입\n"
        "  롱 63000\n"
        "  청산\n"
        "  /도움말"
    )

    offset = 0
    print("대기 중...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url, headers={"User-Agent": "JAMES-Bot"})
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read().decode())
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg:
                    continue
                if str(msg.get("chat", {}).get("id", "")) != CHAT_ID:
                    continue
                text = msg.get("text", "")
                if text:
                    handle(text)
        except KeyboardInterrupt:
            print("종료")
            tg_send("🔴 JAMES AI 종료")
            break
        except Exception as e:
            print(f"오류: {e}")
            import time; time.sleep(5)


if __name__ == "__main__":
    main()
