from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse


HTML = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JAMES 스윙 Lite — 모의투자</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Malgun Gothic',Segoe UI,sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh}

    /* ── 헤더 ── */
    header{padding:12px 20px;background:#1a1d27;border-bottom:1px solid #2d3148;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    header h1{font-size:16px;font-weight:700;color:#fff;white-space:nowrap}
    .badge{background:#16a34a;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px}
    .hdr-right{margin-left:auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap}

    /* ── 종목 선택 버튼 ── */
    .sym-btn{padding:5px 14px;border-radius:6px;border:1px solid #3b82f6;background:transparent;color:#93c5fd;font-size:13px;cursor:pointer;font-family:inherit;transition:all .2s}
    .sym-btn.active{background:#1e3a5f;color:#fff;border-color:#60a5fa}
    .sym-btn:hover{background:#1e3a5f}
    #sym-status{font-size:12px;color:#94a3b8}

    /* ── 그리드 ── */
    main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;padding:12px}
    .card{background:#1a1d27;border:1px solid #2d3148;border-radius:10px;padding:14px}
    .card h2{font-size:12px;color:#94a3b8;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}
    dl{display:grid;grid-template-columns:120px 1fr;gap:6px;font-size:13px}
    dt{color:#64748b} dd{font-weight:600;word-break:break-word}

    /* ── 바이어스 ── */
    .bias-card{grid-column:1/-1}
    .bias-box{display:flex;align-items:center;justify-content:center;padding:16px;border-radius:8px;font-size:22px;font-weight:800;gap:10px}
    .bias-LONG{background:#052e16;color:#4ade80;border:2px solid #16a34a}
    .bias-SHORT{background:#2d0a0a;color:#f87171;border:2px solid #dc2626}
    .bias-NEUTRAL{background:#1c1917;color:#94a3b8;border:2px solid #44403c}
    .bias-label{font-size:12px;color:#94a3b8;margin-top:5px;text-align:center}

    /* ── 액션 색상 ── */
    .action-ENTER_LONG{color:#4ade80} .action-ENTER_SHORT{color:#f87171}
    .action-ADD_LONG,.action-ADD_SHORT{color:#facc15}
    .action-EXIT_PARTIAL{color:#fb923c} .action-EXIT_ALL{color:#f87171}
    .action-HOLD{color:#60a5fa} .action-NO_DECISION{color:#64748b}
    .pos{color:#4ade80} .neg{color:#f87171} .neu{color:#94a3b8}

    /* ── 포지션 단계 ── */
    .stage-tag{display:inline-block;padding:1px 8px;border-radius:4px;font-size:12px;background:#334155;color:#e2e8f0}
    .stage-ENTRY_1,.stage-ENTRY_2,.stage-ENTRY_3,.stage-ENTRY_4{background:#1e3a5f;color:#93c5fd}
    .stage-RUNNER_25{background:#3b1f00;color:#fdba74}
    .stage-CLOSED{background:#1f2937;color:#6b7280}

    details{grid-column:1/-1;background:#1a1d27;border:1px solid #2d3148;border-radius:10px;padding:12px}
    summary{cursor:pointer;color:#64748b;font-size:12px;user-select:none}
    pre{white-space:pre-wrap;font-size:11px;color:#94a3b8;margin-top:8px;line-height:1.5}
    .error-box{background:#2d0a0a;border:1px solid #7f1d1d;border-radius:6px;padding:8px;font-size:12px;color:#fca5a5;word-break:break-word}
    .ok-box{color:#4ade80;font-size:12px}
    .ts{font-size:10px;color:#475569;text-align:right;padding:6px 12px 2px}
    .divider{grid-column:1/-1;border:none;border-top:1px solid #2d3148}

    /* ── 알림 토스트 ── */
    #toast{position:fixed;top:16px;left:50%;transform:translateX(-50%);background:#1e40af;color:#fff;padding:10px 22px;border-radius:8px;font-size:13px;display:none;z-index:999;box-shadow:0 4px 12px #0006}
  </style>
</head>
<body>
<div id="toast"></div>
<header>
  <h1>⚡ JAMES 스윙 Lite</h1>
  <span class="badge">모의투자 전용</span>
  <div class="hdr-right">
    <span style="font-size:12px;color:#64748b">종목:</span>
    <button class="sym-btn active" id="btn-btc" onclick="changeSym('BTCUSDT')">BTC/USDT</button>
    <button class="sym-btn" id="btn-ada" onclick="changeSym('ADAUSDT')">ADA/USDT</button>
    <span id="sym-status"></span>
    <span id="hdr-status" style="font-size:12px;color:#94a3b8"></span>
  </div>
</header>

<main>
  <!-- 시장 바이어스 -->
  <div class="card bias-card">
    <h2>📊 시장 바이어스</h2>
    <div id="bias-box" class="bias-box bias-NEUTRAL">━ 중립 분석 중...</div>
    <div id="bias-reason" class="bias-label">데이터 수집 중...</div>
  </div>

  <!-- 전략 판단 -->
  <div class="card">
    <h2>🎯 전략 판단</h2>
    <dl>
      <dt>판단 결과</dt><dd><span id="action" class="action-NO_DECISION">대기 중</span></dd>
      <dt>판단 이유</dt><dd id="reason" style="font-size:11px;color:#94a3b8;line-height:1.4">-</dd>
      <dt>주문 허용</dt><dd id="order-allowed">-</dd>
    </dl>
  </div>

  <!-- 현재 포지션 -->
  <div class="card">
    <h2>📌 현재 포지션</h2>
    <dl>
      <dt>종목</dt><dd id="pos-symbol">-</dd>
      <dt>방향</dt><dd id="pos-side">-</dd>
      <dt>진입 단계</dt><dd><span id="pos-stage" class="stage-tag">-</span></dd>
      <dt>수량</dt><dd id="pos-qty">0</dd>
      <dt>평균 진입가</dt><dd id="pos-entry">-</dd>
    </dl>
  </div>

  <!-- 기술 지표 -->
  <div class="card">
    <h2>📈 기술 지표</h2>
    <dl>
      <dt>EMA20 (4H)</dt><dd id="ema20-4h">-</dd>
      <dt>EMA50 (4H)</dt><dd id="ema50-4h">-</dd>
      <dt>EMA200 (4H)</dt><dd id="ema200-4h">-</dd>
      <dt>RSI14 (1H)</dt><dd id="rsi-1h">-</dd>
      <dt>RSI14 (15M)</dt><dd id="rsi-15m">-</dd>
      <dt>ATR14 (1H)</dt><dd id="atr-1h">-</dd>
    </dl>
  </div>

  <!-- 감성 지표 -->
  <div class="card">
    <h2>🧠 감성 지표</h2>
    <dl>
      <dt>OI 변화율</dt><dd id="oi-chg">-</dd>
      <dt>고래 L/S</dt><dd id="top-ls">-</dd>
      <dt>전체 L/S</dt><dd id="global-ls">-</dd>
      <dt>Taker 매수비율</dt><dd id="taker">-</dd>
      <dt>펀딩비</dt><dd id="funding">-</dd>
    </dl>
  </div>

  <!-- 시장 데이터 -->
  <div class="card">
    <h2>💹 시장 데이터</h2>
    <dl>
      <dt>현재가</dt><dd id="price" style="font-size:18px;font-weight:800;color:#fff">-</dd>
      <dt>타임프레임</dt><dd id="frames">-</dd>
      <dt>데이터 상태</dt><dd id="stale-status">-</dd>
    </dl>
  </div>

  <!-- 손익 -->
  <div class="card">
    <h2>💰 손익 현황</h2>
    <dl>
      <dt>순자산 (모의)</dt><dd id="equity" style="font-size:15px;font-weight:800">-</dd>
      <dt>미실현 손익</dt><dd id="unrealized-pnl">-</dd>
      <dt>실현 손익</dt><dd id="realized-pnl">-</dd>
      <dt>사용 증거금</dt><dd id="margin">-</dd>
      <dt>누적 수수료</dt><dd id="fees">-</dd>
    </dl>
  </div>

  <!-- 리스크 -->
  <div class="card">
    <h2>🛡️ 리스크 & 엔진</h2>
    <dl>
      <dt>레버리지</dt><dd id="leverage">-</dd>
      <dt>구조적 손절가</dt><dd id="stop">-</dd>
      <dt>주문 건수</dt><dd id="order-count">0건</dd>
      <dt>엔진 상태</dt><dd id="engine-status">-</dd>
    </dl>
  </div>

  <!-- 오류 -->
  <div class="card">
    <h2>⚠️ 오류 및 차단</h2>
    <div id="errors-box" class="ok-box">✅ 정상</div>
    <div id="blocks-box" style="margin-top:6px"></div>
  </div>

  <hr class="divider">
  <details>
    <summary>🔧 개발자 상세 (JSON)</summary>
    <pre id="raw"></pre>
  </details>
</main>
<div class="ts" id="updated-at">마지막 갱신: -</div>

<script>
const BIAS_ICON  = {LONG:'▲ 롱 (상승)', SHORT:'▼ 숏 (하락)', NEUTRAL:'━ 중립'};
const ACTION_KO  = {
  ENTER_LONG:'🟢 롱 진입', ENTER_SHORT:'🔴 숏 진입',
  ADD_LONG:'🟡 롱 분할매수', ADD_SHORT:'🟡 숏 분할매수',
  EXIT_PARTIAL:'🟠 75% 익절', EXIT_ALL:'🔴 전량 청산',
  HOLD:'🔵 포지션 유지', NO_DECISION:'⬜ 판단 대기',
};
const STAGE_KO = {
  NONE:'없음', ENTRY_1:'1차 진입', ENTRY_2:'2차 분할',
  ENTRY_3:'3차 분할', ENTRY_4:'4차 분할',
  RUNNER_25:'러너 25%', CLOSED:'청산 완료',
};

function showToast(msg, ms=2500){
  const t=document.getElementById('toast');
  t.textContent=msg; t.style.display='block';
  setTimeout(()=>t.style.display='none', ms);
}

async function changeSym(sym){
  document.getElementById('sym-status').textContent='변경 중...';
  try{
    const r=await fetch('/api/set_symbol',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol:sym})});
    const d=await r.json();
    if(d.ok){
      document.getElementById('btn-btc').classList.toggle('active', sym==='BTCUSDT');
      document.getElementById('btn-ada').classList.toggle('active', sym==='ADAUSDT');
      showToast('✅ 종목 변경: '+sym);
      document.getElementById('sym-status').textContent='';
    }
  }catch(e){
    document.getElementById('sym-status').textContent='오류';
  }
}

function pnlClass(v){const n=parseFloat(v);return isNaN(n)||n===0?'neu':n>0?'pos':'neg'}

async function tick(){
  try{
    const r=await fetch('/api/status');
    if(!r.ok) return;
    const d=await r.json();

    document.getElementById('hdr-status').textContent=d.health?.status||'';
    const curSym = d.identity?.symbol||'BTCUSDT';
    document.getElementById('btn-btc').classList.toggle('active', curSym==='BTCUSDT');
    document.getElementById('btn-ada').classList.toggle('active', curSym==='ADAUSDT');

    // 바이어스
    const bias=d.bias||'NEUTRAL';
    const bb=document.getElementById('bias-box');
    bb.className='bias-box bias-'+bias;
    bb.textContent=BIAS_ICON[bias]||bias;
    document.getElementById('bias-reason').textContent=d.decision?.reason||'-';

    // 판단
    const action=d.decision?.action||'NO_DECISION';
    const ae=document.getElementById('action');
    ae.textContent=ACTION_KO[action]||action; ae.className='action-'+action;
    document.getElementById('reason').textContent=d.decision?.reason||'-';
    document.getElementById('order-allowed').textContent=d.decision?.order_generation_allowed?'✅ 허용':'❌ 차단';

    // 포지션
    const pos=d.position||{};
    document.getElementById('pos-symbol').textContent=pos.symbol||curSym;
    const side=pos.side||'-';
    const sideEl=document.getElementById('pos-side');
    sideEl.textContent=side==='LONG'?'🟢 롱':side==='SHORT'?'🔴 숏':'-';
    sideEl.className=side==='LONG'?'pos':side==='SHORT'?'neg':'neu';
    const stg=pos.stage||'NONE';
    const stgEl=document.getElementById('pos-stage');
    stgEl.textContent=STAGE_KO[stg]||stg; stgEl.className='stage-tag stage-'+stg;
    document.getElementById('pos-qty').textContent=pos.quantity||'0';
    document.getElementById('pos-entry').textContent=pos.average_entry||'-';

    // 기술 지표
    const tech=d.technical||{};
    document.getElementById('ema20-4h').textContent=tech.ema20_4h||'-';
    document.getElementById('ema50-4h').textContent=tech.ema50_4h||'-';
    document.getElementById('ema200-4h').textContent=tech.ema200_4h||'-';
    const rsi1=parseFloat(tech.rsi14_1h);
    const r1El=document.getElementById('rsi-1h');
    r1El.textContent=tech.rsi14_1h||'-';
    r1El.className=!isNaN(rsi1)&&rsi1>70?'neg':!isNaN(rsi1)&&rsi1<30?'pos':'';
    document.getElementById('rsi-15m').textContent=tech.rsi14_15m||'-';
    document.getElementById('atr-1h').textContent=tech.atr14_1h||'-';

    // 감성 지표
    const sent=d.sentiment||{};
    const oiV=parseFloat(sent.oi_change_pct);
    const oiEl=document.getElementById('oi-chg');
    oiEl.textContent=sent.oi_change_pct||'-';
    oiEl.className=!isNaN(oiV)&&oiV>0?'pos':!isNaN(oiV)&&oiV<0?'neg':'neu';
    const tlV=parseFloat(sent.top_ls_ratio);
    const tlEl=document.getElementById('top-ls');
    tlEl.textContent=sent.top_ls_ratio||'-';
    tlEl.className=!isNaN(tlV)&&tlV>1.2?'pos':!isNaN(tlV)&&tlV<0.8?'neg':'neu';
    document.getElementById('global-ls').textContent=sent.global_ls_ratio||'-';
    const tkV=parseFloat(sent.taker_buy_ratio);
    const tkEl=document.getElementById('taker');
    tkEl.textContent=sent.taker_buy_ratio||'-';
    tkEl.className=!isNaN(tkV)&&tkV>0.55?'pos':!isNaN(tkV)&&tkV<0.45?'neg':'neu';
    const fV=parseFloat(sent.funding_rate);
    const fEl=document.getElementById('funding');
    fEl.textContent=sent.funding_rate||'-';
    fEl.className=!isNaN(fV)&&fV>0.0005?'neg':!isNaN(fV)&&fV<-0.0001?'pos':'neu';

    // 시장
    document.getElementById('price').textContent=d.market?.last_price||'-';
    document.getElementById('frames').textContent=(d.market?.timeframes||[]).join(' / ')||'-';
    const stale=d.market?.stale;
    const stEl=document.getElementById('stale-status');
    stEl.textContent=stale?'⚠️ 지연':'✅ 정상'; stEl.className=stale?'neg':'pos';

    // 손익
    const acc=d.accounting||{};
    const eqEl=document.getElementById('equity');
    eqEl.textContent=acc.equity?parseFloat(acc.equity).toLocaleString('ko-KR',{minimumFractionDigits:2,maximumFractionDigits:2})+' USDT':'-';
    eqEl.className=pnlClass(acc.equity);
    const upEl=document.getElementById('unrealized-pnl');
    upEl.textContent=acc.unrealized_pnl?parseFloat(acc.unrealized_pnl).toFixed(4)+' USDT':'-';
    upEl.className=pnlClass(acc.unrealized_pnl);
    const rpEl=document.getElementById('realized-pnl');
    rpEl.textContent=acc.realized_pnl?parseFloat(acc.realized_pnl).toFixed(4)+' USDT':'-';
    rpEl.className=pnlClass(acc.realized_pnl);
    document.getElementById('margin').textContent=acc.margin_used?parseFloat(acc.margin_used).toFixed(4)+' USDT':'-';
    document.getElementById('fees').textContent=acc.fees_paid?parseFloat(acc.fees_paid).toFixed(4)+' USDT':'-';

    // 리스크
    const risk=d.risk||{};
    document.getElementById('leverage').textContent=risk.leverage?risk.leverage+'x':'-';
    document.getElementById('stop').textContent=risk.structural_stop||'-';
    document.getElementById('order-count').textContent=(d.health?.order_count||0)+'건';
    document.getElementById('engine-status').textContent=d.health?.status||'-';

    // 오류
    const errs=d.health?.errors||[];
    const errBox=document.getElementById('errors-box');
    if(errs.length){errBox.className='error-box';errBox.textContent=errs.slice(-3).join(' | ');}
    else{errBox.className='ok-box';errBox.textContent='✅ 정상';}
    const blocks=risk.hard_blocks||[];
    const blkBox=document.getElementById('blocks-box');
    blkBox.innerHTML=blocks.map(b=>`<span style="background:#7f1d1d;color:#fca5a5;padding:2px 7px;border-radius:4px;font-size:11px;margin:2px;display:inline-block">${b}</span>`).join('');

    document.getElementById('raw').textContent=JSON.stringify(d,null,2);
    document.getElementById('updated-at').textContent='마지막 갱신: '+new Date().toLocaleTimeString('ko-KR');
  }catch(e){
    document.getElementById('hdr-status').textContent='서버 연결 대기중...';
  }
}
setInterval(tick,2000); tick();
</script>
</body></html>"""


def create_dashboard(supervisor) -> "FastAPI":
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel

    app = FastAPI(title="JAMES 스윙 Lite")

    class SymbolRequest(BaseModel):
        symbol: str

    class ExecuteRequest(BaseModel):
        action: str
        price: float = 0.0

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return HTML

    @app.get("/api/status")
    async def status() -> dict:
        return supervisor.snapshot()

    @app.post("/api/set_symbol")
    async def set_symbol(req: SymbolRequest):
        """실시간 종목 전환 API"""
        sym = req.symbol.upper()
        allowed = {"BTCUSDT", "ADAUSDT"}
        if sym not in allowed:
            return JSONResponse({"ok": False, "error": f"지원 종목: {allowed}"}, status_code=400)
        try:
            supervisor.change_symbol(sym)
            return {"ok": True, "symbol": sym}
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    @app.post("/api/execute")
    async def execute_order(req: ExecuteRequest):
        """텔레그램 명령으로 직접 진입/청산 실행"""
        from .domain import DecisionAction, MarketBias, StrategyDecision
        from decimal import Decimal
        action_map = {
            "ENTER_LONG":   DecisionAction.ENTER_LONG,
            "ENTER_SHORT":  DecisionAction.ENTER_SHORT,
            "EXIT_PARTIAL": DecisionAction.EXIT_PARTIAL,
            "EXIT_ALL":     DecisionAction.EXIT_ALL,
        }
        action = action_map.get(req.action.upper())
        if not action:
            return JSONResponse({"ok": False, "error": f"알 수 없는 액션: {req.action}"}, status_code=400)
        try:
            # 지정가 있으면 시장가 오버라이드
            from .domain import MarketSnapshot
            import copy
            market = copy.copy(supervisor.latest_market)
            if req.price > 0:
                market = MarketSnapshot(
                    market.symbol, Decimal(str(req.price)),
                    market.candles, market.timestamp,
                    market.stale, market.reason,
                    market.technical, market.sentiment,
                )
            decision = StrategyDecision(
                symbol=market.symbol,
                action=action,
                reason=f"텔레그램 수동 명령: {req.action}",
                order_generation_allowed=True,
                market_bias=MarketBias.NEUTRAL,
            )
            result = supervisor.execution.execute(
                decision, supervisor.positions,
                supervisor.latest_accounting, market,
            )
            if result.accepted:
                supervisor.accounting.apply_fill(result.pnl, result.fee)
                supervisor.db.save_trade_history(supervisor.config.symbol, result)
                return {
                    "ok": True,
                    "message": result.reason,
                    "fill_price": str(result.fill_price),
                    "quantity": str(result.quantity),
                    "pnl": str(result.pnl),
                    "fee": str(result.fee),
                }
            else:
                return JSONResponse({"ok": False, "error": result.reason}, status_code=400)
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    return app
