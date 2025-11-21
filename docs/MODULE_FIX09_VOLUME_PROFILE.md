# 📊 MODULE FIX #09: VOLUME PROFILE & SESSION ANALYSIS

**Module Name:** `fix09_volume_profile.py`
**Purpose:** Build session-based Volume Profile (VAH/VAL/POC) and detect VA shift between sessions
**Status:** 🟡 Specification Complete - Awaiting Implementation
**Priority:** High (institutional order flow signal)

---

## 🎯 OBJECTIVE

Replicate how professional traders use Volume Profile:
1. **Within-session analysis:** Where is price relative to Value Area (VA) and Point of Control (POC)?
2. **Between-session analysis:** Did Value Area shift between Asia → London → NY sessions?

**Goal:** Model learns:
- Inside VA → choppy, wait for VAH/VAL
- At VAH/VAL/POC → key levels for reversal/breakout
- VA shift up → bullish bias, VA shift down → bearish bias

---

## 📊 VOLUME PROFILE CONCEPTS

### What is Volume Profile?

Volume Profile shows **how much volume traded at each price level** during a period (session).

Key components:
- **POC (Point of Control):** Price level with highest volume (most accepted price)
- **Value Area (VA):** Price range containing 70% of total volume
  - **VAH (Value Area High):** Top of VA
  - **VAL (Value Area Low):** Bottom of VA

### Why Session-Based?

Each trading session (Asia/London/NY) has different participants → different "fair value":
- **Asia session:** Asian institutions, lower volume
- **London session:** European institutions, highest volume
- **NY session:** US institutions, high volume

**VA shift** between sessions = institutional bias change:
- VA London > VA Asia → Bulls took control
- VA NY < VA London → Bears took control

---

## 📥 INPUT DATA (from Phase 1 Export)

### Required Fields Per Bar:

```python
{
    "time_utc": "2025-11-20T10:30:00Z",
    "open": 1.23450,
    "high": 1.23500,
    "low": 1.23400,
    "close": 1.23480,
    "volume": 1250,

    # Session info (NEW - for VP grouping)
    "session_name": "London",        # "Asia" / "London" / "NY" / "Other"
    "session_date": "2025-11-20",    # Date of session
    "session_bar_index": 37,         # Bar number in session

    # Volume delta (for VP weighting)
    "buy_volume": 750,
    "sell_volume": 500,
    "delta": 250,

    # ATR (for normalization)
    "atr_14": 0.00025
}
```

---

## 📤 OUTPUT DATA (added to BarState)

### Per-Bar Outputs (11 fields):

```python
{
    # Current session VP (recalculated each bar as session builds)
    "vp_session_poc_price": 1.23480,      # POC of current session
    "vp_session_vah": 1.23550,            # Value Area High
    "vp_session_val": 1.23420,            # Value Area Low
    "vp_session_range_high": 1.23650,     # Session high
    "vp_session_range_low": 1.23300,      # Session low

    # Price position relative to VP
    "vp_pos_in_range": 0.64,              # (close - range_low) / (range_high - range_low)
    "vp_in_value_area": 1,                # 1 if inside VA, 0 if outside
    "vp_dist_to_poc_rr": -0.12,           # (close - poc) / atr (negative = below POC)
    "vp_dist_to_vah_rr": -0.28,           # (close - vah) / atr
    "vp_dist_to_val_rr": 0.24,            # (close - val) / atr

    # Previous session reference (for VA shift detection)
    "vp_prev_session_name": "Asia",       # Previous session (or null if first)
    "vp_prev_session_poc": 1.23420,       # Previous session POC
    "vp_prev_session_vah": 1.23500,       # Previous session VAH
    "vp_prev_session_val": 1.23380,       # Previous session VAL

    # VA shift analysis (between sessions)
    "vp_poc_shift_from_prev_rr": 0.24,    # (curr_poc - prev_poc) / atr
    "vp_va_mid_shift_from_prev_rr": 0.18, # (curr_va_mid - prev_va_mid) / atr
    "vp_va_overlap_percent": 45.5         # % overlap between current and prev VA
}
```

---

## 🧮 CALCULATION LOGIC

### Step 1: Build Volume Profile Per Session

