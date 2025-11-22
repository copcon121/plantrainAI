"""
Evaluate FVG retest module (#12) directly on raw export JSONL.

Pipeline: raw JSONL -> FVGRetestModule -> simulate TP/SL = 1:3 R
- Entry: close
- SL: fvg_bottom (bull) / fvg_top (bear)
- TP: entry + 3R (bull) / entry - 3R (bear)

Outputs a summary per file (trades, wins, losses, PF, winrate).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from processor.modules.fix12_fvg_retest import FVGRetestModule


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def evaluate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    module = FVGRetestModule(enabled=True)
    enriched: List[Dict[str, Any]] = []
    for bar in records:
        enriched.append(module.process_bar(bar, history=enriched))

    trades: List[Dict[str, Any]] = []
    for i, rec in enumerate(enriched):
        if not rec.get("fvg_retest_detected"):
            continue
        direction = 1 if rec.get("fvg_type") == "bullish" else -1 if rec.get("fvg_type") == "bearish" else 0
        if direction == 0:
            continue
        entry = float(rec.get("close") or 0.0)
        # Prefer creation high/low for stop placement; fall back to fvg edges
        tick_size = float(rec.get("tick_size") or 0.0)
        creation_low = float(rec.get("fvg_creation_low") or 0.0)
        creation_high = float(rec.get("fvg_creation_high") or 0.0)
        sl = creation_low if direction == 1 else creation_high
        if sl == 0.0:
            sl = float(rec.get("fvg_bottom") or 0.0) if direction == 1 else float(rec.get("fvg_top") or 0.0)
        if tick_size > 0 and sl != 0.0:
            sl = sl - tick_size if direction == 1 else sl + tick_size
        if entry == 0.0 or sl == 0.0:
            continue
        risk = (entry - sl) if direction == 1 else (sl - entry)
        if risk <= 0:
            continue
        tp = entry + 3 * risk if direction == 1 else entry - 3 * risk

        # simulate forward
        outcome = "open"
        rr = 0.0
        for j in range(i + 1, min(len(enriched), i + 51)):
            hi = enriched[j].get("high") or enriched[j].get("bar", {}).get("h", 0.0)
            lo = enriched[j].get("low") or enriched[j].get("bar", {}).get("l", 0.0)
            hit_sl = lo <= sl if direction == 1 else hi >= sl
            hit_tp = hi >= tp if direction == 1 else lo <= tp
            if hit_sl and hit_tp:
                outcome = "loss"; rr = -1.0; break
            if hit_sl:
                outcome = "loss"; rr = -1.0; break
            if hit_tp:
                outcome = "win"; rr = 3.0; break
        trades.append({"outcome": outcome, "rr": rr})

    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    opens = [t for t in trades if t["outcome"] == "open"]
    pf = (sum(t["rr"] for t in wins)) / (sum(abs(t["rr"]) for t in losses) or 1e-9)
    winrate = (len(wins) / len(trades) * 100) if trades else 0.0
    avg_rr = (sum(t["rr"] for t in trades) / len(trades)) if trades else 0.0
    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "open": len(opens),
        "winrate_pct": round(winrate, 2),
        "pf": round(pf, 3),
        "avg_rr": round(avg_rr, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate FVG Retest (module #12) on raw JSONL with TP/SL=1:3R.")
    parser.add_argument("--inputs", nargs="+", required=True, help="Raw JSONL file(s) from Ninja export.")
    args = parser.parse_args()

    summaries = []
    for path_str in args.inputs:
        path = Path(path_str)
        records = load_jsonl(path)
        summary = evaluate(records)
        summary["file"] = path.name
        summaries.append(summary)

    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
