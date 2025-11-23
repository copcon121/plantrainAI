# -*- coding: utf-8 -*-
"""
Test Module 14 (MGann Swing) với real data từ JSONL file.

Usage:
    python test_module14_real_data.py
"""

import sys
import io
import json
from pathlib import Path
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

# Fix encoding for Vietnamese on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def load_jsonl_data(filepath, max_bars=100):
    """Load data from JSONL file."""
    print(f"📂 Loading data from: {filepath}")
    
    bars = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= max_bars:
                break
            try:
                bar = json.loads(line.strip())
                bars.append(bar)
            except json.JSONDecodeError as e:
                print(f"⚠️  Error parsing line {i+1}: {e}")
                continue
    
    print(f"✓ Loaded {len(bars)} bars")
    return bars


def prepare_bar_for_module(bar):
    """
    Convert JSONL bar data to format expected by Module 14.
    
    The JSONL has nested structure:
    - OHLC in bar.bar.{o, h, l, c}
    - Volume/Delta in bar.bar.volume_stats
    """
    # Extract nested bar data
    bar_data = bar.get('bar', {})
    volume_stats = bar_data.get('volume_stats', {})
    
    # OHLC from bar.bar
    high = bar_data.get('h', bar.get('high', 0))
    low = bar_data.get('l', bar.get('low', 0))
    open_price = bar_data.get('o', bar.get('open', 0))
    close = bar_data.get('c', bar.get('close', 0))
    
    # Volume and delta from bar.bar.volume_stats
    volume = volume_stats.get('total_volume', bar.get('volume', 0))
    delta = volume_stats.get('cum_delta', bar.get('delta', 0))
    delta_close = volume_stats.get('delta_close', delta)
    
    # Calculate range
    bar_range = high - low if high > low else 0.1
    
    # ATR from bar.bar.atr_14
    atr = bar_data.get('atr_14', bar.get('atr_14', bar.get('atr14', 0.5)))
    
    prepared = {
        'high': high,
        'low': low,
        'open': open_price,
        'close': close,
        'volume': volume,
        'delta': delta,
        'delta_close': delta_close,
        'range': bar_range,
        'tick_size': 0.1,  # GC tick size
        'atr14': atr,
    }
    
    return prepared


def analyze_results(results):
    """Analyze and summarize module 14 results."""
    print("\n" + "=" * 70)
    print("📊 PHÂN TÍCH KẾT QUẢ")
    print("=" * 70)
    
    total_bars = len(results)
    
    # Count patterns
    ut_count = sum(1 for r in results if r['mgann_behavior']['UT'])
    sp_count = sum(1 for r in results if r['mgann_behavior']['SP'])
    pb_count = sum(1 for r in results if r['mgann_behavior']['PB'])
    ex3_count = sum(1 for r in results if r['mgann_behavior']['EX3'])
    
    # Count swing directions
    up_legs = sum(1 for r in results if r['mgann_internal_leg_dir'] == 1)
    down_legs = sum(1 for r in results if r['mgann_internal_leg_dir'] == -1)
    
    # Wave strength stats
    wave_strengths = [r['mgann_wave_strength'] for r in results]
    avg_strength = sum(wave_strengths) / len(wave_strengths) if wave_strengths else 0
    max_strength = max(wave_strengths) if wave_strengths else 0
    min_strength = min(wave_strengths) if wave_strengths else 0
    
    print(f"\n📈 TỔNG QUAN:")
    print(f"   Total bars processed: {total_bars}")
    print(f"   Up legs: {up_legs} ({up_legs/total_bars*100:.1f}%)")
    print(f"   Down legs: {down_legs} ({down_legs/total_bars*100:.1f}%)")
    
    print(f"\n🎯 PATTERN DETECTION:")
    print(f"   UpThrust (UT): {ut_count} bars ({ut_count/total_bars*100:.1f}%)")
    print(f"   Shakeout (SP): {sp_count} bars ({sp_count/total_bars*100:.1f}%)")
    print(f"   Pullback (PB): {pb_count} bars ({pb_count/total_bars*100:.1f}%)")
    print(f"   3-Push Exhaustion: {ex3_count} bars ({ex3_count/total_bars*100:.1f}%)")
    
    print(f"\n💪 WAVE STRENGTH:")
    print(f"   Average: {avg_strength:.1f}/100")
    print(f"   Maximum: {max_strength}/100")
    print(f"   Minimum: {min_strength}/100")
    
    # Find interesting bars
    print(f"\n🔍 INTERESTING BARS:")
    
    # Bars with UpThrust
    ut_bars = [(i, r) for i, r in enumerate(results) if r['mgann_behavior']['UT']]
    if ut_bars:
        print(f"\n   UpThrust detected at bars: {[i for i, _ in ut_bars[:5]]}" + 
              (f" ... (+{len(ut_bars)-5} more)" if len(ut_bars) > 5 else ""))
    
    # Bars with Shakeout
    sp_bars = [(i, r) for i, r in enumerate(results) if r['mgann_behavior']['SP']]
    if sp_bars:
        print(f"   Shakeout detected at bars: {[i for i, _ in sp_bars[:5]]}" + 
              (f" ... (+{len(sp_bars)-5} more)" if len(sp_bars) > 5 else ""))
    
    # Strongest waves
    sorted_by_strength = sorted(enumerate(results), key=lambda x: x[1]['mgann_wave_strength'], reverse=True)
    print(f"\n   Strongest waves (top 5):")
    for i, (bar_idx, result) in enumerate(sorted_by_strength[:5], 1):
        print(f"      {i}. Bar {bar_idx}: strength={result['mgann_wave_strength']}/100, " + 
              f"dir={'UP' if result['mgann_internal_leg_dir']==1 else 'DOWN'}")


