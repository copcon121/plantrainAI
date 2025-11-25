#!/usr/bin/env python3
"""
Inspect data fields in module14_results.json
to understand what fields are available
"""

import json
from pathlib import Path


def main():
    print("\n" + "=" * 70)
    print("  DATA FIELD INSPECTION")
    print("=" * 70 + "\n")

    data_file = Path(__file__).parent / "module14_results.json"

    with open(data_file, 'r') as f:
        bars = json.load(f)

    print(f"Total bars: {len(bars)}\n")

    # Get all unique fields across first 10 bars
    all_fields = set()
    for bar in bars[:10]:
        all_fields.update(bar.keys())

    print(f"All fields found in first 10 bars:")
    print("-" * 70)

    for field in sorted(all_fields):
        # Get sample value
        sample_val = None
        for bar in bars[:10]:
            if field in bar:
                sample_val = bar[field]
                break

        val_type = type(sample_val).__name__
        val_str = str(sample_val)[:50]

        print(f"  {field:30s} | {val_type:10s} | {val_str}")

    # Check for strategy-required fields
    print("\n" + "=" * 70)
    print("STRATEGY V1 REQUIRED FIELDS CHECK")
    print("=" * 70)

    required_fields = {
        'mgann_leg_index': 'MGann leg number (1-2 for early entry)',
        'fvg_detected': 'FVG detection flag',
        'fvg_type': 'FVG type (bullish/bearish)',
        'ext_choch_down': 'CHoCH down flag (LONG setup)',
        'ext_choch_up': 'CHoCH up flag (SHORT setup)',
        'last_swing_low': 'Last swing low for LONG',
        'last_swing_high': 'Last swing high for SHORT',
    }

    print()
    for field, desc in required_fields.items():
        found = field in all_fields
        status = "✓" if found else "✗"

        # Count how many bars have this field
        count = sum(1 for bar in bars if field in bar)

        print(f"{status} {field:20s} - {desc}")
        if found:
            print(f"    Found in {count}/{len(bars)} bars ({count/len(bars)*100:.1f}%)")

    # Check mgann fields
    print("\n" + "=" * 70)
    print("MGANN-RELATED FIELDS")
    print("=" * 70 + "\n")

    mgann_fields = [f for f in sorted(all_fields) if 'mgann' in f.lower()]

    if mgann_fields:
        print("MGann fields found:")
        for field in mgann_fields:
            sample_val = bars[0].get(field, 'N/A')
            print(f"  {field:35s} = {sample_val}")
    else:
        print("⚠️  No MGann fields found!")

    # Check ext/choch fields
    print("\n" + "=" * 70)
    print("EXTERNAL STRUCTURE FIELDS")
    print("=" * 70 + "\n")

    ext_fields = [f for f in sorted(all_fields) if 'ext_' in f.lower() or 'choch' in f.lower()]

    if ext_fields:
        print("External structure fields found:")
        for field in ext_fields:
            sample_val = bars[0].get(field, 'N/A')
            print(f"  {field:35s} = {sample_val}")
    else:
        print("⚠️  No external structure fields found!")

    # Check FVG fields
    print("\n" + "=" * 70)
    print("FVG FIELDS")
    print("=" * 70 + "\n")

    fvg_fields = [f for f in sorted(all_fields) if 'fvg' in f.lower()]

    if fvg_fields:
        print("FVG fields found:")
        for field in fvg_fields:
            sample_val = bars[0].get(field, 'N/A')
            print(f"  {field:35s} = {sample_val}")
    else:
        print("⚠️  No FVG fields found!")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
