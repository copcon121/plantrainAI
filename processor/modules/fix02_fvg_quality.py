"""
Fix #02: FVG Quality (primary signal).
Implement per docs/MODULE_FIX02_FVG_QUALITY.md.

Calculates FVG quality scores including:
- FVG Strength (imbalance quality)
- Value Class Assignment (A/B/C)
- Component scores
"""
from typing import Any, Dict, List

from processor.core.module_base import BaseModule


class FVGQualityModule(BaseModule):
    """FVG Quality Scoring Module - PRIMARY SIGNAL."""

    name = "fix02_fvg_quality"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "strong_size_atr": 1.5,
            "strong_vol_ratio": 2.0,
            "strong_delta_ratio": 0.6,
            "medium_size_atr": 0.8,
            "volume_median_period": 20,
        }

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and calculate FVG quality scores."""
        if not self.enabled:
            return bar_state

        if not bar_state.get("fvg_detected", False):
            return {**bar_state, **self._default_output()}

        history = history or []

        # Calculate FVG strength components
        strength_info = self._calculate_fvg_strength(bar_state, history)

        # Check Value Area context
        va_info = self._check_va_context(bar_state)

        # Determine Value Class
        value_class = self._determine_value_class(strength_info, va_info)

        # Build context string
        context = self._build_context_string(
            strength_info, va_info, bar_state.get("fvg_type", "")
        )

        # Calculate composite quality score
        quality_score = self._calculate_composite_score(strength_info, va_info)

        return {
            **bar_state,
            **strength_info,
            **va_info,
            "fvg_value_class": value_class,
            "fvg_quality_score": round(quality_score, 4),
            "fvg_context": context,
        }

    def _calculate_fvg_strength(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate FVG strength based on imbalance characteristics."""
        fvg_type = bar_state.get("fvg_type", "bullish")
        gap_size = bar_state.get("fvg_gap_size", 0)
        atr = bar_state.get("atr_14", 0.01)
        volume = bar_state.get("fvg_creation_volume", bar_state.get("volume", 0))
        delta = bar_state.get("fvg_creation_delta", bar_state.get("delta", 0))
        buy_vol = bar_state.get("buy_volume", 0)
        sell_vol = bar_state.get("sell_volume", 0)

        # 1. Gap size relative to ATR
        fvg_size_atr = gap_size / atr if atr > 0 else 0
        gap_quality = min(fvg_size_atr / 2.0, 1.0)

        # 2. Volume relative to median
        volume_median = self._get_volume_median(history, 20)
        fvg_vol_ratio = volume / volume_median if volume_median > 0 else 1.0
        volume_quality = min(max((fvg_vol_ratio - 1.0) / 2.0, 0.0), 1.0)

        # 3. Delta imbalance ratio
        total_vol = buy_vol + sell_vol
        fvg_delta_ratio = abs(delta) / total_vol if total_vol > 0 else 0
        imbalance_quality = min(fvg_delta_ratio / 0.8, 1.0)

        # 4. Delta alignment with FVG direction
        if fvg_type == "bullish":
            delta_alignment = 1 if delta > 0 else (-1 if delta < 0 else 0)
        else:
            delta_alignment = 1 if delta < 0 else (-1 if delta > 0 else 0)

        alignment_bonus = 0.1 if delta_alignment == 1 else (-0.1 if delta_alignment == -1 else 0)

        # Calculate composite strength score
        base_score = (
            0.35 * gap_quality
            + 0.30 * volume_quality
            + 0.25 * imbalance_quality
            + 0.10 * (1.0 if delta_alignment == 1 else 0.5)
        )

        strength_score = min(max(base_score + alignment_bonus, 0.0), 1.0)

        # Classify strength
        if (
            strength_score >= 0.75
            and fvg_size_atr >= self.config["strong_size_atr"]
            and fvg_vol_ratio >= self.config["strong_vol_ratio"]
        ):
            strength_class = "Strong"
        elif strength_score >= 0.50 and fvg_size_atr >= self.config["medium_size_atr"]:
            strength_class = "Medium"
        else:
            strength_class = "Weak"

        return {
            "fvg_size_atr": round(fvg_size_atr, 4),
            "fvg_vol_ratio": round(fvg_vol_ratio, 4),
            "fvg_delta_ratio": round(fvg_delta_ratio, 4),
            "fvg_delta_alignment": delta_alignment,
            "fvg_strength_score": round(strength_score, 4),
            "fvg_strength_class": strength_class,
            "fvg_gap_quality_score": round(gap_quality, 4),
            "fvg_volume_quality_score": round(volume_quality, 4),
            "fvg_imbalance_quality_score": round(imbalance_quality, 4),
            "fvg_creation_bar_index": bar_state.get("bar_index", 0),
            "fvg_age_bars": 0,
        }

    def _get_volume_median(self, history: List[Dict[str, Any]], period: int) -> float:
        """Get median volume from history."""
        volumes = [b.get("volume", 0) for b in history[-period:]]
        if not volumes:
            return 1.0
        sorted_vols = sorted(volumes)
        mid = len(sorted_vols) // 2
        return sorted_vols[mid] if sorted_vols else 1.0

    def _check_va_context(self, bar_state: Dict[str, Any]) -> Dict[str, Any]:
        """Check Value Area context."""
        fvg_top = bar_state.get("fvg_top", 0)
        fvg_bottom = bar_state.get("fvg_bottom", 0)
        vah = bar_state.get("vp_session_vah", 0)
        val = bar_state.get("vp_session_val", 0)

        # Check if FVG is in Value Area
        fvg_mid = (fvg_top + fvg_bottom) / 2 if fvg_top and fvg_bottom else 0
        in_va = 0
        breakout_va = 0

        if vah > 0 and val > 0 and fvg_mid > 0:
            if val <= fvg_mid <= vah:
                in_va = 1
            elif fvg_mid > vah or fvg_mid < val:
                breakout_va = 1

        # Check sweep context
        after_sweep = 1 if bar_state.get("liquidity_sweep_detected", False) else 0

        return {
            "fvg_in_va_flag": in_va,
            "fvg_breakout_va_flag": breakout_va,
            "fvg_after_sweep_flag": after_sweep,
        }

    def _determine_value_class(
        self, strength_info: Dict[str, Any], va_info: Dict[str, Any]
    ) -> str:
        """Determine FVG Value Class (A/B/C)."""
        strength_class = strength_info.get("fvg_strength_class", "Weak")
        strength_score = strength_info.get("fvg_strength_score", 0)
        breakout_va = va_info.get("fvg_breakout_va_flag", 0)
        after_sweep = va_info.get("fvg_after_sweep_flag", 0)

        # A class: Strong FVG with good context
        if strength_class == "Strong" and (breakout_va or after_sweep):
            return "A"
        elif strength_class == "Strong":
            return "A"
        elif strength_class == "Medium" and (breakout_va or after_sweep):
            return "B"
        elif strength_class == "Medium":
            return "B"
        elif strength_score >= 0.3:
            return "C"
        else:
            return "C"

    def _build_context_string(
        self,
        strength_info: Dict[str, Any],
        va_info: Dict[str, Any],
        fvg_type: str,
    ) -> str:
        """Build descriptive context string."""
        parts = [fvg_type]

        strength_class = strength_info.get("fvg_strength_class", "").lower()
        if strength_class:
            parts.append(strength_class)

        if va_info.get("fvg_breakout_va_flag"):
            parts.append("breakout_va")
        elif va_info.get("fvg_in_va_flag"):
            parts.append("in_va")

        if va_info.get("fvg_after_sweep_flag"):
            parts.append("after_sweep")

        return "_".join(parts) if parts else "none"

    def _calculate_composite_score(
        self, strength_info: Dict[str, Any], va_info: Dict[str, Any]
    ) -> float:
        """Calculate composite quality score."""
        base_score = strength_info.get("fvg_strength_score", 0)

        # Context bonuses
        if va_info.get("fvg_breakout_va_flag"):
            base_score += 0.1
        if va_info.get("fvg_after_sweep_flag"):
            base_score += 0.05

        return min(base_score, 1.0)

    def _default_output(self) -> Dict[str, Any]:
        """Default output when no FVG detected."""
        return {
            "fvg_size_atr": 0.0,
            "fvg_vol_ratio": 0.0,
            "fvg_delta_ratio": 0.0,
            "fvg_delta_alignment": 0,
            "fvg_strength_score": 0.0,
            "fvg_strength_class": "None",
            "fvg_gap_quality_score": 0.0,
            "fvg_volume_quality_score": 0.0,
            "fvg_imbalance_quality_score": 0.0,
            "fvg_creation_bar_index": 0,
            "fvg_age_bars": 0,
            "fvg_in_va_flag": 0,
            "fvg_breakout_va_flag": 0,
            "fvg_after_sweep_flag": 0,
            "fvg_value_class": "None",
            "fvg_quality_score": 0.0,
            "fvg_context": "none",
        }
