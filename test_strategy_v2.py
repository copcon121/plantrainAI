#!/usr/bin/env python3
"""Test clean strategy V2"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v2 import Fix16StrategyV2

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print("Testing Strategy V2 (Clean Rebuild)\n")

mgann = Fix14MgannSwing()
strategy = Fix16StrategyV2()

signals = []

with open(test_file, 'r') as f:
    for line in f:
        bar = json.loads(line.strip())
        
        # Flatten
        bar_obj = bar.get('bar', {})
        vol_stats = bar_obj.get('volume_stats', {})
        if vol_stats:
            bar['delta'] = vol_stats.get('delta_close', 0)
            bar['volume'] = vol_stats.get('total_volume', 0)
        bar['ext_choch_up'] = bar_obj.get('ext_choch_up', False)
        bar['ext_choch_down'] = bar_obj.get('ext_choch_down', False)
        bar['fvg_detected'] = bar_obj.get('fvg_detected', False)
        bar['fvg_type'] = bar_obj.get('fvg_type')
        bar['fvg_top'] = bar_obj.get('fvg_top')
        bar['fvg_bottom'] = bar_obj.get('fvg_bottom')
        
        # Process
        bar = mgann.process_bar(bar)
        bar = strategy.process_bar(bar)
        
        if bar.get('signal_type') in ['LONG', 'SHORT']:
            signals.append(bar)

print("=" * 70)
print("RESULTS")
print("=" * 70)
print(f"Total signals: {len(signals)}")
print(f"  LONG: {sum(1 for s in signals if s['signal_type'] == 'LONG')}")
print(f"  SHORT: {sum(1 for s in signals if s['signal_type'] == 'SHORT')}")

print(f"\nFirst 5 signals:")
for i, sig in enumerate(signals[:5]):
    print(f"{i+1}. Bar {sig.get('bar_index')}: {sig['signal_type']}")
    print(f"   Entry={sig['entry_price']}, SL={sig['sl']}, TP={sig['tp']}, Risk={sig['risk']:.2f}")

# Check impulse filter
impulse_signals = [s for s in signals if s.get('impulse_wave_strength_ok')]
print(f"\nWith strong impulse: {len(impulse_signals)} ({len(impulse_signals)/max(1,len(signals))*100:.1f}%)")

print("\n" + "=" * 70)
