# MODULE #05: STOP PLACEMENT

## VERSION: 1.0
## STATUS: New Spec
## PRIORITY: HIGH (Risk Management Core)

---

## 1. MODULE OVERVIEW

### 1.1 Mục Đích
Tính **Stop Loss placement** tối ưu cho FVG signal dựa trên SMC structure, đảm bảo:
- Stop đặt đúng vị trí logic (beyond structure)
- Stop không bị hit bởi noise/liquidity sweep
- RR ratio hợp lý với entry và target

### 1.2 Nguyên Lý SMC
> "Stop loss should be placed beyond the invalidation point - where the trade thesis is no longer valid"

**Key SMC Stop Placements:**
- Below/Above the FVG that triggered entry
- Below/Above the Order Block containing FVG
- Below/Above recent swing high/low
- Beyond liquidity pool (avoid stop hunts)

### 1.3 Vị Trí Trong Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     STOP PLACEMENT FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [FVG Signal]                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              STOP CALCULATION OPTIONS               │       │
│  │                                                     │       │
│  │  Option 1: FVG Edge Stop                           │       │
│  │  └─ stop = fvg_bottom - buffer (bullish)           │       │
│  │                                                     │       │
│  │  Option 2: OB Stop                                 │       │
│  │  └─ stop = ob_bottom - buffer (bullish)            │       │
│  │                                                     │       │
│  │  Option 3: Structure Stop                          │       │
│  │  └─ stop = recent_swing_low - buffer (bullish)     │       │
│  │                                                     │       │
│  └─────────────────────────────────────────────────────┘       │
│       │                                                         │
│       ▼                                                         │
│  [Select Optimal Stop] → stop_price, stop_type, stop_distance   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. STOP PLACEMENT METHODS

### 2.1 Method Overview

| Method | Description | When to Use | RR Impact |
|--------|-------------|-------------|-----------|
| `fvg_edge` | Beyond FVG edge | Strong FVG, tight stop | Highest RR |
| `fvg_full` | Beyond FVG opposite edge | Medium FVG | Medium RR |
| `ob_edge` | Beyond Order Block | FVG inside OB | Lower RR |
| `structure` | Beyond swing high/low | Weak FVG, need protection | Lowest RR |

### 2.2 Stop Buffer

```python
# Buffer to add beyond stop level (avoid exact-level stops)
def calculate_stop_buffer(atr: float, method: str) -> float:
    """
    Calculate buffer to add beyond stop level.

    Buffer prevents exact-level stop hunts.
    """
    buffer_ratios = {
        "fvg_edge": 0.1,     # 10% of ATR
        "fvg_full": 0.15,    # 15% of ATR
        "ob_edge": 0.15,     # 15% of ATR
        "structure": 0.2,    # 20% of ATR (more protection)
    }
    return atr * buffer_ratios.get(method, 0.15)
```

---

## 3. STOP CALCULATION LOGIC

### 3.1 FVG Edge Stop (Tightest)

```python
def calculate_fvg_edge_stop(
    fvg_direction: int,  # 1 = bullish, -1 = bearish
    fvg_top: float,
    fvg_bottom: float,
    atr: float
) -> dict:
    """
    Stop just beyond FVG edge.

    For Bullish FVG: stop below fvg_bottom
    For Bearish FVG: stop above fvg_top

    Best for: Strong FVG với high probability
    """
    buffer = calculate_stop_buffer(atr, "fvg_edge")

    if fvg_direction == 1:  # Bullish
        stop_price = fvg_bottom - buffer
        invalidation_level = fvg_bottom
    else:  # Bearish
        stop_price = fvg_top + buffer
        invalidation_level = fvg_top

    return {
        "stop_price": round(stop_price, 5),
        "stop_type": "fvg_edge",
        "invalidation_level": invalidation_level,
        "buffer_used": buffer
    }
```

### 3.2 FVG Full Stop (Conservative)

```python
def calculate_fvg_full_stop(
    fvg_direction: int,
    fvg_top: float,
    fvg_bottom: float,
    atr: float
) -> dict:
    """
    Stop beyond the opposite edge of FVG.

    Allows price to fully fill FVG before invalidating.
    """
    buffer = calculate_stop_buffer(atr, "fvg_full")
    fvg_size = fvg_top - fvg_bottom

    if fvg_direction == 1:  # Bullish
        # Stop below bottom with extra buffer equal to FVG size
        stop_price = fvg_bottom - (fvg_size * 0.2) - buffer
        invalidation_level = fvg_bottom
    else:  # Bearish
        stop_price = fvg_top + (fvg_size * 0.2) + buffer
        invalidation_level = fvg_top

    return {
        "stop_price": round(stop_price, 5),
        "stop_type": "fvg_full",
        "invalidation_level": invalidation_level,
        "buffer_used": buffer
    }
```

