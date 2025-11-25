#!/usr/bin/env python3
"""
Test Label Rules v3 + PB Wave Strength (LOOSE v0.1)

Add back pb_wave_strength_ok with loose thresholds.
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

def check_long_signal(bar, bar_idx, fvg_tracker):
    """LONG with pb_wave_strength_ok (LOOSE)."""
    bar_data = bar.get('bar', {})
    
    # Conditions
    m1_bearish = bar.get('ext_dir', 0) == -1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    pb_ok = bar.get('pb_wave_strength_ok', False)  # NEW: Added back!
    
    if not (m1_bearish and early_leg and pb_ok):
        return False
    
    # FVG (same as before)
    fvg_new = bar_data.get('fvg_detected', False)
    fvg_bullish = bar_data.get('fvg_type') == 'bullish'
    
    if fvg_new and fvg_bullish:
        fvg_top = bar_data.get('fvg_top', 0)
        fvg_bottom = bar_data.get('fvg_bottom', 0)
        fvg_tracker.add_fvg(fvg_top, fvg_bottom, 'bullish', bar_idx)
        return True
    
    price = bar.get('close', 0)
    can_signal, _ = fvg_tracker.check_retest(price, 'bullish')
    return can_signal

def check_short_signal(bar, bar_idx, fvg_tracker):
    """SHORT with pb_wave_strength_ok (LOOSE)."""
    bar_data = bar.get('bar', {})
    
    m1_bullish = bar.get('ext_dir', 0) == 1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    pb_ok = bar.get('pb_wave_strength_ok', False)  # NEW: Added back!
    
    if not (m1_bullish and early_leg and pb_ok):
        return False
    
    fvg_new = bar_data.get('fvg_detected', False)
    fvg_bearish = bar_data.get('fvg_type') == 'bearish'
    
    if fvg_new and fvg_bearish:
        fvg_top = bar_data.get('fvg_top', 0)
        fvg_bottom = bar_data.get('fvg_bottom', 0)
        fvg_tracker.add_fvg(fvg_top, fvg_bottom, 'bearish', bar_idx)
        return True
    
    price = bar.get('close', 0)
    can_signal, _ = fvg_tracker.check_retest(price, 'bearish')
    return can_signal

# FVG Tracker class (same as before)
class FVGTracker:
    def __init__(self):
        self.active_fvgs = []
    
    def add_fvg(self, top, bottom, fvg_type, bar_idx):
        self.active_fvgs.append({
            'top': top, 'bottom': bottom, 'type': fvg_type,
            'signal_count': 1, 'bar_created': bar_idx,
        })
    
    def check_retest(self, price, fvg_type):
        for fvg in self.active_fvgs:
            if fvg['type'] != fvg_type:
                continue
            if fvg['bottom'] <= price <= fvg['top']:
                if fvg['signal_count'] < 3:
                    fvg['signal_count'] += 1
                    return True, fvg
                else:
                    return False, fvg
        return False, None
    
    def cleanup_old_fvgs(self, current_bar, max_age=100):
        self.active_fvgs = [f for f in self.active_fvgs 
                           if current_bar - f['bar_created'] < max_age]

print("=" * 80)
print("LABEL RULES V3 + PB WAVE STRENGTH (LOOSE v0.1)")
print("=" * 80)

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
files = sorted(export_dir.glob("*M1*.jsonl"))

print(f"\nFound {len(files)} M1 files")
print("Rules: M1 context + leg 1-2 + PB strength OK (LOOSE) + FVG")

all_long = []
all_short = []

for jsonl_file in files:
    print(f"\nProcessing {jsonl_file.name}...", end=" ")
    
    with open(jsonl_file, 'r') as f:
        bars = [json.loads(line) for line in f]
    
    module14 = Fix14MgannSwing(threshold_ticks=6)
    fvg_tracker = FVGTracker()
    
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
            'bar': bar_data,
            'ext_bos_up': bar_data.get('ext_bos_up', False),
            'ext_bos_down': bar_data.get('ext_bos_down', False),
            'ext_choch_up': bar_data.get('ext_choch_up', False),
            'ext_choch_down': bar_data.get('ext_choch_down', False),
            'ext_dir': bar_data.get('ext_dir', 0),
        }
        
        processed = module14.process_bar(bar_state)
        results.append(processed)
    
    long_count = 0
    short_count = 0
    
    for i, bar in enumerate(results):
        if check_long_signal(bar, i, fvg_tracker):
            all_long.append((jsonl_file.name, i, bar))
            long_count += 1
        if check_short_signal(bar, i, fvg_tracker):
            all_short.append((jsonl_file.name, i, bar))
            short_count += 1
        
        if i % 50 == 0:
            fvg_tracker.cleanup_old_fvgs(i, max_age=100)
    
    print(f"{len(results)} bars, {long_count} LONG, {short_count} SHORT")

print("\n" + "=" * 80)
print("📊 RESULTS WITH PB WAVE STRENGTH (LOOSE)")
print("=" * 80)

print(f"\n🎯 SIGNALS:")
print(f"  LONG: {len(all_long)}")
print(f"  SHORT: {len(all_short)}")
print(f"  TOTAL: {len(all_long) + len(all_short)}")
print(f"  Per day: {(len(all_long) + len(all_short))/len(files):.1f}")

print(f"\n📊 COMPARISON:")
print(f"  Without pb_ok: 276 signals (23.0/day)")
print(f"  With pb_ok (LOOSE): {len(all_long) + len(all_short)} signals ({(len(all_long) + len(all_short))/len(files):.1f}/day)")

if len(all_long) > 0:
    print(f"\n📌 SAMPLE LONG (first 3):")
    for i, (file, idx, bar) in enumerate(all_long[:3], 1):
        print(f"  {i}. {file} bar {idx} @ {bar.get('timestamp', '')}")
        print(f"     Price: {bar.get('close', 0):.2f}, Leg: {bar.get('mgann_leg_index', 0)}")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE!")
print("=" * 80)