For each unique `(session_date, session_name)` combination:

```python
def build_session_profile(session_bars: List[Bar]) -> SessionProfile:
    """
    Build volume profile for entire session.

    Args:
        session_bars: All bars in the session, in chronological order

    Returns:
        SessionProfile with POC, VAH, VAL
    """

    # 1. Find session range
    range_high = max(bar.high for bar in session_bars)
    range_low = min(bar.low for bar in session_bars)

    # 2. Create price levels (tick by tick or rounded)
    tick_size = 0.00001  # For forex, adjust as needed
    price_levels = {}

    # 3. Distribute volume to price levels
    for bar in session_bars:
        # Simple: assume uniform distribution within bar range
        # Advanced: use TPO or more sophisticated distribution
        bar_range = bar.high - bar.low
        if bar_range < tick_size:
            # Single price level
            price = round(bar.close / tick_size) * tick_size
            price_levels[price] = price_levels.get(price, 0) + bar.volume
        else:
            # Distribute across multiple levels
            num_levels = max(1, int(bar_range / tick_size))
            volume_per_level = bar.volume / num_levels

            for i in range(num_levels):
                price = bar.low + i * tick_size
                price = round(price / tick_size) * tick_size
                price_levels[price] = price_levels.get(price, 0) + volume_per_level

    # 4. Find POC (price with max volume)
    poc_price = max(price_levels.items(), key=lambda x: x[1])[0]

    # 5. Find Value Area (70% of total volume)
    total_volume = sum(price_levels.values())
    target_volume = total_volume * 0.70

    # Start from POC and expand outward
    va_prices = {poc_price}
    va_volume = price_levels[poc_price]

    prices_sorted = sorted(price_levels.keys())
    poc_idx = prices_sorted.index(poc_price)

    up_idx = poc_idx + 1
    down_idx = poc_idx - 1

    while va_volume < target_volume:
        up_vol = price_levels.get(prices_sorted[up_idx], 0) if up_idx < len(prices_sorted) else 0
        down_vol = price_levels.get(prices_sorted[down_idx], 0) if down_idx >= 0 else 0

        if up_vol >= down_vol and up_idx < len(prices_sorted):
            va_prices.add(prices_sorted[up_idx])
            va_volume += up_vol
            up_idx += 1
        elif down_idx >= 0:
            va_prices.add(prices_sorted[down_idx])
            va_volume += down_vol
            down_idx -= 1
        else:
            break

    # 6. Define VAH and VAL
    vah = max(va_prices)
    val = min(va_prices)

    return SessionProfile(
        session_name=session_bars[0].session_name,
        session_date=session_bars[0].session_date,
        range_high=range_high,
        range_low=range_low,
        poc_price=poc_price,
        vah=vah,
        val=val,
        total_volume=total_volume
    )
```

### Step 2: Calculate Price Position Relative to VP

```python
def calculate_vp_position(bar: Bar, session_profile: SessionProfile) -> dict:
    """
    Calculate where price is relative to VP levels.
    """
    close = bar.close
    atr = bar.atr_14

    # Position in range (0 = at low, 1 = at high)
    range_size = session_profile.range_high - session_profile.range_low
    if range_size > 0:
        pos_in_range = (close - session_profile.range_low) / range_size
    else:
        pos_in_range = 0.5

    # Inside Value Area?
    in_value_area = 1 if session_profile.val <= close <= session_profile.vah else 0

    # Distance to key levels (in ATR units)
    dist_to_poc_rr = (close - session_profile.poc_price) / atr if atr > 0 else 0
    dist_to_vah_rr = (close - session_profile.vah) / atr if atr > 0 else 0
    dist_to_val_rr = (close - session_profile.val) / atr if atr > 0 else 0

    return {
        "vp_session_poc_price": session_profile.poc_price,
        "vp_session_vah": session_profile.vah,
        "vp_session_val": session_profile.val,
        "vp_session_range_high": session_profile.range_high,
        "vp_session_range_low": session_profile.range_low,
        "vp_pos_in_range": round(pos_in_range, 4),
        "vp_in_value_area": in_value_area,
        "vp_dist_to_poc_rr": round(dist_to_poc_rr, 4),
        "vp_dist_to_vah_rr": round(dist_to_vah_rr, 4),
        "vp_dist_to_val_rr": round(dist_to_val_rr, 4)
    }
```

