#!/usr/bin/env python3
"""Debug: Check if CHoCH/BOS and FVG exist in data"""
import json
from pathlib import Path

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Checking data fields in: {test_file.name}\n")

choch_up_count = 0
choch_down_count = 0
bos_up_count = 0
bos_down_count = 0
fvg_count = 0
total = 0

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar = json.loads(line.strip())
        bar_obj = bar.get('bar', {})
        
        # Check CHoCH/BOS (both root and nested)
        if bar.get('ext_choch_up') or bar_obj.get('ext_choch_up'):
            choch_up_count += 1
        if bar.get('ext_choch_down') or bar_obj.get('ext_choch_down'):
            choch_down_count += 1
        if bar.get('ext_bos_up') or bar_obj.get('ext_bos_up'):
            bos_up_count += 1
        if bar.get('ext_bos_down') or bar_obj.get('ext_bos_down'):
            bos_down_count += 1
        
        # Check FVG (both root and nested)
        if bar.get('fvg_detected') or bar_obj.get('fvg_detected'):
            fvg_count += 1
        
        total += 1

print("=" * 60)
print("TEST 1: CHoCH/BOS EVENTS")
print("=" * 60)
print(f"CHoCH Up:   {choch_up_count}")
print(f"CHoCH Down: {choch_down_count}")
print(f"BOS Up:     {bos_up_count}")
print(f"BOS Down:   {bos_down_count}")
print(f"Total:      {choch_up_count + choch_down_count + bos_up_count + bos_down_count}")
print(f"\nResult: {'✅ PASS' if (choch_up_count + choch_down_count + bos_up_count + bos_down_count) > 0 else '❌ FAIL - NO EVENTS!'}")

print("\n" + "=" * 60)
print("TEST 2: FVG FIELDS")
print("=" * 60)
print(f"FVG detected: {fvg_count} bars ({fvg_count/total*100:.1f}%)")
print(f"\nResult: {'✅ PASS' if fvg_count > 0 else '❌ FAIL - NO FVGs!'}")

print("\n" + "=" * 60)
print(f"Total bars: {total}")
print("=" * 60)

# Show first FVG example
print("\nFirst FVG example:")
with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar = json.loads(line.strip())
        bar_obj = bar.get('bar', {})
        
        if bar.get('fvg_detected') or bar_obj.get('fvg_detected'):
            print(f"  Bar {bar.get('bar_index', i)}:")
            print(f"    Root level: fvg_detected={bar.get('fvg_detected')}, type={bar.get('fvg_type')}")
            print(f"    Nested bar: fvg_detected={bar_obj.get('fvg_detected')}, type={bar_obj.get('fvg_type')}")
            print(f"    Top/Bottom: {bar_obj.get('fvg_top')} / {bar_obj.get('fvg_bottom')}")
            break
