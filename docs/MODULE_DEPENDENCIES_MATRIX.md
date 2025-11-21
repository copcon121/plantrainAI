# MODULE DEPENDENCIES MATRIX

## VERSION: 1.0
## PURPOSE: Cross-reference of Ninja export fields required by each Python module
## LAST UPDATED: November 21, 2025

---

## 1. SUMMARY TABLE

| Module | Field Count | Critical Fields | Priority |
|--------|-------------|-----------------|----------|
| #01 OB Quality | 12 | `ob_*`, `delta`, `volume` | HIGH |
| #02 FVG Quality | 16 | `fvg_*`, `volume`, `delta`, `atr_14` | **MUST** |
| #03 Structure Context | 16 | `choch_*`, `bos_*`, `current_trend` | **MUST** |
| #04 Confluence | ALL | Combines all module outputs | **MUST** |
| #05 Stop Placement | 14 | `fvg_*`, `ob_*`, `swing_*`, `atr_14` | **MUST** |
| #06 Target Placement | 10 | `swing_*`, `liquidity_*`, `prev_session_*` | HIGH |
| #07 Market Condition | 8 | `atr_14`, `adx_14`, `di_*`, OHLC | HIGH |
| #08 Volume Divergence | 8 | `is_swing_*`, `delta`, `cumulative_delta` | HIGH |
| #09 Volume Profile | 8 | `vp_*`, `prev_session_vah/val/poc` | MEDIUM |
| #10 MTF Alignment | 9 | `htf_*`, `current_trend` | HIGH |
| #11 Liquidity Map | 14 | `eqh_*`, `eql_*`, `liquidity_*`, `swing_*` | HIGH |

---

## 2. DETAILED FIELD REQUIREMENTS BY MODULE

### 2.1 Module #01 - OB Quality

**Purpose:** Assess Order Block quality for FVG context scoring

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `ob_detected` | bool | OB formation flag | Trigger calculation |
| `ob_type` | string | "bullish"/"bearish" | Direction check |
| `ob_top` | float | OB upper bound | Size calculation |
| `ob_bottom` | float | OB lower bound | Size calculation |
| `ob_bar_index` | int | Formation bar | Age calculation |
| `nearest_ob_top` | float | Nearest relevant OB | Proximity check |
| `nearest_ob_bottom` | float | Nearest relevant OB | Proximity check |
| `nearest_ob_type` | string | OB direction | Alignment check |
| `delta` | int | Bar delta | Imbalance ratio |
| `volume` | int | Bar volume | Volume factor |
| `buy_volume` | int | Buy volume | Delta validation |
| `sell_volume` | int | Sell volume | Delta validation |

**Calculated in Python:**
- `ob_displacement_rr` = leg_move / ob_size
- `ob_volume_factor` = ob_volume / median_volume_20
- `ob_delta_imbalance` = |delta| / volume
- `ob_sweep_before` = liquidity sweep detection

---

### 2.2 Module #02 - FVG Quality (PRIMARY SIGNAL)

**Purpose:** Primary signal detection and quality scoring

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `fvg_detected` | bool | FVG formation flag | **PRIMARY TRIGGER** |
| `fvg_type` | string | "bullish"/"bearish" | Direction |
| `fvg_top` | float | FVG upper bound | Size calculation |
| `fvg_bottom` | float | FVG lower bound | Size calculation |
| `fvg_bar_index` | int | Formation bar | Age tracking |
| `fvg_gap_size` | float | fvg_top - fvg_bottom | Raw size |
| `fvg_filled` | bool | Fill status | Fill tracking |
| `fvg_fill_percentage` | float | % filled | Partial fill |
| `fvg_creation_volume` | int | Volume on FVG bar | Strength |
| `fvg_creation_buy_vol` | int | Buy volume | Delta calc |
| `fvg_creation_sell_vol` | int | Sell volume | Delta calc |
| `fvg_creation_delta` | int | Delta on FVG bar | Imbalance |
| `volume` | int | Current bar volume | Normalization |
| `atr_14` | float | ATR(14) | Size normalization |
| `open` | float | Bar open | Displacement |
| `close` | float | Bar close | Displacement |

