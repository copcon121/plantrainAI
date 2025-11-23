import importlib
import pytest

from processor.tests.fixtures import module_inputs

MODULE_NAMES = [
    "fix01_ob_quality",
    "fix02_fvg_quality",
    "fix03_structure_context",
    "fix04_confluence",
    "fix05_stop_placement",
    "fix06_target_placement",
    "fix07_market_condition",
    "fix08_volume_divergence",
    "fix09_volume_profile",
    "fix10_mtf_alignment",
    "fix11_liquidity_map",
    "fix12_fvg_retest",
    "fix13_wave_delta",
]

# Mapping from module file names to actual class names
CLASS_NAME_MAP = {
    "fix01_ob_quality": "OBQualityModule",
    "fix02_fvg_quality": "FVGQualityModule",
    "fix03_structure_context": "StructureContextModule",
    "fix04_confluence": "ConfluenceModule",
    "fix05_stop_placement": "StopPlacementModule",
    "fix06_target_placement": "TargetPlacementModule",
    "fix07_market_condition": "MarketConditionModule",
    "fix08_volume_divergence": "VolumeDivergenceModule",
    "fix09_volume_profile": "VolumeProfileModule",
    "fix10_mtf_alignment": "MTFAlignmentModule",
    "fix11_liquidity_map": "LiquidityMapModule",
    "fix12_fvg_retest": "FVGRetestModule",
    "fix13_wave_delta": "WaveDeltaModule",
}


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_module_process_bar_smoke(module_name):
    module = importlib.import_module(f"processor.modules.{module_name}")
    class_name = CLASS_NAME_MAP[module_name]
    cls = getattr(module, class_name)
    instance = cls()

    # Pick module-specific fixture if available, else BASE_BAR
    fixture_attr = module_name.upper()
    bar = getattr(module_inputs, fixture_attr, module_inputs.BASE_BAR)

    out = instance.process_bar(dict(bar), history=[])

    assert isinstance(out, dict)
    assert out["bar_index"] == bar["bar_index"]
