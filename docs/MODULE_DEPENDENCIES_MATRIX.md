# Dependency Matrix — v3

All legacy module dependencies are replaced by a simple linear chain:

| Upstream | Downstream | Contract |
|----------|------------|----------|
| Layer 1 Exporter | Layer 2 Labeler | `event.jsonl` with canonical fields (`ext_dir`, `ext_choch_*`, `fvg_*`, `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`, `atr`, `session`). |
| Layer 2 Labeler | Layer 3 Train Loop | `train.jsonl` / `val.jsonl` with `{id, features{...}, label}`. |
| Layer 3 Train Loop | Layer 4 Inference | `model_final.zip` + `metrics.json`. |
| Layer 4 Inference | NinjaTrader Autobot | `EnterLong/EnterShort/Skip` actions with scores and timestamps. |

No other dependencies or alternate flows are supported in v3.
