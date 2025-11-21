# 📊 MODULE FIX #02: FVG QUALITY SCORING & CLASSIFICATION (EXPANDED)

**Module Name:** `fix02_fvg_quality.py`
**Version:** 2.0.0 (Major Expansion)
**Purpose:** Comprehensive FVG quality assessment including Strength, Retest Geometry, and Adaptive Entry
**Status:** 🟡 Specification Complete - Awaiting Implementation
**Priority:** 🔴 CRITICAL (Core signal quality module)

---

## ⚠️ CRITICAL DESIGN DECISIONS (Nov 2025)

### 1. FVG is the ONLY Signal Type
- **FVG retest is the ONLY signal type** for ML training
- **OB retest is NOT a separate signal** - OB provides **context features** for FVG
- Model learns: FVG → long/short/skip

### 2. This Module is the "Brain" of Signal Quality
- All FVG-related quality assessment happens here
- Integrates with Module #1 (OB Context), #9 (VP), #11 (Liquidity)
- Output directly determines signal filtering

---

## 🎯 OBJECTIVES

### Primary Goals:
1. **FVG Strength Classification** - Strong/Medium/Weak based on imbalance characteristics
2. **Retest Geometry Analysis** - Penetration ratio, touch type, front-run detection
3. **Rebalance Detection** - FVG mới lấp FVG cũ (institutional footprint)
4. **Adaptive Entry Logic** - Buffer/entry based on FVG strength
5. **Value Class Assignment** - A/B/C for filtering

### Expected Impact:
- Filter out 60-70% of low-quality FVG setups
- Improve win rate from 22.7% → 35-45%
- Provide model with rich features for learning entry quality

---

## 📊 THE 4 COMPONENTS OF FVG QUALITY

### Component 1: FVG STRENGTH (Imbalance Quality)

**Purpose:** Measure how "strong" the imbalance is that created the FVG

**Factors:**
| Factor | Description | Strong | Medium | Weak |
|--------|-------------|--------|--------|------|
| Gap Size | FVG size / ATR | ≥ 1.5 | 0.8 - 1.5 | < 0.8 |
| Volume | Volume / Median_20 | ≥ 2.0x | 1.3 - 2.0x | < 1.3x |
| Delta Ratio | \|delta\| / volume | ≥ 0.6 | 0.4 - 0.6 | < 0.4 |
| Delta Alignment | Delta matches FVG direction | Yes | Partial | No |
| Rebalance | Fills previous FVG | Yes (bonus) | - | - |

**Strength Classes:**
- **Strong (A):** Institutional footprint, high conviction setup
- **Medium (B):** Acceptable setup with moderate conviction
- **Weak (C):** Noise, likely to fill quickly - SKIP

---

### Component 2: RETEST GEOMETRY (Entry Quality)

**Purpose:** Evaluate how price interacts with FVG zone during retest

**Key Metrics:**
| Metric | Description | Best | Acceptable | Poor |
|--------|-------------|------|------------|------|
| Penetration Ratio | How deep into FVG (0-1+) | 0 - 0.2 | 0.2 - 0.5 | > 0.5 |
| Touch Type | Classification of interaction | edge | shallow | deep/break |
| Front-run Distance | Distance before touch (ATR) | < 0.3 ATR | 0.3 - 0.5 ATR | > 0.5 ATR |

**Touch Types:**
```
no_touch  : Price hasn't reached FVG yet (front-run zone)
edge      : Price touched edge, minimal penetration (≤20%)
shallow   : Moderate penetration (20-50%)
deep      : Deep penetration (50-100%) - RISKY
break     : Broke through FVG (>100%) - INVALID
```

**Critical Rule (20 years experience):**
> "Xiên qua 50% vùng FVG = tín hiệu xấu, không nên trade"
> "Chạm mép hoặc shallow penetration + Strong FVG = high quality setup"

---

### Component 3: REBALANCE DETECTION (Institutional Footprint)

**Purpose:** Detect when new FVG fills/rebalances a previous FVG

**Why Important:**
- FVG mới lấp FVG cũ = price đang "dọn dẹp" imbalance
- Institutional behavior: fill old inefficiency before creating new move
- Clean rebalance + new FVG = very strong setup

**Detection Logic:**
```
FVG_old exists (unfilled) at price range [A, B]
FVG_new forms with leg passing through [A, B]
→ FVG_new rebalances FVG_old
→ fvg_rebalances_prev = True
→ fvg_rebalance_ratio = % of FVG_old that got filled
```

---

### Component 4: ADAPTIVE ENTRY (Dynamic Buffer)

**Purpose:** Calculate entry price with buffer based on FVG strength

