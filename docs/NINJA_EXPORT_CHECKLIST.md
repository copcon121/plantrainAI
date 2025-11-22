# NINJA EXPORT CHECKLIST

## VERSION: 1.2
## PURPOSE: Comprehensive list of all fields required from NinjaTrader for all modules
## LAST UPDATED: November 21, 2025

---

## 0. CRITICAL META FIELDS (MUST HAVE FIRST)

### 0.1 Instrument Metadata (Per File Header or Per Bar)

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `schema_version` | string | Export format version (e.g., "1.1") | **MUST** |
| `symbol` | string | Instrument symbol (e.g., "ES", "NQ", "MES") | **MUST** |
| `expiry` | string | Contract expiry (e.g., "202412", "202503") | **MUST** |
| `timezone` | string | Data timezone (e.g., "America/New_York", "UTC") | **MUST** |
| `tick_size` | float | Minimum price increment (e.g., 0.25 for ES) | **MUST** |
| `point_value` | float | Dollar value per point (e.g., 50 for ES) | **MUST** |
| `exchange` | string | Exchange name (e.g., "CME", "COMEX") | Recommended |

```csharp
// NinjaScript Example - Write header line first
string headerJson = $@"{{
    ""schema_version"": ""1.1"",
    ""symbol"": ""{Instrument.MasterInstrument.Name}"",
    ""expiry"": ""{Instrument.Expiry:yyyyMM}"",
    ""timezone"": ""{Core.Globals.GeneralOptions.TimeZoneInfo.Id}"",
    ""tick_size"": {Instrument.MasterInstrument.TickSize},
    ""point_value"": {Instrument.MasterInstrument.PointValue},
    ""exchange"": ""{Instrument.Exchange}""
}}";
// Write header as first line
```

### 0.2 Session & Time Context (Per Bar)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `session_type` | string | "RTH" / "ETH" / "GLOBEX" | Session filtering |
| `session_name` | string | "Asian" / "London" / "NY_AM" / "NY_PM" | Module #07, #09 |
| `session_date` | string | Trading date YYYY-MM-DD | Session grouping |
| `session_bar_index` | int | Bar index within session (resets each day) | Module #09 VP |
| `is_session_open` | bool | Is this bar the session open? | Session analysis |
| `is_session_close` | bool | Is this bar the session close? | Session analysis |
| `minutes_into_session` | int | Minutes since session open | Time-based filters |

```csharp
// NinjaScript Example
jsonBuilder.Append($"\"session_type\": \"{(Bars.IsFirstBarOfSession ? "RTH" : GetSessionType())}\", ");
jsonBuilder.Append($"\"session_name\": \"{GetCurrentSessionName()}\", ");
jsonBuilder.Append($"\"session_date\": \"{Time[0]:yyyy-MM-dd}\", ");
jsonBuilder.Append($"\"session_bar_index\": {sessionBarIndex}, ");
jsonBuilder.Append($"\"is_session_open\": {Bars.IsFirstBarOfSession.ToString().ToLower()}, ");
```

### 0.3 Previous Session Reference (Per Bar)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `prev_session_high` | float | Previous session high | Module #06, #11 |
| `prev_session_low` | float | Previous session low | Module #06, #11 |
| `prev_session_close` | float | Previous session close | Gap analysis |
| `prev_session_vah` | float | Previous session VAH | Module #09 |
| `prev_session_val` | float | Previous session VAL | Module #09 |
| `prev_session_poc` | float | Previous session POC | Module #09 |

### 0.4 Data Quality Flags (Per Bar)

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `is_valid_bar` | bool | Is bar data complete/valid? | Data quality |
| `has_volume_data` | bool | Is volume data available? | Delta validation |
| `bid_ask_available` | bool | Is bid/ask data available? | Spread checks |
| `ask_price` | float | Current ask (optional for spread) | Spread analysis |
| `bid_price` | float | Current bid (optional for spread) | Spread analysis |

---

## 1. OVERVIEW

This document contains the **complete list of fields** that the NinjaTrader indicator must export to JSONL for the Python pipeline to function.

### 1.1 Architecture Reminder

```
+---------------------------------------------------------------+
|                           DATA FLOW                          |
+---------------------------------------------------------------+
| NinjaTrader C# Indicator                                     |
|   |                                                          |
|   |  exports RAW data                                        |
|   v                                                          |
|  raw_smc_export.jsonl  --->  Python Layer 2 processes        |
|                             |                                |
|                             v                                |
|                          bar_states.jsonl (enriched)         |
|                             |                                |
|                             v                                |
|                          event_states.jsonl (FVG signals)    |
|                             |                                |
|                             v                                |
|                        ML Training Pipeline                  |
+---------------------------------------------------------------+
```