### Step 3: Detect VA Shift Between Sessions

```python
def calculate_va_shift(curr_profile: SessionProfile,
                       prev_profile: SessionProfile,
                       atr: float) -> dict:
    """
    Calculate VA shift between consecutive sessions.
    """
    if prev_profile is None:
        return {
            "vp_prev_session_name": None,
            "vp_prev_session_poc": None,
            "vp_prev_session_vah": None,
            "vp_prev_session_val": None,
            "vp_poc_shift_from_prev_rr": 0,
            "vp_va_mid_shift_from_prev_rr": 0,
            "vp_va_overlap_percent": 0
        }

    # POC shift
    poc_shift = curr_profile.poc_price - prev_profile.poc_price
    poc_shift_rr = poc_shift / atr if atr > 0 else 0

    # VA midpoint shift
    curr_va_mid = (curr_profile.vah + curr_profile.val) / 2
    prev_va_mid = (prev_profile.vah + prev_profile.val) / 2
    va_mid_shift = curr_va_mid - prev_va_mid
    va_mid_shift_rr = va_mid_shift / atr if atr > 0 else 0

    # VA overlap percentage
    overlap_high = min(curr_profile.vah, prev_profile.vah)
    overlap_low = max(curr_profile.val, prev_profile.val)

    if overlap_high > overlap_low:
        overlap_size = overlap_high - overlap_low
        curr_va_size = curr_profile.vah - curr_profile.val
        va_overlap_percent = (overlap_size / curr_va_size * 100) if curr_va_size > 0 else 0
    else:
        va_overlap_percent = 0  # No overlap (big shift)

    return {
        "vp_prev_session_name": prev_profile.session_name,
        "vp_prev_session_poc": prev_profile.poc_price,
        "vp_prev_session_vah": prev_profile.vah,
        "vp_prev_session_val": prev_profile.val,
        "vp_poc_shift_from_prev_rr": round(poc_shift_rr, 4),
        "vp_va_mid_shift_from_prev_rr": round(va_mid_shift_rr, 4),
        "vp_va_overlap_percent": round(va_overlap_percent, 2)
    }
```

---

## 🐍 PYTHON MODULE IMPLEMENTATION

```python
# processor/modules/fix09_volume_profile.py

from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np

@dataclass
class SessionProfile:
    """Volume Profile for a single session."""
    session_name: str
    session_date: str
    range_high: float
    range_low: float
    poc_price: float
    vah: float
    val: float
    total_volume: float
    price_levels: Dict[float, float]  # price -> volume

class VolumeProfileModule:
    """
    Module Fix #09: Session-based Volume Profile analysis.

    Builds VP per session (Asia/London/NY) and detects VA shift.
    """

    def __init__(self, tick_size: float = 0.00001):
        self.tick_size = tick_size
        self.session_profiles: Dict[tuple, SessionProfile] = {}  # (date, session_name) -> profile
        self.session_bars_buffer: Dict[tuple, List] = {}  # Accumulate bars per session

    def process_bar(self, bar_state: dict) -> dict:
        """
        Process a single bar and add VP features.

        Returns:
            dict with VP fields added
        """
        session_key = (bar_state['session_date'], bar_state['session_name'])

        # 1. Accumulate bars for current session
        if session_key not in self.session_bars_buffer:
            self.session_bars_buffer[session_key] = []
        self.session_bars_buffer[session_key].append(bar_state)

        # 2. Build/update profile for current session
        curr_profile = self._build_session_profile(self.session_bars_buffer[session_key])
        self.session_profiles[session_key] = curr_profile

        # 3. Get previous session profile (for VA shift)
        prev_profile = self._get_previous_session_profile(
            bar_state['session_date'],
            bar_state['session_name']
        )

        # 4. Calculate VP position
        vp_position = self._calculate_vp_position(bar_state, curr_profile)

        # 5. Calculate VA shift
        va_shift = self._calculate_va_shift(
            curr_profile,
            prev_profile,
            bar_state['atr_14']
        )

        # 6. Merge all VP features
        return {**bar_state, **vp_position, **va_shift}

    def _build_session_profile(self, session_bars: List[dict]) -> SessionProfile:
        """Build volume profile from session bars."""
        # (Implementation from Step 1 above)
        pass

    def _calculate_vp_position(self, bar: dict, profile: SessionProfile) -> dict:
        """Calculate price position relative to VP."""
        # (Implementation from Step 2 above)
        pass

    def _calculate_va_shift(self, curr: SessionProfile, prev: Optional[SessionProfile], atr: float) -> dict:
        """Calculate VA shift between sessions."""
        # (Implementation from Step 3 above)
        pass

    def _get_previous_session_profile(self, curr_date: str, curr_session: str) -> Optional[SessionProfile]:
        """
        Get the profile of the previous session.

        Session order within a day: Asia -> London -> NY
        Between days: NY (day n) -> Asia (day n+1)
        """
        # Map session to order
        session_order = {"Asia": 0, "London": 1, "NY": 2}

        if curr_session not in session_order:
            return None

        curr_order = session_order[curr_session]

        # Try same-day previous session
        if curr_order > 0:
            prev_session_names = {0: "Asia", 1: "London", 2: "NY"}
            prev_session = prev_session_names[curr_order - 1]
            prev_key = (curr_date, prev_session)
            if prev_key in self.session_profiles:
                return self.session_profiles[prev_key]

        # If Asia session, get previous day's NY
        if curr_session == "Asia":
            # Parse date and subtract 1 day
            from datetime import datetime, timedelta
            curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
            prev_dt = curr_dt - timedelta(days=1)
            prev_date = prev_dt.strftime("%Y-%m-%d")
            prev_key = (prev_date, "NY")
            if prev_key in self.session_profiles:
                return self.session_profiles[prev_key]

        return None
```

