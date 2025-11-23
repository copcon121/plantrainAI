# Auto-Trading SMC + MGannSwing + ML (Architecture v3)

**Version:** 3.0.0 (Layer Architecture V3)
**Status:** Production Ready

Single unified flow: NinjaTrader exporter → labeling → LoRA/Qwen training → FastAPI inference. All legacy multi-module plans are retired.

## System overview
- **Layer 1 — Exporter:** NinjaTrader indicator emits `event.jsonl` with structure/FVG/MGann fields. See `docs/LAYER1_EXPORTER.md`.
- **Layer 2 — Label Rules (A):** Deterministic rules (Case A+B merged) assign `long/short/skip`. See `docs/LAYER2_Label_Rules_v1.md`.
- **Layer 3 — Train Loop:** LoRA on Qwen with oversample + class-weighted focal loss. See `docs/LAYER3_TRAIN_LOOP.md`.
- **Layer 4 — Deploy/Infer:** FastAPI endpoint returning `EnterLong/EnterShort/Skip`. See `docs/LAYER4_DEPLOY_INFER.md`.
- **Unified architecture:** `docs/Project_Architecture_v3.md`.

## Label Rule (A) - Official Version

```python
# LONG Signal Conditions (ALL must be True)
conditions = [
    event.ext_choch_down == True,        # External CHoCH down
    event.fvg_up == True,                # Bullish FVG exists
    event.fvg_retest == True,            # FVG has been retested
    event.ext_dir == 1,                  # External direction is UP
    event.mgann_leg_index <= 2,          # MGann leg 1 or 2 (early entry)
    event.pb_wave_strength_ok == True,   # Pullback wave strength confirmed
]

if all(conditions):
    label = "long"
else:
    label = "skip"
```

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
  NINJA_EXPORT_CHECKLIST.md
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

## New V3 Fields

| Field | Type | Description |
|-------|------|-------------|
| `mgann_leg_index` | int | Current MGann leg (1, 2, 3, ...) |
| `mgann_leg_first_fvg` | dict | First FVG in leg sequence |
| `pb_wave_strength_ok` | bool | Pullback wave strength confirmed |
| `ext_choch_down/up` | bool | External CHoCH direction |
| `fvg_retest` | bool | FVG has been retested |

## Entry Cases

- **Case A:** FVG Leg 1 not filled - Entry at Leg 1 FVG (best RR)
- **Case B:** Leg 1 no FVG or filled - Entry at Leg 2 FVG (fallback)

## VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | 2025-11-24 | Layer Architecture V3, Label Rule (A), MGann V3 fields |
| 2.1.0 | 2025-11-21 | FVG Quality v2.0, Wave Delta module |
| 2.0.0 | 2025-11-20 | 14 module architecture |
| 1.0.0 | 2025-11-15 | Initial 3-layer design |
