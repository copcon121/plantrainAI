# NinjaTrader Export Checklist (v3)

Use this checklist before shipping `event.jsonl` from Layer 1.

- [ ] `event.jsonl` uses UTF-8; one JSON object per line.
- [ ] Required fields present: `event_id`, `symbol`, `timeframe`, `timestamp_utc`, `ext_dir`, `int_dir`, `ext_choch_up/down`, `ext_bos`, `int_bos`, `int_choch`, `sweep_prev_high/low`, `fvg_up/down`, `fvg_retest`, `fvg_gap_high/low`, `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`, `atr`, `session`.
- [ ] Booleans are `true/false`, not `0/1`.
- [ ] `mgann_leg_index` resets to 1 after each CHoCH/BOS; never negative.
- [ ] If `fvg_retest=true` then an active `fvg_up/down` exists and gaps are populated.
- [ ] `ext_dir` and `int_dir` are limited to `{1,-1,0}`.
- [ ] Timestamps are UTC; local conversion verified.
- [ ] Sample file validated against schema in `PHASE1_INDICATOR_EXPORT_SPEC.md`.

Canonical reference: `docs/01_LAYER1_EXPORTER.md`.
