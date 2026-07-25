from __future__ import annotations

from decimal import Decimal

from .domain import MarketBias, SentimentData


class SentimentAnalyzer:
    """감성 지표 기반 시장 바이어스 판단 (점수제)."""

    THRESHOLD = 3  # 바이어스 확정에 필요한 최소 점수

    def analyze(self, data: SentimentData) -> tuple[MarketBias, str]:
        long_score = 0
        short_score = 0
        reasons: list[str] = []

        # 1. OI 변화율: 증가=추세강화 신호
        if data.oi_change_pct > Decimal("1.0"):
            long_score += 1
            reasons.append(f"OI증가+{data.oi_change_pct:.2f}%")
        elif data.oi_change_pct < Decimal("-1.0"):
            short_score += 1
            reasons.append(f"OI감소{data.oi_change_pct:.2f}%")

        # 2. Top Trader L/S 비율 (고래 방향)
        if data.top_ls_ratio > Decimal("1.2"):
            long_score += 1
            reasons.append(f"고래롱{data.top_ls_ratio:.2f}")
        elif data.top_ls_ratio < Decimal("0.8"):
            short_score += 1
            reasons.append(f"고래숏{data.top_ls_ratio:.2f}")

        # 3. Global L/S 비율 (개미 역방향 신호)
        if data.global_ls_ratio < Decimal("0.9"):
            long_score += 1
            reasons.append(f"개미과매도→롱{data.global_ls_ratio:.2f}")
        elif data.global_ls_ratio > Decimal("1.2"):
            short_score += 1
            reasons.append(f"개미과매수→숏{data.global_ls_ratio:.2f}")

        # 4. Taker 매수/매도 압력
        if data.taker_buy_ratio > Decimal("0.55"):
            long_score += 1
            reasons.append(f"매수압력{data.taker_buy_ratio:.2f}")
        elif data.taker_buy_ratio < Decimal("0.45"):
            short_score += 1
            reasons.append(f"매도압력{data.taker_buy_ratio:.2f}")

        # 5. 펀딩비: 음수=공포→롱, 양수과열→숏
        if data.funding_rate < Decimal("-0.0001"):
            long_score += 1
            reasons.append(f"펀딩공포{data.funding_rate:.4f}")
        elif data.funding_rate > Decimal("0.0005"):
            short_score += 1
            reasons.append(f"펀딩과열{data.funding_rate:.4f}")

        reason_str = " | ".join(reasons) if reasons else "지표중립"
        total = long_score + short_score

        if long_score >= self.THRESHOLD and long_score > short_score:
            return MarketBias.LONG, f"롱바이어스({long_score}/{total}점): {reason_str}"
        elif short_score >= self.THRESHOLD and short_score > long_score:
            return MarketBias.SHORT, f"숏바이어스({short_score}/{total}점): {reason_str}"
        else:
            return MarketBias.NEUTRAL, f"중립({long_score}롱/{short_score}숏): {reason_str}"
