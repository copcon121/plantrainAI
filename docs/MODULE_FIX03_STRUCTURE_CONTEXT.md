# 📊 MODULE FIX #03: STRUCTURE CONTEXT

**Module Name:** `fix03_structure_context.py`
**Version:** 1.0.0
**Purpose:** Tag FVG với context cấu trúc (Expansion/Retracement/Continuation)
**Status:** 📝 Specification Complete
**Priority:** 🟡 HIGH (Context for FVG quality)

---

## ⚠️ DESIGN DECISION: RENAME FROM "CHoCH FILTERS"

### Tại sao đổi tên?
- CHoCH/BOS riêng lẻ **KHÔNG** phải signal type
- CHoCH/BOS chỉ là **confirmation** của trend change
- Entry point thực tế vẫn là **FVG retest SAU CHoCH**
- Module này tag **CONTEXT** cho FVG, không scoring CHoCH

### Core Principle:
> "FVG nằm trong **expansion leg** (sau BOS/CHoCH) có probability cao hơn FVG trong **retracement leg**"

---

## 🎯 OBJECTIVES

### Primary Goals:
1. **Xác định Structure Context** - FVG thuộc expansion/retracement/continuation
2. **Tag Leg Type** - Impulsive vs Corrective
3. **Provide Context cho FVG Quality** - Không scoring riêng

### Expected Impact:
- FVG in expansion leg: +15-20% win rate bonus
- FVG in retracement leg: -10-15% win rate penalty
- Better filtering of low-probability setups

---

## 📊 STRUCTURE CONTEXT TYPES

### 1. EXPANSION (Impulsive Leg)

```
Definition: FVG được tạo trong leg phá structure (BOS/CHoCH)

Example (Bullish):
    HH ←── BOS break
    │
    │  ┌─────┐
    │  │ FVG │ ← FVG trong expansion leg
    │  └─────┘
    │
   HL

Characteristics:
- Leg mạnh, volume cao
- Institutional participation
- FVG thường được respect
- High probability retest

Context Score Multiplier: 1.2
```

### 2. RETRACEMENT (Corrective Leg)

```
Definition: FVG được tạo trong leg pullback (chưa phá structure)

Example (Bullish pullback):
    HH
    │
    │  ┌─────┐
    │  │ FVG │ ← FVG trong pullback
    │  └─────┘
    │
   HL (support)

Characteristics:
- Leg yếu hơn, volume thấp hơn
- Retail participation
- FVG có thể bị fill
- Lower probability

Context Score Multiplier: 0.8
```

### 3. CONTINUATION (Post-Confirmation)

```
Definition: FVG sau khi trend đã được confirm (HH-HL hoặc LH-LL established)

Example (Bullish continuation):
    HH2 ←── Trend confirmed (HH > HH1)
    │
    HL2
    │
    HH1
    │
   HL1
    │
    │  ┌─────┐
    │  │ FVG │ ← FVG trong continuation
    │  └─────┘

Characteristics:
- Trend đã establish
- "Joining the move" opportunity
- Medium-high probability

Context Score Multiplier: 1.0
```

---

## 📥 INPUT DATA REQUIREMENTS

### From Phase 1 Export (NinjaTrader):
```python
{
    # Structure detection
    "choch_detected": bool,
    "choch_type": str,              # "bullish" / "bearish"
    "choch_price": float,
    "choch_bars_ago": int,

    # Swing points
    "last_swing_high": float,
    "last_swing_low": float,
    "current_trend": str,           # "uptrend" / "downtrend" / "sideways"

    # BOS detection (nếu có)
    "bos_detected": bool,
    "bos_type": str,
    "bos_price": float,

    # Current bar
    "bar_index": int,
    "high": float,
    "low": float,
    "close": float
}
```

### From Other Modules:
```python
# From Module #2 (FVG Quality)
"fvg_detected": bool,
"fvg_type": str,
"fvg_creation_bar_index": int,
```

---

## 📤 OUTPUT DATA SPECIFICATION

### BarState Outputs (7 fields):