**Logic:**
| FVG Strength | Buffer Size | Allow Front-run | Max Penetration |
|--------------|-------------|-----------------|-----------------|
| Strong | 10% of FVG or 0.2 ATR | Yes | 50% |
| Medium | 20% of FVG or 0.3 ATR | No | 40% |
| Weak | 30% of FVG or 0.4 ATR | No | 30% |

**Entry Types:**
- `entry_ideal`: At FVG edge (best RR, highest risk)
- `entry_50pct`: At 50% of FVG (balanced)
- `entry_with_buffer`: With adaptive buffer (safest, lower RR)

---

## 📥 INPUT DATA REQUIREMENTS

### From Phase 1 Export (NinjaTrader):
```python
{
    # FVG Detection (raw)
    "fvg_detected": true,
    "fvg_type": "bullish",           # "bullish" / "bearish"
    "fvg_high": 1.23550,             # Top of FVG zone
    "fvg_low": 1.23520,              # Bottom of FVG zone
    "fvg_gap_size": 0.00030,         # fvg_high - fvg_low
    "fvg_left_bar_index": 1234,      # Bar before gap
    "fvg_right_bar_index": 1236,     # Bar after gap

    # Volume & Delta
    "volume": 1250,
    "buy_volume": 750,
    "sell_volume": 500,
    "delta": 250,                    # buy_volume - sell_volume
    "volume_sma_20": 1100.5,

    # Context
    "atr_14": 0.00025,
    "session_name": "London",

    # OHLCV (for retest detection)
    "open": 1.23450,
    "high": 1.23500,
    "low": 1.23400,
    "close": 1.23480
}
```

### From Other Modules:
```python
# From Module #9 (Volume Profile)
"vp_session_vah": 1.23650,
"vp_session_val": 1.23400,
"vp_in_value_area": 1,

# From Module #11 (Liquidity Map)
"liquidity_sweep_detected": true,
"bars_since_sweep": 5,
"sweep_type": "liquidity_below",

# From Module #1 (OB Quality) - as context
"ob_strength_score": 0.85,
"has_ob_in_leg": true,
"ob_overlap_ratio": 0.7
```

---

## 📤 OUTPUT DATA SPECIFICATION

### A. BarState Outputs (Per-Bar FVG Quality) - 24 Fields

```python
{
    # === 1. BASIC CLASSIFICATION (existing, keep) ===
    "fvg_in_va_flag": 0,                    # 1 if inside VA, 0 if outside
    "fvg_breakout_va_flag": 1,              # 1 if breakout VA pattern
    "fvg_after_sweep_flag": 0,              # 1 if after sweep pattern
    "fvg_value_class": "A",                 # "A" / "B" / "C" / "None"

    # === 2. FVG STRENGTH (NEW - 8 fields) ===
    "fvg_size_atr": 1.8,                    # gap_size / ATR (1.5+ = strong)
    "fvg_vol_ratio": 2.3,                   # volume / median_20 (2.0+ = strong)
    "fvg_delta_ratio": 0.65,                # |delta| / volume (0.6+ = strong)
    "fvg_delta_alignment": 1,               # 1 = aligned, -1 = opposite, 0 = neutral
    "fvg_strength_score": 0.88,             # 0-1 composite strength
    "fvg_strength_class": "Strong",         # "Strong" / "Medium" / "Weak"
    "fvg_creation_bar_index": 1235,         # Bar where FVG was created
    "fvg_age_bars": 15,                     # Bars since FVG creation

    # === 3. REBALANCE DETECTION (NEW - 5 fields) ===
    "fvg_rebalances_prev": true,            # Does this FVG fill a previous FVG?
    "fvg_rebalance_ratio": 0.85,            # % of previous FVG filled (0-1)
    "fvg_is_clean_rebalance": true,         # Filled completely (>80%)?
    "prev_fvg_direction": "bearish",        # Direction of filled FVG
    "prev_fvg_age_bars": 45,                # How old was the filled FVG?

    # === 4. COMPONENT SCORES (NEW - 3 fields) ===
    "fvg_gap_quality_score": 0.85,          # Gap size component (0-1)
    "fvg_volume_quality_score": 0.72,       # Volume component (0-1)
    "fvg_imbalance_quality_score": 0.78,    # Delta imbalance component (0-1)

    # === 5. COMPOSITE & CONTEXT (existing + new) ===
    "fvg_quality_score": 0.82,              # 0-1 final composite
    "fvg_context": "breakout_va_strong_rebalance"  # Descriptive context string
}
```

### B. EventState Outputs (Per-Retest Event) - 18 FVG-specific Fields

