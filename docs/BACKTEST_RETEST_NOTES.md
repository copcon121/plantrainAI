# Retest Notes — v3

Key reminders for FVG retest handling in the unified flow:
- Labels are only emitted when `fvg_retest = true`; no early labels.
- Eligible legs: `mgann_leg_index <= 2` and `pb_wave_strength_ok = true`.
- Prefer `mgann_leg_first_fvg = true`, but do not split rules; use as a soft feature for ML.
- If export shows `fvg_retest` without a matching `fvg_up/down`, drop the event as invalid input.
- During replay/backtest, treat timeouts or missing fields as `Skip` to avoid accidental entries.
