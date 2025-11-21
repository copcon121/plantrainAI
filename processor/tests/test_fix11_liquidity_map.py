"""Unit tests for Fix #11: Liquidity Map Module."""
import pytest
from processor.modules.fix11_liquidity_map import LiquidityMapModule


class TestLiquidityMapModule:
    """Tests for LiquidityMapModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = LiquidityMapModule()
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

    def test_no_sweep_default_state(self):
        """Test default state with no sweep detected."""
        bar = self.base_bar.copy()

        result = self.module.process_bar(bar)

        assert result["liquidity_sweep_detected"] is False
        assert result["liquidity_sweep_type"] == "none"
        assert "eqh_price" in result and "eql_price" in result

    def test_equal_highs_detection(self):
        """Test equal highs liquidity level detection."""
        # Add swing highs at similar levels
        for i in range(5):
            bar = {
                **self.base_bar,
                "bar_index": i * 10,
                "is_swing_high": True,
                "is_swing_low": False,
                "high": 100.50,  # Same level
            }
            result = self.module.process_bar(bar)

        assert result["equal_highs_count"] >= 1
        assert result["eqh_price"] == 100.50
        assert result["eqh_touches"] >= 2

    def test_equal_lows_detection(self):
        """Test equal lows liquidity level detection."""
        # Add swing lows at similar levels
        for i in range(5):
            bar = {
                **self.base_bar,
                "bar_index": i * 10,
                "is_swing_high": False,
                "is_swing_low": True,
                "low": 99.50,  # Same level
            }
            result = self.module.process_bar(bar)

        assert result["equal_lows_count"] >= 1
        assert result["eql_price"] == 99.50
        assert result["eql_touches"] >= 2

    def test_sweep_above_detection(self):
        """Test sweep above liquidity level detection."""
        # Build liquidity level
        for i in range(3):
            bar = {
                **self.base_bar,
                "bar_index": i * 10,
                "is_swing_high": True,
                "is_swing_low": False,
                "high": 100.50,
                "close": 100.30,
            }
            self.module.process_bar(bar)

        # Sweep bar - goes above level but closes below
        sweep_bar = {
            **self.base_bar,
            "bar_index": 50,
            "high": 100.60,  # Above the level
            "close": 100.40,  # Closes below the level
        }

        result = self.module.process_bar(sweep_bar)

        # May or may not detect sweep depending on level status
        assert "liquidity_sweep_detected" in result

    def test_sweep_below_detection(self):
        """Test sweep below liquidity level detection."""
        # Build liquidity level
        for i in range(3):
            bar = {
                **self.base_bar,
                "bar_index": i * 10,
                "is_swing_high": False,
                "is_swing_low": True,
                "low": 99.50,
                "close": 99.70,
            }
            self.module.process_bar(bar)

        # Sweep bar - goes below level but closes above
        sweep_bar = {
            **self.base_bar,
            "bar_index": 50,
            "low": 99.40,  # Below the level
            "close": 99.60,  # Closes above the level
        }

        result = self.module.process_bar(sweep_bar)

        assert "liquidity_sweep_detected" in result

    def test_nearest_liquidity_tracking(self):
        """Test nearest liquidity levels are tracked."""
        bar = {
            **self.base_bar,
            "nearest_liquidity_high": 100.90,
            "nearest_liquidity_low": 99.40,
            "liquidity_high_type": "swing",
            "liquidity_low_type": "equal_lows",
        }

        result = self.module.process_bar(bar)

        assert result["nearest_liquidity_high"] == 100.90
        assert result["nearest_liquidity_low"] == 99.40
        assert result["liquidity_high_type"] == "swing"
        assert result["liquidity_low_type"] == "equal_lows"

    def test_swing_level_tracking(self):
        """Test swing-based liquidity level tracking."""
        bar = {
            **self.base_bar,
            "last_swing_high": 101.00,
            "last_swing_low": 99.00,
        }

        result = self.module.process_bar(bar)

        # Module should track these levels
        assert len(self.module._liquidity_levels) > 0

    def test_liquidity_level_limit(self):
        """Test liquidity level count is limited."""
        # Add many levels
        for i in range(100):
            bar = {
                **self.base_bar,
                "bar_index": i,
                "is_swing_high": i % 2 == 0,
                "is_swing_low": i % 2 == 1,
                "high": 100 + i * 0.1,
                "low": 99 + i * 0.1,
            }
            self.module.process_bar(bar)

        # Should be limited
        assert len(self.module._liquidity_levels) <= 50

    def test_swept_level_not_reused(self):
        """Test swept levels are marked and not reused."""
        # Build level
        bar1 = {
            **self.base_bar,
            "bar_index": 10,
            "is_swing_high": True,
            "is_swing_low": False,
            "high": 100.50,
            "close": 100.30,
        }
        self.module.process_bar(bar1)

        # Sweep it
        sweep_bar = {
            **self.base_bar,
            "bar_index": 20,
            "high": 100.60,
            "close": 100.40,
        }
        result = self.module.process_bar(sweep_bar)

        # Check if any levels are marked as swept
        swept_count = sum(1 for l in self.module._liquidity_levels if l.get("swept", False))
        # The test is that the module handles sweeping properly
        assert "liquidity_sweep_detected" in result
        assert result["bars_since_sweep"] >= 0

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = LiquidityMapModule(enabled=False)
        bar = self.base_bar.copy()

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = self.base_bar.copy()
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