def show_sample_bars(bars, results, num_samples=5):
    """Show detailed output for sample bars."""
    print("\n" + "=" * 70)
    print(f"📋 SAMPLE BARS (showing first {num_samples})")
    print("=" * 70)
    
    for i in range(min(num_samples, len(bars))):
        bar = bars[i]
        result = results[i]
        
        print(f"\nBar {i}:")
        print(f"  Price: O={bar.get('open'):.2f}, H={bar.get('high'):.2f}, " +
              f"L={bar.get('low'):.2f}, C={bar.get('close'):.2f}")
        print(f"  Volume: {bar.get('volume', 0)}, Delta: {bar.get('delta', 0)}")
        print(f"  →  Swing High: {result['mgann_internal_swing_high']}")
        print(f"  →  Swing Low: {result['mgann_internal_swing_low']}")
        print(f"  →  Direction: {result['mgann_internal_leg_dir']} " + 
              f"({'UP' if result['mgann_internal_leg_dir']==1 else 'DOWN' if result['mgann_internal_leg_dir']==-1 else 'INIT'})")
        print(f"  →  Wave Strength: {result['mgann_wave_strength']}/100")
        
        # Show patterns if any detected
        patterns_detected = [k for k, v in result['mgann_behavior'].items() if v]
        if patterns_detected:
            print(f"  →  Patterns: {', '.join(patterns_detected)}")


def main():
    print("\n" + "=" * 70)
    print("  MODULE 14 (MGann Swing) - REAL DATA TEST")
    print("=" * 70 + "\n")
    
    # Find JSONL file
    data_file = Path("deepseek_enhanced_GC 12-25_M1_20251103.jsonl")
    
    if not data_file.exists():
        print(f"❌ File not found: {data_file}")
        print("\nSearching for file...")
        # Try to find it
        possible_paths = [
            Path("deepseek_enhanced_GC 12-25_M1_20251103.jsonl"),
            Path("examples") / "deepseek_enhanced_GC 12-25_M1_20251103.jsonl",
            Path("data") / "deepseek_enhanced_GC 12-25_M1_20251103.jsonl",
        ]
        
        for path in possible_paths:
            if path.exists():
                data_file = path
                print(f"✓ Found at: {data_file}")
                break
        else:
            print("❌ Could not find data file. Please check the path.")
            return
    
    # Load data
    bars = load_jsonl_data(data_file, max_bars=100)
    
    if not bars:
        print("❌ No data loaded!")
        return
    
    # Initialize Module 14
    print(f"\n⚙️  Initializing Module 14...")
    module = Fix14MgannSwing(threshold_ticks=6)  # GC default
    print(f"✓ Module initialized (threshold: 6 ticks × 0.1 = 0.6 points)")
    
    # Process all bars
    print(f"\n🔄 Processing {len(bars)} bars...")
    results = []
    
    for i, bar in enumerate(bars):
        try:
            prepared_bar = prepare_bar_for_module(bar)
            result = module.process_bar(prepared_bar)
            results.append(result)
            
            if (i + 1) % 20 == 0:
                print(f"   Processed {i + 1}/{len(bars)} bars...")
        
        except Exception as e:
            print(f"⚠️  Error processing bar {i}: {e}")
            continue
    
    print(f"✓ Processed {len(results)} bars successfully\n")
    
    # Analyze results
    if results:
        analyze_results(results)
        show_sample_bars(bars, results, num_samples=5)
    
    # Save results to file
    output_file = "module14_results.json"
    print(f"\n💾 Saving results to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Results saved!")
    
    print("\n" + "=" * 70)
    print("✅ Test completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
