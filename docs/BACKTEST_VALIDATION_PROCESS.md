# Backtest & Validation Process — v3

Validation focuses on the single unified flow.

## Pre-train checks
- Run exporter schema validation on a fresh `event.jsonl`.
- Dry-run labeler: verify long/short/skip distribution sits within 30–40% per action.
- Spot-check 20 events to confirm CHoCH → leg → FVG → retest sequence matches the rule set.

## Training validation
- Track `val_macro_f1`, per-class F1, confusion matrix.
- Target: `val_macro_f1 >= 0.60`; long and short F1 ≥ 0.55.
- Save `metrics.json` alongside `model_final.zip`.

## Backtest (post-train)
- Replay predictions on a held-out `event.jsonl` slice.
- Metrics: hit rate per class, PF, average RR if SL/TP policy is applied, and latency per inference.
- Require timeout handling to return `Skip` instead of stale predictions.

## Sign-off checklist
- [ ] Exporter schema pass
- [ ] Label balance verified
- [ ] Training metrics meet targets
- [ ] Backtest replay completed with logs stored
- [ ] Deployment package (`model_final.zip`) hashed and recorded
