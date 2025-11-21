# MODULE #06: TARGET PLACEMENT (SIMPLIFIED)

## VERSION: 1.0
## STATUS: New Spec (Simplified from Dynamic TP)
## PRIORITY: HIGH (Risk Management Core)

---

## 1. MODULE OVERVIEW

### 1.1 Mục Đích
Tính **Take Profit placement** đơn giản và hiệu quả cho FVG signal:
- **TP1**: Nearest structure (swing/liquidity) - conservative target
- **TP2**: Fixed 3x Risk-Reward - extended target

### 1.2 Nguyên Lý SMC (Simplified)
> "Take profit at logical levels - nearest structure for safety, extended target for runners"

**Simplified Approach:**
- TP1 = First structure barrier (swing high/low, liquidity pool)
- TP2 = Fixed RR multiple (3x risk)
- Không cần complex dynamic TP trong v1.0

### 1.3 Vị Trí Trong Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     TARGET PLACEMENT FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Entry Price] + [Stop Price] + [Structure Data]                │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              TARGET CALCULATION                     │       │
│  │                                                     │       │
│  │  TP1 = Nearest structure (swing/liquidity)         │       │
│  │       └─ Within direction of trade                  │       │
│  │       └─ First barrier to price                     │       │
│  │                                                     │       │
│  │  TP2 = Entry + (3 × Risk)                          │       │
│  │       └─ Fixed RR for runners                       │       │
│  │                                                     │       │
│  └─────────────────────────────────────────────────────┘       │
│       │                                                         │
│       ▼                                                         │
│  [TP1, TP2, RR_TP1, RR_TP2]                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. TARGET CALCULATION

### 2.1 TP1: Nearest Structure

```python
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class StructureLevel:
    """A structure level that could act as TP."""
    price: float
    level_type: str      # "swing", "liquidity", "ob_edge"
    distance: float      # Distance from entry
    distance_atr: float  # Distance in ATR


def find_tp1_nearest_structure(
    fvg_direction: int,
    entry_price: float,
    recent_swing_high: Optional[float],
    recent_swing_low: Optional[float],
    nearest_liquidity_high: Optional[float],
    nearest_liquidity_low: Optional[float],
    opposite_ob_edge: Optional[float],
    atr: float,
    min_tp_atr: float = 0.5,     # Minimum TP distance
    max_tp1_atr: float = 3.0      # Maximum TP1 distance
) -> Optional[StructureLevel]:
    """
    Find nearest structure level for TP1.

    For Bullish: Look for resistance above entry
    For Bearish: Look for support below entry

    Returns:
        StructureLevel for TP1, or None if no valid level found
    """
    candidates = []

    if fvg_direction == 1:  # Bullish - find resistance above
        if recent_swing_high and recent_swing_high > entry_price:
            candidates.append(StructureLevel(
                price=recent_swing_high,
                level_type="swing",
                distance=recent_swing_high - entry_price,
                distance_atr=(recent_swing_high - entry_price) / atr if atr > 0 else 0
            ))

        if nearest_liquidity_high and nearest_liquidity_high > entry_price:
            candidates.append(StructureLevel(
                price=nearest_liquidity_high,
                level_type="liquidity",
                distance=nearest_liquidity_high - entry_price,
                distance_atr=(nearest_liquidity_high - entry_price) / atr if atr > 0 else 0
            ))

        if opposite_ob_edge and opposite_ob_edge > entry_price:
            candidates.append(StructureLevel(
                price=opposite_ob_edge,
                level_type="ob_edge",
                distance=opposite_ob_edge - entry_price,
                distance_atr=(opposite_ob_edge - entry_price) / atr if atr > 0 else 0
            ))

    else:  # Bearish - find support below
        if recent_swing_low and recent_swing_low < entry_price:
            candidates.append(StructureLevel(
                price=recent_swing_low,
                level_type="swing",
                distance=entry_price - recent_swing_low,
                distance_atr=(entry_price - recent_swing_low) / atr if atr > 0 else 0
            ))

        if nearest_liquidity_low and nearest_liquidity_low < entry_price:
            candidates.append(StructureLevel(
                price=nearest_liquidity_low,
                level_type="liquidity",
                distance=entry_price - nearest_liquidity_low,
                distance_atr=(entry_price - nearest_liquidity_low) / atr if atr > 0 else 0
            ))

        if opposite_ob_edge and opposite_ob_edge < entry_price:
            candidates.append(StructureLevel(
                price=opposite_ob_edge,
                level_type="ob_edge",
                distance=entry_price - opposite_ob_edge,
                distance_atr=(entry_price - opposite_ob_edge) / atr if atr > 0 else 0
            ))

    # Filter by distance constraints
    valid_candidates = [
        c for c in candidates
        if min_tp_atr <= c.distance_atr <= max_tp1_atr
    ]

    if not valid_candidates:
        return None

    # Return nearest valid structure
    return min(valid_candidates, key=lambda x: x.distance)
```