### 1.2 Key Principle

> **NinjaTrader exports RAW data only. NO scoring, NO complex logic.**
> All quality assessments, scores, and classifications happen in Python.

---

## 2. FIELD CATEGORIES

### 2.1 Summary by Category

| Category | Field Count | Source | Priority |
|----------|-------------|--------|----------|
| **Meta & Instrument** | 7 | NinjaScript | **MUST** |
| **Session & Time** | 7 | Session management | **MUST** |
| **Previous Session** | 6 | Session tracking | HIGH |
| **Data Quality** | 5 | Validation | HIGH |
| Basic Bar Data | 8 | NinjaScript | **MUST** |
| Volume & Delta | 6 | Volume Delta indicators | **MUST** |
| SMC Events (OB) | 8 | Custom OB detection | **MUST** |
| SMC Events (FVG) | 12 | Custom FVG detection | **MUST** |
| SMC Events (CHoCH/BOS) | 16 | Custom CHoCH detection | **MUST** |
| Swing Structure | 6 | Swing indicator | **MUST** |
| Sweep (Top-level) | 2 | From bar pulses | HIGH |
| **EQH/EQL Detection** | 6 | Liquidity detection | HIGH |
| **Volume Profile** | 8 | VP indicator | MEDIUM |
| Market Context | 4 | ATR, ADX | **MUST** |
| HTF Data | 7 | Multi-series | HIGH |
| HTF Structure (pulses) | 4 | Higher TF CHoCH/BOS | HIGH |
| Liquidity Map | 6 | Liquidity tracking | HIGH |
| **TOTAL** | **~102** | | |

### 2.2 Priority Legend

| Priority | Meaning |
|----------|---------|
| **MUST** | Required for basic pipeline to function |
| HIGH | Important for full module functionality |
| MEDIUM | Enhanced features, can calculate in Python if needed |

---

## 3. COMPLETE FIELD LIST

### 3.1 Basic Bar Data (8 fields)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `bar_index` | int | Sequential bar number | All modules |
| `timestamp` | string | ISO format datetime | All modules |
| `open` | float | Bar open price | All modules |
| `high` | float | Bar high price | All modules |
| `low` | float | Bar low price | All modules |
| `close` | float | Bar close price | All modules |
| `volume` | int | Total bar volume | Module #02, #08 |
| `tick_count` | int | Number of ticks (optional) | Optional |

```csharp
// NinjaScript Example
jsonBuilder.Append($"\"bar_index\": {CurrentBar}, ");
jsonBuilder.Append($"\"timestamp\": \"{Time[0]:O}\", ");
jsonBuilder.Append($"\"open\": {Open[0]}, ");
jsonBuilder.Append($"\"high\": {High[0]}, ");
jsonBuilder.Append($"\"low\": {Low[0]}, ");
jsonBuilder.Append($"\"close\": {Close[0]}, ");
jsonBuilder.Append($"\"volume\": {Volume[0]}, ");
```

---

### 3.2 Volume & Delta (6 fields)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `buy_volume` | int | Volume at ask | Module #02, #08 |
| `sell_volume` | int | Volume at bid | Module #02, #08 |
| `delta` | int | buy_volume - sell_volume | Module #02, #08 |
| `cumulative_delta` | int | Running cumulative delta | Module #08 |
| `max_delta` | int | Max delta in bar (optional) | Optional |
| `min_delta` | int | Min delta in bar (optional) | Optional |

```csharp
// NinjaScript Example - requires OrderFlowVolumeProfile or similar
jsonBuilder.Append($"\"buy_volume\": {buyVol}, ");
jsonBuilder.Append($"\"sell_volume\": {sellVol}, ");
jsonBuilder.Append($"\"delta\": {buyVol - sellVol}, ");
jsonBuilder.Append($"\"cumulative_delta\": {cumulativeDelta}, ");
```

---

### 3.3 SMC Events - Order Block (8 fields)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `ob_detected` | bool | Was an OB formed? | Module #01, #04 |
| `ob_type` | string | "bullish" / "bearish" / null | Module #01, #04 |
| `ob_top` | float | OB upper boundary | Module #01, #04, #05 |
| `ob_bottom` | float | OB lower boundary | Module #01, #04, #05 |
| `ob_bar_index` | int | Bar index when OB formed | Module #01 |
| `nearest_ob_top` | float | Nearest relevant OB top | Module #04, #05 |
| `nearest_ob_bottom` | float | Nearest relevant OB bottom | Module #04, #05 |
| `nearest_ob_type` | string | Type of nearest OB | Module #04 |

