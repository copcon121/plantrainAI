# 📊 PHASE 1: INDICATOR EXPORT SPECIFICATION

**Version:** 2.0.0 (Nov 21, 2025)
**Purpose:** Define all fields that NinjaTrader indicator must export for offline processing
**Output File:** `raw_smc_export.jsonl` (one JSON object per line)
**Status:** 🟡 In Progress - Awaiting Implementation

---

## ⚠️ CRITICAL DESIGN DECISIONS (Nov 2025)

### 1. FVG is the ONLY Signal Type
- **FVG retest is the ONLY signal type** for ML training
- **OB/CHoCH are context ONLY** - not separate signals
- Export must support FVG Quality Module v2.0

### 2. Layer 1 (Ninja) = RAW ONLY
All complex calculations happen in Python:
- FVG Strength scoring
- Penetration ratio calculation
- Rebalance detection
- Adaptive entry logic

### 3. Required Raw Data for FVG Quality v2.0
| FVG Component | Required Raw Data from Ninja |
|---------------|------------------------------|
| FVG Strength | fvg_high, fvg_low, volume, buy_volume, sell_volume, delta |
| Retest Geometry | OHLCV per bar (Python detects retest) |
| Rebalance Detection | fvg_left_bar_index, fvg_right_bar_index (Python tracks FVG history) |
| Adaptive Entry | atr_14, fvg boundaries |

---

## 🎯 OVERVIEW