**Calculated in Python:**
- `fvg_atr_ratio` = gap_size / ATR
- `fvg_volume_factor` = creation_volume / median_20
- `fvg_displacement` = |close - open| / ATR
- `fvg_delta_imbalance` = |delta| / volume

---

### 2.3 Module #03 - Structure Context

**Purpose:** Tag FVG events with market structure context

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `choch_detected` | bool | CHoCH flag | Context trigger |
| `choch_type` | string | "bullish"/"bearish" | Direction |
| `choch_price` | float | CHoCH price level | Distance calc |
| `choch_bar_index` | int | CHoCH bar | Age calc |
| `choch_bars_ago` | int | Bars since CHoCH | Recency |
| `choch_swing_broken` | float | Broken swing price | Structure analysis |
| `bos_detected` | bool | BOS flag | Context trigger |
| `bos_type` | string | "bullish"/"bearish" | Direction |
| `bos_price` | float | BOS price level | Distance calc |
| `bos_bar_index` | int | BOS bar | Age calc |
| `bos_bars_ago` | int | Bars since BOS | Recency |
| `bos_swing_broken` | float | Broken swing price | Structure analysis |
| `current_trend` | string | "bullish"/"bearish"/"neutral" | Trend state |
| `trend_swing_count` | int | Swings in trend | Trend maturity |
| `last_structure_break` | string | "choch"/"bos"/"none" | Recent event |
| `bars_since_structure_break` | int | Bars since break | Freshness |

**Calculated in Python:**
- `context_type` = "expansion" / "retracement" / "continuation"
- `context_multiplier` = 1.2 / 0.8 / 1.0

**Context Logic:**
```
IF choch_bars_ago < 10:
    context = "expansion" (new trend)
ELIF bos_bars_ago < 10 AND bars_since_structure_break > 5:
    context = "retracement" (pullback after BOS)
ELSE:
    context = "continuation" (mid-trend)
```

---

### 2.4 Module #04 - Confluence Scoring

**Purpose:** Combine all module outputs into weighted confluence score

**Inputs (from other modules, not Ninja directly):**
| Input | Source | Weight |
|-------|--------|--------|
| `ob_proximity_score` | Module #01 | 25% |
| `structure_score` | Module #03 | 25% |
| `fvg_strength_score` | Module #02 | 20% |
| `mtf_alignment_score` | Module #10 | 15% |
| `liquidity_score` | Module #11 | 10% |
| `volume_confluence_score` | Module #08 | 5% |

**Direct Ninja fields needed:**
- `fvg_type` - For alignment check
- `close` - For proximity calculations
- `atr_14` - For distance normalization

---

### 2.5 Module #05 - Stop Placement

**Purpose:** Calculate optimal stop loss for FVG entries

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `fvg_top` | float | FVG boundary | Stop method 1,2 |
| `fvg_bottom` | float | FVG boundary | Stop method 1,2 |
| `fvg_type` | string | Direction | Stop side selection |
| `nearest_ob_top` | float | OB boundary | Stop method 3 |
| `nearest_ob_bottom` | float | OB boundary | Stop method 3 |
| `nearest_ob_type` | string | OB direction | Alignment check |
| `last_swing_high` | float | Recent swing | Stop method 4 |
| `last_swing_low` | float | Recent swing | Stop method 4 |
| `recent_swing_high` | float | Lookback swing | Alternative stop |
| `recent_swing_low` | float | Lookback swing | Alternative stop |
| `atr_14` | float | ATR(14) | Buffer calculation |
| `close` | float | Current price | Distance calc |
| `high` | float | Bar high | Swing detection |
| `low` | float | Bar low | Swing detection |

**Stop Methods:**
1. **FVG Edge** = fvg_bottom/top + buffer
2. **FVG Full** = opposite FVG edge + buffer
3. **OB Edge** = nearest_ob + buffer
4. **Structure** = recent_swing + buffer

**Buffer** = 0.5 * ATR_14

---

### 2.6 Module #06 - Target Placement

