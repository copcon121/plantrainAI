"""
Fix #05: Stop Placement.
Implement per docs/MODULE_FIX05_STOP_PLACEMENT.md.

Calculates optimal stop loss placement based on:
- FVG Edge Stop (tightest)
- FVG Full Stop
- OB Edge Stop
- Structure Stop (swing-based, widest)
"""
from typing import Any, Dict, List, Optional

from processor.core.module_base import BaseModule


# Stop distance constraints
STOP_CONSTRAINTS = {
    "min_stop_atr": 0.3,
    "max_stop_atr": 2.0,
    "ideal_stop_atr": 0.8,
}

# Buffer ratios per method
BUFFER_RATIOS = {
    "fvg_edge": 0.1,
    "fvg_full": 0.15,
    "ob_edge": 0.15,
    "structure": 0.2,
}


class StopPlacementModule(BaseModule):
    """Stop Placement Module."""

    name = "fix05_stop_placement"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and calculate stop placement."""
        if not self.enabled:
            return bar_state

        # Only calculate for FVG signals
        if not bar_state.get("fvg_detected", False):
            return {**bar_state, **self._default_output()}

        # Get required fields
        fvg_type = bar_state.get("fvg_type", "bullish")
        fvg_direction = 1 if fvg_type == "bullish" else -1
        fvg_top = bar_state.get("fvg_top", 0)
        fvg_bottom = bar_state.get("fvg_bottom", 0)
        entry_price = bar_state.get("close", (fvg_top + fvg_bottom) / 2)
        atr = bar_state.get("atr_14", 0.01)

        ob_top = bar_state.get("nearest_ob_top")
        ob_bottom = bar_state.get("nearest_ob_bottom")
        swing_high = bar_state.get("last_swing_high")
        swing_low = bar_state.get("last_swing_low")
        fvg_strength = bar_state.get("fvg_strength_class", "Medium")

        # Calculate all stop options
        all_options = []

        fvg_edge = self._calc_fvg_edge_stop(fvg_direction, fvg_top, fvg_bottom, atr)
        if fvg_edge:
            all_options.append(fvg_edge)

        fvg_full = self._calc_fvg_full_stop(fvg_direction, fvg_top, fvg_bottom, atr)
        if fvg_full:
            all_options.append(fvg_full)

        ob_stop = self._calc_ob_stop(fvg_direction, ob_top, ob_bottom, atr)
        if ob_stop:
            all_options.append(ob_stop)

        structure_stop = self._calc_structure_stop(fvg_direction, swing_high, swing_low, atr)
        if structure_stop:
            all_options.append(structure_stop)

        # Select optimal stop
        result = self._select_optimal_stop(
            all_options, entry_price, fvg_strength, atr
        )

        if result is None:
            return {**bar_state, **self._default_output()}

        return {
            **bar_state,
            "stop_price": result["stop_price"],
            "stop_type": result["stop_type"],
            "stop_distance": result["stop_distance"],
            "stop_distance_atr": result["stop_distance_atr"],
            "stop_invalidation_level": result["invalidation_level"],
            "stop_buffer": result["buffer_used"],
            "stop_valid": result["valid"],
            "stop_reason": result["reason"],
        }

    def _calc_fvg_edge_stop(
        self, direction: int, fvg_top: float, fvg_bottom: float, atr: float
    ) -> Optional[Dict[str, Any]]:
        """Calculate stop just beyond FVG edge (tightest)."""
        if fvg_top == 0 or fvg_bottom == 0:
            return None

        buffer = atr * BUFFER_RATIOS["fvg_edge"]

        if direction == 1:  # Bullish - stop below FVG bottom
            stop_price = fvg_bottom - buffer
            invalidation = fvg_bottom
        else:  # Bearish - stop above FVG top
            stop_price = fvg_top + buffer
            invalidation = fvg_top

        return {
            "stop_price": round(stop_price, 5),
            "stop_type": "fvg_edge",
            "invalidation_level": invalidation,
            "buffer_used": buffer,
        }

    def _calc_fvg_full_stop(
        self, direction: int, fvg_top: float, fvg_bottom: float, atr: float
    ) -> Optional[Dict[str, Any]]:
        """Calculate stop beyond FVG with extra buffer."""
        if fvg_top == 0 or fvg_bottom == 0:
            return None

        buffer = atr * BUFFER_RATIOS["fvg_full"]
        fvg_size = fvg_top - fvg_bottom

        if direction == 1:
            stop_price = fvg_bottom - (fvg_size * 0.2) - buffer
            invalidation = fvg_bottom
        else:
            stop_price = fvg_top + (fvg_size * 0.2) + buffer
            invalidation = fvg_top

        return {
            "stop_price": round(stop_price, 5),
            "stop_type": "fvg_full",
            "invalidation_level": invalidation,
            "buffer_used": buffer,
        }

    def _calc_ob_stop(
        self,
        direction: int,
        ob_top: Optional[float],
        ob_bottom: Optional[float],
        atr: float,
    ) -> Optional[Dict[str, Any]]:
        """Calculate stop beyond Order Block."""
        if ob_top is None or ob_bottom is None:
            return None

        buffer = atr * BUFFER_RATIOS["ob_edge"]

        if direction == 1:
            stop_price = ob_bottom - buffer
            invalidation = ob_bottom
        else:
            stop_price = ob_top + buffer
            invalidation = ob_top

        return {
            "stop_price": round(stop_price, 5),
            "stop_type": "ob_edge",
            "invalidation_level": invalidation,
            "buffer_used": buffer,
        }

    def _calc_structure_stop(
        self,
        direction: int,
        swing_high: Optional[float],
        swing_low: Optional[float],
        atr: float,
    ) -> Optional[Dict[str, Any]]:
        """Calculate stop beyond swing structure (widest)."""
        buffer = atr * BUFFER_RATIOS["structure"]

        if direction == 1:
            if swing_low is None:
                return None
            stop_price = swing_low - buffer
            invalidation = swing_low
        else:
            if swing_high is None:
                return None
            stop_price = swing_high + buffer
            invalidation = swing_high

        return {
            "stop_price": round(stop_price, 5),
            "stop_type": "structure",
            "invalidation_level": invalidation,
            "buffer_used": buffer,
        }

    def _select_optimal_stop(
        self,
        options: List[Dict[str, Any]],
        entry_price: float,
        fvg_strength: str,
        atr: float,
    ) -> Optional[Dict[str, Any]]:
        """Select optimal stop based on FVG strength."""
        if not options:
            return None

        # Priority order based on FVG strength
        if fvg_strength == "Strong":
            priority = ["fvg_edge", "fvg_full", "ob_edge", "structure"]
        elif fvg_strength == "Medium":
            priority = ["fvg_full", "ob_edge", "fvg_edge", "structure"]
        else:
            priority = ["ob_edge", "structure", "fvg_full", "fvg_edge"]

        for stop_type in priority:
            for option in options:
                if option["stop_type"] != stop_type:
                    continue

                stop_distance = abs(entry_price - option["stop_price"])
                stop_distance_atr = stop_distance / atr if atr > 0 else float("inf")

                # Validate constraints
                if stop_distance_atr < STOP_CONSTRAINTS["min_stop_atr"]:
                    continue
                if stop_distance_atr > STOP_CONSTRAINTS["max_stop_atr"]:
                    continue

                return {
                    **option,
                    "stop_distance": round(stop_distance, 5),
                    "stop_distance_atr": round(stop_distance_atr, 3),
                    "valid": True,
                    "reason": "valid",
                }

        # Fallback: return widest option if within max
        for option in sorted(
            options,
            key=lambda x: abs(entry_price - x["stop_price"]),
            reverse=True,
        ):
            stop_distance = abs(entry_price - option["stop_price"])
            stop_distance_atr = stop_distance / atr if atr > 0 else float("inf")

            if stop_distance_atr <= STOP_CONSTRAINTS["max_stop_atr"]:
                return {
                    **option,
                    "stop_distance": round(stop_distance, 5),
                    "stop_distance_atr": round(stop_distance_atr, 3),
                    "valid": True,
                    "reason": "fallback",
                }

        return None

    def _default_output(self) -> Dict[str, Any]:
        """Default output when no valid stop."""
        return {
            "stop_price": 0.0,
            "stop_type": "none",
            "stop_distance": 0.0,
            "stop_distance_atr": 0.0,
            "stop_invalidation_level": 0.0,
            "stop_buffer": 0.0,
            "stop_valid": False,
            "stop_reason": "no_fvg",
        }
