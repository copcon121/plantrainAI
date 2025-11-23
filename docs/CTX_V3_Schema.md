# CTX V3 Schema (Compact Context 30–50 bars)

Context payload used for training/inference. Designed for higher information density with a shorter window (30–50 bars) while retaining key structural and MGann signals.

## Included fields per bar
- `open`, `high`, `low`, `close`
- `ext_choch_up`, `ext_choch_down`
- `ext_bos_up`, `ext_bos_down`
- `int_choch_up`, `int_choch_down`
- `int_bos_up`, `int_bos_down`
- `sweep_prev_high`, `sweep_prev_low`
- `fvg_up`, `fvg_down`
- `fvg_retest`
- `delta`, `volume`
- `ext_dir`, `int_dir`
- `wave_strength`
- `mgann_leg_index` (new)
- `mgann_leg_first_fvg` (new)
- `pb_wave_strength_ok` (new)

## Design notes
- Window size: **30–50 bars** (vs. legacy 100) to cut tokens while keeping structure and liquidity cues.
- All boolean flags must be `true/false`; directions restricted to `{-1,0,1}`.
- MGann fields and pullback quality are mandatory to align with the unified labeling logic.

## Example JSON snippet
```json
{
  "schema_version": "ctx_v3",
  "context_bars": [
    {
      "open": 1.0781,
      "high": 1.0786,
      "low": 1.0779,
      "close": 1.0784,
      "ext_choch_down": true,
      "ext_bos_down": false,
      "int_choch_down": false,
      "int_bos_down": true,
      "sweep_prev_high": false,
      "sweep_prev_low": true,
      "fvg_up": true,
      "fvg_down": false,
      "fvg_retest": true,
      "delta": -120,
      "volume": 950,
      "ext_dir": 1,
      "int_dir": 1,
      "wave_strength": 0.72,
      "mgann_leg_index": 2,
      "mgann_leg_first_fvg": true,
      "pb_wave_strength_ok": true
    }
    // ... 29-49 more bars
  ]
}
```

## Usage
- Exporter populates the fields above; labeler consumes the same set.
- Trainer/inference should trim/pack context to minimize tokens while preserving directional and liquidity structure.
