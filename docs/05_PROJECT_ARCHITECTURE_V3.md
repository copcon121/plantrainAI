# Project Architecture v3 (Unified)

Single-flow blueprint for the Auto-Trading stack combining SMC structure detection, MGann swing logic, and ML classification.

## Four-layer stack
1) **Layer 1 — Exporter:** NinjaTrader indicator emits structured events (`event.jsonl`) with BOS/CHOCH/FVG/MGann fields. No labeling, no scoring.
2) **Layer 2 — Label Rules (A):** Deterministic rule set (Case A+B merged) assigns `long/short/skip` using exporter fields such as `ext_choch_*`, `fvg_*`, `mgann_leg_index`, `pb_wave_strength_ok`.
3) **Layer 3 — Train Loop:** LoRA on Qwen; consumes labeled JSONL, applies oversample + class-weighted focal loss, outputs `model_final.zip`.
4) **Layer 4 — Deploy/Infer:** FastAPI server wraps the model; NinjaTrader sends payloads and receives `EnterLong/EnterShort/Skip`.

## End-to-end data flow
```
NinjaTrader chart
   ↓ (indicator flags)
Layer 1 Exporter → event.jsonl
   ↓
Layer 2 Labeler → train.jsonl / val.jsonl
   ↓
Layer 3 Train Loop → model_final.zip
   ↓
Layer 4 Inference API → Autobot actions
```

## Core principles
- **One plan only:** No alternate labeling strategies or legacy module trees. Everything routes through the four layers above.
- **Field discipline:** Use canonical names: `ext_dir`, `int_dir`, `ext_choch_up/down`, `fvg_up/down`, `fvg_retest`, `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`.
- **Legibility:** JSONL everywhere; UTF-8; booleans are true/false, not 0/1.
- **Small, clean dataset:** Target 1k–1.5k events; enforce `mgann_leg_index <= 2` to avoid duplicate patterns.

## Deliverables per layer
- **L1:** Updated exporter indicator + `01_LAYER1_EXPORTER.md` + validation checklist.
- **L2:** Unified rule doc `02_LAYER2_LABEL_RULES.md` + labeler script (deterministic).
- **L3:** Training script + `train.jsonl`/`val.jsonl` + `metrics.json` + `model_final.zip`.
- **L4:** FastAPI service + deployment notes + monitoring hooks.

## Versioning and governance
- Architecture version: `v3`. Any change to rules or fields increments minor version and updates all docs simultaneously.
- Deprecated v1/v2 documents must point to this file; do not maintain parallel flows.
- Branch policy: main holds the v3 docs and code; experiments live in feature branches only if they preserve field names.
