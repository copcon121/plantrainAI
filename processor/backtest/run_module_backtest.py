"""
Lightweight module pipeline runner for offline backtest/validation.

Reads JSONL bar_states, runs module pipeline, writes enriched JSONL and summary stats.

Usage:
python -m processor.backtest.run_module_backtest --inputs path/to/file.jsonl --output enriched.jsonl --summary summary.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Dict, Any

from processor.smc_processor import SMCDataProcessor
from processor.modules.fix01_ob_quality import OBQualityModule
from processor.modules.fix02_fvg_quality import FVGQualityModule
from processor.modules.fix03_structure_context import StructureContextModule
from processor.modules.fix04_confluence import ConfluenceModule
from processor.modules.fix05_stop_placement import StopPlacementModule
from processor.modules.fix06_target_placement import TargetPlacementModule
from processor.modules.fix07_market_condition import MarketConditionModule
from processor.modules.fix08_volume_divergence import VolumeDivergenceModule
from processor.modules.fix09_volume_profile import VolumeProfileModule
from processor.modules.fix10_mtf_alignment import MTFAlignmentModule
from processor.modules.fix11_liquidity_map import LiquidityMapModule
from processor.modules.fix12_fvg_retest import FVGRetestModule


def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            yield json.loads(line)


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _get_high_low(rec: Dict[str, Any]) -> tuple[float, float]:
    high = rec.get("high")
    low = rec.get("low")
    bar = rec.get("bar") or {}
    if high is None:
        high = bar.get("h")
    if low is None:
        low = bar.get("l")
    return float(high or 0.0), float(low or 0.0)


def annotate_outcomes(records: list[Dict[str, Any]], max_lookahead: int = 80) -> None:
    """
    Annotate records with outcome for FVG retest signals.
    Fields added: outcome_label (win/loss/open), outcome_rr, outcome_bars_to_exit, outcome_hit (tp/sl/open).
    """
    for i, rec in enumerate(records):
        if not rec.get("fvg_retest_detected"):
            continue
        direction = 1 if rec.get("signal_type") == "fvg_retest_bull" else -1 if rec.get("signal_type") == "fvg_retest_bear" else 0
        if direction == 0:
            continue
        entry = float(rec.get("entry") or rec.get("close") or 0.0)
        sl = float(rec.get("stop_price") or rec.get("sl") or 0.0)
        tp_candidates = [
            rec.get("tp"),
            rec.get("tp1_price"),
            rec.get("tp2_price"),
            rec.get("tp3_price"),
        ]
        tp = float(next((x for x in tp_candidates if x not in (None, 0, 0.0)), 0.0))
        if entry == 0.0 or sl == 0.0 or tp == 0.0:
            continue
        risk = (entry - sl) if direction == 1 else (sl - entry)
        if risk <= 0:
            continue

        last_bar = min(len(records) - 1, i + max_lookahead)
        outcome = {"outcome_label": "open", "outcome_rr": 0.0, "outcome_bars_to_exit": max_lookahead, "outcome_hit": "open"}
        for j in range(i + 1, last_bar + 1):
            hi, lo = _get_high_low(records[j])
            hit_sl = lo <= sl if direction == 1 else hi >= sl
            hit_tp = hi >= tp if direction == 1 else lo <= tp
            if hit_sl and hit_tp:
                outcome = {"outcome_label": "loss", "outcome_rr": -1.0, "outcome_bars_to_exit": j - i, "outcome_hit": "sl_tp_same_bar"}
                break
            if hit_sl:
                outcome = {"outcome_label": "loss", "outcome_rr": -1.0, "outcome_bars_to_exit": j - i, "outcome_hit": "sl"}
                break
            if hit_tp:
                outcome = {"outcome_label": "win", "outcome_rr": (tp - entry) / risk if direction == 1 else (entry - tp) / risk, "outcome_bars_to_exit": j - i, "outcome_hit": "tp"}
                break
        rec.update(outcome)


def build_default_modules() -> List:
    """
    Default pipeline order per dependency matrix:
    - VP/Liquidity -> context
    - Market/MTF -> context
    - OB/FVG/Structure -> core
    - Stop/Target -> after FVG/OB
    - Divergence -> independent
    - Confluence -> last
    """
    return [
        VolumeProfileModule(),
        LiquidityMapModule(),
        MarketConditionModule(),
        MTFAlignmentModule(),
        OBQualityModule(),
        FVGRetestModule(),
        FVGQualityModule(),
        StructureContextModule(),
        StopPlacementModule(),
        TargetPlacementModule(),
        VolumeDivergenceModule(),
        ConfluenceModule(),
    ]


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(records)
    def avg(key: str) -> float:
        vals = [r.get(key, 0) for r in records if key in r]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    def pct(cond):
        cnt = sum(1 for r in records if cond(r))
        return round(cnt * 100.0 / total, 2) if total else 0.0

    return {
        "total": total,
        "fvg_detected_pct": pct(lambda r: r.get("fvg_detected")),
        "avg_fvg_quality": avg("fvg_quality_score"),
        "avg_confluence": avg("confluence_score"),
        "mtf_data_complete_pct": pct(lambda r: r.get("mtf_data_complete")),
        "market_data_complete_pct": pct(lambda r: r.get("market_data_complete")),
        "liquidity_sweep_pct": pct(lambda r: r.get("liquidity_sweep_detected")),
        "divergence_pct": pct(lambda r: r.get("divergence_detected")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run module pipeline on JSONL data.")
    parser.add_argument("--inputs", required=True, help="Path to input JSONL")
    parser.add_argument("--output", required=False, help="Path to write enriched JSONL")
    parser.add_argument("--summary", required=False, help="Path to write summary JSON")
    parser.add_argument(
        "--max-lookahead",
        type=int,
        default=80,
        help="Bars to look ahead when annotating outcomes for retest signals.",
    )
    args = parser.parse_args()

    input_path = Path(args.inputs)
    out_path = Path(args.output) if args.output else None
    summary_path = Path(args.summary) if args.summary else None

    modules = build_default_modules()
    processor = SMCDataProcessor(modules=modules)

    enriched: List[Dict[str, Any]] = []
    for bar in load_jsonl(input_path):
        enriched.append(processor.process_bar(bar))

    # Annotate outcomes for retest signals (uses stop/tp if present)
    annotate_outcomes(enriched, max_lookahead=args.max_lookahead)

    if out_path:
        write_jsonl(out_path, enriched)

    summary = summarize(enriched)
    if summary_path:
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    else:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