### 3.3 Order Block Stop

```python
def calculate_ob_stop(
    fvg_direction: int,
    ob_top: float,
    ob_bottom: float,
    atr: float
) -> dict:
    """
    Stop beyond Order Block containing/near FVG.

    Used when FVG is inside or near OB.
    """
    if ob_top is None or ob_bottom is None:
        return None  # No OB available

    buffer = calculate_stop_buffer(atr, "ob_edge")

    if fvg_direction == 1:  # Bullish
        stop_price = ob_bottom - buffer
        invalidation_level = ob_bottom
    else:  # Bearish
        stop_price = ob_top + buffer
        invalidation_level = ob_top

    return {
        "stop_price": round(stop_price, 5),
        "stop_type": "ob_edge",
        "invalidation_level": invalidation_level,
        "buffer_used": buffer
    }
```

### 3.4 Structure Stop (Swing-based)

```python
def calculate_structure_stop(
    fvg_direction: int,
    recent_swing_high: float,
    recent_swing_low: float,
    atr: float
) -> dict:
    """
    Stop beyond recent swing structure.

    Most conservative option - used for weaker setups.
    """
    buffer = calculate_stop_buffer(atr, "structure")

    if fvg_direction == 1:  # Bullish - stop below swing low
        if recent_swing_low is None:
            return None
        stop_price = recent_swing_low - buffer
        invalidation_level = recent_swing_low
    else:  # Bearish - stop above swing high
        if recent_swing_high is None:
            return None
        stop_price = recent_swing_high + buffer
        invalidation_level = recent_swing_high

    return {
        "stop_price": round(stop_price, 5),
        "stop_type": "structure",
        "invalidation_level": invalidation_level,
        "buffer_used": buffer
    }
```

---

## 4. STOP SELECTION ENGINE

### 4.1 Main Selection Logic

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class StopPlacementResult:
    """Result of stop placement calculation."""
    stop_price: float
    stop_type: str                   # "fvg_edge", "fvg_full", "ob_edge", "structure"
    stop_distance: float             # Distance from entry to stop
    stop_distance_atr: float         # Stop distance in ATR terms
    invalidation_level: float        # The structure level being protected
    all_options: List[dict]          # All calculated stop options


def select_optimal_stop(
    fvg_direction: int,
    entry_price: float,
    fvg_top: float,
    fvg_bottom: float,
    ob_top: Optional[float],
    ob_bottom: Optional[float],
    recent_swing_high: Optional[float],
    recent_swing_low: Optional[float],
    fvg_strength_class: str,
    atr: float,
    max_stop_atr: float = 2.0,       # Max stop distance in ATR
    min_stop_atr: float = 0.3        # Min stop distance in ATR
) -> StopPlacementResult:
    """
    Select optimal stop placement based on FVG strength and available structure.

    Logic:
    1. Strong FVG → FVG edge stop (tightest)
    2. Medium FVG → FVG full stop or OB stop
    3. Weak FVG → Structure stop (widest)

    Constraints:
    - Stop must be between min_stop_atr and max_stop_atr
    - If too tight → widen to next option
    - If too wide → skip trade (return None)
    """

    all_options = []

    # Calculate all stop options
    fvg_edge = calculate_fvg_edge_stop(fvg_direction, fvg_top, fvg_bottom, atr)
    all_options.append(fvg_edge)

    fvg_full = calculate_fvg_full_stop(fvg_direction, fvg_top, fvg_bottom, atr)
    all_options.append(fvg_full)

    ob_stop = calculate_ob_stop(fvg_direction, ob_top, ob_bottom, atr)
    if ob_stop:
        all_options.append(ob_stop)

    structure_stop = calculate_structure_stop(
        fvg_direction, recent_swing_high, recent_swing_low, atr
    )
    if structure_stop:
        all_options.append(structure_stop)

    # Priority order based on FVG strength
    if fvg_strength_class == "Strong":
        priority = ["fvg_edge", "fvg_full", "ob_edge", "structure"]
    elif fvg_strength_class == "Medium":
        priority = ["fvg_full", "ob_edge", "fvg_edge", "structure"]
    else:  # Weak
        priority = ["ob_edge", "structure", "fvg_full", "fvg_edge"]

    # Select best valid stop
    for stop_type in priority:
        for option in all_options:
            if option["stop_type"] != stop_type:
                continue

            stop_distance = abs(entry_price - option["stop_price"])
            stop_distance_atr = stop_distance / atr if atr > 0 else float('inf')

            # Check constraints
            if stop_distance_atr < min_stop_atr:
                continue  # Too tight, try next option
            if stop_distance_atr > max_stop_atr:
                continue  # Too wide, try next option

            return StopPlacementResult(
                stop_price=option["stop_price"],
                stop_type=option["stop_type"],
                stop_distance=round(stop_distance, 5),
                stop_distance_atr=round(stop_distance_atr, 3),
                invalidation_level=option["invalidation_level"],
                all_options=all_options
            )

    # No valid stop found - return widest option if within max
    for option in sorted(all_options, key=lambda x: abs(entry_price - x["stop_price"]), reverse=True):
        stop_distance = abs(entry_price - option["stop_price"])
        stop_distance_atr = stop_distance / atr if atr > 0 else float('inf')

        if stop_distance_atr <= max_stop_atr:
            return StopPlacementResult(
                stop_price=option["stop_price"],
                stop_type=option["stop_type"],
                stop_distance=round(stop_distance, 5),
                stop_distance_atr=round(stop_distance_atr, 3),
                invalidation_level=option["invalidation_level"],
                all_options=all_options
            )

    # Trade invalid - stop would be too wide
    return None