```python
{
    # === SIGNAL TYPE (FVG ONLY) ===
    "signal_type": "fvg_retest_bull",       # "fvg_retest_bull" / "fvg_retest_bear"
    "direction": 1,                          # 1 = long, -1 = short

    # === FVG QUALITY (from BarState) ===
    "fvg_quality_score": 0.82,
    "fvg_value_class": "A",
    "fvg_strength_score": 0.88,
    "fvg_strength_class": "Strong",
    "fvg_rebalances_prev": true,
    "fvg_is_clean_rebalance": true,

    # === RETEST GEOMETRY (NEW - 6 fields) ===
    "fvg_retest_type": "edge",              # "no_touch"/"edge"/"shallow"/"deep"/"break"
    "fvg_penetration_ratio": 0.15,          # 0 = edge, 0.5 = mid, 1.0+ = through
    "fvg_min_distance_to_edge": 0.0,        # Closest approach to FVG (ATR units)
    "fvg_front_run_distance": 0.0,          # If no_touch, distance from edge (ATR)
    "fvg_retest_bar_index": 1250,           # Bar where retest occurred
    "fvg_retest_quality_score": 0.90,       # 0-1 retest quality

    # === ADAPTIVE ENTRY (NEW - 6 fields) ===
    "entry_type": "edge",                   # "edge" / "50pct" / "buffer_adaptive"
    "entry_price_ideal": 1.23550,           # Entry at FVG edge (best RR)
    "entry_price_real": 1.23545,            # Actual entry with buffer
    "entry_buffer_size": 0.00005,           # Buffer applied
    "allow_front_run": true,                # Front-run allowed for this FVG?
    "max_penetration_allowed": 0.50,        # Max penetration for valid entry

    # === RR CALCULATION (NEW - 4 fields) ===
    "rr_ideal": 3.2,                        # RR if entry at edge
    "rr_real": 2.8,                         # RR with actual entry
    "rr_50pct": 2.5,                        # RR if entry at 50% FVG
    "rr_degradation": 0.4,                  # rr_ideal - rr_real

    # === OB CONTEXT (from Module #1) ===
    "has_ob_in_leg": true,
    "ob_overlap_ratio": 0.7,
    "ob_is_m5_hl": true,
    "ob_leg_bos_type": "BOS",
    "ob_strength_score": 0.85,
    "ob_distance_from_source": 1.2,

    # === ENTRY/SL/TP ===
    "entry_price": 1.23545,                 # Final entry price used
    "sl_price": 1.23480,                    # Stop loss
    "sl_buffer_applied": 0.00010,           # Extra buffer beyond FVG for SL
    "tp1_price": 1.23650,                   # TP1 (nearest structure)
    "tp2_price": 1.23750,                   # TP2 (2.5+ RR)
    "tp3_price": 1.23850,                   # TP3 (extended)

    # === LABEL (for ML) ===
    "signal": "long"                        # "long" / "short" / "skip"
}
```

---

## 🧮 CALCULATION LOGIC

### 1. FVG STRENGTH CALCULATION

```python
def calculate_fvg_strength(self, bar_state: dict, historical_bars: list) -> dict:
    """
    Calculate FVG strength based on imbalance characteristics.

    Strong FVG = Institutional footprint, high conviction
    Weak FVG = Noise, likely to fill quickly
    """
    if not bar_state.get('fvg_detected'):
        return self._null_strength_output()

    fvg_type = bar_state['fvg_type']
    gap_size = bar_state['fvg_gap_size']
    atr = bar_state['atr_14']
    volume = bar_state['volume']
    delta = bar_state['delta']
    buy_vol = bar_state['buy_volume']
    sell_vol = bar_state['sell_volume']

    # --- Calculate component metrics ---

    # 1. Gap size relative to ATR
    fvg_size_atr = gap_size / atr if atr > 0 else 0
    gap_quality = min(fvg_size_atr / 2.0, 1.0)  # 2.0 ATR = perfect

    # 2. Volume relative to median
    volume_median = self._get_volume_median(historical_bars, 20)
    fvg_vol_ratio = volume / volume_median if volume_median > 0 else 1.0
    volume_quality = min((fvg_vol_ratio - 1.0) / 2.0, 1.0)  # 3x = perfect
    volume_quality = max(volume_quality, 0.0)

    # 3. Delta imbalance ratio
    total_vol = buy_vol + sell_vol
    fvg_delta_ratio = abs(delta) / total_vol if total_vol > 0 else 0
    imbalance_quality = min(fvg_delta_ratio / 0.8, 1.0)  # 0.8 = perfect

    # 4. Delta alignment with FVG direction
    if fvg_type == 'bullish':
        delta_alignment = 1 if delta > 0 else (-1 if delta < 0 else 0)
    else:  # bearish
        delta_alignment = 1 if delta < 0 else (-1 if delta > 0 else 0)

    alignment_bonus = 0.1 if delta_alignment == 1 else (-0.1 if delta_alignment == -1 else 0)

    # --- Check for rebalance (fills previous FVG) ---
    rebalance_info = self._check_fvg_rebalance(bar_state, historical_bars)
    rebalance_bonus = 0.1 if rebalance_info['fvg_rebalances_prev'] else 0

    # --- Calculate composite strength score ---
    base_score = (
        0.35 * gap_quality +
        0.30 * volume_quality +
        0.25 * imbalance_quality +
        0.10 * (1.0 if delta_alignment == 1 else 0.5)
    )

    strength_score = min(base_score + alignment_bonus + rebalance_bonus, 1.0)

    # --- Classify strength ---
    if strength_score >= 0.75 and fvg_size_atr >= 1.5 and fvg_vol_ratio >= 2.0:
        strength_class = "Strong"
    elif strength_score >= 0.50 and fvg_size_atr >= 0.8:
        strength_class = "Medium"
    else:
        strength_class = "Weak"

    return {
        'fvg_size_atr': round(fvg_size_atr, 4),
        'fvg_vol_ratio': round(fvg_vol_ratio, 4),
        'fvg_delta_ratio': round(fvg_delta_ratio, 4),
        'fvg_delta_alignment': delta_alignment,
        'fvg_strength_score': round(strength_score, 4),
        'fvg_strength_class': strength_class,
        'fvg_gap_quality_score': round(gap_quality, 4),
        'fvg_volume_quality_score': round(volume_quality, 4),
        'fvg_imbalance_quality_score': round(imbalance_quality, 4),
        **rebalance_info
    }
```

