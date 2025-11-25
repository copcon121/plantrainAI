#!/usr/bin/env python3
"""
FULL BACKTEST - Strategy V1 on All Data

Runs Strategy V1 on all files in data_backtesst/ folder
- Generates signals
- Simulates trades (check SL/TP hits)
- Calculates performance metrics
- Generates detailed report
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add project root to path
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
    """Simulate trade execution and track outcomes."""

    def __init__(self):
        self.open_trades = []
        self.closed_trades = []

    def add_signal(self, signal, bars_remaining):
        """Add new signal as pending trade."""
        trade = signal['trade'].copy()
        trade.update({
            'signal_time': signal['timestamp'],
            'signal_bar': signal['bar_index'],
            'direction': signal['direction'],
            'leg': signal['leg'],
            'fvg_new': signal['fvg_new'],
            'status': 'open',
            'exit_bar': None,
            'exit_price': None,
            'exit_reason': None,
            'pnl': 0,
            'bars_held': 0,
        })
        self.open_trades.append(trade)

    def update_trades(self, bar, bar_index):
        """Check if any open trades hit SL or TP."""
        high = bar.get('high', 0)
        low = bar.get('low', 0)

        for trade in self.open_trades[:]:  # Copy list to allow removal
            trade['bars_held'] += 1

            if trade['direction'] == 'LONG':
                # Check SL
                if low <= trade['sl']:
                    trade['status'] = 'loss'
                    trade['exit_bar'] = bar_index
                    trade['exit_price'] = trade['sl']
                    trade['exit_reason'] = 'SL_HIT'
                    trade['pnl'] = -trade['risk']
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)
                    continue

                # Check TP
                if high >= trade['tp']:
                    trade['status'] = 'win'
                    trade['exit_bar'] = bar_index
                    trade['exit_price'] = trade['tp']
                    trade['exit_reason'] = 'TP_HIT'
                    trade['pnl'] = trade['reward']
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)
                    continue

            else:  # SHORT
                # Check SL
                if high >= trade['sl']:
                    trade['status'] = 'loss'
                    trade['exit_bar'] = bar_index
                    trade['exit_price'] = trade['sl']
                    trade['exit_reason'] = 'SL_HIT'
                    trade['pnl'] = -trade['risk']
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)
                    continue

                # Check TP
                if low <= trade['tp']:
                    trade['status'] = 'win'
                    trade['exit_bar'] = bar_index
                    trade['exit_price'] = trade['tp']
                    trade['exit_reason'] = 'TP_HIT'
                    trade['pnl'] = trade['reward']
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)
                    continue

    def get_stats(self):
        """Calculate performance metrics."""
        if not self.closed_trades:
            return None

        wins = [t for t in self.closed_trades if t['status'] == 'win']
        losses = [t for t in self.closed_trades if t['status'] == 'loss']

        total_trades = len(self.closed_trades)
        win_count = len(wins)
        loss_count = len(losses)

        win_rate = win_count / total_trades if total_trades > 0 else 0

        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        net_profit = gross_profit - gross_loss

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        avg_win = gross_profit / win_count if win_count > 0 else 0
        avg_loss = gross_loss / loss_count if loss_count > 0 else 0

        # Calculate max drawdown
        cumulative = 0
        peak = 0
        max_dd = 0

        for trade in self.closed_trades:
            cumulative += trade['pnl']
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        return {
            'total_trades': total_trades,
            'wins': win_count,
            'losses': loss_count,
            'win_rate': win_rate,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': net_profit,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_dd,
            'avg_bars_held': sum(t['bars_held'] for t in self.closed_trades) / total_trades,
        }


def process_file(file_path, mgann, strategy, simulator):
    """Process single JSONL file."""
    file_stats = {
        'file': file_path.name,
        'bars': 0,
        'signals': 0,
        'long_signals': 0,
        'short_signals': 0,
    }

    with open(file_path, 'r') as f:
        for line in f:
            try:
                raw_bar = json.loads(line.strip())
                bar = prepare_bar(raw_bar)

                # Module 14: MGann Swing
                bar = mgann.process_bar(bar)

                # Strategy V1
                bar = strategy.process_bar(bar)

                # Update open trades
                simulator.update_trades(bar, file_stats['bars'])

                # Check for new signal
                if 'signal' in bar:
                    signal = bar['signal']
                    file_stats['signals'] += 1

                    if signal['direction'] == 'LONG':
                        file_stats['long_signals'] += 1
                    else:
                        file_stats['short_signals'] += 1

                    # Add to simulator (pass remaining bars count)
                    simulator.add_signal(signal, 0)

                file_stats['bars'] += 1

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"⚠️  Error processing bar {file_stats['bars']}: {e}")
                continue

    return file_stats


def main():
    print("\n" + "=" * 80)
    print("  FULL BACKTEST - Strategy V1")
    print("=" * 80 + "\n")

    # Find all data files
    data_dir = Path(__file__).parent / "data_backtesst"
    data_files = sorted(data_dir.glob("*.jsonl"))

    if not data_files:
        print(f"❌ No JSONL files found in {data_dir}")
        return 1

    print(f"📂 Data directory: {data_dir}")
    print(f"📊 Files found: {len(data_files)}")
    print(f"   Date range: {data_files[0].name.split('_')[-1].split('.')[0]} → {data_files[-1].name.split('_')[-1].split('.')[0]}")
    print()

    # Initialize modules
    print("⚙️  Initializing Strategy V1...")
    mgann = Fix14MgannSwing(threshold_ticks=6)
    strategy = Fix16StrategyV1(tick_size=0.1, risk_reward_ratio=3.0, sl_buffer_ticks=2)
    simulator = TradeSimulator()
    print("✓ Modules initialized\n")

    # Process all files
    print(f"🔄 Processing {len(data_files)} files...\n")

    all_file_stats = []
    total_bars = 0
    total_signals = 0

    for i, file_path in enumerate(data_files, 1):
        print(f"[{i}/{len(data_files)}] {file_path.name}...", end=" ", flush=True)

        file_stats = process_file(file_path, mgann, strategy, simulator)
        all_file_stats.append(file_stats)

        total_bars += file_stats['bars']
        total_signals += file_stats['signals']

        print(f"✓ {file_stats['bars']} bars, {file_stats['signals']} signals")

    print(f"\n✓ Processing complete!\n")

    # Close any remaining open trades (end of dataset)
    for trade in simulator.open_trades:
        trade['status'] = 'open_eod'
        trade['exit_reason'] = 'END_OF_DATA'

    # Calculate statistics
    stats = simulator.get_stats()

    # Display results
    print("=" * 80)
    print("📊 BACKTEST RESULTS")
    print("=" * 80)

    print(f"\n📈 DATASET OVERVIEW:")
    print(f"   Total files processed: {len(data_files)}")
    print(f"   Total bars: {total_bars:,}")
    print(f"   Total signals generated: {total_signals}")
    print(f"   Signals per day (avg): {total_signals / len(data_files):.1f}")

    if stats:
        print(f"\n💰 TRADE PERFORMANCE:")
        print(f"   Total trades: {stats['total_trades']}")
        print(f"   Wins: {stats['wins']} ({stats['win_rate']*100:.1f}%)")
        print(f"   Losses: {stats['losses']} ({(1-stats['win_rate'])*100:.1f}%)")
        print(f"   Win Rate: {stats['win_rate']*100:.1f}%")

        print(f"\n💵 P&L ANALYSIS:")
        print(f"   Gross Profit: ${stats['gross_profit']:,.2f}")
        print(f"   Gross Loss: ${stats['gross_loss']:,.2f}")
        print(f"   Net Profit: ${stats['net_profit']:,.2f}")
        print(f"   Profit Factor: {stats['profit_factor']:.2f}")

        print(f"\n📊 AVERAGES:")
        print(f"   Average Win: ${stats['avg_win']:.2f}")
        print(f"   Average Loss: ${stats['avg_loss']:.2f}")
        print(f"   Average Bars Held: {stats['avg_bars_held']:.1f}")

        print(f"\n⚠️  RISK METRICS:")
        print(f"   Max Drawdown: ${stats['max_drawdown']:.2f}")

        # Signal distribution
        long_signals = sum(f['long_signals'] for f in all_file_stats)
        short_signals = sum(f['short_signals'] for f in all_file_stats)

        print(f"\n🎯 SIGNAL DISTRIBUTION:")
        print(f"   LONG signals: {long_signals} ({long_signals/total_signals*100:.1f}%)")
        print(f"   SHORT signals: {short_signals} ({short_signals/total_signals*100:.1f}%)")

        # Best/Worst days
        print(f"\n📅 PER-DAY BREAKDOWN:")
        print(f"   Most signals in a day: {max(f['signals'] for f in all_file_stats)}")
        print(f"   Least signals in a day: {min(f['signals'] for f in all_file_stats)}")

    else:
        print("\n⚠️  No closed trades to analyze!")

    # Save detailed results
    output_file = Path(__file__).parent / "backtest_results_full.json"
    print(f"\n💾 Saving detailed results to {output_file.name}...")

    results = {
        'summary': stats,
        'file_stats': all_file_stats,
        'closed_trades': simulator.closed_trades,
        'open_trades': simulator.open_trades,
        'config': {
            'files_processed': len(data_files),
            'total_bars': total_bars,
            'total_signals': total_signals,
            'date_range': {
                'start': data_files[0].name.split('_')[-1].split('.')[0],
                'end': data_files[-1].name.split('_')[-1].split('.')[0],
            }
        }
    }

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"✓ Results saved!")

    # Summary
    print("\n" + "=" * 80)
    if stats:
        status = "✅ PROFITABLE" if stats['net_profit'] > 0 else "❌ LOSING"
        print(f"{status} - Net P&L: ${stats['net_profit']:,.2f} | PF: {stats['profit_factor']:.2f} | WR: {stats['win_rate']*100:.1f}%")
    else:
        print("⚠️  NO COMPLETED TRADES")
    print("=" * 80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
