#!/usr/bin/env python3
"""
Visualize Module 14 Wave Strength Logic
========================================
Visual chart showing:
- mgann_leg_index progression
- impulse wave strength (leg 1, 3, 5...)
- pullback wave strength (leg 2, 4, 6...)
- pb_wave_strength_ok flag
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from processor.modules.fix14_mgann_swing import Fix14MgannSwing

def flatten_bar_fields(bar_state):
    """Flatten nested 'bar' fields to root."""
    bar_obj = bar_state.get("bar", {})
    bar_state['ext_dir'] = bar_obj.get("ext_dir", 0)
    bar_state['ext_choch_up'] = bar_obj.get("ext_choch_up", False)
    bar_state['ext_choch_down'] = bar_obj.get("ext_choch_down", False)
    bar_state['ext_bos_up'] = bar_obj.get("ext_bos_up", False)
    bar_state['ext_bos_down'] = bar_obj.get("ext_bos_down", False)
    
    vol_stats = bar_obj.get('volume_stats', {})
    if vol_stats:
        bar_state['delta'] = vol_stats.get('delta_close', 0)
        bar_state['volume'] = vol_stats.get('total_volume', 0)
    return bar_state

# Test ONE file
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print("=" * 80)
print("MODULE 14 WAVE STRENGTH VISUALIZATION")
print("=" * 80)
print(f"\nFile: {test_file.name}\n")

mgann = Fix14MgannSwing()

# Collect all bars with leg info
bars_data = []

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar_state = json.loads(line.strip())
        
        # FLATTEN nested bar fields to root
        bar_state = flatten_bar_fields(bar_state)
        
        # Process through module
        bar_state = mgann.process_bar(bar_state)
        
        # Collect if leg index > 0
        leg_idx = bar_state.get('mgann_leg_index', 0)
        if leg_idx > 0:
            bars_data.append({
                'bar_num': i,
                'timestamp': bar_state.get('timestamp', ''),
                'leg_index': leg_idx,
                'wave_strength': bar_state.get('mgann_wave_strength', 0),
                'pb_ok': bar_state.get('pb_wave_strength_ok', False),
                'trend_dir': mgann.trend_dir,
                'leg_dir': mgann.last_swing_dir,
                # Internal state
                'impulse_strength': mgann.last_impulse_strength,
                'pb_strength': mgann.pullback_strength,
                'impulse_delta': mgann.last_impulse_delta,
                'pb_delta': mgann.pullback_delta,
            })

# Print summary table
print("\n" + "=" * 140)
print(f"{'Bar':<6} {'Time':<20} {'Leg':<5} {'Trend':<7} {'LegDir':<8} {'WaveStr':<9} {'PB_OK':<7} {'ImpStr':<8} {'PBStr':<8} {'ImpΔ':<10} {'PBΔ':<10}")
print("=" * 140)

for d in bars_data[-50:]:  # Last 50 bars with leg data
    bar_num = d['bar_num']
    time = d['timestamp'][11:19]  # HH:MM:SS
    leg = d['leg_index']
    trend = 'UP' if d['trend_dir'] == 1 else ('DN' if d['trend_dir'] == -1 else 'FLAT')
    leg_dir = 'UP' if d['leg_dir'] == 1 else ('DN' if d['leg_dir'] == -1 else 'FLAT')
    wave_str = d['wave_strength']
    pb_ok = '✅' if d['pb_ok'] else '❌'
    imp_str = d['impulse_strength']
    pb_str = d['pb_strength']
    imp_delta = f"{d['impulse_delta']:.1f}"
    pb_delta = f"{d['pb_delta']:.1f}"
    
    # Highlight leg changes
    marker = ''
    if leg_dir != d.get('prev_leg_dir', leg_dir):
        marker = '  <- LEG CHANGE'
    
    print(f"{bar_num:<6} {time:<20} {leg:<5} {trend:<7} {leg_dir:<8} {wave_str:<9} {pb_ok:<7} {imp_str:<8} {pb_str:<8} {imp_delta:<10} {pb_delta:<10}{marker}")
    
    d['prev_leg_dir'] = leg_dir

print("=" * 140)

# Summary statistics
legs = [d['leg_index'] for d in bars_data]
pb_oks = [d for d in bars_data if d['pb_ok']]

print(f"\n📊 SUMMARY:")
print(f"  Total bars with leg data: {len(bars_data)}")
print(f"  Unique legs seen: {sorted(set(legs))}")
print(f"  Max leg index: {max(legs)}")
print(f"  Bars with pb_wave_strength_ok=True: {len(pb_oks)}")
print(f"  PB OK rate: {len(pb_oks)/len(bars_data)*100:.1f}%")

# Show PB wave strength criteria details
print(f"\n📋 PULLBACK WAVE STRENGTH CRITERIA (Hybrid Rule v4):")
print(f"  1. pb_strength < 40")
print(f"  2. |pb_delta| < |impulse_delta| * 0.3")
print(f"  3. pb_volume < impulse_volume * 0.6")
print(f"  4. pb_delta >= -35 (uptrend) or <= 35 (downtrend)")
print(f"  5. pb_volume <= avg_volume * 1.0")
print(f"  6. pb_low > leg1_low (uptrend) or pb_high < leg1_high (downtrend)")

print(f"\n" + "=" * 80)
print("✅ VISUALIZATION COMPLETE")
print("=" * 80)
