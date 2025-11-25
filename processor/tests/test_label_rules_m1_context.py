#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Label Rules v3 - FVG + Early Leg + M1 CHoCH/BOS

LONG: M1 CHoCH/BOS DOWN → Bullish pullback in leg 1-2 → FVG bullish
SHORT: M1 CHoCH/BOS UP → Bearish pullback in leg 1-2 → FVG bearish
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from processor.modules.fix14_mgann_swing import Fix14MgannSwing


def check_long_signal(bar):
    """
    LONG: Bullish pullback after M1 bearish structure break.
    
    Conditions:
    1. M1 ext_dir = -1 (bearish structure from CHoCH/BOS down)
    2. Early leg (1-2)
    3. FVG bullish (entry zone)
    """
    # M1 structure bearish (from CHoCH/BOS down)
    m1_bearish = bar.get('ext_dir', 0) == -1
    
    # Early leg
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    
    # FVG bullish
    bar_data = bar.get('bar', {})
    fvg_bull = bar_data.get('has_fvg_bull', False)
    
    return m1_bearish and early_leg and fvg_bull


def check_short_signal(bar):
    """
    SHORT: Bearish pullback after M1 bullish structure break.
    
    Conditions:
    1. M1 ext_dir = 1 (bullish structure from CHoCH/BOS up)
    2. Early leg (1-2)
    3. FVG bearish (entry zone)
    """
    # M1 structure bullish (from CHoCH/BOS up)
    m1_bullish = bar.get('ext_dir', 0) == 1
    
    # Early leg
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    
    # FVG bearish
    bar_data = bar.get('bar', {})
    fvg_bear = bar_data.get('has_fvg_bear', False)
    
    return m1_bullish and early_leg and fvg_bear


print("=" * 80)
print("TESTING LABEL RULES V3 - FVG + EARLY LEG + M1 CHOCH/BOS")
print("=" * 80)

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
files = sorted(export_dir.glob("*M1*.jsonl"))

print(f"\nFound {len(files)} M1 files")
print("LONG:  M1 bearish (CHoCH/BOS down) + leg 1-2 + FVG bull")
print("SHORT: M1 bullish (CHoCH/BOS up) + leg 1-2 + FVG bear")

all_long = []
all_short = []
total_bars = 0

for jsonl_file in files:
    print(f"\nProcessing {jsonl_file.name}...", end=" ")
    
    with open(jsonl_file, 'r') as f:
        bars = [json.loads(line) for line in f]
    
    module14 = Fix14MgannSwing(threshold_ticks=6)
    
    results = []
    for raw_bar in bars:
        bar_data = raw_bar.get('bar', {})
        vol_stats = bar_data.get('volume_stats', {})
        
        bar_state = {
            'high': bar_data.get('h', 0),
            'low': bar_data.get('l', 0),
            'open': bar_data.get('o', 0),
            'close': bar_data.get('c', 0),
            'volume': vol_stats.get('total_volume', 0),
            'delta': vol_stats.get('delta_close', 0),
            'delta_close': vol_stats.get('delta_close', 0),
            'tick_size': 0.1,
            'timestamp': raw_bar.get('timestamp', ''),
            'mtf_context': raw_bar.get('mtf_context', {}),
            'bar': bar_data,
            # External CHoCH/BOS (required!)
            'ext_bos_up': bar_data.get('ext_bos_up', False),
            'ext_bos_down': bar_data.get('ext_bos_down', False),
            'ext_choch_up': bar_data.get('ext_choch_up', False),
            'ext_choch_down': bar_data.get('ext_choch_down', False),
            'ext_dir': bar_data.get('ext_dir', 0),
        }
        
        processed = module14.process_bar(bar_state)
        results.append(processed)
    
    # Apply rules
    long_count = sum(1 for r in results if check_long_signal(r))
    short_count = sum(1 for r in results if check_short_signal(r))
    
    for i, bar in enumerate(results):
        if check_long_signal(bar):
            all_long.append((jsonl_file.name, i, bar))
        if check_short_signal(bar):
            all_short.append((jsonl_file.name, i, bar))
    
    total_bars += len(results)
    print(f"{len(results)} bars, {long_count} LONG, {short_count} SHORT")

print("\n" + "=" * 80)
print("📊 RESULTS")
print("=" * 80)
print(f"\nTotal bars: {total_bars}")
print(f"Total days: {len(files)}")
print(f"Avg bars/day: {total_bars/len(files):.0f}")
print(f"\n🎯 SIGNALS:")
print(f"  LONG: {len(all_long)}")
print(f"  SHORT: {len(all_short)}")
print(f"  TOTAL: {len(all_long) + len(all_short)}")
print(f"  Per day: {(len(all_long) + len(all_short))/len(files):.1f}")

# Show reduction vs simplified
print(f"\n📉 FILTERING EFFECT:")
print(f"  Before (simplified): ~3263 signals")
print(f"  After (+ M1 context): {len(all_long) + len(all_short)} signals")
print(f"  Reduction: {(1 - (len(all_long) + len(all_short))/3263)*100:.1f}%")

if all_long:
    print(f"\n📌 SAMPLE LONG SIGNALS (first 5 of {len(all_long)}):")
    for i, (file, idx, bar) in enumerate(all_long[:5], 1):
        print(f"\n  {i}. {file} bar {idx}")
        print(f"     Time: {bar.get('timestamp', '')}")
        print(f"     Price: {bar.get('close', 0):.2f}")
        print(f"     M1 dir: {bar.get('ext_dir', 0)} (bearish)")
        print(f"     Leg: {bar.get('mgann_leg_index', 0)}")
        print(f"     FVG: bull={bar.get('bar', {}).get('has_fvg_bull', False)}")

if all_short:
    print(f"\n📌 SAMPLE SHORT SIGNALS (first 5 of {len(all_short)}):")
    for i, (file, idx, bar) in enumerate(all_short[:5], 1):
        print(f"\n  {i}. {file} bar {idx}")
        print(f"     Time: {bar.get('timestamp', '')}")
        print(f"     Price: {bar.get('close', 0):.2f}")
        print(f"     M1 dir: {bar.get('ext_dir', 0)} (bullish)")
        print(f"     Leg: {bar.get('mgann_leg_index', 0)}")
        print(f"     FVG: bear={bar.get('bar', {}).get('has_fvg_bear', False)}")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE!")
print("=" * 80)