```

### 4.2 Stop Distance Validation

```python
# Stop distance constraints
STOP_CONSTRAINTS = {
    "min_stop_atr": 0.3,    # Minimum 0.3 ATR (avoid too tight)
    "max_stop_atr": 2.0,    # Maximum 2.0 ATR (avoid too wide)
    "ideal_stop_atr": 0.8,  # Ideal stop distance
}

def validate_stop_distance(stop_distance_atr: float) -> tuple[bool, str]:
    """
    Validate if stop distance is acceptable.

    Returns:
        (is_valid, reason)
    """
    if stop_distance_atr < STOP_CONSTRAINTS["min_stop_atr"]:
        return False, "stop_too_tight"
    elif stop_distance_atr > STOP_CONSTRAINTS["max_stop_atr"]:
        return False, "stop_too_wide"
    else:
        return True, "valid"
```

---

## 5. OUTPUT FIELDS

### 5.1 EventState Fields (Python Layer 2)

```python
# === STOP PLACEMENT (Module #05) ===
stop_price: float                    # Calculated stop price
stop_type: str                       # "fvg_edge", "fvg_full", "ob_edge", "structure"
stop_distance: float                 # Distance from entry to stop (price)
stop_distance_atr: float             # Stop distance in ATR units
stop_invalidation_level: float       # The structure level stop protects
stop_buffer: float                   # Buffer added beyond invalidation

# Validation
stop_valid: bool                     # Is stop within acceptable range
stop_reason: str                     # If invalid, why ("too_tight", "too_wide")
```

### 5.2 Sample Output

```json
{
    "stop_price": 99.45,
    "stop_type": "fvg_edge",
    "stop_distance": 0.55,
    "stop_distance_atr": 0.73,
    "stop_invalidation_level": 99.50,
    "stop_buffer": 0.05,

    "stop_valid": true,
    "stop_reason": "valid"
}
```

---

## 6. INTEGRATION WITH RR CALCULATION

### 6.1 RR Validation

Stop placement trực tiếp ảnh hưởng đến RR:

```python
def calculate_risk_reward(
    entry_price: float,
    stop_price: float,
    target_price: float,
    fvg_direction: int
) -> dict:
    """
    Calculate risk-reward ratio.

    Returns:
        dict with RR ratio and validity
    """
    if fvg_direction == 1:  # Bullish
        risk = entry_price - stop_price
        reward = target_price - entry_price
    else:  # Bearish
        risk = stop_price - entry_price
        reward = entry_price - target_price

    rr_ratio = reward / risk if risk > 0 else 0

    return {
        "risk": round(risk, 5),
        "reward": round(reward, 5),
        "rr_ratio": round(rr_ratio, 2),
        "rr_valid": rr_ratio >= 1.5  # Minimum 1.5:1 RR
    }
