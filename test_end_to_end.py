#!/usr/bin/env python3
"""Simple end-to-end test: Module 14 + Strategy with impulse filter"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1

# Load data
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"End-to-end test: Module 14 + Strategy")
print(f"File: {test_file.name}\n")

# Initialize
mgann = Fix14MgannSwing()
strategy = Fix16StrategyV1()

results = []
signals = []

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
        bar['fvg_detected'] = bar_obj.get('fvg_detected', False)
        bar['fvg_type'] = bar_obj.get('fvg_type')
        bar['fvg_top'] = bar_obj.get('fvg_top')
        bar['fvg_bottom'] = bar_obj.get('fvg_bottom')
        
        # Process through Module 14
        bar = mgann.process_bar(bar)
        
        # Process through Strategy
        bar = strategy.process_bar(bar)
        
        results.append(bar)
        
        if bar.get('signal_type') in ['LONG', 'SHORT']:
            signals.append(bar)

print("=" * 70)
print("RESULTS")
print("=" * 70)
print(f"Total bars: {len(results)}")
print(f"Total signals: {len(signals)}")

# Filter by impulse
impulse_signals = [s for s in signals if s.get('impulse_wave_strength_ok')]
print(f"With strong impulse: {len(impulse_signals)} ({len(impulse_signals)/max(1,len(signals))*100:.1f}%)")

# Show breakdown
long_signals = [s for s in signals if s.get('signal_type') == 'LONG']
short_signals = [s for s in signals if s.get('signal_type') == 'SHORT']
long_imp = [s for s in long_signals if s.get('impulse_wave_strength_ok')]
short_imp = [s for s in short_signals if s.get('impulse_wave_strength_ok')]

print(f"\nBreakdown:")
print(f"  LONG: {len(long_signals)} total, {len(long_imp)} with impulse")
print(f"  SHORT: {len(short_signals)} total, {len(short_imp)} with impulse")

if impulse_signals:
    print(f"\nFirst 5 impulse-filtered signals:")
    for i, sig in enumerate(impulse_signals[:5]):
        print(f"  {i+1}. Bar {sig.get('bar_index')}: {sig.get('signal_type')}, " +
              f"Leg={sig.get('mgann_leg_index')}, " +
              f"AvgDelta={sig.get('avg_delta', 0):.1f}, " +
              f"AvgSpeed={sig.get('avg_speed', 0):.4f}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
