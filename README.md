# 🎯 SMC INDICATOR - MODULE-BASED ARCHITECTURE

**Version:** 2.1.0
**Status:** 🟡 In Development
**Approach:** 11 Independent Modules

---

## ⚠️ IMPORTANT DESIGN DECISION (Nov 2025)

### Signal Type: FVG ONLY

**Previous approach (deprecated):**
- Both FVG and OB retest were separate signal types
- Model learned: `fvg_retest_bull`, `fvg_retest_bear`, `ob_ext_retest_bull`, `ob_ext_retest_bear`

**New approach (current):**
- **Only FVG retest is a signal type**
- **OB is CONTEXT, not signal** - provides quality features for FVG events
- Model learns: `fvg_retest_bull`, `fvg_retest_bear` with OB context fields

**Rationale:**
1. Entry thực tế phần lớn là FVG retest (OB chỉ là "nguồn" của leg)
2. OB retest ~6% data nhưng pattern gần giống FVG → data fragmentation
3. Cùng chart pattern nhưng label khác → model confusion
4. Simpler ML target: FVG → long/short/skip

**FVG Event now includes OB context:**
```python
{
    "signal_type": "fvg_retest_bull",    # NOT ob_retest_bull
    "has_ob_in_leg": true,                # OB context
    "ob_overlap_ratio": 0.7,              # How much FVG overlaps with OB
    "ob_is_m5_hl": true,                  # OB at M5 swing HL
    "ob_strength_score": 0.85             # OB quality score
}
```

---

## 📖 OVERVIEW

Hệ thống SMC trading được refactor hoàn toàn theo kiến trúc module-based, với mục tiêu:

**🎯 Primary Goal:** Đạt win rate 35%+ thông qua quality scoring và filtering

**🏗️ Architecture:** 3-layer separation of concerns
```
Layer 1: Lightweight Indicator (C# - Real-time)
    ↓
Layer 2: Data Processor (Python - Batch/Offline)
    ↓
Layer 3: ML Training Pipeline (Python)
```

---

## 📁 FOLDER STRUCTURE

```
SMC_indicator/
├── README.md                    (this file)
├── ARCHITECTURE.md              (detailed architecture)
├── PROJECT_MASTER_PLAN.md       (original plan)
│
├── indicators/                  (Layer 1: NinjaTrader C#)
│   ├── SMC_Structure_Lightweight.cs
│   ├── Volumdelta.cs
│   └── SMC_RawExporter.cs
│
├── processor/                   (Layer 2: Python)
│   ├── core/
│   │   ├── bar_state.py         (BarState dataclass)
│   │   ├── event_state.py       (EventState dataclass)
│   │   └── smc_processor.py     (Main processor)
│   │
│   ├── modules/                 (10 independent modules)
│   │   ├── fix01_ob_quality.py
│   │   ├── fix02_fvg_quality.py
│   │   ├── fix03_choch_filters.py
│   │   ├── fix04_confluence.py
│   │   ├── fix05_stop_placement.py
│   │   ├── fix06_dynamic_tp.py
│   │   ├── fix07_market_condition.py
│   │   ├── fix08_volume_divergence.py
│   │   ├── fix09_mtf_alignment.py
│   │   └── fix10_liquidity_map.py
│   │
│   ├── tests/
│   └── backtest/
│
├── docs/                        (Per-module documentation)
│   ├── MODULE_FIX01_OB_QUALITY.md       ✅
│   ├── MODULE_FIX02_FVG_QUALITY.md      ⏳
│   ├── MODULE_FIX03_CHOCH_FILTERS.md    ⏳
│   └── ... (10 files total)
│
└── examples/
    ├── sample_raw_export.jsonl
    ├── sample_bar_state.jsonl
    └── sample_event_state.jsonl
```

---

## 🎯 THE 11 MODULES

