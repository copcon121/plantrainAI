# SMC SHORT STRATEGY V1

**Version:** 1.0.0
**Date:** November 24, 2025
**Strategy Type:** Short (Bearish)
**Status:** Production Ready

---

## 1. Strategy Overview

### 1.1 Core Concept

The SMC Short Strategy identifies high-probability short entries using:
- External CHoCH Up (reversal signal from bullish)
- MGann Swing Leg tracking (entry timing)
- FVG Retest (entry zone - bearish)
- Pullback Wave Strength (confirmation)

---

## 2. Strategy Flow Diagram

### 2.1 Main Entry Flow

```mermaid
flowchart TD
    subgraph Phase1["PHASE 1: Structure Break"]
        A[Price in Uptrend] --> B[External CHoCH UP<br/>ext_choch_up = True]
        B --> C[Structure Break Confirmed]
    end

    subgraph Phase2["PHASE 2: Reclaim"]
        C --> D[Price Reclaims Down<br/>into Previous Range]
        D --> E[ext_dir = -1<br/>Downtrend Confirmed]
    end

    subgraph Phase3["PHASE 3: MGann Leg Formation"]
        E --> F[MGann Swing Leg 1 DOWN]
        F --> G{FVG Created<br/>in Leg 1?}
    end

    subgraph Phase4["PHASE 4: Entry Decision"]
        G -->|Yes| H[Case A: FVG Leg 1<br/>mgann_leg_index = 1]
        G -->|No/Filled| I[Wait for Leg 2]
        I --> J[Case B: FVG Leg 2<br/>mgann_leg_index = 2]
        H --> K[Wait for FVG Retest]
        J --> K
    end

    subgraph Phase5["PHASE 5: Confirmation"]
        K --> L{FVG Retest<br/>fvg_retest = True?}
        L -->|Yes| M{Pullback Wave<br/>Strength OK?}
        L -->|No| N[Continue Waiting]
        M -->|Yes| O[✅ ENTRY SHORT]
        M -->|No| P[❌ SKIP]
    end

    style A fill:#c8e6c9
    style B fill:#fff9c4
    style E fill:#ffcdd2
    style O fill:#ef5350
    style P fill:#bdbdbd
```

### 2.2 Detailed Price Action Flow

```mermaid
flowchart LR
    subgraph PriceAction["Price Action Sequence"]
        direction TB
        PA1["📈 Uptrend"]
        PA2["🔄 CHoCH Up<br/>(Break of Structure)"]
        PA3["📉 Reclaim DOWN"]
        PA4["⬇️ Leg 1 Impulse<br/>(Creates FVG)"]
        PA5["⬆️ Pullback<br/>(Weak Delta)"]
        PA6["🎯 FVG Retest"]
        PA7["✅ SHORT Entry"]

        PA1 --> PA2 --> PA3 --> PA4 --> PA5 --> PA6 --> PA7
    end
```

---

## 3. Entry Conditions

### 3.1 All Required Conditions

```mermaid
flowchart TD
    START[FVG Retest Event Detected] --> C1

    C1{ext_choch_up<br/>== True?}
    C1 -->|Yes| C2
    C1 -->|No| SKIP1[SKIP: No CHoCH]

    C2{fvg_down<br/>== True?}
    C2 -->|Yes| C3
    C2 -->|No| SKIP2[SKIP: No Bearish FVG]

    C3{fvg_retest<br/>== True?}
    C3 -->|Yes| C4
    C3 -->|No| SKIP3[SKIP: No Retest]

    C4{ext_dir<br/>== -1?}
    C4 -->|Yes| C5
    C4 -->|No| SKIP4[SKIP: Wrong Direction]

    C5{mgann_leg_index<br/><= 2?}
    C5 -->|Yes| C6
    C5 -->|No| SKIP5[SKIP: Late Entry]

    C6{pb_wave_strength_ok<br/>== True?}
    C6 -->|Yes| SHORT[✅ SHORT ENTRY]
    C6 -->|No| SKIP6[SKIP: Weak Pullback]

    style SHORT fill:#ef5350,stroke:#c62828
    style SKIP1 fill:#bdbdbd
    style SKIP2 fill:#bdbdbd
    style SKIP3 fill:#bdbdbd
    style SKIP4 fill:#bdbdbd
    style SKIP5 fill:#bdbdbd
    style SKIP6 fill:#bdbdbd
```

### 3.2 Conditions Summary Table

