#!/usr/bin/env python3
"""
Module 14 Visualization - Zigzag Legs with Wave Strength
========================================================
CORRECT visualization showing:
- Zigzag swing pattern
- Leg numbers AT SWING PIVOTS only
- Impulse legs (odd): Leg 1, 3, 5... - should be STRONG
- Pullback legs (even): Leg 2, 4, 6... - should be WEAK
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

def flatten_bar_fields(bar_state):
    """Flatten nested 'bar' fields to root."""
    bar_obj = bar_state.get("bar", {})
    bar_state['ext_dir'] = bar_obj.get("ext_dir", 0)
    bar_state['ext_choch_up'] = bar_obj.get("ext_choch_up", False)
    bar_state['ext_choch_down'] = bar_obj.get("ext_choch_down", False)
    vol_stats = bar_obj.get('volume_stats', {})
    if vol_stats:
        bar_state['delta'] = vol_stats.get('delta_close', 0)
        bar_state['volume'] = vol_stats.get('total_volume', 0)
    return bar_state

# Load data
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Processing: {test_file.name}\n")

mgann = Fix14MgannSwing()
bars_data = []

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar_state = json.loads(line.strip())
        bar_state = flatten_bar_fields(bar_state)
        bar_state['bar_index'] = i
        bar_state = mgann.process_bar(bar_state)
        bars_data.append(bar_state)

# Take last 500 bars
bars_data = bars_data[-500:]

# Extract basic data
timestamps = [b.get('timestamp', '') for b in bars_data]
highs = [b.get('high', 0) for b in bars_data]
lows = [b.get('low', 0) for b in bars_data]
closes = [b.get('close', 0) for b in bars_data]

# Build ZIGZAG pattern from swing changes
zigzag_x = []
zigzag_y = []
leg_labels = []  # For annotations

prev_swing_high = None
prev_swing_low = None
prev_leg = None

for i, b in enumerate(bars_data):
    swing_high = b.get('mgann_internal_swing_high')
    swing_low = b.get('mgann_internal_swing_low')
    leg_idx = b.get('mgann_leg_index', 0)
    leg_dir = b.get('mgann_internal_leg_dir', 0)
    
    if leg_idx > 0 and leg_idx != prev_leg:
        # Leg changed - mark pivot point
        if leg_dir == 1:
            # Upswing - use swing_low as pivot
            if swing_low is not None:
                zigzag_x.append(i)
                zigzag_y.append(swing_low)
                leg_labels.append({'x': i, 'y': swing_low, 'leg': leg_idx-1, 'type': 'pullback' if (leg_idx-1) % 2 == 0 else 'impulse'})
        else:
            # Downswing - use swing_high as pivot
            if swing_high is not None:
                zigzag_x.append(i)
                zigzag_y.append(swing_high)
                leg_labels.append({'x': i, 'y': swing_high, 'leg': leg_idx-1, 'type': 'pullback' if (leg_idx-1) % 2 == 0 else 'impulse'})
        
        prev_leg = leg_idx
    
    prev_swing_high = swing_high
    prev_swing_low = swing_low

# Add final point
if len(bars_data) > 0:
    last_bar = bars_data[-1]
    last_dir = last_bar.get('mgann_internal_leg_dir', 0)
    if last_dir == 1:
        zigzag_x.append(len(bars_data)-1)
        zigzag_y.append(last_bar.get('mgann_internal_swing_high'))
    else:
        zigzag_x.append(len(bars_data)-1)
        zigzag_y.append(last_bar.get('mgann_internal_swing_low'))

# CHoCH/BOS events
choch_up = [(i, highs[i]) for i, b in enumerate(bars_data) if b.get('ext_choch_up')]
choch_down = [(i, lows[i]) for i, b in enumerate(bars_data) if b.get('ext_choch_down')]

# pb_wave_strength_ok markers
pb_ok_indices = [i for i, b in enumerate(bars_data) if b.get('pb_wave_strength_ok', False)]

# Create figure
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.08,
    row_heights=[0.7, 0.3],
    subplot_titles=('MGann Zigzag Legs + CHoCH/BOS', 'Wave Strength (Impulse vs Pullback)')
)

# === Subplot 1: Candlesticks + Zigzag ===
fig.add_trace(
    go.Candlestick(
        x=list(range(len(bars_data))),
        open=[b.get('open', 0) for b in bars_data],
        high=highs,
        low=lows,
        close=closes,
        name='Price',
        increasing_line_color='cyan',
        decreasing_line_color='orange'
    ),
    row=1, col=1
)

# Zigzag line
fig.add_trace(
    go.Scatter(
        x=zigzag_x,
        y=zigzag_y,
        mode='lines+markers',
        name='MGann Zigzag',
        line=dict(color='yellow', width=2),
        marker=dict(size=6, color='yellow')
    ),
    row=1, col=1
)

# CHoCH markers
if choch_up:
    fig.add_trace(
        go.Scatter(
            x=[x[0] for x in choch_up],
            y=[x[1] for x in choch_up],
            mode='markers+text',
            name='CHoCH Up',
            marker=dict(symbol='triangle-up', size=15, color='lime', line=dict(width=2, color='darkgreen')),
            text=['CHoCH↑'] * len(choch_up),
            textposition='top center'
        ),
        row=1, col=1
    )

if choch_down:
    fig.add_trace(
        go.Scatter(
            x=[x[0] for x in choch_down],
            y=[x[1] for x in choch_down],
            mode='markers+text',
            name='CHoCH Down',
            marker=dict(symbol='triangle-down', size=15, color='red', line=dict(width=2, color='darkred')),
            text=['CHoCH↓'] * len(choch_down),
            textposition='bottom center'
        ),
        row=1, col=1
    )

# pb_wave_strength_ok markers
if pb_ok_indices:
    fig.add_trace(
        go.Scatter(
            x=pb_ok_indices,
            y=[closes[i] for i in pb_ok_indices],
            mode='markers',
            name='PB OK ✓',
            marker=dict(symbol='diamond', size=10, color='gold', line=dict(width=2, color='yellow'))
        ),
        row=1, col=1
    )

# === Subplot 2: Wave Strength colored by Impulse/Pullback ===
impulse_colors = []
for b in bars_data:
    leg_idx = b.get('mgann_leg_index', 0)
    if leg_idx == 0:
        impulse_colors.append('gray')
    elif leg_idx % 2 == 1:
        # Odd leg = IMPULSE
        impulse_colors.append('lime')
    else:
        # Even leg = PULLBACK
        impulse_colors.append('orange')

fig.add_trace(
    go.Bar(
        x=list(range(len(bars_data))),
        y=[b.get('mgann_wave_strength', 0) for b in bars_data],
        name='Wave Strength',
        marker=dict(color=impulse_colors),
        showlegend=False
    ),
    row=2, col=1
)

# Threshold line
fig.add_trace(
    go.Scatter(
        x=[0, len(bars_data)-1],
        y=[40, 40],
        mode='lines',
        name='Threshold (40)',
        line=dict(color='red', width=1, dash='dash')
    ),
    row=2, col=1
)

# Add LEG NUMBER annotations at pivots
for lbl in leg_labels:
    if lbl['leg'] > 0:
        color = 'lime' if lbl['type'] == 'impulse' else 'orange'
        fig.add_annotation(
            x=lbl['x'],
            y=lbl['y'],
            text=f"<b>{lbl['leg']}</b>",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor=color,
            ax=0,
            ay=-40 if lbl['y'] == highs[lbl['x']] else 40,
            font=dict(size=12, color=color, family='Arial Black'),
            bgcolor='rgba(0,0,0,0.7)',
            bordercolor=color,
            borderwidth=2,
            row=1, col=1
        )

# Layout
fig.update_layout(
    title=f'Module 14 - MGann Zigzag Legs (Last 500 bars)<br><sub>{test_file.name}</sub>',
    xaxis2_title='Bar Index',
    yaxis_title='Price',
    yaxis2_title='Strength',
    height=900,
    template='plotly_dark',
    hovermode='x unified',
    showlegend=True
)

fig.update_xaxes(rangeslider_visible=False)

# Save
output_file = Path(__file__).parent / "module14_zigzag_legs.html"
fig.write_html(str(output_file))

print(f"✅ Chart saved: {output_file}")
print(f"\n📊 Statistics:")
print(f"  Zigzag pivots: {len(zigzag_x)}")
print(f"  Leg labels: {len(leg_labels)}")
print(f"  Impulse legs: {len([l for l in leg_labels if l['type'] == 'impulse'])}")
print(f"  Pullback legs: {len([l for l in leg_labels if l['type'] == 'pullback'])}")
print(f"  CHoCH events: {len(choch_up) + len(choch_down)}")
print(f"  pb_wave_strength_ok: {len(pb_ok_indices)} bars ({len(pb_ok_indices)/len(bars_data)*100:.1f}%)")

# Open
import webbrowser
webbrowser.open(f'file://{output_file}')
print(f"\n🌐 Opening in browser...")
