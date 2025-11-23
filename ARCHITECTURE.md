# Architecture v3 — Auto-Trading Stack

Unified four-layer architecture for SMC + MGannSwing + ML. All logic, naming, and flow must follow this document.

## Layer summary
- **Layer 1 — Exporter:** NinjaTrader indicator emits structured events to `event.jsonl` using canonical fields (`ext_dir`, `fvg_up/down`, `fvg_retest`, `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, etc.). No labels or ML decisions.
- **Layer 2 — Label Rules (A):** Deterministic rule set (Case A+B merged) converts events to `long/short/skip`. Uses only Layer 1 fields; no heuristics beyond the canonical gates.
- **Layer 3 — Train Loop:** LoRA on Qwen, class-weighted focal loss, oversampling for balance. Consumes Layer 2 JSONL, outputs `model_final.zip`.
- **Layer 4 — Deploy/Infer:** FastAPI server mapping predictions to `EnterLong/EnterShort/Skip` with strict timeout handling.

## Data flow
```
NinjaTrader (Indicator)
   ↓ event.jsonl (Layer 1)
Labeler (Layer 2) → train.jsonl / val.jsonl
   ↓
LoRA Trainer (Layer 3) → model_final.zip + metrics.json
   ↓
FastAPI Inference (Layer 4) → Autobot actions in NinjaTrader
```

## Canonical field glossary (Layer 1 → Layer 2/3/4)
| Field | Description |
|-------|-------------|
| `ext_dir` | External structure direction (1/-1/0). |
| `int_dir` | Internal structure direction (1/-1/0). |
| `ext_choch_up` / `ext_choch_down` | External CHoCH pulses after sweep/reclaim. |
| `ext_bos` / `int_bos` | BOS flags for context. |
| `int_choch` | Internal CHoCH pulse. |
| `sweep_prev_high` / `sweep_prev_low` | Liquidity sweep markers feeding reclaim logic. |
| `fvg_up` / `fvg_down` | Directional FVG creation. |
| `fvg_retest` | True when price retests the active FVG. |
| `mgann_leg_index` | 1 = leg after CHoCH/BOS, 2 = continuation leg, >2 skipped. |
| `mgann_leg_first_fvg` | True if first FVG inside the leg. |
| `pb_wave_strength_ok` | Pullback wave health gate (delta/volume/depth OK). |
| `wave_strength` | Numeric strength to support the boolean gate. |
| `atr` | ATR for normalization. |
| `session` | Session tag (Asia/London/NY/Other). |

All downstream components must ignore non-canonical fields to prevent divergence.

## Label contract (Layer 2)
- Long rule: `ext_choch_down=true`, `fvg_up=true`, `fvg_retest=true`, `ext_dir=1`, `mgann_leg_index<=2`, `pb_wave_strength_ok=true` → label `long`.
- Short rule: `ext_choch_up=true`, `fvg_down=true`, `fvg_retest=true`, `ext_dir=-1`, `mgann_leg_index<=2`, `pb_wave_strength_ok=true` → label `short`.
- Any failure → label `skip`. Prefer, but do not require, `mgann_leg_first_fvg=true`.
- Dataset size target: 1k–1.5k events to maintain clean balance.

## Training contract (Layer 3)
- Inputs: `train.jsonl`, `val.jsonl` with `{id, features{...}, label}`.
- Loss: class-weighted focal loss (gamma start 1.5).
- Oversample minority classes to keep class share within 30–40%.
- Outputs: `metrics.json` and `model_final.zip` (LoRA adapters).

## Inference contract (Layer 4)
- Endpoint: `POST /predict` (FastAPI).
- Request: `{event_id, symbol, timeframe, timestamp_utc, features{...}}` using the same feature keys as training.
- Response: `{event_id, action: EnterLong|EnterShort|Skip, score, timestamp_utc}`.
- Timeout: >800ms → return `Skip` with reason; NinjaTrader must not retry same `event_id`.

## Governance
- Architecture version: `v3`. Any rule/field change must be reflected across `README.md`, this file, and all `/docs/0x_*.md`.
- Legacy module specs remain only as pointers to v3; they cannot define alternate flows.
