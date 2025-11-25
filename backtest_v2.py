#!/usr/bin/env python3
"""
Backtest Strategy V2
Simulates trade execution and calculates performance metrics
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v2 import Fix16StrategyV2

# Load data
export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

print(f"Backtesting Strategy V2")
print(f"File: {test_file.name}\n")

mgann = Fix14MgannSwing()
strategy = Fix16StrategyV2()

# Process all bars and collect signals
all_bars = []
signals = []

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
        bar['fvg_top'] = bar_obj.get('fvg_top')
        bar['fvg_bottom'] = bar_obj.get('fvg_bottom')
        
        # Process
        bar = mgann.process_bar(bar)
        bar = strategy.process_bar(bar)
        
        all_bars.append(bar)
        
        if bar.get('signal_type') in ['LONG', 'SHORT']:
            signals.append({
                'bar_index': bar.get('bar_index'),
                'type': bar['signal_type'],
                'entry': bar['entry_price'],
                'sl': bar['sl'],
                'tp': bar['tp'],
                'risk': bar['risk'],
                'entry_bar_idx': len(all_bars) - 1,
            })

print(f"Total signals: {len(signals)}")
print(f"  LONG: {sum(1 for s in signals if s['type'] == 'LONG')}")
print(f"  SHORT: {sum(1 for s in signals if s['type'] == 'SHORT')}")

# Simulate each trade
results = []

for sig in signals:
    entry_idx = sig['entry_bar_idx']
    entry = sig['entry']
    sl = sig['sl']
    tp = sig['tp']
    direction = sig['type']
    
    # Look forward from entry to find TP or SL hit
    hit_tp = False
    hit_sl = False
    exit_bar_idx = None
    exit_price = None
    
    for i in range(entry_idx + 1, len(all_bars)):
        bar = all_bars[i]
        high = bar.get('high', 0)
        low = bar.get('low', 0)
        
        if direction == 'LONG':
            # Check SL first
            if low <= sl:
                hit_sl = True
                exit_bar_idx = i
                exit_price = sl
                break
            # Then check TP
            if high >= tp:
                hit_tp = True
                exit_bar_idx = i
                exit_price = tp
                break
        else:  # SHORT
            # Check SL first
            if high >= sl:
                hit_sl = True
                exit_bar_idx = i
                exit_price = sl
                break
            # Then check TP
            if low <= tp:
                hit_tp = True
                exit_bar_idx = i
                exit_price = tp
                break
    
    # Calculate P/L
    if hit_tp:
        pnl = sig['risk'] * 3  # 3R
        outcome = 'WIN'
    elif hit_sl:
        pnl = -sig['risk']
        outcome = 'LOSS'
    else:
        # Open trade (not hit yet)
        pnl = 0
        outcome = 'OPEN'
    
    results.append({
        'signal': sig,
        'outcome': outcome,
        'pnl': pnl,
        'exit_bar_idx': exit_bar_idx,
        'bars_in_trade': exit_bar_idx - entry_idx if exit_bar_idx else None,
    })

# Calculate metrics
wins = [r for r in results if r['outcome'] == 'WIN']
losses = [r for r in results if r['outcome'] == 'LOSS']
open_trades = [r for r in results if r['outcome'] == 'OPEN']

total_pnl = sum(r['pnl'] for r in results)
win_rate = len(wins) / len(results) * 100 if results else 0

print("\n" + "=" * 70)
print("BACKTEST RESULTS")
print("=" * 70)
print(f"Total trades: {len(results)}")
print(f"  Wins: {len(wins)}")
print(f"  Losses: {len(losses)}")
print(f"  Open: {len(open_trades)}")
print(f"\nWin Rate: {win_rate:.1f}%")
print(f"Total P/L: {total_pnl:.2f}")
print(f"Average P/L per trade: {total_pnl/len(results):.2f}" if results else "N/A")

if wins:
    avg_win_time = sum(r['bars_in_trade'] for r in wins) / len(wins)
    print(f"\nAverage bars in winning trade: {avg_win_time:.1f}")
if losses:
    avg_loss_time = sum(r['bars_in_trade'] for r in losses) / len(losses)
    print(f"Average bars in losing trade: {avg_loss_time:.1f}")

# Show first few trades
print(f"\nFirst 10 trades:")
for i, r in enumerate(results[:10]):
    sig = r['signal']
    print(f"{i+1}. Bar {sig['bar_index']}: {sig['type']} -> {r['outcome']}, " +
          f"P/L={r['pnl']:.2f}, Duration={r.get('bars_in_trade', 'N/A')} bars")

print("\n" + "=" * 70)
