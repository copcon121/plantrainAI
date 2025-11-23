# Project Architecture v3 (Unified)

Single authoritative plan for the Auto-Trading SMC + MGannSwing + ML stack. All components must follow this document; no parallel versions are allowed.

## Pipeline overview
- **Layer 1 — Exporter:** NinjaTrader indicator emits `event.jsonl` with canonical fields (`ext_dir`, `ext_choch_*`, `fvg_*`, `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`, `atr`, `session`).
- **Layer 2 — Label Rules v1:** Deterministic rules (Case A+B merged) produce `long/short/skip` labels from exporter fields.
- **Layer 3 — Train Loop:** LoRA/Qwen classification with oversample + class-weighted focal loss; outputs `model_final.zip`.
- **Layer 4 — Deploy/Infer:** FastAPI server returning `EnterLong/EnterShort/Skip`, with strict timeout-to-skip behavior.

## Data flow (Mermaid)
```mermaid
flowchart LR
    NT[NinjaTrader Indicator\n(Layer 1 Exporter)] -->|event.jsonl| L2[Layer 2 Labeler\nunified rules]
    L2 -->|train.jsonl / val.jsonl| L3[Layer 3 Train Loop\nLoRA/Qwen]
    L3 -->|model_final.zip\nmetrics.json| L4[Layer 4 FastAPI Inference]
    L4 -->|EnterLong / EnterShort / Skip| AB[Autobot Execution\nNinjaTrader]
```

## Roles per layer
- **Exporter:** Detect structure/FVG/MGann legs; gate pullback quality; serialize events. No labeling or scoring.
- **Labeler:** Apply the single rule set: CHoCH → reclaim → MGann leg (≤2) → FVG dir → retest → pullback OK → label.
- **Trainer:** Balance classes (target 1k–1.5k events total), train with class-weighted focal loss, evaluate macro-F1, package artifacts.
- **Inference:** Validate payloads, enforce timeouts, map predictions to actions, log audits.

## Timeline (reference)
- **Week 1:** Finalize exporter fields and validation; produce sample `event.jsonl`.
- **Week 2:** Run labeler, confirm class balance, generate `train/val` splits.
- **Week 3:** Train and evaluate LoRA/Qwen; hit target `val_macro_f1 ≥ 0.60`.
- **Week 4:** Deploy FastAPI on VPS; integrate with NinjaTrader; run smoke backtests.

## Governance
- Architecture version: **v3**. Any change to fields or rules must update this file and all layer docs simultaneously.
- Deprecated materials (legacy modules) are informational only and must point back to the v3 docs.
- Canonical field names are mandatory across all layers to avoid drift.
