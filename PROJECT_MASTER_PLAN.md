# Project Master Plan — Auto-Trading v3

## Goals
- Ship a single, unified pipeline (Exporter → Label → Train → Infer) with zero competing rule sets.
- Deliver a balanced dataset (1k–1.5k events) and a deployable `model_final.zip`.
- Keep all documentation synchronized with architecture v3.

## Scope (by layer)
- **Layer 1 (Exporter):** Finalize indicator fields (`ext_dir`, `fvg_*`, `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`, `atr`, `session`) and emit `event.jsonl`. Spec: `docs/01_LAYER1_EXPORTER.md`, `PHASE1_INDICATOR_EXPORT_SPEC.md`.
- **Layer 2 (Label Rules A):** Apply the merged rule set; no alternates. Spec: `docs/02_LAYER2_LABEL_RULES.md`.
- **Layer 3 (Train Loop):** LoRA/Qwen with class-weighted focal loss, oversampling, and metrics in `metrics.json`. Spec: `docs/03_LAYER3_TRAIN_LOOP.md`.
- **Layer 4 (Deploy/Infer):** FastAPI server mapping to `EnterLong/EnterShort/Skip`, strict timeout handling. Spec: `docs/04_LAYER4_DEPLOY_INFER.md`.

## Milestones
1. **Exporter ready**  
   - Fields implemented and validated against `PHASE1_INDICATOR_EXPORT_SPEC.md`.  
   - `event.jsonl` sample produced and schema-checked.
2. **Labeler locked**  
   - Case A+B merged rules applied; dataset balanced report generated.  
   - `train.jsonl` and `val.jsonl` available.
3. **Model trained**  
   - Training run completed with target `val_macro_f1 >= 0.60`.  
   - Artifacts: `metrics.json`, `model_final.zip`.
4. **Inference live**  
   - FastAPI endpoint serving with health checks; NinjaTrader integration tested.  
   - Timeout fallback returns `Skip` and is honored on the chart side.

## Risks & mitigation
- **Imbalanced data (<25% any class):** Use oversample + class-weighted focal loss; revisit labeling thresholds if imbalance persists.
- **Exporter drift:** Enforce schema checks on `event.jsonl`; reject unknown fields.
- **Latency on VPS:** Keep model size <500MB, preload on startup, fall back to CPU-safe settings if GPU unavailable.

## Operating rules
- Version is `v3`; any change to rules/fields must update all docs in this repo.
- No alternate flows or legacy module stacks are allowed in `main`.
- Logs and metrics must be attached to each training or deployment change.