**Purpose:** Calculate take profit targets

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `last_swing_high` | float | Recent high | TP1 (long) |
| `last_swing_low` | float | Recent low | TP1 (short) |
| `recent_swing_high` | float | Lookback high | Alternative TP |
| `recent_swing_low` | float | Lookback low | Alternative TP |
| `nearest_liquidity_high` | float | Liquidity target | TP1 option |
| `nearest_liquidity_low` | float | Liquidity target | TP1 option |
| `prev_session_high` | float | Session level | Extended TP |
| `prev_session_low` | float | Session level | Extended TP |
| `close` | float | Entry price | RR calculation |
| `fvg_type` | string | Direction | TP side selection |

**Target Logic:**
- **TP1** = Nearest structure/liquidity (1-2 RR)
- **TP2** = 3x RR from entry

---

### 2.7 Module #07 - Market Condition

**Purpose:** Classify market regime (trending/ranging, volatile/quiet)

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `atr_14` | float | ATR(14) | Volatility classification |
| `adx_14` | float | ADX(14) | Trend strength |
| `di_plus_14` | float | DI+ | Trend direction |
| `di_minus_14` | float | DI- | Trend direction |
| `high` | float | Bar high | ATR percentile calc |
| `low` | float | Bar low | ATR percentile calc |
| `close` | float | Bar close | Price context |
| `current_trend` | string | Trend state | Confirmation |

**Classifications:**
- **Trend**: ADX > 25 = Trending, ADX < 20 = Ranging
- **Volatility**: ATR percentile vs 100-bar lookback

---

### 2.8 Module #08 - Volume Divergence

**Purpose:** Detect price/delta divergence at swing points

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `is_swing_high` | bool | Swing high flag | Trigger (bearish div) |
| `is_swing_low` | bool | Swing low flag | Trigger (bullish div) |
| `delta` | int | Bar delta | Divergence comparison |
| `cumulative_delta` | int | Running delta | Primary divergence metric |
| `high` | float | Bar high | Swing price |
| `low` | float | Bar low | Swing price |
| `bar_index` | int | Bar number | Distance calculation |
| `close` | float | Bar close | Price context |

**Divergence Logic:**
```
Bullish: Price LL + Delta less negative (cumulative)
Bearish: Price HH + Delta less positive (cumulative)
```

---

### 2.9 Module #09 - Volume Profile

**Purpose:** Provide VAH/VAL/POC levels for analysis

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `vp_session_poc` | float | Session POC | Current POC |
| `vp_session_vah` | float | Session VAH | Liquidity level |
| `vp_session_val` | float | Session VAL | Liquidity level |
| `vp_developing_poc` | float | Developing POC | Dynamic level |
| `prev_session_vah` | float | Prior VAH | Reference level |
| `prev_session_val` | float | Prior VAL | Reference level |
| `prev_session_poc` | float | Prior POC | Reference level |
| `vp_session_volume` | int | Session volume | Normalization |

**Note:** If not available from Ninja, can calculate in Python from tick data.

---

### 2.10 Module #10 - MTF Alignment

**Purpose:** Check higher timeframe trend alignment

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `htf_high` | float | HTF bar high | Trend analysis |
| `htf_low` | float | HTF bar low | Trend analysis |
| `htf_close` | float | HTF bar close | Price position |
| `htf_ema_20` | float | HTF 20 EMA | MA trend |
| `htf_ema_50` | float | HTF 50 EMA | MA trend |
| `htf_is_swing_high` | bool | HTF swing high | Structure trend |
| `htf_is_swing_low` | bool | HTF swing low | Structure trend |
| `current_trend` | string | LTF trend | Alignment check |
| `fvg_type` | string | FVG direction | Alignment check |

**Alignment Score:**
```
+1 if HTF EMA20 > EMA50 (bullish MA trend)
+1 if HTF making HH/HL (bullish structure)
+1 if aligned with FVG direction
Score: 0-3 → Normalized to 0-1
```

---

### 2.11 Module #11 - Liquidity Map

