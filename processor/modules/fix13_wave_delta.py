"""
Fix #13: Wave Delta (ZigZag leg delta accumulator).

Goal:
- Sum delta (and volume) for each swing-to-swing leg (LL→LH/HH, LH→LL/HL, etc.).
- Expose the active leg delta so you can gauge buy/sell pressure inside the current move.
- Keep the last and previous completed legs for quick comparison.
"""
from typing import Any, Dict, List, Optional

from processor.core.module_base import BaseModule


class WaveDeltaModule(BaseModule):
    """Track delta per swing leg using SMC zigzag swings."""

    name = "fix13_wave_delta"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "max_wave_history": 50,  # keep a bounded history of completed legs
        }

        self._last_swing: Optional[Dict[str, Any]] = None
        self._current_accum = self._new_accum()
        self._wave_history: List[Dict[str, Any]] = []
        self._last_symbol: str | None = None

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Accumulate delta along each swing leg and emit wave stats."""
        if not self.enabled:
            return bar_state

        # Reset state on symbol change
        symbol = bar_state.get("symbol")
        if symbol and symbol != self._last_symbol:
            self._reset_state()
            self._last_symbol = symbol

        # Accumulate into the active leg if we already have an anchor swing
        self._accumulate_active_leg(bar_state)

        wave_completed = None
        is_swing_high = bool(bar_state.get("is_swing_high", False))
        is_swing_low = bool(bar_state.get("is_swing_low", False))

        if is_swing_high or is_swing_low:
            swing_type = "high" if is_swing_high else "low"
            wave_completed = self._handle_swing_anchor(swing_type, bar_state)

        outputs = self._build_output(wave_completed)
        return {**bar_state, **outputs}

    # ---- internal helpers -------------------------------------------------
    def _new_accum(self) -> Dict[str, Any]:
        """Fresh accumulator for the active wave."""
        return {"delta": 0.0, "volume": 0.0, "buy_volume": 0.0, "sell_volume": 0.0, "bars": 0}

    def _reset_state(self) -> None:
        """Reset all state (used on symbol change)."""
        self._last_swing = None
        self._current_accum = self._new_accum()
        self._wave_history = []

    def _accumulate_active_leg(self, bar_state: Dict[str, Any]) -> None:
        """Add current bar's flow into the active leg."""
        if not self._last_swing:
            return

        self._current_accum["delta"] += float(bar_state.get("delta", 0.0) or 0.0)
        self._current_accum["volume"] += float(bar_state.get("volume", 0.0) or 0.0)
        self._current_accum["buy_volume"] += float(bar_state.get("buy_volume", 0.0) or 0.0)
        self._current_accum["sell_volume"] += float(bar_state.get("sell_volume", 0.0) or 0.0)
        self._current_accum["bars"] += 1

    def _handle_swing_anchor(self, swing_type: str, bar_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Finalize the current leg when a swing of the opposite type arrives,
        then start a new leg from this swing.
        """
        bar_index = bar_state.get("bar_index", 0)
        swing_price = self._get_swing_price(swing_type, bar_state)

        # No previous swing: set anchor and wait for the next one.
        if not self._last_swing:
            self._last_swing = {"type": swing_type, "bar_index": bar_index, "price": swing_price}
            self._current_accum = self._new_accum()
            return None

        # Same-type swing: reset anchor (avoid zero-length legs).
        if self._last_swing["type"] == swing_type:
            self._last_swing = {"type": swing_type, "bar_index": bar_index, "price": swing_price}
            self._current_accum = self._new_accum()
            return None

        # Opposite swing: finalize leg (SMC swing confirms late; we close leg on this signal bar,
        # but use the SMC swing price if provided to avoid using the current bar's high/low).
        direction = 1 if self._last_swing["type"] == "low" else -1
        wave = {
            "start_type": self._last_swing["type"],
            "end_type": swing_type,
            "direction": direction,
            "start_bar": self._last_swing.get("bar_index", 0),
            "end_bar": bar_index,
            "start_price": self._last_swing.get("price"),
            "end_price": swing_price,
            "delta": self._current_accum["delta"],
            "volume": self._current_accum["volume"],
            "buy_volume": self._current_accum["buy_volume"],
            "sell_volume": self._current_accum["sell_volume"],
            "bars": self._current_accum["bars"],
        }

        self._wave_history.append(wave)
        if len(self._wave_history) > self.config["max_wave_history"]:
            self._wave_history = self._wave_history[-self.config["max_wave_history"] :]

        # Start a new leg from the current swing
        self._last_swing = {"type": swing_type, "bar_index": bar_index, "price": swing_price}
        self._current_accum = self._new_accum()
        return wave

    def _build_output(self, wave_completed: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Flattened outputs for quick downstream use."""
        last_wave = self._wave_history[-1] if self._wave_history else None
        prev_wave = self._wave_history[-2] if len(self._wave_history) >= 2 else None

        active_dir = 0
        if self._last_swing:
            active_dir = 1 if self._last_swing["type"] == "low" else -1

        return {
            # Active leg (running)
            "active_wave_delta": round(self._current_accum["delta"], 3),
            "active_wave_direction": active_dir,
            "active_wave_bars": self._current_accum["bars"],
            "active_wave_volume": round(self._current_accum["volume"], 3),
        # Last completed leg
        "last_wave_delta": round(last_wave["delta"], 3) if last_wave else 0.0,
        "last_wave_direction": last_wave["direction"] if last_wave else 0,
        "last_wave_bars": last_wave["bars"] if last_wave else 0,
        "last_wave_volume": round(last_wave["volume"], 3) if last_wave else 0.0,
        "last_wave_buy_volume": round(last_wave["buy_volume"], 3) if last_wave else 0.0,
        "last_wave_sell_volume": round(last_wave["sell_volume"], 3) if last_wave else 0.0,
        "last_wave_start_bar": last_wave["start_bar"] if last_wave else -1,
        "last_wave_end_bar": last_wave["end_bar"] if last_wave else -1,
        "last_wave_start_price": last_wave.get("start_price") if last_wave else None,
        "last_wave_end_price": last_wave.get("end_price") if last_wave else None,
        # Previous leg (for quick comparison)
        "prev_wave_delta": round(prev_wave["delta"], 3) if prev_wave else 0.0,
        "prev_wave_direction": prev_wave["direction"] if prev_wave else 0,
        "prev_wave_end_price": prev_wave.get("end_price") if prev_wave else None,
        "wave_history_count": len(self._wave_history),
    }

    def _get_swing_price(self, swing_type: str, bar_state: Dict[str, Any]) -> Any:
        """
        Prefer SMC-provided swing prices (which may be earlier than the signal bar)
        to avoid using a later bar's high/low when confirmation is delayed.
        """
        if swing_type == "high":
            for key in ("last_swing_high", "swing_high_price", "prev_swing_high", "high"):
                val = bar_state.get(key)
                if val is not None:
                    return val
        else:
            for key in ("last_swing_low", "swing_low_price", "prev_swing_low", "low"):
                val = bar_state.get(key)
                if val is not None:
                    return val
        return None
