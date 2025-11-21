"""Unit tests for Fix #10: MTF Alignment Module."""
import pytest
from processor.modules.fix10_mtf_alignment import MTFAlignmentModule


class TestMTFAlignmentModule:
    """Tests for MTFAlignmentModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = MTFAlignmentModule()
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

    def test_full_alignment_bullish(self):
        """Test full alignment for bullish setup."""
        bar = {
            **self.base_bar,
            "fvg_type": "bullish",
            "htf_close": 100.50,
            "htf_ema_20": 100.30,  # Price above EMA20
            "htf_ema_50": 100.10,  # Price above EMA50, EMA20 > EMA50
        }

        result = self.module.process_bar(bar)

        assert result["mtf_alignment_score"] == 1.0  # 3/3 points
        assert result["mtf_alignment_points"] == 3
        assert result["htf_trend"] == "bullish"
        assert result["mtf_is_aligned"] is True

    def test_full_alignment_bearish(self):
        """Test full alignment for bearish setup."""
        bar = {
            **self.base_bar,
            "fvg_type": "bearish",
            "htf_close": 100.00,
            "htf_ema_20": 100.20,  # Price below EMA20
            "htf_ema_50": 100.40,  # Price below EMA50, EMA20 < EMA50
        }

        result = self.module.process_bar(bar)

        assert result["mtf_alignment_score"] == 1.0
        assert result["mtf_alignment_points"] == 3
        assert result["htf_trend"] == "bearish"
        assert result["mtf_is_aligned"] is True

    def test_partial_alignment(self):
        """Test partial alignment returns partial score."""
        bar = {
            **self.base_bar,
            "fvg_type": "bullish",
            "htf_close": 100.25,
            "htf_ema_20": 100.20,  # Price above EMA20 (1 point)
            "htf_ema_50": 100.30,  # Price below EMA50 (0 points), EMA20 < EMA50 (0 points)
        }

        result = self.module.process_bar(bar)

        assert 0.0 < result["mtf_alignment_score"] < 1.0
        assert result["mtf_alignment_points"] < 3

    def test_no_alignment_counter_trend(self):
        """Test no alignment when FVG is counter to HTF trend."""
        bar = {
            **self.base_bar,
            "fvg_type": "bullish",  # Bullish FVG
            "htf_close": 100.00,
            "htf_ema_20": 100.20,  # Price below EMA20
            "htf_ema_50": 100.40,  # Bearish HTF trend
        }

        result = self.module.process_bar(bar)

        assert result["mtf_alignment_score"] == 0.0
        assert result["mtf_is_aligned"] is False
        assert result["htf_trend"] == "bearish"

    def test_neutral_trend_no_ema_data(self):
        """Test neutral trend when no EMA data."""
        bar = {
            **self.base_bar,
            "fvg_type": "bullish",
            "htf_close": 100.50,
            "htf_ema_20": 0,  # No EMA data
            "htf_ema_50": 0,
        }

        result = self.module.process_bar(bar)

        assert result["htf_trend"] == "neutral"
        assert result["mtf_alignment_score"] == 0.0

    def test_trend_strength_calculation(self):
        """Test HTF trend strength calculation."""
        bar = {
            **self.base_bar,
            "fvg_type": "bullish",
            "htf_close": 100.50,
            "htf_ema_20": 100.40,
            "htf_ema_50": 100.00,  # Wide EMA spread
        }

        result = self.module.process_bar(bar)

        assert result["htf_trend_strength"] > 0

    def test_price_vs_ema_flags(self):
        """Test price vs EMA position flags."""
        bar = {
            **self.base_bar,
            "fvg_type": "bullish",
            "htf_close": 100.50,
            "htf_ema_20": 100.30,
            "htf_ema_50": 100.10,
        }

        result = self.module.process_bar(bar)

        assert result["htf_price_vs_ema20"] == 1  # Above
        assert result["htf_price_vs_ema50"] == 1  # Above
        assert result["htf_ema_trend"] == 1  # Bullish

    def test_no_fvg_still_calculates(self):
        """Test module still calculates HTF trend without FVG."""
        bar = {
            **self.base_bar,
            "htf_close": 100.50,
            "htf_ema_20": 100.30,
            "htf_ema_50": 100.10,
        }

        result = self.module.process_bar(bar)

        assert result["htf_trend"] == "bullish"
        # Alignment score depends on FVG direction match
        assert "mtf_alignment_score" in result

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = MTFAlignmentModule(enabled=False)
        bar = self.base_bar.copy()

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "fvg_type": "bullish", "htf_ema_20": 100.0}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
