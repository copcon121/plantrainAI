"""
Quick filter & winrate/PF evaluator for enriched JSONL (module #12 retest).

Default filter:
- fvg_retest_detected = True
- fvg_retest_quality_score >= 0.6
- fvg_retest_type in {"edge", "shallow"}
- signal_type in {"fvg_retest_bull", "fvg_retest_bear"}
- fvg_quality_score >= 0.5
- confluence_score >= 0.08
- mtf_is_aligned == True (if present)
- market_condition in {"trend", "balanced"} (if present)

Outcome model:
- Uses future bars' high/low to check TP/SL.
- If both TP/SL touch in the same bar, counts as loss (conservative).
- Skips trades with entry/sl/tp missing or 0.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_FILTER = {
    "min_retest_quality": 0.6,
    "allowed_retest_types": {"edge", "shallow"},
    "min_fvg_quality": 0.0,  # some pipelines may not score quality on retest bar
    "min_confluence": 0.0,  # allow low confluence during early screening
    "require_alignment": True,
    "allowed_market": set(),  # accept all unless specified
    "max_lookahead": 50,
}


def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def get_high_low(bar: Dict[str, Any]) -> Tuple[float, float]:
    """Gracefully fetch high/low from top-level or nested bar{}."""
    high = bar.get("high")
    low = bar.get("low")
    if high is None and isinstance(bar.get("bar"), dict):
        high = bar["bar"].get("h")
    if low is None and isinstance(bar.get("bar"), dict):
        low = bar["bar"].get("l")
    return float(high or 0.0), float(low or 0.0)


def passes_filter(rec: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
    if not rec.get("fvg_retest_detected"):
        return False
    if rec.get("fvg_retest_type") not in cfg["allowed_retest_types"]:
        return False
    if rec.get("signal_type") not in {"fvg_retest_bull", "fvg_retest_bear"}:
        return False
    if rec.get("fvg_retest_quality_score", 0) < cfg["min_retest_quality"]:
        return False
    if rec.get("fvg_quality_score", 0) < cfg["min_fvg_quality"]:
        return False
    if rec.get("confluence_score", 0) < cfg["min_confluence"]:
        return False
    if cfg["require_alignment"] and not rec.get("mtf_is_aligned", False):
        return False
    mc = rec.get("market_condition")
    if cfg["allowed_market"] and mc is not None and mc not in cfg["allowed_market"]:
        return False
    return True


def evaluate_trade(
    records: List[Dict[str, Any]],
    idx: int,
    direction: int,
    entry: float,
    sl: float,
    tp: float,
    max_lookahead: int,
) -> Optional[Dict[str, Any]]:
    """Evaluate TP/SL hit using future bars. Conservative if both hit."""
    if entry == 0 or sl == 0 or tp == 0:
        return None
    if direction not in (1, -1):
        return None

    risk = (entry - sl) if direction == 1 else (sl - entry)
    if risk <= 0:
        return None
    target = (tp - entry) if direction == 1 else (entry - tp)
    rr = target / risk if risk > 0 else 0

    last_bar = min(len(records) - 1, idx + max_lookahead)
    for j in range(idx + 1, last_bar + 1):
        hi, lo = get_high_low(records[j])
        if direction == 1:
            hit_sl = lo <= sl
            hit_tp = hi >= tp
        else:
            hit_sl = hi >= sl
            hit_tp = lo <= tp

        if hit_sl and hit_tp:
            return {"outcome": "loss", "bars_to_exit": j - idx, "rr": -1.0}
        if hit_sl:
            return {"outcome": "loss", "bars_to_exit": j - idx, "rr": -1.0}
        if hit_tp:
            return {"outcome": "win", "bars_to_exit": j - idx, "rr": rr}

    return {"outcome": "open", "bars_to_exit": max_lookahead, "rr": 0.0}


def summarize(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    opens = [t for t in trades if t["outcome"] == "open"]
    winrate = (len(wins) / len(trades)) * 100 if trades else 0.0
    gross_win = sum(t["rr"] for t in wins)
    gross_loss = sum(abs(t["rr"]) for t in losses) or 1e-9
    pf = gross_win / gross_loss
    avg_rr = sum(t["rr"] for t in trades) / len(trades) if trades else 0.0
    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "open": len(opens),
        "winrate_pct": round(winrate, 2),
        "pf": round(pf, 3),
        "avg_rr": round(avg_rr, 3),
        "gross_win_rr": round(gross_win, 3),
        "gross_loss_rr": round(gross_loss, 3),
    }


def process_file(path: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    records = list(load_jsonl(path))
    trades: List[Dict[str, Any]] = []

    for i, rec in enumerate(records):
        if not passes_filter(rec, cfg):
            continue
        direction = 1 if rec.get("signal_type") == "fvg_retest_bull" else -1

        # Entry/SL/TP fallbacks: prefer stop/target module outputs
        entry = float(rec.get("entry") or rec.get("close") or 0.0)
        sl = float(
            rec.get("sl")
            or rec.get("stop_price")
            or rec.get("stop_invalidation_level")
            or 0.0
        )
        # Use first target with non-zero price
        tp_candidates = [
            rec.get("tp"),
            rec.get("tp1_price"),
            rec.get("tp2_price"),
            rec.get("tp3_price"),
        ]
        tp = float(next((x for x in tp_candidates if x not in (None, 0, 0.0)), 0.0))

        # Fallback: derive SL/TP from FVG bounds if missing
        if sl == 0.0:
            fvg_top = float(rec.get("fvg_top") or 0.0)
            fvg_bottom = float(rec.get("fvg_bottom") or 0.0)
            if direction == 1 and fvg_bottom > 0:
                sl = fvg_bottom
            elif direction == -1 and fvg_top > 0:
                sl = fvg_top
        if tp == 0.0 and sl != 0.0:
            risk = (entry - sl) if direction == 1 else (sl - entry)
            if risk > 0:
                tp = entry + 3 * risk if direction == 1 else entry - 3 * risk

        outcome = evaluate_trade(
            records,
            i,
            direction,
            entry,
            sl,
            tp,
            max_lookahead=cfg["max_lookahead"],
        )
        if outcome is None:
            continue
        trades.append(outcome | {"index": i, "direction": direction})

    summary = summarize(trades)
    summary["file"] = path.name
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter enriched JSONL and compute winrate/PF.")
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Paths to enriched JSONL files (can list multiple).",
    )
    parser.add_argument(
        "--max-lookahead",
        type=int,
        default=DEFAULT_FILTER["max_lookahead"],
        help="Bars to look ahead for TP/SL hit.",
    )
    args = parser.parse_args()

    cfg = DEFAULT_FILTER.copy()
    cfg["max_lookahead"] = args.max_lookahead

    summaries = []
    for p in args.inputs:
        summaries.append(process_file(Path(p), cfg))

    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
