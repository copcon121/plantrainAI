# Layer 2 — Label Rules (A)

Single source of truth for labeling logic. Only one rule set is allowed (Case A + B merged) to keep dataset size 1k–1.5k events and avoid class fragmentation.

## Canonical long/short rules

**LONG (Case A+B merged, mandatory):**
- `ext_choch_down = true`
- `fvg_up = true`
- `fvg_retest = true`
- `ext_dir = 1`
- `mgann_leg_index <= 2`
- `pb_wave_strength_ok = true`
- Optional boost: `mgann_leg_first_fvg = true` (preferred but not required)
- => `label = "long"`

**SHORT (mirror):**
- `ext_choch_up = true`
- `fvg_down = true`
- `fvg_retest = true`
- `ext_dir = -1`
- `mgann_leg_index <= 2`
- `pb_wave_strength_ok = true`
- Optional boost: `mgann_leg_first_fvg = true`
- => `label = "short"`

If any required condition fails, set `label = "skip"`. No other rule branches are permitted.

## Flow narrative (CHOCH → Reclaim → MGann Leg → FVG → Retest)
1) **CHOCH/Reclaim**: External CHoCH triggers structure shift (`ext_choch_down` for long, `ext_choch_up` for short). Reset `mgann_leg_index` to 1.
2) **Reclaim / Direction lock**: `ext_dir` aligns with reclaimed side (1 for bullish reclaim, -1 for bearish).
3) **MGann Leg assessment**: `mgann_leg_index` counts legs after reclaim. Only leg 1 and 2 are eligible; `pb_wave_strength_ok` must be true to confirm pullback health.
4) **FVG creation**: Directional FVG must print (`fvg_up`/`fvg_down`). The first FVG in the leg is most desired (`mgann_leg_first_fvg=true`).
5) **Retest confirmation**: `fvg_retest=true` marks price interaction. Without retest the event is skipped.
6) **Label emit**: If all gates pass, write `label` (long/short). Otherwise write `skip`.

## Text flowchart
```
[ext_choch_down/up?] --no--> SKIP
           |
        yes v
[ext_dir matches side?] --no--> SKIP
           |
        yes v
[mgann_leg_index <= 2?] --no--> SKIP
           |
        yes v
[pb_wave_strength_ok?] --no--> SKIP
           |
        yes v
[fvg_up/down created?] --no--> SKIP
           |
        yes v
[fvg_retest?] --no--> WAIT (no label)
           |
        yes v
LABEL = long/short (prefer mgann_leg_first_fvg = true)
```

## ML feature tag mapping
| Export field | ML feature name | Purpose |
|--------------|-----------------|---------|
| `ext_dir` | `ext_dir` | Directional bias from outer structure. |
| `int_dir` | `int_dir` | Micro confirmation; optional weight. |
| `ext_choch_up/down` | `ext_choch_flag` | Reclaim detection. |
| `fvg_up/down` | `fvg_dir` | Signal-side FVG presence. |
| `fvg_retest` | `fvg_retest` | Entry timing gate. |
| `mgann_leg_index` | `mgann_leg_index` | Filter later legs (>2). |
| `mgann_leg_first_fvg` | `mgann_leg_first_fvg` | Prioritize first FVG in leg. |
| `pb_wave_strength_ok` | `pb_wave_strength_ok` | Reject weak pullbacks. |
| `wave_strength` | `wave_strength` | Optional numeric support for `pb_wave_strength_ok`. |
| `sweep_prev_high/low` | `liq_sweep_flag` | Context for reclaim validity. |
| `atr` | `atr` | Normalization for geometric filters. |

Use only these tags for training; any additional indicator output should be ignored to prevent drift.

## Dataset sizing note (1000–1500 events)
- Case A and B were merged to keep enough positive examples per side while preserving pattern purity.
- `mgann_leg_index <= 2` caps event inflation from extended legs.
- `pb_wave_strength_ok` ensures noisy legs are excluded instead of forming new sub-classes.
- Target class balance after labeling: long 30–40%, short 30–40%, skip remainder.

## Quality checklist before writing labels
- No label emitted before `fvg_retest = true`.
- Do not down-sample by symbol/timeframe; balance handled in training.
- Ensure `ext_dir` and `fvg_dir` agree (bullish reclaim must not label a bearish FVG).
- If `mgann_leg_first_fvg=false`, still label but add `first_fvg_bonus=false` tag in features for ML weighting (optional).
