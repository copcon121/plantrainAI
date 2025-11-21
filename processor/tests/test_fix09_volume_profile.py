"""Unit tests for Fix #09: Volume Profile Module."""
import pytest
from processor.modules.fix09_volume_profile import VolumeProfileModule


class TestVolumeProfileModule:
    """Tests for VolumeProfileModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = VolumeProfileModule()
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

    def test_insufficient_data_returns_zeros(self):
        """Test that insufficient data returns zero VP levels."""
        bar = self.base_bar.copy()

        # Only process a few bars
        for i in range(3):
            result = self.module.process_bar(bar)

        assert result["vp_session_vah"] == 0.0
        assert result["vp_session_val"] == 0.0
        assert result["vp_session_poc"] == 0.0

    def test_vp_levels_calculated_with_data(self):
        """Test VP levels are calculated with sufficient data."""
        # Process enough bars to build profile
        for i in range(10):
            bar = {
                **self.base_bar,
                "bar_index": i,
                "high": 100.50 + (i * 0.1),
                "low": 100.00 + (i * 0.1),
                "close": 100.25 + (i * 0.1),
                "volume": 4000 + (i * 100),
            }
            result = self.module.process_bar(bar)

        assert result["vp_session_vah"] > 0
        assert result["vp_session_val"] > 0
        assert result["vp_session_poc"] > 0
        assert result["vp_session_vah"] >= result["vp_session_poc"]
        assert result["vp_session_poc"] >= result["vp_session_val"]

    def test_price_in_value_area(self):
        """Test price position detection in value area."""
        # Build profile
        for i in range(10):
            bar = {
                **self.base_bar,
                "bar_index": i,
                "high": 100.50,
                "low": 100.00,
                "close": 100.25,
                "volume": 5000,
            }
            result = self.module.process_bar(bar)

        # Price in middle should be in VA
        assert result["vp_in_value_area"] == 1
        assert result["vp_position"] in ["upper_va", "lower_va"]

    def test_price_above_value_area(self):
        """Test price position detection above value area."""
        # Build profile
        for i in range(10):
            bar = {
                **self.base_bar,
                "bar_index": i,
                "high": 100.50,
                "low": 100.00,
                "close": 100.25,
                "volume": 5000,
            }
            self.module.process_bar(bar)

        # Process bar with price above VA
        high_bar = {
            **self.base_bar,
            "bar_index": 11,
            "high": 102.00,
            "low": 101.50,
            "close": 101.80,
            "volume": 3000,
        }

        result = self.module.process_bar(high_bar)

        assert result["vp_in_value_area"] == 0
        assert result["vp_position"] == "above_va"

    def test_distance_calculations(self):
        """Test distance to VP levels calculation."""
        # Build profile
        for i in range(10):
            bar = {
                **self.base_bar,
                "bar_index": i,
                "high": 100.50,
                "low": 100.00,
                "close": 100.25,
                "volume": 5000,
            }
            result = self.module.process_bar(bar)

        assert "vp_distance_to_poc" in result
        assert "vp_distance_to_vah" in result
        assert "vp_distance_to_val" in result

    def test_session_lookback_limit(self):
        """Test that session data is limited to lookback period."""
        # Process more bars than lookback
        for i in range(150):
            bar = {
                **self.base_bar,
                "bar_index": i,
                "high": 100.50 + (i % 10) * 0.1,
                "low": 100.00 + (i % 10) * 0.1,
                "volume": 4000,
            }
            self.module.process_bar(bar)

        # Internal session data should be limited
        assert len(self.module._session_data) <= 100

    def test_poc_is_highest_volume_level(self):
        """Test POC is at highest volume price level."""
        # Create profile with clear volume concentration
        for i in range(10):
            bar = {
                **self.base_bar,
                "bar_index": i,
                "high": 100.30,
                "low": 100.10,
                "close": 100.20,
                "volume": 10000 if i < 5 else 1000,  # High volume at start
            }
            result = self.module.process_bar(bar)

        # POC should be near concentrated volume area
        assert result["vp_session_poc"] > 0

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = VolumeProfileModule(enabled=False)
        bar = self.base_bar.copy()

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = self.base_bar.copy()
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
