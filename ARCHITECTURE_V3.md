# LAYER ARCHITECTURE V3 - SMC + MGannSwing + ML System

**Version:** 3.0.0
**Date:** November 23, 2025
**Status:** Production Ready
**Author:** System Architecture Team

---

## Document Overview

| Section | Description |
|---------|-------------|
| [1. Architecture Overview](#1-architecture-overview) | High-level 3-layer design |
| [2. Label Rule (A)](#2-label-rule-a---official-version) | Official labeling logic |
| [3. Entry Cases](#3-entry-cases-a--b) | Case A & Case B entry strategies |
| [4. SMC Flow](#4-smc-standard-flow) | Complete trading flow |
| [5. New Fields](#5-new-exporter-fields) | mgann_leg_index, pb_wave_strength_ok |
| [6. ML Training Notes](#6-ml-training-notes) | Dataset generation |

---

## 1. Architecture Overview

### 1.1 Three-Layer Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: NinjaTrader C# Indicator                 │
│                    (Real-time Raw Data Detection)                    │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  • FVG Detection (boundaries only)                               │ │
│  │  • OB Detection (boundaries only)                                │ │
│  │  • CHoCH Detection (external/internal)                           │ │
│  │  • Swing Points (ext_swing_high/low, int_swing_high/low)        │ │
│  │  • Volume/Delta Raw Data                                         │ │
│  │  • MGann Internal Swing (tick-based zigzag)                      │ │
│  │  • NO SCORING, NO QUALITY ASSESSMENT                             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                              ↓ JSONL Export                          │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 2: Python Data Processor                    │
│                    (Offline/Batch Quality Scoring)                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  14 Independent Modules:                                         │ │
│  │  #01 OB Quality    #02 FVG Quality     #03 Structure Context    │ │
│  │  #04 Confluence    #05 Stop Placement  #06 Target Placement     │ │
│  │  #07 Market Cond   #08 Volume Div      #09 Volume Profile       │ │
│  │  #10 MTF Align     #11 Liquidity Map   #12 FVG Retest Filter    │ │
│  │  #13 Wave Delta    #14 MGann Swing                              │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                              ↓ BarState → EventState                 │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 3: ML Pipeline                              │
│                    (Training Data Generation)                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  • Apply Label Rule (A)                                          │ │
│  │  • Generate train.jsonl / val.jsonl                              │ │
│  │  • Dataset: 1000-1500 events                                     │ │
│  │  • Labels: "long" / "short" / "skip"                             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Layer Objectives

| Layer | Objective | Input | Output |
|-------|-----------|-------|--------|
| **Layer 1** | Raw detection only, no intelligence | Market data tick-by-tick | `raw_smc_export.jsonl` |
| **Layer 2** | Apply quality scoring, filtering | Raw JSONL | `BarState`, `EventState` |
| **Layer 3** | Generate ML training data | EventState | `train.jsonl`, `val.jsonl` |

---

## 2. Label Rule (A) - Official Version

### 2.1 Long Label Conditions

```python
# LABEL RULE (A) - LONG
def apply_label_rule_long(event: EventState) -> str:
    """
    Official Label Rule (A) for LONG signals.
    All conditions must be TRUE for label = "long"
    """
    conditions = [
        event.ext_choch_down == True,        # External CHoCH down (reversal signal)
        event.fvg_up == True,                # Bullish FVG exists
        event.fvg_retest == True,            # FVG has been retested
        event.ext_dir == 1,                  # External direction is UP
        event.mgann_leg_index <= 2,          # MGann leg 1 or 2 (early entry)
        event.pb_wave_strength_ok == True,   # Pullback wave strength confirmed
    ]

    if all(conditions):
        return "long"
    else:
        return "skip"
```

### 2.2 Short Label Conditions

```python
# LABEL RULE (A) - SHORT
def apply_label_rule_short(event: EventState) -> str:
    """
    Official Label Rule (A) for SHORT signals.
    All conditions must be TRUE for label = "short"
    """
    conditions = [
        event.ext_choch_up == True,          # External CHoCH up (reversal signal)
        event.fvg_down == True,              # Bearish FVG exists
        event.fvg_retest == True,            # FVG has been retested
        event.ext_dir == -1,                 # External direction is DOWN
        event.mgann_leg_index <= 2,          # MGann leg 1 or 2 (early entry)
        event.pb_wave_strength_ok == True,   # Pullback wave strength confirmed
    ]

    if all(conditions):
        return "short"
    else:
        return "skip"
```

### 2.3 Label Rule Flowchart

```
                         ┌─────────────────┐
                         │  FVG Retest     │
                         │  Event Detected │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
              ┌─────▼─────┐               ┌─────▼─────┐
              │ Bullish   │               │ Bearish   │
              │ FVG       │               │ FVG       │
              └─────┬─────┘               └─────┬─────┘
                    │                           │
              ┌─────▼─────────────┐       ┌─────▼─────────────┐
              │ ext_choch_down?   │       │ ext_choch_up?     │
              │ (CHoCH từ DOWN)   │       │ (CHoCH từ UP)     │
              └─────┬─────────────┘       └─────┬─────────────┘
                    │ YES                       │ YES
              ┌─────▼─────────────┐       ┌─────▼─────────────┐
              │ ext_dir == 1?     │       │ ext_dir == -1?    │
              │ (Trending UP)     │       │ (Trending DOWN)   │
              └─────┬─────────────┘       └─────┬─────────────┘
                    │ YES                       │ YES
              ┌─────▼─────────────┐       ┌─────▼─────────────┐
              │ mgann_leg_index   │       │ mgann_leg_index   │
              │ <= 2?             │       │ <= 2?             │
              └─────┬─────────────┘       └─────┬─────────────┘
                    │ YES                       │ YES
              ┌─────▼─────────────┐       ┌─────▼─────────────┐
              │ pb_wave_strength  │       │ pb_wave_strength  │
              │ _ok == True?      │       │ _ok == True?      │
              └─────┬─────────────┘       └─────┬─────────────┘
                    │ YES                       │ YES
              ┌─────▼─────┐               ┌─────▼─────┐
              │  LONG     │               │  SHORT    │
              └───────────┘               └───────────┘

              ANY CONDITION FAILS → SKIP
```

### 2.4 Condition Explanations

| Condition | Meaning | Why Important |
|-----------|---------|---------------|
| `ext_choch_down` | External structure broke DOWN then reclaimed | Indicates reversal from bearish to bullish |
| `ext_choch_up` | External structure broke UP then reclaimed | Indicates reversal from bullish to bearish |
| `fvg_up/down` | Bullish/Bearish FVG exists | Entry zone exists |
| `fvg_retest` | Price has retested the FVG | Confirms institutional interest |
| `ext_dir == 1/-1` | Current external trend direction | Aligned with trade direction |
| `mgann_leg_index <= 2` | Entry in leg 1 or 2 of MGann swing | Early entry = better RR |
| `pb_wave_strength_ok` | Pullback wave shows weakness | Confirms exhaustion of counter-trend |

---

## 3. Entry Cases (A & B)

### 3.1 Case A: FVG Leg 1 Not Filled

```
┌─────────────────────────────────────────────────────────────────┐
│                      CASE A: FVG LEG 1 ENTRY                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Điều kiện: FVG tạo ở Leg 1 CHƯA bị fill                        │
│                                                                  │
│  Price Action:                                                   │
│                                                                  │
│        │                                                         │
│        │    ┌──── Swing High                                    │
│        │   /│                                                    │
│       /│  / │                                                    │
│      / │ /  │                                                    │
│     /  │/   │                                                    │
│    /   └────┼──── FVG Zone (Leg 1) ← ENTRY HERE                 │
│   /         │                                                    │
│  └──────────┴──── CHoCH Down                                    │
│                                                                  │
│  Entry Logic:                                                    │
│  1. CHoCH Down xảy ra                                           │
│  2. Leg 1 UP tạo FVG                                            │
│  3. FVG chưa bị price fill (< 50% penetration)                  │
│  4. Entry tại FVG edge khi price retest                         │
│                                                                  │
│  Ưu điểm:                                                        │
│  - RR cao nhất (entry sớm nhất)                                 │
│  - FVG còn fresh, institutional interest cao                    │
│  - Confluence với CHoCH vừa xảy ra                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Case B: FVG Leg 2 Entry (Fallback)

```
┌─────────────────────────────────────────────────────────────────┐
│                      CASE B: FVG LEG 2 ENTRY                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Điều kiện:                                                      │
│  - Leg 1 KHÔNG có FVG, HOẶC                                     │
│  - FVG Leg 1 đã bị fill (> 80% penetration)                     │
│                                                                  │
│  Price Action:                                                   │
│                                                                  │
│           │                                                      │
│           │    ┌──── Swing High (mới)                           │
│          /│   /│                                                 │
│         / │  / │                                                 │
│        /  │ /  │                                                 │
│       /   │/   │                                                 │
│      /    └────┼──── FVG Leg 1 (FILLED hoặc không có)           │
│     │          │                                                 │
│     │    ┌─────┼──── FVG Zone (Leg 2) ← ENTRY HERE              │
│     │   /      │                                                 │
│     └──/───────┴                                                 │
│                                                                  │
│  Entry Logic:                                                    │
│  1. Leg 1 không có FVG hoặc FVG đã filled                       │
│  2. Leg 2 UP tạo FVG mới                                        │
│  3. Entry tại FVG Leg 2                                         │
│                                                                  │
│  Nhược điểm:                                                     │
│  - RR thấp hơn Case A (entry muộn hơn)                          │
│  - Nhưng vẫn valid nếu FVG quality tốt                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Unified Rule for Dataset

```python
# Dataset 1000-1500 events sẽ gộp cả Case A và Case B thành 1 rule:
def get_entry_fvg(event: EventState) -> dict:
    """
    Get the best FVG for entry (Case A or Case B).

    Returns:
        dict: Best FVG zone for entry
    """
    # Ưu tiên Case A (Leg 1 FVG chưa fill)
    if event.mgann_leg_first_fvg is not None:
        if not event.mgann_leg_first_fvg.is_filled:
            return {
                "case": "A",
                "fvg": event.mgann_leg_first_fvg,
                "mgann_leg_index": 1
            }

    # Fallback to Case B (Leg 2 FVG)
    if event.mgann_leg_index == 2:
        return {
            "case": "B",
            "fvg": event.current_fvg,
            "mgann_leg_index": 2
        }

    return None
```

---

## 4. SMC Standard Flow

### 4.1 Complete Trading Flow (Long Setup)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SMC STANDARD FLOW - LONG SETUP                        │
└─────────────────────────────────────────────────────────────────────────┘

Step 1: External CHoCH Down
──────────────────────────
     │
     │     ▲ Swing High
     │    /│
     │   / │
     │  /  │
     │ /   │
     │/    └─────── Structure Break (CHoCH)
     │              ext_choch_down = True

Step 2: Reclaim (Price moves back UP)
─────────────────────────────────────
     │
     │     ▲ Swing High
     │    /│\
     │   / │ \    ← Price reclaims
     │  /  │  \      ext_dir = 1 (UP)
     │ /   │   \
     │/    │    \
     │     │     └── Lower Low (sweep)

Step 3: MGann Leg UP + FVG Creation
───────────────────────────────────
     │
     │     ▲ New High
     │    /│
     │   / │
     │  /──┼──── FVG ZONE
     │ /   │     fvg_up = True
     │/    │
     │     │
     │     └── After CHoCH reclaim
              mgann_leg_index = 1

Step 4: FVG Retest
──────────────────
     │
     │     ▲
     │    /│\
     │   / │ \
     │  /──┼──┼── FVG ZONE
     │ /   │  │\
     │/    │  │ \← Retest (price touches FVG)
     │     │  │     fvg_retest = True
     │     │  │

Step 5: Wave Strength Check (Hybrid Rule v4)
────────────────────────────────────────────
     During retest, check pullback wave:
     - Pullback must stay shallow (no structure break)
     - pb_wave_strength_ok = True only if ALL 6 conditions pass:

     **Hybrid Rule v4 (Implemented in Module 14):**
     
     1. Wave Strength Gate:
        mgann_wave_strength_pullback < 40
     
     2. Delta Ratio Check:
        |pullback_delta| <= |impulse_delta| * 0.3
     
     3. Volume Ratio Check:
        pullback_volume <= impulse_volume * 0.6
     
     4. Absolute Delta Gate:
        (uptrend)   pullback_delta >= -35
        (downtrend) pullback_delta <= 35
     
     5. Volume vs Average:
        pullback_volume <= avg_volume * 1.0
     
     6. Structure Preservation:
        (uptrend)   pullback_low > leg1_low
        (downtrend) pullback_high < leg1_high

     **All 6 conditions must be TRUE for pb_wave_strength_ok = True**

Step 6: LONG ENTRY
──────────────────
     │
     │     ▲ Target
     │    /│
     │   / │
     │  /──┼──── ENTRY at FVG edge
     │ /   │
     │/    └──── Stop Loss below FVG
     │
```

### 4.2 Flow Conditions Summary

```
┌───────────────┬─────────────────────────────────────────────────────┐
│ Step          │ Required Condition                                   │
├───────────────┼─────────────────────────────────────────────────────┤
│ 1. CHoCH      │ ext_choch_down = True (for LONG)                    │
│ 2. Reclaim    │ ext_dir = 1 (trending UP after CHoCH)               │
│ 3. FVG        │ fvg_up = True, FVG created in leg 1 or 2            │
│ 4. Retest     │ fvg_retest = True, penetration < 50%                │
│ 5. Wave       │ pb_wave_strength_ok = True                          │
│ 6. Entry      │ mgann_leg_index <= 2 (early entry)                  │
└───────────────┴─────────────────────────────────────────────────────┘
```

---

## 5. New Exporter Fields

### 5.1 Required New Fields

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `mgann_leg_index` | int | Module #14 | Current leg index (1, 2, 3...) from MGann swing |
| `mgann_leg_first_fvg` | object | Module #14 + #02 | First FVG in current MGann leg sequence |
| `pb_wave_strength_ok` | bool | Module #13 + #14 | Pullback wave strength confirmed |

### 5.2 Field Definitions

```python
# mgann_leg_index
# ----------------
# Tracks which leg of the MGann internal swing we're in
# Leg 1 = First move after CHoCH
# Leg 2 = Second move (pullback completed)
# Leg 3+ = Later moves (lower probability)

mgann_leg_index: int  # 1, 2, 3, ...

# mgann_leg_first_fvg
# -------------------
# Reference to the first FVG created in the current leg sequence
# Used to determine if Case A (leg 1 FVG) is still valid

mgann_leg_first_fvg: {
    "fvg_high": float,
    "fvg_low": float,
    "fvg_type": str,          # "bullish" / "bearish"
    "creation_bar_index": int,
    "is_filled": bool,        # True if > 80% penetration
    "fill_ratio": float,      # 0.0 - 1.0+
    "leg_index": int          # Which leg created this FVG
}

# pb_wave_strength_ok
# -------------------
# Computed by Module #14 (MGann Swing) using Hybrid Rule v4
# True if pullback wave shows weakness (confirmation for entry)

pb_wave_strength_ok: bool

# Hybrid Rule v4 Calculation (Module 14):
# ALL 6 conditions must be TRUE:
#
# 1. mgann_wave_strength_pullback < 40
# 2. abs(pullback_delta) <= abs(impulse_delta) * 0.3
# 3. pullback_volume <= impulse_volume * 0.6
# 4. pullback_delta >= -35 (uptrend) or <= 35 (downtrend)
# 5. pullback_volume <= avg_volume * 1.0
# 6. pb_low > leg1_low (uptrend) or pb_high < leg1_high (downtrend)
```

### 5.3 Updated EventState Schema

```python
@dataclass
class EventState:
    # ... existing fields ...

    # === NEW FIELDS (Layer Architecture v3) ===

    # MGann Leg Tracking
    mgann_leg_index: int              # 1, 2, 3, ... (prefer <= 2)
    mgann_leg_first_fvg: dict         # First FVG reference

    # Wave Strength
    pb_wave_strength_ok: bool         # Pullback wave confirmation
    pb_wave_delta_ratio: float        # pullback_delta / impulse_delta
    pb_wave_volume_ratio: float       # pullback_vol / impulse_vol

    # CHoCH State
    ext_choch_down: bool              # External CHoCH from DOWN
    ext_choch_up: bool                # External CHoCH from UP

    # FVG State
    fvg_up: bool                      # Bullish FVG exists
    fvg_down: bool                    # Bearish FVG exists
    fvg_retest: bool                  # FVG has been retested
```

---

## 6. ML Training Notes

### 6.1 Dataset Generation

```python
# Dataset size: 1000-1500 events
# Split: 70% train / 30% validation

DATASET_CONFIG = {
    "min_events": 1000,
    "max_events": 1500,
    "train_ratio": 0.7,
    "val_ratio": 0.3,

    # Label distribution target
    "target_distribution": {
        "long": 0.35,   # ~35% long signals
        "short": 0.35,  # ~35% short signals
        "skip": 0.30    # ~30% skip
    },

    # Quality filters before ML
    "pre_filters": {
        "min_fvg_quality_score": 0.5,
        "max_penetration_ratio": 0.5,
        "require_wave_strength_ok": True,
        "max_mgann_leg_index": 2
    }
}
```

### 6.2 Feature Engineering

```python
# Features for ML model
FEATURES = {
    # Core SMC Features
    "fvg_quality_score": float,           # 0-1
    "fvg_strength_class": categorical,    # Strong/Medium/Weak
    "fvg_penetration_ratio": float,       # 0-1+
    "fvg_retest_type": categorical,       # edge/shallow/deep/break

    # MGann Features (NEW in v3)
    "mgann_leg_index": int,               # 1, 2, 3+
    "mgann_wave_strength": float,         # 0-100
    "pb_wave_strength_ok": bool,
    "mgann_behavior": categorical,        # PB/UT/SP/EX3

    # Context Features
    "ext_dir": int,                       # 1/-1
    "market_condition_score": float,      # 0-1
    "confluence_score": float,            # 0-100

    # Volume Features
    "volume_delta_ratio": float,
    "vol_div_score": float,
}
```

### 6.3 Label Rule Integration

```python
def generate_training_data(events: List[EventState]) -> Tuple[List, List]:
    """
    Generate training data using Label Rule (A).

    Returns:
        train_data, val_data
    """
    labeled_events = []

    for event in events:
        # Apply Label Rule (A)
        if event.fvg_type == "bullish":
            label = apply_label_rule_long(event)
        else:
            label = apply_label_rule_short(event)

        if label != "skip":
            labeled_events.append({
                "features": extract_features(event),
                "label": label,
                "outcome": {
                    "hit": event.hit,
                    "outcome_rr": event.outcome_rr,
                    "mfe": event.mfe,
                    "mae": event.mae
                }
            })

    # Split train/val
    split_idx = int(len(labeled_events) * 0.7)
    train_data = labeled_events[:split_idx]
    val_data = labeled_events[split_idx:]

    return train_data, val_data
```

### 6.4 Model Target Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Win Rate | >= 40% | After all filters |
| Profit Factor | >= 1.5 | Risk-adjusted returns |
| Max Drawdown | <= 15% | Risk management |
| Sharpe Ratio | >= 1.2 | Risk-adjusted performance |
| Label Accuracy | >= 70% | ML model performance |

---

## 7. Module Documentation Standard (v3)

### 7.1 Required Sections

Every MODULE_FIX*.md must contain:

```markdown
# MODULE FIX #XX: [NAME]

**Version:** X.X.X
**Layer:** [1/2/3]
**Status:** [Draft/Complete/Implemented/Tested]

## 1. Objective
- Problem statement
- Solution approach
- Success criteria

## 2. Input Schema
- Required fields
- Optional fields
- Field types and ranges

## 3. Output Schema
- All output fields
- Field types and ranges
- Null/default values

## 4. Rule Logic
- Core algorithm
- Threshold values
- Edge cases

## 5. Flowchart
- ASCII diagram or Mermaid
- Decision tree

## 6. ML Training Notes
- How this module affects labeling
- Feature importance
- Data requirements

## 7. Integration
- Dependencies
- Execution order
- API examples

## 8. Testing
- Unit test coverage
- Backtest results
- Validation metrics
```

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | 2025-11-23 | Initial Layer Architecture v3 with Label Rule (A), Case A/B, new fields |
| 2.1.0 | 2025-11-21 | FVG Quality v2.0, Wave Delta module |
| 2.0.0 | 2025-11-20 | 14 module architecture |
| 1.0.0 | 2025-11-15 | Initial 3-layer design |

---

## 9. References

- [ARCHITECTURE.md](ARCHITECTURE.md) - Previous version (v2.1.0)
- [MODULE_FIX14_MGANN_SWING.md](docs/MODULE_FIX14_MGANN_SWING.md) - MGann Swing module
- [MODULE_FIX02_FVG_QUALITY.md](docs/MODULE_FIX02_FVG_QUALITY.md) - FVG Quality module
- [LABEL_RULES.md](docs/LABEL_RULES.md) - Complete labeling logic
- [NINJA_EXPORT_CHECKLIST.md](docs/NINJA_EXPORT_CHECKLIST.md) - Export field checklist

---

**Status:** Production Ready
**Next Steps:** Implement new fields in exporter, update ML pipeline