| # | Module | Purpose | Status | Doc |
|---|--------|---------|--------|-----|
| 1 | OB Quality | Score OBs 0-1 (**as FVG context, not signal**) | ✅ Spec Done | [Link](docs/MODULE_FIX01_OB_QUALITY.md) |
| 2 | FVG Quality | FVG Strength + Retest Geometry + Adaptive Entry (v2.0) | ✅ Spec Done v2.0 | [Link](docs/MODULE_FIX02_FVG_QUALITY.md) |
| 3 | Structure Context | Context tagging for FVG (expansion/retracement/continuation) | ✅ Spec Done v1.0 | [Link](docs/MODULE_FIX03_STRUCTURE_CONTEXT.md) |
| 4 | Confluence | 6-factor weighted scoring (0-1) | ✅ Spec Done v1.0 | [Link](docs/MODULE_FIX04_CONFLUENCE.md) |
| 5 | Stop Placement | 4 stop methods (FVG edge/full, OB, structure) | ✅ Spec Done v1.0 | [Link](docs/MODULE_FIX05_STOP_PLACEMENT.md) |
| 6 | Target Placement | Simplified: TP1=struct, TP2=3x RR | ✅ Spec Done v1.0 | [Link](docs/MODULE_FIX06_TARGET_PLACEMENT.md) |
| 7 | Market Condition | ADX trend + ATR volatility regime | ✅ Spec Done v1.0 | [Link](docs/MODULE_FIX07_MARKET_CONDITION.md) |
| 8 | Volume Divergence | Simplified: swing-delta divergence only | ✅ Spec Done v1.1 | [Link](docs/MODULE_FIX08_VOLUME_DIVERGENCE.md) |
| 9 | Volume Profile | Session VP (VAH/VAL/POC) + VA shift | ✅ Spec Done | [Link](docs/MODULE_FIX09_VOLUME_PROFILE.md) |
| 10 | MTF Alignment | Structure + MA based HTF trend alignment | ✅ Spec Done v1.0 | [Link](docs/MODULE_FIX10_MTF_ALIGNMENT.md) |
| 11 | Liquidity Map | Comprehensive sweep detection (EQH/EQL/OB/VP) | ✅ Spec Done | [Link](docs/MODULE_FIX11_LIQUIDITY_MAP.md) |

**Note:** Module #1 (OB Quality) output is used as **context features** in FVG events, not as separate OB events.

### Additional Documentation
| Document | Purpose |
|----------|---------|
| [NINJA_EXPORT_CHECKLIST.md](docs/NINJA_EXPORT_CHECKLIST.md) | Complete list of 55 fields required from NinjaTrader |
| [PHASE1_INDICATOR_EXPORT_SPEC.md](PHASE1_INDICATOR_EXPORT_SPEC.md) | Phase 1 export specification |
| [WORKFLOW_VISUALIZATION.md](WORKFLOW_VISUALIZATION.md) | Visual flow diagrams |

---

## 🚀 QUICK START

### For Developers (Module Implementation)

**Step 1: Read Architecture**
```bash
# Understand the 3-layer design
cat ARCHITECTURE.md
```

**Step 2: Pick a Module**
```bash
# Start with Fix #1 (recommended)
cat docs/MODULE_FIX01_OB_QUALITY.md
```

**Step 3: Implement**
```bash
# Create the module
cd processor/modules
touch fix01_ob_quality.py

# Implement according to spec
# See MODULE_FIX01 for detailed spec
```

**Step 4: Test**
```bash
# Write unit tests
cd processor/tests
touch test_fix01.py

# Run tests
pytest test_fix01.py -v
```

**Step 5: Backtest**
```bash
# Validate on historical data
cd processor/backtest
python backtest_fix01.py
```

**Step 6: Sign Off**
- [ ] All tests pass
- [ ] Backtest shows correlation > 0.5
- [ ] Win rate improvement visible
- [ ] Ready for next module

### For Users (Running the System)

**Step 1: Export Raw Data**
```bash
# Run NinjaTrader with SMC_RawExporter
# Exports to: raw_smc_export.jsonl
```

**Step 2: Process Data**
```python
from processor.core.smc_processor import SMCDataProcessor

# Initialize processor
processor = SMCDataProcessor()

# Enable desired modules
processor.enable_modules([1, 2, 4, 7])  # Enable Fix #1, #2, #4, #7

# Process raw data
processor.process_file("raw_smc_export.jsonl", "bar_states.jsonl")
```

**Step 3: Generate Events**
```python
# Detect trading events
processor.generate_events("bar_states.jsonl", "event_states.jsonl")
```

**Step 4: Train ML Model**
```python
# Use event_states.jsonl for training
# See ../build_enhanced_v2.py
```

---

## 📊 DATA SCHEMAS