This document defines the complete data contract between:
- **Layer 1 (C# Indicator):** NinjaTrader exports raw data
- **Layer 2 (Python Processor):** Reads raw data, applies 11 modules

**Key Principle:** Indicator should be LIGHTWEIGHT and export RAW data only. All complex calculations happen in Python.

---

## 📋 EXPORT FIELDS CHECKLIST

### 1️⃣ Basic Bar Information (7 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `time_utc` | string | Bar time in ISO 8601 UTC | `"2025-11-20T10:30:00Z"` |
| `time_local` | string | Bar time in local timezone | `"2025-11-20T17:30:00+07:00"` |
| `open` | float | Bar open price | `1.23450` |
| `high` | float | Bar high price | `1.23500` |
| `low` | float | Bar low price | `1.23400` |
| `close` | float | Bar close price | `1.23480` |
| `volume` | int | Total bar volume | `1250` |

**Validation:**
- ✅ All prices have 5 decimal places
- ✅ `high >= max(open, close)`
- ✅ `low <= min(open, close)`
- ✅ `volume > 0`

---

### 2️⃣ Volume Delta Information (4 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `buy_volume` | int | Volume traded at ask | `750` |
| `sell_volume` | int | Volume traded at bid | `500` |
| `delta` | int | buy_volume - sell_volume | `250` |
| `cumulative_delta` | int | Running sum of delta | `1500` |

**Source:** Volumedelta indicator
**Validation:**
- ✅ `buy_volume + sell_volume = volume`
- ✅ `delta = buy_volume - sell_volume`
- ✅ `cumulative_delta` updates each bar

---

### 3️⃣ Order Block Detection (12 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ob_detected` | bool | Was OB detected this bar? | `true` |
| `ob_type` | string | "bullish" or "bearish" | `"bullish"` |
| `ob_high` | float | OB zone high | `1.23500` |
| `ob_low` | float | OB zone low | `1.23450` |
| `ob_extreme` | float | OB extreme point (low for bull, high for bear) | `1.23450` |
| `ob_volume` | int | Volume of OB creation bar | `1800` |
| `ob_buy_volume` | int | Buy volume of OB bar | `1200` |
| `ob_sell_volume` | int | Sell volume of OB bar | `600` |
| `ob_delta` | int | Delta of OB bar | `600` |
| `ob_bars_ago` | int | Bars since OB creation | `5` |
| `ob_displacement_target` | float | Price level OB displaced to | `1.23600` |
| `ob_liquidity_sweep` | bool | Did OB sweep liquidity before forming? | `false` |

**Source:** SMC_Structure indicator
**Validation:**
- ✅ If `ob_detected = false`, all other `ob_*` fields are `null`
- ✅ If `ob_detected = true`, all `ob_*` fields must be present
- ✅ For bullish OB: `ob_extreme = ob_low`
- ✅ For bearish OB: `ob_extreme = ob_high`
- ✅ `ob_buy_volume + ob_sell_volume = ob_volume`

---

### 4️⃣ Fair Value Gap Detection (14 fields) - 🔴 CRITICAL FOR FVG QUALITY v2.0

| Field | Type | Description | Example | Used By |
|-------|------|-------------|---------|---------|
| `fvg_detected` | bool | Was FVG detected this bar? | `true` | All |
| `fvg_type` | string | "bullish" or "bearish" | `"bullish"` | All |
| `fvg_high` | float | FVG zone high | `1.23550` | **Strength, Entry** |
| `fvg_low` | float | FVG zone low | `1.23520` | **Strength, Entry** |
| `fvg_gap_size` | float | fvg_high - fvg_low | `0.00030` | **Strength** |
| `fvg_bars_ago` | int | Bars since FVG creation | `3` | Age tracking |
| `fvg_filled_percent` | float | % of gap filled (0-100) | `25.5` | Fill tracking |
| `fvg_still_open` | bool | Is FVG still unfilled? | `true` | Retest detection |
| `fvg_left_bar_index` | int | Bar index before gap | `1234` | **Rebalance** |
| `fvg_right_bar_index` | int | Bar index after gap | `1236` | **Rebalance** |
| `fvg_creation_volume` | int | Volume on FVG middle bar | `2500` | **Strength** |
| `fvg_creation_buy_vol` | int | Buy volume on FVG bar | `2000` | **Strength** |
| `fvg_creation_sell_vol` | int | Sell volume on FVG bar | `500` | **Strength** |
| `fvg_creation_delta` | int | Delta on FVG bar | `1500` | **Strength** |

**Source:** SMC_Structure indicator
**Validation:**
- ✅ If `fvg_detected = false`, all other `fvg_*` fields are `null`
- ✅ `fvg_gap_size = fvg_high - fvg_low`
- ✅ `fvg_filled_percent` between 0 and 100
- ✅ If `fvg_filled_percent >= 100`, then `fvg_still_open = false`
- ✅ `fvg_right_bar_index > fvg_left_bar_index` (should be at least +2)
- ✅ `fvg_creation_buy_vol + fvg_creation_sell_vol = fvg_creation_volume`

**🔴 CRITICAL for FVG Quality v2.0:**
These fields enable Python to calculate:

| Python Calculation | Required Raw Fields |
|-------------------|---------------------|
| `fvg_size_atr` | fvg_gap_size, atr_14 |
| `fvg_vol_ratio` | fvg_creation_volume, volume_sma_20 |
| `fvg_delta_ratio` | fvg_creation_delta, fvg_creation_volume |
| `fvg_delta_alignment` | fvg_type, fvg_creation_delta |
| Rebalance detection | fvg_left_bar_index, fvg_right_bar_index + FVG history |
| Penetration ratio | fvg_high, fvg_low + current bar OHLCV |
| Adaptive entry | fvg_high, fvg_low, atr_14 |

---

### 5️⃣ CHoCH Detection (6 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `choch_detected` | bool | Was CHoCH detected this bar? | `true` |
| `choch_type` | string | "bullish" or "bearish" | `"bullish"` |
| `choch_price` | float | Price where CHoCH occurred | `1.23520` |
| `choch_bars_ago` | int | Bars since CHoCH | `2` |
| `choch_swing_high` | float | Swing high broken | `1.23500` |
| `choch_swing_low` | float | Swing low broken | `1.23400` |

**Source:** SMC_Structure indicator
**Validation:**
- ✅ If `choch_detected = false`, all other `choch_*` fields are `null`
- ✅ For bullish CHoCH: `choch_price > choch_swing_high`
- ✅ For bearish CHoCH: `choch_price < choch_swing_low`

---

### 6️⃣ Market Structure (5 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `current_trend` | string | "uptrend", "downtrend", "sideways" | `"uptrend"` |
| `last_swing_high` | float | Most recent swing high | `1.23600` |
| `last_swing_low` | float | Most recent swing low | `1.23350` |
| `structure_broken` | bool | Was structure broken this bar? | `false` |
| `atr_14` | float | 14-period ATR | `0.00025` |

**Source:** SMC_Structure indicator
**Validation:**
- ✅ `last_swing_high > last_swing_low`
- ✅ `atr_14 > 0`
- ✅ `current_trend` is one of: "uptrend", "downtrend", "sideways"

---

### 6️⃣A Equal Highs/Lows Detection (4 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `eq_highs_detected` | bool | Equal highs detected in recent bars? | `true` |
| `eq_lows_detected` | bool | Equal lows detected in recent bars? | `false` |
| `eq_high_price` | float | Price level of equal highs | `1.23600` |
| `eq_low_price` | float | Price level of equal lows | `null` |

**Source:** SMC_Structure indicator (optional - Python can also detect from swing history)
**Validation:**
- ✅ If `eq_highs_detected = false`, then `eq_high_price = null`
- ✅ If `eq_lows_detected = false`, then `eq_low_price = null`
- ✅ Equal highs = 2+ swing highs within 2 ticks of each other (last 20 bars)
- ✅ Equal lows = 2+ swing lows within 2 ticks of each other (last 20 bars)

**Purpose for Liquidity Map:**
Equal highs/lows are liquidity zones that price often sweeps before reversing. These fields help Python:
1. Build comprehensive liquidity map (not just HL/LL)
2. Detect sweeps of EQH/EQL (common trap pattern)
3. Identify "liquidity before structure" that gets hit before actual HL/LL

**Note:** This is OPTIONAL. If not exported from NinjaTrader, Python can detect EQH/EQL from swing history.

---

### 7️⃣ Volume Statistics (5 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `volume_sma_20` | float | 20-bar SMA of volume | `1100.5` |
| `volume_percentile` | float | Current volume vs last 100 bars (0-100) | `75.5` |
| `high_volume_bar` | bool | Is volume > 1.5x average? | `true` |
| `delta_sma_20` | float | 20-bar SMA of delta | `150.2` |
| `cumulative_delta_slope` | float | Slope of cumulative delta (last 5 bars) | `45.5` |

**Source:** Volumedelta indicator + calculations
**Validation:**
- ✅ `volume_sma_20 > 0`
- ✅ `volume_percentile` between 0 and 100
- ✅ If `volume > 1.5 * volume_sma_20`, then `high_volume_bar = true`

---

### 8️⃣ Price Statistics (4 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `price_sma_20` | float | 20-bar SMA of close | `1.23450` |
| `price_distance_from_sma` | float | (close - sma_20) / sma_20 * 100 | `0.024` |
| `bar_range` | float | high - low | `0.00100` |
| `bar_body` | float | abs(close - open) | `0.00030` |

**Source:** Basic calculations
**Validation:**
- ✅ `bar_range >= bar_body`
- ✅ `bar_range = high - low`
- ✅ `bar_body = abs(close - open)`

---

### 9️⃣ Session Information (8 fields)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `session_name` | string | "Asia", "London", "NY", "Other" | `"London"` |
| `session_date` | string | Date of the session (YYYY-MM-DD) | `"2025-11-20"` |
| `session_bar_index` | int | Bar index within this session (0-based) | `37` |
| `is_high_impact_news` | bool | High-impact news within 30min? | `false` |
| `bars_into_session` | int | Bars since session start (alias for session_bar_index) | `37` |
| `session_high` | float | Highest price in current session | `1.23650` |
| `session_low` | float | Lowest price in current session | `1.23300` |
| `session_volume_total` | int | Total volume accumulated in session so far | `125000` |

**Source:** Custom logic based on session times
**Validation:**
- ✅ `session_name` is one of: "Asia", "London", "NY", "Other"
- ✅ `session_date` format: YYYY-MM-DD
- ✅ `session_bar_index >= 0`
- ✅ `session_high >= high`
- ✅ `session_low <= low`
- ✅ `session_volume_total >= volume` (cumulative)

**Session Times (UTC):**
```
Asia:   00:00 - 09:00 UTC
London: 08:00 - 17:00 UTC (overlap with Asia: 08:00-09:00)
NY:     13:00 - 22:00 UTC (overlap with London: 13:00-17:00)
Other:  22:00 - 00:00 UTC
```

**Purpose for Volume Profile:**
These 3 fields (`session_name`, `session_date`, `session_bar_index`) allow Python to:
1. Group bars by session
2. Build Volume Profile per session (VAH/VAL/POC)
3. Detect VA shift between Asia → London → NY
4. Calculate price distance to session POC/VAH/VAL

---

## 📄 EXAMPLE OUTPUT (1 BAR)

```json
{
  "time_utc": "2025-11-20T10:30:00Z",
  "time_local": "2025-11-20T17:30:00+07:00",
  "open": 1.23450,
  "high": 1.23500,
  "low": 1.23400,
  "close": 1.23480,
  "volume": 1250,

  "buy_volume": 750,
  "sell_volume": 500,
  "delta": 250,
  "cumulative_delta": 1500,

  "ob_detected": true,
  "ob_type": "bullish",
  "ob_high": 1.23500,
  "ob_low": 1.23450,
  "ob_extreme": 1.23450,
  "ob_volume": 1800,
  "ob_buy_volume": 1200,
  "ob_sell_volume": 600,
  "ob_delta": 600,
  "ob_bars_ago": 5,
  "ob_displacement_target": 1.23600,
  "ob_liquidity_sweep": false,

  "fvg_detected": true,
  "fvg_type": "bullish",
  "fvg_high": 1.23550,
  "fvg_low": 1.23520,
  "fvg_gap_size": 0.00030,
  "fvg_bars_ago": 3,
  "fvg_filled_percent": 25.5,
  "fvg_still_open": true,
  "fvg_left_bar_index": 1234,
  "fvg_right_bar_index": 1236,
  "fvg_creation_volume": 2500,
  "fvg_creation_buy_vol": 2000,
  "fvg_creation_sell_vol": 500,
  "fvg_creation_delta": 1500,

  "choch_detected": true,
  "choch_type": "bullish",
  "choch_price": 1.23520,
  "choch_bars_ago": 2,
  "choch_swing_high": 1.23500,
  "choch_swing_low": 1.23400,

  "current_trend": "uptrend",
  "last_swing_high": 1.23600,
  "last_swing_low": 1.23350,
  "structure_broken": false,
  "atr_14": 0.00025,

  "eq_highs_detected": true,
  "eq_lows_detected": false,
  "eq_high_price": 1.23600,
  "eq_low_price": null,

  "volume_sma_20": 1100.5,
  "volume_percentile": 75.5,
  "high_volume_bar": true,
  "delta_sma_20": 150.2,
  "cumulative_delta_slope": 45.5,

  "price_sma_20": 1.23450,
  "price_distance_from_sma": 0.024,
  "bar_range": 0.00100,
  "bar_body": 0.00030,

  "session_name": "London",
  "session_date": "2025-11-20",
  "session_bar_index": 37,
  "is_high_impact_news": false,
  "bars_into_session": 37,
  "session_high": 1.23650,
  "session_low": 1.23300,
  "session_volume_total": 125000
}
```

---

## ✅ VALIDATION CHECKLIST

### Before Moving to Phase 2

- [ ] **Export Format**
  - [ ] File is valid JSONL (one JSON per line)
  - [ ] Each line is valid JSON
  - [ ] No missing commas or brackets

- [ ] **Data Completeness**
  - [ ] All 70 fields present (or null if not applicable)
  - [ ] No empty strings for numeric fields
  - [ ] Boolean fields are `true`/`false` (not 1/0)

- [ ] **Data Quality - Basic Bar**
  - [ ] Timestamps are in correct format
  - [ ] OHLC relationships valid (H≥C≥O≥L)
  - [ ] Volume > 0 for all bars

- [ ] **Data Quality - Volume Delta**
  - [ ] `buy_volume + sell_volume = volume`
  - [ ] `delta = buy_volume - sell_volume`
  - [ ] Cumulative delta is monotonic (always increasing/decreasing)

- [ ] **Data Quality - Order Blocks**
  - [ ] When `ob_detected=true`, all 12 OB fields present
  - [ ] OB high/low/extreme relationships correct
  - [ ] OB volume = OB buy_volume + OB sell_volume

- [ ] **Data Quality - FVG**
  - [ ] When `fvg_detected=true`, all 8 FVG fields present
  - [ ] `fvg_gap_size = fvg_high - fvg_low`
  - [ ] `fvg_filled_percent` between 0-100

- [ ] **Data Quality - CHoCH**
  - [ ] When `choch_detected=true`, all 6 CHoCH fields present
  - [ ] Bullish CHoCH: price > swing_high
  - [ ] Bearish CHoCH: price < swing_low

- [ ] **Statistical Sanity**
  - [ ] ATR is reasonable (not 0 or extremely large)
  - [ ] Volume SMA is positive
  - [ ] Price SMA is close to recent prices

- [ ] **Sample Manual Validation (10 bars)**
  - [ ] Pick 10 random bars
  - [ ] Open NinjaTrader chart
  - [ ] Verify OB zones match chart visually
  - [ ] Verify FVG zones match chart visually
  - [ ] Verify CHoCH points match chart visually
  - [ ] Verify volume numbers match chart data

---

## 🔧 IMPLEMENTATION NOTES

### C# Indicator Structure

```csharp
// SMC_RawExporter.cs
public class SMC_RawExporter : Indicator
{
    private StreamWriter writer;
    private StringBuilder jsonBuilder;

    protected override void OnBarUpdate()
    {
        if (CurrentBar < 20) return; // Need history for SMAs

        // Build JSON object
        jsonBuilder.Clear();
        jsonBuilder.Append("{");

        // 1. Basic bar info
        AppendField("time_utc", Time[0].ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"));
        AppendField("open", Open[0], 5);
        AppendField("high", High[0], 5);
        AppendField("low", Low[0], 5);
        AppendField("close", Close[0], 5);
        AppendField("volume", Volume[0]);

        // 2. Volume delta (from Volumedelta indicator)
        AppendField("buy_volume", BuyVolume[0]);
        AppendField("sell_volume", SellVolume[0]);
        AppendField("delta", BuyVolume[0] - SellVolume[0]);
        AppendField("cumulative_delta", CumulativeDelta[0]);

        // 3. Order block detection (from SMC_Structure indicator)
        bool obDetected = CheckOrderBlock(out OBData ob);
        AppendField("ob_detected", obDetected);
        if (obDetected)
        {
            AppendField("ob_type", ob.Type);
            AppendField("ob_high", ob.High, 5);
            AppendField("ob_low", ob.Low, 5);
            // ... all 12 OB fields
        }
        else
        {
            // Append nulls for all OB fields
            AppendNullFields("ob_type", "ob_high", "ob_low", ...);
        }

        // 4-9. Similar for FVG, CHoCH, Market Structure, etc.

        jsonBuilder.Append("}");

        // Write to file
        writer.WriteLine(jsonBuilder.ToString());
        writer.Flush(); // Important for real-time monitoring
    }

    private void AppendField(string name, object value, int decimals = -1)
    {
        if (jsonBuilder[jsonBuilder.Length - 1] != '{')
            jsonBuilder.Append(", ");

        jsonBuilder.Append($"\"{name}\": ");

        if (value == null)
            jsonBuilder.Append("null");
        else if (value is string)
            jsonBuilder.Append($"\"{value}\"");
        else if (value is bool)
            jsonBuilder.Append(value.ToString().ToLower());
        else if (value is double && decimals > 0)
            jsonBuilder.Append(((double)value).ToString($"F{decimals}"));
        else
            jsonBuilder.Append(value);
    }
}
```

---

## 📊 FILE SIZE ESTIMATION

**Assumptions:**
- 1 bar = ~800 bytes (JSON)
- M1 timeframe
- 24/5 trading (Mon-Fri)

**Estimates:**
```
1 day   = 1,440 bars × 800 bytes = ~1.15 MB
1 week  = 7,200 bars × 800 bytes = ~5.75 MB
1 month = 28,800 bars × 800 bytes = ~23 MB
```

**Manageable** - можно export trực tiếp vào file.

---

## 🚀 NEXT STEPS

1. **Implement C# Indicator**
   - [ ] Create `SMC_RawExporter.cs`
   - [ ] Integrate with existing SMC_Structure + Volumedelta
   - [ ] Add JSON export logic
   - [ ] Handle file I/O safely

2. **Test Export**
   - [ ] Run on 1 day of data (1,440 bars)
   - [ ] Validate JSONL format
   - [ ] Check all fields present
   - [ ] Run automated validation checks

3. **Manual Validation (10 samples)**
   - [ ] Pick 10 random bars
   - [ ] Compare with NinjaTrader chart
   - [ ] Verify OB/FVG/CHoCH visually
   - [ ] Sign off on data quality

4. **Ready for Phase 2**
   - [ ] Once validation passes → Move to Python processor
   - [ ] Python reads `raw_smc_export.jsonl`
   - [ ] Apply 10 modules
   - [ ] Generate `bar_states.jsonl` with enriched data

---

## 📝 NOTES FOR LLM ASSISTANTS

**Purpose of this file:**
- Defines data contract between C# indicator and Python processor
- Lists all 60 fields with types, descriptions, examples
- Provides validation rules for each field group
- Includes example JSON output
- Checklist for manual validation before Phase 2

**How to use:**
1. Read this spec to understand what data is exported
2. Implement C# indicator following the structure
3. Test export on small dataset (1 day)
4. Run validation checks (automated + manual 10 samples)
5. Once validated → proceed to Phase 2 (Python processing)

**Key principle:**
- Indicator exports RAW data only (lightweight)
- No complex calculations in C#
- Python does all heavy processing offline

---

## 🔴 FVG QUALITY v2.0 REQUIREMENTS SUMMARY

### Minimum Required Fields for FVG Quality Module

```
FVG STRENGTH (all required):
├─ fvg_high, fvg_low, fvg_gap_size     → For size_atr calculation
├─ fvg_creation_volume                  → For vol_ratio calculation
├─ fvg_creation_buy_vol, fvg_creation_sell_vol → For delta_ratio
├─ fvg_creation_delta                   → For delta_alignment
└─ atr_14                               → For normalization

FVG REBALANCE (all required):
├─ fvg_left_bar_index                   → For tracking FVG creation leg
├─ fvg_right_bar_index                  → For tracking FVG creation leg
└─ Python tracks FVG history internally

FVG RETEST GEOMETRY (from bar data):
├─ OHLCV per bar                        → Python detects retest
└─ fvg_high, fvg_low                    → For penetration calculation

ADAPTIVE ENTRY:
├─ fvg_high, fvg_low                    → Entry price calculation
└─ atr_14                               → Buffer calculation
```

### What Python Calculates (NOT in Ninja):

| Field | Calculation | Module |
|-------|-------------|--------|
| fvg_size_atr | fvg_gap_size / atr_14 | Fix02 |
| fvg_vol_ratio | fvg_creation_volume / volume_sma_20 | Fix02 |
| fvg_delta_ratio | \|fvg_creation_delta\| / fvg_creation_volume | Fix02 |
| fvg_strength_score | Composite of above | Fix02 |
| fvg_strength_class | "Strong"/"Medium"/"Weak" | Fix02 |
| fvg_rebalances_prev | Leg analysis | Fix02 |
| fvg_penetration_ratio | Retest geometry | Fix02 |
| fvg_retest_type | Penetration classification | Fix02 |
| entry_price_real | Adaptive buffer | Fix02 |

---

**Last Updated:** November 21, 2025
**Version:** 2.0.0
**Status:** 📝 Specification Complete - Awaiting Implementation

**Changes in v2.0:**
- Added 4 FVG volume/delta fields for FVG Strength calculation
- Added FVG Quality v2.0 requirements summary
- Updated example JSON output
- Added critical design decisions section
