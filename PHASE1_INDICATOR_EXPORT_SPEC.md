# Phase 1: Indicator Export Specification (Layer 1)

Contract for the NinjaTrader exporter that feeds the v3 pipeline. Output is `event.jsonl` (UTF-8, one JSON object per line). No labels or scores are produced here.

## Required fields
| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Unique per setup (symbol + timeframe + bar index). |
| `symbol` | string | Instrument code. |
| `timeframe` | string | `"M1"`/`"M5"` etc. |
| `timestamp_utc` | string | ISO8601 bar close time. |
| `ext_dir` | int | External structure direction: `1` up, `-1` down, `0` flat. |
| `int_dir` | int | Internal structure direction. |
| `ext_bos` | bool | External BOS fired. |
| `ext_choch_up` | bool | External CHoCH up break. |
| `ext_choch_down` | bool | External CHoCH down break. |
| `int_bos` | bool | Internal BOS fired. |
| `int_choch` | bool | Internal CHoCH fired. |
| `sweep_prev_high` | bool | Sweep of previous swing high. |
| `sweep_prev_low` | bool | Sweep of previous swing low. |
| `fvg_up` | bool | Bullish FVG created. |
| `fvg_down` | bool | Bearish FVG created. |
| `fvg_retest` | bool | Current bar retests active FVG. |
| `fvg_gap_high` | float | Upper bound of the active FVG. |
| `fvg_gap_low` | float | Lower bound of the active FVG. |
| `ext_dir_confidence` | float | Optional confidence 0-1. |
| `int_dir_confidence` | float | Optional confidence 0-1. |
| `wave_strength` | float | Strength 0-1 for current zigzag wave. |
| `mgann_leg_index` | int | 1 for first leg after CHoCH/BOS, 2 for continuation leg, 3+ ignored by labeling. |
| `mgann_leg_first_fvg` | bool | True if this is the first FVG in the current MGann leg. |
| `pb_wave_strength_ok` | bool | Pullback wave passes health gate. |
| `atr` | float | ATR value for normalization. |
| `session` | string | Session tag (Asia/London/NY/Other). |

## New fields (must be emitted)
- `mgann_leg_index`
- `mgann_leg_first_fvg`
- `pb_wave_strength_ok`

## Leg/FVG behavior
- Reset `mgann_leg_index` to 1 on each confirmed `ext_choch_*` or `ext_bos`.
- First FVG in any leg sets `mgann_leg_first_fvg=true`; subsequent FVGs in same leg set it to false.
- If a pullback is weak (delta/volume/depth), set `pb_wave_strength_ok=false` even if the leg index is eligible.

## JSONL example
```json
{
  "event_id": "ES-M1-20251123-8301",
  "symbol": "ES",
  "timeframe": "M1",
  "timestamp_utc": "2025-11-23T14:30:00Z",
  "ext_dir": -1,
  "int_dir": -1,
  "ext_choch_up": false,
  "ext_choch_down": true,
  "ext_bos": false,
  "int_bos": true,
  "int_choch": false,
  "sweep_prev_high": true,
  "sweep_prev_low": false,
  "fvg_up": true,
  "fvg_down": false,
  "fvg_retest": true,
  "fvg_gap_high": 4580.25,
  "fvg_gap_low": 4579.75,
  "ext_dir_confidence": 0.74,
  "int_dir_confidence": 0.65,
  "wave_strength": 0.70,
  "mgann_leg_index": 2,
  "mgann_leg_first_fvg": true,
  "pb_wave_strength_ok": true,
  "atr": 0.75,
  "session": "NY"
}
```

## Validation checklist
- JSONL well-formed; one object per line.
- Booleans are `true/false`, not `0/1`.
- `mgann_leg_index` resets correctly after CHoCH/BOS.
- If `fvg_retest=true`, then `fvg_up` or `fvg_down` must be true and corresponding `fvg_gap_*` populated.
- `ext_dir` and `int_dir` limited to `{1, -1, 0}`.
- Timestamps are UTC; ensure local → UTC conversion happens before export.
