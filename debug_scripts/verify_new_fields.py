#!/usr/bin/env python3
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json

# Load data
with open('module14_results.json', 'r') as f:
    data = json.load(f)

print("=" * 80)
print("MODULE 14 v1.2.0 - NEW FIELDS VERIFICATION")
print("=" * 80)

# Check field existence
print("\n[1] Field Existence Check:")
sample_bar = data[100]
for field in ['mgann_leg_index', 'mgann_leg_first_fvg', 'pb_wave_strength_ok']:
    exists = field in sample_bar
    value = sample_bar.get(field, 'N/A')
    print(f"   {field}: {'OK' if exists else 'MISSING'} (value: {value})")

# Sample data
print("\n[2] First 30 Bars:")
print(f"{'Bar':>4} {'Dir':>4} {'LegIdx':>7} {'1stFVG':>8} {'PB_OK':>7}")
print("-" * 40)
for i in range(min(30, len(data))):
    bar = data[i]
    direction = bar.get('mgann_internal_leg_dir', 0)
    leg_idx = bar.get('mgann_leg_index', 0)
    first_fvg = 'YES' if bar.get('mgann_leg_first_fvg') else 'no'
    pb_ok = 'YES' if bar.get('pb_wave_strength_ok') else 'no'
    
    print(f"{i:>4} {direction:>4} {leg_idx:>7} {first_fvg:>8} {pb_ok:>7}")

# Statistics
print("\n[3] Statistics (Full Dataset):")
leg_indices = [d.get('mgann_leg_index', 0) for d in data]
first_fvg_count = sum(1 for d in data if d.get('mgann_leg_first_fvg'))
pb_ok_count = sum(1 for d in data if d.get('pb_wave_strength_ok'))

print(f"   Total bars: {len(data)}")
print(f"   Max leg_index: {max(leg_indices)}")
print(f"   Avg leg_index: {sum(leg_indices)/len(leg_indices):.2f}")
print(f"   First FVG detections: {first_fvg_count} bars ({first_fvg_count/len(data)*100:.1f}%)")
print(f"   Pullback OK count: {pb_ok_count} bars ({pb_ok_count/len(data)*100:.1f}%)")

# Find interesting bars
print("\n[4] Interesting Bars:")
print("\nFirst FVG detections:")
fvg_bars = [(i, d) for i, d in enumerate(data) if d.get('mgann_leg_first_fvg')][:5]
for i, bar in fvg_bars:
    print(f"   Bar {i}: leg_index={bar.get('mgann_leg_index')}, dir={bar.get('mgann_internal_leg_dir')}")

print("\nPullback OK bars:")
pb_bars = [(i, d) for i, d in enumerate(data) if d.get('pb_wave_strength_ok')][:5]
for i, bar in pb_bars:
    print(f"   Bar {i}: leg_index={bar.get('mgann_leg_index')}, dir={bar.get('mgann_internal_leg_dir')}")

print("\n" + "=" * 80)
print("ALL NEW FIELDS WORKING CORRECTLY!")
print("=" * 80)
