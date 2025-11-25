#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Label Rules v3 with multiple days of data.

Processes all JSONL files in the export directory.
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from collections import defaultdict


def check_long_signal(bar):
    """LONG: Bullish pullback in early leg of M5 downtrend."""
    mtf_context = bar.get('mtf_context', {})
    m5 = mtf_context.get('m5', {})
    bar_data = bar.get('bar', {})
    
    # All conditions
    m5_bearish = m5.get('choch_down_pulse', False) or m5.get('structure_dir', 0) == -1
    mgann_leg = bar.get('mgann_leg_index', 0)
    early_leg = 0 < mgann_leg <= 2
    pb_strength_ok = bar.get('pb_wave_strength_ok', False)
    fvg_bullish = (
        (bar_data.get('fvg_detected', False) and bar_data.get('fvg_type') == 'bullish') or
        bar_data.get('has_fvg_bull', False)
    )
    
    return m5_bearish and early_leg and pb_strength_ok and fvg_bullish


def check_short_signal(bar):
    """SHORT: Bearish pullback in early leg of M5 uptrend."""
    mtf_context = bar.get('mtf_context', {})
    m5 = mtf_context.get('m5', {})
    bar_data = bar.get('bar', {})
    
    # All conditions
    m5_bullish = m5.get('choch_up_pulse', False) or m5.get('structure_dir', 0) == 1
    mgann_leg = bar.get('mgann_leg_index', 0)
    early_leg = 0 < mgann_leg <= 2
    pb_strength_ok = bar.get('pb_wave_strength_ok', False)
    fvg_bearish = (
        (bar_data.get('fvg_detected', False) and bar_data.get('fvg_type') == 'bearish') or
        bar_data.get('has_fvg_bear', False)
    )
    
    return m5_bullish and early_leg and pb_strength_ok and fvg_bearish


def process_jsonl_file(filepath):
    """Process one JSONL file and return bars with Module 14 processing."""
    from processor.modules.fix14_mgann_swing import Fix14MgannSwing  # Correct class name!
    
    # Load raw data
        volume_stats = bar_data.get('volume_stats', {})
        mtf_context = raw_bar.get('mtf_context', {})
        
        bar_state = {
            'high': bar_data.get('h', 0),
            'low': bar_data.get('l', 0),
            'open': bar_data.get('o', 0),
            'close': bar_data.get('c', 0),
            'volume': volume_stats.get('total_volume', 0),
            'delta': volume_stats.get('delta_close', 0),
            'delta_close': volume_stats.get('delta_close', 0),
            'tick_size': 0.1,
            'atr14': raw_bar.get('atr_14', 0),
            'timestamp': raw_bar.get('timestamp', ''),
            'mtf_context': mtf_context,
            'bar': bar_data,
        }
        
        # Process through Module 14
        processed = module14.process_bar(bar_state)
        results.append(processed)
    
    return results