### 2. REBALANCE DETECTION

```python
def _check_fvg_rebalance(self, current_fvg: dict, historical_bars: list) -> dict:
    """
    Check if current FVG's creation leg filled a previous unfilled FVG.

    This is institutional footprint: "clean up old imbalance before new move"
    """
    fvg_type = current_fvg['fvg_type']
    fvg_left_idx = current_fvg['fvg_left_bar_index']

    # Get unfilled FVGs in opposite direction
    opposite_dir = 'bearish' if fvg_type == 'bullish' else 'bullish'

    unfilled_fvgs = self._get_unfilled_fvgs(historical_bars, opposite_dir)

    if not unfilled_fvgs:
        return {
            'fvg_rebalances_prev': False,
            'fvg_rebalance_ratio': 0.0,
            'fvg_is_clean_rebalance': False,
            'prev_fvg_direction': None,
            'prev_fvg_age_bars': 0
        }

    # Check if the leg creating current FVG passed through any unfilled FVG
    leg_bars = [b for b in historical_bars
                if current_fvg['fvg_left_bar_index'] <= b['bar_index'] <= current_fvg['fvg_right_bar_index']]

    if not leg_bars:
        return self._null_rebalance_output()

    leg_high = max(b['high'] for b in leg_bars)
    leg_low = min(b['low'] for b in leg_bars)

    best_rebalance = None
    best_ratio = 0

    for old_fvg in unfilled_fvgs:
        old_high = old_fvg['fvg_high']
        old_low = old_fvg['fvg_low']
        old_size = old_high - old_low

        # Calculate how much of old FVG was filled by the leg
        if fvg_type == 'bullish':  # Leg moved up, could fill bearish FVG
            if leg_high >= old_low:  # Leg reached into old FVG
                filled_portion = min(leg_high, old_high) - old_low
                rebalance_ratio = filled_portion / old_size if old_size > 0 else 0
            else:
                rebalance_ratio = 0
        else:  # bearish - leg moved down, could fill bullish FVG
            if leg_low <= old_high:
                filled_portion = old_high - max(leg_low, old_low)
                rebalance_ratio = filled_portion / old_size if old_size > 0 else 0
            else:
                rebalance_ratio = 0

        if rebalance_ratio > best_ratio:
            best_ratio = rebalance_ratio
            best_rebalance = old_fvg

    if best_ratio >= 0.3:  # At least 30% filled = counts as rebalance
        return {
            'fvg_rebalances_prev': True,
            'fvg_rebalance_ratio': round(best_ratio, 4),
            'fvg_is_clean_rebalance': best_ratio >= 0.8,
            'prev_fvg_direction': opposite_dir,
            'prev_fvg_age_bars': current_fvg['bar_index'] - best_rebalance['fvg_creation_bar_index']
        }

    return self._null_rebalance_output()
```

### 3. RETEST GEOMETRY EVALUATION