### 2.2 TP2: Fixed 3x RR

```python
def calculate_tp2_fixed_rr(
    fvg_direction: int,
    entry_price: float,
    stop_price: float,
    rr_multiple: float = 3.0
) -> dict:
    """
    Calculate TP2 as fixed RR multiple.

    Args:
        fvg_direction: 1 = bullish, -1 = bearish
        entry_price: Entry price
        stop_price: Stop loss price
        rr_multiple: RR multiple (default 3.0)

    Returns:
        dict with TP2 price and RR info
    """
    risk = abs(entry_price - stop_price)
    reward = risk * rr_multiple

    if fvg_direction == 1:  # Bullish
        tp2_price = entry_price + reward
    else:  # Bearish
        tp2_price = entry_price - reward

    return {
        "tp2_price": round(tp2_price, 5),
        "tp2_rr": rr_multiple,
        "tp2_reward": round(reward, 5),
        "tp2_type": "fixed_rr"
    }
```

---

## 3. TARGET PLACEMENT ENGINE

### 3.1 Main Calculation

```python
@dataclass
class TargetPlacementResult:
    """Result of target placement calculation."""
    # TP1 - Nearest Structure
    tp1_price: Optional[float]
    tp1_type: Optional[str]          # "swing", "liquidity", "ob_edge", None
    tp1_distance: Optional[float]
    tp1_distance_atr: Optional[float]
    tp1_rr: Optional[float]

    # TP2 - Fixed RR
    tp2_price: float
    tp2_type: str                    # "fixed_rr"
    tp2_distance: float
    tp2_distance_atr: float
    tp2_rr: float

    # Validity
    has_valid_tp1: bool
    has_valid_tp2: bool


def calculate_target_placement(
    fvg_direction: int,
    entry_price: float,
    stop_price: float,
    recent_swing_high: Optional[float],
    recent_swing_low: Optional[float],
    nearest_liquidity_high: Optional[float],
    nearest_liquidity_low: Optional[float],
    opposite_ob_edge: Optional[float],
    atr: float,
    tp2_rr_multiple: float = 3.0
) -> TargetPlacementResult:
    """
    Calculate both TP1 (structure) and TP2 (fixed RR).

    Returns:
        TargetPlacementResult with both targets
    """
    risk = abs(entry_price - stop_price)

    # Calculate TP1 - Nearest Structure
    tp1 = find_tp1_nearest_structure(
        fvg_direction=fvg_direction,
        entry_price=entry_price,
        recent_swing_high=recent_swing_high,
        recent_swing_low=recent_swing_low,
        nearest_liquidity_high=nearest_liquidity_high,
        nearest_liquidity_low=nearest_liquidity_low,
        opposite_ob_edge=opposite_ob_edge,
        atr=atr
    )

    # Calculate TP2 - Fixed RR
    tp2 = calculate_tp2_fixed_rr(
        fvg_direction=fvg_direction,
        entry_price=entry_price,
        stop_price=stop_price,
        rr_multiple=tp2_rr_multiple
    )

    # Build result
    if tp1:
        tp1_rr = tp1.distance / risk if risk > 0 else 0
        return TargetPlacementResult(
            # TP1
            tp1_price=tp1.price,
            tp1_type=tp1.level_type,
            tp1_distance=round(tp1.distance, 5),
            tp1_distance_atr=round(tp1.distance_atr, 3),
            tp1_rr=round(tp1_rr, 2),

            # TP2
            tp2_price=tp2["tp2_price"],
            tp2_type=tp2["tp2_type"],
            tp2_distance=tp2["tp2_reward"],
            tp2_distance_atr=round(tp2["tp2_reward"] / atr, 3) if atr > 0 else 0,
            tp2_rr=tp2["tp2_rr"],

            # Validity
            has_valid_tp1=True,
            has_valid_tp2=True
        )
    else:
        # No valid TP1, only TP2
        return TargetPlacementResult(
            # TP1 - None
            tp1_price=None,
            tp1_type=None,
            tp1_distance=None,
            tp1_distance_atr=None,
            tp1_rr=None,

            # TP2
            tp2_price=tp2["tp2_price"],
            tp2_type=tp2["tp2_type"],
            tp2_distance=tp2["tp2_reward"],
            tp2_distance_atr=round(tp2["tp2_reward"] / atr, 3) if atr > 0 else 0,
            tp2_rr=tp2["tp2_rr"],

            # Validity
            has_valid_tp1=False,
            has_valid_tp2=True
        )
```

