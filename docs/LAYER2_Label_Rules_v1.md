# LAYER 2: LABEL RULES V1

**Version:** 1.0.0
**Date:** November 24, 2025
**Layer:** 2 → 3 (Processor to ML Pipeline)
**Status:** Production Ready

---

## 1. Overview

Label Rules V1 implements deterministic labeling for ML training:
- **LONG**: All 6 bullish conditions satisfied
- **SHORT**: All 6 bearish conditions satisfied
- **SKIP**: Any condition fails

---

## 2. Label Rule (A) - Complete Flow

### 2.1 Master Decision Diagram

```mermaid
flowchart TD
    START[FVG Retest Event<br/>Detected] --> TYPE{FVG Direction?}

    TYPE -->|Bullish<br/>fvg_up = True| LONG_PATH
    TYPE -->|Bearish<br/>fvg_down = True| SHORT_PATH
    TYPE -->|Unknown| SKIP_INVALID[SKIP: Invalid FVG]

    subgraph LONG_PATH["LONG Label Path"]
        direction TB
        L1{ext_choch_down<br/>== True?}
        L2{fvg_retest<br/>== True?}
        L3{ext_dir<br/>== 1?}
        L4{mgann_leg_index<br/><= 2?}
        L5{pb_wave_strength_ok<br/>== True?}

        L1 -->|Yes| L2
        L1 -->|No| SKIP_L1[SKIP]
        L2 -->|Yes| L3
        L2 -->|No| SKIP_L2[SKIP]
        L3 -->|Yes| L4
        L3 -->|No| SKIP_L3[SKIP]
        L4 -->|Yes| L5
        L4 -->|No| SKIP_L4[SKIP]
        L5 -->|Yes| LONG[✅ LONG]
        L5 -->|No| SKIP_L5[SKIP]
    end

    subgraph SHORT_PATH["SHORT Label Path"]
        direction TB
        S1{ext_choch_up<br/>== True?}
        S2{fvg_retest<br/>== True?}
        S3{ext_dir<br/>== -1?}
        S4{mgann_leg_index<br/><= 2?}
        S5{pb_wave_strength_ok<br/>== True?}

        S1 -->|Yes| S2
        S1 -->|No| SKIP_S1[SKIP]
        S2 -->|Yes| S3
        S2 -->|No| SKIP_S2[SKIP]
        S3 -->|Yes| S4
        S3 -->|No| SKIP_S3[SKIP]
        S4 -->|Yes| S5
        S4 -->|No| SKIP_S4[SKIP]
        S5 -->|Yes| SHORT[✅ SHORT]
        S5 -->|No| SKIP_S5[SKIP]
    end

    style LONG fill:#81c784,stroke:#2e7d32
    style SHORT fill:#ef5350,stroke:#c62828
    style SKIP_INVALID fill:#bdbdbd
    style SKIP_L1 fill:#bdbdbd
    style SKIP_L2 fill:#bdbdbd
    style SKIP_L3 fill:#bdbdbd
    style SKIP_L4 fill:#bdbdbd
    style SKIP_L5 fill:#bdbdbd
    style SKIP_S1 fill:#bdbdbd
    style SKIP_S2 fill:#bdbdbd
    style SKIP_S3 fill:#bdbdbd
    style SKIP_S4 fill:#bdbdbd
    style SKIP_S5 fill:#bdbdbd
```

---

## 3. Conditions Detail

### 3.1 LONG Conditions

```mermaid
flowchart LR
    subgraph Conditions["6 LONG Conditions"]
        C1["1️⃣ ext_choch_down<br/>= True"]
        C2["2️⃣ fvg_up<br/>= True"]
        C3["3️⃣ fvg_retest<br/>= True"]
        C4["4️⃣ ext_dir<br/>= 1"]
        C5["5️⃣ mgann_leg_index<br/><= 2"]
        C6["6️⃣ pb_wave_strength_ok<br/>= True"]

        C1 --> C2 --> C3 --> C4 --> C5 --> C6
    end

    C6 --> RESULT{All True?}
    RESULT -->|Yes| LONG[LONG ✅]
    RESULT -->|No| SKIP[SKIP ❌]

    style LONG fill:#81c784
    style SKIP fill:#bdbdbd
```

### 3.2 SHORT Conditions

```mermaid
flowchart LR
    subgraph Conditions["6 SHORT Conditions"]
        C1["1️⃣ ext_choch_up<br/>= True"]
        C2["2️⃣ fvg_down<br/>= True"]
        C3["3️⃣ fvg_retest<br/>= True"]
        C4["4️⃣ ext_dir<br/>= -1"]
        C5["5️⃣ mgann_leg_index<br/><= 2"]
        C6["6️⃣ pb_wave_strength_ok<br/>= True"]

        C1 --> C2 --> C3 --> C4 --> C5 --> C6
    end

    C6 --> RESULT{All True?}
    RESULT -->|Yes| SHORT[SHORT ✅]
    RESULT -->|No| SKIP[SKIP ❌]

    style SHORT fill:#ef5350
    style SKIP fill:#bdbdbd
```