---

## ✅ SUCCESS CRITERIA

### Statistical Validation:

**Hypothesis:** Setups with favorable VP conditions should have higher win rate.

**Expected Patterns:**

| Condition | Expected Win Rate | Reasoning |
|-----------|------------------|-----------|
| Price inside VA, no clear setup | < 25% | Choppy, low conviction |
| Price at VAH/VAL with confluence | 35-40% | Key levels, good for reversals |
| Price at POC retest | 35-40% | Most accepted price, strong support/resistance |
| VA shift > +0.5 ATR + long setup | 40-45% | Bullish bias confirmed |
| VA shift < -0.5 ATR + short setup | 40-45% | Bearish bias confirmed |
| VA overlap < 30% (big shift) | 38-42% | Strong institutional move |

### Backtest Targets:

```python
def validate_vp_module(events: List[dict]):
    """
    Validate VP module performance.
    """

    # 1. Inside VA vs Outside VA
    inside_va = [e for e in events if e['vp_in_value_area'] == 1]
    outside_va = [e for e in events if e['vp_in_value_area'] == 0]

    inside_wr = win_rate(inside_va)
    outside_wr = win_rate(outside_va)

    print(f"Inside VA win rate: {inside_wr:.1f}%")
    print(f"Outside VA win rate: {outside_wr:.1f}%")
    assert outside_wr > inside_wr + 5, "Outside VA should perform better"

    # 2. VA shift alignment
    bullish_shift_long = [e for e in events
                          if e['vp_va_mid_shift_from_prev_rr'] > 0.5
                          and e['direction'] == 1]
    bearish_shift_short = [e for e in events
                           if e['vp_va_mid_shift_from_prev_rr'] < -0.5
                           and e['direction'] == -1]

    aligned_wr = win_rate(bullish_shift_long + bearish_shift_short)
    print(f"VA shift aligned win rate: {aligned_wr:.1f}%")
    assert aligned_wr > 35, "Aligned setups should have >35% win rate"

    # 3. Near key levels (POC/VAH/VAL)
    near_key_levels = [e for e in events
                       if abs(e['vp_dist_to_poc_rr']) < 0.3
                       or abs(e['vp_dist_to_vah_rr']) < 0.3
                       or abs(e['vp_dist_to_val_rr']) < 0.3]

    near_levels_wr = win_rate(near_key_levels)
    print(f"Near key VP levels win rate: {near_levels_wr:.1f}%")
    assert near_levels_wr > 32, "Near key levels should have >32% win rate"

    print("✅ VP Module validation PASSED")
```

