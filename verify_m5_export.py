#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify M5 CHoCH/BOS fields in exported JSONL data.

Usage:
    python verify_m5_export.py <jsonl_file>
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path

def verify_m5_export(filepath):
    """Verify M5 fields are present and working."""
    print("=" * 80)
    print(f"VERIFYING M5 EXPORT: {filepath}")
    print("=" * 80)
    
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        return False
    
    # Load data
    bars = []
    with open(filepath, 'r') as f:
        for line in f:
            bars.append(json.loads(line.strip()))
    
    print(f"\n✓ Loaded {len(bars)} M1 bars")
    
    # Check first bar structure
    print("\n" + "=" * 80)
    print("CHECKING FIRST BAR STRUCTURE")
    print("=" * 80)
    
    first_bar = bars[0]
    has_mtf = 'mtf_context' in first_bar  # ← CORRECT KEY NAME!
    has_m5 = has_mtf and 'm5' in first_bar['mtf_context']
    
    print(f"\n'mtf_context' key present: {has_mtf}")
    print(f"'m5' key present: {has_m5}")
    
    if not has_m5:
        print("\n❌ M5 data NOT found!")
        print("   Did you enable EnableM5Structure in C# indicator?")
        print("   Did you recompile and restart NinjaTrader?")
        return False
    
    # Show M5 fields
    m5 = first_bar['mtf_context']['m5']  # ← CORRECT PATH!
    print(f"\n✓ M5 fields found!")
    print(f"\nM5 fields in first bar:")
    for key, value in m5.items():
        print(f"  {key}: {value}")
    
    # Check required fields
    required_fields = ['structure_dir', 'bos_up_pulse', 'bos_down_pulse', 
                      'choch_up_pulse', 'choch_down_pulse']
    missing = [f for f in required_fields if f not in m5]
    
    if missing:
        print(f"\n⚠️  Missing fields: {missing}")
        return False
    
    print(f"\n✓ All required M5 fields present!")
    
    # Count M5 events
    print("\n" + "=" * 80)
    print("M5 CHoCH/BOS EVENT ANALYSIS")
    print("=" * 80)
    
    events = []
    for i, bar in enumerate(bars):
        mtf_context = bar.get('mtf_context', {})  # ← CORRECT KEY!
        m5 = mtf_context.get('m5', {})
        
        if m5.get('bos_up_pulse'):
            events.append((i, 'BOS_UP', m5.get('structure_dir', 0)))
        if m5.get('bos_down_pulse'):
            events.append((i, 'BOS_DOWN', m5.get('structure_dir', 0)))
        if m5.get('choch_up_pulse'):
            events.append((i, 'CHOCH_UP', m5.get('structure_dir', 0)))
        if m5.get('choch_down_pulse'):
            events.append((i, 'CHOCH_DOWN', m5.get('structure_dir', 0)))
    
    print(f"\nTotal M5 events: {len(events)}")
    print(f"  BOS_UP: {sum(1 for e in events if e[1] == 'BOS_UP')}")
    print(f"  BOS_DOWN: {sum(1 for e in events if e[1] == 'BOS_DOWN')}")
    print(f"  CHOCH_UP: {sum(1 for e in events if e[1] == 'CHOCH_UP')}")
    print(f"  CHOCH_DOWN: {sum(1 for e in events if e[1] == 'CHOCH_DOWN')}")
    
    # Show first 10 events
    print(f"\nFirst 10 M5 events:")
    print(f"{'#':<4} {'M1 Bar':<10} {'Event':<15} {'M5 Dir':<10} {'Timestamp'}")
    print("-" * 80)
    
    for i, (bar_idx, event, m5_dir) in enumerate(events[:10], 1):
        timestamp = bars[bar_idx].get('timestamp', '')
        print(f"{i:<4} {bar_idx:<10} {event:<15} {m5_dir:<10} {timestamp}")
    
    # Check if events are reasonable
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    total_events = len(events)
    expected_min = 1  # At least 1 event
    expected_max = 20  # Not more than ~20 per day
    
    if total_events < expected_min:
        print(f"\n⚠️  Too few events ({total_events})")
        print("   Expected at least 1-2 M5 CHoCH/BOS per day")
        print("   Check if M5 indicator is running correctly")
    elif total_events > expected_max:
        print(f"\n⚠️  Too many events ({total_events})")
        print(f"   Expected ~2-10 per day, got {total_events}")
        print("   M5 logic might be too sensitive")
    else:
        print(f"\n✅ Event count looks good! ({total_events} events)")
        print(f"   Expected range: {expected_min}-{expected_max}")
    
    # M5 direction distribution
    m5_dirs = [bar.get('mtf_context', {}).get('m5', {}).get('structure_dir', 0) for bar in bars]
    dir_up = sum(1 for d in m5_dirs if d == 1)
    dir_down = sum(1 for d in m5_dirs if d == -1)
    dir_none = sum(1 for d in m5_dirs if d == 0)
    
    print(f"\nM5 Direction Distribution:")
    print(f"  Uptrend: {dir_up} bars ({dir_up/len(bars)*100:.1f}%)")
    print(f"  Downtrend: {dir_down} bars ({dir_down/len(bars)*100:.1f}%)")
    print(f"  No trend: {dir_none} bars ({dir_none/len(bars)*100:.1f}%)")
    
    if dir_none > len(bars) * 0.5:
        print(f"\n⚠️  Warning: {dir_none/len(bars)*100:.1f}% bars have no M5 direction")
        print("   This is unusual - check M5 indicator initialization")
    
    print("\n" + "=" * 80)
    print("✅ M5 VERIFICATION COMPLETE!")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        # Default file
        filepath = "deepseek_enhanced_GC 12-25_M1_20251103.jsonl"
        print(f"No file specified, using default: {filepath}")
    else:
        filepath = sys.argv[1]
    
    success = verify_m5_export(filepath)
    sys.exit(0 if success else 1)