def main():
    print("=" * 80)
    print("TESTING LABEL RULES V3 - MULTI-DAY DATASET")
    print("=" * 80)
    
    # Find all M1 JSONL files (not M5!)
    export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
    jsonl_files = sorted(export_dir.glob("*M1*.jsonl"))  # M1 files only!
    
    print(f"\n📂 Found {len(jsonl_files)} data files:")
    for f in jsonl_files:
        print(f"   - {f.name}")
    
    # Process all files
    all_long_signals = []
    all_short_signals = []
    total_bars = 0
    
    stats_by_file = {}
    
    print("\n🔄 Processing files...")
    for jsonl_file in jsonl_files:
        print(f"\n   Processing {jsonl_file.name}...")
        
        # Process file
        bars = process_jsonl_file(jsonl_file)
        total_bars += len(bars)
        
        # Apply rules
        long_signals = []
        short_signals = []
        
        for i, bar in enumerate(bars):
            if check_long_signal(bar):
                long_signals.append((i, bar, jsonl_file.name))
                all_long_signals.append((i, bar, jsonl_file.name))
            
            if check_short_signal(bar):
                short_signals.append((i, bar, jsonl_file.name))
                all_short_signals.append((i, bar, jsonl_file.name))
        
        # Store stats
        stats_by_file[jsonl_file.name] = {
            'bars': len(bars),
            'long': len(long_signals),
            'short': len(short_signals),
        }
        
        print(f"      → {len(bars)} bars, {len(long_signals)} LONG, {len(short_signals)} SHORT")
    
    # Overall results
    print("\n" + "=" * 80)
    print("📊 OVERALL RESULTS")
    print("=" * 80)
    print(f"\nTotal bars processed: {total_bars}")
    print(f"Total files: {len(jsonl_files)}")
    print(f"Average bars per day: {total_bars / len(jsonl_files):.0f}")
    
    print(f"\n🎯 SIGNALS:")
    print(f"  LONG signals: {len(all_long_signals)}")
    print(f"  SHORT signals: {len(all_short_signals)}")
    print(f"  Total signals: {len(all_long_signals) + len(all_short_signals)}")
    print(f"  Signals per day: {(len(all_long_signals) + len(all_short_signals)) / len(jsonl_files):.1f}")
    
    # Show signals by file
    print("\n" + "=" * 80)
    print("📅 SIGNALS BY FILE")
    print("=" * 80)
    print(f"\n{'File':<50} {'Bars':<8} {'LONG':<6} {'SHORT':<6} {'Total'}")
    print("-" * 80)
    for filename, stats in stats_by_file.items():
        total_sigs = stats['long'] + stats['short']
        print(f"{filename:<50} {stats['bars']:<8} {stats['long']:<6} {stats['short']:<6} {total_sigs}")
    
    # Show sample signals
    if all_long_signals:
        print("\n" + "=" * 80)
        print(f"SAMPLE LONG SIGNALS (showing first 5 of {len(all_long_signals)})")
        print("=" * 80)
        
        for idx, (bar_idx, bar, filename) in enumerate(all_long_signals[:5], 1):
            mtf = bar.get('mtf_context', {}).get('m5', {})
            bar_data = bar.get('bar', {})
            
            print(f"\n{idx}. {filename} - Bar {bar_idx}")
            print(f"   Time: {bar.get('timestamp', 'N/A')}")
            print(f"   Price: {bar.get('close', 0):.2f}")
            print(f"   M5: dir={mtf.get('structure_dir', 0)}, CHoCH_down={mtf.get('choch_down_pulse', False)}")
            print(f"   M1: leg={bar.get('mgann_leg_index', 0)}, pb_ok={bar.get('pb_wave_strength_ok', False)}")
            print(f"   FVG: bull={bar_data.get('has_fvg_bull', False)}")
    
    if all_short_signals:
        print("\n" + "=" * 80)
        print(f"SAMPLE SHORT SIGNALS (showing first 5 of {len(all_short_signals)})")
        print("=" * 80)
        
        for idx, (bar_idx, bar, filename) in enumerate(all_short_signals[:5], 1):
            mtf = bar.get('mtf_context', {}).get('m5', {})
            bar_data = bar.get('bar', {})
            
            print(f"\n{idx}. {filename} - Bar {bar_idx}")
            print(f"   Time: {bar.get('timestamp', 'N/A')}")
            print(f"   Price: {bar.get('close', 0):.2f}")
            print(f"   M5: dir={mtf.get('structure_dir', 0)}, CHoCH_up={mtf.get('choch_up_pulse', False)}")
            print(f"   M1: leg={bar.get('mgann_leg_index', 0)}, pb_ok={bar.get('pb_wave_strength_ok', False)}")
            print(f"   FVG: bear={bar_data.get('has_fvg_bear', False)}")
    
    print("\n" + "=" * 80)
    print("✅ MULTI-DAY TEST COMPLETE!")
    print("=" * 80)


if __name__ == '__main__':
    main()
