#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Label Rules v3 FINAL + FVG Retest Limit

Each FVG can generate max 3 signals:
- Signal 1: When FVG first created (NEW)
- Signal 2: First retest of FVG
- Signal 3: Second retest of FVG
- No signal: Third retest or later (invalid)
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from processor.modules.fix14_mgann_swing import Fix14MgannSwing


class FVGTracker:
    """Track FVG zones and their signal counts."""
    
    def __init__(self):
        self.active_fvgs = []  # List of (top, bottom, type, signal_count, bar_created)
    
    def add_fvg(self, top, bottom, fvg_type, bar_idx):
        """Add new FVG zone with signal_count = 1 (NEW FVG is first signal)."""
        self.active_fvgs.append({
            'top': top,
            'bottom': bottom,
            'type': fvg_type,
            'signal_count': 1,  # NEW FVG = signal #1
            'bar_created': bar_idx,
        })
    
    def check_retest(self, price, fvg_type):
        """
        Check if price retests any active FVG.
        Returns (can_signal, fvg_info).
        Can signal if signal_count < 3 (allow NEW + 2 retests = 3 total).
        """
        for fvg in self.active_fvgs:
            if fvg['type'] != fvg_type:
                continue
            
            # Check if price is in FVG zone
            if fvg['bottom'] <= price <= fvg['top']:
                # Found retest!
                if fvg['signal_count'] < 3:  # Allow 3 signals total
                    fvg['signal_count'] += 1
                    return True, fvg
                else:
                    # Already 3 signals (1 NEW + 2 retests), invalid
                    return False, fvg
        
        return False, None
    
    def cleanup_old_fvgs(self, current_bar, max_age=100):
        """Remove FVGs older than max_age bars."""
        self.active_fvgs = [
            fvg for fvg in self.active_fvgs
            if current_bar - fvg['bar_created'] < max_age
        ]


def check_long_signal(bar, bar_idx, fvg_tracker):
    """LONG with FVG retest limit."""
    bar_data = bar.get('bar', {})
    
    # Conditions 1-2
    m1_bearish = bar.get('ext_dir', 0) == -1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    
    if not (m1_bearish and early_leg):
        return False
    
    # Condition 3: NEW FVG or valid retest
    fvg_new = bar_data.get('fvg_detected', False)
    fvg_bullish = bar_data.get('fvg_type') == 'bullish'
    
    if fvg_new and fvg_bullish:
        # NEW FVG created this bar
        fvg_top = bar_data.get('fvg_top', 0)
        fvg_bottom = bar_data.get('fvg_bottom', 0)
        fvg_tracker.add_fvg(fvg_top, fvg_bottom, 'bullish', bar_idx)
        return True  # Signal on NEW FVG
    
    # Check if current bar retests existing FVG
    price = bar.get('close', 0)
    can_signal, fvg_info = fvg_tracker.check_retest(price, 'bullish')
    
    return can_signal


def check_short_signal(bar, bar_idx, fvg_tracker):
    """SHORT with FVG retest limit."""
    bar_data = bar.get('bar', {})
    
    m1_bullish = bar.get('ext_dir', 0) == 1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    
    if not (m1_bullish and early_leg):
        return False
    
    fvg_new = bar_data.get('fvg_detected', False)
    fvg_bearish = bar_data.get('fvg_type') == 'bearish'
    
    if fvg_new and fvg_bearish:
        fvg_top = bar_data.get('fvg_top', 0)
        fvg_bottom = bar_data.get('fvg_bottom', 0)
        fvg_tracker.add_fvg(fvg_top, fvg_bottom, 'bearish', bar_idx)
        return True
    
    price = bar.get('close', 0)
    can_signal, fvg_info = fvg_tracker.check_retest(price, 'bearish')
    
    return can_signal


print("=" * 80)
print("LABEL RULES V3 FINAL + FVG RETEST LIMIT (MAX 3 SIGNALS: NEW + 2 RETESTS)")
print("=" * 80)

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
files = sorted(export_dir.glob("*M1*.jsonl"))

print(f"\nFound {len(files)} M1 files")
print("Rule: Each FVG can signal max 3 times (NEW + 2 retests)")

all_long = []
all_short = []
total_bars = 0

for jsonl_file in files:
    print(f"\nProcessing {jsonl_file.name}...", end=" ")
    
    with open(jsonl_file, 'r') as f:
        bars = [json.loads(line) for line in f]
    
    module14 = Fix14MgannSwing(threshold_ticks=6)
    fvg_tracker = FVGTracker()  # NEW: Track FVG retests
    
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
    
    # Apply rules with FVG tracking
    long_count = 0
    short_count = 0
    
    for i, bar in enumerate(results):
        if check_long_signal(bar, i, fvg_tracker):
            all_long.append((jsonl_file.name, i, bar))
            long_count += 1
        
        if check_short_signal(bar, i, fvg_tracker):
            all_short.append((jsonl_file.name, i, bar))
            short_count += 1
        
        # Cleanup old FVGs every 50 bars
        if i % 50 == 0:
            fvg_tracker.cleanup_old_fvgs(i, max_age=100)
    
    total_bars += len(results)
    print(f"{len(results)} bars, {long_count} LONG, {short_count} SHORT")

print("\n" + "=" * 80)
print("📊 FINAL RESULTS (WITH FVG RETEST LIMIT)")
print("=" * 80)
print(f"\nTotal bars: {total_bars}")
print(f"Total days: {len(files)}")

print(f"\n🎯 SIGNALS:")
print(f"  LONG: {len(all_long)}")
print(f"  SHORT: {len(all_short)}")
print(f"  TOTAL: {len(all_long) + len(all_short)}")
print(f"  Per day: {(len(all_long) + len(all_short))/len(files):.1f}")

print(f"\n📊 COMPARISON:")
print(f"  Before (NEW FVG only): 202 signals (16.8/day)")
print(f"  After (+ 1st retest): {len(all_long) + len(all_short)} signals ({(len(all_long) + len(all_short))/len(files):.1f}/day)")
if len(all_long) + len(all_short) > 202:
    print(f"  Increase: {((len(all_long) + len(all_short))/202 - 1)*100:.1f}%")

if all_long:
    print(f"\n📌 SAMPLE LONG SIGNALS (first 5 of {len(all_long)}):")
    for i, (file, idx, bar) in enumerate(all_long[:5], 1):
        bar_data = bar.get('bar', {})
        fvg_new = bar_data.get('fvg_detected', False)
        signal_type = "NEW FVG" if fvg_new else "RETEST"
        
        print(f"\n  {i}. {file} bar {idx} ({signal_type})")
        print(f"     Time: {bar.get('timestamp', '')}")
        print(f"     Price: {bar.get('close', 0):.2f}")
        print(f"     Leg: {bar.get('mgann_leg_index', 0)}")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE!")
print("=" * 80)
