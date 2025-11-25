#!/usr/bin/env python3
"""
Add leg numbers to visualizer - simple patch script
"""
import json
from pathlib import Path

# Check if module14_results.json has mgann_leg_index
data_file = Path("module14_results.json")
if data_file.exists():
    with open(data_file) as f:
        data = json.load(f)
    
    if len(data) > 0:
        sample = data[0]
        has_leg = 'mgann_leg_index' in sample
        print(f"✓ File exists: {data_file}")
        print(f"  Total bars: {len(data)}")
        print(f"  Has mgann_leg_index: {has_leg}")
        
        if has_leg:
            # Count leg changes
            legs = [b.get('mgann_leg_index', 0) for b in data]
            max_leg = max(legs)
            print(f"  Max leg index: {max_leg}")
        else:
            print("❌ Data missing mgann_leg_index field!")
            print("   Need to regenerate data with Module 14 processing")
else:
    print(f"❌ File not found: {data_file}")
    print("   Need to run pipeline to generate this file")