```python
{
    # === STRUCTURE CONTEXT ===
    "structure_context": str,           # "expansion" / "retracement" / "continuation" / "unclear"
    "structure_dir": int,               # 1 = bullish, -1 = bearish, 0 = unclear
    "structure_context_score": float,   # Multiplier: 0.8 / 1.0 / 1.2

    # === LEG ANALYSIS ===
    "fvg_in_impulsive_leg": bool,       # FVG trong leg mạnh (expansion)?
    "bars_since_structure_break": int,  # Bars since last BOS/CHoCH
    "structure_break_type": str,        # "BOS" / "CHoCH" / "None"

    # === TREND ESTABLISHMENT ===
    "trend_established": bool,          # HH-HL or LH-LL pattern complete?
}
```

---

## 🧮 CALCULATION LOGIC

### 1. Structure Context Detection

```python
def detect_structure_context(self, bar_state: dict, history: list) -> dict:
    """
    Determine if current bar/FVG is in expansion, retracement, or continuation.
    """
    # Get recent structure breaks
    recent_choch = self._find_recent_choch(history, lookback=50)
    recent_bos = self._find_recent_bos(history, lookback=50)

    # Get swing pattern
    swing_pattern = self._analyze_swing_pattern(history)

    current_bar = bar_state['bar_index']
    fvg_bar = bar_state.get('fvg_creation_bar_index', current_bar)

    # === EXPANSION DETECTION ===
    # FVG created within 10 bars of structure break
    if recent_choch and (fvg_bar - recent_choch['bar_index']) <= 10:
        # FVG is in the leg that broke structure
        if self._fvg_in_break_leg(bar_state, recent_choch, history):
            return {
                'structure_context': 'expansion',
                'structure_dir': 1 if recent_choch['type'] == 'bullish' else -1,
                'structure_context_score': 1.2,
                'fvg_in_impulsive_leg': True,
                'bars_since_structure_break': current_bar - recent_choch['bar_index'],
                'structure_break_type': 'CHoCH',
                'trend_established': False
            }

    if recent_bos and (fvg_bar - recent_bos['bar_index']) <= 10:
        if self._fvg_in_break_leg(bar_state, recent_bos, history):
            return {
                'structure_context': 'expansion',
                'structure_dir': 1 if recent_bos['type'] == 'bullish' else -1,
                'structure_context_score': 1.2,
                'fvg_in_impulsive_leg': True,
                'bars_since_structure_break': current_bar - recent_bos['bar_index'],
                'structure_break_type': 'BOS',
                'trend_established': True  # BOS confirms trend
            }

    # === CONTINUATION DETECTION ===
    # Trend established (HH-HL or LH-LL pattern)
    if swing_pattern['trend_established']:
        if self._fvg_aligns_with_trend(bar_state, swing_pattern):
            return {
                'structure_context': 'continuation',
                'structure_dir': swing_pattern['direction'],
                'structure_context_score': 1.0,
                'fvg_in_impulsive_leg': False,
                'bars_since_structure_break': swing_pattern.get('bars_since_confirmation', 0),
                'structure_break_type': 'None',
                'trend_established': True
            }

    # === RETRACEMENT DETECTION ===
    # FVG in pullback leg (counter to recent move)
    if self._is_in_pullback(bar_state, history):
        return {
            'structure_context': 'retracement',
            'structure_dir': swing_pattern.get('direction', 0),
            'structure_context_score': 0.8,
            'fvg_in_impulsive_leg': False,
            'bars_since_structure_break': 0,
            'structure_break_type': 'None',
            'trend_established': swing_pattern.get('trend_established', False)
        }

    # === UNCLEAR ===
    return {
        'structure_context': 'unclear',
        'structure_dir': 0,
        'structure_context_score': 0.7,
        'fvg_in_impulsive_leg': False,
        'bars_since_structure_break': 0,
        'structure_break_type': 'None',
        'trend_established': False
    }
```

### 2. Swing Pattern Analysis