### BarState (per bar)
```python
{
    "time_utc": "2025-11-20T10:30:00Z",
    "ohlcv": {...},

    # Fix #1 outputs
    "ob_strength_score": 0.85,
    "ob_volume_factor": 2.3,
    "ob_delta_imbalance": 0.71,

    # Fix #2 outputs
    "fvg_quality_score": 0.78,
    "fvg_gap_atr_ratio": 0.95,

    # ... all 10 modules contribute fields
}
```

### EventState (per setup)
```python
{
    # Signal type: FVG ONLY (no OB events)
    "signal_type": "fvg_retest_bull",
    "direction": 1,

    # FVG Quality (from Module #2)
    "fvg_quality_score": 0.78,
    "fvg_value_class": "A",

    # OB Context (from Module #1 - NOT separate event)
    "has_ob_in_leg": true,
    "ob_overlap_ratio": 0.7,
    "ob_is_m5_hl": true,
    "ob_leg_bos_type": "BOS",
    "ob_strength_score": 0.88,

    # Confluence
    "confluence_score": 85.2,

    # Entry/SL/TP
    "entry_price": 1.2345,
    "sl_price": 1.2300,
    "tp1_price": 1.2400,
    "tp2_price": 1.2450,

    "signal": "long"  # For ML training
}
```

---

## 🎯 SUCCESS METRICS

### Per-Module Targets

**Fix #1 (OB Quality):**
- Scores ≥ 0.7 → Win rate ≥ 30%
- Correlation > 0.5

**Fix #2 (FVG Quality):**
- Scores ≥ 0.7 → Win rate ≥ 32%
- Correlation > 0.5

**... (same pattern for all modules)**

### Overall System Target

After all 10 modules:
- Overall win rate: ≥ 35%
- Confluence 80-100: Win rate ≥ 45%
- Confluence 70-80: Win rate 35-45%
- Confluence < 70: Rejected (skip)

---

## 📝 DEVELOPMENT WORKFLOW

### Module Development (1 module/day)

```
Day 1: Fix #1
├── Morning: Read spec, implement module
├── Afternoon: Write tests, debug
└── Evening: Backtest, validate, sign off

Day 2: Fix #2
├── Same workflow
└── ...

Day 11: Integration
├── Test all modules together
├── Full system backtest
└── Final validation
```

### Per-Module Checklist

- [ ] Read MODULE_FIXnn.md thoroughly
- [ ] Implement module class
- [ ] Write unit tests (100% coverage)
- [ ] Run tests (all pass)
- [ ] Mini backtest (1000 bars)
- [ ] Validate correlation > 0.5
- [ ] Document results
- [ ] Commit to git
- [ ] Move to next module

---

## 🔧 CONFIGURATION

### Enable/Disable Modules

```python
from processor.core.smc_processor import SMCDataProcessor

processor = SMCDataProcessor()

# Enable specific modules
processor.enable_modules([1, 2, 4, 7])

# Or disable specific modules
processor.disable_modules([3, 5])

# Check status
print(processor.get_enabled_modules())
# Output: [1, 2, 4, 7, 6, 8, 9, 10]
```

### Module Parameters

```python
# Each module can be configured
processor.set_module_params('fix01_ob_quality', {
    'displacement_weight': 0.4,
    'volume_weight': 0.3,
    'delta_weight': 0.2,
    'sweep_weight': 0.1,
    'min_displacement_rr': 1.5
})
```

---

## 📚 DOCUMENTATION

### Core Docs
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [PROJECT_MASTER_PLAN.md](PROJECT_MASTER_PLAN.md) - Original master plan

### Module Docs (in `docs/`) - ALL COMPLETE ✅
- [MODULE_FIX01_OB_QUALITY.md](docs/MODULE_FIX01_OB_QUALITY.md) ✅
- [MODULE_FIX02_FVG_QUALITY.md](docs/MODULE_FIX02_FVG_QUALITY.md) ✅ v2.0
- [MODULE_FIX03_STRUCTURE_CONTEXT.md](docs/MODULE_FIX03_STRUCTURE_CONTEXT.md) ✅ v1.0
- [MODULE_FIX04_CONFLUENCE.md](docs/MODULE_FIX04_CONFLUENCE.md) ✅ v1.0
- [MODULE_FIX05_STOP_PLACEMENT.md](docs/MODULE_FIX05_STOP_PLACEMENT.md) ✅ v1.0
- [MODULE_FIX06_TARGET_PLACEMENT.md](docs/MODULE_FIX06_TARGET_PLACEMENT.md) ✅ v1.0
- [MODULE_FIX07_MARKET_CONDITION.md](docs/MODULE_FIX07_MARKET_CONDITION.md) ✅ v1.0
- [MODULE_FIX08_VOLUME_DIVERGENCE.md](docs/MODULE_FIX08_VOLUME_DIVERGENCE.md) ✅ v1.1
- [MODULE_FIX09_VOLUME_PROFILE.md](docs/MODULE_FIX09_VOLUME_PROFILE.md) ✅
- [MODULE_FIX10_MTF_ALIGNMENT.md](docs/MODULE_FIX10_MTF_ALIGNMENT.md) ✅ v1.0
- [MODULE_FIX11_LIQUIDITY_MAP.md](docs/MODULE_FIX11_LIQUIDITY_MAP.md) ✅
- [NINJA_EXPORT_CHECKLIST.md](docs/NINJA_EXPORT_CHECKLIST.md) ✅ (55 fields)

