# PROJECT ARCHITECTURE V3 - System Overview

**Version:** 3.0.0
**Date:** November 24, 2025
**Status:** Production Ready

---

## 1. System Architecture Overview

### 1.1 Complete Data Flow Diagram

```mermaid
flowchart LR
    subgraph Layer1["Layer 1: NinjaTrader"]
        A[NinjaTrader Core<br/>SMC Indicator] --> B[Raw JSON Exporter]
    end

    subgraph Layer2["Layer 2: Python Processor"]
        C[14 Independent Modules] --> D[Label Rules v1<br/>Long/Short/Skip]
    end

    subgraph Layer3["Layer 3: ML Training"]
        E[Dataset Generation] --> F[LoRA Fine-tune<br/>Qwen Model]
    end

    subgraph Layer4["Layer 4: Deployment"]
        G[Inference API] --> H[NinjaTrader Autobot]
    end

    B --> C
    D --> E
    F --> G
    H --> I[Order Execution]

    style Layer1 fill:#e1f5fe
    style Layer2 fill:#fff3e0
    style Layer3 fill:#e8f5e9
    style Layer4 fill:#fce4ec
```

### 1.2 Detailed Layer Architecture

```mermaid
flowchart TB
    subgraph L1["LAYER 1: NinjaTrader C# Indicator"]
        L1A[SMC_Structure_OB_Only_v12]
        L1B[SMCDeepSeekExporter_Enhanced]
        L1C[Volumdelta.cs]
        L1D[MGann Internal Swing]

        L1A --> L1E[FVG Detection]
        L1A --> L1F[OB Detection]
        L1A --> L1G[CHoCH/BOS Detection]
        L1C --> L1H[Volume/Delta Raw]
        L1D --> L1I[Swing Points]

        L1E & L1F & L1G & L1H & L1I --> L1B
        L1B --> L1J[raw_smc_export.jsonl]
    end

    subgraph L2["LAYER 2: Python Data Processor"]
        L2A[fix09_volume_profile]
        L2B[fix11_liquidity_map]
        L2C[fix07_market_condition]
        L2D[fix14_mgann_swing]
        L2E[fix02_fvg_quality]
        L2F[fix12_fvg_retest]
        L2G[fix04_confluence]

        L1J --> L2A
        L2A --> L2B --> L2C --> L2D --> L2E --> L2F --> L2G

        L2G --> L2H[BarState]
        L2G --> L2I[EventState]
    end

    subgraph L3["LAYER 3: ML Pipeline"]
        L3A[Label Rule A<br/>Long/Short/Skip]
        L3B[Dataset Split<br/>70% Train / 30% Val]
        L3C[Feature Engineering]
        L3D[LoRA Fine-tune Qwen]

        L2H & L2I --> L3A
        L3A --> L3B --> L3C --> L3D
        L3D --> L3E[model.safetensors]
    end

    subgraph L4["LAYER 4: Deployment"]
        L4A[Inference Server]
        L4B[REST API /predict]
        L4C[NinjaTrader Autobot]

        L3E --> L4A --> L4B --> L4C
        L4C --> L4D[EnterLong/EnterShort/Skip]
    end

    style L1 fill:#e3f2fd
    style L2 fill:#fff8e1
    style L3 fill:#e8f5e9
    style L4 fill:#fce4ec
```

---

## 2. Module Pipeline Flow

### 2.1 Layer 2 Processing Order

```mermaid
flowchart TD
    subgraph Pipeline["Module Processing Pipeline"]
        M1["#09 Volume Profile<br/>Session POC/VAH/VAL"]
        M2["#11 Liquidity Map<br/>Sweep Detection"]
        M3["#07 Market Condition<br/>ADX/ATR Regime"]
        M4["#10 MTF Alignment<br/>Higher TF Confluence"]
        M5["#01 OB Quality<br/>Order Block Context"]
        M6["#02 FVG Quality<br/>PRIMARY Signal"]
        M7["#03 Structure Context<br/>Expansion/Retracement"]
        M8["#12 FVG Retest<br/>SIGNAL GATE"]
        M9["#14 MGann Swing<br/>Leg Index Tracking"]
        M10["#13 Wave Delta<br/>Leg Accumulation"]
        M11["#05 Stop Placement<br/>SL Optimization"]
        M12["#06 Target Placement<br/>TP Selection"]
        M13["#08 Volume Divergence<br/>Delta Divergence"]
        M14["#04 Confluence<br/>Final Score"]

        M1 --> M2 --> M3 --> M4 --> M5
        M5 --> M6 --> M7 --> M8 --> M9
        M9 --> M10 --> M11 --> M12 --> M13 --> M14
    end

    M14 --> OUT[EventState with<br/>All Scores + Label]

    style M6 fill:#ffcdd2
    style M8 fill:#ffcdd2
    style M9 fill:#ffcdd2
    style M14 fill:#c8e6c9
```

---

## 3. Data Structures

### 3.1 BarState Schema

```mermaid
classDiagram
    class BarState {
        +datetime time_utc
        +float o, h, l, c
        +float volume, delta
        +int ext_dir, int_dir
        +bool is_swing_high, is_swing_low
        +str session
        +float atr
        +bool has_ob_bull, has_ob_bear
        +bool has_fvg_bull, has_fvg_bear
        +bool has_choch
        +float fvg_quality_score
        +float ob_strength_score
        +float market_condition_score
        +int mgann_leg_index
        +bool pb_wave_strength_ok
    }
```

