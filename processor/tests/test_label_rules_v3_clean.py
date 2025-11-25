#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Label Rules v3 with real multi-day M1 data.
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from processor.modules.fix14_mgann_swing import Fix14MgannSwing


def check_long_signal(bar):
    """LONG: Bullish pullback in early leg of M5 downtrend."""
    mtf = bar.get('mtf_context', {}).get('m5', {})
    bar_data = bar.get('bar', {})
    
    m5_bearish = mtf.get('choch_down_pulse', False) or mtf.get('structure_dir', 0) == -1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    pb_ok = bar.get('pb_wave_strength_ok', False)
    fvg_bull = bar_data.get('has_fvg_bull', False)
    
    return m5_bearish and early_leg and pb_ok and fvg_bull


def check_short_signal(bar):
    """SHORT: Bearish pullback in early leg of M5 uptrend."""
    mtf = bar.get('mtf_context', {}).get('m5', {})
    bar_data = bar.get('bar', {})
    
    m5_bullish = mtf.get('choch_up_pulse', False) or mtf.get('structure_dir', 0) == 1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    pb_ok = bar.get('pb_wave_strength_ok', False)
    fvg_bear = bar_data.get('has_fvg_bear', False)
    
    return m5_bullish and early_leg and pb_ok and fvg_bear


print("=" * 80)
print("TESTING LABEL RULES V3 - 12 DAYS OF DATA")
print("=" * 80)

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
files = sorted(export_dir.glob("*M1*.jsonl"))

print(f"\nFound {len(files)} M1 files")

all_long = []
all_short = []
total_bars = 0

for jsonl_file in files:
    print(f"\nProcessing {jsonl_file.name}...", end=" ")
    
    # Load data
    with open(jsonl_file, 'r') as f:
        bars = [json.loads(line) for line in f]
    
    # Initialize Module 14
    module14 = Fix14MgannSwing(threshold_ticks=6)
    
    # Process bars
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
            # External CHoCH/BOS fields (REQUIRED for leg detection!)
            'ext_bos_up': bar_data.get('ext_bos_up', False),
            'ext_bos_down': bar_data.get('ext_bos_down', False),
            'ext_choch_up': bar_data.get('ext_choch_up', False),
            'ext_choch_down': bar_data.get('ext_choch_down', False),
            'ext_dir': bar_data.get('ext_dir', 0),
        }
        
        processed = module14.process_bar(bar_state)
        results.append(processed)
    
    # Apply rules
    for i, bar in enumerate(results):
        if check_long_signal(bar):
            all_long.append((jsonl_file.name, i, bar))
        if check_short_signal(bar):
            all_short.append((jsonl_file.name, i, bar))
    
    total_bars += len(results)
    print(f"{len(results)} bars, {len([r for r in results if check_long_signal(r)])} LONG, {len([r for r in results if check_short_signal(r)])} SHORT")

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

if all_long:
    print(f"\n📌 SAMPLE LONG SIGNALS (first 3 of {len(all_long)}):")
    for i, (file, idx, bar) in enumerate(all_long[:3], 1):
        print(f"\n  {i}. {file} bar {idx} @ {bar.get('timestamp', '')}")
        print(f"     Price: {bar.get('close', 0):.2f}, Leg: {bar.get('mgann_leg_index', 0)}")

if all_short:
    print(f"\n📌 SAMPLE SHORT SIGNALS (first 3 of {len(all_short)}):")
    for i, (file, idx, bar) in enumerate(all_short[:3], 1):
        print(f"\n  {i}. {file} bar {idx} @ {bar.get('timestamp', '')}")
        print(f"     Price: {bar.get('close', 0):.2f}, Leg: {bar.get('mgann_leg_index', 0)}")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE!")
print("=" * 80)
