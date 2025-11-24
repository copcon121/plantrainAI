#!/usr/bin/env python3
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json

# Load data
with open('module14_results.json', 'r') as f:
    data = json.load(f)

# Find swing points
swing_highs = [b.get('mgann_internal_swing_high') for b in data]
swing_lows = [b.get('mgann_internal_swing_low') for b in data]
leg_dirs = [b.get('mgann_internal_leg_dir', 0) for b in data]

swing_points = []
last_high, last_low = None, None

for i in range(len(data)):
    curr_dir = leg_dirs[i]
    if curr_dir == 1 and (i == 0 or leg_dirs[i-1] != 1):
        if swing_lows[i] and swing_lows[i] != last_low:
            swing_points.append((i, swing_lows[i], 'low'))
            last_low = swing_lows[i]
    elif curr_dir == -1 and (i == 0 or leg_dirs[i-1] != -1):
        if swing_highs[i] and swing_highs[i] != last_high:
            swing_points.append((i, swing_highs[i], 'high'))
            last_high = swing_highs[i]

if len(data) > 0:
    if leg_dirs[-1] == 1 and swing_highs[-1] and swing_highs[-1] != last_high:
        swing_points.append((len(data)-1, swing_highs[-1], 'high'))
    elif leg_dirs[-1] == -1 and swing_lows[-1] and swing_lows[-1] != last_low:
        swing_points.append((len(data)-1, swing_lows[-1], 'low'))

print(f"Found {len(swing_points)} swing points\n")

# Calculate delta sums for each wave
print("Wave Analysis (bars 0-200):")
print("=" * 80)
for i in range(min(20, len(swing_points))):
    if i == 0:
        print(f"Swing {i}: Bar {swing_points[i][0]}, Type={swing_points[i][2]}, Price={swing_points[i][1]:.2f}")
        print(f"  → First swing, no previous wave")
    else:
        prev_idx = swing_points[i-1][0]
        curr_idx = swing_points[i][0]
        delta_sum = sum(data[j].get('delta', 0) for j in range(prev_idx, curr_idx + 1))
        wave_type = 'UP' if delta_sum > 0 else 'DOWN'
        
        print(f"\nSwing {i}: Bar {curr_idx}, Type={swing_points[i][2]}, Price={swing_points[i][1]:.2f}")
        print(f"  → Wave from bar {prev_idx} to {curr_idx} ({curr_idx - prev_idx} bars)")
        print(f"  → Delta Sum: {delta_sum} ({wave_type} wave)")
