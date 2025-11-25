#!/usr/bin/env python3
"""Test Module 14 wave strength validation"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

# Load test data
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Testing Module 14 with wave strength validation...")
print(f"File: {test_file.name}\n")

mgann = Fix14MgannSwing()
results = []
stats = {
    'impulse_ok': 0,
    'pullback_ok': 0,
    'total_bars': 0,
    'leg_1_bars': 0,
    'leg_2_bars': 0,
}

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar = json.loads(line.strip())
        
        # Flatten bar fields
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
        
        # Process
        bar = mgann.process_bar(bar)
        results.append(bar)
        
        # Collect stats
        stats['total_bars'] += 1
        if bar.get('impulse_wave_strength_ok'):
            stats['impulse_ok'] += 1
        if bar.get('pb_wave_strength_ok'):
            stats['pullback_ok'] += 1
        if bar.get('mgann_leg_index') == 1:
            stats['leg_1_bars'] += 1
        elif bar.get('mgann_leg_index') == 2:
            stats['leg_2_bars'] += 1

print("=" * 60)
print("WAVE STRENGTH VALIDATION STATISTICS")
print("=" * 60)
print(f"Total bars processed: {stats['total_bars']}")
print(f"\nLeg distribution:")
print(f"  Leg 1 bars: {stats['leg_1_bars']} ({stats['leg_1_bars']/stats['total_bars']*100:.1f}%)")
print(f"  Leg 2 bars: {stats['leg_2_bars']} ({stats['leg_2_bars']/stats['total_bars']*100:.1f}%)")
print(f"\nWave strength validation:")
print(f"  Impulse OK: {stats['impulse_ok']} ({stats['impulse_ok']/stats['total_bars']*100:.1f}%)")
print(f"  Pullback OK: {stats['pullback_ok']} ({stats['pullback_ok']/stats['total_bars']*100:.1f}%)")
print("=" * 60)

# Show last few bars with details
print(f"\nLast 5 bars detail:")
for bar in results[-5:]:
    print(f"  Bar {bar.get('bar_index', '?')}: " +
          f"Leg={bar.get('mgann_leg_index', 0)}, " +
          f"ImpOK={bar.get('impulse_wave_strength_ok', False)}, " +
          f"PbOK={bar.get('pb_wave_strength_ok', False)}, " +
          f"AvgDelta={bar.get('avg_delta', 0):.1f}, " +
          f"AvgSpeed={bar.get('avg_speed', 0):.4f}")

print(f"\nModule 14 test complete!")
