# LAYER 3: TRAIN LOOP PIPELINE

**Version:** 1.0.0
**Date:** November 24, 2025
**Layer:** 3 (ML Training)
**Status:** Specification Ready

---

## 1. Overview

Layer 3 handles ML model training using:
- LoRA fine-tuning on Qwen model
- Class-weighted Focal Loss for imbalanced data
- Oversampling for minority classes
- Evaluation metrics: accuracy, macro-F1

---

## 2. Training Pipeline Flow

### 2.1 Complete Pipeline Diagram

```mermaid
flowchart LR
    subgraph Input["Data Input"]
        A[train.jsonl]
        B[val.jsonl]
    end

    subgraph Preprocessing["Preprocessing"]
        C[Load Dataset]
        D[Oversample Classes]
        E[Tokenize Context]
    end

    subgraph Training["Training Loop"]
        F[Class-Weighted<br/>Focal Loss]
        G[LoRA Fine-tune<br/>Qwen Model]
        H[Gradient Update]
    end

    subgraph Evaluation["Evaluation"]
        I[Validation Pass]
        J[Accuracy]
        K[Macro-F1]
    end

    subgraph Output["Output"]
        L[Post-calibration<br/>Optional]
        M[Save Model<br/>model.safetensors]
        N[Generate Summary]
    end

    A --> C
    B --> C
    C --> D --> E --> F --> G --> H
    H --> I --> J & K
    K --> L --> M --> N

    style Training fill:#e8f5e9
    style Evaluation fill:#fff8e1
```

### 2.2 Detailed Training Flow

```mermaid
flowchart TD
    subgraph DataPipeline["Data Pipeline"]
        DP1[Load train.jsonl]
        DP2[Parse CTX Windows]
        DP3[Extract Features]
        DP4[Apply Oversampling]
        DP5[Create DataLoader]

        DP1 --> DP2 --> DP3 --> DP4 --> DP5
    end

    subgraph ModelSetup["Model Setup"]
        MS1[Load Qwen Base Model]
        MS2[Apply LoRA Config]
        MS3[Setup Optimizer]
        MS4[Setup Scheduler]

        MS1 --> MS2 --> MS3 --> MS4
    end

    subgraph TrainLoop["Training Loop"]
        TL1[For each epoch]
        TL2[For each batch]
        TL3[Forward Pass]
        TL4[Compute Focal Loss]
        TL5[Backward Pass]
        TL6[Update Weights]
        TL7[Log Metrics]

        TL1 --> TL2 --> TL3 --> TL4 --> TL5 --> TL6 --> TL7
        TL7 --> TL2
    end

    DP5 --> TL1
    MS4 --> TL1

    TL7 --> EVAL[Validation Eval]
    EVAL --> SAVE[Save Checkpoint]

    style TrainLoop fill:#e8f5e9
```

---

## 3. Class Balancing

### 3.1 Oversampling Strategy

```mermaid
flowchart TD
    subgraph Original["Original Distribution"]
        O1["LONG: 350 (35%)"]
        O2["SHORT: 350 (35%)"]
        O3["SKIP: 300 (30%)"]
    end

    subgraph Oversampled["After Oversampling"]
        N1["LONG: 400 (33.3%)"]
        N2["SHORT: 400 (33.3%)"]
        N3["SKIP: 400 (33.3%)"]
    end

    Original --> OVERSAMPLE[Random Oversampling<br/>Minority Classes]
    OVERSAMPLE --> Oversampled

    style OVERSAMPLE fill:#fff9c4
```

### 3.2 Class Weights Calculation

```mermaid
flowchart LR
    subgraph Weights["Class Weight Calculation"]
        W1["Count per class"]
        W2["Inverse frequency"]
        W3["Normalize weights"]
        W4["Apply to loss"]

        W1 --> W2 --> W3 --> W4
    end

    W4 --> FOCAL[Focal Loss]
```

---

## 4. Loss Function

### 4.1 Focal Loss Formula

```mermaid
flowchart TD
    subgraph FocalLoss["Focal Loss Components"]
        FL1["CE = -log(p_t)"]
        FL2["FL = α_t × (1-p_t)^γ × CE"]

        FL1 --> FL2
    end

    subgraph Parameters["Parameters"]
        P1["α (alpha): Class weight"]
        P2["γ (gamma): Focusing parameter<br/>Default: 2.0"]
        P3["p_t: Predicted probability"]
    end

    Parameters --> FL2

    FL2 --> LOSS[Final Loss]
```

### 4.2 Loss Computation Flow

```mermaid
sequenceDiagram
    participant M as Model
    participant L as Loss Function
    participant O as Optimizer

    M->>M: Forward pass
    M->>L: logits, labels
    L->>L: Compute softmax
    L->>L: Get p_t for true class
    L->>L: Compute focal weight: (1-p_t)^γ
    L->>L: Apply class weight α_t
    L->>L: Compute CE loss
    L-->>M: weighted_focal_loss

    M->>O: loss.backward()
    O->>M: optimizer.step()
```

---

## 5. LoRA Configuration

### 5.1 LoRA Architecture