```python
def _analyze_swing_pattern(self, history: list, lookback: int = 50) -> dict:
    """
    Analyze recent swing pattern to determine trend establishment.

    Bullish: HH > HH_prev AND HL > HL_prev
    Bearish: LH < LH_prev AND LL < LL_prev
    """
    swings = self._extract_swings(history[-lookback:])

    if len(swings['highs']) < 2 or len(swings['lows']) < 2:
        return {'trend_established': False, 'direction': 0}

    # Get last 2 swing highs and lows
    hh1, hh2 = swings['highs'][-2], swings['highs'][-1]
    hl1, hl2 = swings['lows'][-2], swings['lows'][-1]

    # Bullish: Higher Highs + Higher Lows
    if hh2['price'] > hh1['price'] and hl2['price'] > hl1['price']:
        return {
            'trend_established': True,
            'direction': 1,
            'pattern': 'HH-HL',
            'bars_since_confirmation': history[-1]['bar_index'] - hh2['bar_index']
        }

    # Bearish: Lower Highs + Lower Lows
    lh1, lh2 = swings['highs'][-2], swings['highs'][-1]
    ll1, ll2 = swings['lows'][-2], swings['lows'][-1]

    if lh2['price'] < lh1['price'] and ll2['price'] < ll1['price']:
        return {
            'trend_established': True,
            'direction': -1,
            'pattern': 'LH-LL',
            'bars_since_confirmation': history[-1]['bar_index'] - ll2['bar_index']
        }

    return {'trend_established': False, 'direction': 0}
```

### 3. FVG in Break Leg Detection

```python
def _fvg_in_break_leg(self, bar_state: dict, structure_break: dict, history: list) -> bool:
    """
    Check if FVG was created in the same leg that broke structure.

    Logic:
    - FVG created AFTER structure break starts
    - FVG created BEFORE or AT structure break completion
    - FVG direction matches break direction
    """
    fvg_bar = bar_state.get('fvg_creation_bar_index')
    fvg_type = bar_state.get('fvg_type')
    break_bar = structure_break['bar_index']
    break_type = structure_break['type']

    # FVG must be created within the break leg (before completion)
    # Typically within 5-10 bars before the break
    leg_start = break_bar - 10
    leg_end = break_bar + 2  # Small buffer after break

    if not (leg_start <= fvg_bar <= leg_end):
        return False

    # FVG direction must match break direction
    if break_type == 'bullish' and fvg_type != 'bullish':
        return False
    if break_type == 'bearish' and fvg_type != 'bearish':
        return False

    return True
```

### 4. Pullback Detection

```python
def _is_in_pullback(self, bar_state: dict, history: list) -> bool:
    """
    Detect if current price action is in a pullback/retracement.

    Pullback characteristics:
    - Price moving against recent trend
    - Lower volume than impulse
    - Smaller candles
    """
    recent_bars = history[-20:]

    # Find recent impulse direction
    impulse_dir = self._detect_impulse_direction(recent_bars[:10])
    current_dir = self._detect_current_direction(recent_bars[-5:])

    # Pullback = current direction opposite to impulse
    if impulse_dir != 0 and current_dir == -impulse_dir:
        # Verify with volume (pullback should have lower volume)
        impulse_vol = sum(b['volume'] for b in recent_bars[:10]) / 10
        pullback_vol = sum(b['volume'] for b in recent_bars[-5:]) / 5

        if pullback_vol < impulse_vol * 0.8:  # 80% or less volume
            return True

    return False
```

---

## 🐍 MODULE CLASS STRUCTURE

