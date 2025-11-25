#!/usr/bin/env python3
"""Test Strategy 1 with new wave strength validation"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.smc_data_processor import SMCDataProcessor

# Config
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Testing Strategy 1 with wave strength validation...")
print(f"File: {test_file.name}\n")

processor = SMCDataProcessor()
processor.process_file(test_file, output_signals=True)

# Load signal stats
signals_file = Path("strategy_signals") / f"{test_file.stem}_signals.jsonl"
if not signals_file.exists():
    print("No signals file generated!")
    sys.exit(1)

signals = []
with open(signals_file) as f:
    for line in f:
        signals.append(json.loads(line))

print("=" * 70)
print(f"STRATEGY SIGNALS: {len(signals)} total")
print("=" * 70)

# Analyze by wave strength
impulse_ok_count = 0
pb_ok_count = 0

for sig in signals:
    if sig.get('impulse_wave_strength_ok'):
        impulse_ok_count += 1
    if sig.get('pb_wave_strength_ok'):
        pb_ok_count += 1

print(f"\nWave strength distribution:")
print(f"  With strong impulse: {impulse_ok_count} ({impulse_ok_count/len(signals)*100:.1f}%)")
print(f"  With weak pullback: {pb_ok_count} ({pb_ok_count/len(signals)*100:.1f}%)")
print(f"  Both conditions: {min(impulse_ok_count, pb_ok_count)}")

# Show first 3 signals
print(f"\nFirst 3 signals:")
for i, sig in enumerate(signals[:3]):
    print(f"{i+1}. Bar {sig.get('bar_index')}: " +
          f"Type={sig.get('signal_type')}, " +
          f"Leg={sig.get('mgann_leg_index')}, " +
          f"ImpOK={sig.get('impulse_wave_strength_ok')}, " +
          f"PbOK={sig.get('pb_wave_strength_ok')}")

print("\n" + "=" * 70)