```csharp
// NinjaScript Example
if (orderBlockDetected)
{
    jsonBuilder.Append($"\"ob_detected\": true, ");
    jsonBuilder.Append($"\"ob_type\": \"{obType}\", ");
    jsonBuilder.Append($"\"ob_top\": {obTop}, ");
    jsonBuilder.Append($"\"ob_bottom\": {obBottom}, ");
    jsonBuilder.Append($"\"ob_bar_index\": {obBarIndex}, ");
}
else
{
    jsonBuilder.Append("\"ob_detected\": false, ");
    jsonBuilder.Append("\"ob_type\": null, ");
    jsonBuilder.Append("\"ob_top\": null, ");
    jsonBuilder.Append("\"ob_bottom\": null, ");
}
```

---

### 3.4 SMC Events - Fair Value Gap (12 fields)

**Core FVG Fields (8):**

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `fvg_detected` | bool | Was an FVG formed? | Module #02 (PRIMARY) |
| `fvg_type` | string | "bullish" / "bearish" / null | Module #02 |
| `fvg_top` | float | FVG upper boundary | Module #02, #05 |
| `fvg_bottom` | float | FVG lower boundary | Module #02, #05 |
| `fvg_bar_index` | int | Bar index when FVG formed | Module #02 |
| `fvg_gap_size` | float | fvg_top - fvg_bottom | Module #02 |
| `fvg_filled` | bool | Has FVG been filled? | Module #02 |
| `fvg_fill_percentage` | float | % of FVG that's been filled | Module #02 |

**FVG Strength Fields (4) - NEW in v2.0:**

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `fvg_creation_volume` | int | Volume on FVG middle bar | Module #02 |
| `fvg_creation_buy_vol` | int | Buy volume on FVG bar | Module #02 |
| `fvg_creation_sell_vol` | int | Sell volume on FVG bar | Module #02 |
| `fvg_creation_delta` | int | Delta on FVG bar | Module #02 |

```csharp
// NinjaScript Example - FVG Detection
if (fvgDetected)
{
    jsonBuilder.Append($"\"fvg_detected\": true, ");
    jsonBuilder.Append($"\"fvg_type\": \"{fvgType}\", ");
    jsonBuilder.Append($"\"fvg_top\": {fvgTop}, ");
    jsonBuilder.Append($"\"fvg_bottom\": {fvgBottom}, ");
    jsonBuilder.Append($"\"fvg_bar_index\": {fvgBarIndex}, ");
    jsonBuilder.Append($"\"fvg_gap_size\": {fvgTop - fvgBottom}, ");
    jsonBuilder.Append($"\"fvg_filled\": {fvgFilled.ToString().ToLower()}, ");
    jsonBuilder.Append($"\"fvg_fill_percentage\": {fvgFillPct}, ");

    // Strength fields (from the bar that created the FVG)
    jsonBuilder.Append($"\"fvg_creation_volume\": {fvgVolume}, ");
    jsonBuilder.Append($"\"fvg_creation_buy_vol\": {fvgBuyVol}, ");
    jsonBuilder.Append($"\"fvg_creation_sell_vol\": {fvgSellVol}, ");
    jsonBuilder.Append($"\"fvg_creation_delta\": {fvgDelta}, ");
}
```

---

### 3.5 SMC Events - CHoCH/BOS (12 fields) - EXPANDED for Module #03

**Core Detection (4 fields):**

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `choch_detected` | bool | Was CHoCH detected? | Module #03 |
| `choch_type` | string | "bullish" / "bearish" / null | Module #03 |
| `bos_detected` | bool | Was BOS detected? | Module #03 |
| `bos_type` | string | "bullish" / "bearish" / null | Module #03 |

**CHoCH Details (4 fields) - NEW for Structure Context:**

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `choch_price` | float | Price level where CHoCH occurred | Module #03 |
| `choch_bar_index` | int | Bar index of CHoCH | Module #03 |
| `choch_bars_ago` | int | Bars since CHoCH (age) | Module #03 |
| `choch_swing_broken` | float | Price of swing that was broken | Module #03 |

**BOS Details (4 fields) - NEW for Structure Context:**

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `bos_price` | float | Price level where BOS occurred | Module #03 |
| `bos_bar_index` | int | Bar index of BOS | Module #03 |
| `bos_bars_ago` | int | Bars since BOS (age) | Module #03 |
| `bos_swing_broken` | float | Price of swing that was broken | Module #03 |

