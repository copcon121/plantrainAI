#!/usr/bin/env python3
"""Debug strategy conditions - find why 0 signals"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1

# Load data
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"DEBUG: Strategy Conditions Check")
print(f"File: {test_file.name}\n")

mgann = Fix14MgannSwing()
strategy = Fix16StrategyV1()

# Track condition passes
stats = {
    'total_bars': 0,
    'choch_up': 0,
    'choch_down': 0,
    'ext_dir_1': 0,
    'ext_dir_minus1': 0,
    'leg_1_or_2': 0,
    'fvg_bullish': 0,
    'fvg_bearish': 0,
    'all_long_conditions': 0,
    'all_short_conditions': 0,
}

choch_bars = []

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar = json.loads(line.strip())
        
        # Flatten
        bar_obj = bar.get('bar', {})
        bar['ext_dir'] = bar_obj.get('ext_dir', 0)
        bar['ext_choch_up'] = bar_obj.get('ext_choch_up', False)
        bar['ext_choch_down'] = bar_obj.get('ext_choch_down', False)
        bar['ext_bos_up'] = bar_obj.get('ext_bos_up', False)
        bar['ext_bos_down'] = bar_obj.get('ext_bos_down', False)
        vol_stats = bar_obj.get('volume_stats', {})
        if vol_stats:
            bar['delta'] = vol_stats.get('delta_close', 0)
            bar['volume'] = vol_stats.get('total_volume', 0)
        bar['fvg_detected'] = bar_obj.get('fvg_detected', False)
        bar['fvg_type'] = bar_obj.get('fvg_type')
        bar['fvg_top'] = bar_obj.get('fvg_top')
        bar['fvg_bottom'] = bar_obj.get('fvg_bottom')
        
        # Process Module 14
        bar = mgann.process_bar(bar)
        
        stats['total_bars'] += 1
        
        # Check each condition
        if bar.get('ext_choch_up'):
            stats['choch_up'] += 1
            choch_bars.append({
                'index': bar.get('bar_index'),
                'type': 'CHoCH_UP',
                'ext_dir': bar.get('ext_dir'),
                'leg': bar.get('mgann_leg_index'),
                'fvg': bar.get('fvg_detected'),
                'fvg_type': bar.get('fvg_type'),
            })
        
        if bar.get('ext_choch_down'):
            stats['choch_down'] += 1
            choch_bars.append({
                'index': bar.get('bar_index'),
                'type': 'CHoCH_DOWN',
                'ext_dir': bar.get('ext_dir'),
                'leg': bar.get('mgann_leg_index'),
                'fvg': bar.get('fvg_detected'),
                'fvg_type': bar.get('fvg_type'),
            })
        
        if bar.get('ext_dir') == 1:
            stats['ext_dir_1'] += 1
        if bar.get('ext_dir') == -1:
            stats['ext_dir_minus1'] += 1
        
        leg_idx = bar.get('mgann_leg_index', 0)
        if leg_idx in [1, 2]:
            stats['leg_1_or_2'] += 1
        
        if bar.get('fvg_detected') and bar.get('fvg_type') == 'bullish':
            stats['fvg_bullish'] += 1
        if bar.get('fvg_detected') and bar.get('fvg_type') == 'bearish':
            stats['fvg_bearish'] += 1
        
        # Check LONG conditions together
        if (bar.get('ext_choch_down') and 
            bar.get('ext_dir') == 1 and
            leg_idx in [1, 2] and
            bar.get('fvg_detected') and bar.get('fvg_type') == 'bullish'):
            stats['all_long_conditions'] += 1
        
        # Check SHORT conditions together
        if (bar.get('ext_choch_up') and 
            bar.get('ext_dir') == -1 and
            leg_idx in [1, 2] and
            bar.get('fvg_detected') and bar.get('fvg_type') == 'bearish'):
            stats['all_short_conditions'] += 1

print("=" * 70)
print("CONDITION ANALYSIS")
print("=" * 70)
print(f"Total bars: {stats['total_bars']}\n")

print("Individual conditions:")
print(f"  CHoCH Up:          {stats['choch_up']}")
print(f"  CHoCH Down:        {stats['choch_down']}")
print(f"  ext_dir = 1:       {stats['ext_dir_1']} ({stats['ext_dir_1']/stats['total_bars']*100:.1f}%)")
print(f"  ext_dir = -1:      {stats['ext_dir_minus1']} ({stats['ext_dir_minus1']/stats['total_bars']*100:.1f}%)")
print(f"  Leg 1 or 2:        {stats['leg_1_or_2']} ({stats['leg_1_or_2']/stats['total_bars']*100:.1f}%)")
print(f"  FVG bullish:       {stats['fvg_bullish']}")
print(f"  FVG bearish:       {stats['fvg_bearish']}")

print(f"\nCombined conditions:")
print(f"  All LONG conditions:  {stats['all_long_conditions']}")
print(f"  All SHORT conditions: {stats['all_short_conditions']}")

print("\n" + "=" * 70)
print("CHoCH EVENTS DETAIL")
print("=" * 70)
for event in choch_bars[:10]:
    print(f"  Bar {event['index']}: {event['type']}")
    print(f"    ext_dir: {event['ext_dir']}")
    print(f"    Leg: {event['leg']}")
    print(f"    FVG: {event['fvg']} (type: {event['fvg_type']})")
    print()

print("=" * 70)
