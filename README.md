# Auto-Trading SMC + MGannSwing + ML (Architecture v3)

Single unified flow: NinjaTrader exporter → labeling → LoRA/Qwen training → FastAPI inference. All legacy multi-module plans are retired.

## System overview
- **Layer 1 — Exporter:** NinjaTrader indicator emits `event.jsonl` with structure/FVG/MGann fields. See `docs/LAYER1_EXPORTER.md`.
- **Layer 2 — Label Rules (A):** Deterministic rules (Case A+B merged) assign `long/short/skip`. See `docs/LAYER2_Label_Rules_v1.md`.
- **Layer 3 — Train Loop:** LoRA on Qwen with oversample + class-weighted focal loss. See `docs/LAYER3_TRAIN_LOOP.md`.
- **Layer 4 — Deploy/Infer:** FastAPI endpoint returning `EnterLong/EnterShort/Skip`. See `docs/LAYER4_DEPLOY_INFER.md`.
- **Unified architecture:** `docs/Project_Architecture_v3.md`.

## Folder map (docs-first)
```
README.md                       (this overview)
ARCHITECTURE.md                 (stack details)
PROJECT_MASTER_PLAN.md          (plan + milestones)
PHASE1_INDICATOR_EXPORT_SPEC.md (export contract, Layer 1)
docs/
  Project_Architecture_v3.md
  LAYER1_EXPORTER.md
  LAYER2_Label_Rules_v1.md
  LAYER3_TRAIN_LOOP.md
  LAYER4_DEPLOY_INFER.md
  SMC_Strategy_Long_v1.md
  SMC_Strategy_Short_v1.md
  CTX_V3_Schema.md
  ... legacy module files now point to the v3 docs above
```

## Quick start
1) Implement/verify exporter fields (`ext_dir`, `fvg_up/down`, `mgann_leg_index`, `pb_wave_strength_ok`, etc.) and write `event.jsonl`.
2) Run the labeling script using the Layer 2 rules to produce `train.jsonl` and `val.jsonl`.
3) Train with the Layer 3 loop; expect `model_final.zip` + `metrics.json`.
4) Deploy the FastAPI service from Layer 4; wire NinjaTrader to `POST /predict` and honor `Skip` on timeout or validation failure.

## Principles
- One plan only; no alternate rule trees.
- Canonical field names across all layers.
- Keep dataset small, clean (1k–1.5k events) by limiting MGann legs to 1–2 and requiring `pb_wave_strength_ok=true`.