**Purpose:** Track and detect liquidity sweeps

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `eqh_detected` | bool | Equal highs flag | Liquidity detection |
| `eqh_price` | float | EQH level | Target price |
| `eqh_count` | int | Touch count | Liquidity strength |
| `eql_detected` | bool | Equal lows flag | Liquidity detection |
| `eql_price` | float | EQL level | Target price |
| `eql_count` | int | Touch count | Liquidity strength |
| `nearest_liquidity_high` | float | Nearest high liq | Sweep detection |
| `nearest_liquidity_low` | float | Nearest low liq | Sweep detection |
| `liquidity_high_type` | string | Type of high liq | Classification |
| `liquidity_low_type` | string | Type of low liq | Classification |
| `last_swing_high` | float | Recent swing | Liquidity candidate |
| `last_swing_low` | float | Recent swing | Liquidity candidate |
| `high` | float | Current bar high | Sweep detection |
| `low` | float | Current bar low | Sweep detection |

**Sweep Detection:**
```
Sweep detected when:
- Price exceeds liquidity level (high > nearest_liquidity_high)
- Then reverses (close < open for high sweep)
```

---

## 3. FIELD COVERAGE VALIDATION

### 3.1 Cross-Module Field Usage

| Field | M01 | M02 | M03 | M04 | M05 | M06 | M07 | M08 | M09 | M10 | M11 |
|-------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| `bar_index` | | X | | | | | | X | | | |
| `open` | | X | | | | | | | | | |
| `high` | | | | | X | | X | X | | | X |
| `low` | | | | | X | | X | X | | | X |
| `close` | | X | | X | X | X | X | X | | | |
| `volume` | X | X | | | | | | | | | |
| `buy_volume` | X | X | | | | | | | | | |
| `sell_volume` | X | X | | | | | | | | | |
| `delta` | X | | | | | | | X | | | |
| `cumulative_delta` | | | | | | | | X | | | |
| `fvg_*` | | X | | X | X | X | | | | | |
| `ob_*` | X | | | | X | | | | | | |
| `choch_*` | | | X | | | | | | | | |
| `bos_*` | | | X | | | | | | | | |
| `current_trend` | | | X | | | | X | | | X | |
| `swing_*` | | | | | X | X | | X | | | X |
| `atr_14` | | X | | | X | | X | | | | |
| `adx_14` | | | | | | | X | | | | |
| `htf_*` | | | | | | | | | | X | |
| `eqh/eql_*` | | | | | | | | | | | X |
| `vp_*` | | | | | | | | | X | | |
| `liquidity_*` | | | | | | X | | | | | X |
| `prev_session_*` | | | | | | X | | | X | | |

### 3.2 Missing Field Alerts

Run this check before processing:

```python
MODULE_REQUIRED_FIELDS = {
    "module_02_fvg": ["fvg_detected", "fvg_type", "fvg_top", "fvg_bottom",
                      "fvg_gap_size", "fvg_creation_volume", "fvg_creation_delta",
                      "volume", "atr_14"],
    "module_03_structure": ["choch_detected", "choch_type", "choch_bars_ago",
                            "bos_detected", "bos_type", "bos_bars_ago",
                            "current_trend", "bars_since_structure_break"],
    "module_05_stop": ["fvg_top", "fvg_bottom", "fvg_type",
                       "nearest_ob_top", "nearest_ob_bottom",
                       "last_swing_high", "last_swing_low", "atr_14"],
    # ... etc
}

def validate_module_dependencies(bar: dict, module: str) -> list:
    """Return list of missing required fields for a module."""
    missing = []
    for field in MODULE_REQUIRED_FIELDS.get(module, []):
        if field not in bar or bar[field] is None:
            missing.append(field)
    return missing
```

---

## 4. IMPLEMENTATION ORDER

### Phase 1 - Core (Must Have)
1. Module #02 - FVG Quality (PRIMARY)
2. Module #03 - Structure Context
3. Module #05 - Stop Placement
4. Module #04 - Confluence (combines above)

### Phase 2 - Enhancement
5. Module #07 - Market Condition
6. Module #10 - MTF Alignment
7. Module #08 - Volume Divergence

### Phase 3 - Advanced
8. Module #01 - OB Quality
9. Module #06 - Target Placement
10. Module #09 - Volume Profile
11. Module #11 - Liquidity Map

---

## 5. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-11-21 | Initial matrix creation |
