#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Label Rules v3 with real data.

Usage:
    python test_label_rules_v3.py
"""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path


def check_long_signal(bar):
    """
    LONG: Bullish pullback in early leg of M5 downtrend.
    
    Setup: M5 bearish CHoCH → M1 pullback up → Early leg ≤2 → Strong wave → FVG entry
    """
    # Extract data
    mtf_context = bar.get('mtf_context', {})
    m5 = mtf_context.get('m5', {})
    bar_data = bar.get('bar', {})
    
    # Condition 1: M5 bearish context
    m5_bearish = (
        m5.get('choch_down_pulse', False) or  # Fresh CHoCH down
        m5.get('structure_dir', 0) == -1       # Already bearish
    )
    
    # Condition 2: Early M1 leg
    mgann_leg = bar.get('mgann_leg_index', 0)
    early_leg = 0 < mgann_leg <= 2
    
    # Condition 3: Pullback strength validated
    pb_strength_ok = bar.get('pb_wave_strength_ok', False)
    
    # Condition 4: Bullish FVG (pullback entry zone)
    fvg_bullish = (
        (bar_data.get('fvg_detected', False) and 
         bar_data.get('fvg_type') == 'bullish') or
        bar_data.get('has_fvg_bull', False)
    )
    
    # ALL conditions must be TRUE
    return m5_bearish and early_leg and pb_strength_ok and fvg_bullish


def check_short_signal(bar):
    """
    SHORT: Bearish pullback in early leg of M5 uptrend.
    
    Setup: M5 bullish CHoCH → M1 pullback down → Early leg ≤2 → Strong wave → FVG entry
    """
    # Extract data
    mtf_context = bar.get('mtf_context', {})
    m5 = mtf_context.get('m5', {})
    bar_data = bar.get('bar', {})
    
    # Condition 1: M5 bullish context
    m5_bullish = (
        m5.get('choch_up_pulse', False) or  # Fresh CHoCH up
        m5.get('structure_dir', 0) == 1      # Already bullish
    )
    
    # Condition 2: Early M1 leg
    mgann_leg = bar.get('mgann_leg_index', 0)
    early_leg = 0 < mgann_leg <= 2
    
    # Condition 3: Pullback strength validated
    pb_strength_ok = bar.get('pb_wave_strength_ok', False)
    
    # Condition 4: Bearish FVG (pullback entry zone)
    fvg_bearish = (
        (bar_data.get('fvg_detected', False) and 
         bar_data.get('fvg_type') == 'bearish') or
        bar_data.get('has_fvg_bear', False)
    )
    
    # ALL conditions must be TRUE
    return m5_bullish and early_leg and pb_strength_ok and fvg_bearish


def main():
    print("=" * 80)
    print("TESTING LABEL RULES V3")
    print("=" * 80)
    
    # Load data
    filepath = "module14_results.json"
    print(f"\nLoading data from: {filepath}")
    
    with open(filepath, 'r') as f:
        bars = json.load(f)
    
    print(f"✓ Loaded {len(bars)} bars")
    
    # Test rules
    print("\n" + "=" * 80)
    print("APPLYING LABEL RULES V3")
    print("=" * 80)
    
    long_signals = []
    short_signals = []
    
    for i, bar in enumerate(bars):
        if check_long_signal(bar):
            long_signals.append((i, bar))
        
        if check_short_signal(bar):
            short_signals.append((i, bar))
    
    # Results
    print(f"\n📊 RESULTS:")
    print(f"  LONG signals: {len(long_signals)}")
    print(f"  SHORT signals: {len(short_signals)}")
    print(f"  Total signals: {len(long_signals) + len(short_signals)}")
    
    # Show LONG signals
    if long_signals:
        print("\n" + "=" * 80)
        print(f"LONG SIGNALS ({len(long_signals)} total)")
        print("=" * 80)
        
        for idx, (bar_idx, bar) in enumerate(long_signals[:10], 1):
            mtf = bar.get('mtf_context', {}).get('m5', {})
            bar_data = bar.get('bar', {})
            
            print(f"\n{idx}. Bar {bar_idx} @ {bar.get('timestamp', 'N/A')}")
            print(f"   Price: {bar.get('close', 0):.2f}")
            print(f"   M5 dir: {mtf.get('structure_dir', 0)}")
            print(f"   M5 CHoCH down: {mtf.get('choch_down_pulse', False)}")
            print(f"   MGann leg: {bar.get('mgann_leg_index', 0)}")
            print(f"   Wave strength OK: {bar.get('pb_wave_strength_ok', False)}")
            print(f"   FVG bullish: {bar_data.get('has_fvg_bull', False)}")
            
            if bar_data.get('fvg_top') and bar_data.get('fvg_bottom'):
                print(f"   FVG zone: {bar_data.get('fvg_bottom', 0):.2f} - {bar_data.get('fvg_top', 0):.2f}")
    
    # Show SHORT signals
    if short_signals:
        print("\n" + "=" * 80)
        print(f"SHORT SIGNALS ({len(short_signals)} total)")
        print("=" * 80)
        
        for idx, (bar_idx, bar) in enumerate(short_signals[:10], 1):
            mtf = bar.get('mtf_context', {}).get('m5', {})
            bar_data = bar.get('bar', {})
            
            print(f"\n{idx}. Bar {bar_idx} @ {bar.get('timestamp', 'N/A')}")
            print(f"   Price: {bar.get('close', 0):.2f}")
            print(f"   M5 dir: {mtf.get('structure_dir', 0)}")
            print(f"   M5 CHoCH up: {mtf.get('choch_up_pulse', False)}")
            print(f"   MGann leg: {bar.get('mgann_leg_index', 0)}")
            print(f"   Wave strength OK: {bar.get('pb_wave_strength_ok', False)}")
            print(f"   FVG bearish: {bar_data.get('has_fvg_bear', False)}")
            
            if bar_data.get('fvg_top') and bar_data.get('fvg_bottom'):
                print(f"   FVG zone: {bar_data.get('fvg_bottom', 0):.2f} - {bar_data.get('fvg_top', 0):.2f}")
    
    # Condition breakdown
    print("\n" + "=" * 80)
    print("CONDITION BREAKDOWN")
    print("=" * 80)
    
    # Count each condition separately
    m5_bearish_count = sum(1 for b in bars if b.get('mtf_context', {}).get('m5', {}).get('structure_dir', 0) == -1)
    m5_bullish_count = sum(1 for b in bars if b.get('mtf_context', {}).get('m5', {}).get('structure_dir', 0) == 1)
    early_leg_count = sum(1 for b in bars if 0 < b.get('mgann_leg_index', 0) <= 2)
    pb_strength_count = sum(1 for b in bars if b.get('pb_wave_strength_ok', False))
    fvg_bull_count = sum(1 for b in bars if b.get('bar', {}).get('has_fvg_bull', False))
    fvg_bear_count = sum(1 for b in bars if b.get('bar', {}).get('has_fvg_bear', False))
    
    print(f"\nM5 bearish: {m5_bearish_count} bars ({m5_bearish_count/len(bars)*100:.1f}%)")
    print(f"M5 bullish: {m5_bullish_count} bars ({m5_bullish_count/len(bars)*100:.1f}%)")
    print(f"Early leg (1-2): {early_leg_count} bars ({early_leg_count/len(bars)*100:.1f}%)")
    print(f"Wave strength OK: {pb_strength_count} bars ({pb_strength_count/len(bars)*100:.1f}%)")
    print(f"FVG bullish active: {fvg_bull_count} bars ({fvg_bull_count/len(bars)*100:.1f}%)")
    print(f"FVG bearish active: {fvg_bear_count} bars ({fvg_bear_count/len(bars)*100:.1f}%)")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE!")
    print("=" * 80)


if __name__ == '__main__':
    main()
