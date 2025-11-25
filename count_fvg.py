#!/usr/bin/env python3
import json
from pathlib import Path

file_path = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced\deepseek_enhanced_GC 12-25_M1_20250904.jsonl")

fvg_count = 0
total = 0

with open(file_path) as f:
    for line in f:
        bar = json.loads(line)
        bar_obj = bar.get('bar', {})
        
        if bar.get('fvg_detected') or bar_obj.get('fvg_detected'):
            fvg_count += 1
        
        total += 1

print(f"TEST 2: FVG FIELDS")
print(f"FVG detected: {fvg_count} bars ({fvg_count/total*100:.1f}%)")
print(f"Result: PASS" if fvg_count > 0 else "Result: FAIL")
