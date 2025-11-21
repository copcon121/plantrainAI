# NINJA EXPORT CHECKLIST

## VERSION: 1.0
## PURPOSE: Comprehensive list of all fields required from NinjaTrader for all modules
## LAST UPDATED: 2024

---

## 1. OVERVIEW

This document contains the **complete list of fields** that the NinjaTrader indicator must export to JSONL for the Python pipeline to function.

### 1.1 Architecture Reminder

```
┌────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  NinjaTrader C# Indicator                                          │
│       │                                                            │
│       │  exports RAW data                                          │
│       ▼                                                            │
│  raw_smc_export.jsonl  ──────────────────────────────────────────►│
│       │                                                            │
│       │  Python Layer 2 processes                                  │
│       ▼                                                            │
│  bar_states.jsonl  (enriched with module calculations)             │
│       │                                                            │
│       ▼                                                            │
│  event_states.jsonl  (FVG signals only)                           │
│       │                                                            │
│       ▼                                                            │
│  ML Training Pipeline                                              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Principle

> **NinjaTrader exports RAW data only. NO scoring, NO complex logic.**
> All quality assessments, scores, and classifications happen in Python.

---

## 2. FIELD CATEGORIES

### 2.1 Summary by Category

| Category | Field Count | Source |
|----------|-------------|--------|
| Basic Bar Data | 8 | NinjaScript |
| Volume & Delta | 6 | Volume Delta indicators |
| SMC Events (OB) | 8 | Custom OB detection |
| SMC Events (FVG) | 12 | Custom FVG detection |
| SMC Events (CHoCH/BOS) | 4 | Custom CHoCH detection |
| Swing Structure | 6 | Swing indicator |
| Market Context | 4 | ATR, ADX |
| HTF Data | 7 | Multi-series |
| **TOTAL** | **55** | |

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

### 3.5 SMC Events - CHoCH/BOS (4 fields)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `choch_detected` | bool | Was CHoCH detected? | Module #03 |
| `choch_type` | string | "bullish" / "bearish" / null | Module #03 |
| `bos_detected` | bool | Was BOS detected? | Module #03 |
| `bos_type` | string | "bullish" / "bearish" / null | Module #03 |

```csharp
// NinjaScript Example
jsonBuilder.Append($"\"choch_detected\": {chochDetected.ToString().ToLower()}, ");
jsonBuilder.Append($"\"choch_type\": {(chochDetected ? $"\"{chochType}\"" : "null")}, ");
jsonBuilder.Append($"\"bos_detected\": {bosDetected.ToString().ToLower()}, ");
jsonBuilder.Append($"\"bos_type\": {(bosDetected ? $"\"{bosType}\"" : "null")}, ");
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

## 4. FIELD PRIORITY

### 4.1 MUST HAVE (Phase 1)

These fields are required for core functionality:

```json
// Minimum Viable Export
{
    // Bar basics
    "bar_index": 1000,
    "timestamp": "2024-01-15T09:30:00",
    "open": 100.00,
    "high": 100.50,
    "low": 99.80,
    "close": 100.30,
    "volume": 5000,

    // Volume delta
    "buy_volume": 3000,
    "sell_volume": 2000,
    "delta": 1000,
    "cumulative_delta": 15000,

    // FVG (PRIMARY SIGNAL)
    "fvg_detected": true,
    "fvg_type": "bullish",
    "fvg_top": 100.40,
    "fvg_bottom": 100.10,
    "fvg_bar_index": 998,
    "fvg_gap_size": 0.30,
    "fvg_creation_volume": 4500,
    "fvg_creation_delta": 900,

    // OB (context)
    "ob_detected": false,
    "nearest_ob_top": 100.80,
    "nearest_ob_bottom": 100.50,

    // Structure
    "is_swing_high": false,
    "is_swing_low": false,
    "last_swing_high": 100.60,
    "last_swing_low": 99.50,

    // CHoCH (context)
    "choch_detected": false,
    "bos_detected": false,

    // ATR
    "atr_14": 0.25
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
┌──────────────────────────────────────────────────────────────────┐
│                     MODULE DEPENDENCIES                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  NINJA EXPORT                                                    │
│       │                                                          │
│       ├──► Module #02 FVG Quality (PRIMARY)                     │
│       │        └──► Needs: FVG fields, volume, delta, ATR       │
│       │                                                          │
│       ├──► Module #01 OB Quality                                │
│       │        └──► Needs: OB fields                            │
│       │                                                          │
│       ├──► Module #03 Structure Context                         │
│       │        └──► Needs: CHoCH, BOS, swing fields             │
│       │                                                          │
│       ├──► Module #05 Stop Placement                            │
│       │        └──► Needs: FVG, OB, swing fields                │
│       │                                                          │
│       ├──► Module #06 Target Placement                          │
│       │        └──► Needs: swing, liquidity fields              │
│       │                                                          │
│       ├──► Module #07 Market Condition                          │
│       │        └──► Needs: ATR, ADX, OHLC                       │
│       │                                                          │
│       ├──► Module #08 Volume Divergence                         │
│       │        └──► Needs: swing, delta fields                  │
│       │                                                          │
│       ├──► Module #10 MTF Alignment                             │
│       │        └──► Needs: HTF fields                           │
│       │                                                          │
│       └──► Module #11 Liquidity Map                             │
│                └──► Needs: swing, liquidity fields              │
│                                                                  │
│       │                                                          │
│       ▼                                                          │
│  Module #04 Confluence                                          │
│       └──► Combines outputs from all above modules              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial checklist with all 55 fields |

---

## 9. NOTES

### 9.1 Performance Considerations
- Write JSONL incrementally (don't buffer entire session)
- Use StringBuilder for JSON construction
- Flush file periodically to avoid data loss

### 9.2 Data Quality
- Always validate field values before export
- Use null for missing optional fields (not 0 or empty string)
- Ensure consistent precision for floats (5 decimal places)

### 9.3 Future Extensions
- Add Volume Profile fields (Module #09)
- Add session markers (Asian/London/NY)
- Add news event flags
