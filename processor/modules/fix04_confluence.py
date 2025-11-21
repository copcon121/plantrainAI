"""
Fix #04: Confluence Scoring.
Combines outputs from other modules per docs/MODULE_FIX04_CONFLUENCE.md.

Calculates weighted confluence score from:
- OB Proximity
- Structure Context
- FVG Strength
- MTF Alignment
- Liquidity Proximity
- Volume Confirmation
"""
from typing import Any, Dict, List

from processor.core.module_base import BaseModule


# Factor weights
CONFLUENCE_WEIGHTS = {
    "ob_proximity": 0.25,
    "structure_context": 0.25,
    "fvg_strength": 0.20,
    "mtf_alignment": 0.15,
    "liquidity_proximity": 0.10,
    "volume_confirm": 0.05,
}


class ConfluenceModule(BaseModule):
    """Confluence Scoring Module."""

    name = "fix04_confluence"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and calculate confluence score."""
        if not self.enabled:
            return bar_state

        # Only calculate confluence for FVG signals
        if not bar_state.get("fvg_detected", False):
            return {**bar_state, **self._default_output()}

        history = history or []

        # Calculate individual factor scores
        factor_scores, missing_inputs = self._calculate_factor_scores(bar_state, history)

        # Calculate weighted confluence score
        weighted_sum = sum(
            factor_scores[factor] * weight
            for factor, weight in CONFLUENCE_WEIGHTS.items()
        )

        # Classify confluence
        if weighted_sum >= 0.75:
            confluence_class = "Strong"
        elif weighted_sum >= 0.50:
            confluence_class = "Moderate"
        else:
            confluence_class = "Weak"

        # Find contributing factors (score > 0.6)
        contributing_factors = [
            factor for factor, score in factor_scores.items() if score >= 0.6
        ]

        return {
            **bar_state,
            "confluence_score": round(weighted_sum, 3),
            "confluence_class": confluence_class,
            "conf_ob_proximity": round(factor_scores["ob_proximity"], 3),
            "conf_structure": round(factor_scores["structure_context"], 3),
            "conf_fvg_strength": round(factor_scores["fvg_strength"], 3),
            "conf_mtf_alignment": round(factor_scores["mtf_alignment"], 3),
            "conf_liquidity": round(factor_scores["liquidity_proximity"], 3),
            "conf_volume": round(factor_scores["volume_confirm"], 3),
            "confluence_factor_count": len(contributing_factors),
            "confluence_factors_list": contributing_factors,
            "confluence_data_complete": len(missing_inputs) == 0,
            "confluence_missing_inputs": missing_inputs,
        }

    def _calculate_factor_scores(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> tuple[Dict[str, float], List[str]]:
        """Calculate individual factor scores."""
        scores: Dict[str, float] = {}
        missing: List[str] = []

        scores["ob_proximity"], miss = self._calc_ob_proximity_score(bar_state)
        if miss:
            missing.append("ob_proximity")

        scores["structure_context"], miss = self._calc_structure_score(bar_state)
        if miss:
            missing.append("structure_context")

        scores["fvg_strength"], miss = self._calc_fvg_strength_score(bar_state)
        if miss:
            missing.append("fvg_strength")

        scores["mtf_alignment"], miss = self._calc_mtf_alignment_score(bar_state)
        if miss:
            missing.append("mtf_alignment")

        scores["liquidity_proximity"], miss = self._calc_liquidity_score(bar_state)
        if miss:
            missing.append("liquidity_proximity")

        scores["volume_confirm"], miss = self._calc_volume_score(bar_state, history)
        if miss:
            missing.append("volume_confirm")

        return scores, missing

    def _calc_ob_proximity_score(self, bar_state: Dict[str, Any]) -> tuple[float, bool]:
        """Calculate OB proximity score."""
        fvg_top = bar_state.get("fvg_top", 0)
        fvg_bottom = bar_state.get("fvg_bottom", 0)
        ob_top = bar_state.get("nearest_ob_top")
        ob_bottom = bar_state.get("nearest_ob_bottom")
        atr = bar_state.get("atr_14", 0.01)

        if ob_top is None or ob_bottom is None or fvg_top == 0:
            return 0.5, True

        # Check if FVG is completely inside OB
        if fvg_top <= ob_top and fvg_bottom >= ob_bottom:
            return 1.0, False

        # Check overlap
        overlap_top = min(fvg_top, ob_top)
        overlap_bottom = max(fvg_bottom, ob_bottom)

        if overlap_top > overlap_bottom:
            # There is overlap
            overlap_size = overlap_top - overlap_bottom
            fvg_size = fvg_top - fvg_bottom
            overlap_ratio = overlap_size / fvg_size if fvg_size > 0 else 0
            return 0.7 + (0.3 * overlap_ratio), False

        # Calculate distance
        if fvg_bottom > ob_top:
            distance = fvg_bottom - ob_top
        else:
            distance = ob_bottom - fvg_top

        distance_atr = distance / atr if atr > 0 else float("inf")

        if distance_atr <= 0.5:
            return 0.6, False
        elif distance_atr <= 1.0:
            return 0.4, False
        elif distance_atr <= 2.0:
            return 0.2, False
        else:
            return 0.0, False

    def _calc_structure_score(self, bar_state: Dict[str, Any]) -> tuple[float, bool]:
        """Calculate structure context score."""
        context_type = bar_state.get("structure_context", "unknown")
        context_multiplier = bar_state.get("structure_context_score", 1.0)

        score_map = {
            "expansion": 1.0,
            "continuation": 0.7,
            "retracement": 0.5,
            "unclear": 0.3,
            "none": 0.3,
            "unknown": 0.3,
        }

        base_score = score_map.get(context_type, 0.3)

        if context_multiplier >= 1.2:
            return min(1.0, base_score * 1.1), False
        elif context_multiplier <= 0.8:
            return base_score * 0.9, False

        return base_score, False

    def _calc_fvg_strength_score(self, bar_state: Dict[str, Any]) -> tuple[float, bool]:
        """Get FVG strength score from Module #02."""
        if "fvg_strength_score" not in bar_state:
            return 0.5, True
        return bar_state.get("fvg_strength_score", 0.0), False

    def _calc_mtf_alignment_score(self, bar_state: Dict[str, Any]) -> tuple[float, bool]:
        """Calculate MTF alignment score."""
        fvg_type = bar_state.get("fvg_type", "")
        fvg_direction = 1 if fvg_type == "bullish" else -1

        htf_trend = bar_state.get("htf_trend", bar_state.get("current_trend", ""))
        htf_strength = bar_state.get("htf_trend_strength", 0.5)

        trend_direction = {"bullish": 1, "bearish": -1, "neutral": 0}.get(htf_trend, 0)

        if trend_direction == 0:
            return 0.5, True

        if fvg_direction == trend_direction:
            return 0.6 + (0.4 * htf_strength), False
        else:
            return max(0.1, 0.4 - (0.3 * htf_strength)), False

    def _calc_liquidity_score(self, bar_state: Dict[str, Any]) -> tuple[float, bool]:
        """Calculate liquidity proximity score."""
        fvg_type = bar_state.get("fvg_type", "bullish")
        atr = bar_state.get("atr_14", 0.01)

        # Get nearest liquidity based on direction
        if fvg_type == "bullish":
            liq_price = bar_state.get("nearest_liquidity_high", 0)
            current = bar_state.get("close", 0)
        else:
            liq_price = bar_state.get("nearest_liquidity_low", 0)
            current = bar_state.get("close", 0)

        if liq_price == 0 or current == 0:
            return 0.5, True

        distance = abs(liq_price - current)
        distance_atr = distance / atr if atr > 0 else float("inf")

        if distance_atr <= 1.0:
            base_score = 1.0
        elif distance_atr <= 2.0:
            base_score = 0.8
        elif distance_atr <= 3.0:
            base_score = 0.6
        else:
            base_score = 0.3

        # Bonus for equal highs/lows
        liq_type = bar_state.get("liquidity_high_type", "") or bar_state.get(
            "liquidity_low_type", ""
        )
        if liq_type in ["equal_highs", "equal_lows"]:
            base_score = min(1.0, base_score * 1.1)

        return base_score, False

    def _calc_volume_score(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> tuple[float, bool]:
        """Calculate volume confirmation score."""
        fvg_volume = bar_state.get("fvg_creation_volume", bar_state.get("volume", 0))
        delta_alignment = bar_state.get("fvg_delta_alignment", 0)

        # Get median volume
        volumes = [b.get("volume", 0) for b in history[-20:]]
        if not volumes:
            median_vol = fvg_volume
        else:
            sorted_vols = sorted(volumes)
            median_vol = sorted_vols[len(sorted_vols) // 2]

        if median_vol == 0:
            return 0.5, True

        vol_ratio = fvg_volume / median_vol

        if vol_ratio >= 2.0:
            base_score = 1.0
        elif vol_ratio >= 1.5:
            base_score = 0.8
        elif vol_ratio >= 1.0:
            base_score = 0.6
        else:
            base_score = 0.4

        # Delta alignment bonus/penalty
        if delta_alignment == 1:
            base_score = min(1.0, base_score * 1.1)
        elif delta_alignment == -1:
            base_score = base_score * 0.8

        return base_score, False

    def _default_output(self) -> Dict[str, Any]:
        """Default output when no FVG."""
        return {
            "confluence_score": 0.0,
            "confluence_class": "None",
            "conf_ob_proximity": 0.0,
            "conf_structure": 0.0,
            "conf_fvg_strength": 0.0,
            "conf_mtf_alignment": 0.0,
            "conf_liquidity": 0.0,
            "conf_volume": 0.0,
            "confluence_factor_count": 0,
            "confluence_factors_list": [],
            "confluence_data_complete": False,
            "confluence_missing_inputs": [],
        }
