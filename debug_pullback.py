#!/usr/bin/env python3
"""Debug pullback validation - why 0%?"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

# Load test data
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Debugging pullback validation...")
print(f"File: {test_file.name}\n")

mgann = Fix14MgannSwing()
leg2_samples = []

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar = json.loads(line.strip())
        
        # Flatten
        bar_obj = bar.get('bar', {})
        bar['ext_dir'] = bar_obj.get('ext_dir', 0)
        bar['ext_choch_up'] = bar_obj.get('ext_choch_up', False)
        bar['ext_choch_down'] = bar_obj.get('ext_choch_down', False)
        vol_stats = bar_obj.get('volume_stats', {})
        if vol_stats:
            bar['delta'] = vol_stats.get('delta_close', 0)
            bar['volume'] = vol_stats.get('total_volume', 0)
        
        bar = mgann.process_bar(bar)
        
        # Collect Leg 2 bars for analysis
        if bar.get('mgann_leg_index') == 2:
            leg2_samples.append({
                'bar_index': bar.get('bar_index'),
                'pullback_delta': abs(mgann.pullback_delta),
                'pullback_volume': mgann.pullback_volume,
                'pullback_speed': mgann.pullback_speed,
                'avg_delta': mgann.avg_delta,
                'avg_volume': mgann.avg_volume,
                'avg_speed': mgann.avg_speed,
                'pb_ok': bar.get('pb_wave_strength_ok', False),
            })

if not leg2_samples:
    print("No Leg 2 bars found!")
    sys.exit(1)

# Analyze thresholds
print(f"Found {len(leg2_samples)} Leg 2 bars\n")
print("=" * 80)
print("PULLBACK VALIDATION ANALYSIS")
print("=" * 80)

# Check each condition
delta_pass = sum(1 for s in leg2_samples if s['pullback_delta'] < s['avg_delta'] * 0.7)
volume_pass = sum(1 for s in leg2_samples if s['pullback_volume'] < s['avg_volume'] * 0.7)
speed_pass = sum(1 for s in leg2_samples if s['avg_speed'] > 0 and s['pullback_speed'] < s['avg_speed'] * 0.7)

print(f"\nCondition pass rates (threshold 0.7):")
print(f"  Delta < avg*0.7:  {delta_pass}/{len(leg2_samples)} ({delta_pass/len(leg2_samples)*100:.1f}%)")
print(f"  Volume < avg*0.7: {volume_pass}/{len(leg2_samples)} ({volume_pass/len(leg2_samples)*100:.1f}%)")
print(f"  Speed < avg*0.7:  {speed_pass}/{len(leg2_samples)} ({speed_pass/len(leg2_samples)*100:.1f}%)")

# Show some examples
print(f"\nFirst 5 Leg 2 bars:")
for i, s in enumerate(leg2_samples[:5]):
    delta_ratio = s['pullback_delta'] / s['avg_delta'] if s['avg_delta'] > 0 else 999
    volume_ratio = s['pullback_volume'] / s['avg_volume'] if s['avg_volume'] > 0 else 999
    speed_ratio = s['pullback_speed'] / s['avg_speed'] if s['avg_speed'] > 0 else 999
    
    print(f"\n  Bar {s['bar_index']}:")
    print(f"    Delta:  {s['pullback_delta']:.1f} / {s['avg_delta']:.1f} = {delta_ratio:.2f}x (need <0.7)")
    print(f"    Volume: {s['pullback_volume']:.0f} / {s['avg_volume']:.0f} = {volume_ratio:.2f}x (need <0.7)")
    print(f"    Speed:  {s['pullback_speed']:.4f} / {s['avg_speed']:.4f} = {speed_ratio:.2f}x (need <0.7)")
    print(f"    Result: {'PASS' if s['pb_ok'] else 'FAIL'}")

# Test with relaxed thresholds
print("\n" + "=" * 80)
print("RELAXED THRESHOLD TESTING")
print("=" * 80)

for threshold in [0.75, 0.80, 0.85, 0.90]:
    delta_pass = sum(1 for s in leg2_samples if s['pullback_delta'] < s['avg_delta'] * threshold)
    volume_pass = sum(1 for s in leg2_samples if s['pullback_volume'] < s['avg_volume'] * threshold)
    speed_pass = sum(1 for s in leg2_samples if s['avg_speed'] > 0 and s['pullback_speed'] < s['avg_speed'] * threshold)
    all_pass = sum(1 for s in leg2_samples 
                   if s['pullback_delta'] < s['avg_delta'] * threshold
                   and s['pullback_volume'] < s['avg_volume'] * threshold
                   and (s['avg_speed'] == 0 or s['pullback_speed'] < s['avg_speed'] * threshold'))
    
    print(f"\nThreshold {threshold}:")
    print(f"  Delta pass: {delta_pass} ({delta_pass/len(leg2_samples)*100:.1f}%)")
    print(f"  Volume pass: {volume_pass} ({volume_pass/len(leg2_samples)*100:.1f}%)")
    print(f"  Speed pass: {speed_pass} ({speed_pass/len(leg2_samples)*100:.1f}%)")
    print(f"  ALL 3 pass: {all_pass} ({all_pass/len(leg2_samples)*100:.1f}%)")

print("\n" + "=" * 80)
