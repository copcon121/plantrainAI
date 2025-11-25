#!/usr/bin/env python3
"""
Full Pipeline Test - WITHOUT PB Wave Filter
============================================
This script:
1. Loads JSONL data files
2. Flattens nested 'bar' object fields to root level
3. Runs Module 14 (MGann Swing)
4. Runs Module 16 (Strategy V1) with PB filter DISABLED
5. Generates and exports signals
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1

def flatten_bar_fields(bar_state):
    """
    Flatten nested 'bar' object fields to root level.
    Modules expect fields like ext_dir, ext_choch_up at root.
    """
    bar_obj = bar_state.get('bar', {})
    
    # Structure fields
    bar_state['ext_dir'] = bar_obj.get('ext_dir', 0)
    bar_state['int_dir'] = bar_obj.get('int_dir', 0)
    bar_state['ext_bos_up'] = bar_obj.get('ext_bos_up', False)
    bar_state['ext_bos_down'] = bar_obj.get('ext_bos_down', False)
    bar_state['ext_choch_up'] = bar_obj.get('ext_choch_up', False)
    bar_state['ext_choch_down'] = bar_obj.get('ext_choch_down', False)
    bar_state['int_bos_up'] = bar_obj.get('int_bos_up', False)
    bar_state['int_bos_down'] = bar_obj.get('int_bos_down', False)
    bar_state['int_choch_up'] = bar_obj.get('int_choch_up', False)
    bar_state['int_choch_down'] = bar_obj.get('int_choch_down', False)
    
    # FVG fields
    bar_state['fvg_detected'] = bar_obj.get('fvg_detected', False)
    bar_state['fvg_type'] = bar_obj.get('fvg_type', None)
    bar_state['fvg_top'] = bar_obj.get('fvg_top', None)
    bar_state['fvg_bottom'] = bar_obj.get('fvg_bottom', None)
    
    # Swing levels
    bar_state['last_swing_high'] = bar_obj.get('last_swing_high', None)
    bar_state['last_swing_low'] = bar_obj.get('last_swing_low', None)
    
    # Volume/Delta from nested volume_stats if exists
    vol_stats = bar_obj.get('volume_stats', {})
    if vol_stats:
        bar_state['delta'] = vol_stats.get('delta_close', 0)
        bar_state['volume'] = vol_stats.get('total_volume', 0)
    
    return bar_state


def main():
    print("=" * 80)
    print("FULL PIPELINE TEST - WITHOUT PB WAVE FILTER")
    print("=" * 80)
    
    # Load data files
    export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
    files = sorted(export_dir.glob("*M1*.jsonl"))
    
    print(f"\n📂 Found {len(files)} M1 files")
    print("   ⚠️  PB Wave Filter: DISABLED in strategy")
    print("   🔧 Field flattening: ENABLED\n")
    
    all_signals = []
    
    for jsonl_file in files:
        # Fresh modules for each file
        mgann = Fix14MgannSwing()
        strategy = Fix16StrategyV1()
        
        signals_long = 0
        signals_short = 0
        
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                bar_state = json.loads(line.strip())
                
                # CRITICAL: Flatten nested bar fields to root level
                bar_state = flatten_bar_fields(bar_state)
                
                # Process through modules
                bar_state = mgann.process_bar(bar_state)
                bar_state = strategy.process_bar(bar_state)
                
                # Collect signals
                if bar_state.get('strategy_signal_long'):
                    all_signals.append({
                        'timestamp': bar_state['timestamp'],
                        'direction': 'LONG',
                        'trade': bar_state['strategy_trade_long'],
                        'fvg_info': bar_state.get('strategy_fvg_info_long')
                    })
                    signals_long += 1
                
                if bar_state.get('strategy_signal_short'):
                    all_signals.append({
                        'timestamp': bar_state['timestamp'],
                        'direction': 'SHORT',
                        'trade': bar_state['strategy_trade_short'],
                        'fvg_info': bar_state.get('strategy_fvg_info_short')
                    })
                    signals_short += 1
        
        print(f"📄 {jsonl_file.name[-17:]}: {signals_long}L {signals_short}S")
    
    # Save results
    with open('signals_no_pb_filter_full_pipeline.json', 'w') as f:
        json.dump(all_signals, f, indent=2)
    
    # Summary
    longs = sum(1 for s in all_signals if s['direction'] == 'LONG')
    shorts = sum(1 for s in all_signals if s['direction'] == 'SHORT')
    
    print(f"\n{'='*80}")
    print("📊 RESULTS - NO PB WAVE FILTER")
    print(f"{'='*80}")
    print(f"\n🎯 SIGNALS:")
    print(f"  LONG:  {longs}")
    print(f"  SHORT: {shorts}")
    print(f"  TOTAL: {len(all_signals)}")
    print(f"  Per day: {len(all_signals)/30:.1f}")
    
    print(f"\n📊 COMPARISON:")
    print(f"  WITH PB filter (v0.2):    130 signals (4.3/day) - 37.4% WR, $317 P&L")
    print(f"  WITHOUT PB filter:        {len(all_signals)} signals ({len(all_signals)/30:.1f}/day)")
    
    if len(all_signals) > 130:
        diff = len(all_signals) - 130
        pct = (diff / 130) * 100
        print(f"  Difference:               +{diff} signals (+{pct:.1f}%)")
        print(f"\n💡 Filter removed {diff} weak pullback trades")
    elif len(all_signals) < 130:
        print(f"  ⚠️  FEWER signals - something wrong!")
    else:
        print(f"  Same count - filter had no effect?")
    
    print(f"\n💾 Saved to: signals_no_pb_filter_full_pipeline.json")
    print(f"\n{'='*80}")
    print("✅ PIPELINE TEST COMPLETE!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