**Trend State (4 fields) - NEW for Structure Context:**

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `current_trend` | string | "bullish" / "bearish" / "neutral" | Module #03, #07 |
| `trend_swing_count` | int | Number of swings in current trend | Module #03 |
| `last_structure_break` | string | "choch" / "bos" / "none" | Module #03 |
| `bars_since_structure_break` | int | Bars since last CHoCH or BOS | Module #03 |

```csharp
// NinjaScript Example - Expanded CHoCH/BOS
jsonBuilder.Append($"\"choch_detected\": {chochDetected.ToString().ToLower()}, ");
jsonBuilder.Append($"\"choch_type\": {(chochDetected ? $"\"{chochType}\"" : "null")}, ");
jsonBuilder.Append($"\"choch_price\": {(chochDetected ? chochPrice.ToString() : "null")}, ");
jsonBuilder.Append($"\"choch_bar_index\": {(chochDetected ? chochBarIndex.ToString() : "null")}, ");
jsonBuilder.Append($"\"choch_bars_ago\": {chochBarsAgo}, ");
jsonBuilder.Append($"\"choch_swing_broken\": {(chochDetected ? chochSwingBroken.ToString() : "null")}, ");

jsonBuilder.Append($"\"bos_detected\": {bosDetected.ToString().ToLower()}, ");
jsonBuilder.Append($"\"bos_type\": {(bosDetected ? $"\"{bosType}\"" : "null")}, ");
jsonBuilder.Append($"\"bos_price\": {(bosDetected ? bosPrice.ToString() : "null")}, ");
jsonBuilder.Append($"\"bos_bar_index\": {(bosDetected ? bosBarIndex.ToString() : "null")}, ");
jsonBuilder.Append($"\"bos_bars_ago\": {bosBarsAgo}, ");
jsonBuilder.Append($"\"bos_swing_broken\": {(bosDetected ? bosSwingBroken.ToString() : "null")}, ");

// Trend state
jsonBuilder.Append($"\"current_trend\": \"{currentTrend}\", ");
jsonBuilder.Append($"\"trend_swing_count\": {trendSwingCount}, ");
jsonBuilder.Append($"\"last_structure_break\": \"{lastStructureBreak}\", ");
jsonBuilder.Append($"\"bars_since_structure_break\": {barsSinceStructureBreak}, ");
```

---

### 3.6 Swing Structure (6 fields)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `is_swing_high` | bool | Is this bar a swing high? | Module #03, #05, #06, #08 |
| `is_swing_low` | bool | Is this bar a swing low? | Module #03, #05, #06, #08 |
| `last_swing_high` | float | Most recent swing high price | Module #05, #06 |
| `last_swing_low` | float | Most recent swing low price | Module #05, #06 |
| `recent_swing_high` | float | Recent swing high (lookback) | Module #05, #06 |
| `recent_swing_low` | float | Recent swing low (lookback) | Module #05, #06 |

```csharp
// NinjaScript Example - using Swing indicator
Swing swing = Swing(5);  // 5-bar swing strength

jsonBuilder.Append($"\"is_swing_high\": {(swing.SwingHighBar(0, 1, 10) == 0).ToString().ToLower()}, ");
jsonBuilder.Append($"\"is_swing_low\": {(swing.SwingLowBar(0, 1, 10) == 0).ToString().ToLower()}, ");
jsonBuilder.Append($"\"last_swing_high\": {swing.SwingHigh[0]}, ");
jsonBuilder.Append($"\"last_swing_low\": {swing.SwingLow[0]}, ");
```

---

### 3.7 Market Context (4 fields)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `atr_14` | float | 14-period ATR | Module #02, #05, #07 |
| `adx_14` | float | 14-period ADX (optional) | Module #07 |
| `di_plus_14` | float | DI+ (optional) | Module #07 |
| `di_minus_14` | float | DI- (optional) | Module #07 |

```csharp
// NinjaScript Example
ATR atr = ATR(14);
ADX adx = ADX(14);

jsonBuilder.Append($"\"atr_14\": {atr[0]}, ");
jsonBuilder.Append($"\"adx_14\": {adx[0]}, ");
jsonBuilder.Append($"\"di_plus_14\": {adx.DiPlus[0]}, ");
jsonBuilder.Append($"\"di_minus_14\": {adx.DiMinus[0]}, ");
```

---

