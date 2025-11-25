#!/usr/bin/env python3
"""
Test Module 15 (M5 Context) with real M1 data.

Usage:
    python test_module15_m5.py
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from processor.modules.fix14_mgann_swing import Fix14MgannSwing
from processor.modules.fix15_m5_context import Fix15M5Context


def load_jsonl(filepath, max_bars=None):
    """Load JSONL data."""
    bars = []
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            if max_bars and i >= max_bars:
                break
            bars.append(json.loads(line.strip()))
    return bars


def prepare_bar(bar):
    """Prepare bar for modules."""
    bar_data = bar.get('bar', {})
    volume_stats = bar_data.get('volume_stats', {})
    
    return {
        'open': bar_data.get('o', 0),
        'high': bar_data.get('h', 0),
        'low': bar_data.get('l', 0),
        'close': bar_data.get('c', 0),
        'volume': volume_stats.get('total_volume', 0),
        'delta': volume_stats.get('delta_close', 0),
        'timestamp': bar.get('timestamp', ''),
        'ext_bos_up': bar_data.get('ext_bos_up', False),
        'ext_bos_down': bar_data.get('ext_bos_down', False),
        'ext_choch_up': bar_data.get('ext_choch_up', False),
        'ext_choch_down': bar_data.get('ext_choch_down', False),
        'ext_dir': bar_data.get('ext_dir', 0),
    }


def main():
    print("=" * 80)
    print("MODULE 15 (M5 Context) - TEST")
    print("=" * 80)
    
    # Load data
    filepath = Path("deepseek_enhanced_GC 12-25_M1_20251103.jsonl")
    print(f"\nLoading data from: {filepath}")
    raw_bars = load_jsonl(filepath)
    print(f"✓ Loaded {len(raw_bars)} M1 bars")
    
    # Initialize modules
    print("\nInitializing modules...")
    module14 = Fix14MgannSwing(threshold_ticks=6)
    module15 = Fix15M5Context()
    print("✓ Modules initialized")
    
    # Process bars
    print(f"\nProcessing {len(raw_bars)} M1 bars...")
    results = []
    
    for i, raw_bar in enumerate(raw_bars):
        bar_state = prepare_bar(raw_bar)
        bar_state = module14.process_bar(bar_state, history=results)
        bar_state = module15.process_bar(bar_state, history=results)
        results.append(bar_state)
        
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(raw_bars)} bars...")
    
    print(f"✓ Processed {len(results)} bars")
    
    # Analyze M5 signals
    print("\n" + "=" * 80)
    print("M5 CHoCH/BOS ANALYSIS")
    print("=" * 80)
    
    m5_bos_up = sum(1 for r in results if r.get('m5_ext_bos_up'))
    m5_bos_down = sum(1 for r in results if r.get('m5_ext_bos_down'))
    m5_choch_up = sum(1 for r in results if r.get('m5_ext_choch_up'))
    m5_choch_down = sum(1 for r in results if r.get('m5_ext_choch_down'))
    
    m5_dir_up = sum(1 for r in results if r.get('m5_ext_dir') == 1)
    m5_dir_down = sum(1 for r in results if r.get('m5_ext_dir') == -1)
    m5_dir_none = sum(1 for r in results if r.get('m5_ext_dir') == 0)
    
    print(f"\nM5 BOS Events:")
    print(f"  BOS_UP: {m5_bos_up}")
    print(f"  BOS_DOWN: {m5_bos_down}")
    
    print(f"\nM5 CHoCH Events:")
    print(f"  CHoCH_UP: {m5_choch_up}")
    print(f"  CHoCH_DOWN: {m5_choch_down}")
    
    print(f"\nM5 Direction Distribution:")
    print(f"  Uptrend: {m5_dir_up} bars ({m5_dir_up/len(results)*100:.1f}%)")
    print(f"  Downtrend: {m5_dir_down} bars ({m5_dir_down/len(results)*100:.1f}%)")
    print(f"  No trend: {m5_dir_none} bars ({m5_dir_none/len(results)*100:.1f}%)")
    
    # Show events
    print("\n" + "=" * 80)
    print("M5 EVENT DETAILS (First 10)")
    print("=" * 80)
    
    events = []
    for i, r in enumerate(results):
        if r.get('m5_ext_bos_up'):
            events.append((i, 'BOS_UP', r.get('m5_ext_dir')))
        if r.get('m5_ext_bos_down'):
            events.append((i, 'BOS_DOWN', r.get('m5_ext_dir')))
        if r.get('m5_ext_choch_up'):
            events.append((i, 'CHOCH_UP', r.get('m5_ext_dir')))
        if r.get('m5_ext_choch_down'):
            events.append((i, 'CHOCH_DOWN', r.get('m5_ext_dir')))
    
    for i, (bar_idx, event, m5_dir) in enumerate(events[:10]):
        print(f"{i+1}. Bar {bar_idx}: {event} → m5_dir={m5_dir}")
    
    # Save
    output_file = "module15_m5_results.json"
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print("✓ Saved!")
    
    print("\n" + "=" * 80)
    print("✅ Test complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
