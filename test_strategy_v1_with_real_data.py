#!/usr/bin/env python3
"""
Test Strategy V1 with REAL JSONL data from main branch

This tests fix16_strategy_v1.py with actual NinjaTrader exports
that have ALL required fields: fvg_detected, fvg_type, last_swing_high, etc.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix16_strategy_v1 import Fix16StrategyV1


def prepare_bar(raw_bar):
    """
    Convert JSONL bar to format expected by modules.

    Data has both root-level and nested 'bar' fields.
    Strategy needs flattened structure.
    """
    # Get nested bar data
    bar_data = raw_bar.get('bar', {})

    # Flatten to root level
    prepared = {
        # OHLC
        'high': raw_bar.get('high', 0),
        'low': raw_bar.get('low', 0),
        'open': raw_bar.get('open', 0),
        'close': raw_bar.get('close', 0),

        # Volume (from nested if available)
        'volume': bar_data.get('volume_stats', {}).get('total_volume', raw_bar.get('volume', 0)),
        'delta': bar_data.get('volume_stats', {}).get('delta_close', raw_bar.get('delta', 0)),

        # Technical
        'atr14': raw_bar.get('atr_14', 0),
        'range': raw_bar.get('high', 0) - raw_bar.get('low', 0),
        'tick_size': 0.1,

        # Timestamp
        'timestamp': raw_bar.get('timestamp', ''),
        'bar_index': raw_bar.get('bar_index', 0),

        # External structure (from nested bar.*)
        'ext_dir': bar_data.get('ext_dir', raw_bar.get('current_trend', 0)),
        'ext_choch_up': bar_data.get('ext_choch_up', False),
        'ext_choch_down': bar_data.get('ext_choch_down', False),
        'ext_bos_up': bar_data.get('ext_bos_up', False),
        'ext_bos_down': bar_data.get('ext_bos_down', False),

        # FVG fields (ROOT LEVEL in export!)
        'fvg_detected': raw_bar.get('fvg_detected', False),
        'fvg_type': raw_bar.get('fvg_type'),
        'fvg_top': raw_bar.get('fvg_top'),
        'fvg_bottom': raw_bar.get('fvg_bottom'),

        # Swing points (ROOT LEVEL)
        'last_swing_high': raw_bar.get('last_swing_high'),
        'last_swing_low': raw_bar.get('last_swing_low'),

        # Will be added by Module 14
        # 'mgann_leg_index': ...,
        # 'pb_wave_strength_ok': ...,
    }

    return prepared


def main():
    print("\n" + "=" * 70)
    print("  STRATEGY V1 TEST - Real NinjaTrader Data")
    print("=" * 70 + "\n")

    # Use JSONL data from main branch
    data_files = list(Path(__file__).parent.glob("deepseek_enhanced_*.jsonl"))

    if not data_files:
        print("❌ No JSONL data files found!")
        print("   Expected: deepseek_enhanced_GC 12-25_M1_*.jsonl")
        return 1

    # Use first file
    data_file = data_files[0]
    print(f"📂 Using data file: {data_file.name}")
    print(f"   Size: {data_file.stat().st_size / 1024 / 1024:.1f} MB\n")

    # Load bars (limit to 500 for quick test)
    MAX_BARS = 500
    print(f"⚙️  Loading first {MAX_BARS} bars...")

    bars = []
    with open(data_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= MAX_BARS:
                break
            try:
                bar = json.loads(line.strip())
                bars.append(bar)
            except json.JSONDecodeError as e:
                print(f"⚠️  Error parsing line {i}: {e}")
                continue

    print(f"✓ Loaded {len(bars)} bars\n")

    # Check first bar structure
    print("📋 Sample bar structure (first bar):")
    sample = bars[0]
    print(f"   Root fields: {len(sample.keys())} fields")
    print(f"   FVG fields present: fvg_detected={sample.get('fvg_detected')}, fvg_type={sample.get('fvg_type')}")
    print(f"   Swing points: last_swing_high={sample.get('last_swing_high')}, last_swing_low={sample.get('last_swing_low')}")
    print()

    # Initialize modules
    print("⚙️  Initializing modules...")
    mgann = Fix14MgannSwing(threshold_ticks=6)  # GC default
    strategy = Fix16StrategyV1(tick_size=0.1, risk_reward_ratio=3.0, sl_buffer_ticks=2)
    print("✓ Modules initialized\n")

    # Process bars
    print(f"🔄 Processing {len(bars)} bars through pipeline...")

    signals = []
    long_signals = []
    short_signals = []

    for i, raw_bar in enumerate(bars):
        try:
            # Prepare bar
            bar = prepare_bar(raw_bar)

            # Module 14: MGann Swing
            bar = mgann.process_bar(bar)

            # Strategy V1
            bar = strategy.process_bar(bar)

            # Check for signal
            if 'signal' in bar:
                signal = bar['signal']
                signals.append(signal)

                if signal['direction'] == 'LONG':
                    long_signals.append(signal)
                elif signal['direction'] == 'SHORT':
                    short_signals.append(signal)

                # Print signal inline
                print(f"   🎯 Signal #{len(signals)}: {signal['direction']} at bar {i} (leg {signal['leg']})")

            # Progress
            if (i + 1) % 100 == 0:
                print(f"   Processed {i + 1}/{len(bars)} bars... (Signals: {len(signals)})")

        except Exception as e:
            print(f"⚠️  Error processing bar {i}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"✓ Processing complete!\n")

    # Display results
    print("=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    print(f"\nTotal bars processed: {len(bars)}")
    print(f"Total signals generated: {len(signals)}")

    if signals:
        print(f"  LONG signals: {len(long_signals)} ({len(long_signals)/len(signals)*100:.1f}%)")
        print(f"  SHORT signals: {len(short_signals)} ({len(short_signals)/len(signals)*100:.1f}%)")

        print(f"\n📋 DETAILED SIGNALS:")
        print("-" * 70)

        for i, sig in enumerate(signals, 1):
            trade = sig.get('trade', {})
            print(f"\n{i}. {sig['direction']} Signal")
            print(f"   Bar Index: {sig['bar_index']}")
            print(f"   Timestamp: {sig['timestamp']}")
            print(f"   Leg: {sig['leg']}")
            print(f"   FVG: {'NEW' if sig['fvg_new'] else 'RETEST'}")
            print(f"   FVG Zone: {sig['fvg_zone']['bottom']:.2f} - {sig['fvg_zone']['top']:.2f}")
            print(f"   Trade:")
            print(f"     Entry: ${trade['entry']:.2f}")
            print(f"     SL:    ${trade['sl']:.2f}")
            print(f"     TP:    ${trade['tp']:.2f}")
            print(f"     Risk:  ${trade['risk']:.2f}")
            print(f"     R:R:   1:{trade['rr_ratio']:.1f}")
    else:
        print("\n⚠️  No signals generated!")
        print("\nChecking why...")

        # Debug: Check conditions
        has_choch_down = sum(1 for b in bars if prepare_bar(b).get('ext_choch_down'))
        has_choch_up = sum(1 for b in bars if prepare_bar(b).get('ext_choch_up'))
        has_fvg = sum(1 for b in bars if prepare_bar(b).get('fvg_detected'))

        print(f"  CHoCH down bars: {has_choch_down}")
        print(f"  CHoCH up bars: {has_choch_up}")
        print(f"  FVG detected bars: {has_fvg}")

    # Save signals
    if signals:
        output_file = Path(__file__).parent / "strategy_v1_real_signals.json"
        print(f"\n💾 Saving signals to {output_file.name}...")

        with open(output_file, 'w') as f:
            json.dump(signals, f, indent=2)

        print(f"✓ Signals saved!")

    print("\n" + "=" * 70)
    print("✅ Test completed!")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
