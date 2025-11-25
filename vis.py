#!/usr/bin/env python3
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse, json
import plotly.graph_objects as go

def load_data(filepath, start=None, end=None):
    with open(filepath, 'r') as f:
        data = json.load(f)
    start = start or 0
    end = end or len(data)
    return data[start:end], start

def create_chart(data, start_idx, min_delta=0, min_bars=0):
    """
    min_delta: Only show delta sum if abs(delta) >= this value (0 = show all)
    min_bars: Only show delta sum if wave >= this many bars (0 = show all)
    """
    fig = go.Figure()
    indices = list(range(start_idx, start_idx + len(data)))
    
    # 1. Price candles
    # Extract timestamps for hover
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
    legs = [b.get('mgann_leg_index') for b in data]
    
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
            f"{ts}<br>O: {o:.2f}<br>H: {h:.2f}<br>L: {l:.2f}<br>C: {c:.2f}<br>Leg: {leg if leg is not None else '-'}"
            for ts, o, h, l, c, leg in zip(timestamps, opens, highs, lows, closes, legs)
        ],
        hoverinfo='text',
    ))
    
    # 2. Swing zigzag
    swing_highs = [b.get('mgann_internal_swing_high') for b in data]
    swing_lows = [b.get('mgann_internal_swing_low') for b in data]
    leg_dirs = [b.get('mgann_internal_leg_dir', 0) for b in data]
    bos_up_x, bos_up_y = [], []
    bos_down_x, bos_down_y = [], []
    choch_up_x, choch_up_y = [], []
    choch_down_x, choch_down_y = [], []
    bos_up_hover, bos_down_hover = [], []
    choch_up_hover, choch_down_hover = [], []
    
    swing_points = []
    last_high, last_low = None, None
    
    for i in range(len(data)):
        curr_dir = leg_dirs[i]
        # Collect BOS/CHOCH markers for arrows
        bar = data[i]
        h = bar.get('high', highs[i])
        l = bar.get('low', lows[i])
        ts = timestamps[i]
        if bar.get('ext_bos_up'):
            bos_up_x.append(indices[i])
            bos_up_y.append(h)
            bos_up_hover.append(f"{ts}<br>BOS Up<br>H: {h:.2f}")
        if bar.get('ext_bos_down'):
            bos_down_x.append(indices[i])
            bos_down_y.append(l)
            bos_down_hover.append(f"{ts}<br>BOS Down<br>L: {l:.2f}")
        if bar.get('ext_choch_up'):
            choch_up_x.append(indices[i])
            choch_up_y.append(h)
            choch_up_hover.append(f"{ts}<br>CHOCH Up<br>H: {h:.2f}")
        if bar.get('ext_choch_down'):
            choch_down_x.append(indices[i])
            choch_down_y.append(l)
            choch_down_hover.append(f"{ts}<br>CHOCH Down<br>L: {l:.2f}")

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
    
    if len(swing_points) >= 2:
        # Zigzag line
        fig.add_trace(go.Scatter(
            x=[p[0] for p in swing_points],
            y=[p[1] for p in swing_points],
            mode='lines', line=dict(width=3, color='#FF6B00'),
            name='Zigzag'
        ))
        
        # Wave strength markers - SEPARATE normalization for UP and DOWN waves
        wave_strengths = []
        wave_delta_sums = []
        wave_types = []  # 'up' or 'down'
        
        for i in range(len(swing_points)):
            if i == 0:
                wave_delta_sums.append(0)
                wave_types.append('neutral')
            else:
                prev_idx = swing_points[i-1][3]
                curr_idx = swing_points[i][3]
                delta_sum = sum(data[j].get('delta', 0) for j in range(prev_idx, curr_idx + 1) 
                              if 0 <= j < len(data))
                wave_delta_sums.append(delta_sum)
                wave_types.append('up' if delta_sum > 0 else 'down')
        
        # Separate normalization for up and down waves
        up_deltas = [d for d, t in zip(wave_delta_sums, wave_types) if t == 'up']
        down_deltas = [abs(d) for d, t in zip(wave_delta_sums, wave_types) if t == 'down']
        
        max_up = max(up_deltas) if up_deltas else 1
        max_down = max(down_deltas) if down_deltas else 1
        
        # Calculate strength based on wave type
        for delta, wave_type in zip(wave_delta_sums, wave_types):
            if wave_type == 'neutral':
                wave_strengths.append(0)
            elif wave_type == 'up':
                # Compare with other upwaves
                strength = int(min(100, (delta / max_up) * 100))
                wave_strengths.append(strength)
            else:  # down
                # Compare with other downwaves
                strength = int(min(100, (abs(delta) / max_down) * 100))
                wave_strengths.append(strength)
        
        fig.add_trace(go.Scatter(
            x=[p[0] for p in swing_points],
            y=[p[1] for p in swing_points],
            mode='markers',
            marker=dict(
                size=10,
                color=wave_strengths,
                colorscale='RdYlGn',  # Red (weak) to Green (strong)
                cmin=0,
                cmax=100,
                showscale=True,
                colorbar=dict(
                    title="Wave<br>Strength<br>(Delta)",
                    x=1.12,
                    len=0.3,
                    y=0.8,
                )
            ),
            name='Wave Strength',
            hovertext=[f"Delta: {d}<br>Type: {t}<br>Strength: {s}/100" 
                      for d, t, s in zip(wave_delta_sums, wave_types, wave_strengths)],
            hoverinfo='text',
        ))


        
        # Delta sum labels - Calculate for COMPLETED waves (from prev swing to current swing)
        # This shows the delta accumulated when a new swing is confirmed
        for i in range(1, len(swing_points)):
            prev_swing_idx = swing_points[i-1][3]  # Previous swing data index
            curr_swing_idx = swing_points[i][3]    # Current swing data index
            curr_swing_type = swing_points[i][2]   # 'high' or 'low'
            
            # Calculate delta sum from previous swing to current swing
            delta_sum = sum(data[j].get('delta', 0) for j in range(prev_swing_idx, curr_swing_idx + 1) 
                          if 0 <= j < len(data))
            
            wave_length = curr_swing_idx - prev_swing_idx
            
            # FILTER: All waves shown when min_delta/min_bars = 0
            if abs(delta_sum) >= min_delta and wave_length >= min_bars:
                x_pos = swing_points[i][0]  # Position at current swing point
                y_pos = swing_points[i][1]
                
                # Color based on wave direction and delta sign
                # Upwave (to high): blue color, positive delta
                # Downwave (to low): red color, negative delta
                if curr_swing_type == 'high':
                    # Wave went UP to create this high
                    color = '#0066CC'  # Blue
                    y_offset = 2.5  # Above the high
                else:
                    # Wave went DOWN to create this low
                    color = '#CC0000'  # Red
                    y_offset = -2.5  # Below the low
                
                fig.add_annotation(
                    x=x_pos, y=y_pos + y_offset,
                    text=str(int(delta_sum)),
                    showarrow=False,
                    font=dict(size=10, color=color, family='Arial'),
                    bgcolor='rgba(255,255,255,0.7)'
                )

        # Leg index labels at swing points
        for x_pos, y_pos, swing_type, data_idx in swing_points:
            if 0 <= data_idx < len(legs):
                leg_idx = legs[data_idx]
            else:
                leg_idx = None

            if leg_idx is None:
                continue

            # Offset to avoid overlapping the zigzag lines
            y_offset = 4 if swing_type == 'low' else -4
            fig.add_annotation(
                x=x_pos,
                y=y_pos + y_offset,
                text=f"Leg {leg_idx}",
                showarrow=False,
                font=dict(size=9, color="#444", family="Arial"),
                bgcolor='rgba(255,255,255,0.65)'
            )

    # BOS/CHOCH arrow markers
    if bos_up_x:
        fig.add_trace(go.Scatter(
            x=bos_up_x, y=bos_up_y,
            mode='markers', name='BOS Up',
            marker=dict(symbol='triangle-up', size=12, color='#00CC00', line=dict(width=1, color='#006600')),
            hovertext=bos_up_hover, hoverinfo='text'
        ))
    if bos_down_x:
        fig.add_trace(go.Scatter(
            x=bos_down_x, y=bos_down_y,
            mode='markers', name='BOS Down',
            marker=dict(symbol='triangle-down', size=12, color='#CC0000', line=dict(width=1, color='#660000')),
            hovertext=bos_down_hover, hoverinfo='text'
        ))
    if choch_up_x:
        fig.add_trace(go.Scatter(
            x=choch_up_x, y=choch_up_y,
            mode='markers', name='CHOCH Up',
            marker=dict(symbol='triangle-up', size=11, color='#00CCCC', line=dict(width=1, color='#008888')),
            hovertext=choch_up_hover, hoverinfo='text'
        ))
    if choch_down_x:
        fig.add_trace(go.Scatter(
            x=choch_down_x, y=choch_down_y,
            mode='markers', name='CHOCH Down',
            marker=dict(symbol='triangle-down', size=11, color='#FF9900', line=dict(width=1, color='#AA6600')),
            hovertext=choch_down_hover, hoverinfo='text'
        ))
    
    # 3. BOS/CHOCH horizontal dash lines at pivot levels
    line_length = 20  # Number of bars to extend line on each side
    
    for i, bar in enumerate(data):
        x = indices[i]
        x_start = x - line_length
        x_end = x + line_length
        
        if bar.get('ext_bos_up'):
            price = bar.get('high', 0)
            fig.add_shape(type="line", x0=x_start, x1=x_end, y0=price, y1=price,
                         line=dict(color="#00CC00", width=2, dash="dash"))
            fig.add_annotation(x=x+line_length+5, y=price, text="BOS", showarrow=False,
                             font=dict(size=9, color='#00CC00'), bgcolor='rgba(255,255,255,0.8)')
        if bar.get('ext_bos_down'):
            price = bar.get('low', 0)
            fig.add_shape(type="line", x0=x_start, x1=x_end, y0=price, y1=price,
                         line=dict(color="#CC0000", width=2, dash="dash"))
            fig.add_annotation(x=x+line_length+5, y=price, text="BOS", showarrow=False,
                             font=dict(size=9, color='#CC0000'), bgcolor='rgba(255,255,255,0.8)')
        if bar.get('ext_choch_up'):
            price = bar.get('high', 0)
            fig.add_shape(type="line", x0=x_start, x1=x_end, y0=price, y1=price,
                         line=dict(color="#00CCCC", width=2, dash="dash"))
            fig.add_annotation(x=x+line_length+5, y=price, text="CH", showarrow=False,
                             font=dict(size=9, color='#00CCCC'), bgcolor='rgba(255,255,255,0.8)')
        if bar.get('ext_choch_down'):
            price = bar.get('low', 0)
            fig.add_shape(type="line", x0=x_start, x1=x_end, y0=price, y1=price,
                         line=dict(color="#FF9900", width=2, dash="dash"))
            fig.add_annotation(x=x+line_length+5, y=price, text="CH", showarrow=False,
                             font=dict(size=9, color='#FF9900'), bgcolor='rgba(255,255,255,0.8)')
    
    fig.update_layout(
        title=f'MGann Swing (Bars {start_idx}-{start_idx+len(data)}) - Delta ≥{min_delta}, Bars ≥{min_bars}',
        xaxis=dict(title='Bar Index', rangeslider=dict(visible=False)),
        yaxis=dict(title='Price'),
        height=800,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int)
    parser.add_argument('--min-delta', type=int, default=0, help='Minimum delta to show label (0 = show all)')
    parser.add_argument('--min-bars', type=int, default=0, help='Minimum bars in wave to show label (0 = show all)')
    args = parser.parse_args()
    
    data, start_idx = load_data(args.input, args.start, args.end)
    print(f"✓ Loaded {len(data)} bars")
    
    fig = create_chart(data, start_idx, args.min_delta, args.min_bars)
    output = f"charts/visual_mgann_{args.start}_{args.start+len(data)}.html"
    fig.write_html(output)
    print(f"✅ Saved: {output}")
    print(f"   Filter: delta ≥ {args.min_delta}, wave ≥ {args.min_bars} bars")
