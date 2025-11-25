#!/usr/bin/env python3
"""
DEBUG Pipeline - Track why 0 signals
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1

def flatten_bar_fields(bar_state):
    """Flatten nested 'bar' fields to root."""
    bar_obj = bar_state.get('bar', {})
    bar_state['ext_dir'] = bar_obj.get('ext_dir', 0)
    bar_state['ext_choch_up'] = bar_obj.get('ext_choch_up', False)
    bar_state['ext_choch_down'] = bar_obj.get('ext_choch_down', False)
    bar_state['fvg_detected'] = bar_obj.get('fvg_detected', False)
    bar_state['fvg_type'] = bar_obj.get('fvg_type', None)
    bar_state['last_swing_high'] = bar_obj.get('last_swing_high', None)
    bar_state['last_swing_low'] = bar_obj.get('last_swing_low', None)
    
    vol_stats = bar_obj.get('volume_stats', {})
    if vol_stats:
        bar_state['delta'] = vol_stats.get('delta_close', 0)
        bar_state['volume'] = vol_stats.get('total_volume', 0)
    return bar_state

# Test ONE file only
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Testing: {test_file.name}\n")

mgann = Fix14MgannSwing()
strategy = Fix16StrategyV1()

choch_count = 0
leg_index_set = 0
fvg_detected_count = 0
ext_dir_set = 0

with open(test_file, 'r') as f:
    for i, line in enumerate(f):
        bar_state = json.loads(line.strip())
        bar_state = flatten_bar_fields(bar_state)
        
        # Track CHoCH
        if bar_state.get('ext_choch_up') or bar_state.get('ext_choch_down'):
            choch_count += 1
            print(f"Bar {i}: CHoCH! ext_dir={bar_state.get('ext_dir')}")
        
        # Process
        bar_state = mgann.process_bar(bar_state)
        
        # Track module output
        if bar_state.get('mgann_leg_index', 0) > 0:
            if leg_index_set == 0:
                leg_index_set = i
                print(f"Bar {i}: mgann_leg_index SET to {bar_state['mgann_leg_index']}")
        
        if bar_state.get('ext_dir', 0) != 0:
            if ext_dir_set == 0:
                ext_dir_set = i
                print(f"Bar {i}: ext_dir SET to {bar_state['ext_dir']}")
        
        if bar_state.get('fvg_detected'):
            fvg_detected_count += 1
            print(f"Bar {i}: FVG detected! Type={bar_state.get('fvg_type')}, Leg={bar_state.get('mgann_leg_index')}")
        
        bar_state = strategy.process_bar(bar_state)
        
        # Check signals
        if bar_state.get('strategy_signal_long'):
            print(f"✅ Bar {i}: LONG SIGNAL!")
        if bar_state.get('strategy_signal_short'):
            print(f"✅ Bar {i}: SHORT SIGNAL!")

print(f"\n{'='*60}")
print(f"Summary:")
print(f"  CHoCH events: {choch_count}")
print(f"  FVG detected: {fvg_detected_count}")
print(f"  ext_dir first set at bar: {ext_dir_set}")
print(f"  mgann_leg_index first set at bar: {leg_index_set}")
print(f"{'='*60}")