```python
def evaluate_retest_geometry(self, fvg_zone: dict, retest_bar: dict) -> dict:
    """
    Evaluate how price interacted with FVG zone during retest.

    KEY INSIGHT (20 years experience):
    - Edge touch / slight penetration = HIGH QUALITY
    - Deep penetration (>50%) = LOW QUALITY, likely to break
    - Front-run (before touch) = ACCEPTABLE for strong FVG only
    """
    fvg_high = fvg_zone['fvg_high']
    fvg_low = fvg_zone['fvg_low']
    fvg_size = fvg_high - fvg_low
    fvg_type = fvg_zone['fvg_type']
    fvg_strength = fvg_zone.get('fvg_strength_class', 'Medium')

    bar_high = retest_bar['high']
    bar_low = retest_bar['low']
    bar_close = retest_bar['close']
    atr = retest_bar['atr_14']

    # === Calculate penetration based on FVG direction ===
    if fvg_type == 'bullish':
        # Bull FVG: price comes DOWN to test from above
        # Penetration measured from TOP of FVG
        if bar_low >= fvg_high:
            # No touch yet - in front-run zone
            penetration_ratio = 0.0
            min_dist_to_edge = (bar_low - fvg_high) / atr
            front_run_distance = min_dist_to_edge
        elif bar_low >= fvg_low:
            # Inside FVG zone
            penetration_ratio = (fvg_high - bar_low) / fvg_size
            min_dist_to_edge = 0.0
            front_run_distance = 0.0
        else:
            # Broke through FVG
            penetration_ratio = 1.0 + (fvg_low - bar_low) / fvg_size
            min_dist_to_edge = 0.0
            front_run_distance = 0.0
    else:
        # Bear FVG: price comes UP to test from below
        # Penetration measured from BOTTOM of FVG
        if bar_high <= fvg_low:
            penetration_ratio = 0.0
            min_dist_to_edge = (fvg_low - bar_high) / atr
            front_run_distance = min_dist_to_edge
        elif bar_high <= fvg_high:
            penetration_ratio = (bar_high - fvg_low) / fvg_size
            min_dist_to_edge = 0.0
            front_run_distance = 0.0
        else:
            penetration_ratio = 1.0 + (bar_high - fvg_high) / fvg_size
            min_dist_to_edge = 0.0
            front_run_distance = 0.0

    # === Classify touch type ===
    if penetration_ratio == 0.0:
        retest_type = "no_touch"      # Front-run candidate
    elif penetration_ratio <= 0.20:
        retest_type = "edge"          # BEST - just touched edge
    elif penetration_ratio <= 0.50:
        retest_type = "shallow"       # OK - moderate penetration
    elif penetration_ratio <= 1.00:
        retest_type = "deep"          # RISKY - deep penetration
    else:
        retest_type = "break"         # INVALID - broke through

    # === Calculate retest quality score ===
    if retest_type == "break":
        retest_quality = 0.0
    elif retest_type == "deep":
        retest_quality = 0.25 if fvg_strength == "Strong" else 0.10
    elif retest_type == "shallow":
        retest_quality = 0.60 if fvg_strength == "Strong" else 0.40
    elif retest_type == "edge":
        retest_quality = 0.95 if fvg_strength == "Strong" else 0.75
    elif retest_type == "no_touch":
        # Front-run: only valid for Strong FVG within reasonable distance
        if fvg_strength == "Strong" and front_run_distance <= 0.3:
            retest_quality = 0.80
        elif fvg_strength == "Strong" and front_run_distance <= 0.5:
            retest_quality = 0.60
        else:
            retest_quality = 0.20  # Too far or weak FVG

    return {
        'fvg_retest_type': retest_type,
        'fvg_penetration_ratio': round(penetration_ratio, 4),
        'fvg_min_distance_to_edge': round(min_dist_to_edge, 4),
        'fvg_front_run_distance': round(front_run_distance, 4),
        'fvg_retest_quality_score': round(retest_quality, 4)
    }
```

### 4. ADAPTIVE ENTRY CALCULATION

