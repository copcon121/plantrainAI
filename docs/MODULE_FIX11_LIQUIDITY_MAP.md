# 📍 MODULE FIX #11: LIQUIDITY MAP & COMPREHENSIVE SWEEP DETECTION

**Module Name:** `fix11_liquidity_map.py`
**Purpose:** Build comprehensive liquidity map and detect sweeps beyond just HL/LL
**Status:** 🟡 Specification Complete - Awaiting Implementation
**Priority:** High (Required for FVG Quality Module)

---

## 🎯 OBJECTIVE

**Problem:** Current sweep detection only looks at Higher High/Lower Low breaks. But liquidity exists in many forms:
- Equal Highs/Lows (EQH/EQL)
- Order Block edges
- Previous session highs/lows
- Value Area High/Low (VAH/VAL)

**Solution:** Build comprehensive liquidity map and detect sweeps of ANY liquidity level, not just structural HL/LL.

**Goal:**
- Detect "liquidity before structure" sweeps (common trap pattern)
- Enable FVG Quality Module to identify post-sweep setups
- Improve setup quality by filtering non-sweep vs sweep contexts

---

## 🗺️ LIQUIDITY MAP COMPONENTS

### 1. Swing Structure Liquidity

**Levels:**
- **Higher High (HH)** resting liquidity above
- **Lower Low (LL)** resting liquidity below
- **Previous swing high/low**

**Why it matters:**
- Most obvious liquidity pools
- Stop losses sitting above/below these levels
- Classic "liquidity grab" before reversal

---

### 2. Equal Highs/Lows (EQH/EQL)

**Levels:**
- **Equal Highs:** 2+ swing highs within 2-3 ticks
- **Equal Lows:** 2+ swing lows within 2-3 ticks

**Why it matters:**
- **Retail pattern:** Traders see "double top/bottom" → place stops above/below
- **Smart money knows:** These are liquidity magnets
- **Common trap:** Price sweeps EQH/EQL → reverses sharply

---

### 3. Order Block Edges

**Levels:**
- **Bullish OB low** (demand zone bottom)
- **Bearish OB high** (supply zone top)

**Why it matters:**
- OBs represent institutional orders
- Edge of OB = "liquidity before actual structure"
- Price often hits OB edge → reacts → doesn't need to hit HL/LL

---

### 4. Session Liquidity (Volume Profile)

**Levels:**
- **VAH (Value Area High)** - top of fair value
- **VAL (Value Area Low)** - bottom of fair value
- **Previous session high/low**

**Why it matters:**
- Session extremes = significant liquidity pools
- VAH/VAL = boundaries where stops accumulate
- Multi-day highs/lows even more significant

---

### 5. Round Number / Psychological Levels (Optional)

**Levels:**
- Round numbers (e.g., 1.2000, 1.2500)
- 00/50 levels

**Why it matters:**
- Retail traders love round numbers
- More stops = more liquidity
- Less critical than above, but can add confluence

---

## 📥 INPUT DATA (from Phase 1 Export + Module #9 VP)

### Required Fields Per Bar:

```python
{
    # Basic bar
    "time_utc": "2025-11-20T10:30:00Z",
    "bar_index": 1250,
    "high": 1.23500,
    "low": 1.23400,
    "close": 1.23480,

    # Swing structure (from Ninja)
    "is_swing_high": False,
    "is_swing_low": False,
    "last_swing_high": 1.23600,
    "last_swing_low": 1.23350,

    # EQH/EQL (from Ninja or Python detects)
    "eq_highs_detected": True,
    "eq_high_price": 1.23600,
    "eq_lows_detected": False,
    "eq_low_price": null,

    # OB (from Ninja)
    "ob_bull": True,
    "ob_high": 1.23500,
    "ob_low": 1.23450,
    "ob_bear": False,

    # Volume Profile (from Module #9)
    "vp_session_vah": 1.23650,
    "vp_session_val": 1.23400,
    "vp_prev_session_high": 1.23700,
    "vp_prev_session_low": 1.23300,

    # ATR (for buffer/tolerance)
    "atr_14": 0.00025
}
```

---

## 📤 OUTPUT DATA (added to BarState)

### Per-Bar Outputs (12 fields):

