"""
Fix #01: OB Quality Scoring.
Implement logic per docs/MODULE_FIX01_OB_QUALITY.md.

Calculates ob_strength_score from 0-1 based on:
- Displacement RR
- Volume factor
- Delta imbalance
- Liquidity sweep
"""
from typing import Any, Dict, List

from processor.core.module_base import BaseModule


class OBQualityModule(BaseModule):
    """Order Block Quality Scoring Module."""

    name = "fix01_ob_quality"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "volume_median_period": 20,
            "max_ob_age_bars": 30,
            "require_sweep": True,
            "require_flip_flag": False,  # allows enforcement if indicator supplies ob_flip_valid
            # Scoring weights (must sum to 1.0)
            "weight_displacement": 0.4,
            "weight_volume": 0.3,
            "weight_delta": 0.2,
            "weight_sweep": 0.1,
            # Liquidity sweep detection
            "sweep_lookback_bars": 10,  # bars to look back for swing high/low before OB
            "sweep_min_bars": 3,  # minimum bars needed for sweep detection
        }

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and calculate OB quality scores."""
        if not self.enabled:
            return bar_state

        history = history or []

        # Check if OB detected
        if not bar_state.get("ob_detected", False):
            return {**bar_state, **self._default_output()}

        eligibility, reason = self._check_eligibility(bar_state, history)
        if not eligibility:
            return {**bar_state, **self._default_output(reason)}

        # Calculate each component
        displacement_rr = self._calculate_displacement_rr(bar_state)
        displacement_score = min(displacement_rr / 4.0, 1.0)

        historical_volumes = [
            b.get("volume", 0) for b in history[-self.config["volume_median_period"] :]
        ]
        ob_volume = bar_state.get("ob_volume", bar_state.get("volume", 0) or 0)
        volume_factor = self._calculate_volume_factor(ob_volume, historical_volumes)
        volume_score = min(max((volume_factor - 1.0) / 2.0, 0.0), 1.0)

        delta_imbalance = self._calculate_delta_imbalance(
            bar_state.get("buy_volume", bar_state.get("buy_vol", 0)),
            bar_state.get("sell_volume", bar_state.get("sell_vol", 0)),
            bar_state.get("ob_direction", "bull"),
        )

        liquidity_sweep = self._detect_liquidity_sweep(
            history + [bar_state],
            len(history),
            bar_state.get("ob_direction", "bull"),
        )

        # Final weighted score using configurable weights
        ob_strength_score = (
            self.config["weight_displacement"] * displacement_score
            + self.config["weight_volume"] * volume_score
            + self.config["weight_delta"] * delta_imbalance
            + self.config["weight_sweep"] * (1.0 if liquidity_sweep else 0.0)
        )

        return {
            **bar_state,
            "ob_strength_score": round(ob_strength_score, 3),
            "ob_volume_factor": round(volume_factor, 2),
            "ob_delta_imbalance": round(delta_imbalance, 3),
            "ob_displacement_rr": round(displacement_rr, 2),
            "ob_liquidity_sweep": liquidity_sweep,
            "ob_valid": True,
            "ob_invalid_reason": "",
        }

    def _check_eligibility(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> tuple[bool, str]:
        """Validate required OB inputs and conditions before scoring."""
        required_fields = ["ob_high", "ob_low", "ob_direction"]
        for field in required_fields:
            if bar_state.get(field) in (None, 0):
                return False, f"missing_{field}"

        # Time-in-range guard
        current_bar = bar_state.get("bar_index", len(history))
        ob_bar_index = bar_state.get("ob_bar_index", current_bar)
        if current_bar - ob_bar_index > self.config["max_ob_age_bars"]:
            return False, "stale_ob"

        # Optional flip validation if provided by exporter
        if self.config["require_flip_flag"]:
            flip_valid = bar_state.get("ob_flip_valid")
            if flip_valid is False or flip_valid is None:
                return False, "no_flip"

        # Require sweep if configured (use detection with available history)
        if self.config["require_sweep"]:
            sweep = self._detect_liquidity_sweep(
                history + [bar_state], len(history), bar_state.get("ob_direction", "bull")
            )
            if not sweep:
                return False, "no_sweep"

        return True, ""

    def _calculate_displacement_rr(self, ob_data: Dict[str, Any]) -> float:
        """Calculate OB displacement RR ratio."""
        ob_high = ob_data.get("ob_high", 0)
        ob_low = ob_data.get("ob_low", 0)

        if ob_high == 0 or ob_low == 0:
            return 0.0

        ob_mid = (ob_high + ob_low) / 2.0
        ob_direction = ob_data.get("ob_direction", "bull")
        swing_after = ob_data.get("swing_after_price", 0)

        if swing_after == 0:
            # Use high/close as proxy for swing after
            if ob_direction == "bull":
                swing_after = ob_data.get("high", ob_mid)
            else:
                swing_after = ob_data.get("low", ob_mid)

        if ob_direction == "bull":
            ob_extreme = ob_low
            if swing_after <= ob_mid:
                return 0.0
            ob_move = abs(swing_after - ob_mid)
        else:
            ob_extreme = ob_high
            if swing_after >= ob_mid:
                return 0.0
            ob_move = abs(ob_mid - swing_after)

        ob_risk = abs(ob_mid - ob_extreme)
        if ob_risk < 1e-8:
            return 0.0

        return ob_move / ob_risk

    def _calculate_volume_factor(
        self, ob_volume: float, historical_volumes: List[float]
    ) -> float:
        """Calculate volume factor vs median."""
        if not historical_volumes:
            return 1.0

        lookback = self.config["volume_median_period"]
        if len(historical_volumes) < lookback:
            median_vol = (
                sum(historical_volumes) / len(historical_volumes) if historical_volumes else 1
            )
        else:
            sorted_vols = sorted(historical_volumes[-lookback:])
            mid = len(sorted_vols) // 2
            median_vol = sorted_vols[mid]

        if median_vol < 1:
            return 1.0

        return ob_volume / median_vol

    def _calculate_delta_imbalance(
        self, buy_vol: float, sell_vol: float, direction: str
    ) -> float:
        """Calculate delta imbalance score."""
        total_vol = buy_vol + sell_vol
        if total_vol < 1:
            return 0.0

        raw_imbalance = abs(buy_vol - sell_vol) / total_vol

        # Check direction alignment
        if direction == "bull" and buy_vol > sell_vol:
            return raw_imbalance
        elif direction == "bear" and sell_vol > buy_vol:
            return raw_imbalance
        else:
            return raw_imbalance * 0.3  # Wrong direction penalty

    def _detect_liquidity_sweep(
        self, bars: List[Dict[str, Any]], ob_index: int, direction: str
    ) -> bool:
        """Detect if OB formed after liquidity sweep."""
        lookback = self.config["sweep_lookback_bars"]
        min_bars = self.config["sweep_min_bars"]

        if ob_index < min_bars or ob_index >= len(bars):
            return False

        # Get recent swing high/low before OB with configurable lookback
        lookback_bars = bars[max(0, ob_index - lookback) : ob_index]
        if len(lookback_bars) < min_bars:
            return False

        recent_swing_high = max(b.get("high", 0) for b in lookback_bars)
        recent_swing_low = min(b.get("low", float("inf")) for b in lookback_bars)

        ob_bar = bars[ob_index]
        ob_low = ob_bar.get("low", 0)
        ob_high = ob_bar.get("high", 0)
        ob_close = ob_bar.get("close", 0)

        if direction == "bull":
            # Bull OB: Sweep low, then close higher
            if ob_low <= recent_swing_low and ob_close > recent_swing_low:
                return True
        else:
            # Bear OB: Sweep high, then close lower
            if ob_high >= recent_swing_high and ob_close < recent_swing_high:
                return True

        return False

    def _default_output(self, reason: str = "no_ob") -> Dict[str, Any]:
        """Default output when module disabled or no OB."""
        return {
            "ob_strength_score": 0.0,
            "ob_volume_factor": 0.0,
            "ob_delta_imbalance": 0.0,
            "ob_displacement_rr": 0.0,
            "ob_liquidity_sweep": False,
            "ob_valid": False,
            "ob_invalid_reason": reason,
        }