| # | Condition | Field | Value | Purpose |
|---|-----------|-------|-------|---------|
| 1 | CHoCH Up | `ext_choch_up` | `True` | Reversal signal |
| 2 | Bearish FVG | `fvg_down` | `True` | Entry zone exists |
| 3 | FVG Retest | `fvg_retest` | `True` | Price tested zone |
| 4 | Downtrend | `ext_dir` | `-1` | Aligned direction |
| 5 | Early Leg | `mgann_leg_index` | `<= 2` | Better RR |
| 6 | PB Weak | `pb_wave_strength_ok` | `True` | Exhaustion confirmed |

---

## 4. Case A vs Case B Entry

### 4.1 Entry Case Decision

```mermaid
flowchart TD
    subgraph CaseDecision["Entry Case Selection"]
        START[CHoCH Confirmed] --> LEG1[MGann Leg 1 Forms]
        LEG1 --> CHECK{FVG in Leg 1?}

        CHECK -->|Yes + Not Filled| CASE_A
        CHECK -->|No or Filled| CASE_B

        subgraph CASE_A["CASE A: Leg 1 Entry"]
            A1[FVG Created in Leg 1]
            A2[FVG Not Filled < 80%]
            A3[Entry at FVG Leg 1]
            A4[Best RR Potential]
            A1 --> A2 --> A3 --> A4
        end

        subgraph CASE_B["CASE B: Leg 2 Entry"]
            B1[Leg 1 No FVG or Filled]
            B2[Wait for Pullback]
            B3[Leg 2 Creates New FVG]
            B4[Entry at FVG Leg 2]
            B1 --> B2 --> B3 --> B4
        end
    end

    style CASE_A fill:#ffcdd2
    style CASE_B fill:#fff9c4
```

### 4.2 Visual Price Action

```
CASE A (Best Scenario):
    CHoCH ────┐
               \    │
                \───┤ ← FVG Zone (Entry)
                 \  │
                  \ │
                   \│
                    └─── Leg 1 Low
                         Stop Loss Above

CASE B (Fallback):
    CHoCH──┐       ┌─────┐
           │      /      │
           \│(filled)    │
            └─── Leg 1  /──┤ ← FVG Zone (Entry)
                       /   │
                      /    │
                     └─── Leg 2 Low
```

---

## 5. Risk Management

### 5.1 Stop Loss Placement

```mermaid
flowchart TD
    subgraph SL["Stop Loss Options"]
        SL1["Option 1: Above FVG High<br/>(Tightest)"]
        SL2["Option 2: Above Swing High<br/>(Standard)"]
        SL3["Option 3: Above OB Source<br/>(Conservative)"]
    end

    ENTRY[Entry at FVG Edge] --> SL1 & SL2 & SL3

    SL1 --> RR1["RR: 3-5x"]
    SL2 --> RR2["RR: 2-3x"]
    SL3 --> RR3["RR: 1.5-2x"]

    style SL1 fill:#ffcdd2
    style SL2 fill:#fff9c4
    style SL3 fill:#c8e6c9
```

### 5.2 Target Placement

| Target | Description | RR |
|--------|-------------|-----|
| TP1 | Nearest structure low | 1:1 - 1.5:1 |
| TP2 | Previous swing low | 2:1 - 3:1 |
| TP3 | Liquidity below | 3:1+ |

---

## 6. Long vs Short Comparison

```mermaid
flowchart LR
    subgraph LONG["LONG Strategy"]
        L1[ext_choch_down]
        L2[fvg_up]
        L3[ext_dir = 1]
        L4[Entry: Buy]
        L1 --> L2 --> L3 --> L4
    end

    subgraph SHORT["SHORT Strategy"]
        S1[ext_choch_up]
        S2[fvg_down]
        S3[ext_dir = -1]
        S4[Entry: Sell]
        S1 --> S2 --> S3 --> S4
    end

    LONG ---|Mirror| SHORT

    style LONG fill:#c8e6c9
    style SHORT fill:#ffcdd2
```

---

## 7. Validation Metrics

### 7.1 Expected Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Win Rate | >= 40% | After all filters |
| Average RR | >= 2.0 | Risk-adjusted |
| Profit Factor | >= 1.5 | Gross profit / Gross loss |
| Max Drawdown | <= 15% | Risk management |

### 7.2 Correlation with Label Rule (A)

```python
# Label Rule (A) - SHORT
def is_valid_short(event):
    return all([
        event.ext_choch_up == True,
        event.fvg_down == True,
        event.fvg_retest == True,
        event.ext_dir == -1,
        event.mgann_leg_index <= 2,
        event.pb_wave_strength_ok == True,
    ])
```

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-24 | Initial SMC Short Strategy with Mermaid diagrams |

---

**Status:** Production Ready
**Related:** [Label Rules](LABEL_RULES.md), [MGann Swing](MODULE_FIX14_MGANN_SWING.md)