```python
{
    # Sweep detection
    "liquidity_sweep_detected": True,       # Was liquidity swept this bar?
    "sweep_type": "liquidity_above",        # "liquidity_above" / "liquidity_below"
    "sweep_level_price": 1.23600,           # Price of liquidity that was swept
    "sweep_level_type": "eq_highs",         # Type: "swing_high" / "eq_highs" / "ob_edge" / "vah" / etc.
    "sweep_wick_penetration": 0.00015,      # How far wick went past level
    "sweep_body_rejection": True,           # Did body close back inside? (confirmation)

    # Sweep context
    "bars_since_sweep": 0,                  # Bars since last sweep (0 = this bar)
    "sweep_count_recent": 2,                # Number of sweeps in last 20 bars

    # Liquidity distance (for future use)
    "nearest_liq_above_price": 1.23650,     # Nearest liquidity above price
    "nearest_liq_above_type": "vah",
    "nearest_liq_below_price": 1.23400,     # Nearest liquidity below price
    "nearest_liq_below_type": "val"
}
```

---

## 🧮 CALCULATION LOGIC

### Step 1: Build Liquidity Map

```python
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class LiquidityLevel:
    """Represents a single liquidity level."""
    price: float
    level_type: str  # "swing_high", "swing_low", "eq_highs", "eq_lows", "ob_high", "ob_low", "vah", "val", etc.
    created_bar_index: int
    side: str  # "above" or "below" (relative to when created)
    strength: float  # 0-1, how significant

class LiquidityMapModule:
    """
    Module Fix #11: Build liquidity map and detect comprehensive sweeps.
    """

    def __init__(self, buffer_ticks: int = 3, lookback_bars: int = 100):
        self.buffer_ticks = buffer_ticks
        self.lookback_bars = lookback_bars
        self.liquidity_levels: List[LiquidityLevel] = []
        self.last_sweep_bar_index = -999

    def build_liquidity_map(self, bar_states_history: list,
                            current_bar: dict) -> List[LiquidityLevel]:
        """
        Build comprehensive liquidity map from all sources.

        Returns list of LiquidityLevel objects.
        """
        liquidity_levels = []

        # Get lookback window
        lookback_bars = bar_states_history[-self.lookback_bars:]

        # === SOURCE 1: SWING HIGHS/LOWS ===
        for bar in lookback_bars:
            if bar.get("is_swing_high"):
                liquidity_levels.append(LiquidityLevel(
                    price=bar["high"],
                    level_type="swing_high",
                    created_bar_index=bar["bar_index"],
                    side="above",
                    strength=0.8
                ))

            if bar.get("is_swing_low"):
                liquidity_levels.append(LiquidityLevel(
                    price=bar["low"],
                    level_type="swing_low",
                    created_bar_index=bar["bar_index"],
                    side="below",
                    strength=0.8
                ))

        # === SOURCE 2: EQUAL HIGHS/LOWS ===
        # Detect EQH/EQL if not provided by Ninja
        eq_highs = self._detect_equal_highs(lookback_bars)
        eq_lows = self._detect_equal_lows(lookback_bars)

        for eq_high in eq_highs:
            liquidity_levels.append(LiquidityLevel(
                price=eq_high["price"],
                level_type="eq_highs",
                created_bar_index=eq_high["bar_index"],
                side="above",
                strength=0.9  # Higher strength - common trap
            ))

        for eq_low in eq_lows:
            liquidity_levels.append(LiquidityLevel(
                price=eq_low["price"],
                level_type="eq_lows",
                created_bar_index=eq_low["bar_index"],
                side="below",
                strength=0.9
            ))

        # === SOURCE 3: ORDER BLOCK EDGES ===
        for bar in lookback_bars:
            if bar.get("ob_bull"):
                # Bullish OB low = liquidity below
                liquidity_levels.append(LiquidityLevel(
                    price=bar["ob_low"],
                    level_type="ob_low",
                    created_bar_index=bar["bar_index"],
                    side="below",
                    strength=0.7
                ))

            if bar.get("ob_bear"):
                # Bearish OB high = liquidity above
                liquidity_levels.append(LiquidityLevel(
                    price=bar["ob_high"],
                    level_type="ob_high",
                    created_bar_index=bar["bar_index"],
                    side="above",
                    strength=0.7
                ))

        # === SOURCE 4: SESSION VP LEVELS ===
        vah = current_bar.get("vp_session_vah")
        val = current_bar.get("vp_session_val")
        prev_session_high = current_bar.get("vp_prev_session_high")
        prev_session_low = current_bar.get("vp_prev_session_low")

        if vah:
            liquidity_levels.append(LiquidityLevel(
                price=vah,
                level_type="vah",
                created_bar_index=current_bar["bar_index"],
                side="above",
                strength=0.75
            ))

        if val:
            liquidity_levels.append(LiquidityLevel(
                price=val,
                level_type="val",
                created_bar_index=current_bar["bar_index"],
                side="below",
                strength=0.75
            ))

        if prev_session_high:
            liquidity_levels.append(LiquidityLevel(
                price=prev_session_high,
                level_type="prev_session_high",
                created_bar_index=current_bar["bar_index"] - 1440,  # ~1 day ago
                side="above",
                strength=0.85
            ))

        if prev_session_low:
            liquidity_levels.append(LiquidityLevel(
                price=prev_session_low,
                level_type="prev_session_low",
                created_bar_index=current_bar["bar_index"] - 1440,
                side="below",
                strength=0.85
            ))

        # Deduplicate levels within tolerance (buffer_ticks)
        liquidity_levels = self._deduplicate_levels(liquidity_levels, current_bar["atr_14"])

        return liquidity_levels

    def _detect_equal_highs(self, lookback_bars: list) -> List[dict]:
        """
        Detect equal highs: 2+ swing highs within tolerance.

        Returns list of {"price": float, "bar_index": int}
        """
        swing_highs = [
            {"price": bar["high"], "bar_index": bar["bar_index"]}
            for bar in lookback_bars
            if bar.get("is_swing_high")
        ]

        eq_highs = []
        tolerance = 3 * 0.00001  # 3 ticks (adjust for instrument)

        for i, sh1 in enumerate(swing_highs):
            for sh2 in swing_highs[i + 1:]:
                if abs(sh1["price"] - sh2["price"]) <= tolerance:
                    # Found equal high
                    avg_price = (sh1["price"] + sh2["price"]) / 2
                    eq_highs.append({
                        "price": avg_price,
                        "bar_index": max(sh1["bar_index"], sh2["bar_index"])
                    })
                    break  # Only count once per swing high

        return eq_highs

    def _detect_equal_lows(self, lookback_bars: list) -> List[dict]:
        """Detect equal lows: 2+ swing lows within tolerance."""
        swing_lows = [
            {"price": bar["low"], "bar_index": bar["bar_index"]}
            for bar in lookback_bars
            if bar.get("is_swing_low")
        ]

        eq_lows = []
        tolerance = 3 * 0.00001

        for i, sl1 in enumerate(swing_lows):
            for sl2 in swing_lows[i + 1:]:
                if abs(sl1["price"] - sl2["price"]) <= tolerance:
                    avg_price = (sl1["price"] + sl2["price"]) / 2
                    eq_lows.append({
                        "price": avg_price,
                        "bar_index": max(sl1["bar_index"], sl2["bar_index"])
                    })
                    break

        return eq_lows

    def _deduplicate_levels(self, levels: List[LiquidityLevel],
                           atr: float) -> List[LiquidityLevel]:
        """
        Remove duplicate levels within ATR tolerance.
        Keep the one with highest strength.
        """
        tolerance = 0.5 * atr  # Within 0.5 ATR = same level

        unique_levels = []

        for level in levels:
            # Check if similar level already exists
            similar = next((l for l in unique_levels
                           if abs(l.price - level.price) <= tolerance), None)

            if similar:
                # Keep the one with higher strength
                if level.strength > similar.strength:
                    unique_levels.remove(similar)
                    unique_levels.append(level)
            else:
                unique_levels.append(level)

        return unique_levels
```