---

## 4. POSITION MANAGEMENT STRATEGY

### 4.1 Two-Target Exit Strategy

```
Trade với 2 TPs:

┌─────────────────────────────────────────────────────────────┐
│  TP2 (3x RR)  ←─────────────────────────────── 50% position │
│       │                                                     │
│       │   (runner với breakeven stop)                       │
│       │                                                     │
│  TP1 (structure) ←─────────────────────────── 50% position  │
│       │                                                     │
│       │   (conservative exit)                               │
│       │                                                     │
│  Entry ────────────────────────────────────────────────────│
│       │                                                     │
│       │                                                     │
│  Stop ─────────────────────────────────────── 100% risk     │
└─────────────────────────────────────────────────────────────┘

Position Management:
1. Enter full position
2. At TP1: Exit 50%, move stop to breakeven
3. At TP2: Exit remaining 50%
4. If price reverses after TP1: Exit at breakeven (0 loss on runner)
```

### 4.2 Expected Value Calculation

```python
def calculate_expected_value(
    tp1_rr: float,
    tp2_rr: float,
    tp1_hit_probability: float = 0.6,  # Higher probability for conservative target
    tp2_hit_probability: float = 0.3   # Lower probability for extended target
) -> dict:
    """
    Calculate expected value of the two-target strategy.

    Assumptions:
    - 50% position at each target
    - TP1 has higher hit rate than TP2
    - After TP1 hit, stop moves to breakeven

    Returns:
        dict with expected values
    """
    # Scenario outcomes
    # A: Both TPs hit → 0.5 * TP1_RR + 0.5 * TP2_RR
    # B: Only TP1 hit, runner stopped at BE → 0.5 * TP1_RR + 0
    # C: Stop hit → -1.0

    # Simplified calculation
    ev_tp1 = tp1_hit_probability * (0.5 * tp1_rr)
    ev_tp2 = tp2_hit_probability * (0.5 * tp2_rr)
    ev_loss = (1 - tp1_hit_probability) * (-1.0)

    total_ev = ev_tp1 + ev_tp2 + ev_loss

    return {
        "ev_tp1_contribution": round(ev_tp1, 3),
        "ev_tp2_contribution": round(ev_tp2, 3),
        "ev_loss": round(ev_loss, 3),
        "total_expected_value": round(total_ev, 3),
        "is_positive_ev": total_ev > 0
    }
```

---

## 5. OUTPUT FIELDS

### 5.1 EventState Fields (Python Layer 2)

```python
# === TARGET PLACEMENT (Module #06) ===

# TP1 - Nearest Structure
tp1_price: Optional[float]           # TP1 price
tp1_type: Optional[str]              # "swing", "liquidity", "ob_edge"
tp1_distance: Optional[float]        # Distance from entry
tp1_distance_atr: Optional[float]    # Distance in ATR
tp1_rr: Optional[float]              # RR at TP1

# TP2 - Fixed RR
tp2_price: float                     # TP2 price (always calculated)
tp2_type: str                        # "fixed_rr"
tp2_distance: float                  # Distance from entry
tp2_distance_atr: float              # Distance in ATR
tp2_rr: float                        # RR at TP2 (default 3.0)

# Validity
has_valid_tp1: bool                  # Is TP1 available
has_valid_tp2: bool                  # Is TP2 valid (always True)
```

### 5.2 Sample Output