---

## 4. Condition Explanations

### 4.1 Condition Matrix

```mermaid
graph TD
    subgraph Explanations["Condition Explanations"]
        E1["<b>ext_choch_down/up</b><br/>External CHoCH indicates<br/>major reversal point"]
        E2["<b>fvg_up/down</b><br/>FVG provides<br/>entry zone"]
        E3["<b>fvg_retest</b><br/>Price tested FVG zone<br/>confirms interest"]
        E4["<b>ext_dir</b><br/>Current trend aligned<br/>with trade direction"]
        E5["<b>mgann_leg_index</b><br/>Early entry (leg 1-2)<br/>= better RR"]
        E6["<b>pb_wave_strength_ok</b><br/>Pullback shows exhaustion<br/>= ready to continue"]
    end

    E1 --> E2 --> E3
    E4 --> E5 --> E6
```

### 4.2 Field Sources

| Condition | Source Module | Field Type |
|-----------|---------------|------------|
| ext_choch_down/up | Module #03 Structure Context | bool |
| fvg_up/down | Module #02 FVG Quality | bool |
| fvg_retest | Module #12 FVG Retest | bool |
| ext_dir | Module #03 Structure Context | int |
| mgann_leg_index | Module #14 MGann Swing | int |
| pb_wave_strength_ok | Module #14 MGann Swing | bool |

---

## 5. Label Distribution

### 5.1 Target Distribution

```mermaid
pie title Expected Label Distribution
    "LONG" : 35
    "SHORT" : 35
    "SKIP" : 30
```

### 5.2 Dataset Requirements

```mermaid
flowchart LR
    subgraph Dataset["Dataset Configuration"]
        D1[Min Events: 1000]
        D2[Max Events: 1500]
        D3[Train: 70%]
        D4[Val: 30%]
    end

    D1 & D2 --> SPLIT[Dataset Split]
    SPLIT --> D3
    SPLIT --> D4
```

---

## 6. Skip Reasons Analysis

### 6.1 Common Skip Reasons

```mermaid
flowchart TD
    SKIP[SKIP Label] --> REASONS

    subgraph REASONS["Skip Reasons"]
        R1["No CHoCH<br/>(35% of skips)"]
        R2["Late Entry<br/>leg > 2<br/>(25% of skips)"]
        R3["Weak PB Strength<br/>(20% of skips)"]
        R4["Direction Mismatch<br/>(10% of skips)"]
        R5["No FVG Retest<br/>(10% of skips)"]
    end

    R1 --> ACTION1[Wait for CHoCH]
    R2 --> ACTION2[Entry window closed]
    R3 --> ACTION3[Pullback not weak enough]
    R4 --> ACTION4[Trend not aligned]
    R5 --> ACTION5[No valid touch]
```

---

## 7. Implementation

### 7.1 Python Implementation

```python
def apply_label_rule_a(event: dict) -> dict:
    """
    Apply Label Rule (A) to determine signal label.

    Returns:
        dict: {label, confidence, reason, conditions_met, conditions_failed}
    """
    fvg_type = event.get("fvg_type", "unknown")

    if fvg_type == "bullish" or event.get("fvg_up", False):
        return apply_label_rule_long(event)
    elif fvg_type == "bearish" or event.get("fvg_down", False):
        return apply_label_rule_short(event)
    else:
        return {
            "label": "skip",
            "confidence": 0.0,
            "reason": "No valid FVG detected"
        }
```

### 7.2 Labeling Process Flow

```mermaid
sequenceDiagram
    participant E as EventState
    participant L as Label Rule (A)
    participant D as Dataset

    E->>L: Submit event for labeling
    L->>L: Check FVG direction
    L->>L: Evaluate 6 conditions

    alt All conditions pass
        L-->>E: label = "long" or "short"
    else Any condition fails
        L-->>E: label = "skip"
    end

    E->>D: Add to train.jsonl
```

---

## 8. Quality Metrics

### 8.1 Label Quality Validation

```mermaid
flowchart TD
    subgraph Validation["Label Validation Pipeline"]
        V1[Generate Labels]
        V2[Backtest Results]
        V3[Compare Win Rates]
        V4[Adjust Thresholds]

        V1 --> V2 --> V3 --> V4
        V4 -.-> V1
    end

    subgraph Metrics["Target Metrics"]
        M1["Win Rate >= 40%"]
        M2["Label Accuracy >= 70%"]
        M3["Balanced Distribution"]
    end

    V3 --> Metrics
```

### 8.2 Expected Results

| Label | Win Rate Target | Distribution |
|-------|-----------------|--------------|
| LONG | >= 40% | ~35% |
| SHORT | >= 40% | ~35% |
| SKIP | N/A (filtered) | ~30% |

---

## 9. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-24 | Initial Label Rules V1 with Mermaid diagrams |

---

**Status:** Production Ready
**Related:** [LABEL_RULES.md](LABEL_RULES.md), [ARCHITECTURE_V3.md](../ARCHITECTURE_V3.md)
