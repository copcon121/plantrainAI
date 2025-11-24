# LAYER 4: DEPLOYMENT & INFERENCE

**Version:** 1.0.0
**Date:** November 24, 2025
**Layer:** 4 (Deployment)
**Status:** Specification Ready

---

## 1. Overview

Layer 4 handles model deployment and real-time inference:
- REST API serving the trained model
- Real-time predictions for NinjaTrader
- Trade execution logic
- Performance monitoring

---

## 2. Inference Server Architecture

### 2.1 System Overview

```mermaid
flowchart TB
    subgraph NinjaTrader["NinjaTrader (Layer 1)"]
        NT1[Autobot Strategy]
        NT2[Real-time Bar Data]
        NT3[Order Execution]
    end

    subgraph InferenceServer["Inference Server (Layer 4)"]
        API[REST API<br/>/predict endpoint]
        PREPROC[Preprocessing<br/>Feature Engineering]
        MODEL[ML Model<br/>Qwen + LoRA]
        POSTPROC[Post-processing<br/>Confidence Filtering]
    end

    subgraph Outputs["Response"]
        OUT1[label: long/short/skip]
        OUT2[confidence: 0.0-1.0]
        OUT3[probabilities: array]
    end

    NT2 --> NT1
    NT1 -->|POST /predict| API
    API --> PREPROC --> MODEL --> POSTPROC
    POSTPROC --> OUT1 & OUT2 & OUT3
    OUT1 & OUT2 & OUT3 -->|JSON Response| NT1
    NT1 --> NT3

    style InferenceServer fill:#fce4ec
    style MODEL fill:#e8f5e9
```

### 2.2 Detailed API Flow

```mermaid
sequenceDiagram
    participant NT as NinjaTrader Autobot
    participant API as Inference API
    participant PRE as Preprocessor
    participant ML as ML Model
    participant POST as Post-processor

    rect rgb(252, 228, 236)
        Note over NT,POST: Real-time Prediction Flow

        NT->>API: POST /predict
        Note right of NT: {context, bar, features}

        API->>PRE: Validate & Transform
        PRE->>PRE: Build CTX window
        PRE->>PRE: Normalize features
        PRE->>PRE: Tokenize input

        PRE->>ML: Forward pass
        ML->>ML: Generate logits
        ML->>ML: Apply softmax

        ML->>POST: Raw predictions
        POST->>POST: Apply temperature scaling
        POST->>POST: Confidence threshold check
        POST->>POST: Format response

        POST-->>API: Processed result
        API-->>NT: JSON Response
        Note left of API: {label, confidence, probabilities}

        NT->>NT: Execute trade logic
        alt label == "long"
            NT->>NT: EnterLong()
        else label == "short"
            NT->>NT: EnterShort()
        else label == "skip"
            NT->>NT: No action
        end
    end
```

---

## 3. API Specification

### 3.1 Request/Response Flow

```mermaid
flowchart LR
    subgraph Request["POST /predict Request"]
        REQ1[context_bars: array]
        REQ2[current_bar: object]
        REQ3[features: object]
        REQ4[metadata: object]
    end

    subgraph Processing["Server Processing"]
        P1[Validate JSON]
        P2[Build CTX window]
        P3[Model inference]
        P4[Format response]
    end

    subgraph Response["Response JSON"]
        RES1[label: string]
        RES2[confidence: float]
        RES3[probabilities: object]
        RES4[processing_time_ms: int]
    end

    Request --> P1 --> P2 --> P3 --> P4 --> Response
```

### 3.2 Request Schema

```mermaid
classDiagram
    class PredictRequest {
        +array context_bars
        +object current_bar
        +object features
        +object metadata
    }

    class ContextBar {
        +datetime time_utc
        +float o, h, l, c
        +float volume, delta
        +int ext_dir, int_dir
        +bool has_fvg_bull, has_fvg_bear
        +bool has_ob_bull, has_ob_bear
        +float atr
    }

    class Features {
        +float fvg_quality_score
        +str fvg_retest_type
        +float fvg_penetration_ratio
        +int mgann_leg_index
        +bool pb_wave_strength_ok
        +float confluence_score
    }

    class Metadata {
        +str symbol
        +str timeframe
        +str session
        +datetime request_time
    }

    PredictRequest --> ContextBar : context_bars[30-50]
    PredictRequest --> Features
    PredictRequest --> Metadata
```

### 3.3 Response Schema

```mermaid
classDiagram
    class PredictResponse {
        +str label
        +float confidence
        +object probabilities
        +int processing_time_ms
        +str model_version
    }

    class Probabilities {
        +float long
        +float short
        +float skip
    }

    PredictResponse --> Probabilities
```

---

## 4. Trade Execution Logic

### 4.1 NinjaTrader Autobot Flow

