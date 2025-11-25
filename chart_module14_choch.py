#!/usr/bin/env python3
"""
Interactive Chart: Module 14 + CHoCH/BOS Visualization
========================================================
Shows:
- Price candlesticks
- MGann swing levels
- CHoCH/BOS events
- Leg index progression
- Wave strength
- pb_wave_strength_ok flags
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
    bar_state['ext_bos_up'] = bar_obj.get("ext_bos_up", False)
    bar_state['ext_bos_down'] = bar_obj.get("ext_bos_down", False)
    
    vol_stats = bar_obj.get('volume_stats', {})
    if vol_stats:
        bar_state['delta'] = vol_stats.get('delta_close', 0)
        bar_state['volume'] = vol_stats.get('total_volume', 0)
    return bar_state

# Load data
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Loading data from: {test_file.name}")

# Process data
mgann = Fix14MgannSwing()
bars_data = []

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar_state = json.loads(line.strip())
        bar_state = flatten_bar_fields(bar_state)
        bar_state = mgann.process_bar(bar_state)
        bars_data.append(bar_state)

# Take last 500 bars for visibility
bars_data = bars_data[-500:]

print(f"Loaded {len(bars_data)} bars")

# Extract data for plotting
timestamps = [b.get('timestamp', '') for b in bars_data]
opens = [b.get('open', 0) for b in bars_data]
highs = [b.get('high', 0) for b in bars_data]
lows = [b.get('low', 0) for b in bars_data]
closes = [b.get('close', 0) for b in bars_data]

# Module 14 outputs
swing_highs = [b.get('mgann_internal_swing_high') for b in bars_data]
swing_lows = [b.get('mgann_internal_swing_low') for b in bars_data]
leg_index = [b.get('mgann_leg_index', 0) for b in bars_data]
wave_strength = [b.get('mgann_wave_strength', 0) for b in bars_data]
pb_ok = [b.get('pb_wave_strength_ok', False) for b in bars_data]

# CHoCH/BOS events
choch_up = [(i, highs[i]) for i, b in enumerate(bars_data) if b.get('ext_choch_up')]
choch_down = [(i, lows[i]) for i, b in enumerate(bars_data) if b.get('ext_choch_down')]
bos_up = [(i, highs[i]) for i, b in enumerate(bars_data) if b.get('ext_bos_up')]
bos_down = [(i, lows[i]) for i, b in enumerate(bars_data) if b.get('ext_bos_down')]

# Create subplots
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.5, 0.25, 0.25],
    subplot_titles=('Price + Swings + CHoCH/BOS', 'Leg Index', 'Wave Strength')
)

# === Subplot 1: Price + Swings ===
# Candlesticks
fig.add_trace(
    go.Candlestick(
        x=list(range(len(bars_data))),
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        name='Price',
        increasing_line_color='cyan',
        decreasing_line_color='orange'
    ),
    row=1, col=1
)

# Swing highs
fig.add_trace(
    go.Scatter(
        x=list(range(len(bars_data))),
        y=swing_highs,
        mode='lines',
        name='Swing High',
        line=dict(color='red', width=1, dash='dot'),
        opacity=0.7
    ),
    row=1, col=1
)

# Swing lows
fig.add_trace(
    go.Scatter(
        x=list(range(len(bars_data))),
        y=swing_lows,
        mode='lines',
        name='Swing Low',
        line=dict(color='green', width=1, dash='dot'),
        opacity=0.7
    ),
    row=1, col=1
)

# CHoCH Up markers
if choch_up:
    fig.add_trace(
        go.Scatter(
            x=[x[0] for x in choch_up],
            y=[x[1] for x in choch_up],
            mode='markers',
            name='CHoCH Up',
            marker=dict(symbol='triangle-up', size=12, color='lime', line=dict(width=2, color='darkgreen'))
        ),
        row=1, col=1
    )

# CHoCH Down markers
if choch_down:
    fig.add_trace(
        go.Scatter(
            x=[x[0] for x in choch_down],
            y=[x[1] for x in choch_down],
            mode='markers',
            name='CHoCH Down',
            marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=2, color='darkred'))
        ),
        row=1, col=1
    )

# BOS Up markers
if bos_up:
    fig.add_trace(
        go.Scatter(
            x=[x[0] for x in bos_up],
            y=[x[1] for x in bos_up],
            mode='markers',
            name='BOS Up',
            marker=dict(symbol='star', size=10, color='cyan')
        ),
        row=1, col=1
    )

# BOS Down markers
if bos_down:
    fig.add_trace(
        go.Scatter(
            x=[x[0] for x in bos_down],
            y=[x[1] for x in bos_down],
            mode='markers',
            name='BOS Down',
            marker=dict(symbol='star', size=10, color='orange')
        ),
        row=1, col=1
    )

# pb_wave_strength_ok markers
pb_ok_indices = [i for i, ok in enumerate(pb_ok) if ok]
if pb_ok_indices:
    fig.add_trace(
        go.Scatter(
            x=pb_ok_indices,
            y=[closes[i] for i in pb_ok_indices],
            mode='markers',
            name='PB OK ✓',
            marker=dict(symbol='diamond', size=8, color='yellow', line=dict(width=1, color='gold'))
        ),
        row=1, col=1
    )

# === Subplot 2: Leg Index ===
fig.add_trace(
    go.Scatter(
        x=list(range(len(bars_data))),
        y=leg_index,
        mode='lines+markers',
        name='Leg Index',
        line=dict(color='purple', width=2),
        marker=dict(size=4)
    ),
    row=2, col=1
)

# === Subplot 3: Wave Strength ===
fig.add_trace(
    go.Scatter(
        x=list(range(len(bars_data))),
        y=wave_strength,
        mode='lines',
        name='Wave Strength',
        line=dict(color='blue', width=1),
        fill='tozeroy',
        fillcolor='rgba(0,100,255,0.2)'
    ),
    row=3, col=1
)

# Add threshold line at 40 (pullback strength criteria)
fig.add_trace(
    go.Scatter(
        x=[0, len(bars_data)-1],
        y=[40, 40],
        mode='lines',
        name='PB Threshold (40)',
        line=dict(color='red', width=1, dash='dash'),
        showlegend=True
    ),
    row=3, col=1
)

# Update layout
fig.update_layout(
    title=f'Module 14 + CHoCH/BOS Visualization - {test_file.name}<br><sub>Last 500 bars</sub>',
    xaxis3_title='Bar Index',
    yaxis_title='Price',
    yaxis2_title='Leg #',
    yaxis3_title='Strength',
    height=1000,
    template='plotly_dark',
    hovermode='x unified',
    showlegend=True,
    legend=dict(x=1.02, y=1, xanchor='left', yanchor='top')
)

# Update axes
fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
fig.update_yaxes(fixedrange=False)

# Save and open
output_file = Path(__file__).parent / "module14_choch_chart.html"
fig.write_html(str(output_file))

print(f"\n✅ Chart saved to: {output_file}")
print(f"\nChart Statistics:")
print(f"  CHoCH Up events: {len(choch_up)}")
print(f"  CHoCH Down events: {len(choch_down)}")
print(f"  BOS Up events: {len(bos_up)}")
print(f"  BOS Down events: {len(bos_down)}")
print(f"  pb_wave_strength_ok bars: {len(pb_ok_indices)} ({len(pb_ok_indices)/len(bars_data)*100:.1f}%)")
print(f"  Max leg index: {max(leg_index)}")

# Open in browser
import webbrowser
webbrowser.open(f'file://{output_file}')
print(f"\n🌐 Opening in browser...")
