"""Unit tests for Fix #01: OB Quality Module."""
import pytest
from processor.modules.fix01_ob_quality import OBQualityModule


class TestOBQualityModule:
    """Tests for OBQualityModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = OBQualityModule()
        self.base_bar = {
            "bar_index": 100,
            "timestamp": "2024-01-15T10:45:00Z",
            "open": 100.00,
            "high": 100.50,
            "low": 99.50,
            "close": 100.30,
            "volume": 5000,
            "buy_volume": 3000,
            "sell_volume": 2000,
            "delta": 1000,
            "cumulative_delta": 15000,
            "atr_14": 0.25,
        }

    def test_no_ob_detected_returns_defaults(self):
        """Test that no OB detected returns default scores."""
        bar = {**self.base_bar, "ob_detected": False}
        result = self.module.process_bar(bar)

        assert result["ob_strength_score"] == 0.0
        assert result["ob_volume_factor"] == 0.0
        assert result["ob_liquidity_sweep"] is False

    def test_ob_with_valid_data_returns_scores(self):
        """Test OB with valid data returns calculated scores."""
        bar = {
            **self.base_bar,
            "ob_detected": True,
            "ob_high": 100.50,
            "ob_low": 100.00,
            "ob_direction": "bull",
            "ob_volume": 6000,
            "swing_after_price": 101.50,
        }
        history = [{"volume": 4000} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        assert "ob_strength_score" in result
        assert 0.0 <= result["ob_strength_score"] <= 1.0
        assert result["ob_volume_factor"] > 0
        assert "ob_displacement_rr" in result

    def test_displacement_rr_calculation_bullish(self):
        """Test displacement RR for bullish OB."""
        bar = {
            **self.base_bar,
            "ob_detected": True,
            "ob_high": 100.50,
            "ob_low": 100.00,
            "ob_direction": "bull",
            "swing_after_price": 101.50,
        }

        result = self.module.process_bar(bar)

        # Displacement should be positive for bullish move
        assert result["ob_displacement_rr"] > 0

    def test_displacement_rr_calculation_bearish(self):
        """Test displacement RR for bearish OB."""
        bar = {
            **self.base_bar,
            "ob_detected": True,
            "ob_high": 100.50,
            "ob_low": 100.00,
            "ob_direction": "bear",
            "swing_after_price": 99.00,
        }

        result = self.module.process_bar(bar)

        assert result["ob_displacement_rr"] > 0

    def test_volume_factor_above_median(self):
        """Test volume factor when OB volume > median."""
        bar = {
            **self.base_bar,
            "ob_detected": True,
            "ob_high": 100.50,
            "ob_low": 100.00,
            "ob_direction": "bull",
            "ob_volume": 10000,
        }
        history = [{"volume": 4000} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        assert result["ob_volume_factor"] > 1.0

    def test_delta_imbalance_aligned(self):
        """Test delta imbalance when aligned with direction."""
        bar = {
            **self.base_bar,
            "ob_detected": True,
            "ob_high": 100.50,
            "ob_low": 100.00,
            "ob_direction": "bull",
            "buy_volume": 4000,
            "sell_volume": 1000,
        }

        result = self.module.process_bar(bar)

        # Strong buy imbalance should give high score
        assert result["ob_delta_imbalance"] > 0.5

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = OBQualityModule(enabled=False)
        bar = {**self.base_bar, "ob_detected": True}

        result = module.process_bar(bar)

        # Should return input unchanged (no new keys added)
        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "ob_detected": True}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
