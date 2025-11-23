# NinjaTrader Export Checklist (v3)

**Version:** 3.0 (Layer Architecture V3)
**Last Updated:** November 24, 2025

Use this checklist before shipping `event.jsonl` from Layer 1.

## Required Field Checklist

- [ ] `event.jsonl` uses UTF-8; one JSON object per line.
- [ ] Required fields present: `event_id`, `symbol`, `timeframe`, `timestamp_utc`, `ext_dir`, `int_dir`, `ext_choch_up/down`, `ext_bos`, `int_bos`, `int_choch`, `sweep_prev_high/low`, `fvg_up/down`, `fvg_retest`, `fvg_gap_high/low`, `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`, `atr`, `session`.
- [ ] Booleans are `true/false`, not `0/1`.
- [ ] `mgann_leg_index` resets to 1 after each CHoCH/BOS; never negative.
- [ ] If `fvg_retest=true` then an active `fvg_up/down` exists and gaps are populated.
- [ ] `ext_dir` and `int_dir` are limited to `{1,-1,0}`.
- [ ] Timestamps are UTC; local conversion verified.
- [ ] Sample file validated against schema in `PHASE1_INDICATOR_EXPORT_SPEC.md`.

## Canonical reference
`docs/LAYER1_EXPORTER.md`

---

## Label Rule (A) Required Fields

These fields are **CRITICAL** for the Label Rule (A) labeling system:

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `ext_choch_down` | bool | External CHoCH from DOWN (reversal signal for LONG) | Label Rule (A) |
| `ext_choch_up` | bool | External CHoCH from UP (reversal signal for SHORT) | Label Rule (A) |
| `ext_dir` | int | External trend direction: 1=UP, -1=DOWN, 0=neutral | Label Rule (A) |
| `fvg_up` | bool | Bullish FVG exists | Label Rule (A) |
| `fvg_down` | bool | Bearish FVG exists | Label Rule (A) |
| `fvg_retest` | bool | FVG has been retested | Label Rule (A) |

## MGann Swing Fields (V3)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `mgann_leg_index` | int | Current leg index (1, 2, 3, ...) | Label Rule (A) |
| `mgann_leg_first_fvg` | dict/null | First FVG in current leg sequence | Case A/B Entry |
| `mgann_wave_strength` | int | Wave strength score 0-100 | Module #14 |

## Wave Strength Fields (V3)

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `pb_wave_strength_ok` | bool | Pullback wave strength confirmed | Label Rule (A) |
| `wave_strength` | float | Current wave strength (0-1) | Quality filter |

## FVG Retest Fields

| Field | Type | Description | Required For |
|-------|------|-------------|--------------|
| `fvg_retest` | bool | Valid FVG retest detected | Label Rule (A) |
| `fvg_retest_type` | string | "no_touch"/"edge"/"shallow"/"deep"/"break" | Quality |
| `fvg_penetration_ratio` | float | 0 = edge, 0.5 = mid, 1.0+ = through | Quality |

---

## Label Rule (A) Example

```python
# LONG conditions (ALL must be True)
conditions = [
    event.ext_choch_down == True,        # External CHoCH down
    event.fvg_up == True,                # Bullish FVG exists
    event.fvg_retest == True,            # FVG has been retested
    event.ext_dir == 1,                  # External direction is UP
    event.mgann_leg_index <= 2,          # MGann leg 1 or 2
    event.pb_wave_strength_ok == True,   # Pullback wave strength confirmed
]
if all(conditions):
    label = "long"
else:
    label = "skip"
```

---

## Minimum Viable Export Example

```json
{
    "event_id": "6E-M1-20251124-12345",
    "symbol": "6E",
    "timeframe": "M1",
    "timestamp_utc": "2025-11-24T10:30:00Z",
    "ext_dir": 1,
    "int_dir": 1,
    "ext_choch_down": true,
    "ext_choch_up": false,
    "fvg_up": true,
    "fvg_down": false,
    "fvg_retest": true,
    "fvg_gap_high": 1.0855,
    "fvg_gap_low": 1.0850,
    "mgann_leg_index": 2,
    "mgann_leg_first_fvg": {"high": 1.0855, "low": 1.0850, "type": "bullish"},
    "pb_wave_strength_ok": true,
    "wave_strength": 0.72,
    "atr": 0.00024,
    "session": "London"
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0 | 2025-11-24 | Unified v3 checklist with Label Rule (A) fields |
| 2.0 | 2025-11-23 | Added MGann, Wave Strength, FVG Retest fields |
| 1.3 | 2025-11-21 | Removed FVG retest pulses from Ninja export |
