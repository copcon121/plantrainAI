"""
Quick field-quality checker for exported JSONL files.

Usage:
  python -m processor.validation.analyze_fields --inputs file1.jsonl file2.jsonl --threshold 0.5

If you omit --inputs, the script will scan the current working directory for *.jsonl.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, List


# Fields we care about for data completeness
DEFAULT_FIELDS: List[str] = [
    "di_plus_14",
    "di_minus_14",
    "adx_14",
    "htf_high",
    "htf_low",
    "htf_close",
    "htf_ema_20",
    "htf_ema_50",
    "nearest_liquidity_high",
    "nearest_liquidity_low",
    "liquidity_high_type",
    "liquidity_low_type",
]


def find_jsonl_files(paths: Iterable[str]) -> List[Path]:
    files: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.glob("*.jsonl")))
        elif p.is_file():
            files.append(p)
    return files


def analyze_file(path: Path, fields: List[str]) -> None:
    counts = Counter()
    zeros = Counter()
    nulls = Counter()
    total_rows = 0

    with path.open(encoding="utf-8") as f:
        for line in f:
            total_rows += 1
            try:
                obj = json.loads(line)
            except Exception:
                continue
            counts.update(fields)
            for fld in fields:
                val = obj.get(fld, None)
                if val is None:
                    nulls[fld] += 1
                elif isinstance(val, (int, float)):
                    if val == 0:
                        zeros[fld] += 1
                else:
                    if val in ("", "none", "None"):
                        zeros[fld] += 1

    print(f"\nFile: {path}")
    print(f"Total rows: {total_rows}")
    for fld in fields:
        t = counts[fld] or 1
        z_ratio = zeros[fld] / t
        n_ratio = nulls[fld] / t
        print(f"  {fld:24} zero/empty={z_ratio:6.2%}  null/miss={n_ratio:6.2%}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze field completeness in JSONL exports.")
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=None,
        help="List of JSONL files or directories to scan (default: all *.jsonl in cwd).",
    )
    parser.add_argument(
        "--fields",
        nargs="*",
        default=DEFAULT_FIELDS,
        help="Fields to analyze (default: key HTF/DI/liquidity fields).",
    )
    args = parser.parse_args()

    if args.inputs:
        files = find_jsonl_files(args.inputs)
    else:
        files = sorted(Path(".").glob("*.jsonl"))

    if not files:
        print("No JSONL files found.")
        return

    for fp in files:
        analyze_file(fp, args.fields)


if __name__ == "__main__":
    main()
