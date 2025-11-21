"""Unit tests for Fix #03: Structure Context Module."""
import pytest
from processor.modules.fix03_structure_context import StructureContextModule


class TestStructureContextModule:
    """Tests for StructureContextModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = StructureContextModule()
        self.base_bar = {
            "bar_index": 100,
            "timestamp": "2024-01-15T10:45:00Z",
            "open": 100.15,
            "high": 100.55,
            "low": 100.05,
            "close": 100.45,
            "volume": 4500,
            "atr_14": 0.22,
        }

    def test_no_fvg_returns_defaults(self):
        """Test that no FVG returns default context."""
        bar = {**self.base_bar, "fvg_detected": False}
        result = self.module.process_bar(bar)

        assert result["structure_context"] == "none"
        assert result["structure_dir"] == 0

    def test_expansion_context_after_choch(self):
        """Test expansion context detected after CHoCH."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "choch_detected": True,
            "choch_type": "bullish",
            "choch_bars_ago": 0,
            "fvg_creation_bar_index": 100,
        }

        result = self.module.process_bar(bar)

        assert result["structure_context"] == "expansion"
        assert result["structure_dir"] == 1
        assert result["fvg_in_impulsive_leg"] is True
        assert result["structure_break_type"] == "CHoCH"

    def test_expansion_context_after_bos(self):
        """Test expansion context detected after BOS."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "bos_detected": True,
            "bos_type": "bullish",
            "bos_bars_ago": 0,
            "fvg_creation_bar_index": 100,
        }

        result = self.module.process_bar(bar)

        assert result["structure_context"] == "expansion"
        assert result["structure_break_type"] == "BOS"
        assert result["trend_established"] is True

    def test_continuation_context_with_trend(self):
        """Test continuation context when trend is established."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "current_trend": "bullish",
            "choch_detected": False,
            "bos_detected": False,
            "choch_bars_ago": 0,
            "bos_bars_ago": 0,
        }

        result = self.module.process_bar(bar)

        assert result["structure_context"] == "continuation"
        assert result["structure_dir"] == 1
        assert result["trend_established"] is True

    def test_retracement_context_counter_trend_fvg(self):
        """Test retracement context when FVG is counter to trend."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bearish",  # Counter to trend
            "current_trend": "bullish",
            "choch_detected": False,
            "bos_detected": False,
            "choch_bars_ago": 0,
            "bos_bars_ago": 0,
        }
        history = [self.base_bar.copy() for _ in range(15)]

        result = self.module.process_bar(bar, history)

        assert result["structure_context"] == "retracement"
        assert result["structure_context_score"] < 1.0

    def test_structure_context_multipliers(self):
        """Test that context multipliers are applied correctly."""
        # Expansion should have highest multiplier
        bar_expansion = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "choch_detected": True,
            "choch_type": "bullish",
        }

        result = self.module.process_bar(bar_expansion)

        assert result["structure_context_score"] >= 1.0

    def test_bearish_expansion(self):
        """Test bearish expansion context."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bearish",
            "choch_detected": True,
            "choch_type": "bearish",
            "choch_bars_ago": 0,
        }

        result = self.module.process_bar(bar)

        assert result["structure_context"] == "expansion"
        assert result["structure_dir"] == -1

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = StructureContextModule(enabled=False)
        bar = {**self.base_bar, "fvg_detected": True}

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "fvg_detected": True, "fvg_type": "bullish"}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