```mermaid
flowchart TD
    subgraph LoRA["LoRA Fine-tuning"]
        BASE[Qwen Base Model<br/>Frozen Weights]

        subgraph Adapter["LoRA Adapters"]
            A1[Query Adapter]
            A2[Key Adapter]
            A3[Value Adapter]
            A4[Output Adapter]
        end

        BASE --> Adapter
        Adapter --> OUTPUT[Model Output]
    end

    subgraph Config["LoRA Config"]
        C1["rank (r): 8-16"]
        C2["alpha: 16-32"]
        C3["dropout: 0.05"]
        C4["target_modules:<br/>q_proj, k_proj, v_proj, o_proj"]
    end

    Config --> Adapter

    style Adapter fill:#e8f5e9
```

### 5.2 Parameter Efficiency

```mermaid
pie title Trainable Parameters
    "LoRA Adapters (0.1%)" : 1
    "Frozen Base (99.9%)" : 999
```

---

## 6. Evaluation Metrics

### 6.1 Metrics Computation

```mermaid
flowchart LR
    subgraph Metrics["Evaluation Metrics"]
        M1["Accuracy<br/>correct / total"]
        M2["Precision<br/>per class"]
        M3["Recall<br/>per class"]
        M4["F1 Score<br/>per class"]
        M5["Macro-F1<br/>average F1"]
    end

    PREDS[Model Predictions] --> M1 & M2 & M3
    M2 & M3 --> M4 --> M5

    style M5 fill:#c8e6c9
```

### 6.2 Target Metrics

| Metric | Target | Priority |
|--------|--------|----------|
| Accuracy | >= 65% | HIGH |
| Macro-F1 | >= 0.60 | **CRITICAL** |
| LONG Precision | >= 60% | HIGH |
| SHORT Precision | >= 60% | HIGH |
| LONG Recall | >= 55% | MEDIUM |
| SHORT Recall | >= 55% | MEDIUM |

---

## 7. Training Configuration

### 7.1 Hyperparameters

```mermaid
graph TD
    subgraph Hyperparams["Training Hyperparameters"]
        H1["epochs: 10-20"]
        H2["batch_size: 8-16"]
        H3["learning_rate: 1e-4"]
        H4["warmup_steps: 100"]
        H5["weight_decay: 0.01"]
        H6["gradient_accumulation: 4"]
    end

    subgraph LoRAParams["LoRA Parameters"]
        L1["lora_r: 8"]
        L2["lora_alpha: 16"]
        L3["lora_dropout: 0.05"]
    end

    subgraph LossParams["Loss Parameters"]
        LP1["focal_gamma: 2.0"]
        LP2["class_weights: auto"]
    end
```

### 7.2 Training Schedule

```mermaid
gantt
    title Training Schedule
    dateFormat X
    axisFormat %s

    section Warmup
    Learning Rate Warmup :0, 100

    section Training
    Epoch 1-5 (High LR)  :100, 500
    Epoch 6-10 (Decay)   :500, 1000

    section Eval
    Validation Each Epoch :active, 0, 1000
```

---

## 8. Checkpointing

### 8.1 Checkpoint Strategy

```mermaid
flowchart TD
    subgraph Checkpointing["Checkpoint Strategy"]
        CP1[Save after each epoch]
        CP2[Track best macro-F1]
        CP3[Keep top-3 checkpoints]
        CP4[Final model selection]

        CP1 --> CP2 --> CP3 --> CP4
    end

    subgraph Output["Output Files"]
        O1[checkpoint_epoch_1.pt]
        O2[checkpoint_epoch_2.pt]
        O3[...]
        O4[best_model.safetensors]
        O5[training_summary.json]
    end

    CP4 --> O4 & O5
```

---

## 9. Post-Training

### 9.1 Post-Calibration (Optional)

```mermaid
flowchart LR
    subgraph Calibration["Temperature Scaling"]
        CAL1[Validation predictions]
        CAL2[Learn temperature T]
        CAL3[Apply: p' = softmax(logits/T)]
        CAL4[Better probability estimates]

        CAL1 --> CAL2 --> CAL3 --> CAL4
    end
```

### 9.2 Model Export

```mermaid
flowchart TD
    subgraph Export["Model Export"]
        E1[Merge LoRA weights]
        E2[Convert to safetensors]
        E3[Generate config.json]
        E4[Package for inference]

        E1 --> E2 --> E3 --> E4
    end

    E4 --> ZIP[final_model.zip]
```

---

## 10. Code Structure

```python
# ml/train.py
class TrainingPipeline:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.optimizer = None
        self.loss_fn = None

    def load_data(self):
        """Load and preprocess train/val datasets"""
        pass

    def setup_model(self):
        """Initialize Qwen + LoRA"""
        pass

    def train_epoch(self):
        """Single training epoch"""
        pass

    def evaluate(self):
        """Validation evaluation"""
        pass

    def save_checkpoint(self):
        """Save model checkpoint"""
        pass

    def run(self):
        """Full training loop"""
        for epoch in range(self.config.epochs):
            self.train_epoch()
            metrics = self.evaluate()
            self.save_checkpoint(metrics)
```

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-24 | Initial Train Loop specification |

---

**Status:** Specification Ready
**Next Steps:** Implement ml/train.py
