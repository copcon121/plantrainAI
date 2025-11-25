#!/usr/bin/env python3
"""
Test Strategy V1 with available data (module14_results.json)

This script tests fix16_strategy_v1.py using the processed data
from module14_results.json instead of requiring raw JSONL exports.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from processor.modules.fix16_strategy_v1 import Fix16StrategyV1


def main():
    print("\n" + "=" * 70)
    print("  STRATEGY V1 TEST - Using Available Data")
    print("=" * 70 + "\n")

    # Load processed data from module14_results.json
    data_file = Path(__file__).parent / "module14_results.json"

    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        return 1

    print(f"📂 Loading data from: {data_file.name}")

    with open(data_file, 'r') as f:
        bars = json.load(f)

    print(f"✓ Loaded {len(bars)} bars\n")

    # Initialize Strategy V1
    print("⚙️  Initializing Strategy V1...")
    strategy = Fix16StrategyV1(tick_size=0.1, risk_reward_ratio=3.0, sl_buffer_ticks=2)
    print("✓ Strategy initialized\n")

    # Process bars and collect signals
    print(f"🔄 Processing {len(bars)} bars...")

    signals = []
    long_signals = []
    short_signals = []

    for i, bar in enumerate(bars):
        try:
            # Process bar through strategy
            result = strategy.process_bar(bar)

            # Check if signal was generated
            if 'signal' in result:
                signal = result['signal']
                signals.append(signal)

                if signal['direction'] == 'LONG':
                    long_signals.append(signal)
                elif signal['direction'] == 'SHORT':
                    short_signals.append(signal)

            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"   Processed {i + 1}/{len(bars)} bars... (Signals: {len(signals)})")

        except Exception as e:
            print(f"⚠️  Error processing bar {i}: {e}")
            continue

    print(f"✓ Processing complete!\n")

    # Display results
    print("=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    print(f"\nTotal bars processed: {len(bars)}")
    print(f"Total signals generated: {len(signals)}")
    print(f"  LONG signals: {len(long_signals)} ({len(long_signals)/max(1,len(signals))*100:.1f}%)")
    print(f"  SHORT signals: {len(short_signals)} ({len(short_signals)/max(1,len(signals))*100:.1f}%)")

    # Show sample signals
    if signals:
        print(f"\n📋 SAMPLE SIGNALS (first 5):")
        print("-" * 70)

        for i, sig in enumerate(signals[:5], 1):
            trade = sig.get('trade', {})
            print(f"\n{i}. {sig['direction']} Signal at Bar {sig['bar_index']}")
            print(f"   Timestamp: {sig['timestamp']}")
            print(f"   Leg: {sig['leg']}")
            print(f"   FVG: {'NEW' if sig['fvg_new'] else 'RETEST'}")
            print(f"   FVG Zone: {sig['fvg_zone']['bottom']:.2f} - {sig['fvg_zone']['top']:.2f}")
            print(f"   Entry: {trade['entry']:.2f}")
            print(f"   SL: {trade['sl']:.2f}")
            print(f"   TP: {trade['tp']:.2f}")
            print(f"   Risk: {trade['risk']:.2f}")
            print(f"   Reward: {trade['reward']:.2f}")
            print(f"   R:R: 1:{trade['rr_ratio']:.1f}")
    else:
        print("\n⚠️  No signals were generated!")
        print("\nPossible reasons:")
        print("  1. Strategy conditions are too strict")
        print("  2. Data doesn't contain required fields (mgann_leg_index, fvg_detected, etc.)")
        print("  3. No valid setups in this dataset")

        # Check first bar to see what fields are available
        if bars:
            print("\n📋 Sample bar fields (first bar):")
            sample_keys = list(bars[0].keys())
            print(f"   Available fields: {', '.join(sample_keys[:10])}")
            if len(sample_keys) > 10:
                print(f"   ... and {len(sample_keys) - 10} more")

    # Save signals to file
    if signals:
        output_file = Path(__file__).parent / "strategy_v1_signals.json"
        print(f"\n💾 Saving signals to {output_file.name}...")

        with open(output_file, 'w') as f:
            json.dump(signals, f, indent=2)

        print(f"✓ Signals saved!")

    print("\n" + "=" * 70)
    print("✅ Test completed successfully!")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