```

---

## 7. NINJA EXPORT REQUIREMENTS

### 7.1 Fields Needed from Layer 1 (NinjaTrader)

Module này cần các fields sau từ NinjaTrader:

| Field | Type | Description |
|-------|------|-------------|
| `fvg_top` | float | FVG top price (đã có) |
| `fvg_bottom` | float | FVG bottom price (đã có) |
| `nearest_ob_top` | float | Nearest OB top (đã có) |
| `nearest_ob_bottom` | float | Nearest OB bottom (đã có) |
| `recent_swing_high` | float | Recent swing high price |
| `recent_swing_low` | float | Recent swing low price |

### 7.2 New Fields Required

```
# SWING DETECTION (for Structure Stop)
recent_swing_high: float       # Most recent swing high within lookback
recent_swing_low: float        # Most recent swing low within lookback
swing_lookback_bars: int       # Number of bars to look back (default: 20)
```

### 7.3 Computation Location

| Calculation | Location | Reason |
|-------------|----------|--------|
| FVG Edge Stop | Python | Simple calculation |
| OB Stop | Python | Needs OB data |
| Structure Stop | Python | Uses swing data from Ninja |
| Buffer | Python | ATR-based |
| **Stop Selection** | Python | Logic + validation |

---

## 8. UNIT TESTS

```python
def test_fvg_edge_stop_bullish():
    """Test FVG edge stop for bullish setup."""
    result = calculate_fvg_edge_stop(
        fvg_direction=1,
        fvg_top=100.50,
        fvg_bottom=100.00,
        atr=0.50
    )

    assert result["stop_type"] == "fvg_edge"
    assert result["stop_price"] < 100.00  # Below FVG bottom
    assert result["invalidation_level"] == 100.00


def test_fvg_edge_stop_bearish():
    """Test FVG edge stop for bearish setup."""
    result = calculate_fvg_edge_stop(
        fvg_direction=-1,
        fvg_top=100.50,
        fvg_bottom=100.00,
        atr=0.50
    )

    assert result["stop_type"] == "fvg_edge"
    assert result["stop_price"] > 100.50  # Above FVG top
    assert result["invalidation_level"] == 100.50


def test_stop_selection_strong_fvg():
    """Test stop selection prefers tight stop for strong FVG."""
    result = select_optimal_stop(
        fvg_direction=1,
        entry_price=100.20,
        fvg_top=100.50,
        fvg_bottom=100.00,
        ob_top=101.00,
        ob_bottom=99.50,
        recent_swing_high=101.50,
        recent_swing_low=99.00,
        fvg_strength_class="Strong",
        atr=0.50
    )

    assert result is not None
    assert result.stop_type == "fvg_edge"  # Tightest stop for strong FVG


def test_stop_selection_weak_fvg():
    """Test stop selection prefers wider stop for weak FVG."""
    result = select_optimal_stop(
        fvg_direction=1,
        entry_price=100.20,
        fvg_top=100.50,
        fvg_bottom=100.00,
        ob_top=101.00,
        ob_bottom=99.50,
        recent_swing_high=101.50,
        recent_swing_low=99.00,
        fvg_strength_class="Weak",
        atr=0.50
    )

    assert result is not None
    assert result.stop_type in ["ob_edge", "structure"]  # Wider stop for weak FVG


def test_stop_validation():
    """Test stop distance validation."""
    # Valid stop
    valid, reason = validate_stop_distance(0.8)
    assert valid is True
    assert reason == "valid"

    # Too tight
    valid, reason = validate_stop_distance(0.2)
    assert valid is False
    assert reason == "stop_too_tight"

    # Too wide
    valid, reason = validate_stop_distance(2.5)
    assert valid is False
    assert reason == "stop_too_wide"
```

---

## 9. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial spec - 4 stop methods with selection engine |

---

## 10. NOTES

### 10.1 Stop Hunt Protection
- Buffer được tính dựa trên ATR để tránh exact-level stops
- Structure stop có buffer lớn nhất vì swing levels thường bị hunt

### 10.2 Dynamic Stop (Future Enhancement)
- Trailing stop sau khi price move favorable
- Breakeven stop sau khi đạt 1:1 RR
- Partial take profit với stop adjustment

### 10.3 Market Condition Adjustment
- Volatile market → wider stops (tăng buffer)
- Quiet market → tighter stops (giảm buffer)