```python
def calculate_adaptive_entry(self, fvg_zone: dict, atr: float) -> dict:
    """
    Calculate entry price with adaptive buffer based on FVG strength.

    Strong FVG: tight buffer, can front-run
    Medium FVG: moderate buffer, wait for touch
    Weak FVG: wide buffer, need deep retest
    """
    fvg_high = fvg_zone['fvg_high']
    fvg_low = fvg_zone['fvg_low']
    fvg_size = fvg_high - fvg_low
    fvg_type = fvg_zone['fvg_type']
    fvg_strength = fvg_zone.get('fvg_strength_class', 'Medium')

    # === Determine buffer parameters based on strength ===
    if fvg_strength == "Strong":
        buffer_ratio = 0.10          # 10% of FVG size
        min_buffer_atr = 0.15        # Min 0.15 ATR
        allow_front_run = True
        max_penetration = 0.50
    elif fvg_strength == "Medium":
        buffer_ratio = 0.20
        min_buffer_atr = 0.25
        allow_front_run = False
        max_penetration = 0.40
    else:  # Weak
        buffer_ratio = 0.30
        min_buffer_atr = 0.35
        allow_front_run = False
        max_penetration = 0.30

    # Calculate buffer size (max of ratio-based and ATR-based)
    buffer_size = max(buffer_ratio * fvg_size, min_buffer_atr * atr)

    # === Calculate entry prices ===
    if fvg_type == 'bullish':
        # Long entry: buy at/above FVG
        entry_ideal = fvg_high                       # At edge
        entry_50pct = (fvg_high + fvg_low) / 2      # At 50%
        entry_with_buffer = fvg_high + buffer_size   # Conservative (above FVG)
    else:
        # Short entry: sell at/below FVG
        entry_ideal = fvg_low
        entry_50pct = (fvg_high + fvg_low) / 2
        entry_with_buffer = fvg_low - buffer_size

    return {
        'entry_type': 'buffer_adaptive',
        'entry_price_ideal': round(entry_ideal, 5),
        'entry_price_real': round(entry_with_buffer, 5),
        'entry_50pct': round(entry_50pct, 5),
        'entry_buffer_size': round(buffer_size, 6),
        'allow_front_run': allow_front_run,
        'max_penetration_allowed': max_penetration
    }
```

### 5. RR CALCULATION (Ideal vs Real)

```python
def calculate_rr_variants(self, fvg_zone: dict, entry_info: dict,
                          sl_price: float, tp_price: float) -> dict:
    """
    Calculate multiple RR variants for comparison.

    - rr_ideal: If entry at FVG edge (best case)
    - rr_real: With actual entry (buffer applied)
    - rr_50pct: If entry at 50% of FVG
    """
    fvg_type = fvg_zone['fvg_type']

    entry_ideal = entry_info['entry_price_ideal']
    entry_real = entry_info['entry_price_real']
    entry_50pct = entry_info['entry_50pct']

    def calc_rr(entry, sl, tp, direction):
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk <= 0:
            return 0.0
        # For short: TP below entry, SL above entry
        if direction == -1:  # short
            risk = abs(sl - entry)
            reward = abs(entry - tp)
        return reward / risk

    direction = 1 if fvg_type == 'bullish' else -1

    rr_ideal = calc_rr(entry_ideal, sl_price, tp_price, direction)
    rr_real = calc_rr(entry_real, sl_price, tp_price, direction)
    rr_50pct = calc_rr(entry_50pct, sl_price, tp_price, direction)

    return {
        'rr_ideal': round(rr_ideal, 4),
        'rr_real': round(rr_real, 4),
        'rr_50pct': round(rr_50pct, 4),
        'rr_degradation': round(rr_ideal - rr_real, 4)
    }
```

---

## 🐍 MODULE CLASS STRUCTURE

```python
# processor/modules/fix02_fvg_quality.py

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

@dataclass
class FVGZone:
    """Represents an FVG zone with all quality metrics."""
    fvg_high: float
    fvg_low: float
    fvg_type: str
    creation_bar_index: int
    strength_score: float
    strength_class: str
    is_filled: bool = False
    fill_ratio: float = 0.0

class FVGQualityModule:
    """
    Module Fix #02: Comprehensive FVG Quality Assessment.

    Components:
    1. FVG Strength (imbalance quality)
    2. Retest Geometry (penetration, touch type)
    3. Rebalance Detection (fills previous FVG)
    4. Adaptive Entry (dynamic buffer)
    5. Value Class Assignment (A/B/C)
    """

    def __init__(self, config: dict = None):
        self.config = config or self._default_config()
        self.active_fvgs: List[FVGZone] = []  # Track unfilled FVGs
        self.fvg_history: List[FVGZone] = []  # All FVGs (for rebalance check)

    def _default_config(self) -> dict:
        return {
            # Strength thresholds
            'strong_size_atr': 1.5,
            'strong_vol_ratio': 2.0,
            'strong_delta_ratio': 0.6,
            'medium_size_atr': 0.8,
            'medium_vol_ratio': 1.3,
            'medium_delta_ratio': 0.4,

            # Retest thresholds
            'edge_penetration_max': 0.20,
            'shallow_penetration_max': 0.50,
            'deep_penetration_max': 1.00,

            # Entry buffer
            'strong_buffer_ratio': 0.10,
            'medium_buffer_ratio': 0.20,
            'weak_buffer_ratio': 0.30,

            # Rebalance
            'min_rebalance_ratio': 0.30,
            'clean_rebalance_ratio': 0.80,

            # Lookback
            'fvg_lookback_bars': 100,
            'volume_median_period': 20
        }

    def process_bar(self, bar_state: dict, bar_history: list,
                    session_vp: dict = None) -> dict:
        """
        Main processing function - adds all FVG quality fields to bar_state.
        """
        if not bar_state.get('fvg_detected'):
            return {**bar_state, **self._null_output()}

        # 1. Calculate FVG Strength
        strength_info = self.calculate_fvg_strength(bar_state, bar_history)

        # 2. Check Value Area context (if VP available)
        va_info = self._check_va_context(bar_state, session_vp)

        # 3. Check sweep context (from Module #11)
        sweep_info = self._check_sweep_context(bar_state)

        # 4. Determine Value Class
        value_class = self._determine_value_class(
            strength_info, va_info, sweep_info
        )

        # 5. Build context string
        context = self._build_context_string(
            strength_info, va_info, sweep_info, bar_state['fvg_type']
        )

        # 6. Calculate composite quality score
        quality_score = self._calculate_composite_score(
            strength_info, va_info, sweep_info, value_class
        )

        # 7. Register this FVG for tracking
        self._register_fvg(bar_state, strength_info)

        # Merge all outputs
        return {
            **bar_state,
            **strength_info,
            **va_info,
            **sweep_info,
            'fvg_value_class': value_class,
            'fvg_quality_score': quality_score,
            'fvg_context': context
        }

    def evaluate_retest(self, fvg_zone: dict, retest_bar: dict) -> dict:
        """
        Evaluate a retest of an FVG zone.
        Returns retest geometry + adaptive entry info.
        """
        # Geometry evaluation
        geometry = self.evaluate_retest_geometry(fvg_zone, retest_bar)

        # Adaptive entry calculation
        entry_info = self.calculate_adaptive_entry(
            fvg_zone, retest_bar['atr_14']
        )

        return {**geometry, **entry_info}

    # ... (implement all helper methods from above)
```