### 3.8 HTF Data - Multi-Timeframe (7 fields)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `htf_high` | float | Higher TF bar high | Module #10 |
| `htf_low` | float | Higher TF bar low | Module #10 |
| `htf_close` | float | Higher TF bar close | Module #10 |
| `htf_ema_20` | float | HTF 20 EMA (optional) | Module #10 |
| `htf_ema_50` | float | HTF 50 EMA (optional) | Module #10 |
| `htf_is_swing_high` | bool | HTF swing high | Module #10 |
| `htf_is_swing_low` | bool | HTF swing low | Module #10 |
| `htf_bos_type` | string | HTF BOS direction | Module #10 |
| `htf_bos_bars_ago` | int | Bars since HTF BOS | Module #10 |
| `htf_choch_type` | string | HTF CHoCH direction | Module #10 |
| `htf_choch_bars_ago` | int | Bars since HTF CHoCH | Module #10 |

```csharp
// NinjaScript Example - Multi-series
// Add secondary series in OnStateChange
AddDataSeries(BarsPeriodType.Minute, 60);  // 1H HTF

// In OnBarUpdate
if (BarsInProgress == 0)  // Primary series (5m)
{
    int htfBarIndex = BarsArray[1].GetBar(Time[0]);

    jsonBuilder.Append($"\"htf_high\": {Highs[1][htfBarIndex]}, ");
    jsonBuilder.Append($"\"htf_low\": {Lows[1][htfBarIndex]}, ");
    jsonBuilder.Append($"\"htf_close\": {Closes[1][htfBarIndex]}, ");
    // ... EMAs and swings similarly
}
```

---

### 3.9 Liquidity Map (6 fields) - Module #11

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `nearest_liquidity_high` | float | Nearest untested high liquidity | Module #04, #06, #11 |
| `nearest_liquidity_low` | float | Nearest untested low liquidity | Module #04, #06, #11 |
| `liquidity_high_type` | string | "equal_highs" / "swing" / null | Module #04, #11 |
| `liquidity_low_type` | string | "equal_lows" / "swing" / null | Module #04, #11 |
| `liquidity_high_tested` | bool | Has high liquidity been tested? | Module #11 |
| `liquidity_low_tested` | bool | Has low liquidity been tested? | Module #11 |

---

### 3.10 EQH/EQL Detection (6 fields) - Module #11

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `eqh_detected` | bool | Equal Highs detected at this bar? | Module #11 |
| `eqh_price` | float | Price level of equal highs | Module #11 |
| `eqh_count` | int | Number of touches at this level | Module #11 |
| `eqh_touches` | int | Touch count (alias/count) | Module #11 |
| `eql_detected` | bool | Equal Lows detected at this bar? | Module #11 |
| `eql_price` | float | Price level of equal lows | Module #11 |
| `eql_count` | int | Number of touches at this level | Module #11 |
| `eql_touches` | int | Touch count (alias/count) | Module #11 |

```csharp
// NinjaScript Example - EQH/EQL Detection
// Equal Highs: Multiple swing highs within tolerance (e.g., 2 ticks)
jsonBuilder.Append($"\"eqh_detected\": {eqhDetected.ToString().ToLower()}, ");
jsonBuilder.Append($"\"eqh_price\": {(eqhDetected ? eqhPrice : "null")}, ");
jsonBuilder.Append($"\"eqh_count\": {eqhCount}, ");
jsonBuilder.Append($"\"eql_detected\": {eqlDetected.ToString().ToLower()}, ");
jsonBuilder.Append($"\"eql_price\": {(eqlDetected ? eqlPrice : "null")}, ");
jsonBuilder.Append($"\"eql_count\": {eqlCount}, ");
```

---

### 3.11 Volume Profile Session Data (8 fields) - Module #09

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `vp_session_poc` | float | Current session POC | Module #09 |
| `vp_session_vah` | float | Current session VAH | Module #09, #11 |
| `vp_session_val` | float | Current session VAL | Module #09, #11 |
| `vp_session_volume` | int | Total session volume so far | Module #09 |
| `vp_value_area_pct` | float | % of volume in VA (typically 70%) | Module #09 |
| `vp_developing_poc` | float | Developing POC (updates each bar) | Module #09 |
| `vp_high_volume_nodes` | string | JSON array of HVN prices | Module #09 |
| `vp_low_volume_nodes` | string | JSON array of LVN prices | Module #09 |
| `tick_size` | float | Tick size (if per-bar different instrument) | Module #09 bin sizing |

**Note:** Volume Profile can be calculated in Python from tick data, but if NinjaTrader has built-in VP indicator, exporting these fields saves computation.

---

