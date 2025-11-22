"""
Fix #10: MTF Alignment.
Implement per docs/MODULE_FIX10_MTF_ALIGNMENT.md.

Evaluates higher timeframe trend alignment:
- HTF EMA alignment (price vs EMA20/50)
- HTF structure alignment
- Normalized alignment score (0-1)
"""
from typing import Any, Dict, List

from processor.core.module_base import BaseModule


class MTFAlignmentModule(BaseModule):
    """Multi-Timeframe Alignment Module."""

    name = "fix10_mtf_alignment"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and evaluate MTF alignment."""
        if not self.enabled:
            return bar_state

        # Get HTF data (expected from Ninja export)
        htf_close = bar_state.get("htf_close", bar_state.get("close", 0))
        htf_ema_20 = bar_state.get("htf_ema_20", 0)
        htf_ema_50 = bar_state.get("htf_ema_50", 0)
        htf_high = bar_state.get("htf_high", bar_state.get("high", 0))
        htf_low = bar_state.get("htf_low", bar_state.get("low", 0))

        # Current timeframe data
        fvg_type = bar_state.get("fvg_type", "")
        fvg_direction = 1 if fvg_type == "bullish" else -1 if fvg_type == "bearish" else 0

        # Calculate alignment components
        ema_alignment = self._check_ema_alignment(htf_close, htf_ema_20, htf_ema_50)
        structure_alignment = self._check_structure_alignment(bar_state)

        # If HTF data missing, return neutral defaults and flag incomplete
        if not ema_alignment.get("data_complete", False):
            return {
                **bar_state,
                "mtf_alignment_score": 0.0,
                "mtf_alignment_points": 0,
                "htf_trend": "neutral",
                "htf_trend_strength": 0.0,
                "htf_price_vs_ema20": 0,
                "htf_price_vs_ema50": 0,
                "htf_ema_trend": 0,
                "htf_structure_direction": structure_alignment["direction"],
                "htf_structure_source": structure_alignment["type"],
                "mtf_is_aligned": False,
                "mtf_data_complete": False,
            }

        # Calculate overall alignment score (0-3/4 points -> normalized to 0-1)
        total_points = 0
        total_factors = 3 + (1 if structure_alignment["direction"] != 0 else 0)

        # Point 1: Price above/below EMA20
        if ema_alignment["price_vs_ema20"] == fvg_direction:
            total_points += 1

        # Point 2: Price above/below EMA50
        if ema_alignment["price_vs_ema50"] == fvg_direction:
            total_points += 1

        # Point 3: EMA20 above/below EMA50 (trend)
        if ema_alignment["ema_trend"] == fvg_direction:
            total_points += 1

        # Point 4: HTF structure direction
        if structure_alignment["direction"] == fvg_direction and fvg_direction != 0:
            total_points += 1

        # Normalize to 0-1
        alignment_score = total_points / max(total_factors, 1)

        # Determine trend
        if ema_alignment["ema_trend"] == 1:
            htf_trend = "bullish"
        elif ema_alignment["ema_trend"] == -1:
            htf_trend = "bearish"
        else:
            htf_trend = "neutral"

        # Check if FVG aligns with HTF trend
        is_aligned = fvg_direction == ema_alignment["ema_trend"] if fvg_direction != 0 else False
        data_complete = ema_alignment["data_complete"]

        return {
            **bar_state,
            "mtf_alignment_score": round(alignment_score, 3),
            "mtf_alignment_points": total_points,
            "htf_trend": htf_trend,
            "htf_trend_strength": round(abs(ema_alignment["trend_strength"]), 3),
            "htf_price_vs_ema20": ema_alignment["price_vs_ema20"],
            "htf_price_vs_ema50": ema_alignment["price_vs_ema50"],
            "htf_ema_trend": ema_alignment["ema_trend"],
            "htf_structure_direction": structure_alignment["direction"],
            "htf_structure_source": structure_alignment["type"],
            "mtf_is_aligned": is_aligned,
            "mtf_data_complete": data_complete,
        }

    def _check_ema_alignment(
        self, price: float, ema_20: float, ema_50: float
    ) -> Dict[str, Any]:
        """Check price and EMA alignment."""
        if ema_20 == 0 or ema_50 == 0:
            return {
                "price_vs_ema20": 0,
                "price_vs_ema50": 0,
                "ema_trend": 0,
                "trend_strength": 0.0,
                "data_complete": False,
            }

        # Price vs EMAs
        price_vs_ema20 = 1 if price > ema_20 else -1 if price < ema_20 else 0
        price_vs_ema50 = 1 if price > ema_50 else -1 if price < ema_50 else 0

        # EMA trend (EMA20 vs EMA50)
        ema_trend = 1 if ema_20 > ema_50 else -1 if ema_20 < ema_50 else 0

        # Trend strength (distance between EMAs as % of price)
        ema_diff = abs(ema_20 - ema_50)
        trend_strength = ema_diff / price if price > 0 else 0

        return {
            "price_vs_ema20": price_vs_ema20,
            "price_vs_ema50": price_vs_ema50,
            "ema_trend": ema_trend,
            "trend_strength": trend_strength,
            "data_complete": True,
        }

    def _check_structure_alignment(self, bar_state: Dict[str, Any]) -> Dict[str, Any]:
        """Check HTF structure alignment."""
        htf_is_swing_high = bar_state.get("htf_is_swing_high", False)
        htf_is_swing_low = bar_state.get("htf_is_swing_low", False)

        # HTF BOS/CHoCH if provided (only count recent)
        bos_type = bar_state.get("htf_bos_type")
        choch_type = bar_state.get("htf_choch_type")
        bos_bars_ago = bar_state.get("htf_bos_bars_ago", 999)
        choch_bars_ago = bar_state.get("htf_choch_bars_ago", 999)
        max_structure_age = 20

        if (bos_type == "bullish" and bos_bars_ago <= max_structure_age) or (
            choch_type == "bullish" and choch_bars_ago <= max_structure_age
        ):
            return {"direction": 1, "type": "bos_bull" if bos_type == "bullish" else "choch_bull"}
        if (bos_type == "bearish" and bos_bars_ago <= max_structure_age) or (
            choch_type == "bearish" and choch_bars_ago <= max_structure_age
        ):
            return {"direction": -1, "type": "bos_bear" if bos_type == "bearish" else "choch_bear"}

        if htf_is_swing_low:
            return {"direction": 1, "type": "swing_low"}
        if htf_is_swing_high:
            return {"direction": -1, "type": "swing_high"}

        return {"direction": 0, "type": "none"}