---

### Step 2: Detect Liquidity Sweep

```python
def detect_sweep(self, current_bar: dict,
                liquidity_levels: List[LiquidityLevel]) -> dict:
    """
    Detect if current bar swept any liquidity level.

    Sweep criteria:
    1. Wick penetrates level (high > level for above, low < level for below)
    2. Body rejects level (close doesn't stay past level) - OPTIONAL but stronger
    3. Level is recent enough (not too old)

    Returns:
        dict with sweep info or null dict
    """
    high = current_bar["high"]
    low = current_bar["low"]
    close = current_bar["close"]
    open_price = current_bar["open"]
    bar_index = current_bar["bar_index"]
    atr = current_bar["atr_14"]

    buffer = self.buffer_ticks * 0.00001  # Convert ticks to price

    # Separate levels into above/below
    levels_above = [l for l in liquidity_levels if l.side == "above" and l.price > close]
    levels_below = [l for l in liquidity_levels if l.side == "below" and l.price < close]

    # Check sweep above (bearish sweep)
    for level in sorted(levels_above, key=lambda x: x.price):
        # Did wick penetrate level?
        if high >= level.price + buffer:
            # Wick hit level

            # Check body rejection (stronger signal)
            body_rejected = (close < level.price)

            # Check if level is recent enough (not stale)
            bars_since_creation = bar_index - level.created_bar_index
            if bars_since_creation > self.lookback_bars:
                continue  # Level too old

            # Calculate penetration distance
            penetration = high - level.price

            # Update last sweep tracking
            self.last_sweep_bar_index = bar_index

            return {
                "liquidity_sweep_detected": True,
                "sweep_type": "liquidity_above",
                "sweep_level_price": level.price,
                "sweep_level_type": level.level_type,
                "sweep_wick_penetration": round(penetration, 5),
                "sweep_body_rejection": body_rejected,
                "bars_since_sweep": 0
            }

    # Check sweep below (bullish sweep)
    for level in sorted(levels_below, key=lambda x: x.price, reverse=True):
        if low <= level.price - buffer:
            body_rejected = (close > level.price)
            bars_since_creation = bar_index - level.created_bar_index

            if bars_since_creation > self.lookback_bars:
                continue

            penetration = level.price - low
            self.last_sweep_bar_index = bar_index

            return {
                "liquidity_sweep_detected": True,
                "sweep_type": "liquidity_below",
                "sweep_level_price": level.price,
                "sweep_level_type": level.level_type,
                "sweep_wick_penetration": round(penetration, 5),
                "sweep_body_rejection": body_rejected,
                "bars_since_sweep": 0
            }

    # No sweep detected
    # Calculate bars since last sweep
    bars_since_sweep = bar_index - self.last_sweep_bar_index

    return {
        "liquidity_sweep_detected": False,
        "sweep_type": "none",
        "sweep_level_price": None,
        "sweep_level_type": "none",
        "sweep_wick_penetration": 0.0,
        "sweep_body_rejection": False,
        "bars_since_sweep": bars_since_sweep if bars_since_sweep < 999 else 999
    }
```

