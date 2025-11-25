#!/usr/bin/env python3
"""Quick check: Leg 1 bars with FVG and range pass"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

mgann = Fix14MgannSwing()
leg1_bars = []

with open(test_file, 'r') as f:
    for line in f:
        bar = json.loads(line.strip())
        
        # Flatten
        bar_obj = bar.get('bar', {})
        vol_stats = bar_obj.get('volume_stats', {})
        if vol_stats:
            bar['delta'] = vol_stats.get('delta_close', 0)
            bar['volume'] = vol_stats.get('total_volume', 0)
        bar['ext_choch_up'] = bar_obj.get('ext_choch_up', False)
        bar['ext_choch_down'] = bar_obj.get('ext_choch_down', False)
        bar['fvg_detected'] = bar_obj.get('fvg_detected', False)
        bar['fvg_type'] = bar_obj.get('fvg_type')
        
        bar = mgann.process_bar(bar)
        
        if bar.get('mgann_leg_index') == 1:
            leg1_bars.append({
                'bar': bar.get('bar_index'),
                'close': bar.get('close'),
                'swing_low': bar.get('last_swing_low'),
                'swing_high': bar.get('last_swing_high'),
                'pass_long_range': bar.get('close', 0) > bar.get('last_swing_low', 0) if bar.get('last_swing_low') else None,
                'pass_short_range': bar.get('close', 0) < bar.get('last_swing_high', 0) if bar.get('last_swing_high') else None,
                'fvg': bar.get('fvg_detected'),
                'fvg_type': bar.get('fvg_type'),
            })

print(f"Total Leg 1 bars: {len(leg1_bars)}\n")

# LONG candidates
long_candidates = [b for b in leg1_bars 
                   if b['pass_long_range'] and b['fvg'] and b['fvg_type'] == 'bullish']
print(f"LONG candidates (Leg1 + range + FVG bullish): {len(long_candidates)}")
for b in long_candidates[:5]:
    print(f"  Bar {b['bar']}: close={b['close']}, swing_low={b['swing_low']}")

# SHORT candidates
short_candidates = [b for b in leg1_bars
                    if b['pass_short_range'] and b['fvg'] and b['fvg_type'] == 'bearish']
print(f"\nSHORT candidates (Leg1 + range + FVG bearish): {len(short_candidates)}")
for b in short_candidates[:5]:
    print(f"  Bar {b['bar']}: close={b['close']}, swing_high={b['swing_high']}")

print(f"\n=> Total potential signals: {len(long_candidates) + len(short_candidates)}")