## 4. FIELD PRIORITY

### 4.1 MUST HAVE (Phase 1)

These fields are required for core functionality:

```json
// Minimum Viable Export
{
    // === META (CRITICAL) ===
    "schema_version": "1.1",
    "symbol": "ES",
    "expiry": "202503",
    "timezone": "America/New_York",
    "tick_size": 0.25,
    "point_value": 50.0,

    // === SESSION (CRITICAL) ===
    "session_type": "RTH",
    "session_name": "NY_AM",
    "session_date": "2024-01-15",
    "session_bar_index": 45,

    // === BAR BASICS ===
    "bar_index": 1000,
    "timestamp": "2024-01-15T09:30:00-05:00",
    "open": 5000.00,
    "high": 5002.50,
    "low": 4998.00,
    "close": 5001.25,
    "volume": 5000,

    // === VOLUME DELTA ===
    "buy_volume": 3000,
    "sell_volume": 2000,
    "delta": 1000,
    "cumulative_delta": 15000,

    // === FVG (PRIMARY SIGNAL) ===
    "fvg_detected": true,
    "fvg_type": "bullish",
    "fvg_top": 5001.00,
    "fvg_bottom": 4999.50,
    "fvg_bar_index": 998,
    "fvg_gap_size": 1.50,
    "fvg_creation_volume": 4500,
    "fvg_creation_delta": 900,

    // === OB (CONTEXT) ===
    "ob_detected": false,
    "nearest_ob_top": 5005.00,
    "nearest_ob_bottom": 5003.50,

    // === STRUCTURE ===
    "is_swing_high": false,
    "is_swing_low": false,
    "last_swing_high": 5010.00,
    "last_swing_low": 4990.00,

    // === CHOCH (CONTEXT) ===
    "choch_detected": false,
    "bos_detected": false,

    // === ATR ===
    "atr_14": 12.50,

    // === PREVIOUS SESSION ===
    "prev_session_high": 5015.00,
    "prev_session_low": 4985.00,
    "prev_session_close": 5000.00
}
```

### 4.2 NICE TO HAVE (Phase 2)

Additional fields for enhanced analysis:

```json
// Phase 2 additions
{
    // ADX for market condition
    "adx_14": 28.5,
    "di_plus_14": 22.0,
    "di_minus_14": 15.0,

    // HTF for MTF alignment
    "htf_high": 101.20,
    "htf_low": 99.80,
    "htf_close": 100.50,
    "htf_ema_20": 100.30,
    "htf_ema_50": 100.00,

    // Liquidity map
    "nearest_liquidity_high": 101.00,
    "nearest_liquidity_low": 99.20,
    "liquidity_high_type": "equal_highs"
}
```

---

## 5. JSON OUTPUT FORMAT

### 5.1 Complete Example

```json
{
    "bar_index": 1250,
    "timestamp": "2024-01-15T10:45:00",
    "open": 100.15,
    "high": 100.55,
    "low": 100.05,
    "close": 100.45,
    "volume": 4500,

    "buy_volume": 2800,
    "sell_volume": 1700,
    "delta": 1100,
    "cumulative_delta": 18500,

    "fvg_detected": true,
    "fvg_type": "bullish",
    "fvg_top": 100.40,
    "fvg_bottom": 100.20,
    "fvg_bar_index": 1248,
    "fvg_gap_size": 0.20,
    "fvg_filled": false,
    "fvg_fill_percentage": 0.0,
    "fvg_creation_volume": 5200,
    "fvg_creation_buy_vol": 3500,
    "fvg_creation_sell_vol": 1700,
    "fvg_creation_delta": 1800,

    "ob_detected": false,
    "ob_type": null,
    "ob_top": null,
    "ob_bottom": null,
    "nearest_ob_top": 100.80,
    "nearest_ob_bottom": 100.50,
    "nearest_ob_type": "bullish",

    "choch_detected": false,
    "choch_type": null,
    "bos_detected": true,
    "bos_type": "bullish",

    "is_swing_high": false,
    "is_swing_low": false,
    "last_swing_high": 100.70,
    "last_swing_low": 99.80,
    "recent_swing_high": 100.70,
    "recent_swing_low": 99.80,

    "atr_14": 0.22,
    "adx_14": 32.5,
    "di_plus_14": 25.0,
    "di_minus_14": 12.0,

    "htf_high": 101.00,
    "htf_low": 99.50,
    "htf_close": 100.40,
    "htf_ema_20": 100.20,
    "htf_ema_50": 99.90,
    "htf_is_swing_high": false,
    "htf_is_swing_low": false,

    "nearest_liquidity_high": 100.90,
    "nearest_liquidity_low": 99.40,
    "liquidity_high_type": "swing",
    "liquidity_low_type": "equal_lows"
}
```