---

### Step 3: Calculate Nearest Liquidity (for distance features)

```python
def calculate_nearest_liquidity(self, current_bar: dict,
                                liquidity_levels: List[LiquidityLevel]) -> dict:
    """
    Find nearest liquidity above and below current price.

    Used for:
    - Target setting (TP toward next liquidity)
    - Risk assessment (how close to liquidity trap)
    """
    close = current_bar["close"]

    levels_above = [l for l in liquidity_levels if l.price > close]
    levels_below = [l for l in liquidity_levels if l.price < close]

    # Find nearest above
    if levels_above:
        nearest_above = min(levels_above, key=lambda x: x.price - close)
        nearest_liq_above_price = nearest_above.price
        nearest_liq_above_type = nearest_above.level_type
    else:
        nearest_liq_above_price = None
        nearest_liq_above_type = "none"

    # Find nearest below
    if levels_below:
        nearest_below = max(levels_below, key=lambda x: x.price)
        nearest_liq_below_price = nearest_below.price
        nearest_liq_below_type = nearest_below.level_type
    else:
        nearest_liq_below_price = None
        nearest_liq_below_type = "none"

    return {
        "nearest_liq_above_price": nearest_liq_above_price,
        "nearest_liq_above_type": nearest_liq_above_type,
        "nearest_liq_below_price": nearest_liq_below_price,
        "nearest_liq_below_type": nearest_liq_below_type
    }
```

---

### Step 4: Main Process Function

```python
def process_bar(self, current_bar: dict, bar_states_history: list) -> dict:
    """
    Process a single bar and add liquidity map fields.

    Returns:
        dict with liquidity fields added
    """
    # Step 1: Build liquidity map
    liquidity_levels = self.build_liquidity_map(bar_states_history, current_bar)

    # Step 2: Detect sweep
    sweep_info = self.detect_sweep(current_bar, liquidity_levels)

    # Step 3: Calculate nearest liquidity
    nearest_liq = self.calculate_nearest_liquidity(current_bar, liquidity_levels)

    # Step 4: Count recent sweeps (for context)
    recent_bars = bar_states_history[-20:]
    sweep_count_recent = sum(1 for b in recent_bars
                            if b.get("liquidity_sweep_detected", False))

    # Merge all outputs
    output = {
        **current_bar,
        **sweep_info,
        **nearest_liq,
        "sweep_count_recent": sweep_count_recent
    }

    return output
```

