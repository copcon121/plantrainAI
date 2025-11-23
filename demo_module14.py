# -*- coding: utf-8 -*-
"""
Demo script để test Module 14 (MGann Swing) với data thực tế.

Chạy script này để xem module hoạt động như thế nào:
    python demo_module14.py
"""

import sys
import io
from processor.modules.fix14_mgann_swing import Fix14MgannSwing
import json

# Fix encoding for Vietnamese characters on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def demo_basic_usage():
    """Demo cơ bản: khởi tạo và xử lý một bar."""
    print("=" * 60)
    print("DEMO 1: Sử dụng cơ bản")
    print("=" * 60)
    
    # Khởi tạo module với threshold 6 ticks
    module = Fix14MgannSwing(threshold_ticks=6)
    print(f"✓ Module initialized với threshold_ticks=6")
    print(f"  (6 ticks × 0.1 tick_size = 0.6 points movement required)\n")
    
    # Tạo bar đầu tiên
    bar1 = {
        "high": 100.5,
        "low": 99.5,
        "open": 100.0,
        "close": 100.3,
        "volume": 1000,
        "delta": 50,
        "delta_close": 50,
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    print("Bar 1 input:")
    print(f"  High: {bar1['high']}, Low: {bar1['low']}")
    print(f"  Open: {bar1['open']}, Close: {bar1['close']}")
    
    # Process bar
    result = module.process_bar(bar1)
    
    print("\nBar 1 output:")
    print(f"  Swing High: {result['mgann_internal_swing_high']}")
    print(f"  Swing Low: {result['mgann_internal_swing_low']}")
    print(f"  Leg Direction: {result['mgann_internal_leg_dir']} (0=init, 1=up, -1=down)")
    print(f"  Wave Strength: {result['mgann_wave_strength']}/100")
    print(f"  Patterns: {result['mgann_behavior']}")
    print()


def demo_swing_detection():
    """Demo phát hiện swing movements."""
    print("=" * 60)
    print("DEMO 2: Phát hiện Swing Movements")
    print("=" * 60)
    
    module = Fix14MgannSwing(threshold_ticks=6)
    
    # Tạo chuỗi bars tạo swing pattern
    bars = [
        {
            "high": 100.0, "low": 99.0, "open": 99.5, "close": 99.8,
            "volume": 1000, "delta": 50, "delta_close": 50,
            "range": 1.0, "tick_size": 0.1, "atr14": 0.5,
        },
        {
            "high": 99.8, "low": 99.2, "open": 99.6, "close": 99.4,
            "volume": 900, "delta": -30, "delta_close": -30,
            "range": 0.6, "tick_size": 0.1, "atr14": 0.5,
        },
        {
            "high": 100.2, "low": 99.5, "open": 99.6, "close": 100.0,
            "volume": 1200, "delta": 80, "delta_close": 80,
            "range": 0.7, "tick_size": 0.1, "atr14": 0.5,
        },
    ]
    
    for i, bar in enumerate(bars, 1):
        result = module.process_bar(bar)
        print(f"\nBar {i}:")
        print(f"  Price: H={bar['high']}, L={bar['low']}, C={bar['close']}")
        print(f"  → Swing High: {result['mgann_internal_swing_high']}")
        print(f"  → Swing Low: {result['mgann_internal_swing_low']}")
        print(f"  → Direction: {result['mgann_internal_leg_dir']}")
        
        if result['mgann_internal_leg_dir'] != 0:
            direction_text = "UPLEG ↑" if result['mgann_internal_leg_dir'] == 1 else "DOWNLEG ↓"
            print(f"  → Status: {direction_text}")
    print()


def demo_pattern_detection():
    """Demo phát hiện patterns (UpThrust, Shakeout, Pullback)."""
    print("=" * 60)
    print("DEMO 3: Phát hiện Patterns")
    print("=" * 60)
    
    module = Fix14MgannSwing(threshold_ticks=6)
    
    # Initialize first
    init_bar = {
        "high": 100.0, "low": 99.0, "open": 99.5, "close": 99.8,
        "volume": 1000, "delta": 50, "delta_close": 50,
        "range": 1.0, "tick_size": 0.1, "atr14": 0.5,
    }
    module.process_bar(init_bar)
    
    # Test UpThrust pattern
    print("\n1. Testing UpThrust (UT) Pattern:")
    print("   (High wick + negative delta + rejection)")
    
    upthrust_bar = {
        "high": 100.5,      # High wick
        "low": 99.5,
        "open": 99.8,
        "close": 99.9,      # Close back inside
        "volume": 1000,
        "delta": -100,
        "delta_close": -100,  # Negative delta!
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(upthrust_bar)
    print(f"   UpThrust detected: {result['mgann_behavior']['UT']}")
    
    # Test Shakeout pattern
    print("\n2. Testing Shakeout (SP) Pattern:")
    print("   (Low sweep + positive delta + strong close)")
    
    # Reset module
    module = Fix14MgannSwing(threshold_ticks=6)
    module.process_bar(init_bar)
    
    shakeout_bar = {
        "high": 100.0,
        "low": 99.0,        # Low sweep
        "open": 99.5,
        "close": 99.8,      # Close strong
        "volume": 1000,
        "delta": 100,
        "delta_close": 100,  # Positive delta!
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(shakeout_bar)
    print(f"   Shakeout detected: {result['mgann_behavior']['SP']}")
    
    print("\n3. Testing Pullback (PB) Pattern:")
    print("   (Small counter-move + weak delta)")
    
    # Create uptrend first
    module = Fix14MgannSwing(threshold_ticks=6)
    module.process_bar(init_bar)
    module.last_swing_dir = 1  # Set to uptrend
    
    pullback_bar = {
        "high": 100.0,
        "low": 99.8,
        "open": 100.0,
        "close": 99.9,      # Small down move
        "volume": 1000,
        "delta": 5,
        "delta_close": 5,    # Weak delta (<10% volume)
        "range": 0.2,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(pullback_bar)
    print(f"   Pullback detected: {result['mgann_behavior']['PB']}")
    print()


def demo_wave_strength():
    """Demo tính toán wave strength."""
    print("=" * 60)
    print("DEMO 4: Wave Strength Calculation")
    print("=" * 60)
    
    module = Fix14MgannSwing(threshold_ticks=6)
    
    # Strong wave: high delta, high volume, strong momentum
    print("\n1. Strong Wave:")
    strong_bar = {
        "high": 101.0, "low": 99.0, "open": 99.2, "close": 100.8,
        "volume": 5000,     # High volume
        "delta": 3000,      # Strong delta
        "delta_close": 3000,
        "range": 2.0,       # Large range
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    result = module.process_bar(strong_bar)
    print(f"   Delta: {strong_bar['delta']}, Volume: {strong_bar['volume']}")
    print(f"   Body: {abs(strong_bar['close'] - strong_bar['open']):.2f}")
    print(f"   → Wave Strength: {result['mgann_wave_strength']}/100")
    
    # Weak wave: low delta, low volume, weak momentum
    print("\n2. Weak Wave:")
    weak_bar = {
        "high": 100.2, "low": 100.0, "open": 100.1, "close": 100.15,
        "volume": 200,      # Low volume
        "delta": 10,        # Weak delta
        "delta_close": 10,
        "range": 0.2,       # Small range
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    result = module.process_bar(weak_bar)
    print(f"   Delta: {weak_bar['delta']}, Volume: {weak_bar['volume']}")
    print(f"   Body: {abs(weak_bar['close'] - weak_bar['open']):.2f}")
    print(f"   → Wave Strength: {result['mgann_wave_strength']}/100")
    print()


def demo_json_output():
    """Demo xuất kết quả dưới dạng JSON."""
    print("=" * 60)
    print("DEMO 5: JSON Output Format")
    print("=" * 60)
    
    module = Fix14MgannSwing(threshold_ticks=6)
    
    bar = {
        "high": 100.5, "low": 99.5, "open": 100.0, "close": 100.3,
        "volume": 1000, "delta": 50, "delta_close": 50,
        "range": 1.0, "tick_size": 0.1, "atr14": 0.5,
    }
    
    result = module.process_bar(bar)
    
    # Extract MGann fields
    mgann_output = {
        "mgann_internal_swing_high": result["mgann_internal_swing_high"],
        "mgann_internal_swing_low": result["mgann_internal_swing_low"],
        "mgann_internal_leg_dir": result["mgann_internal_leg_dir"],
        "mgann_wave_strength": result["mgann_wave_strength"],
        "mgann_behavior": result["mgann_behavior"],
    }
    
    print("\nMGann Swing Output (JSON format):")
    print(json.dumps(mgann_output, indent=2))
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  MODULE 14 (MGann Swing) - DEMO SCRIPT")
    print("=" * 60 + "\n")
    
    # Run all demos
    demo_basic_usage()
    demo_swing_detection()
    demo_pattern_detection()
    demo_wave_strength()
    demo_json_output()
    
    print("=" * 60)
    print("✓ All demos completed successfully!")
    print("=" * 60)
    print("\nĐể test với data của bạn:")
    print("1. Import module: from processor.modules.fix14_mgann_swing import Fix14MgannSwing")
    print("2. Tạo instance: module = Fix14MgannSwing(threshold_ticks=6)")
    print("3. Process bars: result = module.process_bar(your_bar_data)")
    print()
