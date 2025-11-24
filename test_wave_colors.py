#!/usr/bin/env python3
# Test wave strengths with explicit output for manual verification
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import plotly.graph_objects as go

def load_data(filepath, start=None, end=None):
    with open(filepath, 'r') as f:
        data = json.load(f)
    start = start or 0
    end = end or len(data)
    return data[start:end], start

def create_test_chart():
    data, start_idx = load_data('module14_results.json', 0, 200)
    indices = list(range(start_idx, start_idx + len(data)))
    
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
                swing_points.append((indices[i], swing_lows[i], 'low', i))
                last_low = swing_lows[i]
        elif curr_dir == -1 and (i == 0 or leg_dirs[i-1] != -1):
            if swing_highs[i] and swing_highs[i] != last_high:
                swing_points.append((indices[i], swing_highs[i], 'high', i))
                last_high = swing_highs[i]
    
    if len(data) > 0:
        if leg_dirs[-1] == 1 and swing_highs[-1] and swing_highs[-1] != last_high:
            swing_points.append((indices[-1], swing_highs[-1], 'high', len(data)-1))
        elif leg_dirs[-1] == -1 and swing_lows[-1] and swing_lows[-1] != last_low:
            swing_points.append((indices[-1], swing_lows[-1], 'low', len(data)-1))
    
    # Calculate wave strengths
    wave_strengths = []
    wave_delta_sums = []
    wave_types = []
    
    for i in range(len(swing_points)):
        if i == 0:
            wave_delta_sums.append(0)
            wave_types.append('neutral')
        else:
            prev_idx = swing_points[i-1][3]
            curr_idx = swing_points[i][3]
            delta_sum = sum(data[j].get('delta', 0) for j in range(prev_idx, curr_idx + 1))
            wave_delta_sums.append(delta_sum)
            wave_types.append('up' if delta_sum > 0 else 'down')
    
    # Separate normalization
    up_deltas = [d for d, t in zip(wave_delta_sums, wave_types) if t == 'up']
    down_deltas = [abs(d) for d, t in zip(wave_delta_sums, wave_types) if t == 'down']
    
    max_up = max(up_deltas) if up_deltas else 1
    max_down = max(down_deltas) if down_deltas else 1
    
    for delta, wave_type in zip(wave_delta_sums, wave_types):
        if wave_type == 'neutral':
            wave_strengths.append(0)
        elif wave_type == 'up':
            strength = int(min(100, (delta / max_up) * 100))
            wave_strengths.append(strength)
        else:  # down
            strength = int(min(100, (abs(delta) / max_down) * 100))
            wave_strengths.append(strength)
    
    # Print debug info
    print("WAVE STRENGTH DEBUG OUTPUT:")
    print("=" * 80)
    print(f"Max UP delta: {max_up}")
    print(f"Max DOWN delta: {max_down}")
    print()
    for i in range(len(swing_points)):
        if i > 0:
            print(f"Swing {i}: Bar {swing_points[i][0]}, Delta={wave_delta_sums[i]:4d}, Type={wave_types[i]:4s}, Strength={wave_strengths[i]:3d}/100")
            if i == 16:
                print("  >>> SWING 16 (-91): Expected RED/ORANGE color (low strength)")
            if i == 18:
                print("  >>> SWING 18 (-19): Expected DARK RED color (very low strength)")
    
    # Create chart
    fig = go.Figure()
    
    # Add swing points with colors
    fig.add_trace(go.Scatter(
        x=[p[0] for p in swing_points],
        y=[p[1] for p in swing_points],
        mode='markers+text',
        marker=dict(
            size=15,
            color=wave_strengths,
            colorscale='RdYlGn',
            cmin=0,
            cmax=100,
            showscale=True,
            colorbar=dict(title="Strength")
        ),
        text=[f"S{i}<br>{wave_strengths[i]}" for i in range(len(swing_points))],
        textposition='top center',
        name='Swings'
    ))
    
    fig.update_layout(
        title='Wave Strength Test - Check colors manually',
        height=600,
    )
    
    fig.write_html('charts/wave_strength_test.html')
    print("\nChart saved to: charts/wave_strength_test.html")
    print("EXPECTED COLORS:")
    print("  Swing 16 (strength=18): Should be RED/ORANGE (weak wave)")
    print("  Swing 18 (strength=3): Should be DARK RED (very weak wave)")
   
create_test_chart()
