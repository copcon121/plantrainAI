"""
Fix #12: FVG Retest Filter.

Purpose:
- Detect and score FVG retests (edge/shallow/deep/no_touch/break).
- Gate signals so only valid retests are surfaced.
- Provides retest quality score for downstream confluence/entry timing.
"""
from typing import Any, Dict, List

from processor.core.module_base import BaseModule


class FVGRetestModule(BaseModule):
    """FVG Retest Detection/Scoring."""

    name = "fix12_fvg_retest"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "max_age_bars": 50,
            "max_fill_pct": 0.8,
            "front_run_buffer_atr": 0.1,  # no-touch threshold
            "edge_penetration": 0.15,
            "shallow_penetration": 0.45,
            "deep_penetration": 0.8,
        }

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        if not self.enabled:
            return bar_state

        history = history or []

        # Require active FVG zone
        fvg_active = bar_state.get("fvg_active", False) or bar_state.get(
            "fvg_detected", False
        )
        fvg_top = bar_state.get("fvg_top", 0.0)
        fvg_bottom = bar_state.get("fvg_bottom", 0.0)
        fvg_type = bar_state.get("fvg_type")
        fvg_bar_index = bar_state.get("fvg_bar_index", bar_state.get("fvg_creation_bar_index", -1))
        bar_index = bar_state.get("bar_index", 0)
        atr = bar_state.get("atr_14", 0.0) or 0.0

        if not fvg_active or fvg_top == 0 or fvg_bottom == 0 or fvg_type is None:
            return {**bar_state, **self._default_output("no_fvg")}

        age_bars = max(bar_index - fvg_bar_index, 0)
        if age_bars > self.config["max_age_bars"]:
            return {**bar_state, **self._default_output("stale")}

        gap_size = abs(fvg_top - fvg_bottom)
        if gap_size <= 0:
            return {**bar_state, **self._default_output("invalid_gap")}

        # Compute fill% from current price if not provided
        fill_percent = bar_state.get("fvg_fill_percent")
        if fill_percent is None:
            close = bar_state.get("close", 0.0)
            fill_percent = self._compute_fill_pct(fvg_type, fvg_top, fvg_bottom, close)

        # Current bar penetration into zone
        penetration_pct, retest_type = self._classify_retest(
            fvg_type, fvg_top, fvg_bottom, bar_state
        )

        if fill_percent >= self.config["max_fill_pct"] or retest_type == "break":
            return {**bar_state, **self._default_output("break_or_filled")}

        # Context triggers (must have at least one)
        context_ok = self._has_reversal_context(fvg_type, bar_state)
        if not context_ok:
            return {**bar_state, **self._default_output("no_context")}

        # Score retest quality
        strength_score = bar_state.get("fvg_strength_score", 0.5)
        retest_quality = self._score_retest(retest_type, penetration_pct, strength_score)

        # Age penalty (linear)
        age_penalty = min(age_bars / self.config["max_age_bars"], 1.0)
        retest_quality *= (1 - 0.3 * age_penalty)

        # Market/structure penalty/bonus
        retest_quality = self._adjust_context_bonus(retest_quality, fvg_type, bar_state)
        retest_quality = max(min(retest_quality, 1.0), 0.0)

        retest_valid = retest_type in {"edge", "shallow", "no_touch"} and retest_quality > 0

        signal_type = None
        if retest_valid:
            signal_type = "fvg_retest_bull" if fvg_type == "bullish" else "fvg_retest_bear"

        return {
            **bar_state,
            "fvg_retest_detected": retest_valid,
            "fvg_retest_type": retest_type,
            "fvg_retest_quality_score": round(retest_quality, 4),
            "fvg_retest_bar_index": bar_index,
            "fvg_retest_penetration_pct": round(penetration_pct, 4),
            "fvg_retest_distance_atr": self._distance_atr(fvg_type, fvg_top, fvg_bottom, bar_state, atr),
            "fvg_retest_valid": retest_valid,
            "fvg_retest_reason": "" if retest_valid else "filtered",
            "signal_type": signal_type or bar_state.get("signal_type", "none"),
        }

    def _compute_fill_pct(self, fvg_type: str, top: float, bottom: float, price: float) -> float:
        gap = abs(top - bottom)
        if gap <= 0 or price == 0:
            return 0.0
        if fvg_type == "bullish":
            if price <= bottom:
                return 1.0
            if price >= top:
                return 0.0
            return (top - price) / gap
        else:
            if price >= top:
                return 1.0
            if price <= bottom:
                return 0.0
            return (price - bottom) / gap

    def _classify_retest(
        self, fvg_type: str, top: float, bottom: float, bar: Dict[str, Any]
    ) -> tuple[float, str]:
        high = bar.get("high", 0.0)
        low = bar.get("low", 0.0)
        gap = abs(top - bottom)
        if gap <= 0:
            return 0.0, "break"

        # Penetration into zone
        if fvg_type == "bullish":
            penetration = max(0.0, top - low)
            break_cond = low < bottom
        else:
            penetration = max(0.0, high - bottom)
            break_cond = high > top

        penetration_pct = min(penetration / gap, 2.0)

        if break_cond or penetration_pct >= 1.0:
            return penetration_pct, "break"
        if penetration_pct <= self.config["edge_penetration"]:
            return penetration_pct, "edge"
        if penetration_pct <= self.config["shallow_penetration"]:
            return penetration_pct, "shallow"
        if penetration_pct <= self.config["deep_penetration"]:
            return penetration_pct, "deep"
        return penetration_pct, "break"

    def _score_retest(self, retest_type: str, penetration_pct: float, strength_score: float) -> float:
        if retest_type == "break":
            return 0.0
        if retest_type == "deep":
            return 0.25 if strength_score >= 0.5 else 0.1
        if retest_type == "shallow":
            return 0.6 if strength_score >= 0.5 else 0.4
        if retest_type == "edge":
            return 0.95 if strength_score >= 0.5 else 0.75
        if retest_type == "no_touch":
            # Closer to edge -> higher
            return max(0.2, 0.8 - penetration_pct)
        return 0.0

    def _has_reversal_context(self, fvg_type: str, bar_state: Dict[str, Any]) -> bool:
        is_bull = fvg_type == "bullish"
        sweep_up = bar_state.get("sweep_prev_high") or (
            bar_state.get("liquidity_sweep_detected")
            and bar_state.get("liquidity_sweep_type", "").startswith("sweep_above")
        )
        sweep_down = bar_state.get("sweep_prev_low") or (
            bar_state.get("liquidity_sweep_detected")
            and bar_state.get("liquidity_sweep_type", "").startswith("sweep_below")
        )

        bos_up = bar_state.get("ext_bos_up") or bar_state.get("int_bos_up")
        bos_down = bar_state.get("ext_bos_down") or bar_state.get("int_bos_down")
        choch_up = bar_state.get("ext_choch_up") or bar_state.get("int_choch_up")
        choch_down = bar_state.get("ext_choch_down") or bar_state.get("int_choch_down")

        premium = bar_state.get("in_premium") or bar_state.get("vp_position") == "upper_va"
        discount = bar_state.get("in_discount") or bar_state.get("vp_position") == "lower_va"

        ob_bull = bar_state.get("has_ob_ext_bull")
        ob_bear = bar_state.get("has_ob_ext_bear")

        if is_bull:
            return sweep_down or bos_up or choch_up or discount or ob_bull
        else:
            return sweep_up or bos_down or choch_down or premium or ob_bear

    def _distance_atr(
        self, fvg_type: str, top: float, bottom: float, bar: Dict[str, Any], atr: float
    ) -> float:
        close = bar.get("close", 0.0)
        if atr <= 0:
            return 0.0
        if fvg_type == "bullish":
            ref = bottom
        else:
            ref = top
        return round(abs(close - ref) / atr, 4)

    def _adjust_context_bonus(self, score: float, fvg_type: str, bar_state: Dict[str, Any]) -> float:
        mc = bar_state.get("market_condition", "")
        struct = bar_state.get("structure_context", "")
        if mc == "ranging_volatile" or mc == "ranging_quiet":
            score *= 0.9
        if struct == "expansion":
            score *= 1.05
        elif struct == "retracement":
            score *= 0.9
        return score

    def _default_output(self, reason: str) -> Dict[str, Any]:
        return {
            "fvg_retest_detected": False,
            "fvg_retest_type": "none",
            "fvg_retest_quality_score": 0.0,
            "fvg_retest_bar_index": -1,
            "fvg_retest_penetration_pct": 0.0,
            "fvg_retest_distance_atr": 0.0,
            "fvg_retest_valid": False,
            "fvg_retest_reason": reason,
            "signal_type": "none",
        }