---

## 🐍 COMPLETE PYTHON MODULE

```python
# processor/modules/fix11_liquidity_map.py

from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class LiquidityLevel:
    """Represents a single liquidity level."""
    price: float
    level_type: str
    created_bar_index: int
    side: str
    strength: float

class LiquidityMapModule:
    """
    Module Fix #11: Comprehensive Liquidity Map & Sweep Detection.

    Builds liquidity map from:
    - Swing highs/lows
    - Equal highs/lows
    - Order block edges
    - Session VP levels (VAH/VAL)
    - Previous session extremes

    Detects sweeps of ANY liquidity, not just HL/LL.
    """

    def __init__(self, buffer_ticks: int = 3, lookback_bars: int = 100):
        self.buffer_ticks = buffer_ticks
        self.lookback_bars = lookback_bars
        self.last_sweep_bar_index = -999

    def process_bar(self, current_bar: dict, bar_states_history: list) -> dict:
        """Main processing function."""
        # (Implementation from Step 4 above)
        pass

    def build_liquidity_map(self, bar_states_history: list,
                            current_bar: dict) -> List[LiquidityLevel]:
        """Build comprehensive liquidity map."""
        # (Implementation from Step 1 above)
        pass

    def detect_sweep(self, current_bar: dict,
                    liquidity_levels: List[LiquidityLevel]) -> dict:
        """Detect liquidity sweep."""
        # (Implementation from Step 2 above)
        pass

    def calculate_nearest_liquidity(self, current_bar: dict,
                                    liquidity_levels: List[LiquidityLevel]) -> dict:
        """Find nearest liquidity above/below."""
        # (Implementation from Step 3 above)
        pass

    def _detect_equal_highs(self, lookback_bars: list) -> List[dict]:
        """Detect equal highs."""
        # (Implementation from Step 1)
        pass

    def _detect_equal_lows(self, lookback_bars: list) -> List[dict]:
        """Detect equal lows."""
        # (Implementation from Step 1)
        pass

    def _deduplicate_levels(self, levels: List[LiquidityLevel],
                           atr: float) -> List[LiquidityLevel]:
        """Remove duplicate levels."""
        # (Implementation from Step 1)
        pass
```

---

## ✅ SUCCESS CRITERIA

### Statistical Validation:

**Hypothesis:** Setups after liquidity sweeps have higher win rate than setups without sweeps.

**Expected Patterns:**

| Pattern | Expected Win Rate | Reasoning |
|---------|------------------|-----------|
| No sweep context | 25-30% | Random setups |
| Sweep + aligned setup | 40-45% | Trap → reversal |
| Sweep EQH/EQL | 45-50% | Common trap pattern |
| Multiple sweeps (2+) | 35-40% | Choppy, less reliable |

### Backtest Targets:

```python
def validate_liquidity_module(events: List[dict]):
    """
    Validate Liquidity Map Module performance.
    """

    # Separate by sweep context
    no_sweep = [e for e in events if not e.get("liquidity_sweep_detected")]
    with_sweep = [e for e in events if e.get("liquidity_sweep_detected")]
    sweep_eq = [e for e in with_sweep
                if "eq_" in e.get("sweep_level_type", "")]

    # Calculate win rates
    wr_no_sweep = win_rate(no_sweep)
    wr_with_sweep = win_rate(with_sweep)
    wr_sweep_eq = win_rate(sweep_eq)

    print(f"No sweep: {len(no_sweep)} events, WR: {wr_no_sweep:.1f}%")
    print(f"With sweep: {len(with_sweep)} events, WR: {wr_with_sweep:.1f}%")
    print(f"Sweep EQH/EQL: {len(sweep_eq)} events, WR: {wr_sweep_eq:.1f}%")

    # Assertions
    assert wr_with_sweep > wr_no_sweep + 5, "Sweep setups should have +5% higher WR"
    assert wr_sweep_eq > wr_with_sweep, "EQH/EQL sweeps should be best"

    print("✅ Liquidity Map Module validation PASSED")
```

---

## 🧪 UNIT TESTS

