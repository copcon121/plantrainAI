"""
Lightweight schema and validators for raw_smc_export.jsonl lines.
Keeps dependencies minimal (no jsonschema).
"""

from typing import Dict, List, Tuple

# Base fields expected on every bar (Phase 1)
BASE_REQUIRED_FIELDS = [
    "bar_index",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "buy_volume",
    "sell_volume",
    "delta",
    "cumulative_delta",
    "atr_14",
]

# Module-specific required fields (per NINJA_EXPORT_CHECKLIST)
MODULE_REQUIRED_FIELDS: Dict[str, List[str]] = {
    "fix02_fvg_quality": [
        "fvg_detected",
        "fvg_type",
        "fvg_top",
        "fvg_bottom",
        "fvg_gap_size",
        "fvg_creation_volume",
        "fvg_creation_delta",
    ],
    "fix03_structure_context": [
        "choch_detected",
        "choch_type",
        "choch_bars_ago",
        "bos_detected",
        "bos_type",
        "bos_bars_ago",
        "current_trend",
        "last_structure_break",
    ],
    "fix05_stop_placement": [
        "fvg_top",
        "fvg_bottom",
        "fvg_type",
        "nearest_ob_top",
        "nearest_ob_bottom",
        "last_swing_high",
        "last_swing_low",
    ],
    "fix06_target_placement": [
        "last_swing_high",
        "last_swing_low",
        "recent_swing_high",
        "recent_swing_low",
    ],
    "fix07_market_condition": [
        "atr_14",
        "adx_14",
        "di_plus_14",
        "di_minus_14",
    ],
    "fix08_volume_divergence": [
        "is_swing_high",
        "is_swing_low",
        "delta",
        "cumulative_delta",
    ],
    "fix10_mtf_alignment": [
        "htf_high",
        "htf_low",
        "htf_close",
        "htf_ema_20",
        "htf_ema_50",
        "htf_is_swing_high",
        "htf_is_swing_low",
    ],
    "fix11_liquidity_map": [
        "nearest_liquidity_high",
        "nearest_liquidity_low",
        "liquidity_high_type",
        "liquidity_low_type",
    ],
}


def find_missing_fields(record: Dict[str, object], required: List[str]) -> List[str]:
    """Return list of missing or None fields."""
    return [field for field in required if field not in record or record[field] is None]


def validate_record(record: Dict[str, object]) -> List[Tuple[str, List[str]]]:
    """
    Validate a single bar record against base and module requirements.
    Returns list of (section, missing_fields).
    """
    problems: List[Tuple[str, List[str]]] = []

    missing_base = find_missing_fields(record, BASE_REQUIRED_FIELDS)
    if missing_base:
        problems.append(("base", missing_base))

    for module, fields in MODULE_REQUIRED_FIELDS.items():
        missing = find_missing_fields(record, fields)
        if missing:
            problems.append((module, missing))

    return problems
