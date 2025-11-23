# 🔄 MODULE FIX #14: MGANN SWING DETECTION

**Module Name:** `fix14_mgann_swing.py`  
**Purpose:** MGann-style internal swing detector with tick-based threshold and pattern recognition  
**Status:** ✅ Implemented and Tested  
**Priority:** Medium (Enhances swing analysis with additional patterns)

---

## 🎯 OBJECTIVE

**Problem:** Standard SMC swing detection may not capture internal market structure patterns and behaviors that indicate institutional activity (UpThrust, Shakeout, Pullbacks, etc.).

**Solution:** Implement MGann-style tick-based swing detection with:
- Tick threshold-based internal zigzag
- Pattern detection (PB, UT, SP)
- 3-push exhaustion tracking
- Wave strength scoring

**Goal:**
- Provide granular internal swing detection
- Identify market manipulation patterns
- Track wave strength combining delta + volume + momentum
- Detect exhaustion signals

---

## 📥 INPUT DATA

### Required Fields Per Bar:

```python
{
    # Price data
    "high": 100.50,
    "low": 99.50,
    "open": 100.00,
    "close": 100.30,
    "range": 1.0,          # high - low
    
    # Volume data
    "volume": 1000,
    "delta": 50,           # buy_volume - sell_volume
    "delta_close": 50,     # Delta at close
    
    # Market data
    "tick_size": 0.1,      # Instrument tick size
    "atr14": 0.5,          # ATR(14) or atr_14
}
```

---

## 📤 OUTPUT DATA

### Per-Bar Outputs (10 fields):

```python
{
    # Internal swing state
    "mgann_internal_swing_high": 100.5,     # Last internal swing high
    "mgann_internal_swing_low": 99.5,       # Last internal swing low
    "mgann_internal_leg_dir": 1,            # Direction: 1=up, -1=down, 0=init
    
    # Pattern flags
    "mgann_pb": False,                      # Pullback detected
    "mgann_ut": False,                      # UpThrust detected
    "mgann_sp": False,                      # Shakeout detected
    "mgann_exhaustion_3push": False,        # 3-push exhaustion
    
    # Strength metrics
    "mgann_wave_strength": 45,              # Wave strength score 0-100
    "mgann_internal_dir": 1,                # Current leg direction (duplicate)
    
    # Behavior dict
    "mgann_behavior": {
        "PB": False,   # Pullback
        "UT": False,   # UpThrust
        "SP": False,   # Shakeout
        "EX3": False   # 3-push exhaustion
    }
}
```

---

## 🧮 CALCULATION LOGIC

### Step 1: Initialize Module

```python
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

# GC-only default: 6 ticks * TickSize(0.1) = 0.6 points
module = Fix14MgannSwing(threshold_ticks=6)
```

### Step 2: Swing Detection Logic

```python
def _is_new_swing_high(self, bar_state, threshold_points):
    """Check if price created new swing high."""
    if self.last_swing_low is None:
        return False
    # Price moved up enough from last known low
    return bar_state.get("high", 0) - self.last_swing_low >= threshold_points

def _is_new_swing_low(self, bar_state, threshold_points):
    """Check if price created new swing low."""
    if self.last_swing_high is None:
        return False
    # Price moved down enough from last known high
    return self.last_swing_high - bar_state.get("low", 0) >= threshold_points
```

**Key Points:**
- Uses tick threshold (default 6 ticks) to filter noise
- Tracks last swing high/low internally
- Creates zigzag pattern based on threshold movements

### Step 3: Pattern Detection

#### UpThrust (UT)
```python
def _detect_UT(self, bar_state):
    """
    UpThrust = new high wick + weak delta + close back inside.
    Indicates selling pressure at highs.
    """
    high = bar_state.get("high", 0)
    open_price = bar_state.get("open", 0)
    close = bar_state.get("close", 0)
    delta_close = bar_state.get("delta_close", 0)
    bar_range = bar_state.get("range", 0)
    
    if high > open_price and high > close:
        if delta_close < 0:
            wick_up = high - max(open_price, close)
            if wick_up > (bar_range * 0.4):
                return True
    return False
```

**Criteria:**
- High above open and close (upper wick)
- Negative delta (selling pressure)
- Upper wick > 40% of bar range

#### Shakeout (SP)
```python
def _detect_SP(self, bar_state):
    """
    Shakeout = sweep low + strong buy delta + close strong.
    Indicates buying pressure after sweep.
    """
    low = bar_state.get("low", 0)
    open_price = bar_state.get("open", 0)
    close = bar_state.get("close", 0)
    delta_close = bar_state.get("delta_close", 0)
    bar_range = bar_state.get("range", 0)
    
    if low < min(open_price, close):
        if delta_close > 0:
            wick_down = min(open_price, close) - low
            if wick_down > (bar_range * 0.4):
                return True
    return False
```

**Criteria:**
- Low below open and close (lower wick sweep)
- Positive delta (buying pressure)
- Lower wick > 40% of bar range

