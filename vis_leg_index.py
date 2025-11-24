#!/usr/bin/env python3
"""
Enhanced visualizer showing leg_index annotations.
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import argparse
import plotly.graph_objects as go

def create_leg_index_chart(data, start_idx=0):
    """Create chart with leg_index annotations."""
    indices = list(range(start_idx, start_idx + len(data)))
    
    fig = go.Figure()
    
    # 1. Price candlesticks
    timestamps = []
    for b in data:
        ts = b.get('timestamp', '')
        if ts:
            ts_display = ts.replace('.000Z', '').replace('T', ' ')
        else:
            ts_display = f'Bar {b.get("bar_index", "")}'
        timestamps.append(ts_display)
    
    opens = [b.get('open',0) for b in data]
    highs = [b.get('high',0) for b in data]
    lows = [b.get('low',0) for b in data]
    closes = [b.get('close',0) for b in data]
    
    fig.add_trace(go.Candlestick(
        x=indices,
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        name='Price',
        increasing_line_color='#26A69A',
        decreasing_line_color='#EF5350',
        hovertext=[
            f"{ts}<br>O: {o:.2f}<br>H: {h:.2f}<br>L: {l:.2f}<br>C: {c:.2f}"
            for ts, o, h, l, c in zip(timestamps, opens, highs, lows, closes)
        ],
        hoverinfo='text',
    ))
    
    # 2. MGann Swing Zigzag Line
    swing_highs = [b.get('mgann_internal_swing_high') for b in data]
    swing_lows = [b.get('mgann_internal_swing_low') for b in data]
    leg_dirs = [b.get('mgann_internal_leg_dir', 0) for b in data]
    
    # Build swing points
    swing_points = []  # (x, y, type, data_idx)
    last_high, last_low = None, None
    
    for i in range(len(data)):
        curr_dir = leg_dirs[i]
        
        # Detect swing transitions
        if curr_dir == 1 and (i == 0 or leg_dirs[i-1] != 1):
            # Started upswing - mark the low
            if swing_lows[i] and swing_lows[i] != last_low:
                swing_points.append((indices[i], swing_lows[i], 'low', i))
                last_low = swing_lows[i]
        elif curr_dir == -1 and (i == 0 or leg_dirs[i-1] != -1):
            # Started downswing - mark the high
            if swing_highs[i] and swing_highs[i] != last_high:
                swing_points.append((indices[i], swing_highs[i], 'high', i))
                last_high = swing_highs[i]
    
    # Add final swing point
    if len(data) > 0:
        if leg_dirs[-1] == 1 and swing_highs[-1] and swing_highs[-1] != last_high:
            swing_points.append((indices[-1], swing_highs[-1], 'high', len(data)-1))
        elif leg_dirs[-1] == -1 and swing_lows[-1] and swing_lows[-1] != last_low:
            swing_points.append((indices[-1], swing_lows[-1], 'low', len(data)-1))
    
    # Draw zigzag line
    if len(swing_points) >= 2:
        fig.add_trace(go.Scatter(
            x=[p[0] for p in swing_points],
            y=[p[1] for p in swing_points],
            mode='lines',
            line=dict(width=3, color='#FF6B00'),
            name='MGann Zigzag',
            hovertext=[f"{p[2].upper()}: {p[1]:.2f}" for p in swing_points],
            hoverinfo='text',
        ))
        
        # Wave strength markers
        wave_strengths = []
        for i in range(len(swing_points)):
            data_idx = swing_points[i][3]
            strength = data[data_idx].get('mgann_wave_strength', 0) if data_idx < len(data) else 0
            wave_strengths.append(strength)
        
        fig.add_trace(go.Scatter(
            x=[p[0] for p in swing_points],
            y=[p[1] for p in swing_points],
            mode='markers',
            marker=dict(
                size=10,
                color=wave_strengths,
                colorscale='RdYlGn',
                cmin=0,
                cmax=100,
                showscale=True,
                colorbar=dict(
                    title="Wave<br>Strength",
                    x=1.12,
                    len=0.25,
                    y=0.85,
                )
            ),
            name='Wave Strength',
            hovertext=[f"Strength: {s}/100" for s in wave_strengths],
            hoverinfo='text',
        ))
    
    # 3. Leg index annotations at transitions
    for i in range(1, len(data)):
        prev_leg = data[i-1].get('mgann_leg_index', 0)
        curr_leg = data[i].get('mgann_leg_index', 0)
        
        if curr_leg != prev_leg and curr_leg > 0:
            # Leg changed - add annotation
            x_pos = indices[i]
            y_pos = data[i].get('high', 0) + 2
            
            # Color based on ext_dir
            ext_dir = data[i].get('ext_dir', 0)
            if ext_dir == 1:
                color = '#00AA00'  # Green for uptrend
            elif ext_dir == -1:
                color = '#AA0000'  # Red for downtrend
            else:
                color = '#666666'  # Gray for no trend
            
            fig.add_annotation(
                x=x_pos,
                y=y_pos,
                text=f"L{curr_leg}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=color,
                ax=0,
                ay=-40,
                font=dict(size=11, color=color, family='Arial Black'),
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor=color,
                borderwidth=2
            )
    
    # 4. BOS/CHOCH event markers
    for i, bar in enumerate(data):
        x = indices[i]
        
        if bar.get('ext_bos_up'):
            fig.add_annotation(x=x, y=bar.get('high')+5, text="BOS↑", showarrow=False,
                             font=dict(size=10, color='#00CC00'), bgcolor='rgba(255,255,255,0.8)',
                             bordercolor='#00CC00', borderwidth=1)
        if bar.get('ext_bos_down'):
            fig.add_annotation(x=x, y=bar.get('low')-5, text="BOS↓", showarrow=False,
                             font=dict(size=10, color='#CC0000'), bgcolor='rgba(255,255,255,0.8)',
                             bordercolor='#CC0000', borderwidth=1)
        if bar.get('ext_choch_up'):
            fig.add_annotation(x=x, y=bar.get('high')+5, text="CH↑", showarrow=False,
                             font=dict(size=10, color='#00CCCC'), bgcolor='rgba(255,255,255,0.8)',
                             bordercolor='#00CCCC', borderwidth=1)
        if bar.get('ext_choch_down'):
            fig.add_annotation(x=x, y=bar.get('low')-5, text="CH↓", showarrow=False,
                             font=dict(size=10, color='#FF9900'), bgcolor='rgba(255,255,255,0.8)',
                             bordercolor='#FF9900', borderwidth=1)
    
    fig.update_layout(
        title=f'Module 14 v1.2.0 - Leg Index Visualization (Bars {start_idx}-{start_idx+len(data)})',
        xaxis_title='Bar Index',
        yaxis_title='Price',
        height=700,
        hovermode='x unified',
        xaxis=dict(rangeslider=dict(visible=False)),
    )
    
    return fig

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='module14_results.json')
    parser.add_argument('--start', type=int, default=300)
    parser.add_argument('--end', type=int, default=500)
    args = parser.parse_args()
    
    # Load data
    with open(args.input, 'r') as f:
        full_data = json.load(f)
    
    data = full_data[args.start:args.end]
    
    print(f"✓ Loaded {len(data)} bars (range {args.start}-{args.end})")
    
    # Create chart
    fig = create_leg_index_chart(data, args.start)
    
    # Save
    output_file = f'charts/leg_index_{args.start}_{args.end}.html'
    fig.write_html(output_file)
    
    print(f"✅ Saved: {output_file}")
    
    # Stats
    leg_changes = sum(1 for i in range(1, len(data)) 
                     if data[i].get('mgann_leg_index') != data[i-1].get('mgann_leg_index'))
    max_leg = max(d.get('mgann_leg_index', 0) for d in data)
    
    print(f"   Leg transitions: {leg_changes}")
    print(f"   Max leg index: {max_leg}")
