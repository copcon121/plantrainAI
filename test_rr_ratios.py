#!/usr/bin/env python3
"""
Test Strategy V1 with different Risk:Reward ratios
Compare 2:1, 3:1, and 4:1 to find optimal setup
"""

import json
import sys
import os
from pathlib import Path

# Add processor to path
sys.path.insert(0, str(Path(__file__).parent))

from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1


def prepare_bar(raw_bar):
    """Convert JSONL bar to format expected by modules."""
    bar_data = raw_bar.get('bar', {})

    prepared = {
        # OHLC
        'high': raw_bar.get('high', 0),
        'low': raw_bar.get('low', 0),
        'open': raw_bar.get('open', 0),
        'close': raw_bar.get('close', 0),

        # Volume
        'volume': bar_data.get('volume_stats', {}).get('total_volume', raw_bar.get('volume', 0)),
        'delta': bar_data.get('volume_stats', {}).get('delta_close', raw_bar.get('delta', 0)),

        # Technical
        'atr14': raw_bar.get('atr_14', 0),
        'range': raw_bar.get('high', 0) - raw_bar.get('low', 0),
        'tick_size': 0.1,

        # Timestamp
        'timestamp': raw_bar.get('timestamp', ''),
        'bar_index': raw_bar.get('bar_index', 0),

        # External structure
        'ext_dir': bar_data.get('ext_dir', raw_bar.get('current_trend', 0)),
        'ext_choch_up': bar_data.get('ext_choch_up', False),
        'ext_choch_down': bar_data.get('ext_choch_down', False),
        'ext_bos_up': bar_data.get('ext_bos_up', False),
        'ext_bos_down': bar_data.get('ext_bos_down', False),

        # FVG fields (ROOT LEVEL)
        'fvg_detected': raw_bar.get('fvg_detected', False),
        'fvg_type': raw_bar.get('fvg_type'),
        'fvg_top': raw_bar.get('fvg_top'),
        'fvg_bottom': raw_bar.get('fvg_bottom'),

        # Swing points
        'last_swing_high': raw_bar.get('last_swing_high'),
        'last_swing_low': raw_bar.get('last_swing_low'),
    }

    return prepared


