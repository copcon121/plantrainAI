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
    args = parser.parse_args()

    input_path = Path(args.inputs)
    out_path = Path(args.output) if args.output else None
    summary_path = Path(args.summary) if args.summary else None

    modules = build_default_modules()
    processor = SMCDataProcessor(modules=modules)

    enriched: List[Dict[str, Any]] = []
    for bar in load_jsonl(input_path):
        enriched.append(processor.process_bar(bar))

    if out_path:
        write_jsonl(out_path, enriched)

    summary = summarize(enriched)
    if summary_path:
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    else:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
