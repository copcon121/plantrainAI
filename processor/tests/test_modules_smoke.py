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
]


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_module_process_bar_smoke(module_name):
    module = importlib.import_module(f"processor.modules.{module_name}")
    class_name = "".join(part.capitalize() for part in module_name.split("_"))
    cls = getattr(module, f"{class_name}Module")
    instance = cls()

    # Pick module-specific fixture if available, else BASE_BAR
    fixture_attr = module_name.upper()
    bar = getattr(module_inputs, fixture_attr, module_inputs.BASE_BAR)

    out = instance.process_bar(dict(bar), history=[])

    assert isinstance(out, dict)
    assert out["bar_index"] == bar["bar_index"]
