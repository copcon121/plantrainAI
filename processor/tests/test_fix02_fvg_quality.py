"""Unit tests for Fix #02: FVG Quality Module."""
import pytest
from processor.modules.fix02_fvg_quality import FVGQualityModule


class TestFVGQualityModule:
    """Tests for FVGQualityModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = FVGQualityModule()
        self.base_bar = {
            "bar_index": 100,
            "timestamp": "2024-01-15T10:45:00Z",
            "open": 100.15,
            "high": 100.55,
            "low": 100.05,
            "close": 100.45,
            "volume": 4500,
            "buy_volume": 2800,
            "sell_volume": 1700,
            "delta": 1100,
            "cumulative_delta": 18500,
            "atr_14": 0.22,
        }

    def test_no_fvg_detected_returns_defaults(self):
        """Test that no FVG detected returns default values."""
        bar = {**self.base_bar, "fvg_detected": False}
        result = self.module.process_bar(bar)

        assert result["fvg_strength_score"] == 0.0
        assert result["fvg_value_class"] == "None"
        assert result["fvg_context"] == "none"

    def test_bullish_fvg_strength_calculation(self):
        """Test FVG strength calculation for bullish FVG."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.40,
            "fvg_bottom": 100.20,
            "fvg_gap_size": 0.20,
            "fvg_creation_volume": 5200,
            "fvg_creation_delta": 1800,
        }
        history = [{"volume": 4000} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        assert 0.0 <= result["fvg_strength_score"] <= 1.0
        assert result["fvg_strength_class"] in ["Strong", "Medium", "Weak"]
        assert result["fvg_delta_alignment"] == 1  # Positive delta aligns with bullish

    def test_bearish_fvg_strength_calculation(self):
        """Test FVG strength calculation for bearish FVG."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bearish",
            "fvg_top": 100.40,
            "fvg_bottom": 100.20,
            "fvg_gap_size": 0.20,
            "fvg_creation_volume": 5200,
            "fvg_creation_delta": -1800,
            "delta": -1100,
        }

        result = self.module.process_bar(bar)

        assert 0.0 <= result["fvg_strength_score"] <= 1.0
        assert result["fvg_delta_alignment"] == 1  # Negative delta aligns with bearish

    def test_value_class_strong_fvg(self):
        """Test value class assignment for strong FVG."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.80,
            "fvg_bottom": 100.00,
            "fvg_gap_size": 0.80,  # Large gap
            "fvg_creation_volume": 12000,  # High volume
            "fvg_creation_delta": 4000,
            "buy_volume": 8000,
            "sell_volume": 2000,
        }
        history = [{"volume": 4000} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        # Large gap + high volume + strong delta should be Strong/A class
        assert result["fvg_value_class"] in ["A", "B"]

    def test_value_class_weak_fvg(self):
        """Test value class assignment for weak FVG."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.05,
            "fvg_bottom": 100.00,
            "fvg_gap_size": 0.05,  # Small gap
            "fvg_creation_volume": 2000,  # Low volume
            "fvg_creation_delta": 100,
        }
        history = [{"volume": 4000} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        # Small gap + low volume = Weak/C class
        assert result["fvg_strength_class"] == "Weak"
        assert result["fvg_value_class"] == "C"

    def test_fvg_size_atr_calculation(self):
        """Test FVG size in ATR terms."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.44,
            "fvg_bottom": 100.00,
            "fvg_gap_size": 0.44,
            "atr_14": 0.22,
        }

        result = self.module.process_bar(bar)

        # 0.44 / 0.22 = 2.0 ATR
        assert abs(result["fvg_size_atr"] - 2.0) < 0.01

    def test_context_string_generation(self):
        """Test context string is properly generated."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.40,
            "fvg_bottom": 100.20,
            "fvg_gap_size": 0.20,
        }

        result = self.module.process_bar(bar)

        assert "bullish" in result["fvg_context"]
        assert result["fvg_context"] != "none"

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = FVGQualityModule(enabled=False)
        bar = {**self.base_bar, "fvg_detected": True}

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "fvg_detected": True, "fvg_type": "bullish"}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
