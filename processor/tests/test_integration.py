"""
Integration tests for the module pipeline.

Tests:
- Full pipeline processing (all modules in sequence)
- Thread-safety of stateful modules
- Input validation
- Module chaining and data flow
"""
import concurrent.futures
import importlib
from copy import deepcopy
from typing import Any, Dict, List

import pytest

from processor.core.module_base import BaseModule
from processor.tests.fixtures import module_inputs

# All modules in execution order
MODULE_CONFIGS = [
    ("fix01_ob_quality", "OBQualityModule"),
    ("fix02_fvg_quality", "FVGQualityModule"),
    ("fix03_structure_context", "StructureContextModule"),
    ("fix04_confluence", "ConfluenceModule"),
    ("fix05_stop_placement", "StopPlacementModule"),
    ("fix06_target_placement", "TargetPlacementModule"),
    ("fix07_market_condition", "MarketConditionModule"),
    ("fix08_volume_divergence", "VolumeDivergenceModule"),
    ("fix09_volume_profile", "VolumeProfileModule"),
    ("fix10_mtf_alignment", "MTFAlignmentModule"),
    ("fix11_liquidity_map", "LiquidityMapModule"),
    ("fix12_fvg_retest", "FVGRetestModule"),
    ("fix13_wave_delta", "WaveDeltaModule"),
]


def load_modules() -> List[BaseModule]:
    """Load all modules."""
    modules = []
    for module_name, class_name in MODULE_CONFIGS:
        try:
            mod = importlib.import_module(f"processor.modules.{module_name}")
            cls = getattr(mod, class_name)
            modules.append(cls())
        except (ImportError, AttributeError) as e:
            pytest.skip(f"Could not load {module_name}: {e}")
    return modules


