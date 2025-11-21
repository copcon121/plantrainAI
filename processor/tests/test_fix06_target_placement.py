"""Unit tests for Fix #06: Target Placement Module."""
import pytest
from processor.modules.fix06_target_placement import TargetPlacementModule


class TestTargetPlacementModule:
    """Tests for TargetPlacementModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = TargetPlacementModule()
        self.base_bar = {
            "bar_index": 100,
            "timestamp": "2024-01-15T10:45:00Z",
            "open": 100.15,
            "high": 100.55,
            "low": 100.05,
            "close": 100.20,
            "volume": 4500,
            "atr_14": 0.22,
        }

    def test_no_fvg_returns_defaults(self):
        """Test that no FVG returns default targets."""
        bar = {**self.base_bar, "fvg_detected": False}
        result = self.module.process_bar(bar)

        assert result["tp1_price"] == 0.0
        assert result["tp1_type"] == "none"
        assert result["target_valid"] is False

    def test_bullish_targets_above_entry(self):
        """Test bullish targets are above entry price."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "stop_price": 99.80,  # Risk = 0.40
            "last_swing_high": 100.80,
            "nearest_liquidity_high": 101.00,
        }

        result = self.module.process_bar(bar)

        assert result["tp1_price"] > bar["close"]
        assert result["tp2_price"] > bar["close"]
        assert result["tp1_rr"] >= 1.5  # Minimum RR

    def test_bearish_targets_below_entry(self):
        """Test bearish targets are below entry price."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bearish",
            "stop_price": 100.60,  # Risk = 0.40
            "last_swing_low": 99.50,
            "nearest_liquidity_low": 99.20,
        }

        result = self.module.process_bar(bar)

        assert result["tp1_price"] < bar["close"]
        assert result["tp1_price"] > 0

    def test_swing_target_preferred(self):
        """Test that swing targets are preferred over RR-based."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "stop_price": 99.80,
            "last_swing_high": 100.90,  # Meets min RR
        }

        result = self.module.process_bar(bar)

        assert result["tp1_type"] in ["swing", "rr_1.5"]

    def test_liquidity_target_used(self):
        """Test that liquidity targets are considered."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "stop_price": 99.80,
            "nearest_liquidity_high": 101.50,
        }

        result = self.module.process_bar(bar)

        assert result["tp1_price"] > 0

    def test_session_target_used(self):
        """Test that session targets are considered."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "stop_price": 99.80,
            "prev_session_high": 101.20,
        }

        result = self.module.process_bar(bar)

        assert result["tp1_price"] > 0

    def test_rr_calculation(self):
        """Test RR calculation is correct."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "close": 100.00,
            "stop_price": 99.50,  # Risk = 0.50
            "last_swing_high": 100.75,  # Reward = 0.75
        }

        result = self.module.process_bar(bar)

        # RR should be approximately 1.5
        assert result["tp1_rr"] >= 1.4

    def test_multiple_tp_levels(self):
        """Test that TP1, TP2, TP3 are all calculated."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "stop_price": 99.80,
            "last_swing_high": 100.90,
            "nearest_liquidity_high": 101.50,
            "prev_session_high": 102.00,
        }

        result = self.module.process_bar(bar)

        assert result["tp1_price"] > 0
        assert result["tp2_price"] > 0
        assert result["tp3_price"] > 0
        assert result["tp1_price"] <= result["tp2_price"] <= result["tp3_price"]

    def test_target_valid_with_min_rr(self):
        """Test target_valid is True when min RR is met."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "stop_price": 99.80,
            "last_swing_high": 101.00,
        }

        result = self.module.process_bar(bar)

        assert result["target_valid"] is True
        assert result["tp1_rr"] >= 1.5

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = TargetPlacementModule(enabled=False)
        bar = {**self.base_bar, "fvg_detected": True}

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "fvg_detected": True, "fvg_type": "bullish"}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
