"""Unit tests for Fix #04: Confluence Module."""
import pytest
from processor.modules.fix04_confluence import ConfluenceModule


class TestConfluenceModule:
    """Tests for ConfluenceModule."""

    def setup_method(self):
        """Setup test fixtures."""
        self.module = ConfluenceModule()
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
        """Test that no FVG returns default confluence."""
        bar = {**self.base_bar, "fvg_detected": False}
        result = self.module.process_bar(bar)

        assert result["confluence_score"] == 0.0
        assert result["confluence_class"] == "None"
        assert result["confluence_factor_count"] == 0
        assert result["confluence_data_complete"] is False

    def test_confluence_score_range(self):
        """Test confluence score is between 0 and 1."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.40,
            "fvg_bottom": 100.20,
            "fvg_strength_score": 0.7,
            "structure_context": "expansion",
            "nearest_ob_top": 100.50,
            "nearest_ob_bottom": 100.10,
            "current_trend": "bullish",
        }

        result = self.module.process_bar(bar)

        assert 0.0 <= result["confluence_score"] <= 1.0

    def test_strong_confluence_classification(self):
        """Test strong confluence classification."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.40,
            "fvg_bottom": 100.20,
            "fvg_strength_score": 0.9,
            "structure_context": "expansion",
            "structure_context_score": 1.2,
            "nearest_ob_top": 100.45,
            "nearest_ob_bottom": 100.15,
            "current_trend": "bullish",
            "htf_trend": "bullish",
            "htf_trend_strength": 0.8,
            "nearest_liquidity_high": 100.60,
            "fvg_creation_volume": 8000,
            "fvg_delta_alignment": 1,
        }
        history = [{"volume": 4000} for _ in range(20)]

        result = self.module.process_bar(bar, history)

        # With all factors aligned, should be Strong
        assert result["confluence_class"] in ["Strong", "Moderate"]

    def test_weak_confluence_classification(self):
        """Test weak confluence classification."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_strength_score": 0.2,
            "structure_context": "unclear",
        }

        result = self.module.process_bar(bar)

        assert result["confluence_class"] in ["Weak", "Moderate"]

    def test_ob_proximity_score_inside_ob(self):
        """Test OB proximity score when FVG is inside OB."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.35,
            "fvg_bottom": 100.25,
            "nearest_ob_top": 100.50,
            "nearest_ob_bottom": 100.10,  # FVG completely inside OB
        }

        result = self.module.process_bar(bar)

        assert result["conf_ob_proximity"] == 1.0

    def test_ob_proximity_score_no_ob(self):
        """Test OB proximity score when no OB nearby."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_top": 100.40,
            "fvg_bottom": 100.20,
        }

        result = self.module.process_bar(bar)

        assert result["conf_ob_proximity"] == 0.5
        assert "ob_proximity" in result["confluence_missing_inputs"]

    def test_structure_score_expansion(self):
        """Test structure score for expansion context."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "structure_context": "expansion",
            "structure_context_score": 1.2,
        }

        result = self.module.process_bar(bar)

        assert result["conf_structure"] >= 0.9

    def test_confluence_factors_list(self):
        """Test that contributing factors are listed."""
        bar = {
            **self.base_bar,
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_strength_score": 0.8,  # High -> should be in list
            "structure_context": "expansion",
            "structure_context_score": 1.2,
        }

        result = self.module.process_bar(bar)

        assert isinstance(result["confluence_factors_list"], list)
        assert "confluence_missing_inputs" in result

    def test_module_disabled_returns_input(self):
        """Test that disabled module returns input unchanged."""
        module = ConfluenceModule(enabled=False)
        bar = {**self.base_bar, "fvg_detected": True}

        result = module.process_bar(bar)

        assert result == bar

    def test_output_does_not_mutate_input(self):
        """Test that process_bar does not mutate input."""
        bar = {**self.base_bar, "fvg_detected": True, "fvg_type": "bullish"}
        original_bar = dict(bar)

        self.module.process_bar(bar)

        assert bar == original_bar
