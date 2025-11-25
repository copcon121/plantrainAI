#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze 1 day in detail to understand signal clustering."""
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
# Pick Oct 14 (186 LONG, highest)
test_file = list(export_dir.glob("*M1_20251014.jsonl"))[0]

print(f"Analyzing: {test_file.name}")
print("=" * 80)

with open(test_file, 'r') as f:
    bars = [json.loads(line) for line in f]

module14 = Fix14MgannSwing(threshold_ticks=6)

results = []
for raw_bar in bars:
    bar_data = raw_bar.get('bar', {})
    vol_stats = bar_data.get('volume_stats', {})
    
    bar_state = {
        'high': bar_data.get('h', 0),
        'low': bar_data.get('l', 0),
        'open': bar_data.get('o', 0),
        'close': bar_data.get('c', 0),
        'volume': vol_stats.get('total_volume', 0),
        'delta': vol_stats.get('delta_close', 0),
        'delta_close': vol_stats.get('delta_close', 0),
        'tick_size': 0.1,
        'timestamp': raw_bar.get('timestamp', ''),
        'bar': bar_data,
        'ext_bos_up': bar_data.get('ext_bos_up', False),
        'ext_bos_down': bar_data.get('ext_bos_down', False),
        'ext_choch_up': bar_data.get('ext_choch_up', False),
        'ext_choch_down': bar_data.get('ext_choch_down', False),
        'ext_dir': bar_data.get('ext_dir', 0),
    }
    
    processed = module14.process_bar(bar_state)
    results.append(processed)

# Find LONG signals
long_signals = []
for i, bar in enumerate(results):
    m1_bearish = bar.get('ext_dir', 0) == -1
    early_leg = 0 < bar.get('mgann_leg_index', 0) <= 2
    fvg_bull = bar.get('bar', {}).get('has_fvg_bull', False)
    
    if m1_bearish and early_leg and fvg_bull:
        long_signals.append((i, bar))

print(f"\n📊 Total bars: {len(results)}")
print(f"🎯 LONG signals: {len(long_signals)}")
print(f"   Per bar: {len(long_signals)/len(results)*100:.1f}%")

# Analyze signal clustering
print(f"\n🔍 Signal Clustering:")

# Group consecutive signals
clusters = []
current_cluster = []
for i, (bar_idx, bar) in enumerate(long_signals):
    if not current_cluster or bar_idx == long_signals[i-1][0] + 1:
        # Consecutive
        current_cluster.append((bar_idx, bar))
    else:
        # Gap - new cluster
        clusters.append(current_cluster)
        current_cluster = [(bar_idx, bar)]

if current_cluster:
    clusters.append(current_cluster)

print(f"\nTotal clusters: {len(clusters)}")
print(f"Average cluster size: {len(long_signals)/len(clusters):.1f} signals")

# Show largest clusters
clusters_sorted = sorted(clusters, key=len, reverse=True)
print(f"\n📋 Top 10 largest signal clusters:")
print(f"{'#':<4} {'Size':<6} {'Start Bar':<12} {'Start Time':<25} {'Leg':<6} {'Duration'}")
print("-" * 80)

for i, cluster in enumerate(clusters_sorted[:10], 1):
    start_bar, start_data = cluster[0]
    end_bar, end_data = cluster[-1]
    
    size = len(cluster)
    start_time = start_data.get('timestamp', '')
    leg = start_data.get('mgann_leg_index', 0)
    duration = f"{end_bar - start_bar + 1} bars"
    
    print(f"{i:<4} {size:<6} {start_bar:<12} {start_time:<25} {leg:<6} {duration}")

# Show signal distribution by leg
leg_1_signals = sum(1 for _, bar in long_signals if bar.get('mgann_leg_index', 0) == 1)
leg_2_signals = sum(1 for _, bar in long_signals if bar.get('mgann_leg_index', 0) == 2)

print(f"\n📊 Signal Distribution by Leg:")
print(f"   Leg 1: {leg_1_signals} signals ({leg_1_signals/len(long_signals)*100:.1f}%)")
print(f"   Leg 2: {leg_2_signals} signals ({leg_2_signals/len(long_signals)*100:.1f}%)")

# Check FVG active duration
fvg_active_bars = sum(1 for r in results if r.get('bar', {}).get('has_fvg_bull', False))
print(f"\n💡 FVG Analysis:")
print(f"   FVG bull active: {fvg_active_bars} bars ({fvg_active_bars/len(results)*100:.1f}%)")
print(f"   Early leg (1-2): {sum(1 for r in results if 0 < r.get('mgann_leg_index', 0) <= 2)} bars")
print(f"   M1 bearish: {sum(1 for r in results if r.get('ext_dir', 0) == -1)} bars")

# Check if FVG stays active too long
print(f"\n⚠️  ISSUE: FVG stays active across many bars!")
print(f"   → Multiple signals in same FVG zone")
print(f"   → Need to filter: FIRST bar only when FVG appears")

# Sample consecutive signals
print(f"\n📌 Sample: First cluster (size {len(clusters[0])}):")
for i, (bar_idx, bar) in enumerate(clusters[0][:5], 1):
    print(f"\n  {i}. Bar {bar_idx} @ {bar.get('timestamp', '')}")
    print(f"     Price: {bar.get('close', 0):.2f}")
    print(f"     Leg: {bar.get('mgann_leg_index', 0)}")
    print(f"     FVG: {bar.get('bar', {}).get('has_fvg_bull', False)}")

print("\n" + "=" * 80)
print("✅ ANALYSIS COMPLETE")
print("=" * 80)
print("\n💡 RECOMMENDATION:")
print("   Add filter: Signal only on FIRST bar when condition becomes TRUE")
print("   Or: Add cooldown period (no signal for N bars after trigger)")
