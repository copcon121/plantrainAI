# Layer 1 — Exporter (v3)

Specification for the NinjaTrader exporter indicator that feeds the unified pipeline. Output: `event.jsonl`, one JSON object per setup. No labels or ML scoring here.

## Responsibilities
- Detect structure signals (BOS/CHOCH), liquidity sweeps, FVG creation/retest, and MGann leg context in real time.
- Emit canonical fields only; ensure consistent naming for downstream layers.
- Guard pullback quality via `pb_wave_strength_ok` to prevent noisy legs from entering the dataset.

## Field set (must export)
| Field | Type | Notes |
|-------|------|-------|
| `event_id` | string | Unique per setup (symbol + timeframe + bar index). |
| `symbol` | string | Instrument code. |
| `timeframe` | string | e.g., `M1`. |
| `timestamp_utc` | string | ISO8601 UTC of bar close. |
| `ext_dir` | int | External structure dir: `1/-1/0`. |
| `int_dir` | int | Internal structure dir: `1/-1/0`. |
| `ext_bos` | bool | External BOS pulse. |
| `ext_choch_up` | bool | External CHoCH up. |
| `ext_choch_down` | bool | External CHoCH down. |
| `int_bos` | bool | Internal BOS pulse. |
| `int_choch` | bool | Internal CHoCH pulse. |
| `sweep_prev_high` | bool | Liquidity sweep of prior swing high. |
| `sweep_prev_low` | bool | Liquidity sweep of prior swing low. |
| `fvg_up` | bool | Bullish FVG created. |
| `fvg_down` | bool | Bearish FVG created. |
| `fvg_retest` | bool | Current bar retests the active FVG. |
| `fvg_gap_high` | float | FVG upper bound. |
| `fvg_gap_low` | float | FVG lower bound. |
| `wave_strength` | float | 0–1 strength score for current zigzag wave. |
| `mgann_leg_index` | int | 1 = first leg after CHoCH/BOS; 2 = continuation; >2 ignored by labeling. |
| `mgann_leg_first_fvg` | bool | True if first FVG in the current MGann leg. |
| `pb_wave_strength_ok` | bool | Pullback wave health gate. |
| `atr` | float | ATR for normalization. |
| `session` | string | Session tag (Asia/London/NY/Other). |

## Event emission rules
- Reset `mgann_leg_index` to 1 on every confirmed `ext_choch_*` or `ext_bos`.
- Set `mgann_leg_first_fvg = true` only for the first FVG inside each leg.
- Emit an event when an eligible directional FVG exists and `fvg_retest = true`; skip if `pb_wave_strength_ok = false`.
- Keep booleans as `true/false` (not `0/1`), and limit `ext_dir/int_dir` to `{-1,0,1}`.

## Mapping to CTX v3
- Structural flags: `ext_choch_*`, `ext_bos`, `int_choch`, `int_bos`, `ext_dir`, `int_dir`.
- Liquidity context: `sweep_prev_high`, `sweep_prev_low`.
- FVG context: `fvg_up/down`, `fvg_retest`, `fvg_gap_high/low`.
- MGann context: `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`.
- Normalizers: `atr`, `session`.

## Example `event.jsonl` line
```json
{
  "event_id": "6E-M1-20251123-12345",
  "symbol": "6E",
  "timeframe": "M1",
  "timestamp_utc": "2025-11-23T10:30:00Z",
  "ext_dir": 1,
  "int_dir": 1,
  "ext_choch_down": true,
  "ext_bos": false,
  "int_bos": true,
  "sweep_prev_high": false,
  "sweep_prev_low": true,
  "fvg_up": true,
  "fvg_down": false,
  "fvg_retest": true,
  "fvg_gap_high": 1.07850,
  "fvg_gap_low": 1.07810,
  "wave_strength": 0.72,
  "mgann_leg_index": 2,
  "mgann_leg_first_fvg": true,
  "pb_wave_strength_ok": true,
  "atr": 0.00024,
  "session": "London"
}
```

## MGann Leg Fields (Module 14)

> [!IMPORTANT]
> The following fields are **calculated by Module 14 (Python layer)**, not the C# exporter.
> The C# exporter only exports raw SMC data (ext_dir, ext_bos_up, etc.).
> Module 14 processes this raw data and calculates these derived fields.

| Field | Type | Calculated By | Description |
|-------|------|---------------|-------------|
| `mgann_leg_index` | int | Module 14 | Current leg number (1, 2, 3...). Resets on CHoCH/BOS trend change. |
| `mgann_leg_first_fvg` | bool | Module 14 | True if this bar has the FIRST FVG of the current leg. Subsequent FVGs in same leg = false. |
| `pb_wave_strength_ok` | bool | Module 14 | True if pullback meets Hybrid Rule v4 criteria (6 conditions). See ARCHITECTURE_V3.md for formula. |

**Pipeline:**
```
NinjaTrader C# → JSONL (raw: ext_dir, ext_bos_up, fvg_up, etc.)
                  ↓
Module 14 Python → JSON (+ mgann_leg_index, mgann_leg_first_fvg, pb_wave_strength_ok)
```

**Why Module 14 calculates these:**
- Requires leg classification (impulse vs pullback)
- Requires historical accumulation (impulse delta/volume)
- Requires structure tracking (leg1 anchor levels)
- Cannot be derived from single bar data alone

## Version
- **v3** — canonical exporter contract for the unified pipeline.