### API Docs
```bash
# Generate API docs
cd processor
pdoc --html core modules -o ../docs/api
```

---

## 🧪 TESTING

### Run All Tests
```bash
cd processor
pytest tests/ -v --cov=modules --cov-report=html
```

### Run Single Module Tests
```bash
pytest tests/test_fix01.py -v
```

### Backtest Single Module
```bash
python backtest/backtest_fix01.py
```

### Backtest Full System
```bash
python backtest/backtest_full_system.py
```

---

## 📈 PROGRESS TRACKING

### Current Status (November 21, 2025)

| Phase | Status | Progress |
|-------|--------|----------|
| Architecture Design | ✅ Complete | 100% |
| Folder Structure | ✅ Complete | 100% |
| **Signal Type Decision** | ✅ FVG only, OB as context | 100% |
| Fix #1 Spec (OB as context) | ✅ Complete | 100% |
| Fix #2 Spec (FVG Quality v2.0) | ✅ Complete | 100% |
| Fix #3 Spec (Structure Context) | ✅ Complete | 100% |
| Fix #4 Spec (Confluence) | ✅ Complete | 100% |
| Fix #5 Spec (Stop Placement) | ✅ Complete | 100% |
| Fix #6 Spec (Target Placement) | ✅ Complete | 100% |
| Fix #7 Spec (Market Condition) | ✅ Complete | 100% |
| Fix #8 Spec (Volume Divergence v1.1) | ✅ Complete | 100% |
| Fix #9 Spec (Volume Profile) | ✅ Complete | 100% |
| Fix #10 Spec (MTF Alignment) | ✅ Complete | 100% |
| Fix #11 Spec (Liquidity Map) | ✅ Complete | 100% |
| NinjaTrader Export Checklist | ✅ Complete | 100% |
| NinjaTrader Implementation | ⏳ Pending | 0% |
| Python Modules Implementation | ⏳ Pending | 0% |

**Overall Progress:** 100% Specs Complete - Ready for Implementation 🚀

---

## 🤝 CONTRIBUTING

### Workflow
1. Pick a module from the list
2. Read the spec doc
3. Implement the module
4. Write tests
5. Backtest
6. Create PR
7. Review & merge

### Code Style
- Follow PEP 8
- Type hints required
- Docstrings for all public methods
- 100% test coverage

---

## 📞 SUPPORT

**Questions about architecture?**
→ Read [ARCHITECTURE.md](ARCHITECTURE.md)

**Questions about a specific module?**
→ Read `docs/MODULE_FIXnn.md`

**Found a bug?**
→ Create issue with module name in title

**Need help?**
→ Contact module owner or project lead

---

## 📄 LICENSE

Proprietary - SMC Trading System
© 2025 All Rights Reserved

---

## 🚀 LET'S BUILD!

**Current Focus:** Implement NinjaTrader Indicator (Layer 1)

**All Specs Complete! Next Steps:**
1. Review [NINJA_EXPORT_CHECKLIST.md](docs/NINJA_EXPORT_CHECKLIST.md) - 55 fields to export
2. Implement NinjaTrader C# indicator (Layer 1)
3. Implement Python processor modules (Layer 2)
4. ML Pipeline integration

**Remember:** Mỗi module độc lập, có thể test riêng, backtest riêng. Quality over speed!

---

**Last Updated:** November 21, 2025
**Status:** ✅ All 11 Module Specs Complete - Ready for Implementation 🚀
**Key Decision:** FVG is the only signal type, OB provides context features