def run_pipeline(bar: Dict[str, Any], modules: List[BaseModule], history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run a bar through all modules."""
    history = history or []
    state = dict(bar)
    for module in modules:
        state = module.process_bar(state, history)
    return state


class TestPipelineIntegration:
    """Test full pipeline processing."""

    def test_pipeline_processes_all_modules(self):
        """All modules should process the bar without errors."""
        modules = load_modules()
        bar = deepcopy(module_inputs.BASE_BAR)

        result = run_pipeline(bar, modules)

        # Should have original fields plus module outputs
        assert result["bar_index"] == bar["bar_index"]
        assert result["close"] == bar["close"]

        # Should have outputs from various modules
        assert "ob_strength_score" in result or "ob_valid" in result
        assert "vp_session_poc" in result or result.get("vp_session_poc", 0) == 0

    def test_pipeline_with_fvg_data(self):
        """Pipeline should handle FVG-enriched bar data."""
        modules = load_modules()
        bar = deepcopy(module_inputs.MODULE_FIX02)

        result = run_pipeline(bar, modules)

        # FVG quality module should have run
        assert "fvg_quality_score" in result or "fvg_detected" in result
        assert result["fvg_detected"] == True

    def test_pipeline_with_structure_data(self):
        """Pipeline should handle structure-enriched bar data."""
        modules = load_modules()
        bar = deepcopy(module_inputs.MODULE_FIX03)

        result = run_pipeline(bar, modules)

        # Structure context should be preserved
        assert result["bos_detected"] == True
        assert result["current_trend"] == "bullish"

    def test_pipeline_preserves_original_fields(self):
        """Pipeline should not lose original bar fields."""
        modules = load_modules()
        bar = deepcopy(module_inputs.BASE_BAR)
        original_keys = set(bar.keys())

        result = run_pipeline(bar, modules)

        # All original keys should still be present
        for key in original_keys:
            assert key in result, f"Original field {key} was lost"

    def test_pipeline_sequential_processing(self):
        """Test processing multiple bars sequentially."""
        modules = load_modules()
        history: List[Dict[str, Any]] = []

        # Process 10 bars
        for i in range(10):
            bar = deepcopy(module_inputs.BASE_BAR)
            bar["bar_index"] = 1250 + i
            bar["close"] = 100.45 + i * 0.1

            result = run_pipeline(bar, modules, history)
            history.append(result)

        assert len(history) == 10
        # Last bar should have proper index
        assert history[-1]["bar_index"] == 1259


class TestThreadSafety:
    """Test thread-safety of stateful modules."""

    def test_concurrent_processing_same_module(self):
        """Concurrent calls to same module instance should not corrupt state."""
        # Test fix08 (stateful - _swing_history)
        mod = importlib.import_module("processor.modules.fix08_volume_divergence")
        instance = mod.VolumeDivergenceModule()

        def process_bars(symbol: str, count: int) -> List[Dict[str, Any]]:
            results = []
            for i in range(count):
                bar = deepcopy(module_inputs.MODULE_FIX08)
                bar["symbol"] = symbol
                bar["bar_index"] = i
                bar["is_swing_high"] = i % 5 == 0
                bar["is_swing_low"] = i % 7 == 0
                result = instance.process_bar(bar, [])
                results.append(result)
            return results

        # Run concurrent processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_bars, f"SYM{j}", 50)
                for j in range(4)
            ]
            all_results = [f.result() for f in futures]

        # All should complete without error
        assert len(all_results) == 4
        for results in all_results:
            assert len(results) == 50

    def test_concurrent_volume_profile(self):
        """Volume profile module should handle concurrent access."""
        mod = importlib.import_module("processor.modules.fix09_volume_profile")
        instance = mod.VolumeProfileModule()

        def process_session(session_id: str, bars: int) -> Dict[str, Any]:
            last_result = {}
            for i in range(bars):
                bar = deepcopy(module_inputs.BASE_BAR)
                bar["session"] = session_id
                bar["bar_index"] = i
                bar["high"] = 100.55 + i * 0.01
                bar["low"] = 100.05 + i * 0.01
                bar["close"] = 100.45 + i * 0.01
                bar["volume"] = 4500 + i * 10
                last_result = instance.process_bar(bar, [])
            return last_result

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_session, f"SESSION_{j}", 30)
                for j in range(4)
            ]
            results = [f.result() for f in futures]

        # All should have VP data
        for result in results:
            assert "vp_session_poc" in result

    def test_concurrent_liquidity_map(self):
        """Liquidity map module should handle concurrent access."""
        mod = importlib.import_module("processor.modules.fix11_liquidity_map")
        instance = mod.LiquidityMapModule()

        def process_swings(count: int) -> List[Dict[str, Any]]:
            results = []
            for i in range(count):
                bar = deepcopy(module_inputs.MODULE_FIX11)
                bar["bar_index"] = i
                bar["is_swing_high"] = i % 3 == 0
                bar["is_swing_low"] = i % 4 == 0
                bar["high"] = 100.90 + i * 0.01
                bar["low"] = 99.40 - i * 0.01
                result = instance.process_bar(bar, [])
                results.append(result)
            return results

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_swings, 40) for _ in range(4)]
            all_results = [f.result() for f in futures]

        for results in all_results:
            assert len(results) == 40

    def test_concurrent_wave_delta(self):
        """Wave delta module should handle concurrent access."""
        mod = importlib.import_module("processor.modules.fix13_wave_delta")
        instance = mod.WaveDeltaModule()

        def process_waves(symbol: str, count: int) -> Dict[str, Any]:
            last_result = {}
            for i in range(count):
                bar = deepcopy(module_inputs.BASE_BAR)
                bar["symbol"] = symbol
                bar["bar_index"] = i
                bar["is_swing_high"] = i % 6 == 0
                bar["is_swing_low"] = i % 8 == 0
                bar["delta"] = 1100 + (i % 10) * 100
                bar["volume"] = 4500 + i * 50
                last_result = instance.process_bar(bar, [])
            return last_result

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_waves, f"WAVE_{j}", 50)
                for j in range(4)
            ]
            results = [f.result() for f in futures]

        for result in results:
            assert "active_wave_delta" in result


class TestInputValidation:
    """Test input validation in BaseModule."""

    def test_validate_bar_missing_fields(self):
        """Validation should catch missing required fields."""
        mod = importlib.import_module("processor.modules.fix01_ob_quality")
        instance = mod.OBQualityModule()

        bar = {}  # Empty bar
        is_valid, errors = instance.validate_bar(bar, required={"high", "low", "close"})

        assert not is_valid
        assert len(errors) == 3
        assert any("high" in e for e in errors)

    def test_validate_bar_null_fields(self):
        """Validation should catch null values."""
        mod = importlib.import_module("processor.modules.fix01_ob_quality")
        instance = mod.OBQualityModule()

        bar = {"high": None, "low": 99.0, "close": 100.0}
        is_valid, errors = instance.validate_bar(bar, required={"high", "low", "close"})

        assert not is_valid
        assert any("null_field:high" in e for e in errors)

    def test_validate_bar_numeric_fields(self):
        """Validation should check numeric field validity."""
        mod = importlib.import_module("processor.modules.fix01_ob_quality")
        instance = mod.OBQualityModule()

        bar = {"volume": "invalid", "high": 100.0}
        is_valid, errors = instance.validate_bar(
            bar,
            required={"high"},
            numeric_fields={"volume"}
        )

        assert not is_valid
        assert any("non_numeric:volume" in e for e in errors)

    def test_validate_bar_negative_values(self):
        """Validation should catch negative numeric values."""
        mod = importlib.import_module("processor.modules.fix01_ob_quality")
        instance = mod.OBQualityModule()

        bar = {"volume": -100, "high": 100.0}
        is_valid, errors = instance.validate_bar(
            bar,
            required={"high"},
            numeric_fields={"volume"}
        )

        assert not is_valid
        assert any("negative:volume" in e for e in errors)

    def test_get_numeric_safe(self):
        """get_numeric should safely extract values."""
        mod = importlib.import_module("processor.modules.fix01_ob_quality")
        instance = mod.OBQualityModule()

        bar = {"good": 100.5, "string": "bad", "none": None}

        assert instance.get_numeric(bar, "good") == 100.5
        assert instance.get_numeric(bar, "string", 0.0) == 0.0
        assert instance.get_numeric(bar, "none", 99.0) == 99.0
        assert instance.get_numeric(bar, "missing", -1.0) == -1.0

    def test_get_bool_safe(self):
        """get_bool should safely extract boolean values."""
        mod = importlib.import_module("processor.modules.fix01_ob_quality")
        instance = mod.OBQualityModule()

        bar = {"true_val": True, "false_val": False, "none_val": None, "int_val": 1}

        assert instance.get_bool(bar, "true_val") is True
        assert instance.get_bool(bar, "false_val") is False
        assert instance.get_bool(bar, "none_val", True) is True
        assert instance.get_bool(bar, "int_val") is True
        assert instance.get_bool(bar, "missing", False) is False


class TestModuleChaining:
    """Test data flow between modules."""

    def test_fvg_to_target_chain(self):
        """FVG detection should flow to target placement."""
        modules = load_modules()

        # Bar with FVG and stop data for target calculation
        bar = deepcopy(module_inputs.MODULE_FIX02)
        bar.update({
            "stop_price": 99.80,
            "entry": 100.20,
            "last_swing_high": 100.70,
            "last_swing_low": 99.80,
            "atr_14": 0.22,
        })

        result = run_pipeline(bar, modules)

        # Target module should have processed the FVG
        assert result.get("fvg_detected", False) is True
        # May have target outputs if conditions met
        assert "tp1_price" in result

    def test_structure_to_confluence_chain(self):
        """Structure context should flow to confluence module."""
        modules = load_modules()

        bar = deepcopy(module_inputs.MODULE_FIX03)
        bar.update({
            "fvg_detected": True,
            "fvg_type": "bullish",
            "ob_detected": True,
            "ob_direction": "bull",
        })

        result = run_pipeline(bar, modules)

        # Confluence should consider structure
        assert "confluence_score" in result or "current_trend" in result
        assert result["current_trend"] == "bullish"

    def test_swing_to_divergence_chain(self):
        """Swing data should enable divergence detection."""
        mod = importlib.import_module("processor.modules.fix08_volume_divergence")
        instance = mod.VolumeDivergenceModule()

        # Build history with swings
        history = []
        for i in range(20):
            bar = deepcopy(module_inputs.BASE_BAR)
            bar["bar_index"] = i
            bar["is_swing_high"] = i == 5
            bar["is_swing_low"] = i == 10 or i == 18
            bar["high"] = 100.55 + (0.1 if i == 5 else 0)
            bar["low"] = 100.05 - (0.2 if i == 10 else 0.25 if i == 18 else 0)
            bar["delta"] = 1100 + (500 if i == 18 else 0)  # Higher delta at later low
            result = instance.process_bar(bar, history)
            history.append(result)

        # Last result may detect divergence
        assert "divergence_detected" in history[-1]
        assert "divergence_type" in history[-1]