```mermaid
flowchart TD
    START[OnBarUpdate] --> CHECK{New Bar?}
    CHECK -->|No| END[Return]
    CHECK -->|Yes| BUILD[Build Request JSON]

    BUILD --> SEND[POST /predict]
    SEND --> RECEIVE[Parse Response]

    RECEIVE --> VALIDATE{Valid Response?}
    VALIDATE -->|No| LOG_ERR[Log Error]
    LOG_ERR --> END

    VALIDATE -->|Yes| CONF_CHECK{Confidence >= Threshold?}
    CONF_CHECK -->|No| SKIP[Skip Trade]
    SKIP --> END

    CONF_CHECK -->|Yes| LABEL{Label?}

    LABEL -->|long| LONG_CHECK{Position Check}
    LABEL -->|short| SHORT_CHECK{Position Check}
    LABEL -->|skip| SKIP

    LONG_CHECK -->|No position| ENTER_LONG[EnterLong]
    LONG_CHECK -->|Already long| END
    LONG_CHECK -->|Short position| CLOSE_SHORT[Close Short]
    CLOSE_SHORT --> ENTER_LONG

    SHORT_CHECK -->|No position| ENTER_SHORT[EnterShort]
    SHORT_CHECK -->|Already short| END
    SHORT_CHECK -->|Long position| CLOSE_LONG[Close Long]
    CLOSE_LONG --> ENTER_SHORT

    ENTER_LONG --> SET_SL_TP[Set SL/TP]
    ENTER_SHORT --> SET_SL_TP
    SET_SL_TP --> END

    style ENTER_LONG fill:#c8e6c9
    style ENTER_SHORT fill:#ffcdd2
    style SKIP fill:#eeeeee
```

### 4.2 Confidence Threshold Logic

```mermaid
flowchart LR
    subgraph Thresholds["Confidence Thresholds"]
        T1["HIGH: >= 0.70<br/>Full size entry"]
        T2["MEDIUM: 0.55-0.70<br/>Reduced size"]
        T3["LOW: < 0.55<br/>Skip trade"]
    end

    PRED[Model Prediction] --> CONF{Confidence Level}
    CONF -->|>= 0.70| T1 --> FULL[100% Position Size]
    CONF -->|0.55-0.70| T2 --> HALF[50% Position Size]
    CONF -->|< 0.55| T3 --> NONE[No Entry]

    style FULL fill:#c8e6c9
    style HALF fill:#fff9c4
    style NONE fill:#eeeeee
```

---

## 5. Server Implementation

### 5.1 Component Architecture

```mermaid
flowchart TB
    subgraph Server["FastAPI Server"]
        MAIN[main.py<br/>App Entry]
        ROUTES[routes.py<br/>API Endpoints]
        MODELS[models.py<br/>Pydantic Schemas]
    end

    subgraph Core["Core Components"]
        LOADER[model_loader.py<br/>Load safetensors]
        INFERENCE[inference.py<br/>Run predictions]
        PREPROCESS[preprocess.py<br/>Feature engineering]
    end

    subgraph Utils["Utilities"]
        CONFIG[config.py<br/>Settings]
        LOGGER[logger.py<br/>Logging]
        METRICS[metrics.py<br/>Performance]
    end

    MAIN --> ROUTES
    ROUTES --> MODELS
    ROUTES --> INFERENCE
    INFERENCE --> LOADER
    INFERENCE --> PREPROCESS
    MAIN --> CONFIG & LOGGER & METRICS

    style Server fill:#fce4ec
    style Core fill:#e8f5e9
```

### 5.2 Request Processing Pipeline

```mermaid
flowchart TD
    subgraph Pipeline["Request Processing Pipeline"]
        P1[Receive JSON]
        P2[Validate Schema]
        P3[Extract Context Bars]
        P4[Build Feature Vector]
        P5[Tokenize Input]
        P6[Model Forward Pass]
        P7[Post-process Output]
        P8[Return Response]

        P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8
    end

    subgraph Timing["Timing Targets"]
        T1["Validation: < 5ms"]
        T2["Preprocessing: < 20ms"]
        T3["Inference: < 50ms"]
        T4["Total: < 100ms"]
    end

    P2 -.-> T1
    P3 & P4 & P5 -.-> T2
    P6 -.-> T3
    P8 -.-> T4
```

---

## 6. Error Handling

### 6.1 Error Response Flow

```mermaid
flowchart TD
    REQ[Incoming Request] --> VAL{Validation}

    VAL -->|Invalid JSON| ERR1[400: Bad Request]
    VAL -->|Valid| SCHEMA{Schema Check}

    SCHEMA -->|Missing fields| ERR2[422: Validation Error]
    SCHEMA -->|Valid| PROCESS{Processing}

    PROCESS -->|Model error| ERR3[500: Internal Error]
    PROCESS -->|Timeout| ERR4[504: Gateway Timeout]
    PROCESS -->|Success| OK[200: Success]

    subgraph ErrorResponses["Error Response Format"]
        E1["{ error: string,<br/>  code: int,<br/>  details: object }"]
    end

    ERR1 & ERR2 & ERR3 & ERR4 --> ErrorResponses

    style ERR1 fill:#ffcdd2
    style ERR2 fill:#ffcdd2
    style ERR3 fill:#ffcdd2
    style ERR4 fill:#ffcdd2
    style OK fill:#c8e6c9
```

