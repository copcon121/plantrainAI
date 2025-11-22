"""
Fix #03: Structure Context.
Implement per docs/MODULE_FIX03_STRUCTURE_CONTEXT.md.

Tags FVG with structure context:
- Expansion (impulsive leg after BOS/CHoCH)
- Retracement (corrective leg)
- Continuation (post-confirmation)
"""
from typing import Any, Dict, List, Optional

from processor.core.module_base import BaseModule


class StructureContextModule(BaseModule):
    """Structure Context Analysis Module."""

    name = "fix03_structure_context"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            "structure_lookback": 50,
            "expansion_max_bars": 10,
            "expansion_multiplier": 1.2,
            "continuation_multiplier": 1.0,
            "retracement_multiplier": 0.8,
            "unclear_multiplier": 0.7,
            "pullback_volume_ratio": 0.8,
        }

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and calculate structure context."""
        if not self.enabled:
            return bar_state

        history = history or []

        # Only process if FVG detected
        if not bar_state.get("fvg_detected", False):
            return {**bar_state, **self._default_output()}

        context = self._detect_structure_context(bar_state, history)
        return {**bar_state, **context}

    def _detect_structure_context(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Determine structure context for FVG."""
        current_bar = bar_state.get("bar_index", 0)
        fvg_bar = bar_state.get(
            "fvg_creation_bar_index",
            bar_state.get("fvg_bar_index", current_bar),
        )
        fvg_type = bar_state.get("fvg_type", "")

        # Check for recent structure breaks
        recent_choch = self._find_recent_structure(bar_state, history, "choch")
        recent_bos = self._find_recent_structure(bar_state, history, "bos")

        # Analyze swing pattern
        swing_pattern = self._analyze_swing_pattern(bar_state, history)

        # EXPANSION: FVG in leg that broke structure
        if recent_choch and self._is_expansion(bar_state, recent_choch, history):
            return {
                "structure_context": "expansion",
                "structure_dir": 1 if recent_choch.get("type") == "bullish" else -1,
                "structure_context_score": self.config["expansion_multiplier"],
                "fvg_in_impulsive_leg": True,
                "bars_since_structure_break": current_bar - recent_choch.get("bar_index", 0),
                "structure_break_type": "CHoCH",
                "trend_established": False,
            }

        if recent_bos and self._is_expansion(bar_state, recent_bos, history):
            return {
                "structure_context": "expansion",
                "structure_dir": 1 if recent_bos.get("type") == "bullish" else -1,
                "structure_context_score": self.config["expansion_multiplier"],
                "fvg_in_impulsive_leg": True,
                "bars_since_structure_break": current_bar - recent_bos.get("bar_index", 0),
                "structure_break_type": "BOS",
                "trend_established": True,
            }

        # CONTINUATION: Trend established
        if swing_pattern.get("trend_established", False):
            trend_dir = swing_pattern.get("direction", 0)
            fvg_dir = 1 if fvg_type == "bullish" else -1

            if fvg_dir == trend_dir:
                return {
                    "structure_context": "continuation",
                    "structure_dir": trend_dir,
                    "structure_context_score": self.config["continuation_multiplier"],
                    "fvg_in_impulsive_leg": False,
                    "bars_since_structure_break": swing_pattern.get("bars_since_confirmation", 0),
                    "structure_break_type": "None",
                    "trend_established": True,
                }

        # RETRACEMENT: FVG in pullback
        if self._is_in_pullback(bar_state, history):
            return {
                "structure_context": "retracement",
                "structure_dir": swing_pattern.get("direction", 0),
                "structure_context_score": self.config["retracement_multiplier"],
                "fvg_in_impulsive_leg": False,
                "bars_since_structure_break": 0,
                "structure_break_type": "None",
                "trend_established": swing_pattern.get("trend_established", False),
            }

        # UNCLEAR
        return {
            "structure_context": "unclear",
            "structure_dir": 0,
            "structure_context_score": self.config["unclear_multiplier"],
            "fvg_in_impulsive_leg": False,
            "bars_since_structure_break": 0,
            "structure_break_type": "None",
            "trend_established": False,
        }

    def _find_recent_structure(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]], break_type: str
    ) -> Optional[Dict[str, Any]]:
        """Find recent structure break (CHoCH or BOS)."""
        detected_key = f"{break_type}_detected"
        type_key = f"{break_type}_type"
        bars_ago_key = f"{break_type}_bars_ago"

        if bar_state.get(detected_key, False):
            return {
                "bar_index": bar_state.get("bar_index", 0),
                "type": bar_state.get(type_key, ""),
            }

        bars_ago = bar_state.get(bars_ago_key, 0)
        if bars_ago > 0 and bars_ago <= self.config["expansion_max_bars"]:
            current_bar = bar_state.get("bar_index", 0)
            return {
                "bar_index": current_bar - bars_ago,
                "type": bar_state.get(type_key, bar_state.get("current_trend", "")),
            }

        return None

    def _is_expansion(
        self,
        bar_state: Dict[str, Any],
        structure_break: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> bool:
        """Check if FVG is in expansion leg (break leg)."""
        fvg_bar = bar_state.get(
            "fvg_creation_bar_index",
            bar_state.get("fvg_bar_index", bar_state.get("bar_index", 0)),
        )
        break_bar = structure_break.get("bar_index", 0)
        break_type = structure_break.get("type", "")
        fvg_type = bar_state.get("fvg_type", "")

        # FVG must be within expansion window of break
        leg_start = break_bar - self.config["expansion_max_bars"]
        leg_end = break_bar + 2

        if not (leg_start <= fvg_bar <= leg_end):
            return False

        # FVG direction must match break direction
        if break_type == "bullish" and fvg_type != "bullish":
            return False
        if break_type == "bearish" and fvg_type != "bearish":
            return False

        return True

    def _analyze_swing_pattern(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze swing pattern for trend establishment."""
        current_trend = bar_state.get("current_trend", "")

        if current_trend == "bullish":
            return {
                "trend_established": True,
                "direction": 1,
                "pattern": "HH-HL",
                "bars_since_confirmation": 0,
            }
        elif current_trend == "bearish":
            return {
                "trend_established": True,
                "direction": -1,
                "pattern": "LH-LL",
                "bars_since_confirmation": 0,
            }

        return {"trend_established": False, "direction": 0}

    def _is_in_pullback(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> bool:
        """Detect if current price action is in pullback."""
        if len(history) < 10:
            return False

        fvg_type = bar_state.get("fvg_type", "")
        current_trend = bar_state.get("current_trend", "")

        # Pullback = FVG counter to trend
        if current_trend == "bullish" and fvg_type == "bearish":
            return True
        if current_trend == "bearish" and fvg_type == "bullish":
            return True

        return False

    def _default_output(self) -> Dict[str, Any]:
        """Default output when no FVG."""
        return {
            "structure_context": "none",
            "structure_dir": 0,
            "structure_context_score": 1.0,
            "fvg_in_impulsive_leg": False,
            "bars_since_structure_break": 0,
            "structure_break_type": "None",
            "trend_established": False,
        }
