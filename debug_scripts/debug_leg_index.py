#!/usr/bin/env python3
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json

# Load Module 14 output
with open('module14_results.json', 'r') as f:
    data = json.load(f)

print("=" * 80)
print("DEBUGGING: Why leg_index = 0?")
print("=" * 80)

# Check if ext fields are in JSON output
print("\n[1] Check if ext fields exist in Module 14 output:")
sample_bar = data[100]
for field in ['ext_dir', 'ext_bos_up', 'ext_bos_down', 'ext_choch_up', 'ext_choch_down']:
    exists = field in sample_bar
    value = sample_bar.get(field, 'MISSING')
    print(f"   {field}: {exists} (value={value})")

# Count ext_dir values
print("\n[2] ext_dir distribution in Module 14 output:")
ext_dirs = [b.get('ext_dir', 'missing') for b in data]
from collections import Counter
print(f"   {dict(Counter(ext_dirs))}")

# Check leg_index progression
print("\n[3] leg_index progression (first 50 bars):")
print(f"{'Bar':>4} {'ext_dir':>8} {'BOS/CH':>10} {'leg_idx':>8}")
print("-" * 35)
for i in range(min(50, len(data))):
    bar = data[i]
    ext_dir = bar.get('ext_dir', '?')
    
    event = ''
    if bar.get('ext_bos_up'): event = 'BOS_UP'
    elif bar.get('ext_bos_down'): event = 'BOS_DN'
    elif bar.get('ext_choch_up'): event = 'CHOCH_UP'
    elif bar.get('ext_choch_down'): event = 'CHOCH_DN'
    
    leg_idx = bar.get('mgann_leg_index', 0)
    
    if i < 10 or event or leg_idx > 0:
        print(f"{i:>4} {ext_dir:>8} {event:>10} {leg_idx:>8}")

print("\n[4] Find bars where leg_index changes:")
leg_changes = []
for i in range(1, len(data)):
    prev_leg = data[i-1].get('mgann_leg_index', 0)
    curr_leg = data[i].get('mgann_leg_index', 0)
    if curr_leg != prev_leg:
        leg_changes.append((i, prev_leg, curr_leg, data[i].get('ext_dir'), data[i].get('ext_bos_up'), data[i].get('ext_choch_down')))

print(f"\n   Found {len(leg_changes)} leg index changes:")
for i, prev, curr, ext_dir, bos, choch in leg_changes[:10]:
    print(f"   Bar {i}: {prev} -> {curr}, ext_dir={ext_dir}, bos_up={bos}, choch_dn={choch}")

print("\n" + "=" * 80)
