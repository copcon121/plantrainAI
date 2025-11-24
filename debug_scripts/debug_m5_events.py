#!/usr/bin/env python3
"""Debug M5 event timing and frequency."""
import json

# Load results
with open('module15_m5_results.json', 'r') as f:
    results = json.load(f)

print("=" * 80)
print("M5 EVENT TIMING ANALYSIS")
print("=" * 80)

# Find all M5 events
m5_events = []
for i, bar in enumerate(results):
    if bar.get('m5_ext_bos_up'):
        m5_events.append((i, 'BOS_UP'))
    if bar.get('m5_ext_bos_down'):
        m5_events.append((i, 'BOS_DOWN'))
    if bar.get('m5_ext_choch_up'):
        m5_events.append((i, 'CHOCH_UP'))
    if bar.get('m5_ext_choch_down'):
        m5_events.append((i, 'CHOCH_DOWN'))

print(f"\nTotal M1 bars: {len(results)}")
print(f"Expected M5 bars: {len(results) // 5} (every 5 M1 bars)")
print(f"Total M5 events found: {len(m5_events)}")

print("\n" + "=" * 80)
print("FIRST 20 M5 EVENTS - BAR INDEX ANALYSIS")
print("=" * 80)
print(f"{'#':<4} {'Bar Idx':<10} {'Event':<15} {'Bar % 5':<10} {'M5 Bar #':<10}")
print("-" * 80)

for i, (bar_idx, event) in enumerate(m5_events[:20], 1):
    mod5 = bar_idx % 5
    m5_bar_num = bar_idx // 5
    status = "✓ LAST" if mod5 == 4 else f"✗ {mod5}/5"
    print(f"{i:<4} {bar_idx:<10} {event:<15} {status:<10} {m5_bar_num:<10}")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

# Check if events only happen on 5th bars (index % 5 == 4)
correct_timing = [idx for idx, _ in m5_events if idx % 5 == 4]
wrong_timing = [idx for idx, _ in m5_events if idx % 5 != 4]

print(f"\nEvents on correct bars (index % 5 == 4): {len(correct_timing)}")
print(f"Events on wrong bars (index % 5 != 4): {len(wrong_timing)}")

if wrong_timing:
    print(f"\n⚠️  PROBLEM: Events firing on non-M5-completion bars!")
    print(f"   Wrong bar indices (first 10): {wrong_timing[:10]}")
else:
    print(f"\n✓ All events correctly timed to M5 bar completion")

# Analyze event frequency
print("\n" + "=" * 80)
print("EXPECTED vs ACTUAL")
print("=" * 80)

expected_m5_bars = len(results) // 5
print(f"M1 bars: {len(results)}")
print(f"Expected M5 bars: {expected_m5_bars}")
print(f"Actual M5 events: {len(m5_events)}")
print(f"Event rate: {len(m5_events)/expected_m5_bars*100:.1f}% of M5 bars have events")

# This is NORMAL - not every M5 bar has CHoCH/BOS
# CHoCH/BOS only happens on swing direction changes
print(f"\n💡 NOTE: {len(m5_events)/expected_m5_bars*100:.1f}% event rate is NORMAL")
print(f"   CHoCH/BOS only occurs on M5 swing direction changes")
print(f"   Not every M5 bar creates a CHoCH/BOS event")
