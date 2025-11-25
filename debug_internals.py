#!/usr/bin/env python3
"""Debug strategy internals - print WHY no signals"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print("DEBUG: Strategy Internal Check\n")

mgann = Fix14MgannSwing()
strategy = Fix16StrategyV1()

leg1_with_fvg = 0
signals_generated = 0

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        if i > 100:  # Just first 100 bars
            break
            
        bar = json.loads(line.strip() )
        
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
        bar['fvg_top'] = bar_obj.get('fvg_top')
        bar['fvg_bottom'] = bar_obj.get('fvg_bottom')
        
        # Process Module 14
        bar = mgann.process_bar(bar)
        
        # Track Leg 1 + FVG bars
        if bar.get('mgann_leg_index') == 1 and bar.get('fvg_detected'):
            leg1_with_fvg += 1
            print(f"Bar {bar.get('bar_index')}: Leg 1 + FVG ({bar.get('fvg_type')})")
            print(f"  Before strategy: {bar.keys()}")
        
        # Process strategy
        bar = strategy.process_bar(bar)
        
        if bar.get('signal'):
            signals_generated += 1
            print(f"  SIGNAL! {bar['signal']['direction']}")

print(f"\n=> Leg 1 + FVG bars: {leg1_with_fvg}")
print(f"=> Signals generated: {signals_generated}")