---

## ✅ SUCCESS CRITERIA

### Statistical Validation Targets:

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| Strong FVG win rate | ≥ 42% | Backtest on historical data |
| Medium FVG win rate | ≥ 32% | Backtest on historical data |
| Weak FVG win rate | < 25% | Backtest (should be filtered) |
| Edge retest win rate | ≥ 45% | Backtest by touch type |
| Deep penetration win rate | < 28% | Backtest (confirms filter rule) |
| Rebalance FVG win rate | ≥ 48% | Backtest (should be highest) |
| Strength-WinRate correlation | > 0.5 | Statistical analysis |
| Penetration-WinRate correlation | < -0.4 | Statistical analysis (inverse) |

### Filtering Impact:

| Filter | Events Removed | Expected WR Improvement |
|--------|----------------|-------------------------|
| Weak FVG | ~50-60% | +8-10% |
| Deep penetration (>50%) | ~20-30% | +5-7% |
| In VA (no breakout) | ~30-40% | +5-8% |
| Combined | ~60-70% | +15-20% |

---

## 🧪 UNIT TESTS

```python
# processor/tests/test_fix02_fvg_quality.py

def test_fvg_strength_strong():
    """Test Strong FVG classification."""
    module = FVGQualityModule()

    bar = {
        'fvg_detected': True,
        'fvg_type': 'bullish',
        'fvg_gap_size': 0.00040,  # 1.6 ATR
        'atr_14': 0.00025,
        'volume': 2500,
        'buy_volume': 2000,
        'sell_volume': 500,
        'delta': 1500
    }

    history = [{'volume': 1000} for _ in range(20)]

    result = module.calculate_fvg_strength(bar, history)

    assert result['fvg_strength_class'] == "Strong"
    assert result['fvg_strength_score'] >= 0.75
    assert result['fvg_delta_alignment'] == 1  # Bullish FVG + positive delta

def test_retest_geometry_edge():
    """Test edge touch detection."""
    module = FVGQualityModule()

    fvg = {
        'fvg_high': 1.2350,
        'fvg_low': 1.2330,
        'fvg_type': 'bullish',
        'fvg_strength_class': 'Strong'
    }

    retest_bar = {
        'high': 1.2360,
        'low': 1.2348,  # Just touched edge (2 ticks in)
        'close': 1.2355,
        'atr_14': 0.00025
    }

    result = module.evaluate_retest_geometry(fvg, retest_bar)

    assert result['fvg_retest_type'] == "edge"
    assert result['fvg_penetration_ratio'] <= 0.20
    assert result['fvg_retest_quality_score'] >= 0.90

def test_retest_geometry_deep():
    """Test deep penetration detection."""
    module = FVGQualityModule()

    fvg = {
        'fvg_high': 1.2350,
        'fvg_low': 1.2330,
        'fvg_type': 'bullish',
        'fvg_strength_class': 'Medium'
    }

    retest_bar = {
        'high': 1.2360,
        'low': 1.2335,  # 75% penetration
        'close': 1.2345,
        'atr_14': 0.00025
    }

    result = module.evaluate_retest_geometry(fvg, retest_bar)

    assert result['fvg_retest_type'] == "deep"
    assert result['fvg_penetration_ratio'] >= 0.50
    assert result['fvg_retest_quality_score'] <= 0.25

def test_rebalance_detection():
    """Test FVG rebalance detection."""
    module = FVGQualityModule()

    # Old bearish FVG (unfilled)
    old_fvg = {
        'fvg_detected': True,
        'fvg_type': 'bearish',
        'fvg_high': 1.2340,
        'fvg_low': 1.2320,
        'bar_index': 100,
        'fvg_creation_bar_index': 100
    }

    # New bullish FVG whose leg passes through old FVG
    new_fvg = {
        'fvg_detected': True,
        'fvg_type': 'bullish',
        'fvg_high': 1.2380,
        'fvg_low': 1.2360,
        'fvg_left_bar_index': 110,
        'fvg_right_bar_index': 112,
        'bar_index': 112
    }

    # Leg bars that created new FVG
    leg_bars = [
        {'bar_index': 110, 'high': 1.2345, 'low': 1.2310},  # Swept through old FVG
        {'bar_index': 111, 'high': 1.2370, 'low': 1.2340},
        {'bar_index': 112, 'high': 1.2385, 'low': 1.2355}
    ]

    history = [old_fvg] + leg_bars

    result = module._check_fvg_rebalance(new_fvg, history)

    assert result['fvg_rebalances_prev'] == True
    assert result['fvg_rebalance_ratio'] >= 0.80
    assert result['fvg_is_clean_rebalance'] == True

def test_adaptive_entry_strong():
    """Test adaptive entry for Strong FVG."""
    module = FVGQualityModule()

    fvg = {
        'fvg_high': 1.2350,
        'fvg_low': 1.2330,
        'fvg_type': 'bullish',
        'fvg_strength_class': 'Strong'
    }

    result = module.calculate_adaptive_entry(fvg, atr=0.00025)

    assert result['allow_front_run'] == True
    assert result['max_penetration_allowed'] == 0.50
    assert result['entry_buffer_size'] <= 0.00005  # Small buffer for strong FVG
```

