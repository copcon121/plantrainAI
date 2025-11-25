#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Label Rules v3 FINAL - Signal on NEW FVG only

LONG: M1 bearish + leg 1-2 + NEW FVG bullish
SHORT: M1 bullish + leg 1-2 + NEW FVG bearish
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from processor.modules.fix14_mgann_swing import Fix14MgannSwing


def check_long_signal(bar):
    """
    LONG: Bullish pullback after M1 bearish structure.
    
    Conditions:
    1. M1 ext_dir = -1 (bearish)
    2. Early leg (1-2)
    3. NEW FVG bullish detected THIS bar (not just active)
    """
    bar_data = bar.get('bar', {})
    
    m1_bearish = bar.get('ext_dir', 0) == -1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    
    # NEW FVG detected (not just active!)
    fvg_new = bar_data.get('fvg_detected', False)
    fvg_bullish = bar_data.get('fvg_type') == 'bullish'
    
    return m1_bearish and early_leg and fvg_new and fvg_bullish


def check_short_signal(bar):
    """
    SHORT: Bearish pullback after M1 bullish structure.
    
    Conditions:
    1. M1 ext_dir = 1 (bullish)
    2. Early leg (1-2)
    3. NEW FVG bearish detected THIS bar
    """
    bar_data = bar.get('bar', {})
    
    m1_bullish = bar.get('ext_dir', 0) == 1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    
    # NEW FVG detected
    fvg_new = bar_data.get('fvg_detected', False)
    fvg_bearish = bar_data.get('fvg_type') == 'bearish'
    
    return m1_bullish and early_leg and fvg_new and fvg_bearish


print("=" * 80)
print("LABEL RULES V3 FINAL - NEW FVG ONLY")
print("=" * 80)

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
files = sorted(export_dir.glob("*M1*.jsonl"))

print(f"\nFound {len(files)} M1 files")
print("LONG:  M1 bearish + leg 1-2 + NEW FVG bull")
print("SHORT: M1 bullish + leg 1-2 + NEW FVG bear")

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
print("📊 FINAL RESULTS")
print("=" * 80)
print(f"\nTotal bars: {total_bars}")
print(f"Total days: {len(files)}")
print(f"Avg bars/day: {total_bars/len(files):.0f}")

print(f"\n🎯 SIGNALS:")
print(f"  LONG: {len(all_long)}")
print(f"  SHORT: {len(all_short)}")
print(f"  TOTAL: {len(all_long) + len(all_short)}")
print(f"  Per day: {(len(all_long) + len(all_short))/len(files):.1f}")

print(f"\n📉 IMPROVEMENT:")
print(f"  Before (active FVG): 1482 signals (123.5/day)")
print(f"  After (NEW FVG only): {len(all_long) + len(all_short)} signals ({(len(all_long) + len(all_short))/len(files):.1f}/day)")
if len(all_long) + len(all_short) > 0:
    print(f"  Reduction: {(1 - (len(all_long) + len(all_short))/1482)*100:.1f}%")

if all_long:
    print(f"\n📌 SAMPLE LONG SIGNALS (first 10 of {len(all_long)}):")
    for i, (file, idx, bar) in enumerate(all_long[:10], 1):
        bar_data = bar.get('bar', {})
        print(f"\n  {i}. {file} bar {idx}")
        print(f"     Time: {bar.get('timestamp', '')}")
        print(f"     Price: {bar.get('close', 0):.2f}")
        print(f"     M1 dir: {bar.get('ext_dir', 0)}")
        print(f"     Leg: {bar.get('mgann_leg_index', 0)}")
        print(f"     FVG: NEW {bar_data.get('fvg_type')} @ {bar_data.get('fvg_bottom', 0):.2f}-{bar_data.get('fvg_top', 0):.2f}")

if all_short:
    print(f"\n📌 SAMPLE SHORT SIGNALS (first 10 of {len(all_short)}):")
    for i, (file, idx, bar) in enumerate(all_short[:10], 1):
        bar_data = bar.get('bar', {})
        print(f"\n  {i}. {file} bar {idx}")
        print(f"     Time: {bar.get('timestamp', '')}")
        print(f"     Price: {bar.get('close', 0):.2f}")
        print(f"     M1 dir: {bar.get('ext_dir', 0)}")
        print(f"     Leg: {bar.get('mgann_leg_index', 0)}")
        print(f"     FVG: NEW {bar_data.get('fvg_type')} @ {bar_data.get('fvg_bottom', 0):.2f}-{bar_data.get('fvg_top', 0):.2f}")

print("\n" + "=" * 80)
print("✅ LABEL RULES V3 FINAL TEST COMPLETE!")
print("=" * 80)
