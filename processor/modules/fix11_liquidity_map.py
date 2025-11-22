"""
Fix #11: Liquidity Map.
Implement per docs/MODULE_FIX11_LIQUIDITY_MAP.md.

Tracks liquidity levels and detects sweeps:
- Equal highs/lows detection
- Swing-based liquidity levels
- Sweep detection
"""
from typing import Any, Dict, List, Optional

from processor.core.module_base import BaseModule


class LiquidityMapModule(BaseModule):
    """Liquidity Map Module."""

    name = "fix11_liquidity_map"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "equal_level_tolerance": 0.0002,  # Default tolerance ratio if tick_size not provided
            "min_touches": 2,  # Minimum touches to form liquidity level
            "lookback_bars": 50,  # Bars to look back for liquidity
            "sweep_confirmation_bars": 2,  # Bars to confirm sweep
        }
        self._liquidity_levels: List[Dict[str, Any]] = []
        self._recent_highs: List[Dict[str, Any]] = []
        self._recent_lows: List[Dict[str, Any]] = []

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and update liquidity map."""
        if not self.enabled:
            return bar_state

        history = history or []

        # Update swing tracking
        self._update_swing_tracking(bar_state)

        # Detect equal highs/lows
        equal_highs = self._detect_equal_levels(self._recent_highs, "high")
        equal_lows = self._detect_equal_levels(self._recent_lows, "low")

        # Update liquidity levels
        self._update_liquidity_levels(equal_highs, equal_lows, bar_state)

        # Check for sweep
        sweep_info = self._detect_sweep(bar_state, history)

        # Find nearest liquidity
        current_price = bar_state.get("close", 0)
        nearest_info = self._find_nearest_liquidity(current_price)

        # Get from bar_state if available (from Ninja export)
        nearest_liq_high = bar_state.get("nearest_liquidity_high", nearest_info.get("nearest_high", 0))
        nearest_liq_low = bar_state.get("nearest_liquidity_low", nearest_info.get("nearest_low", 0))
        liq_high_type = bar_state.get("liquidity_high_type", nearest_info.get("high_type", ""))
        liq_low_type = bar_state.get("liquidity_low_type", nearest_info.get("low_type", ""))

        eqh_price = equal_highs[0]["price"] if equal_highs else 0
        eql_price = equal_lows[0]["price"] if equal_lows else 0
        eqh_touches = equal_highs[0]["touches"] if equal_highs else 0
        eql_touches = equal_lows[0]["touches"] if equal_lows else 0

        return {
            **bar_state,
            # Liquidity levels (use existing or calculated)
            "nearest_liquidity_high": nearest_liq_high,
            "nearest_liquidity_low": nearest_liq_low,
            "liquidity_high_type": liq_high_type,
            "liquidity_low_type": liq_low_type,
            # Sweep detection
            "liquidity_sweep_detected": sweep_info["detected"],
            "liquidity_sweep_type": sweep_info["type"],
            "liquidity_sweep_level": round(sweep_info["level"], 5),
            "bars_since_sweep": sweep_info["bars_ago"],
            # Equal level counts
            "equal_highs_count": len(equal_highs),
            "equal_lows_count": len(equal_lows),
            "eqh_price": eqh_price,
            "eql_price": eql_price,
            "eqh_touches": eqh_touches,
            "eql_touches": eql_touches,
        }

    def _update_swing_tracking(self, bar_state: Dict[str, Any]) -> None:
        """Track recent swing highs and lows."""
        bar_index = bar_state.get("bar_index", 0)
        high = bar_state.get("high", 0)
        low = bar_state.get("low", 0)
        tick_size = bar_state.get("tick_size")

        is_swing_high = bar_state.get("is_swing_high", False)
        is_swing_low = bar_state.get("is_swing_low", False)

        if is_swing_high:
            self._recent_highs.append({"bar_index": bar_index, "price": high, "tick_size": tick_size})

        if is_swing_low:
            self._recent_lows.append({"bar_index": bar_index, "price": low, "tick_size": tick_size})

        # Cleanup old data
        max_size = self.config["lookback_bars"]
        if len(self._recent_highs) > max_size:
            self._recent_highs = self._recent_highs[-max_size:]
        if len(self._recent_lows) > max_size:
            self._recent_lows = self._recent_lows[-max_size:]

    def _detect_equal_levels(
        self, swings: List[Dict[str, Any]], level_type: str
    ) -> List[Dict[str, Any]]:
        """Detect equal highs or lows."""
        equal_levels = []

        if len(swings) < 2:
            return equal_levels

        prices = [s["price"] for s in swings[-10:] if s.get("price")]
        if not prices:
            return equal_levels

        # Adaptive tolerance: use tick_size if present, else ratio
        tick_size = None
        for s in swings:
            if s.get("tick_size"):
                tick_size = s["tick_size"]
                break
        if tick_size:
            tolerance_abs = tick_size * 2  # within 2 ticks
        else:
            tolerance_abs = None
        tolerance_ratio = self.config["equal_level_tolerance"]

        for i, price in enumerate(prices):
            touches = 1
            for j, other_price in enumerate(prices):
                if i == j:
                    continue
                price_diff = abs(price - other_price)
                within_tick = tolerance_abs is not None and price_diff <= tolerance_abs
                relative_diff = price_diff / price if price > 0 else float("inf")
                within_ratio = relative_diff <= tolerance_ratio
                if within_tick or within_ratio:
                    touches += 1

            if touches >= self.config["min_touches"]:
                equal_levels.append({
                    "price": price,
                    "touches": touches,
                    "type": f"equal_{level_type}s",
                    "tick_size_used": tick_size,
                })

        # Deduplicate
        seen_prices = set()
        unique_levels = []
        for level in equal_levels:
            price_key = round(level["price"], 5)
            if price_key not in seen_prices:
                seen_prices.add(price_key)
                unique_levels.append(level)

        return unique_levels

    def _update_liquidity_levels(
        self,
        equal_highs: List[Dict[str, Any]],
        equal_lows: List[Dict[str, Any]],
        bar_state: Dict[str, Any],
    ) -> None:
        """Update internal liquidity level tracking."""
        bar_index = bar_state.get("bar_index", 0)

        # Add equal levels
        for level in equal_highs:
            self._liquidity_levels.append({
                "price": level["price"],
                "type": "equal_highs",
                "direction": "above",
                "bar_index": bar_index,
                "swept": False,
            })

        for level in equal_lows:
            self._liquidity_levels.append({
                "price": level["price"],
                "type": "equal_lows",
                "direction": "below",
                "bar_index": bar_index,
                "swept": False,
            })

        # Add swing levels
        swing_high = bar_state.get("last_swing_high")
        swing_low = bar_state.get("last_swing_low")

        if swing_high and not any(
            abs(l["price"] - swing_high) < 0.0001 for l in self._liquidity_levels
        ):
            self._liquidity_levels.append({
                "price": swing_high,
                "type": "swing",
                "direction": "above",
                "bar_index": bar_index,
                "swept": False,
            })

        if swing_low and not any(
            abs(l["price"] - swing_low) < 0.0001 for l in self._liquidity_levels
        ):
            self._liquidity_levels.append({
                "price": swing_low,
                "type": "swing",
                "direction": "below",
                "bar_index": bar_index,
                "swept": False,
            })

        # Cleanup old levels
        max_levels = 50
        if len(self._liquidity_levels) > max_levels:
            # Keep most recent and unswept levels
            unswept = [l for l in self._liquidity_levels if not l["swept"]]
            self._liquidity_levels = unswept[-max_levels:]

    def _detect_sweep(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect liquidity sweep."""
        default = {
            "detected": False,
            "type": "none",
            "level": 0.0,
            "bars_ago": 0,
        }

        bar_high = bar_state.get("high", 0)
        bar_low = bar_state.get("low", 0)
        bar_close = bar_state.get("close", 0)
        bar_index = bar_state.get("bar_index", 0)

        for level in self._liquidity_levels:
            if level["swept"]:
                continue

            price = level["price"]
            level_type = level["type"]

            # Check for sweep above (liquidity above current price)
            if level["direction"] == "above":
                if bar_high > price and bar_close < price:
                    # Swept above and closed below = bearish sweep
                    level["swept"] = True
                    return {
                        "detected": True,
                        "type": f"sweep_above_{level_type}",
                        "level": price,
                        "bars_ago": bar_index - level.get("bar_index", bar_index),
                    }

            # Check for sweep below
            elif level["direction"] == "below":
                if bar_low < price and bar_close > price:
                    # Swept below and closed above = bullish sweep
                    level["swept"] = True
                    return {
                        "detected": True,
                        "type": f"sweep_below_{level_type}",
                        "level": price,
                        "bars_ago": bar_index - level.get("bar_index", bar_index),
                    }

        return default

    def _find_nearest_liquidity(self, current_price: float) -> Dict[str, Any]:
        """Find nearest unswept liquidity levels."""
        if not self._liquidity_levels or current_price == 0:
            return {
                "nearest_high": 0,
                "nearest_low": 0,
                "high_type": "",
                "low_type": "",
            }

        unswept = [l for l in self._liquidity_levels if not l["swept"]]

        # Find nearest above
        above_levels = [l for l in unswept if l["price"] > current_price]
        nearest_above = min(above_levels, key=lambda x: x["price"]) if above_levels else None

        # Find nearest below
        below_levels = [l for l in unswept if l["price"] < current_price]
        nearest_below = max(below_levels, key=lambda x: x["price"]) if below_levels else None

        return {
            "nearest_high": nearest_above["price"] if nearest_above else 0,
            "nearest_low": nearest_below["price"] if nearest_below else 0,
            "high_type": nearest_above["type"] if nearest_above else "",
            "low_type": nearest_below["type"] if nearest_below else "",
        }