```json
{
    "tp1_price": 101.50,
    "tp1_type": "swing",
    "tp1_distance": 1.30,
    "tp1_distance_atr": 1.73,
    "tp1_rr": 1.86,

    "tp2_price": 102.30,
    "tp2_type": "fixed_rr",
    "tp2_distance": 2.10,
    "tp2_distance_atr": 2.80,
    "tp2_rr": 3.0,

    "has_valid_tp1": true,
    "has_valid_tp2": true
}
```

---

## 6. NINJA EXPORT REQUIREMENTS

### 6.1 Fields Needed from Layer 1 (NinjaTrader)

| Field | Type | Description |
|-------|------|-------------|
| `recent_swing_high` | float | Recent swing high (from Module #05) |
| `recent_swing_low` | float | Recent swing low (from Module #05) |
| `nearest_liquidity_high` | float | Nearest untested high liquidity |
| `nearest_liquidity_low` | float | Nearest untested low liquidity |

### 6.2 Fields from Other Modules

| Field | Source | Description |
|-------|--------|-------------|
| `entry_price` | Module #02 | Entry price (adaptive) |
| `stop_price` | Module #05 | Stop loss price |
| `fvg_direction` | BarState | 1 = bullish, -1 = bearish |

### 6.3 Computation Location

| Calculation | Location | Reason |
|-------------|----------|--------|
| TP1 Structure | Python | Needs structure comparison |
| TP2 Fixed RR | Python | Simple calculation from stop |
| RR Calculation | Python | Entry/Stop/TP math |

---

## 7. UNIT TESTS

```python
def test_tp1_bullish_swing():
    """Test TP1 finds nearest swing high for bullish."""
    tp1 = find_tp1_nearest_structure(
        fvg_direction=1,
        entry_price=100.0,
        recent_swing_high=101.5,
        recent_swing_low=99.0,
        nearest_liquidity_high=102.0,
        nearest_liquidity_low=98.5,
        opposite_ob_edge=101.8,
        atr=0.75
    )

    assert tp1 is not None
    assert tp1.price == 101.5  # Nearest structure above entry
    assert tp1.level_type == "swing"


def test_tp2_fixed_rr():
    """Test TP2 calculates correct 3x RR."""
    tp2 = calculate_tp2_fixed_rr(
        fvg_direction=1,
        entry_price=100.0,
        stop_price=99.3,  # 0.7 risk
        rr_multiple=3.0
    )

    assert tp2["tp2_price"] == 102.1  # 100 + (0.7 * 3)
    assert tp2["tp2_rr"] == 3.0


def test_full_target_placement():
    """Test complete target placement calculation."""
    result = calculate_target_placement(
        fvg_direction=1,
        entry_price=100.0,
        stop_price=99.3,
        recent_swing_high=101.2,
        recent_swing_low=99.0,
        nearest_liquidity_high=102.0,
        nearest_liquidity_low=98.5,
        opposite_ob_edge=None,
        atr=0.75
    )

    assert result.has_valid_tp1 is True
    assert result.tp1_price == 101.2
    assert result.tp1_rr < result.tp2_rr  # TP1 should have lower RR
    assert result.tp2_rr == 3.0


def test_no_tp1_available():
    """Test when no structure available for TP1."""
    result = calculate_target_placement(
        fvg_direction=1,
        entry_price=100.0,
        stop_price=99.3,
        recent_swing_high=None,  # No swing high
        recent_swing_low=None,
        nearest_liquidity_high=None,  # No liquidity
        nearest_liquidity_low=None,
        opposite_ob_edge=None,
        atr=0.75
    )

    assert result.has_valid_tp1 is False
    assert result.tp1_price is None
    assert result.has_valid_tp2 is True  # TP2 always available
    assert result.tp2_rr == 3.0
```

---

## 8. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial simplified spec - TP1 structure + TP2 fixed RR |

---

## 9. NOTES

### 9.1 Why Simplified?
- v1.0 focus on simplicity và reliability
- Dynamic TP phức tạp, dễ overfit
- Fixed RR dễ backtest và optimize
- Structure-based TP1 có SMC logic rõ ràng

### 9.2 Future Enhancements (v2.0)
- Trailing TP based on structure breaks
- Dynamic RR based on confluence score
- Partial profit at multiple levels
- Time-based exit rules

### 9.3 Position Sizing Integration
Target placement ảnh hưởng đến position sizing:
- Higher TP1 probability → có thể size lớn hơn
- No TP1 (only TP2) → size conservative hơn
