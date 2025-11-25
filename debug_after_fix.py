#!/usr/bin/env python3
"""Debug strategy after ext_dir removal - find NEW blocking condition"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print("DEBUG: Check each condition after ext_dir removal\n")

mgann = Fix14MgannSwing()
strategy = Fix16StrategyV1()

choch_events = []

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar = json.loads(line.strip())
        
        # Flatten
        bar_obj = bar.get('bar', {})
        bar['ext_choch_up'] = bar_obj.get('ext_choch_up', False)
        bar['ext_choch_down'] = bar_obj.get('ext_choch_down', False)
        vol_stats = bar_obj.get('volume_stats', {})
        if vol_stats:
            bar['delta'] = vol_stats.get('delta_close', 0)
            bar['volume'] = vol_stats.get('volume', 0)
        bar['fvg_detected'] = bar_obj.get('fvg_detected', False)
        bar['fvg_type'] = bar_obj.get('fvg_type')
        bar['fvg_top'] = bar_obj.get('fvg_top')
        bar['fvg_bottom'] = bar_obj.get('fvg_bottom')
        
        # Process Module 14
        bar = mgann.process_bar(bar)
        
        # Check CHoCH events and conditions
        if bar.get('ext_choch_down'):
            # LONG signal attempt
            choch_events.append({
                'bar': bar.get('bar_index'),
                'type': 'CHoCH_DOWN (LONG)',
                'close': bar.get('close'),
                'last_swing_low': bar.get('last_swing_low'),
                'pass_range': bar.get('close', 0) > bar.get('last_swing_low', 0) if bar.get('last_swing_low') else True,
                'leg': bar.get('mgann_leg_index'),
                'pass_leg': 0 < bar.get('mgann_leg_index', 0) <= 2,
                'fvg': bar.get('fvg_detected'),
                'fvg_type': bar.get('fvg_type'),
                'pass_fvg': bar.get('fvg_detected') and bar.get('fvg_type') == 'bullish',
            })
        
        if bar.get('ext_choch_up'):
            # SHORT signal attempt
            choch_events.append({
                'bar': bar.get('bar_index'),
                'type': 'CHoCH_UP (SHORT)',
                'close': bar.get('close'),
                'last_swing_high': bar.get('last_swing_high'),
                'pass_range': bar.get('close', 0) < bar.get('last_swing_high', 0) if bar.get('last_swing_high') else True,
                'leg': bar.get('mgann_leg_index'),
                'pass_leg': 0 < bar.get('mgann_leg_index', 0) <= 2,
                'fvg': bar.get('fvg_detected'),
                'fvg_type': bar.get('fvg_type'),
                'pass_fvg': bar.get('fvg_detected') and bar.get('fvg_type') == 'bearish',
            })

print("=" * 70)
print(f"Found {len(choch_events)} CHoCH events")
print("=" * 70)

for event in choch_events:
    all_pass = event['pass_range'] and event['pass_leg'] and event['pass_fvg']
    status = "ALL PASS" if all_pass else "BLOCKED"
    
    print(f"\nBar {event['bar']}: {event['type']} - {status}")
    print(f"  Range Filter: {event['pass_range']} (close={event['close']}, swing={event.get('last_swing_low') or event.get('last_swing_high')})")
    print(f"  Leg Filter: {event['pass_leg']} (leg={event['leg']})")
    print(f"  FVG Filter: {event['pass_fvg']} (fvg={event['fvg']}, type={event['fvg_type']})")

print("\n" + "=" * 70)
print(f"Summary: {sum(1 for e in choch_events if e['pass_range'] and e['pass_leg'] and e['pass_fvg'])} would generate signals")
