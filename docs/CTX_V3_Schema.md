# CTX V3 SCHEMA - Context Window Layout

**Version:** 3.0.0
**Date:** November 24, 2025
**Purpose:** Define context window structure for ML training
**Status:** Production Ready

---

## 1. Overview

The CTX V3 Schema defines the structure of the 30-50 bar context window used for ML training. Each context window contains:
- Historical bar features (30-50 bars)
- Current bar features
- Target label (long/short/skip)

---

## 2. Context Window Structure

### 2.1 Complete Schema Diagram

```mermaid
graph TD
    subgraph CTX["Context Window (30-50 bars)"]
        direction TB

        subgraph PerBar["Per-Bar Features"]
            direction LR
            F1[OHLC]
            F2[Volume/Delta]
            F3[SMC Flags]
            F4[Structure]
            F5[MGann]
        end

        subgraph OHLC["Price Data"]
            O1[open]
            O2[high]
            O3[low]
            O4[close]
        end

        subgraph Volume["Volume Data"]
            V1[volume]
            V2[delta]
            V3[buy_vol]
            V4[sell_vol]
        end

        subgraph SMC["SMC Flags"]
            S1[ext_bos]
            S2[ext_choch]
            S3[int_bos]
            S4[int_choch]
        end

        subgraph Structure["Structure"]
            ST1[ext_dir]
            ST2[int_dir]
            ST3[sweep_prev_high]
            ST4[sweep_prev_low]
        end

        subgraph MGann["MGann Features"]
            M1[mgann_leg_index]
            M2[mgann_wave_strength]
            M3[pb_wave_strength_ok]
            M4[mgann_leg_first_fvg]
        end

        F1 --> OHLC
        F2 --> Volume
        F3 --> SMC
        F4 --> Structure
        F5 --> MGann
    end

    CTX --> CURRENT[Current Bar Features]
    CTX --> TARGET[Label/Target]

    style CTX fill:#e3f2fd
    style CURRENT fill:#fff8e1
    style TARGET fill:#e8f5e9
```

### 2.2 Feature Categories

```mermaid
flowchart LR
    subgraph Categories["Feature Categories"]
        direction TB

        subgraph Price["Price (4 fields)"]
            P1[open]
            P2[high]
            P3[low]
            P4[close]
        end

        subgraph Vol["Volume (4 fields)"]
            V1[volume]
            V2[delta]
            V3[buy_vol]
            V4[sell_vol]
        end

        subgraph ExtSMC["External SMC (4 fields)"]
            E1[ext_bos]
            E2[ext_choch]
            E3[ext_choch_down]
            E4[ext_choch_up]
        end

        subgraph IntSMC["Internal SMC (4 fields)"]
            I1[int_bos]
            I2[int_choch]
            I3[int_dir]
            I4[sweep flags]
        end

        subgraph FVG["FVG (5 fields)"]
            F1[fvg_up]
            F2[fvg_down]
            F3[fvg_retest]
            F4[fvg_penetration]
            F5[fvg_quality]
        end

        subgraph MGann["MGann (4 fields)"]
            M1[mgann_leg_index]
            M2[wave_strength]
            M3[pb_wave_ok]
            M4[leg_first_fvg]
        end
    end

    Price --> Total[Total: ~25 fields per bar]
    Vol --> Total
    ExtSMC --> Total
    IntSMC --> Total
    FVG --> Total
    MGann --> Total
```

---

## 3. Detailed Field Specification

### 3.1 Per-Bar Features Table

| Category | Field | Type | Range | Description |
|----------|-------|------|-------|-------------|
| **Price** | `open` | float | > 0 | Bar open price |
| | `high` | float | > 0 | Bar high price |
| | `low` | float | > 0 | Bar low price |
| | `close` | float | > 0 | Bar close price |
| **Volume** | `volume` | int | >= 0 | Total volume |
| | `delta` | int | any | buy_vol - sell_vol |
| | `buy_vol` | int | >= 0 | Volume at ask |
| | `sell_vol` | int | >= 0 | Volume at bid |
| **External SMC** | `ext_bos` | bool | T/F | External BOS detected |
| | `ext_choch` | bool | T/F | External CHoCH detected |
| | `ext_choch_down` | bool | T/F | CHoCH from down |
| | `ext_choch_up` | bool | T/F | CHoCH from up |
| **Internal SMC** | `int_bos` | bool | T/F | Internal BOS |
| | `int_choch` | bool | T/F | Internal CHoCH |
| | `sweep_prev_high` | bool | T/F | Swept previous high |
| | `sweep_prev_low` | bool | T/F | Swept previous low |
| **Direction** | `ext_dir` | int | -1,0,1 | External direction |
| | `int_dir` | int | -1,0,1 | Internal direction |
| **FVG** | `fvg_up` | bool | T/F | Bullish FVG exists |
| | `fvg_down` | bool | T/F | Bearish FVG exists |
| | `fvg_retest` | bool | T/F | FVG was retested |
| **MGann** | `mgann_leg_index` | int | 1-10 | Current leg index |
| | `wave_strength` | int | 0-100 | Wave strength score |
| | `pb_wave_strength_ok` | bool | T/F | PB strength confirmed |