class TradeSimulator:
    """Simulates trade execution with SL/TP"""

    def __init__(self, rr_ratio=3.0):
        self.rr_ratio = rr_ratio
        self.open_trades = []
        self.closed_trades = []

    def add_signal(self, signal_data, bar_index):
        """Add new signal as open trade"""
        trade = {
            'direction': signal_data['direction'],
            'entry': signal_data['entry_price'],
            'sl': signal_data['stop_loss'],
            'tp': signal_data['take_profit'],
            'risk': signal_data['risk_dollars'],
            'reward': signal_data['reward_dollars'],
            'entry_bar': bar_index,
            'status': 'open',
            'pnl': 0,
            'hold_bars': 0,
            'signal_data': signal_data
        }
        self.open_trades.append(trade)

    def update_trades(self, bar, bar_index):
        """Check if any open trades hit SL or TP"""
        high = bar.get('high', 0)
        low = bar.get('low', 0)

        for trade in self.open_trades[:]:
            trade['hold_bars'] = bar_index - trade['entry_bar']

            if trade['direction'] == 'LONG':
                # Check SL first (conservative)
                if low <= trade['sl']:
                    trade['status'] = 'loss'
                    trade['exit_bar'] = bar_index
                    trade['exit_price'] = trade['sl']
                    trade['pnl'] = -trade['risk']
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)
                # Then check TP
                elif high >= trade['tp']:
                    trade['status'] = 'win'
                    trade['exit_bar'] = bar_index
                    trade['exit_price'] = trade['tp']
                    trade['pnl'] = trade['reward']
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)

            elif trade['direction'] == 'SHORT':
                # Check SL first
                if high >= trade['sl']:
                    trade['status'] = 'loss'
                    trade['exit_bar'] = bar_index
                    trade['exit_price'] = trade['sl']
                    trade['pnl'] = -trade['risk']
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)
                # Then check TP
                elif low <= trade['tp']:
                    trade['status'] = 'win'
                    trade['exit_bar'] = bar_index
                    trade['exit_price'] = trade['tp']
                    trade['pnl'] = trade['reward']
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)

    def get_stats(self):
        """Calculate performance statistics"""
        if not self.closed_trades:
            return None

        wins = [t for t in self.closed_trades if t['status'] == 'win']
        losses = [t for t in self.closed_trades if t['status'] == 'loss']

        total_trades = len(self.closed_trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        total_win_pnl = sum(t['pnl'] for t in wins)
        total_loss_pnl = abs(sum(t['pnl'] for t in losses))
        net_pnl = sum(t['pnl'] for t in self.closed_trades)

        profit_factor = (total_win_pnl / total_loss_pnl) if total_loss_pnl > 0 else 0

        avg_win = (total_win_pnl / win_count) if win_count > 0 else 0
        avg_loss = (total_loss_pnl / loss_count) if loss_count > 0 else 0

        avg_hold_bars = sum(t['hold_bars'] for t in self.closed_trades) / total_trades

        return {
            'total_trades': total_trades,
            'wins': win_count,
            'losses': loss_count,
            'win_rate': win_rate,
            'net_pnl': net_pnl,
            'total_win_pnl': total_win_pnl,
            'total_loss_pnl': total_loss_pnl,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_hold_bars': avg_hold_bars,
            'rr_ratio': self.rr_ratio
        }


def run_backtest_with_rr(rr_ratio, data_folder='data_backtesst', max_files=30):
    """Run backtest with specified R:R ratio"""

    print(f"\n{'='*60}")
    print(f"Testing R:R Ratio: {rr_ratio}:1")
    print(f"{'='*60}\n")

    # Initialize modules
    mgann = Fix14MgannSwing()
    strategy = Fix16StrategyV1(risk_reward_ratio=rr_ratio)

    # Initialize simulator
    simulator = TradeSimulator(rr_ratio=rr_ratio)

    # Get data files
    data_path = Path(data_folder)
    if not data_path.exists():
        print(f"❌ Data folder not found: {data_folder}")
        return None

    jsonl_files = sorted(data_path.glob('*.jsonl'))[:max_files]
    print(f"📁 Processing {len(jsonl_files)} files...")

    total_bars = 0
    total_signals = 0

    # Process each file
    for file_idx, file_path in enumerate(jsonl_files, 1):
        with open(file_path, 'r') as f:
            bars = [json.loads(line) for line in f]

        total_bars += len(bars)

        # Process bars
        for bar_idx, raw_bar in enumerate(bars):
            # Prepare bar
            bar = prepare_bar(raw_bar)

            # Module 14: MGann swing
            bar = mgann.process_bar(bar)

            # Strategy V1
            bar = strategy.process_bar(bar)

            if 'signal' in bar and isinstance(bar['signal'], dict):
                signal_info = bar['signal']
                trade_info = signal_info.get('trade', {})

                # Only process if we have valid trade info
                if trade_info:
                    # Convert to simulator format
                    signal_data = {
                        'direction': signal_info['direction'],
                        'entry_price': trade_info['entry'],
                        'stop_loss': trade_info['sl'],
                        'take_profit': trade_info['tp'],
                        'risk_dollars': trade_info['risk'],
                        'reward_dollars': trade_info['reward']
                    }

                    total_signals += 1
                    simulator.add_signal(signal_data, bar_idx)

            # Update open trades
            simulator.update_trades(bar, bar_idx)

        # Progress
        if file_idx % 5 == 0:
            print(f"  Processed {file_idx}/{len(jsonl_files)} files... ({total_bars:,} bars, {total_signals} signals)")

    print(f"\n✅ Completed: {total_bars:,} bars, {total_signals} signals generated")

    # Get statistics
    stats = simulator.get_stats()

    if stats:
        # Calculate break-even win rate needed
        breakeven_wr = 100 / (1 + rr_ratio)

        print(f"\n{'='*60}")
        print(f"BACKTEST RESULTS (R:R = {rr_ratio}:1)")
        print(f"{'='*60}")
        print(f"Total Trades:      {stats['total_trades']}")
        print(f"Wins:              {stats['wins']} ({stats['win_rate']:.1f}%)")
        print(f"Losses:            {stats['losses']}")
        print(f"Win Rate:          {stats['win_rate']:.1f}%")
        print(f"Break-even WR:     {breakeven_wr:.1f}%")
        print(f"")
        print(f"Net P&L:           ${stats['net_pnl']:.2f}")
        print(f"Profit Factor:     {stats['profit_factor']:.2f}")
        print(f"Avg Win:           ${stats['avg_win']:.2f}")
        print(f"Avg Loss:          ${stats['avg_loss']:.2f}")
        print(f"Avg Hold:          {stats['avg_hold_bars']:.1f} bars")
        print(f"")

        # Expectancy per trade
        expectancy = stats['net_pnl'] / stats['total_trades']
        print(f"Expectancy/Trade:  ${expectancy:.2f}")

        # Evaluation
        if stats['win_rate'] > breakeven_wr:
            print(f"✅ PROFITABLE (Win Rate > {breakeven_wr:.1f}%)")
        else:
            print(f"❌ LOSING (Win Rate < {breakeven_wr:.1f}%)")

        print(f"{'='*60}\n")

        # Add signals per day
        stats['signals'] = total_signals
        stats['signals_per_day'] = total_signals / len(jsonl_files)
        stats['breakeven_wr'] = breakeven_wr
        stats['expectancy'] = expectancy

    else:
        print("⚠️  No closed trades to analyze")

    return stats


def compare_rr_ratios():
    """Test and compare different R:R ratios"""

    ratios = [2.0, 3.0, 4.0]
    results = {}

    print(f"\n{'#'*60}")
    print(f"# STRATEGY V1 - R:R RATIO COMPARISON TEST")
    print(f"{'#'*60}\n")

    # Run backtest for each ratio
    for rr in ratios:
        stats = run_backtest_with_rr(rr)
        if stats:
            results[rr] = stats

    # Compare results
    print(f"\n{'='*80}")
    print(f"COMPARISON SUMMARY")
    print(f"{'='*80}")
    print(f"{'Metric':<20} {'2:1':<20} {'3:1':<20} {'4:1':<20}")
    print(f"{'-'*80}")

    metrics = [
        ('Total Trades', 'total_trades', '{:.0f}'),
        ('Signals/Day', 'signals_per_day', '{:.1f}'),
        ('Win Rate', 'win_rate', '{:.1f}%'),
        ('Break-even WR', 'breakeven_wr', '{:.1f}%'),
        ('Net P&L', 'net_pnl', '${:.2f}'),
        ('Profit Factor', 'profit_factor', '{:.2f}'),
        ('Expectancy/Trade', 'expectancy', '${:.2f}'),
        ('Avg Win', 'avg_win', '${:.2f}'),
        ('Avg Loss', 'avg_loss', '${:.2f}'),
    ]

    for metric_name, metric_key, fmt in metrics:
        row = f"{metric_name:<20}"
        for rr in ratios:
            if rr in results:
                value = results[rr].get(metric_key, 0)
                row += f" {fmt.format(value):<20}"
            else:
                row += f" {'N/A':<20}"
        print(row)

    print(f"{'-'*80}\n")

    # Recommendations
    print(f"\n{'='*80}")
    print(f"RECOMMENDATIONS")
    print(f"{'='*80}\n")

    if not results:
        print("⚠️  No results to analyze - no signals were generated")
        return results

    # Find best by net P&L
    best_pnl = max(results.items(), key=lambda x: x[1]['net_pnl'])
    print(f"🏆 Highest Net P&L:     {best_pnl[0]}:1 (${best_pnl[1]['net_pnl']:.2f})")

    # Find best by profit factor
    best_pf = max(results.items(), key=lambda x: x[1]['profit_factor'])
    print(f"📈 Best Profit Factor:  {best_pf[0]}:1 ({best_pf[1]['profit_factor']:.2f})")

    # Find best by expectancy
    best_exp = max(results.items(), key=lambda x: x[1]['expectancy'])
    print(f"💰 Best Expectancy:     {best_exp[0]}:1 (${best_exp[1]['expectancy']:.2f}/trade)")

    # Analysis
    print(f"\n📊 ANALYSIS:")
    for rr in ratios:
        if rr not in results:
            continue

        stats = results[rr]
        wr = stats['win_rate']
        be_wr = stats['breakeven_wr']
        pf = stats['profit_factor']

        print(f"\n{rr}:1 R:R:")
        print(f"  - Break-even WR needed: {be_wr:.1f}%")
        print(f"  - Actual WR achieved: {wr:.1f}%")

        if wr > be_wr:
            edge = wr - be_wr
            print(f"  - ✅ PROFITABLE with {edge:.1f}% edge over break-even")
        else:
            deficit = be_wr - wr
            print(f"  - ❌ LOSING, needs {deficit:.1f}% higher win rate")

        if pf > 1.5:
            print(f"  - Profit Factor {pf:.2f} is EXCELLENT")
        elif pf > 1.0:
            print(f"  - Profit Factor {pf:.2f} is profitable but could be better")
        else:
            print(f"  - Profit Factor {pf:.2f} is LOSING")

    print(f"\n{'='*80}\n")

    # Save results
    output_file = 'rr_ratio_comparison.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"📁 Full results saved to: {output_file}\n")

    return results


if __name__ == '__main__':
    results = compare_rr_ratios()
