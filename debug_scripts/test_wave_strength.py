#!/usr/bin/env python3
import json
import plotly.graph_objects as go

# Load data
with open('module14_results.json', 'r') as f:
    data = json.load(f)[:200]  # First 200 bars

# Build swing points
swing_highs = [b.get('mgann_internal_swing_high') for b in data]
swing_lows = [b.get('mgann_internal_swing_low') for b in data]
leg_dirs = [b.get('mgann_internal_leg_dir', 0) for b in data]

swing_points = []
last_high, last_low = None, None

for i in range(len(data)):
    curr_dir = leg_dirs[i]
    if curr_dir == 1 and (i == 0 or leg_dirs[i-1] != 1):
        if swing_lows[i] and swing_lows[i] != last_low:
            swing_points.append((i, swing_lows[i], 'low', i))
            last_low = swing_lows[i]
    elif curr_dir == -1 and (i == 0 or leg_dirs[i-1] != -1):
        if swing_highs[i] and swing_highs[i] != last_high:
            swing_points.append((i, swing_highs[i], 'high', i))
            last_high = swing_highs[i]

if len(data) > 0:
    if leg_dirs[-1] == 1 and swing_highs[-1] and swing_highs[-1] != last_high:
        swing_points.append((len(data)-1, swing_highs[-1], 'high', len(data)-1))
    elif leg_dirs[-1] == -1 and swing_lows[-1] and swing_lows[-1] != last_low:
        swing_points.append((len(data)-1, swing_lows[-1], 'low', len(data)-1))

# Calculate wave strengths
wave_strengths = []
wave_delta_sums = []
wave_types = []

for i in range(len(swing_points)):
    if i == 0:
        wave_delta_sums.append(0)
        wave_types.append('neutral')
        wave_strengths.append(0)
    else:
        prev_idx = swing_points[i-1][3]
        curr_idx = swing_points[i][3]
        delta_sum = sum(data[j].get('delta', 0) for j in range(prev_idx, curr_idx + 1))
        wave_delta_sums.append(delta_sum)
        wave_types.append('up' if delta_sum > 0 else 'down')

# Find swing 16 (-91) and swing 18 (-19)
print("DEBUG: Wave Delta Calculation")
print("=" * 80)
for i in range(len(swing_points)):
    if i > 0:
        print(f"Swing {i}: Bar {swing_points[i][0]}, Type={swing_points[i][2]}, ")
        print(f"  Delta={wave_delta_sums[i]}, WaveType={wave_types[i]}")
        if i == 16:
            print(f"  >>> THIS IS SWING 16 (delta -91)")
        if i == 18:
            print(f"  >>> THIS IS SWING 18 (delta -19)")

# Separate normalization
up_deltas = [d for d, t in zip(wave_delta_sums, wave_types) if t == 'up']
down_deltas = [abs(d) for d, t in zip(wave_delta_sums, wave_types) if t == 'down']

max_up = max(up_deltas) if up_deltas else 1
max_down = max(down_deltas) if down_deltas else 1

print(f"\nMax UP delta: {max_up}")
print(f"Max DOWN delta: {max_down}")

# Calculate strengths
for delta, wave_type in zip(wave_delta_sums[1:], wave_types[1:]):
    if wave_type == 'up':
        strength = int(min(100, (delta / max_up) * 100))
    else:
        strength = int(min(100, (abs(delta) / max_down) * 100))
    wave_strengths.append(strength)

print(f"\nWave 16 (delta -91): Strength = {wave_strengths[16]}/100")
print(f"Wave 18 (delta -19): Strength = {wave_strengths[18]}/100")

# Check if wave 16 has higher strength than wave 18
if wave_strengths[16] > wave_strengths[18]:
    print("\n✅ CORRECT: Wave -91 has higher strength than wave -19")
else:
    print("\n❌ ERROR: Wave -91 has LOWER strength than wave -19!")
    print("   This is the BUG!")
