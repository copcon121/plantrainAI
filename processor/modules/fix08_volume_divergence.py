"""
Fix #08: Volume Divergence.
Implement per docs/MODULE_FIX08_VOLUME_DIVERGENCE.md.

Detects price/delta divergence at swings:
- Bullish divergence: Lower price low, higher delta
- Bearish divergence: Higher price high, lower delta
"""
from typing import Any, Dict, List, Optional

from processor.core.module_base import BaseModule


class VolumeDivergenceModule(BaseModule):
    """Volume/Delta Divergence Detection Module."""

    name = "fix08_volume_divergence"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "lookback_swings": 10,  # Number of bars to look back for swings
            "min_swing_distance": 3,  # Minimum bars between swings
            "divergence_threshold": 0.1,  # Minimum delta difference ratio
        }
        self._swing_history: List[Dict[str, Any]] = []

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and detect divergence."""
        if not self.enabled:
            return bar_state

        history = history or []

        # Update swing history if current bar is a swing
        self._update_swing_history(bar_state, history)

        # Detect divergence
        divergence_info = self._detect_divergence(bar_state, history)

        return {
            **bar_state,
            "divergence_detected": divergence_info["detected"],
            "divergence_type": divergence_info["type"],
            "divergence_strength": round(divergence_info["strength"], 3),
            "divergence_swing_count": divergence_info["swing_count"],
            "divergence_bars_ago": divergence_info["bars_ago"],
        }

    def _update_swing_history(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> None:
        """Track swing highs and lows."""
        is_swing_high = bar_state.get("is_swing_high", False)
        is_swing_low = bar_state.get("is_swing_low", False)

        if is_swing_high or is_swing_low:
            swing_data = {
                "bar_index": bar_state.get("bar_index", 0),
                "high": bar_state.get("high", 0),
                "low": bar_state.get("low", 0),
                "delta": bar_state.get("delta", 0),
                "cumulative_delta": bar_state.get("cumulative_delta", 0),
                "is_high": is_swing_high,
                "is_low": is_swing_low,
            }
            self._swing_history.append(swing_data)

            # Keep only recent swings
            max_swings = self.config["lookback_swings"] * 2
            if len(self._swing_history) > max_swings:
                self._swing_history = self._swing_history[-max_swings:]

    def _detect_divergence(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect bullish or bearish divergence."""
        default = {
            "detected": False,
            "type": "none",
            "strength": 0.0,
            "swing_count": 0,
            "bars_ago": 0,
        }

        is_swing_high = bar_state.get("is_swing_high", False)
        is_swing_low = bar_state.get("is_swing_low", False)

        if not (is_swing_high or is_swing_low):
            return default

        current_bar = bar_state.get("bar_index", 0)
        current_price_high = bar_state.get("high", 0)
        current_price_low = bar_state.get("low", 0)
        current_delta = bar_state.get("delta", 0)
        current_cum_delta = bar_state.get("cumulative_delta", 0)

        # Check for bullish divergence at swing low
        if is_swing_low:
            prev_swing_low = self._find_previous_swing(
                "low", current_bar, self.config["min_swing_distance"]
            )

            if prev_swing_low:
                # Bullish divergence: Lower low in price, higher delta
                price_lower = current_price_low < prev_swing_low["low"]
                delta_higher = current_delta > prev_swing_low["delta"]

                if price_lower and delta_higher:
                    strength = self._calculate_divergence_strength(
                        current_price_low,
                        prev_swing_low["low"],
                        current_delta,
                        prev_swing_low["delta"],
                    )
                    return {
                        "detected": True,
                        "type": "bullish",
                        "strength": strength,
                        "swing_count": 2,
                        "bars_ago": current_bar - prev_swing_low["bar_index"],
                    }

        # Check for bearish divergence at swing high
        if is_swing_high:
            prev_swing_high = self._find_previous_swing(
                "high", current_bar, self.config["min_swing_distance"]
            )

            if prev_swing_high:
                # Bearish divergence: Higher high in price, lower delta
                price_higher = current_price_high > prev_swing_high["high"]
                delta_lower = current_delta < prev_swing_high["delta"]

                if price_higher and delta_lower:
                    strength = self._calculate_divergence_strength(
                        current_price_high,
                        prev_swing_high["high"],
                        current_delta,
                        prev_swing_high["delta"],
                    )
                    return {
                        "detected": True,
                        "type": "bearish",
                        "strength": strength,
                        "swing_count": 2,
                        "bars_ago": current_bar - prev_swing_high["bar_index"],
                    }

        return default

    def _find_previous_swing(
        self, swing_type: str, current_bar: int, min_distance: int
    ) -> Optional[Dict[str, Any]]:
        """Find the most recent swing of given type."""
        key = "is_high" if swing_type == "high" else "is_low"

        for swing in reversed(self._swing_history[:-1]):  # Exclude current
            if swing[key]:
                bars_distance = current_bar - swing["bar_index"]
                if bars_distance >= min_distance:
                    return swing

        return None

    def _calculate_divergence_strength(
        self,
        current_price: float,
        prev_price: float,
        current_delta: float,
        prev_delta: float,
    ) -> float:
        """Calculate divergence strength (0-1)."""
        if prev_price == 0 or prev_delta == 0:
            return 0.5

        # Price divergence magnitude
        price_diff_pct = abs(current_price - prev_price) / prev_price

        # Delta divergence magnitude
        delta_diff = abs(current_delta - prev_delta)
        delta_base = max(abs(prev_delta), abs(current_delta), 1)
        delta_diff_pct = delta_diff / delta_base

        # Combined strength (weighted average)
        strength = 0.4 * min(price_diff_pct * 10, 1.0) + 0.6 * min(delta_diff_pct, 1.0)

        return min(strength, 1.0)
