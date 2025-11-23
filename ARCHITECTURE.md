# 🏗️ KIẾN TRÚC HỆ THỐNG SMC - 13 MODULES

**Version:** 2.1.0 (Nov 23, 2025)
**Major Update:** FVG Quality Module v2.0 + Wave Delta (Fix #13)

---

## ⚠️ CRITICAL DESIGN DECISIONS (Nov 2025)

### 1. FVG is the ONLY Signal Type
- **FVG retest is the ONLY signal type** for ML training
- **OB retest is NOT a separate signal** - OB provides **context features** for FVG events
- Model learns: FVG → long/short/skip

### 2. Layer 1 (Ninja) = RAW ONLY
- NinjaTrader indicator CHỈ detect raw structures
- KHÔNG scoring, KHÔNG quality assessment
- Export: FVG boundaries, OHLCV, volume, delta, swing points
- Tất cả logic phức tạp (strength, penetration, rebalance) → Python

### 3. FVG Quality v2.0 Components
Module #2 giờ có 4 components chính:
1. **FVG Strength** - Imbalance quality (size, volume, delta, rebalance)
2. **Retest Geometry** - Penetration ratio, touch type, front-run
3. **Rebalance Detection** - FVG mới lấp FVG cũ
4. **Adaptive Entry** - Dynamic buffer based on FVG strength

### 4. Critical Rules (20 Years Experience)
- **Penetration > 50% = BAD** - Don't trade deep penetration
- **Edge touch + Strong FVG = BEST** - Highest probability setup
- **Rebalance FVG = INSTITUTIONAL FOOTPRINT** - Very strong signal
- **Weak FVG = SKIP** - Likely to fill quickly

---

## 📋 NGUYÊN TẮC THIẾT KẾ

### SEPARATION OF CONCERNS
```
LIGHTWEIGHT INDICATOR (Real-time)
    ↓ (raw data)
HEAVYWEIGHT PROCESSOR (Offline/Batch)
    ↓ (processed events)
ML PIPELINE (Training)
```

### MODULE-BASED APPROACH
**Mỗi Fix = 1 Module độc lập:**
- Có MD riêng
- Test riêng
- Backtest riêng
- Có thể on/off

---

## 🎯 KIẾN TRÚC 3 LAYERS

### LAYER 1: SMC INDICATOR (NinjaTrader C#)
**Mục đích:** CHỈ detect raw SMC structures
**File:** `SMC_Structure_Lightweight.cs`

**Chỉ export:**
```csharp
// Basic SMC flags
public Series<bool> ObBullDetected;      // Có OB bull
public Series<bool> ObBearDetected;      // Có OB bear
public Series<double> ObBullHigh;        // OB bull high
public Series<double> ObBullLow;         // OB bull low
public Series<double> ObBullVolume;      // Volume bar OB
// ... tương tự cho FVG, CHoCH

// NO SCORING, NO FILTERING
// CHỈ detect raw structures
```

**Lý do:**
- ✅ Nhẹ, chạy real-time nhanh
- ✅ Dễ debug (chỉ lo detect structure)
- ✅ Không bị lag chart
- ✅ Có thể reuse cho nhiều strategies

---

### LAYER 2: DATA PROCESSOR (Python)
**Mục đích:** Tính scores, apply filters, generate states
**File:** `smc_data_processor.py`

**Input:** Raw exports từ Indicator
**Output:** `BarState` và `EventState`

**Modules (11 fixes):**
```python
class SMCDataProcessor:
    def __init__(self):
        self.fix1_ob_quality = OBQualityModule()
        self.fix2_fvg_quality = FVGQualityModule()
        self.fix3_choch_filters = CHoCHFilterModule()
        self.fix4_confluence = ConfluenceModule()
        self.fix5_stop_placement = StopPlacementModule()
        self.fix6_dynamic_tp = DynamicTPModule()
        self.fix7_market_condition = MarketConditionModule()
        self.fix8_volume_divergence = VolumeDivergenceModule()
        self.fix9_volume_profile = VolumeProfileModule()
        self.fix10_mtf_alignment = MTFAlignmentModule()
        self.fix11_liquidity_map = LiquidityMapModule()

    def process_bar(self, raw_bar) -> BarState:
        """Xử lý 1 bar raw thành BarState đầy đủ"""
        pass

    def detect_events(self, bar_states) -> List[EventState]:
        """Từ chuỗi BarState → detect EventState"""
        pass
```

**Lý do:**
- ✅ Python linh hoạt hơn C#
- ✅ Dễ test từng module
- ✅ Có thể chạy offline trên historical data
- ✅ Không ảnh hưởng real-time performance

---

### LAYER 3: ML PIPELINE
**File:** `build_enhanced_v2.py`

**Input:** EventState từ Processor
**Output:** train.jsonl, val.jsonl

---

## 📁 FOLDER STRUCTURE

```
SMC_indicator/
├── ARCHITECTURE.md                           (file này)
├── README.md                                 (overview)
│
├── indicators/                               (Layer 1)
│   ├── SMC_Structure_Lightweight.cs          (core indicator)
│   ├── Volumdelta.cs                         (volume delta)
│   └── SMC_RawExporter.cs                    (export raw data)
│
├── processor/                                (Layer 2)
│   ├── core/
│   │   ├── bar_state.py                      (BarState class)
│   │   ├── event_state.py                    (EventState class)
│   │   └── smc_processor.py                  (main processor)
│   │
│   ├── modules/                              (13 MODULES)
│   │   ├── __init__.py
│   │   ├── fix01_ob_quality.py               (Module 1)
│   │   ├── fix02_fvg_quality.py              (Module 2)
│   │   ├── fix03_choch_filters.py            (Module 3)
│   │   ├── fix04_confluence.py               (Module 4)
│   │   ├── fix05_stop_placement.py           (Module 5)
│   │   ├── fix06_dynamic_tp.py               (Module 6)
│   │   ├── fix07_market_condition.py         (Module 7)
│   │   ├── fix08_volume_divergence.py        (Module 8)
│   │   ├── fix09_volume_profile.py           (Module 9: VP + VA shift)
│   │   ├── fix10_mtf_alignment.py            (Module 10)
│   │   └── fix11_liquidity_map.py            (Module 11)
│   │
│   ├── tests/                                (Testing)
│   │   ├── test_fix01.py
│   │   ├── test_fix02.py
│   │   └── ...
│   │
│   └── backtest/                             (Per-module backtest)
│       ├── backtest_fix01.py
│       ├── backtest_fix02.py
│       └── ...
│
├── docs/                                     (Documentation)
│   ├── MODULE_FIX01_OB_QUALITY.md
│   ├── MODULE_FIX02_FVG_QUALITY.md
│   ├── MODULE_FIX03_CHOCH_FILTERS.md
│   └── ... (10 files)
│
└── examples/
    ├── sample_raw_export.jsonl               (raw từ indicator)
    ├── sample_bar_state.jsonl                (sau processor)
    └── sample_event_state.jsonl              (final output)
```

---

## 🔄 DATA FLOW CHI TIẾT

### Step 1: Indicator Export Raw Data

**NinjaTrader Indicator** chạy real-time:
```
Bar 0: { time, OHLCV, ob_detected=true, ob_high=1.234, ... }
Bar 1: { time, OHLCV, fvg_detected=true, fvg_gap=0.01, ... }
...
```

Export to: `raw_smc_export.jsonl`

### Step 2: Python Processor

```python
# Load raw data
raw_bars = load_jsonl("raw_smc_export.jsonl")

# Process each bar
processor = SMCDataProcessor()
bar_states = []

for raw_bar in raw_bars:
    # Tính toán scores cho bar này
    bar_state = processor.process_bar(raw_bar)
    bar_states.append(bar_state)

# Save BarState
save_jsonl(bar_states, "bar_states.jsonl")
```

**Output `bar_states.jsonl`:**
```json
{
  "time_utc": "2025-11-20T10:30:00Z",
  "ohlcv": {...},
  "ob_strength_score": 0.85,
  "fvg_quality_score": 0.72,
  "market_condition_score": 0.90,
  "confluence_score": 78.5,
  ...
}
```

### Step 3: Event Detection

```python
# Detect trading events
events = processor.detect_events(bar_states)

# Save EventState
save_jsonl(events, "event_states.jsonl")
```

**Output `event_states.jsonl`:**
```json
{
  "signal_type": "fvg_retest_bull",
  "direction": 1,
  "entry_price": 1.2345,
  "sl_price": 1.2300,
  "tp1_price": 1.2400,
  "tp2_price": 1.2450,
  "confluence_score": 85.2,
  "fvg_quality_score": 0.78,
  "fvg_value_class": "A",
  "has_ob_in_leg": true,
  "ob_overlap_ratio": 0.7,
  "ob_is_m5_hl": true,
  "ob_leg_bos_type": "BOS",
  "ob_strength_score": 0.88,
  "market_condition_score": 0.92,
  ...
}
```

### Step 4: ML Training

```python
# Convert EventState to ML format
from build_enhanced_v2 import convert_to_ml_format

train_data = convert_to_ml_format(events, labeling_strategy="option_a")
save_jsonl(train_data, "train.jsonl")
```

---

## 🎯 SCHEMA DEFINITIONS

### BarState Schema

```python
@dataclass
class BarState:
    # === CORE DATA ===
    time_utc: datetime
    o: float
    h: float
    l: float
    c: float
    volume: float

    # === VOLUME DELTA ===
    delta: float
    buy_vol: float
    sell_vol: float
    cum_delta: float

    # === STRUCTURE ===
    ext_dir: int              # 1, -1, 0
    int_dir: int              # 1, -1, 0
    is_swing_high: bool
    is_swing_low: bool

    # === SESSION ===
    session: str              # "Asia", "London", "NY", "Other"
    session_date: str         # "2025-11-20"
    session_bar_index: int    # Bar index in session (for VP)
    atr: float

    # === SMC FLAGS ===
    has_ob_bull: bool
    has_ob_bear: bool
    has_fvg_bull: bool
    has_fvg_bear: bool
    has_choch: bool
    choch_dir: int

    # === FIX #1: OB QUALITY ===
    ob_strength_score: float      # 0-1
    ob_volume_factor: float       # volume / median
    ob_delta_imbalance: float     # 0-1
    ob_displacement_rr: float     # move / risk
    ob_liquidity_sweep: bool

    # === FIX #2: FVG QUALITY (EXPANDED v2.0) ===
    # --- Basic Classification ---
    fvg_in_va_flag: int           # 1 if inside VA, 0 if outside
    fvg_breakout_va_flag: int     # 1 if breakout VA pattern
    fvg_after_sweep_flag: int     # 1 if after sweep pattern
    fvg_value_class: str          # "A" / "B" / "C" / "None"

    # --- FVG Strength (NEW in v2.0) ---
    fvg_size_atr: float           # gap_size / ATR (1.5+ = strong)
    fvg_vol_ratio: float          # volume / median_20 (2.0+ = strong)
    fvg_delta_ratio: float        # |delta| / volume (0.6+ = strong)
    fvg_delta_alignment: int      # 1 = aligned, -1 = opposite, 0 = neutral
    fvg_strength_score: float     # 0-1 composite strength
    fvg_strength_class: str       # "Strong" / "Medium" / "Weak"
    fvg_creation_bar_index: int   # Bar where FVG was created
    fvg_age_bars: int             # Bars since FVG creation

    # --- Rebalance Detection (NEW in v2.0) ---
    fvg_rebalances_prev: bool     # Does this FVG fill a previous FVG?
    fvg_rebalance_ratio: float    # % of previous FVG filled (0-1)
    fvg_is_clean_rebalance: bool  # Filled completely (>80%)?
    prev_fvg_direction: str       # Direction of filled FVG
    prev_fvg_age_bars: int        # How old was the filled FVG?

    # --- Component Scores ---
    fvg_gap_quality_score: float  # Gap size component (0-1)
    fvg_volume_quality_score: float # Volume component (0-1)
    fvg_imbalance_quality_score: float # Delta imbalance component (0-1)

    # --- Composite & Context ---
    fvg_quality_score: float      # 0-1 (final composite)
    fvg_context: str              # "breakout_va_strong_rebalance" / etc.

    # === FIX #3: CHOCH QUALITY ===
    choch_strength_score: float   # 0-1
    choch_atr_factor: float
    choch_volume_factor: float

    # === FIX #7: MARKET CONDITION ===
    trend_dir: int                # 1, -1, 0
    trend_strength: float         # 0-1
    volatility_regime: str        # "Low", "Normal", "High"
    volatility_score: float       # 0-1
    session_score: float          # 0-1
    market_condition_score: float # 0-1

    # === FIX #8: VOLUME DIVERGENCE ===
    has_vol_div: bool
    vol_div_type: str             # "None", "Bull", "Bear"
    vol_div_score: float          # 0-1 (divergence strength)
    vol_div_swing_distance: int   # Bars between divergent swings
    approx_absorption_bull: int   # 1 if bullish absorption pattern
    approx_absorption_bear: int   # 1 if bearish absorption pattern

    # === FIX #9: VOLUME PROFILE ===
    vp_session_poc_price: float   # Session POC
    vp_session_vah: float         # Value Area High
    vp_session_val: float         # Value Area Low
    vp_pos_in_range: float        # 0-1 (position in session range)
    vp_in_value_area: int         # 1 if inside VA, 0 if outside
    vp_dist_to_poc_rr: float      # Distance to POC in ATR
    vp_dist_to_vah_rr: float      # Distance to VAH in ATR
    vp_dist_to_val_rr: float      # Distance to VAL in ATR
    vp_prev_session_poc: float    # Previous session POC
    vp_prev_session_vah: float    # Previous session VAH
    vp_prev_session_val: float    # Previous session VAL
    vp_poc_shift_from_prev_rr: float      # POC shift in ATR
    vp_va_mid_shift_from_prev_rr: float   # VA midpoint shift in ATR
    vp_va_overlap_percent: float  # % overlap between current and prev VA

    # === FIX #10: MTF ===
    htf_trend_dir: int            # from M15/H1
    htf_trend_strength: float
    htf_premium_discount: str     # "Premium", "Discount", "Mid"
    htf_ob_confluence: bool

    # === FIX #11: LIQUIDITY MAP ===
    liquidity_sweep_detected: bool        # Was liquidity swept this bar?
    sweep_type: str                       # "liquidity_above" / "liquidity_below"
    sweep_level_price: float              # Price of liquidity swept
    sweep_level_type: str                 # "swing_high" / "eq_highs" / "ob_edge" / etc.
    sweep_wick_penetration: float         # How far wick penetrated
    sweep_body_rejection: bool            # Did body close back inside?
    bars_since_sweep: int                 # Bars since last sweep
    sweep_count_recent: int               # Number of sweeps in last 20 bars
    nearest_liq_above_price: float        # Nearest liquidity above
    nearest_liq_above_type: str           # Type of liquidity above
    nearest_liq_below_price: float        # Nearest liquidity below
    nearest_liq_below_type: str           # Type of liquidity below
```

### EventState Schema

**⚠️ IMPORTANT DESIGN DECISION (Nov 2025):**
- **ONLY FVG retest events** are used as signals
- **OB retest is NOT a separate signal type** - OB is used as **context feature** for FVG events
- Rationale: Entry thực tế phần lớn là FVG retest, OB chỉ là "nguồn" của leg tạo FVG

```python
@dataclass
class EventState:
    # === META ===
    symbol: str
    timeframe: str               # "M1"
    bar_index: int
    time_utc: datetime

    # === SIGNAL (FVG RETEST ONLY) ===
    signal_type: str             # "fvg_retest_bull", "fvg_retest_bear" ONLY
    direction: int               # 1 (long), -1 (short)

    # === FVG QUALITY (from Fix #2 - EXPANDED v2.0) ===
    fvg_quality_score: float     # 0-1 composite
    fvg_value_class: str         # "A", "B", "C"
    fvg_strength_score: float    # 0-1 strength
    fvg_strength_class: str      # "Strong" / "Medium" / "Weak"
    fvg_rebalances_prev: bool    # Does FVG fill previous FVG?
    fvg_is_clean_rebalance: bool # Filled completely?
    fvg_in_va_flag: int          # 1 if inside VA
    fvg_breakout_va_flag: int    # 1 if breakout VA pattern
    fvg_after_sweep_flag: int    # 1 if after sweep pattern

    # === RETEST GEOMETRY (NEW in v2.0) ===
    fvg_retest_type: str         # "no_touch"/"edge"/"shallow"/"deep"/"break"
    fvg_penetration_ratio: float # 0 = edge, 0.5 = mid, 1.0+ = through
    fvg_min_distance_to_edge: float  # Closest approach (ATR units)
    fvg_front_run_distance: float    # Distance from edge if no_touch
    fvg_retest_bar_index: int    # Bar where retest occurred
    fvg_retest_quality_score: float  # 0-1 retest quality

    # === ADAPTIVE ENTRY (NEW in v2.0) ===
    entry_type: str              # "edge" / "50pct" / "buffer_adaptive"
    entry_price_ideal: float     # Entry at FVG edge (best RR)
    entry_price_real: float      # Actual entry with buffer
    entry_buffer_size: float     # Buffer applied
    allow_front_run: bool        # Front-run allowed for this FVG?
    max_penetration_allowed: float  # Max penetration for valid entry

    # === RR CALCULATION (NEW in v2.0) ===
    rr_ideal: float              # RR if entry at edge
    rr_real: float               # RR with actual entry
    rr_50pct: float              # RR if entry at 50% FVG
    rr_degradation: float        # rr_ideal - rr_real

    # === OB CONTEXT (NOT SIGNAL - from Fix #1) ===
    # OB provides CONTEXT for FVG quality, not separate event type
    has_ob_in_leg: bool          # Leg tạo FVG có OB source không?
    ob_overlap_ratio: float      # Phần FVG trùng với OB (0-1)
    ob_is_m5_hl: bool            # OB tại chân HL m5?
    ob_leg_bos_type: str         # "BOS" / "CHOCH" / "None"
    ob_distance_from_source: float  # Normalized theo ATR
    ob_strength_score: float     # 0-1 (if OB exists)

    # === OTHER SCORES ===
    choch_strength_score: float  # 0-1
    volume_bias_score: float     # 0-1
    market_condition_score: float # 0-1
    vol_div_score: float         # 0-1

    # === FIX #4: CONFLUENCE ===
    confluence_score: float      # 0-100

    # === FIX #5 & #6: ENTRY/STOP/TP ===
    entry_price: float           # Final entry price used (= entry_price_real)
    sl_price: float              # Stop loss price
    sl_buffer_applied: float     # Extra buffer beyond FVG for SL
    tp1_price: float             # TP1 (nearest structure)
    tp2_price: float             # TP2 (2.5+ RR)
    tp3_price: float             # TP3 (extended target)
    rr_tp1: float                # RR to TP1
    rr_tp2: float                # RR to TP2
    rr_tp3: float                # RR to TP3

    # === FIX #9: VOLUME PROFILE ===
    vp_in_value_area: int        # 1 if inside VA, 0 if outside
    vp_dist_to_poc_rr: float     # Distance to POC in ATR
    vp_dist_to_vah_rr: float     # Distance to VAH in ATR
    vp_dist_to_val_rr: float     # Distance to VAL in ATR
    vp_poc_shift_from_prev_rr: float   # POC shift between sessions
    vp_va_mid_shift_from_prev_rr: float # VA shift between sessions

    # === FIX #11: LIQUIDITY ===
    liquidity_distance: float    # ticks to same-direction liquidity
    next_swing_target: float

    # === LABEL (for ML) ===
    signal: str                  # "long", "short", "skip"

    # === OUTCOME (for backtesting) ===
    hit: str                     # "tp1", "tp2", "sl", "none"
    outcome_rr: float
    mfe: float
    mae: float
    mfe_rr: float
    mae_rr: float
    bars_to_hit: int
```

### OB Context Fields Explained

```python
# OB Context được thêm vào FVG event (KHÔNG phải separate event)
# Giúp model học: "FVG nào có OB backing thì expectancy cao hơn"

has_ob_in_leg: bool          # True nếu leg tạo FVG đi qua OB
ob_overlap_ratio: float      # 0.0-1.0: Bao nhiêu % FVG nằm trong OB zone
ob_is_m5_hl: bool            # True nếu OB tại chân HL trên M5 (high quality)
ob_leg_bos_type: str         # "BOS" (ext), "CHOCH" (int), hoặc "None"
ob_distance_from_source: float  # FVG cách OB source bao xa (normalized)
ob_strength_score: float     # Score từ Module #1 (nếu có OB)

# FVG "đẹp kiểu thực chiến" là:
#   has_ob_in_leg = True
#   ob_is_m5_hl = True
#   ob_overlap_ratio >= 0.5
#   ob_leg_bos_type = "BOS"
```

---

## 🔧 IMPLEMENTATION STRATEGY

### Phase 1: Setup (Day 1)
- [ ] Create folder structure
- [ ] Setup base classes (BarState, EventState)
- [ ] Create skeleton for 13 MODULES
- [ ] Setup testing framework

### Phase 2: Module Implementation (Days 2-13)
**Mỗi module = 1 ngày:**
- [ ] Fix #1: OB Quality (Day 2)
- [ ] Fix #2: FVG Quality (Day 3)
- [ ] Fix #3: CHoCH Filters (Day 4)
- [ ] Fix #4: Confluence (Day 5)
- [ ] Fix #5: Stop Placement (Day 6)
- [ ] Fix #6: Dynamic TP (Day 7)
- [ ] Fix #7: Market Condition (Day 8)
- [ ] Fix #8: Volume Divergence (Day 9)
- [ ] Fix #9: Volume Profile (Day 10)
- [ ] Fix #10: MTF Alignment (Day 11)
- [ ] Fix #11: Liquidity Map (Day 12)
- [ ] Integration Testing (Day 13)

### Per-Module Workflow:
```
1. Đọc spec (từ file MD)
2. Implement module
3. Unit test
4. Mini backtest (on 1000 bars)
5. Validate metrics
6. Document results
7. Commit & move to next
```

---

## 📊 BACKTEST FRAMEWORK

### Per-Module Backtest

```python
# backtest/backtest_fix01.py
class Fix01Backtest:
    def __init__(self):
        self.raw_data = load_raw_exports()
        self.processor = SMCDataProcessor()
        # Enable ONLY Fix #1
        self.processor.enable_modules([1])

    def run(self):
        results = []
        for bar in self.raw_data:
            bar_state = self.processor.process_bar(bar)
            # Calculate OB score
            # Track if OB quality predicts wins
            results.append({
                'ob_score': bar_state.ob_strength_score,
                'win': bar.hit == 'tp',
                ...
            })

        # Analyze correlation
        self.analyze_score_vs_winrate(results)
        self.generate_report()
```

**Output:** `reports/fix01_backtest_report.md`

```markdown
# Fix #1: OB Quality Backtest

## Metrics
- Total OBs detected: 450
- OBs with score ≥ 0.7: 180 (40%)
- Win rate (all OBs): 24.2%
- Win rate (score ≥ 0.7): 38.5% ✅

## Conclusion
✅ OB score correlates with win rate
✅ Filter at 0.7 improves win rate by 14.3%
```

---

## 🎯 SUCCESS CRITERIA

### Per-Module Criteria

**Fix #1 (OB Quality):**
- [ ] `ob_strength_score` ranges 0-1
- [ ] Scores ≥ 0.7 have win rate ≥ 30%
- [ ] Scores < 0.5 have win rate < 20%
- [ ] Correlation coefficient > 0.5

**Fix #2 (FVG Quality):**
- [ ] `fvg_quality_score` ranges 0-1
- [ ] Scores ≥ 0.7 have win rate ≥ 32%
- [ ] Quick-fill FVGs score lower
- [ ] Correlation > 0.5

*... tương tự cho 13 MODULES*

### Integration Criteria

After all 13 MODULES:
- [ ] Overall win rate ≥ 35%
- [ ] Confluence score (0-100) correlates with success
- [ ] Scores 80-100: Win rate ≥ 45%
- [ ] Scores 70-80: Win rate 35-45%
- [ ] Scores < 70: Rejected

---

## 🚀 GETTING STARTED

### Bước 1: Tạo folder structure
```bash
cd SMC_indicator
mkdir -p processor/core processor/modules processor/tests processor/backtest docs examples
```

### Bước 2: Implement base classes
```python
# processor/core/bar_state.py
# processor/core/event_state.py
```

### Bước 3: Bắt đầu Fix #1
```bash
# Đọc docs/MODULE_FIX01_OB_QUALITY.md
# Implement processor/modules/fix01_ob_quality.py
# Test processor/tests/test_fix01.py
# Backtest processor/backtest/backtest_fix01.py
```

---

## ❓ FAQ

**Q: Tại sao không làm tất cả trong C#?**
A: C# trong NinjaTrader bị giới hạn, chạy real-time phải nhẹ. Python linh hoạt hơn cho complex logic.

**Q: Processor chạy real-time hay offline?**
A: CÓ THỂ cả hai. Export raw → process offline cho ML. Hoặc process real-time nếu cần live trading.

**Q: 13 MODULES có thể on/off riêng được không?**
A: Có! Mỗi module độc lập, có thể enable/disable để A/B test.

**Q: Backtest từng module để làm gì?**
A: Validate module đó có improve win rate không. Nếu không → fix hoặc skip.

---

## 📊 MODULE SPECS STATUS

| Module | Status | Spec File | Notes |
|--------|--------|-----------|-------|
| Fix #01: OB Quality | ✅ Spec Complete | [MODULE_FIX01_OB_QUALITY.md](docs/MODULE_FIX01_OB_QUALITY.md) | Context for FVG |
| Fix #02: FVG Quality | ✅ Spec Complete v2.0 | [MODULE_FIX02_FVG_QUALITY.md](docs/MODULE_FIX02_FVG_QUALITY.md) | PRIMARY signal |
| Fix #03: Structure Context | ✅ Spec Complete v1.0 | [MODULE_FIX03_STRUCTURE_CONTEXT.md](docs/MODULE_FIX03_STRUCTURE_CONTEXT.md) | Redesigned from CHoCH |
| Fix #04: Confluence | ✅ Spec Complete v1.0 | [MODULE_FIX04_CONFLUENCE.md](docs/MODULE_FIX04_CONFLUENCE.md) | 6-factor weighted |
| Fix #05: Stop Placement | ✅ Spec Complete v1.0 | [MODULE_FIX05_STOP_PLACEMENT.md](docs/MODULE_FIX05_STOP_PLACEMENT.md) | 4 stop methods |
| Fix #06: Target Placement | ✅ Spec Complete v1.0 | [MODULE_FIX06_TARGET_PLACEMENT.md](docs/MODULE_FIX06_TARGET_PLACEMENT.md) | Simplified: TP1 struct + TP2 3x RR |
| Fix #07: Market Condition | ✅ Spec Complete v1.0 | [MODULE_FIX07_MARKET_CONDITION.md](docs/MODULE_FIX07_MARKET_CONDITION.md) | ADX + ATR regime |
| Fix #08: Volume Divergence | ✅ Spec Complete v1.1 | [MODULE_FIX08_VOLUME_DIVERGENCE.md](docs/MODULE_FIX08_VOLUME_DIVERGENCE.md) | Simplified: swing only |
| Fix #09: Volume Profile | ✅ Spec Complete | [MODULE_FIX09_VOLUME_PROFILE.md](docs/MODULE_FIX09_VOLUME_PROFILE.md) | VP + VA shift |
| Fix #10: MTF Alignment | ✅ Spec Complete v1.0 | [MODULE_FIX10_MTF_ALIGNMENT.md](docs/MODULE_FIX10_MTF_ALIGNMENT.md) | Structure + MA trend |
| Fix #11: Liquidity Map | ✅ Spec Complete | [MODULE_FIX11_LIQUIDITY_MAP.md](docs/MODULE_FIX11_LIQUIDITY_MAP.md) | Sweep detection |
| Fix #12: FVG Retest Filter | In Code v1.0 | (module only) | Gate edge/shallow/deep/no_touch/break |
| Fix #13: Wave Delta | In Code v1.0 | (module only) | Live leg delta/volume per zigzag swing |

### Additional Documentation

| Document | Purpose |
|----------|---------|
| [NINJA_EXPORT_CHECKLIST.md](docs/NINJA_EXPORT_CHECKLIST.md) | Complete list of 55 fields required from NinjaTrader |
| [PHASE1_INDICATOR_EXPORT_SPEC.md](PHASE1_INDICATOR_EXPORT_SPEC.md) | Phase 1 export specification |
| [WORKFLOW_VISUALIZATION.md](WORKFLOW_VISUALIZATION.md) | Visual flow diagrams |

---

**Status:** ✅ All Module Specs Complete - Ready for Implementation

**Last Updated:** November 21, 2025

**Next Steps:**
1. ✅ All 11 module specs completed
2. ✅ NinjaTrader export checklist created (55 fields)
3. **NEXT:** Implement NinjaTrader indicator (Layer 1)
4. **THEN:** Implement Python processor modules (Layer 2)
5. **FINALLY:** ML Pipeline integration


