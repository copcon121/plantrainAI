#!/usr/bin/env python3
"""Test strategy with impulse_wave_strength_ok filter"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.smc_processor import SMCProcessor

# Load and process
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Testing Strategy with IMPULSE filter...")
print(f"File: {test_file.name}\n")

processor = SMCProcessor()
results = processor.process_file(str(test_file))

print("=" * 70)
print("PROCESSING COMPLETE")
print("=" * 70)

# Count signals with impulse filter
impulse_signals = []
all_signals = []

for bar in results:
    sig_type = bar.get('signal_type')
    if sig_type in ['LONG', 'SHORT']:
        all_signals.append(bar)
        if bar.get('impulse_wave_strength_ok'):
            impulse_signals.append(bar)

print(f"\nTotal signals: {len(all_signals)}")
print(f"With strong impulse: {len(impulse_signals)} ({len(impulse_signals)/max(1,len(all_signals))*100:.1f}%)")

if impulse_signals:
    print(f"\nFirst 3 impulse-filtered signals:")
    for i, sig in enumerate(impulse_signals[:3]):
        print(f"{i+1}. Bar {sig.get('bar_index')}: {sig.get('signal_type')}, " +
              f"Leg={sig.get('mgann_leg_index')}, " +
              f"Entry={sig.get('entry_price'):.2f}")

print("\n" + "=" * 70)
