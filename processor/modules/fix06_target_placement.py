"""
Fix #06: Target Placement.
Implement per docs/MODULE_FIX06_TARGET_PLACEMENT.md.

Calculates take profit levels based on:
- Swing structure targets
- Liquidity pool targets
- Session level targets
- RR-based targets
"""
from typing import Any, Dict, List, Optional

from processor.core.module_base import BaseModule


class TargetPlacementModule(BaseModule):
    """Target Placement Module."""

    name = "fix06_target_placement"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "min_rr": 1.5,
            "tp1_rr": 1.5,
            "tp2_rr": 2.5,
            "tp3_rr": 4.0,
        }

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and calculate target levels."""
        if not self.enabled:
            return bar_state

        # Need FVG (or retest) and stop to calculate targets
        if not (
            bar_state.get("fvg_detected", False)
            or bar_state.get("fvg_retest_detected", False)
            or bar_state.get("fvg_active", False)
        ):
            return {**bar_state, **self._default_output(reason="no_fvg")}

        fvg_type = bar_state.get("fvg_type", "bullish")
        fvg_direction = 1 if fvg_type == "bullish" else -1

        entry_price = bar_state.get("entry", bar_state.get("close", 0))
        stop_price = bar_state.get("stop_price", 0)
        atr = bar_state.get("atr_14", 0.01)

        if not entry_price or not stop_price or stop_price == entry_price:
            return {**bar_state, **self._default_output(reason="missing_stop_or_entry")}
        if atr is None or atr <= 0:
            return {**bar_state, **self._default_output(reason="invalid_atr")}

        # Get target sources
        swing_high = bar_state.get("last_swing_high", bar_state.get("recent_swing_high"))
        swing_low = bar_state.get("last_swing_low", bar_state.get("recent_swing_low"))
        liq_high = bar_state.get("nearest_liquidity_high")
        liq_low = bar_state.get("nearest_liquidity_low")
        session_high = bar_state.get("prev_session_high")
        session_low = bar_state.get("prev_session_low")

        # Calculate risk for RR-based targets
        risk = abs(entry_price - stop_price) if stop_price else atr

        # Collect potential targets
        targets = self._collect_targets(
            fvg_direction,
            entry_price,
            risk,
            swing_high,
            swing_low,
            liq_high,
            liq_low,
            session_high,
            session_low,
        )

        # Select TP1, TP2, TP3
        tp1, tp1_type = self._select_tp(targets, entry_price, risk, self.config["tp1_rr"], fvg_direction)
        tp2, tp2_type = self._select_tp(targets, entry_price, risk, self.config["tp2_rr"], fvg_direction)
        tp3, tp3_type = self._select_tp(targets, entry_price, risk, self.config["tp3_rr"], fvg_direction)

        # Calculate RRs
        rr1 = self._calc_rr(entry_price, stop_price, tp1, fvg_direction) if tp1 else 0
        rr2 = self._calc_rr(entry_price, stop_price, tp2, fvg_direction) if tp2 else 0
        rr3 = self._calc_rr(entry_price, stop_price, tp3, fvg_direction) if tp3 else 0

        return {
            **bar_state,
            "tp1_price": round(tp1, 5) if tp1 else 0.0,
            "tp1_type": tp1_type,
            "tp1_rr": round(rr1, 2),
            "tp2_price": round(tp2, 5) if tp2 else 0.0,
            "tp2_type": tp2_type,
            "tp2_rr": round(rr2, 2),
            "tp3_price": round(tp3, 5) if tp3 else 0.0,
            "tp3_type": tp3_type,
            "tp3_rr": round(rr3, 2),
            "target_valid": tp1 is not None and rr1 >= self.config["min_rr"],
            "target_reason": "ok" if tp1 else "no_target",
        }

    def _collect_targets(
        self,
        direction: int,
        entry: float,
        risk: float,
        swing_high: Optional[float],
        swing_low: Optional[float],
        liq_high: Optional[float],
        liq_low: Optional[float],
        session_high: Optional[float],
        session_low: Optional[float],
    ) -> List[Dict[str, Any]]:
        """Collect all potential target levels."""
        targets = []

        if direction == 1:  # Bullish - targets above entry
            if swing_high and swing_high > entry:
                targets.append({"price": swing_high, "type": "swing"})
            if liq_high and liq_high > entry:
                targets.append({"price": liq_high, "type": "liquidity"})
            if session_high and session_high > entry:
                targets.append({"price": session_high, "type": "session"})

            # Add RR-based targets
            for rr in [1.5, 2.0, 2.5, 3.0, 4.0]:
                targets.append({"price": entry + (risk * rr), "type": f"rr_{rr}"})

        else:  # Bearish - targets below entry
            if swing_low and swing_low < entry:
                targets.append({"price": swing_low, "type": "swing"})
            if liq_low and liq_low < entry:
                targets.append({"price": liq_low, "type": "liquidity"})
            if session_low and session_low < entry:
                targets.append({"price": session_low, "type": "session"})

            # Add RR-based targets
            for rr in [1.5, 2.0, 2.5, 3.0, 4.0]:
                targets.append({"price": entry - (risk * rr), "type": f"rr_{rr}"})

        return targets

    def _select_tp(
        self,
        targets: List[Dict[str, Any]],
        entry: float,
        risk: float,
        min_rr: float,
        direction: int,
    ) -> tuple:
        """Select target meeting minimum RR requirement."""
        if not targets:
            return None, "none"

        min_distance = risk * min_rr

        # Filter valid targets
        valid_targets = []
        for t in targets:
            distance = abs(t["price"] - entry)
            if distance >= min_distance:
                # Check direction validity
                if direction == 1 and t["price"] > entry:
                    valid_targets.append(t)
                elif direction == -1 and t["price"] < entry:
                    valid_targets.append(t)

        if not valid_targets:
            # Fallback to RR-based
            if direction == 1:
                return entry + min_distance, f"rr_{min_rr}"
            else:
                return entry - min_distance, f"rr_{min_rr}"

        # Sort by distance and pick closest that meets RR
        valid_targets.sort(key=lambda x: abs(x["price"] - entry))

        # Prefer structure targets over RR-based
        for t in valid_targets:
            if t["type"] in ["swing", "liquidity", "session"]:
                return t["price"], t["type"]

        return valid_targets[0]["price"], valid_targets[0]["type"]

    def _calc_rr(
        self, entry: float, stop: float, target: float, direction: int
    ) -> float:
        """Calculate risk-reward ratio."""
        if stop == 0 or target is None:
            return 0.0

        risk = abs(entry - stop)
        if risk < 1e-8:
            return 0.0

        reward = abs(target - entry)
        return reward / risk

    def _default_output(self, reason: str = "no_fvg") -> Dict[str, Any]:
        """Default output when no targets."""
        return {
            "tp1_price": 0.0,
            "tp1_type": "none",
            "tp1_rr": 0.0,
            "tp2_price": 0.0,
            "tp2_type": "none",
            "tp2_rr": 0.0,
            "tp3_price": 0.0,
            "tp3_type": "none",
            "tp3_rr": 0.0,
            "target_valid": False,
            "target_reason": reason,
        }
