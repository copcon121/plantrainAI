# Layer 1 — Exporter (NinjaTrader → event.jsonl)

Canonical spec for the NinjaTrader exporter indicator that feeds the v3 Auto-Trading pipeline. Layer 1 only packages raw/structured facts; zero labeling and zero ML logic happen here.

## Responsibilities
- Capture structure pulses (BOS/CHOCH), liquidity sweeps, fair-value-gap (FVG) creation/retest, and MGann swing context in real time.
- Normalize directions to the shared terminology: `ext_dir`, `int_dir`, `fvg_up`, `fvg_down`, `mgann_leg_index`, `pb_wave_strength_ok`, etc.
- Emit one JSON object per trading event into `event.jsonl`. Bar-level streams can be kept separately but are not part of this contract.

## Field Mapping (exporter indicator → event.jsonl)

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Unique id per setup (bar index + symbol + timeframe is acceptable). |
| `symbol` | string | Ninja instrument code. |
| `timeframe` | string | `"M1"`/`"M5"` etc. |
| `timestamp_utc` | string | ISO8601, bar close time that triggered the event. |
| `ext_dir` | int | External swing direction: `1` up, `-1` down, `0` flat. |
| `int_dir` | int | Internal swing direction (faster leg). |
| `ext_bos` | bool | External BOS fired on this bar. |
| `ext_choch_up` | bool | External CHoCH up break. |
| `ext_choch_down` | bool | External CHoCH down break. |
| `int_bos` | bool | Internal BOS fired. |
| `int_choch` | bool | Internal CHoCH fired (direction implied by `int_dir`). |
| `sweep_prev_high` | bool | Liquidity sweep of previous swing high. |
| `sweep_prev_low` | bool | Liquidity sweep of previous swing low. |
| `fvg_up` | bool | Bullish FVG created. |
| `fvg_down` | bool | Bearish FVG created. |
| `fvg_retest` | bool | Current bar retests an open FVG in its direction. |
| `fvg_gap_high` | float | Upper bound of active FVG (when `fvg_up` or `fvg_down`). |
| `fvg_gap_low` | float | Lower bound of active FVG. |
| `ext_dir_confidence` | float | Optional 0-1 strength for external swing. |
| `int_dir_confidence` | float | Optional 0-1 strength for internal swing. |
| `wave_strength` | float | Strength metric for current zigzag wave (0-1). |
| `mgann_leg_index` | int | 1 for first leg after CHoCH/BOS, 2 for continuation leg, 3+ for extended sequences. |
| `mgann_leg_first_fvg` | bool | True if this is the first FVG inside the current MGann leg. |
| `pb_wave_strength_ok` | bool | Pullback wave strength passes threshold for entry. |
| `ext_dir_after_reclaim` | int | External direction after reclaim/CHOCH resolution. |
| `int_dir_after_reclaim` | int | Internal direction after reclaim/CHOCH resolution. |
| `atr` | float | ATR used for downstream normalization. |
| `session` | string | Session tag (Asia/London/NY/Other). |

> Keep numeric formats as plain decimals; avoid thousands separators. Prices can be exported with 5 decimal places, ATR with 6.

## New Fields (must be added to indicator)
- `mgann_leg_index`: Counter of MGann legs within the current swing package.
- `mgann_leg_first_fvg`: True only for the first FVG printed in a leg; resets on leg change.
- `pb_wave_strength_ok`: Boolean gate indicating the pullback wave is healthy enough to trade (e.g., delta/volume alignment and depth constraints).

## Leg/FVG Scenarios
- **Leg1 creates FVG:** `mgann_leg_index = 1`, `mgann_leg_first_fvg = true`. Treated as reclaim confirmation immediately after CHoCH/BOS.
- **Leg2 creates first FVG of the leg:** `mgann_leg_index = 2`, `mgann_leg_first_fvg = true`. This is the default continuation entry window.
- **Leg2 subsequent FVGs:** `mgann_leg_index = 2`, `mgann_leg_first_fvg = false`. Lower priority; labeling layer may down-rank or skip.
- **Any leg with weak pullback:** set `pb_wave_strength_ok = false` so Layer 2 can reject the setup early.

## Input → Output Contract
- **Input:** Real-time bar stream inside NinjaTrader; indicator computes structure flags and MGann leg metadata.
- **Output:** Append one line per valid entry setup to `event.jsonl` (UTF-8, one JSON object per line).

### Minimal event.jsonl example
```json
{
  "event_id": "6E-M1-20251123-12345",
  "symbol": "6E",
  "timeframe": "M1",
  "timestamp_utc": "2025-11-23T10:30:00Z",
  "ext_dir": 1,
  "int_dir": 1,
  "ext_choch_down": true,
  "fvg_up": true,
  "fvg_retest": true,
  "ext_dir_confidence": 0.78,
  "int_dir_confidence": 0.66,
  "wave_strength": 0.71,
  "mgann_leg_index": 2,
  "mgann_leg_first_fvg": true,
  "pb_wave_strength_ok": true,
  "atr": 0.00025,
  "session": "London"
}
```

### Export validation checklist
- All boolean flags must be `true/false`, never `0/1` strings.
- `mgann_leg_index` resets to 1 after each confirmed CHoCH/BOS.
- If `fvg_retest=true` then either `fvg_up` or `fvg_down` must already exist in the active leg.
- `ext_dir` and `int_dir` must be in `{1,-1,0}`; do not emit other values.
- Timestamps must be UTC; timezone math belongs in the exporter, not downstream.