```python
# processor/modules/fix03_structure_context.py

from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class StructureBreak:
    """Represents a BOS or CHoCH event."""
    bar_index: int
    break_type: str  # "BOS" or "CHoCH"
    direction: str   # "bullish" or "bearish"
    price: float

@dataclass
class SwingPoint:
    """Represents a swing high or low."""
    bar_index: int
    price: float
    swing_type: str  # "high" or "low"

class StructureContextModule:
    """
    Module Fix #03: Structure Context Analysis.

    Purpose: Tag FVG với context cấu trúc để improve quality assessment.

    NOT for:
    - Scoring CHoCH independently
    - Creating CHoCH-based signals

    FOR:
    - Providing context multiplier for FVG quality
    - Identifying expansion vs retracement legs
    """

    def __init__(self, config: dict = None):
        self.config = config or self._default_config()
        self.structure_history: List[StructureBreak] = []
        self.swing_history: List[SwingPoint] = []

    def _default_config(self) -> dict:
        return {
            # Lookback periods
            'structure_lookback': 50,
            'swing_lookback': 30,

            # Expansion leg parameters
            'expansion_max_bars': 10,  # Max bars from break to still be "expansion"

            # Context score multipliers
            'expansion_multiplier': 1.2,
            'continuation_multiplier': 1.0,
            'retracement_multiplier': 0.8,
            'unclear_multiplier': 0.7,

            # Pullback detection
            'pullback_volume_ratio': 0.8,  # Pullback vol < 80% impulse vol
        }

    def process_bar(self, bar_state: dict, bar_history: list) -> dict:
        """
        Main processing function - adds structure context fields to bar_state.
        """
        # Update internal tracking
        self._update_structure_history(bar_state)
        self._update_swing_history(bar_state)

        # Only process if FVG detected (context is for FVG)
        if not bar_state.get('fvg_detected'):
            return {
                **bar_state,
                'structure_context': 'none',
                'structure_dir': 0,
                'structure_context_score': 1.0,
                'fvg_in_impulsive_leg': False,
                'bars_since_structure_break': 0,
                'structure_break_type': 'None',
                'trend_established': False
            }

        # Detect context
        context = self.detect_structure_context(bar_state, bar_history)

        return {**bar_state, **context}

    # ... (implement helper methods from above)
```

---

## ✅ SUCCESS CRITERIA

### Statistical Validation:

| Context Type | Expected Win Rate | Sample Size |
|--------------|-------------------|-------------|
| Expansion | ≥ 45% | Min 200 events |
| Continuation | ≥ 38% | Min 300 events |
| Retracement | ≤ 32% | Min 200 events |
| Unclear | ≤ 28% | - |

### Correlation Targets:
- Context type should correlate with outcome (r > 0.3)
- Expansion FVGs should have higher RR outcomes

---

## 🧪 UNIT TESTS

```python
def test_expansion_detection():
    """Test FVG in expansion leg detection."""
    module = StructureContextModule()

    # Setup: CHoCH bullish at bar 100, FVG bullish at bar 103
    bar_state = {
        'fvg_detected': True,
        'fvg_type': 'bullish',
        'fvg_creation_bar_index': 103,
        'bar_index': 105
    }

    history = [
        # ... bars leading up to CHoCH
        {'bar_index': 100, 'choch_detected': True, 'choch_type': 'bullish'},
        # ... bars after
    ]

    result = module.process_bar(bar_state, history)

    assert result['structure_context'] == 'expansion'
    assert result['structure_dir'] == 1
    assert result['fvg_in_impulsive_leg'] == True
    assert result['structure_context_score'] == 1.2

def test_retracement_detection():
    """Test FVG in retracement detection."""
    module = StructureContextModule()

    # Setup: Uptrend established, FVG bearish in pullback
    bar_state = {
        'fvg_detected': True,
        'fvg_type': 'bearish',  # Counter-trend FVG
        'fvg_creation_bar_index': 150,
        'bar_index': 152
    }

    result = module.process_bar(bar_state, history_with_uptrend)

    assert result['structure_context'] == 'retracement'
    assert result['structure_context_score'] == 0.8
    assert result['fvg_in_impulsive_leg'] == False
```

---

## 📝 INTEGRATION NOTES

### Module Dependencies:
```
Module #2 (FVG Quality) → Provides FVG detection
        ↓
Module #3 (Structure Context) ← THIS MODULE
        ↓
Module #4 (Confluence) → Uses context score as multiplier
```

### Usage in Confluence:
```python
# In Module #4 (Confluence)
def calculate_confluence(self, event_data):
    # Get structure context multiplier
    struct_mult = event_data.get('structure_context_score', 1.0)

    # Apply to base FVG score
    adjusted_score = event_data['fvg_strength_score'] * struct_mult
    # ...
```

---

**Last Updated:** November 21, 2025
**Version:** 1.0.0
**Status:** 📝 Specification Complete