### 6.2 Retry Logic (Client Side)

```mermaid
sequenceDiagram
    participant NT as NinjaTrader
    participant API as Inference API

    NT->>API: POST /predict (attempt 1)
    API--xNT: Timeout/Error

    Note over NT: Wait 100ms

    NT->>API: POST /predict (attempt 2)
    API--xNT: Timeout/Error

    Note over NT: Wait 200ms

    NT->>API: POST /predict (attempt 3)
    API-->>NT: Success

    Note over NT: Max 3 retries<br/>Exponential backoff
```

---

## 7. Monitoring & Metrics

### 7.1 Metrics Dashboard

```mermaid
flowchart TB
    subgraph Metrics["Key Metrics"]
        M1[Request Count]
        M2[Latency P50/P95/P99]
        M3[Error Rate]
        M4[Prediction Distribution]
        M5[Confidence Distribution]
    end

    subgraph Alerts["Alert Thresholds"]
        A1["Latency P95 > 100ms"]
        A2["Error Rate > 1%"]
        A3["Skip Rate > 80%"]
    end

    M1 & M2 --> A1
    M3 --> A2
    M4 --> A3

    style A1 fill:#fff9c4
    style A2 fill:#ffcdd2
    style A3 fill:#fff9c4
```

### 7.2 Logging Structure

```mermaid
flowchart LR
    subgraph LogLevels["Log Levels"]
        L1[DEBUG: Full request/response]
        L2[INFO: Prediction summary]
        L3[WARN: Slow requests]
        L4[ERROR: Failures]
    end

    subgraph LogFields["Log Fields"]
        F1[timestamp]
        F2[request_id]
        F3[label]
        F4[confidence]
        F5[latency_ms]
        F6[error_type]
    end

    LogLevels --> LogFields --> OUTPUT[JSON Log Output]
```

---

## 8. Deployment Configuration

### 8.1 Production Setup

```mermaid
flowchart TB
    subgraph Deployment["Production Deployment"]
        LB[Load Balancer]

        subgraph Instances["API Instances"]
            I1[Instance 1<br/>GPU]
            I2[Instance 2<br/>GPU]
        end

        MODEL_STORE[(Model Store<br/>safetensors)]
        CACHE[(Redis Cache<br/>Optional)]
    end

    CLIENT[NinjaTrader] --> LB
    LB --> I1 & I2
    I1 & I2 --> MODEL_STORE
    I1 & I2 -.-> CACHE

    style LB fill:#fff9c4
    style I1 fill:#e8f5e9
    style I2 fill:#e8f5e9
```

### 8.2 Environment Configuration

```mermaid
flowchart LR
    subgraph EnvVars["Environment Variables"]
        E1[MODEL_PATH]
        E2[PORT]
        E3[LOG_LEVEL]
        E4[CONFIDENCE_THRESHOLD]
        E5[MAX_BATCH_SIZE]
        E6[TIMEOUT_MS]
    end

    subgraph Defaults["Default Values"]
        D1["./models/best_model.safetensors"]
        D2["8000"]
        D3["INFO"]
        D4["0.55"]
        D5["1"]
        D6["100"]
    end

    E1 --> D1
    E2 --> D2
    E3 --> D3
    E4 --> D4
    E5 --> D5
    E6 --> D6
```

---

## 9. Code Structure

```python
# api/server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch

app = FastAPI(title="SMC ML Inference API")

class PredictRequest(BaseModel):
    context_bars: list[dict]
    current_bar: dict
    features: dict
    metadata: dict | None = None

class PredictResponse(BaseModel):
    label: str
    confidence: float
    probabilities: dict
    processing_time_ms: int

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Run inference on trading signal"""
    start = time.time()

    # Preprocess
    features = preprocess(request)

    # Inference
    with torch.no_grad():
        logits = model(features)
        probs = torch.softmax(logits, dim=-1)

    # Post-process
    label_idx = probs.argmax().item()
    label = ["long", "short", "skip"][label_idx]
    confidence = probs[label_idx].item()

    return PredictResponse(
        label=label,
        confidence=confidence,
        probabilities={
            "long": probs[0].item(),
            "short": probs[1].item(),
            "skip": probs[2].item(),
        },
        processing_time_ms=int((time.time() - start) * 1000)
    )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": model is not None}
```

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-24 | Initial Deployment & Inference specification |

---

**Status:** Specification Ready
**Next Steps:** Implement api/server.py, api/predict.py
