#!/usr/bin/env python3
"""Debug Module 15 swing detection logic."""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from processor.modules.fix15_m5_context import Fix15M5Context

# Load test data
with open('deepseek_enhanced_GC 12-25_M1_20251103.jsonl', 'r') as f:
    bars = [json.loads(line) for line in f]

print("Testing Module 15 M5 swing detection...")
print(f"Total M1 bars: {len(bars)}")
print(f"Expected M5 bars: {len(bars) // 5}")

module = Fix15M5Context(swing_window=50)

# Process first 300 M1 bars (= 60 M5 bars)
for i, raw_bar in enumerate(bars[:300]):
    bar_data = raw_bar.get('bar', {})
    volume_stats = bar_data.get('volume_stats', {})
    
    bar_state = {
        'open': bar_data.get('o', 0),
        'high': bar_data.get('h', 0),
        'low': bar_data.get('l', 0),
        'close': bar_data.get('c', 0),
        'volume': volume_stats.get('total_volume', 0),
    }
    
    result = module.process_bar(bar_state)
    
    # Print M5 bar completions
    if (i + 1) % 5 == 0:
        m5_bar_num = (i + 1) // 5
        print(f"\nM5 Bar {m5_bar_num} (M1 bar {i+1}):")
        
        if len(module.m5_bars_history) > 0:
            latest_m5 = list(module.m5_bars_history)[-1]
            print(f"  OHLC: O={latest_m5['open']:.2f}, H={latest_m5['high']:.2f}, "
                  f"L={latest_m5['low']:.2f}, C={latest_m5['close']:.2f}")
        
        print(f"  last_leg_ext: {module.last_leg_ext}")
        print(f"  ext_high_curr: {module.ext_high_curr}")
        print(f"  ext_low_curr: {module.ext_low_curr}")
        print(f"  ext_high_last: {module.ext_high_last}")
        print(f"  ext_low_last: {module.ext_low_last}")
        print(f"  ext_bias: {module.ext_bias}")
        
        if result.get('m5_ext_bos_up') or result.get('m5_ext_bos_down') or \
           result.get('m5_ext_choch_up') or result.get('m5_ext_choch_down'):
            print(f"  *** EVENTS: BOS_UP={result.get('m5_ext_bos_up')}, "
                  f"BOS_DOWN={result.get('m5_ext_bos_down')}, "
                  f"CHOCH_UP={result.get('m5_ext_choch_up')}, "
                  f"CHOCH_DOWN={result.get('m5_ext_choch_down')}")
        
        # Show swing calculation details for first 55 M5  bars
        if m5_bar_num <= 55 and m5_bar_num >= 48:
            current_idx = len(module.m5_bars_history) - 1
            win = module.swing_window
            
            if current_idx >= win:
                idx = win
                start_idx = max(0, current_idx - win)
                window_bars = list(module.m5_bars_history)[start_idx:current_idx]
                
                if window_bars:
                    max_high = max(b['high'] for b in window_bars)
                    min_low = min(b['low'] for b in window_bars)
                    bar_at_win = list(module.m5_bars_history)[current_idx - idx]
                    
                    print(f"  [DEBUG] Swing calc: idx={idx}, current_idx={current_idx}")
                    print(f"  [DEBUG] Window bars: {start_idx} to {current_idx} ({len(window_bars)} bars)")
                    print(f"  [DEBUG] MAX(high) in window: {max_high:.2f}")
                    print(f"  [DEBUG] MIN(low) in window: {min_low:.2f}")
                    print(f"  [DEBUG] Bar @ win: H={bar_at_win['high']:.2f}, L={bar_at_win['low']:.2f}")
                    print(f"  [DEBUG] newLegHigh? {bar_at_win['high'] > max_high}")
                    print(f"  [DEBUG] newLegLow? {bar_at_win['low'] < min_low}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"M5 bars created: {len(module.m5_bars_history)}")
print(f"Swing window: {module.swing_window}")
print(f"Last leg: {module.last_leg_ext}")
print(f"Ext bias: {module.ext_bias}")