---

## 🧪 UNIT TESTS

```python
# processor/tests/test_fix09.py

def test_session_profile_basic():
    """Test basic VP calculation."""
    module = VolumeProfileModule(tick_size=0.00001)

    # Create mock session bars
    bars = [
        {"high": 1.2340, "low": 1.2320, "close": 1.2330, "volume": 1000},
        {"high": 1.2350, "low": 1.2330, "close": 1.2345, "volume": 1500},
        {"high": 1.2345, "low": 1.2325, "close": 1.2335, "volume": 1200},
    ]

    profile = module._build_session_profile(bars)

    # Assertions
    assert profile.range_high == 1.2350
    assert profile.range_low == 1.2320
    assert profile.vah > profile.val
    assert profile.val <= profile.poc_price <= profile.vah
    assert profile.total_volume == 3700

def test_va_shift_calculation():
    """Test VA shift detection."""
    module = VolumeProfileModule()

    asia_profile = SessionProfile(
        session_name="Asia",
        session_date="2025-11-20",
        range_high=1.2350,
        range_low=1.2300,
        poc_price=1.2325,
        vah=1.2340,
        val=1.2310,
        total_volume=50000,
        price_levels={}
    )

    london_profile = SessionProfile(
        session_name="London",
        session_date="2025-11-20",
        range_high=1.2380,
        range_low=1.2330,
        poc_price=1.2355,
        vah=1.2370,
        val=1.2340,
        total_volume=80000,
        price_levels={}
    )

    atr = 0.00025
    shift = module._calculate_va_shift(london_profile, asia_profile, atr)

    # POC shifted up by 0.0030, which is 0.0030/0.00025 = 12 ATR
    assert shift['vp_poc_shift_from_prev_rr'] > 10

    # VA shifted up (bullish)
    assert shift['vp_va_mid_shift_from_prev_rr'] > 0
```

---

## 📝 INTEGRATION NOTES

### How VP Fits in ML Pipeline:

**Training Data:**
```python
# Each event now has VP features
event = {
    # ... existing features ...

    # VP features (17 new fields)
    "vp_in_value_area": 0,           # Outside VA → higher conviction
    "vp_dist_to_poc_rr": -0.8,       # Below POC → looking for retest
    "vp_va_mid_shift_from_prev_rr": 1.2,  # VA shifted up → bullish bias

    # Model learns:
    # - If outside VA + near VAH/VAL + VA shifted in trade direction → TAKE
    # - If inside VA + no clear level → SKIP
}
```

**Feature Importance (Expected):**
- `vp_va_mid_shift_from_prev_rr` → High (institutional bias)
- `vp_in_value_area` → Medium (filter choppy zones)
- `vp_dist_to_poc_rr` → Medium (key level proximity)

---

## 🚀 IMPLEMENTATION PRIORITY

**Priority Level:** HIGH

**Why?**
1. **Institutional signal** - VA shift = smart money movement
2. **Clear logic** - Not complex, easy to validate
3. **High impact** - Expected to improve win rate by 3-5%
4. **Complements SMC** - VP + OB/FVG = powerful confluence

**Implement after:**
- Fix #01 (OB Quality) ✅
- Fix #02 (FVG Quality)
- Fix #04 (Confluence)

**Before:**
- Fix #10 (Liquidity Map)

---

## 📚 REFERENCES

**Volume Profile Theory:**
- Market Profile concept by J. Peter Steidlmayer
- Value Area = 70% of volume (standard)
- POC = highest volume node (price acceptance)

**SMC + VP Integration:**
- OB near POC → high probability retest
- FVG inside VA → likely to fill
- CHoCH with VA shift → strong trend confirmation

**Session Analysis:**
- Asia: 00:00-09:00 UTC (low volume, ranging)
- London: 08:00-17:00 UTC (high volume, trending)
- NY: 13:00-22:00 UTC (high volume, volatile)
- Overlap periods: Highest activity

---

**Last Updated:** November 20, 2025
**Status:** 📝 Spec Complete - Ready for Implementation