---

## 📝 INTEGRATION NOTES

### Module Dependencies:

```
Module #9 (Volume Profile) → Provides VA context
Module #11 (Liquidity Map) → Provides sweep context
Module #1 (OB Quality) → Provides OB context for events
                ↓
        Module #2 (FVG Quality) ← THIS MODULE
                ↓
        Module #4 (Confluence) → Uses FVG quality score
```

### Execution Order:

```python
# In SMCDataProcessor.process_bar()
def process_bar(self, raw_bar: dict) -> dict:
    bar_state = raw_bar.copy()

    # 1. Volume Profile (foundation)
    bar_state = self.fix9_volume_profile.process_bar(bar_state)

    # 2. Liquidity Map (sweep detection)
    bar_state = self.fix11_liquidity_map.process_bar(bar_state, self.bar_history)

    # 3. OB Quality (context)
    bar_state = self.fix1_ob_quality.process_bar(bar_state, self.bar_history)

    # 4. FVG Quality (THIS MODULE - uses all above)
    bar_state = self.fix2_fvg_quality.process_bar(
        bar_state,
        self.bar_history,
        self.current_session_vp
    )

    # 5. Continue with other modules...
    return bar_state
```

---

## 📚 THEORY REFERENCE

### FVG Strength Interpretation:

**Strong FVG (Institutional Footprint):**
- Large gap (> 1.5 ATR) = significant price inefficiency
- High volume (> 2x median) = institutional participation
- Delta alignment = clear directional intent
- Rebalances previous FVG = "cleaning up" before major move

**Weak FVG (Noise):**
- Small gap = minor fluctuation
- Low volume = retail activity
- No delta confirmation = mixed intent
- Likely to fill quickly without significant move

### Retest Geometry Interpretation:

**Edge Touch = HIGH QUALITY:**
- Smart money defends zone
- Minimal "price discovery" needed
- High probability of continuation

**Deep Penetration = LOW QUALITY:**
- Zone losing strength
- More stops being hit
- Higher probability of full break

### Rebalance Significance:

**Why it matters:**
- Markets seek efficiency
- Old imbalances get "filled" before new moves
- Institutional footprint: clean up → new position
- FVG that rebalances old FVG = very strong signal

---

**Last Updated:** November 21, 2025
**Version:** 2.0.0
**Status:** 📝 Specification Complete - Ready for Implementation
**Dependencies:** Module #1, #9, #11 (recommended)
