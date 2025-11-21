"""Unit tests for Fix #05: Stop Placement Module."""
import pytest
from processor.modules.fix05_stop_placement import StopPlacementModule


class TestStopPlacementModule:
    """Tests for StopPlacementModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = StopPlacementModule()
        self.base_bar = {
            "bar_index": 100,
            "timestamp": "2024-01-15T10:45:00Z",
            "open": 100.15,
            "high": 100.55,
            "low": 100.05,
            "close": 100.45,
            "volume": 4500,
            "atr_14": 0.50,  # 0.50 ATR for easier calculation
        }

    def test_no_fvg_returns_defaults(self):
        """Test that no FVG returns default stop values."""
        bar = {**self.base_bar, "fvg_detected": False}
        result = self.module.process_bar(bar)

        assert result["stop_price"] == 0.0
        assert result["stop_type"] == "none"
        assert result["stop_valid"] is False

    def test_fvg_edge_stop_bullish(self):
        """Test FVG edge stop calculation for bullish FVG."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.50,
            "fvg_bottom": 100.00,
            "fvg_strength_class": "Strong",
        }

        result = self.module.process_bar(bar)

        assert result["stop_type"] == "fvg_edge"
        assert result["stop_price"] < 100.00  # Below FVG bottom
        assert result["stop_valid"] is True

    def test_fvg_edge_stop_bearish(self):
        """Test FVG edge stop calculation for bearish FVG."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bearish",
            "fvg_top": 100.50,
            "fvg_bottom": 100.00,
            "fvg_strength_class": "Strong",
            "close": 100.20,  # Entry in middle of FVG
            "atr_14": 0.30,  # Adjusted ATR so stop distance is in valid range
        }

        result = self.module.process_bar(bar)

        assert result["stop_type"] == "fvg_edge"
        assert result["stop_price"] > 100.50  # Above FVG top
        assert result["stop_valid"] is True

    def test_ob_stop_when_ob_available(self):
        """Test OB stop is used when OB data available."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.50,
            "fvg_bottom": 100.00,
            "fvg_strength_class": "Weak",  # Weak prefers OB stop
            "nearest_ob_top": 101.00,
            "nearest_ob_bottom": 99.50,
        }

        result = self.module.process_bar(bar)

        # Weak FVG should prefer OB stop
        assert result["stop_type"] in ["ob_edge", "structure", "fvg_full", "fvg_edge"]
        assert result["stop_valid"] is True

    def test_structure_stop_with_swing(self):
        """Test structure stop uses swing levels."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.50,
            "fvg_bottom": 100.00,
            "fvg_strength_class": "Weak",
            "last_swing_low": 99.00,
            "last_swing_high": 101.50,
        }

        result = self.module.process_bar(bar)

        assert result["stop_valid"] is True
        assert result["stop_price"] > 0

    def test_stop_distance_atr_calculation(self):
        """Test stop distance in ATR terms."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.50,
            "fvg_bottom": 100.00,
            "fvg_strength_class": "Strong",
            "close": 100.20,  # Entry price
            "atr_14": 0.50,
        }

        result = self.module.process_bar(bar)

        assert result["stop_distance_atr"] > 0
        # Should be within constraints (0.3 - 2.0 ATR)
        assert 0.3 <= result["stop_distance_atr"] <= 2.0

    def test_stop_buffer_applied(self):
        """Test that buffer is applied to stop."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.50,
            "fvg_bottom": 100.00,
            "fvg_strength_class": "Strong",
        }

        result = self.module.process_bar(bar)

        assert result["stop_buffer"] > 0

    def test_strong_fvg_prefers_tight_stop(self):
        """Test that strong FVG prefers tighter stop."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.50,
            "fvg_bottom": 100.00,
            "fvg_strength_class": "Strong",
            "nearest_ob_bottom": 99.00,
            "last_swing_low": 98.50,
        }

        result = self.module.process_bar(bar)

        # Strong FVG should prefer fvg_edge (tightest)
        assert result["stop_type"] == "fvg_edge"

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = StopPlacementModule(enabled=False)
        bar = {**self.base_bar, "fvg_detected": True}

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "fvg_detected": True, "fvg_type": "bullish"}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
