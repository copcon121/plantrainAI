"""Unit tests for Fix #12: FVG Retest Module."""
from processor.modules.fix12_fvg_retest import FVGRetestModule


class TestFVGRetestModule:
    """Tests for FVGRetestModule."""

    def setup_method(self):
        self.module = FVGRetestModule()
        # For bullish FVG: penetration = (fvg_top - low) / gap
        # low=100.95 → penetration = (101.0-100.95)/0.5 = 0.1 → "edge" retest
        self.base_bar = {
            "bar_index": 100,
            "fvg_active": True,
            "fvg_type": "bullish",
            "fvg_top": 101.0,
            "fvg_bottom": 100.5,
            "fvg_bar_index": 95,
            "close": 100.98,
            "high": 101.2,
            "low": 100.95,  # Edge penetration into FVG zone
            "atr_14": 0.5,
            "fvg_strength_score": 0.8,
            "ext_bos_up": True,
        }

    def test_edge_retest_valid(self):
        bar = {**self.base_bar}
        result = self.module.process_bar(bar)
        assert result["fvg_retest_detected"] is True
        assert result["fvg_retest_type"] in ["edge", "shallow", "no_touch"]
        assert result["fvg_retest_quality_score"] > 0
        assert result["signal_type"] == "fvg_retest_bull"

    def test_bearish_break_invalid(self):
        bar = {
            **self.base_bar,
            "fvg_type": "bearish",
            "fvg_top": 100.0,
            "fvg_bottom": 99.5,
            "high": 100.8,  # break through (high > fvg_top)
            "low": 99.6,
            "ext_bos_down": True,
        }
        result = self.module.process_bar(bar)
        assert result["fvg_retest_detected"] is False
        # Module returns reason "break_or_filled", type stays "none"
        assert result["fvg_retest_reason"] == "break_or_filled"

    def test_stale_rejected(self):
        bar = {**self.base_bar, "bar_index": 200, "fvg_bar_index": 0}
        result = self.module.process_bar(bar)
        assert result["fvg_retest_detected"] is False
        assert result["fvg_retest_reason"] == "stale"

    def test_no_context_rejected(self):
        bar = {**self.base_bar}
        bar.pop("ext_bos_up", None)
        result = self.module.process_bar(bar)
        assert result["fvg_retest_detected"] is False
        assert result["fvg_retest_reason"] == "no_context"