### 5.2 File Format

```
// raw_smc_export.jsonl
// One JSON object per line, one line per bar

{"bar_index":1248,...}
{"bar_index":1249,...}
{"bar_index":1250,...}
```

---

## 6. IMPLEMENTATION CHECKLIST

### 6.1 NinjaTrader Indicator Tasks

- [ ] **Basic Bar Data**
  - [ ] Export OHLCV for each bar
  - [ ] Include timestamp in ISO format
  - [ ] Include bar_index

- [ ] **Volume Delta**
  - [ ] Integrate with Volume Delta indicator
  - [ ] Export buy_volume, sell_volume, delta
  - [ ] Track cumulative_delta

- [ ] **FVG Detection**
  - [ ] Implement 3-bar FVG detection logic
  - [ ] Track FVG boundaries (top/bottom)
  - [ ] Track FVG fill status
  - [ ] Capture creation bar volume/delta

- [ ] **OB Detection**
  - [ ] Implement OB detection logic
  - [ ] Track nearest relevant OB
  - [ ] Export OB boundaries

- [ ] **CHoCH/BOS Detection**
  - [ ] Implement CHoCH detection
  - [ ] Implement BOS detection
  - [ ] Export type (bullish/bearish)

- [ ] **Swing Structure**
  - [ ] Use Swing indicator or custom
  - [ ] Export is_swing_high/low flags
  - [ ] Track recent swing prices

- [ ] **Market Context**
  - [ ] Add ATR(14) indicator
  - [ ] Add ADX(14) indicator (optional)
  - [ ] Export values

- [ ] **HTF Data**
  - [ ] Add secondary data series
  - [ ] Export HTF OHLC
  - [ ] Export HTF EMAs (optional)
  - [ ] Export HTF swings

- [ ] **File Output**
  - [ ] Write to JSONL format
  - [ ] Append mode (not overwrite)
  - [ ] Flush after each bar

### 6.2 Validation Tasks

- [ ] Verify JSON format is valid
- [ ] Check all required fields are present
- [ ] Validate data types (int vs float vs string)
- [ ] Test with Python loader
- [ ] Verify field values make sense (no nulls for required fields)

---

## 7. MODULE DEPENDENCY MAP

```
+-------------------------------------------------------------+
|                     MODULE DEPENDENCIES                     |
+-------------------------------------------------------------+
|  NINJA EXPORT                                               |
|      |                                                      |
|      +--> Module #02 FVG Quality (PRIMARY)                  |
|      |        \--> Needs: FVG fields, volume, delta, ATR    |
|      |                                                      |
|      +--> Module #01 OB Quality                             |
|      |        \--> Needs: OB fields                         |
|      |                                                      |
|      +--> Module #03 Structure Context                      |
|      |        \--> Needs: CHoCH, BOS, swing fields          |
|      |                                                      |
|      +--> Module #05 Stop Placement                         |
|      |        \--> Needs: FVG, OB, swing fields             |
|      |                                                      |
|      +--> Module #06 Target Placement                       |
|      |        \--> Needs: swing, liquidity fields           |
|      |                                                      |
|      +--> Module #07 Market Condition                       |
|      |        \--> Needs: ATR, ADX, OHLC                    |
|      |                                                      |
|      +--> Module #08 Volume Divergence                      |
|      |        \--> Needs: swing, delta fields               |
|      |                                                      |
|      +--> Module #10 MTF Alignment                          |
|      |        \--> Needs: HTF fields                        |
|      |                                                      |
|      \--> Module #11 Liquidity Map                          |
|               \--> Needs: swing, liquidity fields           |
|                                                          |
|      |                                                      |
|      v                                                      |
|  Module #04 Confluence                                      |
|         \--> Combines outputs from all above modules        |
+-------------------------------------------------------------+
```

---

## 8. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial checklist with 55 fields |
| 1.1 | 2024-11-21 | Added: Meta/Instrument (7), Session/Time (7), Prev Session (6), Data Quality (5), EQH/EQL (6), VP (8), Expanded CHoCH/BOS (16). Total: ~102 fields |
| 1.2 | 2025-11-21 | Added HTF BOS/CHoCH fields, EQH/EQL touch counts, tick_size note for VP binning, clarified DI/ATR percentile use in Market Condition. |

---

## 9. NOTES