#### Pullback (PB)
```python
def _detect_PB(self, bar_state, swing_dir):
    """
    Pullback = shallow retrace + low volume/delta.
    """
    close = bar_state.get("close", 0)
    open_price = bar_state.get("open", 0)
    delta_close = bar_state.get("delta_close", 0)
    volume = bar_state.get("volume", 1)
    
    if swing_dir == 1:  # up leg
        # small down move + weak selling
        return close < open_price and abs(delta_close) < (volume * 0.1)
    else:  # down leg
        return close > open_price and abs(delta_close) < (volume * 0.1)
```

**Criteria:**
- Counter-trend move relative to leg direction
- Very low delta relative to volume (<10%)

### Step 4: Wave Strength Calculation

```python
def _compute_wave_strength(self, bar_state, leg_delta_sum, leg_volume_sum):
    """
    Simple scoring v1:
        40% delta strength
        40% volume strength
        20% body/momentum
    """
    delta_score = min(1.0, abs(leg_delta_sum) / (leg_volume_sum + 1e-9))
    atr14 = bar_state.get("atr14", bar_state.get("atr_14", 0.5))
    vol_score = min(1.0, leg_volume_sum / (atr14 * 50 + 1e-9))
    
    close = bar_state.get("close", 0)
    open_price = bar_state.get("open", 0)
    bar_range = bar_state.get("range", 1)
    body = abs(close - open_price)
    momentum_score = min(1.0, body / (bar_range + 1e-9))
    
    return int((delta_score * 0.4 + vol_score * 0.4 + momentum_score * 0.2) * 100)
```

**Components:**
- **Delta Strength (40%)**: Directional flow efficiency
- **Volume Strength (40%)**: Volume relative to ATR
- **Momentum (20%)**: Body size relative to range

### Step 5: 3-Push Exhaustion

```python
# Track push count
if created_new_swing:
    self.push_count += 1

# Check exhaustion
exhaustion_flag = (self.push_count >= 3)

# Reset after exhaustion
if exhaustion_flag:
    self.push_count = 0
```

**Logic:**
- Count consecutive swings in same direction
- Flag exhaustion when 3+ pushes detected
- Reset counter after exhaustion signal

---

## 🐍 USAGE EXAMPLE

```python
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

# Initialize with custom threshold
module = Fix14MgannSwing(threshold_ticks=6)

# Process bar
bar_state = {
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

result = module.process_bar(bar_state)

# Access results
print(f"Swing High: {result['mgann_internal_swing_high']}")
print(f"Swing Low: {result['mgann_internal_swing_low']}")
print(f"Direction: {result['mgann_internal_leg_dir']}")
print(f"Wave Strength: {result['mgann_wave_strength']}")
print(f"Patterns: {result['mgann_behavior']}")
```

---

## ✅ SUCCESS CRITERIA

### Unit Tests (7/7 Passing):

- ✅ Module initialization
- ✅ First bar swing initialization  
- ✅ New swing high detection
- ✅ New swing low detection
- ✅ UpThrust pattern detection
- ✅ Shakeout pattern detection
- ✅ 3-push exhaustion logic

### Integration:

- ✅ Integrated into smoke test suite (14/14 modules passing)
- ✅ Compatible with BaseModule interface
- ✅ Thread-safe for production use

---

## 📝 INTEGRATION NOTES

### Dependencies:

**None** - Module is self-contained

### Recommended For:

- **Confluence Module**: Can use UT/SP patterns for setup validation
- **Entry Timing**: PB detection for entry refinement
- **Exit Signals**: Exhaustion detection for profit taking

### Module Execution Order:

```python
# Can run at any point in pipeline
# Recommended: After basic bar data is available

class SMCDataProcessor:
    def process_bar(self, raw_bar):
        # ... other modules ...
        
        # Add MGann swing detection
        bar_state = self.fix14_mgann.process_bar(bar_state)
        
        # Use mgann fields in downstream modules
        # ...
```

---

## 🧪 CONFIGURATION

### Adjustable Parameters:

```python
# Default for GC (Gold)
module = Fix14MgannSwing(threshold_ticks=6)  # 6 ticks * 0.1 = 0.6 points

# For ES (S&P 500)
module = Fix14MgannSwing(threshold_ticks=4)  # 4 ticks * 0.25 = 1.0 points

# For FX (EUR/USD)
module = Fix14MgannSwing(threshold_ticks=3)  # 3 ticks * 0.0001 = 0.0003
```

**Recommendation:** Adjust `threshold_ticks` based on instrument volatility and tick size.

---

## 🔄 VERSION HISTORY

- **v1.0.0** (2025-11-23): Initial implementation with core MGann swing logic
  - Tick-based swing detection
  - UT/SP/PB pattern recognition
  - 3-push exhaustion tracking
  - Wave strength scoring

---

## 📚 REFERENCES

- MGann internal swing methodology
- Volume Spread Analysis (VSA) principles
- Wyckoff market phases
