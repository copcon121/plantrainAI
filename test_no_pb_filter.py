#!/usr/bin/env python3
"""Test WITHOUT PB Wave Filter - Direct approach"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
files = sorted(export_dir.glob("*M1*.jsonl"))

print("=" * 80)
print("TEST WITHOUT PB WAVE FILTER")
print("=" * 80)
print(f"\n📂 {len(files)} files")
print("⚠️  PB Wave Filter: DISABLED\n")

all_signals = []

for jsonl_file in files:
    # Fresh modules for each file
    mgann = Fix14MgannSwing()
    strategy = Fix16StrategyV1()
    
    signals_long = 0
    signals_short = 0
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            bar = json.loads(line.strip())
            
            # Process (data already has ext_dir, fvg_detected from NinjaTrader)
            mgann.process_bar(bar)
            strategy.process_bar(bar)
            
            if bar.get('strategy_signal_long'):
                all_signals.append({
                    'timestamp': bar['timestamp'],
                    'direction': 'LONG',
                    'trade': bar['strategy_trade_long'],
                    'fvg_info': bar.get('strategy_fvg_info_long')
                })
                signals_long += 1
            
            if bar.get('strategy_signal_short'):
                all_signals.append({
                    'timestamp': bar['timestamp'],
                    'direction': 'SHORT',
                    'trade': bar['strategy_trade_short'],
                    'fvg_info': bar.get('strategy_fvg_info_short')
                })
                signals_short += 1
    
    print(f"{jsonl_file.name[-17:]}: {signals_long}L {signals_short}S")

with open('strategy_no_pb_filter.json', 'w') as f:
    json.dump(all_signals, f, indent=2)

longs = sum(1 for s in all_signals if s['direction'] == 'LONG')
shorts = sum(1 for s in all_signals if s['direction'] == 'SHORT')

print(f"\n{'='*80}\n📊 RESULTS\n{'='*80}")
print(f"\nLONG: {longs} | SHORT: {shorts} | TOTAL: {len(all_signals)}")
print(f"Per day: {len(all_signals)/30:.1f}")

print(f"\n📊 COMPARISON:")
print(f"  WITH filter:    130 (4.3/day) - 37.4% WR, $317 P&L")
print(f"  WITHOUT filter: {len(all_signals)} ({len(all_signals)/30:.1f}/day)")  
print(f"  Difference:     {len(all_signals)-130:+d} ({(len(all_signals)-130)/130*100:+.1f}%)")

print(f"\n{'='*80}\n✅ DONE!\n{'='*80}")