### 9.1 Performance Considerations
- Write JSONL incrementally (don't buffer entire session)
- Use StringBuilder for JSON construction
- Flush file periodically to avoid data loss
- Consider separate files per session for large datasets

### 9.2 Data Quality
- Always validate field values before export
- Use null for missing optional fields (not 0 or empty string)
- Ensure consistent precision for floats (5 decimal places for price, 3 for ratios)
- Validate: `buy_volume + sell_volume ≈ volume` (within 5% tolerance)
- Validate: `delta = buy_volume - sell_volume`

### 9.3 Schema Versioning
- Always include `schema_version` in header
- Update version when adding/removing fields
- Python loader should check schema version compatibility

---

## 10. IMPLEMENTATION NOTES

### 10.1 Module #01 OB Quality - Special Considerations

> **OB là context, không phải signal riêng.**

OB Quality cần:
- `ob_displacement_rr`: Calculated from leg move / OB size
- `ob_volume_factor`: ob_volume / median_volume_20
- `ob_delta_imbalance`: |delta| / volume on OB bar
- `ob_sweep_before`: Was there a liquidity sweep before OB formed?

**Validation before use:**
1. Sync OB detection với FVG event builder
2. Labeling/correlation check: Does OB quality correlate with FVG win rate?
3. Only use as FVG context feature after validation passes

### 10.2 Module #03 Structure Context - Dependencies

Cần CHoCH/BOS details đầy đủ:
- `choch_price`, `choch_bars_ago` → For expansion detection
- `bos_price`, `bos_bars_ago` → For continuation detection
- `current_trend`, `trend_swing_count` → For context tagging

**Context Types:**
- **Expansion**: After CHoCH, new trend starting
- **Retracement**: Pullback in existing trend (after BOS)
- **Continuation**: Mid-trend, no recent structure break

### 10.3 Module #11 Liquidity Map - EQH/EQL Detection

**Equal Highs/Lows Definition:**
- Multiple swing points within tolerance (e.g., 2 ticks for ES)
- Minimum 2 touches to qualify as EQH/EQL
- Track untested vs tested status

**Fields needed:**
- `eqh_price`, `eql_price` → Liquidity levels
- `eqh_count`, `eql_count` → Number of touches (more = stronger liquidity)
- `prev_session_vah`, `prev_session_val` → Session-based liquidity

### 10.4 RTH vs ETH Handling

**RTH (Regular Trading Hours):**
- Primary session for analysis
- Higher volume, more reliable signals
- Session markers: NY_AM, NY_PM

**ETH (Extended Trading Hours):**
- Globex overnight session
- Lower volume, wider spreads
- Use for overnight gap analysis only

**Recommendation:** Filter most signals to RTH only, use ETH data for context.

### 10.5 Spread/Bid-Ask Sanity Checks

Before exporting:
```csharp
// Validate spread is reasonable
double spread = Ask[0] - Bid[0];
bool validSpread = spread > 0 && spread < 10 * TickSize;

// Validate bid/ask vs OHLC
bool bidAskValid = Bid[0] <= Close[0] && Ask[0] >= Close[0];

jsonBuilder.Append($"\"is_valid_bar\": {(validSpread && bidAskValid).ToString().ToLower()}, ");
```

---

## 11. PYTHON LOADER REQUIREMENTS

### 11.1 Schema Validation

```python
REQUIRED_FIELDS = [
    "schema_version", "symbol", "expiry", "timezone", "tick_size",
    "bar_index", "timestamp", "open", "high", "low", "close", "volume",
    "buy_volume", "sell_volume", "delta",
    "fvg_detected", "fvg_type", "fvg_top", "fvg_bottom",
    "atr_14"
]

def validate_bar(bar: dict) -> bool:
    """Validate bar has all required fields."""
    for field in REQUIRED_FIELDS:
        if field not in bar:
            return False
    return True
```

### 11.2 Data Integrity Checks

```python
def validate_data_integrity(bar: dict) -> list:
    """Check data integrity, return list of warnings."""
    warnings = []

    # Delta consistency
    expected_delta = bar.get("buy_volume", 0) - bar.get("sell_volume", 0)
    if abs(bar.get("delta", 0) - expected_delta) > 1:
        warnings.append("delta_mismatch")

    # OHLC consistency
    if bar["high"] < max(bar["open"], bar["close"]):
        warnings.append("high_invalid")
    if bar["low"] > min(bar["open"], bar["close"]):
        warnings.append("low_invalid")

    # Volume sanity
    if bar["volume"] <= 0:
        warnings.append("zero_volume")

    return warnings
```
