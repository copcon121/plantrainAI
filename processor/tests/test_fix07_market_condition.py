"""Unit tests for Fix #07: Market Condition Module."""
import pytest
from processor.modules.fix07_market_condition import MarketConditionModule


class TestMarketConditionModule:
    """Tests for MarketConditionModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = MarketConditionModule()
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

    def test_strong_trend_bullish(self):
        """Test strong bullish trend classification."""
        bar = {
            **self.base_bar,
            "adx_14": 35.0,  # Strong ADX
            "di_plus_14": 30.0,
            "di_minus_14": 15.0,  # DI+ > DI-
        }

        result = self.module.process_bar(bar)

        assert result["market_trend"] == "trending"
        assert result["market_trend_direction"] == 1
        assert result["adx_class"] == "strong"

    def test_strong_trend_bearish(self):
        """Test strong bearish trend classification."""
        bar = {
            **self.base_bar,
            "adx_14": 35.0,
            "di_plus_14": 15.0,
            "di_minus_14": 30.0,  # DI- > DI+
        }

        result = self.module.process_bar(bar)

        assert result["market_trend"] == "trending"
        assert result["market_trend_direction"] == -1

    def test_ranging_market(self):
        """Test ranging market classification."""
        bar = {
            **self.base_bar,
            "adx_14": 12.0,  # Low ADX
            "di_plus_14": 18.0,
            "di_minus_14": 16.0,
        }

        result = self.module.process_bar(bar)

        assert result["market_trend"] == "ranging"
        assert result["adx_class"] == "weak"

    def test_volatility_high_regime(self):
        """Test high volatility regime classification."""
        bar = {
            **self.base_bar,
            "atr_14": 0.50,  # High ATR
            "adx_14": 20.0,
            "di_plus_14": 18.0,
            "di_minus_14": 16.0,
        }
        history = [{"atr_14": 0.20} for _ in range(20)]  # Lower historical ATR

        result = self.module.process_bar(bar, history)

        assert result["volatility_regime"] == "high"
        assert result["volatility_percentile"] > 75

    def test_volatility_low_regime(self):
        """Test low volatility regime classification."""
        bar = {
            **self.base_bar,
            "atr_14": 0.10,  # Low ATR
            "adx_14": 20.0,
            "di_plus_14": 18.0,
            "di_minus_14": 16.0,
        }
        history = [{"atr_14": 0.30} for _ in range(20)]  # Higher historical ATR

        result = self.module.process_bar(bar, history)

        assert result["volatility_regime"] == "low"
        assert result["volatility_percentile"] < 25

    def test_favorable_environment(self):
        """Test favorable trading environment detection."""
        bar = {
            **self.base_bar,
            "adx_14": 35.0,
            "di_plus_14": 30.0,
            "di_minus_14": 15.0,
            "atr_14": 0.25,
        }
        history = [{"atr_14": 0.22} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        assert result["market_condition"] == "trending_strong"
        assert result["trade_environment"] == "favorable"

    def test_unfavorable_environment(self):
        """Test unfavorable trading environment detection."""
        bar = {
            **self.base_bar,
            "adx_14": 10.0,  # Very weak
            "di_plus_14": 18.0,
            "di_minus_14": 17.0,
            "atr_14": 0.08,  # Low volatility
        }
        history = [{"atr_14": 0.22} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        assert result["market_condition"] in ["ranging_quiet", "ranging_normal"]

    def test_market_condition_score(self):
        """Test market condition score range."""
        bar = {
            **self.base_bar,
            "adx_14": 25.0,
            "di_plus_14": 25.0,
            "di_minus_14": 15.0,
        }

        result = self.module.process_bar(bar)

        assert 0.0 <= result["market_condition_score"] <= 1.0

    def test_atr_vs_avg_calculation(self):
        """Test ATR vs average calculation."""
        bar = {
            **self.base_bar,
            "atr_14": 0.44,  # 2x average
            "adx_14": 25.0,
            "di_plus_14": 20.0,
            "di_minus_14": 15.0,
        }
        history = [{"atr_14": 0.22} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        assert abs(result["atr_vs_avg"] - 2.0) < 0.1

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = MarketConditionModule(enabled=False)
        bar = self.base_bar.copy()

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "adx_14": 25.0, "di_plus_14": 20.0, "di_minus_14": 15.0}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