### 3.2 EventState Schema

```mermaid
classDiagram
    class EventState {
        +str signal_type
        +int direction
        +float fvg_quality_score
        +str fvg_value_class
        +str fvg_retest_type
        +float fvg_penetration_ratio
        +bool has_ob_in_leg
        +float entry_price
        +float sl_price
        +float tp1_price, tp2_price
        +str signal
        +int mgann_leg_index
        +dict mgann_leg_first_fvg
        +bool pb_wave_strength_ok
    }

    class LabelOutput {
        +str label
        +float label_confidence
        +str label_reason
        +list conditions_met
        +list conditions_failed
    }

    EventState --> LabelOutput : applies Label Rule A
```

---

## 4. Key Components

### 4.1 Label Rule (A) Decision Flow

```mermaid
flowchart TD
    START[FVG Retest Event] --> CHECK_TYPE{FVG Type?}

    CHECK_TYPE -->|Bullish| LONG_PATH
    CHECK_TYPE -->|Bearish| SHORT_PATH

    subgraph LONG_PATH["LONG Conditions"]
        L1[ext_choch_down == True]
        L2[fvg_up == True]
        L3[fvg_retest == True]
        L4[ext_dir == 1]
        L5[mgann_leg_index <= 2]
        L6[pb_wave_strength_ok == True]
        L1 --> L2 --> L3 --> L4 --> L5 --> L6
    end

    subgraph SHORT_PATH["SHORT Conditions"]
        S1[ext_choch_up == True]
        S2[fvg_down == True]
        S3[fvg_retest == True]
        S4[ext_dir == -1]
        S5[mgann_leg_index <= 2]
        S6[pb_wave_strength_ok == True]
        S1 --> S2 --> S3 --> S4 --> S5 --> S6
    end

    L6 -->|All True| LONG[Label: LONG]
    L6 -->|Any False| SKIP1[Label: SKIP]
    S6 -->|All True| SHORT[Label: SHORT]
    S6 -->|Any False| SKIP2[Label: SKIP]

    style LONG fill:#c8e6c9
    style SHORT fill:#ffcdd2
    style SKIP1 fill:#eeeeee
    style SKIP2 fill:#eeeeee
```

---

## 5. Integration Points

### 5.1 NinjaTrader ↔ Python Integration

```mermaid
sequenceDiagram
    participant NT as NinjaTrader
    participant EXP as Exporter
    participant PY as Python Processor
    participant ML as ML Pipeline
    participant API as Inference API

    rect rgb(225, 245, 254)
        Note over NT,EXP: Layer 1 - Real-time Export
        NT->>EXP: OnBarUpdate()
        EXP->>EXP: Detect FVG/OB/CHoCH
        EXP-->>PY: Write JSONL
    end

    rect rgb(255, 243, 224)
        Note over PY,ML: Layer 2-3 - Offline Processing
        PY->>PY: Process 14 modules
        PY->>ML: Generate train.jsonl
        ML->>ML: LoRA Fine-tune
        ML-->>API: Deploy model
    end

    rect rgb(252, 228, 236)
        Note over NT,API: Layer 4 - Live Trading
        NT->>API: POST /predict
        API-->>NT: {label, confidence}
        NT->>NT: Execute trade
    end
```

---

## 6. File Structure

```
plantrainAI/
├── ARCHITECTURE_V3.md              # Master architecture document
├── README.md                       # Project overview
│
├── indicators/                     # Layer 1: NinjaTrader C#
│   ├── SMCDeepSeekExporter_Enhanced.cs
│   ├── SMC_Structure_OB_Only_v12_FVG_CHOCHFlags_DeepSeek.cs
│   └── Volumdelta.cs
│
├── processor/                      # Layer 2: Python Processor
│   ├── core/
│   │   ├── bar_state.py
│   │   ├── event_state.py
│   │   └── module_base.py
│   ├── modules/                    # 14 Independent Modules
│   │   ├── fix01_ob_quality.py
│   │   ├── fix02_fvg_quality.py
│   │   ├── ...
│   │   └── fix14_mgann_swing.py
│   ├── backtest/
│   └── validation/
│
├── ml/                             # Layer 3: ML Pipeline (future)
│   ├── train.py
│   ├── dataset.py
│   └── models/
│
├── api/                            # Layer 4: Inference (future)
│   ├── server.py
│   └── predict.py
│
└── docs/                           # Documentation
    ├── Project_Architecture_v3.md  # This file
    ├── SMC_Strategy_Long_v1.md
    ├── SMC_Strategy_Short_v1.md
    ├── LAYER2_Label_Rules_v1.md
    ├── CTX_V3_Schema.md
    ├── LAYER3_TRAIN_LOOP.md
    └── LAYER4_DEPLOY_INFER.md
```

---

## 7. Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | 2025-11-24 | Complete Mermaid diagrams, Layer Architecture V3 |
| 2.1.0 | 2025-11-21 | FVG Quality v2.0, Wave Delta module |
| 2.0.0 | 2025-11-20 | 14 module architecture |

---

**Status:** Production Ready
**Next Steps:** Implement Layer 3 (ML Pipeline) and Layer 4 (Inference API)
