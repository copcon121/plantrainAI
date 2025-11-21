"""Unit tests for Fix #08: Volume Divergence Module."""
import pytest
from processor.modules.fix08_volume_divergence import VolumeDivergenceModule


class TestVolumeDivergenceModule:
    """Tests for VolumeDivergenceModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = VolumeDivergenceModule()
        self.base_bar = {
            "bar_index": 100,
            "timestamp": "2024-01-15T10:45:00Z",
            "open": 100.15,
            "high": 100.55,
            "low": 100.05,
            "close": 100.45,
            "volume": 4500,
            "delta": 1000,
            "cumulative_delta": 15000,
            "atr_14": 0.22,
        }

    def test_no_swing_returns_no_divergence(self):
        """Test that non-swing bars return no divergence."""
        bar = {
            **self.base_bar,
            "is_swing_high": False,
            "is_swing_low": False,
        }

        result = self.module.process_bar(bar)

        assert result["divergence_detected"] is False
        assert result["divergence_type"] == "none"

    def test_bullish_divergence_at_swing_low(self):
        """Test bullish divergence detection at swing low."""
        # First, add a previous swing low to history
        prev_swing = {
            **self.base_bar,
            "bar_index": 90,
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.50,  # Higher low
            "delta": 500,  # Lower delta
        }

        # Process previous swing first
        self.module.process_bar(prev_swing)

        # Current swing low with bullish divergence
        current = {
            **self.base_bar,
            "bar_index": 100,
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.00,  # Lower low
            "delta": 1500,  # Higher delta - bullish divergence
        }

        result = self.module.process_bar(current)

        assert result["divergence_detected"] is True
        assert result["divergence_type"] == "bullish"

    def test_bearish_divergence_at_swing_high(self):
        """Test bearish divergence detection at swing high."""
        # Add previous swing high
        prev_swing = {
            **self.base_bar,
            "bar_index": 90,
            "is_swing_high": True,
            "is_swing_low": False,
            "high": 100.00,  # Lower high
            "delta": 1500,  # Higher delta
        }

        self.module.process_bar(prev_swing)

        # Current swing high with bearish divergence
        current = {
            **self.base_bar,
            "bar_index": 100,
            "is_swing_high": True,
            "is_swing_low": False,
            "high": 101.00,  # Higher high
            "delta": 500,  # Lower delta - bearish divergence
        }

        result = self.module.process_bar(current)

        assert result["divergence_detected"] is True
        assert result["divergence_type"] == "bearish"

    def test_no_divergence_when_aligned(self):
        """Test no divergence when price and delta aligned."""
        prev_swing = {
            **self.base_bar,
            "bar_index": 90,
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.50,
            "delta": 500,
        }

        self.module.process_bar(prev_swing)

        current = {
            **self.base_bar,
            "bar_index": 100,
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.00,  # Lower low
            "delta": 400,  # Also lower delta - no divergence
        }

        result = self.module.process_bar(current)

        assert result["divergence_detected"] is False

    def test_divergence_strength_calculation(self):
        """Test divergence strength is between 0 and 1."""
        prev_swing = {
            **self.base_bar,
            "bar_index": 90,
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.50,
            "delta": 500,
        }

        self.module.process_bar(prev_swing)

        current = {
            **self.base_bar,
            "bar_index": 100,
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.00,
            "delta": 1500,
        }

        result = self.module.process_bar(current)

        if result["divergence_detected"]:
            assert 0.0 <= result["divergence_strength"] <= 1.0

    def test_min_swing_distance_respected(self):
        """Test minimum swing distance is respected."""
        prev_swing = {
            **self.base_bar,
            "bar_index": 98,  # Too close
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.50,
            "delta": 500,
        }

        self.module.process_bar(prev_swing)

        current = {
            **self.base_bar,
            "bar_index": 100,  # Only 2 bars difference
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.00,
            "delta": 1500,
        }

        result = self.module.process_bar(current)

        # Should not detect divergence due to min distance
        assert result["divergence_detected"] is False

    def test_bars_ago_calculation(self):
        """Test bars_ago is correctly calculated."""
        prev_swing = {
            **self.base_bar,
            "bar_index": 85,
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.50,
            "delta": 500,
        }

        self.module.process_bar(prev_swing)

        current = {
            **self.base_bar,
            "bar_index": 100,
            "is_swing_low": True,
            "is_swing_high": False,
            "low": 99.00,
            "delta": 1500,
        }

        result = self.module.process_bar(current)

        if result["divergence_detected"]:
            assert result["divergence_bars_ago"] == 15

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = VolumeDivergenceModule(enabled=False)
        bar = self.base_bar.copy()

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "is_swing_low": True}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
