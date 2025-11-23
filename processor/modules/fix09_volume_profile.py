"""
Fix #09: Volume Profile.
Implement per docs/MODULE_FIX09_VOLUME_PROFILE.md.

Computes session-based volume profile levels:
- VAH (Value Area High)
- VAL (Value Area Low)
- POC (Point of Control)
"""
from typing import Any, Dict, List

from processor.core.module_base import BaseModule


class VolumeProfileModule(BaseModule):
    """Volume Profile Module."""

    name = "fix09_volume_profile"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "value_area_pct": 0.70,  # 70% of volume
            "price_bins": 50,  # Number of price bins
            "max_session_bars": 2000,  # Safety cap to prevent memory issues
        }
        self._session_data: List[Dict[str, Any]] = []
        self._current_session: str | None = None

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and calculate volume profile levels."""
        if not self.enabled:
            return bar_state

        history = history or []

        # Check for session change
        current_session = bar_state.get("session", "unknown")
        if current_session != self._current_session:
            self._session_data = []  # Reset profile for new session
            self._current_session = current_session

        # Accumulate session data
        self._update_session_data(bar_state)

        # Calculate volume profile
        vp_info = self._calculate_volume_profile()

        # Determine price position relative to VP levels
        current_close = bar_state.get("close", 0)
        position_info = self._get_price_position(current_close, vp_info)

        return {
            **bar_state,
            "vp_session_vah": round(vp_info["vah"], 5),
            "vp_session_val": round(vp_info["val"], 5),
            "vp_session_poc": round(vp_info["poc"], 5),
            "vp_in_value_area": position_info["in_va"],
            "vp_position": position_info["position"],
            "vp_distance_to_poc": round(position_info["distance_to_poc"], 5),
            "vp_distance_to_vah": round(position_info["distance_to_vah"], 5),
            "vp_distance_to_val": round(position_info["distance_to_val"], 5),
        }

    def _update_session_data(self, bar_state: Dict[str, Any]) -> None:
        """Update session data for volume profile calculation."""
        bar_data = {
            "high": bar_state.get("high", 0),
            "low": bar_state.get("low", 0),
            "close": bar_state.get("close", 0),
            "volume": bar_state.get("volume", 0),
            "tick_size": bar_state.get("tick_size"),
        }
        self._session_data.append(bar_data)

        # Safety cap only (not sliding window)
        if len(self._session_data) > self.config["max_session_bars"]:
            self._session_data.pop(0)

    def _calculate_volume_profile(self) -> Dict[str, Any]:
        """Calculate VAH, VAL, POC from session data."""
        if len(self._session_data) < 5:
            return {"vah": 0.0, "val": 0.0, "poc": 0.0}

        # Find price range
        all_highs = [b["high"] for b in self._session_data if b["high"] > 0]
        all_lows = [b["low"] for b in self._session_data if b["low"] > 0]

        if not all_highs or not all_lows:
            return {"vah": 0.0, "val": 0.0, "poc": 0.0}

        price_high = max(all_highs)
        price_low = min(all_lows)
        price_range = price_high - price_low

        if price_range <= 0:
            return {"vah": price_high, "val": price_low, "poc": (price_high + price_low) / 2}

        # Create price bins (tick-aware if provided)
        tick_size = next((b.get("tick_size") for b in self._session_data if b.get("tick_size")), None)
        base_bin = price_range / self.config["price_bins"]
        bin_size = max(base_bin, tick_size) if tick_size else base_bin
        num_bins = max(int(price_range / bin_size), 1)
        bin_size = price_range / num_bins if num_bins > 0 else price_range
        bins = [0.0] * num_bins

        # Distribute volume to bins
        total_volume = 0
        for bar in self._session_data:
            vol = bar["volume"]
            if vol <= 0:
                continue

            # Distribute bar volume across its range
            bar_high = bar["high"]
            bar_low = bar["low"]

            for i in range(num_bins):
                bin_low = price_low + (i * bin_size)
                bin_high = bin_low + bin_size

                # Check overlap between bar range and bin
                overlap_low = max(bar_low, bin_low)
                overlap_high = min(bar_high, bin_high)

                if overlap_high > overlap_low:
                    bar_range = bar_high - bar_low
                    if bar_range > 0:
                        overlap_pct = (overlap_high - overlap_low) / bar_range
                        bins[i] += vol * overlap_pct
                        total_volume += vol * overlap_pct

        if total_volume == 0:
            return {"vah": price_high, "val": price_low, "poc": (price_high + price_low) / 2}

        # Find POC (bin with highest volume)
        max_vol = max(bins)
        poc_bin = bins.index(max_vol)
        poc = price_low + (poc_bin + 0.5) * bin_size

        # Find Value Area (70% of volume) using top-volume bins around POC
        target_vol = total_volume * self.config["value_area_pct"]
        included_indices = set([poc_bin])
        accumulated_vol = bins[poc_bin]

        bin_order = sorted(
            [(i, v) for i, v in enumerate(bins)],
            key=lambda x: x[1],
            reverse=True,
        )
        for idx, vol in bin_order:
            if accumulated_vol >= target_vol:
                break
            if idx in included_indices:
                continue
            included_indices.add(idx)
            accumulated_vol += vol

        va_low_bin = min(included_indices)
        va_high_bin = max(included_indices)

        vah = price_low + (va_high_bin + 1) * bin_size
        val = price_low + va_low_bin * bin_size

        return {"vah": vah, "val": val, "poc": poc}

    def _get_price_position(
        self, current_price: float, vp_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine price position relative to VP levels."""
        vah = vp_info["vah"]
        val = vp_info["val"]
        poc = vp_info["poc"]

        if vah == 0 or val == 0:
            return {
                "in_va": 0,
                "position": "unknown",
                "distance_to_poc": 0.0,
                "distance_to_vah": 0.0,
                "distance_to_val": 0.0,
            }

        # Check if in value area
        in_va = 1 if val <= current_price <= vah else 0

        # Determine position
        if current_price > vah:
            position = "above_va"
        elif current_price < val:
            position = "below_va"
        elif current_price > poc:
            position = "upper_va"
        else:
            position = "lower_va"

        return {
            "in_va": in_va,
            "position": position,
            "distance_to_poc": current_price - poc,
            "distance_to_vah": current_price - vah,
            "distance_to_val": current_price - val,
        }