---

## 4. Context Window Layout

### 4.1 Window Structure

```mermaid
flowchart TB
    subgraph Window["Context Window: 30-50 Bars"]
        direction LR

        subgraph Historical["Historical Bars (29-49)"]
            B1[Bar -49]
            B2[Bar -48]
            B3[...]
            B4[Bar -2]
            B5[Bar -1]
        end

        subgraph Current["Current Bar (1)"]
            B6[Bar 0<br/>Current]
        end

        B1 --> B2 --> B3 --> B4 --> B5 --> B6
    end

    Window --> Features[Flatten to Feature Vector]
    Features --> Model[ML Model Input]
```

### 4.2 Feature Vector Construction

```mermaid
flowchart TD
    subgraph Construction["Feature Vector Construction"]
        direction TB

        INPUT[Context Window<br/>30-50 bars × 25 features]

        FLATTEN[Flatten: Sequential Features]

        CURRENT[Current Bar Features<br/>25 features]

        META[Meta Features<br/>session, time, etc.]

        CONCAT[Concatenate All]

        OUTPUT[Final Feature Vector<br/>~800-1300 dimensions]
    end

    INPUT --> FLATTEN --> CONCAT
    CURRENT --> CONCAT
    META --> CONCAT
    CONCAT --> OUTPUT
```

---

## 5. Target/Label Schema

### 5.1 Label Format

```mermaid
graph LR
    subgraph Target["Target Schema"]
        L1[label: str<br/>'long'/'short'/'skip']
        L2[confidence: float<br/>0.0 - 1.0]
        L3[conditions_met: list]
        L4[conditions_failed: list]
    end

    Target --> Training[ML Training]
```

### 5.2 Label Distribution Target

```mermaid
pie title Target Label Distribution
    "LONG" : 35
    "SHORT" : 35
    "SKIP" : 30
```

---

## 6. Data Flow

### 6.1 Context Generation Pipeline

```mermaid
sequenceDiagram
    participant RAW as Raw JSONL
    participant PROC as Processor
    participant CTX as Context Builder
    participant DS as Dataset

    RAW->>PROC: Load bars
    PROC->>PROC: Apply 14 modules
    PROC->>CTX: BarState stream

    loop For each signal event
        CTX->>CTX: Extract 30-50 bar window
        CTX->>CTX: Flatten features
        CTX->>CTX: Apply Label Rule (A)
        CTX->>DS: Add to dataset
    end

    DS->>DS: Split train/val (70/30)
    DS-->>DS: Save train.jsonl, val.jsonl
```

---

## 7. JSON Schema Example

### 7.1 Single Training Sample

```json
{
    "context_bars": [
        {
            "bar_index": 950,
            "open": 2050.0,
            "high": 2052.5,
            "low": 2049.0,
            "close": 2051.5,
            "volume": 1000,
            "delta": 150,
            "ext_dir": 1,
            "int_dir": 1,
            "ext_bos": false,
            "ext_choch": false,
            "ext_choch_down": false,
            "fvg_up": false,
            "fvg_down": false,
            "fvg_retest": false,
            "mgann_leg_index": 1,
            "wave_strength": 65,
            "pb_wave_strength_ok": false
        }
        // ... 29-49 more bars
    ],
    "current_bar": {
        "bar_index": 1000,
        "open": 2055.0,
        "high": 2058.0,
        "low": 2054.0,
        "close": 2057.5,
        "volume": 1500,
        "delta": 400,
        "ext_dir": 1,
        "ext_choch_down": true,
        "fvg_up": true,
        "fvg_retest": true,
        "mgann_leg_index": 2,
        "pb_wave_strength_ok": true
    },
    "label": "long",
    "label_confidence": 1.0,
    "conditions_met": [
        "ext_choch_down",
        "fvg_up",
        "fvg_retest",
        "ext_dir_up",
        "mgann_leg_early",
        "pb_wave_ok"
    ],
    "conditions_failed": []
}
```

---

## 8. Normalization

### 8.1 Feature Normalization

```mermaid
flowchart LR
    subgraph Normalization["Normalization Methods"]
        N1["Price: % change from first bar"]
        N2["Volume: z-score"]
        N3["Delta: z-score"]
        N4["Scores: already 0-1"]
        N5["Flags: binary 0/1"]
    end

    Raw[Raw Features] --> N1 & N2 & N3 & N4 & N5 --> Normalized[Normalized Vector]
```

---

## 9. Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | 2025-11-24 | CTX V3 Schema with Mermaid diagrams |

---

**Status:** Production Ready
**Related:** [ARCHITECTURE_V3.md](../ARCHITECTURE_V3.md), [LABEL_RULES.md](LABEL_RULES.md)