```python
# processor/tests/test_fix11.py

def test_liquidity_map_building():
    """Test liquidity map builds all sources."""
    module = LiquidityMapModule()

    history = [
        {"bar_index": 100, "is_swing_high": True, "high": 1.2350},
        {"bar_index": 101, "is_swing_low": True, "low": 1.2300},
        {"bar_index": 102, "ob_bull": True, "ob_low": 1.2310}
    ]

    current_bar = {
        "bar_index": 103,
        "vp_session_vah": 1.2360,
        "vp_session_val": 1.2290,
        "atr_14": 0.00020
    }

    levels = module.build_liquidity_map(history, current_bar)

    # Should have: swing_high, swing_low, ob_low, vah, val = 5 levels
    assert len(levels) >= 5
    assert any(l.level_type == "swing_high" for l in levels)
    assert any(l.level_type == "vah" for l in levels)

def test_sweep_detection_above():
    """Test sweep above detection."""
    module = LiquidityMapModule()

    level = LiquidityLevel(
        price=1.2350,
        level_type="eq_highs",
        created_bar_index=100,
        side="above",
        strength=0.9
    )

    current_bar = {
        "bar_index": 105,
        "high": 1.2355,  # Wick swept above 1.2350
        "low": 1.2340,
        "close": 1.2345,  # Body rejected back below
        "open": 1.2342,
        "atr_14": 0.00020
    }

    sweep_info = module.detect_sweep(current_bar, [level])

    assert sweep_info["liquidity_sweep_detected"] == True
    assert sweep_info["sweep_type"] == "liquidity_above"
    assert sweep_info["sweep_level_type"] == "eq_highs"
    assert sweep_info["sweep_body_rejection"] == True

def test_equal_highs_detection():
    """Test EQH detection."""
    module = LiquidityMapModule()

    bars = [
        {"bar_index": 100, "is_swing_high": True, "high": 1.2350},
        {"bar_index": 102, "is_swing_high": True, "high": 1.2351}  # Within 1 tick
    ]

    eq_highs = module._detect_equal_highs(bars)

    assert len(eq_highs) >= 1
    assert 1.23505 - 0.00005 <= eq_highs[0]["price"] <= 1.23505 + 0.00005
```

---

## 📝 INTEGRATION NOTES

### Dependency on Other Modules:

**Module #9 (Volume Profile):** RECOMMENDED
- Provides VAH/VAL/POC for session liquidity
- If not available, session liquidity will be skipped (module still works)

**Required for:**
- **Module #2 (FVG Quality):** Uses sweep detection for "after sweep" classification
- **Module #5 (Stop Placement):** Uses nearest liquidity for better SL placement
- **Module #6 (Dynamic TP):** Uses nearest liquidity for TP targets

### Module Execution Order:

```python
# processor/core/smc_processor.py

class SMCDataProcessor:
    def process_bar(self, raw_bar):
        # Step 1: Build session VP (optional but recommended)
        bar_state = self.fix9_volume_profile.process_bar(raw_bar)

        # Step 2: Build liquidity map & detect sweeps
        bar_state = self.fix11_liquidity_map.process_bar(
            bar_state,
            self.bar_history
        )

        # Step 3: FVG Quality (uses sweep info)
        bar_state = self.fix2_fvg_quality.process_bar(bar_state)

        return bar_state
```

---

## 🚀 IMPLEMENTATION PRIORITY

**Priority Level:** HIGH (Required for FVG Quality Module)

**Why?**
1. **Enables FVG Quality:** Module #2 depends on sweep detection
2. **Universal utility:** Many other modules benefit from liquidity map
3. **High signal value:** Sweep detection is a strong predictor
4. **Moderate complexity:** Not trivial, but well-defined logic

**Implement after:**
- Module #9: Volume Profile (recommended, not required)

**Implement before:**
- Module #2: FVG Quality (critical dependency)
- Module #5: Stop Placement
- Module #6: Dynamic TP

---

## 📚 REFERENCES

**SMC Liquidity Theory:**
- Liquidity = resting stop losses + pending orders
- Smart money sweeps liquidity before reversing
- "Buy stops above resistance, sell stops below support"

**Common Trap Patterns:**
- Double top/bottom (EQH/EQL) → sweep → reversal
- False breakout → sweep HL/LL → trap
- "Stop hunt" before true move

**Liquidity Sources:**
- Swing structure (most obvious)
- Equal highs/lows (retail pattern)
- Order blocks (institutional levels)
- Session extremes (time-based liquidity)

---

**Last Updated:** November 20, 2025
**Status:** 📝 Spec Complete - Ready for Implementation
**Dependencies:** Module #9 (VP) - Recommended (not required)
