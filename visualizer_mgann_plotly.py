#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MGann Swing Visualizer with Plotly
==================================
Visualize internal swing (FIX14), external swing (SMC), and behavior patterns.

Usage:
    python visualizer_mgann_plotly.py --input module14_results.json --start 0 --end 500
"""

import sys
import io

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def load_data(filepath, start=None, end=None):
    """Load JSON data and slice to range."""
    print(f"📂 Loading data from: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Slice data if range specified
    if start is not None or end is not None:
        start = start or 0
        end = end or len(data)
        data = data[start:end]
    
    print(f"✓ Loaded {len(data)} bars (range: {start}-{end})")
    return data, start or 0


def plot_price(fig, data, start_idx):
    """Plot OHLC candlesticks (Layer 1)."""
    print("[*] Plotting price candlesticks...")
    
    indices = list(range(start_idx, start_idx + len(data)))
    
    # Extract OHLC
    opens = [bar.get('open', 0) for bar in data]
    highs = [bar.get('high', 0) for bar in data]
    lows = [bar.get('low', 0) for bar in data]
    closes = [bar.get('close', 0) for bar in data]
    
    # Extract timestamps
    timestamps = []
    for bar in data:
        ts = bar.get('timestamp', '')
        if ts:
            # Format timestamp for display (remove milliseconds and Z)
            ts_display = ts.replace('.000Z', '').replace('T', ' ')
        else:
            ts_display = f'Bar {bar.get("bar_index", "")}'
        timestamps.append(ts_display)
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=indices,
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        name='Price',
        increasing_line_color='#26A69A',  # Green
        decreasing_line_color='#EF5350',  # Red
        hovertext=[
            f"{ts}<br>O: {o:.2f}<br>H: {h:.2f}<br>L: {l:.2f}<br>C: {c:.2f}"
            for ts, o, h, l, c in zip(timestamps, opens, highs, lows, closes)
        ],
        hoverinfo='text',
    ))
    
    return timestamps  # Return timestamps for use in other layers


def plot_internal_swing(fig, data, start_idx):
    """Plot MGann internal swing zigzag (Layer 2)."""
    print("[*] Plotting internal swing (MGann FIX14)...")
    
    indices = list(range(start_idx, start_idx + len(data)))
    
    # Extract swing data
    swing_highs = [bar.get('mgann_internal_swing_high') for bar in data]
    swing_lows = [bar.get('mgann_internal_swing_low') for bar in data]
    leg_dirs = [bar.get('mgann_internal_leg_dir', 0) for bar in data]
    wave_strengths = [bar.get('mgann_wave_strength', 0) for bar in data]
    
    # Build swing points by detecting VALUE CHANGES (not just direction changes)
    swing_points = []  # List of (index, price, type)
    
    for i in range(1, len(data)):
        swing_high_changed = swing_highs[i] != swing_highs[i-1]
        swing_low_changed = swing_lows[i] != swing_lows[i-1]
        
        # When swing high changes, we formed a new swing high at previous bar
        if swing_high_changed and swing_highs[i-1] is not None:
            swing_points.append((indices[i-1], swing_highs[i-1], 'high', wave_strengths[i-1]))
        
        # When swing low changes, we formed a new swing low at previous bar
        if swing_low_changed and swing_lows[i-1] is not None:
            swing_points.append((indices[i-1], swing_lows[i-1], 'low', wave_strengths[i-1]))
    
    print(f"   Found {len(swing_points)} total swing points")
    
    # Separate highs and lows
    swing_high_points = [(x, y, s) for x, y, t, s in swing_points if t == 'high']
    swing_low_points = [(x, y, s) for x, y, t, s in swing_points if t == 'low']
    
    print(f"   Swing highs: {len(swing_high_points)}, Swing lows: {len(swing_low_points)}")
    
    # Plot swing highs
    if swing_high_points:
        fig.add_trace(go.Scatter(
            x=[x for x, y, s in swing_high_points],
            y=[y for x, y, s in swing_high_points],
            mode='markers',
            marker=dict(
                size=10,
                color='#1E88E5',  # Blue
                symbol='triangle-down',
                line=dict(width=2, color='white')
            ),
            name='Swing High',
            hovertext=[f"Swing High: {y:.2f}<br>Strength: {s}/100" for x, y, s in swing_high_points],
            hoverinfo='text',
        ))
    
    # Plot swing lows
    if swing_low_points:
        fig.add_trace(go.Scatter(
            x=[x for x, y, s in swing_low_points],
            y=[y for x, y, s in swing_low_points],
            mode='markers',
            marker=dict(
                size=10,
                color='#E53935',  # Red
                symbol='triangle-up',
                line=dict(width=2, color='white')
            ),
            name='Swing Low',
            hovertext=[f"Swing Low: {y:.2f}<br>Strength: {s}/100" for x, y, s in swing_low_points],
            hoverinfo='text',
        ))
    
    # Create zigzag by connecting swings in chronological order
    if len(swing_points) >= 2:
        # Sort by index (already in order, but make sure)
        swing_points.sort(key=lambda p: p[0])
        
        zigzag_x = [p[0] for p in swing_points]
        zigzag_y = [p[1] for p in swing_points]
        zigzag_strengths = [p[3] for p in swing_points]
        
        print(f"   Drawing zigzag with {len(zigzag_x)} points")
        
        # ZIGZAG LINE - make it VERY visible
        fig.add_trace(go.Scatter(
            x=zigzag_x,
            y=zigzag_y,
            mode='lines',
            line=dict(
                width=4,  # Very thick
                color='#FF6B00',  # Orange - very visible
                dash='solid'
            ),
            name='Zigzag Line',
            hovertext=[f"Point {i+1}/{len(zigzag_x)}" for i in range(len(zigzag_x))],
            hoverinfo='text',
            showlegend=True,
        ))
        
        # Wave strength markers on zigzag
        fig.add_trace(go.Scatter(
            x=zigzag_x,
            y=zigzag_y,
            mode='markers',
            marker=dict(
                size=8,
                color=zigzag_strengths,
                colorscale='RdYlGn',
                cmin=0,
                cmax=100,
                showscale=True,
                colorbar=dict(
                    title="Wave<br>Strength",
                    x=1.12,
                    len=0.3,
                    y=0.8,
                )
            ),
            name='Wave Strength',
            hovertext=[f"Strength: {s}/100" for s in zigzag_strengths],
            hoverinfo='text',
        ))
    else:
        print(f"   [!] Not enough swing points to draw zigzag ({len(swing_points)} points)")


def plot_external_swing(fig, data, start_idx):
    """Plot SMC external swing (Layer 3)."""
    print("[*] Plotting external swing (SMC)...")
    
    indices = list(range(start_idx, start_idx + len(data)))
    
    # Check if data has external swing fields
    if not data or not any(k.startswith('ext_') for k in data[0].keys()):
        print("   [!] No external swing data found (ext_bos_up, ext_choch_up, etc.)")
        print("   [!] Skipping external swing layer.")
        return
    
    # Collect external BOS/CHOCH events
    bos_up = [(i, data[i].get('high', 0)) for i in range(len(data)) 
              if data[i].get('ext_bos_up', False)]
    bos_down = [(i, data[i].get('low', 0)) for i in range(len(data)) 
                if data[i].get('ext_bos_down', False)]
    choch_up = [(i, data[i].get('high', 0)) for i in range(len(data)) 
                if data[i].get('ext_choch_up', False)]
    choch_down = [(i, data[i].get('low', 0)) for i in range(len(data)) 
                  if data[i].get('ext_choch_down', False)]
    
    total_events = len(bos_up) + len(bos_down) + len(choch_up) + len(choch_down)
    print(f"   Found {total_events} external events (BOS↑:{len(bos_up)}, BOS↓:{len(bos_down)}, CH↑:{len(choch_up)}, CH↓:{len(choch_down)})")
    
    # Plot BOS up
    if bos_up:
        fig.add_trace(go.Scatter(
            x=[indices[i] for i, _ in bos_up],
            y=[p for _, p in bos_up],
            mode='text',
            text=['BOS↑'] * len(bos_up),
            textposition='top center',
            textfont=dict(color='#4CAF50', size=10, family='Arial Black'),
            name='BOS ↑',
            hovertext=['Break of Structure (Bullish)'] * len(bos_up),
            hoverinfo='text',
        ))
    
    # Plot BOS down
    if bos_down:
        fig.add_trace(go.Scatter(
            x=[indices[i] for i, _ in bos_down],
            y=[p for _, p in bos_down],
            mode='text',
            text=['BOS↓'] * len(bos_down),
            textposition='bottom center',
            textfont=dict(color='#F44336', size=10, family='Arial Black'),
            name='BOS ↓',
            hovertext=['Break of Structure (Bearish)'] * len(bos_down),
            hoverinfo='text',
        ))
    
    # Plot CHOCH up
    if choch_up:
        fig.add_trace(go.Scatter(
            x=[indices[i] for i, _ in choch_up],
            y=[p for _, p in choch_up],
            mode='text',
            text=['CH↑'] * len(choch_up),
            textposition='top center',
            textfont=dict(color='#2196F3', size=10, family='Arial Black'),
            name='CHOCH ↑',
            hovertext=['Change of Character (Bullish)'] * len(choch_up),
            hoverinfo='text',
        ))
    
    # Plot CHOCH down
    if choch_down:
        fig.add_trace(go.Scatter(
            x=[indices[i] for i, _ in choch_down],
            y=[p for _, p in choch_down],
            mode='text',
            text=['CH↓'] * len(choch_down),
            textposition='bottom center',
            textfont=dict(color='#FF9800', size=10, family='Arial Black'),
            name='CHOCH ↓',
            hovertext=['Change of Character (Bearish)'] * len(choch_down),
            hoverinfo='text',
        ))


def plot_behaviors(fig, data, start_idx):
    """Plot behavior flags: UT, SP, PB, EX3 (Layer 4)."""
    print("🏷️  Plotting behavior flags...")
    
    indices = list(range(start_idx, start_idx + len(data)))
    
    # Collect behavior events
    ut_bars = []
    sp_bars = []
    pb_bars = []
    ex3_bars = []
    
    for i, bar in enumerate(data):
        behavior = bar.get('mgann_behavior', {})
        
        if behavior.get('UT', False):
            ut_bars.append((i, bar.get('high', 0)))
        if behavior.get('SP', False):
            sp_bars.append((i, bar.get('low', 0)))
        if behavior.get('PB', False):
            pb_bars.append((i, (bar.get('high', 0) + bar.get('low', 0)) / 2))
        if behavior.get('EX3', False):
            ex3_bars.append((i, bar.get('high', 0)))
    
    # Plot UpThrust (UT) - red lightning on top
    if ut_bars:
        fig.add_trace(go.Scatter(
            x=[indices[i] for i, _ in ut_bars],
            y=[p for _, p in ut_bars],
            mode='text',
            text=['⚡'] * len(ut_bars),
            textposition='top center',
            textfont=dict(color='#E53935', size=16),
            name='UpThrust (UT)',
            hovertext=['UpThrust: Selling pressure at highs'] * len(ut_bars),
            hoverinfo='text',
        ))
    
    # Plot Shakeout (SP) - green lightning on bottom
    if sp_bars:
        fig.add_trace(go.Scatter(
            x=[indices[i] for i, _ in sp_bars],
            y=[p for _, p in sp_bars],
            mode='text',
            text=['⚡'] * len(sp_bars),
            textposition='bottom center',
            textfont=dict(color='#4CAF50', size=16),
            name='Shakeout (SP)',
            hovertext=['Shakeout: Liquidity sweep + recovery'] * len(sp_bars),
            hoverinfo='text',
        ))
    
    # Plot Pullback (PB) - orange dot in middle
    if pb_bars:
        fig.add_trace(go.Scatter(
            x=[indices[i] for i, _ in pb_bars],
            y=[p for _, p in pb_bars],
            mode='markers',
            marker=dict(
                size=10,
                color='#FF9800',  # Orange
                symbol='circle',
                line=dict(width=2, color='white')
            ),
            name='Pullback (PB)',
            hovertext=['Pullback: Shallow consolidation'] * len(pb_bars),
            hoverinfo='text',
        ))
    
    # Plot 3-Push Exhaustion (EX3) - purple triangle
    if ex3_bars:
        fig.add_trace(go.Scatter(
            x=[indices[i] for i, _ in ex3_bars],
            y=[p for _, p in ex3_bars],
            mode='markers',
            marker=dict(
                size=12,
                color='#9C27B0',  # Purple
                symbol='triangle-down',
                line=dict(width=2, color='white')
            ),
            name='3-Push Exhaustion',
            hovertext=['3-Push Exhaustion detected'] * len(ex3_bars),
            hoverinfo='text',
        ))
    
    print(f"   UT: {len(ut_bars)}, SP: {len(sp_bars)}, PB: {len(pb_bars)}, EX3: {len(ex3_bars)}")


def create_chart(data, start_idx, end_idx):
    """Create complete interactive chart."""
    print(f"\n[*] Creating chart for bars {start_idx}-{end_idx}...")
    
    # Create figure
    fig = go.Figure()
    
    # Layer 1: Price candlesticks (returns timestamps)
    timestamps = plot_price(fig, data, start_idx)
    
    # Layer 2: Internal swing (MGann)
    plot_internal_swing(fig, data, start_idx)
    
    # Layer 3: External swing (SMC)
    plot_external_swing(fig, data, start_idx)
    
    # Layer 4: Behavior flags
    plot_behaviors(fig, data, start_idx)
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f'MGann Swing Visualizer (Bars {start_idx}-{end_idx})',
            font=dict(size=20, color='#333'),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title='Bar Index',
            gridcolor='#E0E0E0',
            showgrid=True,
            rangeslider=dict(visible=False),
        ),
        yaxis=dict(
            title='Price',
            gridcolor='#E0E0E0',
            showgrid=True,
        ),
        hovermode='x unified',
        template='plotly_white',
        height=800,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#CCCCCC",
            borderwidth=1
        ),
        font=dict(family='Arial, sans-serif', size=12),
    )
    
    return fig


def save_chart(fig, start_idx, end_idx):
    """Save chart to HTML file."""
    # Create output directory
    output_dir = Path('charts')
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename
    filename = f'visual_mgann_{start_idx}_{end_idx}.html'
    filepath = output_dir / filename
    
    # Save
    print(f"\n💾 Saving chart to: {filepath}")
    fig.write_html(str(filepath))
    print(f"✓ Chart saved successfully!")
    
    return filepath


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Visualize MGann Swing patterns with Plotly',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python visualizer_mgann_plotly.py --input module14_results.json
  python visualizer_mgann_plotly.py --input module14_results.json --start 0 --end 500
  python visualizer_mgann_plotly.py --input module14_results.json --start 500 --end 1000
        """
    )
    
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to JSON file with bar data'
    )
    parser.add_argument(
        '--start',
        type=int,
        default=None,
        help='Start bar index (default: 0)'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=None,
        help='End bar index (default: all)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("  MGann Swing Visualizer v1.0 (Plotly)")
    print("=" * 70 + "\n")
    
    # Load data
    data, start_idx = load_data(args.input, args.start, args.end)
    
    if not data:
        print("❌ No data to visualize!")
        return
    
    end_idx = start_idx + len(data)
    
    # Create chart
    fig = create_chart(data, start_idx, end_idx)
    
    # Save chart
    filepath = save_chart(fig, start_idx, end_idx)
    
    print("\n" + "=" * 70)
    print(f"✅ Visualization complete!")
    print(f"📁 Open: {filepath}")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
