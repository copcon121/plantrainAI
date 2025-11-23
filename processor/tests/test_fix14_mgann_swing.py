"""Tests for Fix #14: MGann Swing Module."""
from processor.modules.fix14_mgann_swing import Fix14MgannSwing


def test_mgann_swing_initialization():
    """Test that MGann Swing module initializes correctly."""
    module = Fix14MgannSwing(threshold_ticks=6)
    assert module.threshold_ticks == 6
    assert module.last_swing_high is None
    assert module.last_swing_low is None
    assert module.last_swing_dir == 0
    assert module.push_count == 0


def test_mgann_swing_first_bar_initializes_swings():
    """Test that first bar initializes swing high and low."""
    module = Fix14MgannSwing(threshold_ticks=6)
    
    bar = {
        "bar_index": 1,
        "timestamp": "2024-01-15T10:00:00Z",
        "open": 100.0,
        "high": 100.5,
        "low": 99.5,
        "close": 100.2,
        "volume": 1000,
        "delta": 50,
        "delta_close": 50,
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(bar)
    
    assert module.last_swing_high == 100.5
    assert module.last_swing_low == 99.5


def test_mgann_swing_detects_new_swing_high():
    """Test that module detects new swing high when threshold is exceeded."""
    module = Fix14MgannSwing(threshold_ticks=6)
    
    # First bar to initialize
    bar1 = {
        "bar_index": 1,
        "high": 100.0,
        "low": 99.0,
        "open": 99.5,
        "close": 99.8,
        "volume": 1000,
        "delta": 50,
        "delta_close": 50,
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    module.process_bar(bar1)
    
    # Second bar with high enough to create swing high (threshold = 6 ticks * 0.1 = 0.6 points)
    bar2 = {
        "bar_index": 2,
        "high": 99.7,  # 99.0 + 0.7 > threshold of 0.6
        "low": 99.2,
        "open": 99.3,
        "close": 99.6,
        "volume": 1000,
        "delta": 60,
        "delta_close": 60,
        "range": 0.5,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(bar2)
    
    assert module.last_swing_dir == 1  # Up direction
    assert module.last_swing_high == 99.7


def test_mgann_swing_detects_new_swing_low():
    """Test that module detects new swing low when threshold is exceeded."""
    module = Fix14MgannSwing(threshold_ticks=6)
    
    # First bar to initialize
    bar1 = {
        "bar_index": 1,
        "high": 100.0,
        "low": 99.0,
        "open": 99.5,
        "close": 99.8,
        "volume": 1000,
        "delta": 50,
        "delta_close": 50,
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    module.process_bar(bar1)
    
    # Second bar with low enough to create swing low (threshold = 6 ticks * 0.1 = 0.6 points)
    bar2 = {
        "bar_index": 2,
        "high": 99.5,
        "low": 99.3,  # 100.0 - 99.3 = 0.7 > threshold of 0.6
        "open": 99.4,
        "close": 99.35,
        "volume": 1000,
        "delta": -60,
        "delta_close": -60,
        "range": 0.2,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(bar2)
    
    assert module.last_swing_dir == -1  # Down direction
    assert module.last_swing_low == 99.3


def test_mgann_swing_detects_upthrust():
    """Test UpThrust detection: new high wick + weak delta + close back inside."""
    module = Fix14MgannSwing(threshold_ticks=6)
    
    # Initialize first
    bar1 = {
        "bar_index": 1,
        "high": 100.0,
        "low": 99.0,
        "open": 99.5,
        "close": 99.8,
        "volume": 1000,
        "delta": 50,
        "delta_close": 50,
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    module.process_bar(bar1)
    
    # UpThrust bar: high > open/close, negative delta, large upper wick
    bar2 = {
        "bar_index": 2,
        "high": 100.5,  # High wick
        "low": 99.5,
        "open": 99.8,
        "close": 99.9,  # Close back inside
        "volume": 1000,
        "delta": -100,
        "delta_close": -100,  # Negative delta
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(bar2)
    
    assert result["mgann_behavior"]["UT"] == True


def test_mgann_swing_detects_shakeout():
    """Test Shakeout detection: sweep low + strong buy delta + close strong."""
    module = Fix14MgannSwing(threshold_ticks=6)
    
    # Initialize first
    bar1 = {
        "bar_index": 1,
        "high": 100.0,
        "low": 99.0,
        "open": 99.5,
        "close": 99.8,
        "volume": 1000,
        "delta": 50,
        "delta_close": 50,
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    module.process_bar(bar1)
    
    # Shakeout bar: low sweep, positive delta, close strong
    bar2 = {
        "bar_index": 2,
        "high": 100.0,
        "low": 99.0,  # Low sweep
        "open": 99.5,
        "close": 99.8,  # Close strong
        "volume": 1000,
        "delta": 100,
        "delta_close": 100,  # Positive delta
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(bar2)
    
    assert result["mgann_behavior"]["SP"] == True


def test_mgann_swing_three_push_exhaustion():
    """Test 3-push exhaustion detection."""
    module = Fix14MgannSwing(threshold_ticks=6)
    
    # Manually set push_count to test exhaustion logic
    module.push_count = 3
    
    bar = {
        "bar_index": 1,
        "high": 100.0,
        "low": 99.0,
        "open": 99.5,
        "close": 99.8,
        "volume": 1000,
        "delta": 50,
        "delta_close": 50,
        "range": 1.0,
        "tick_size": 0.1,
        "atr14": 0.5,
    }
    
    result = module.process_bar(bar)
    
    # With push_count >= 3, exhaustion flag should be True
    assert result["mgann_behavior"]["EX3"] == True
    # And push_count should be reset to 0
    assert module.push_count == 0
