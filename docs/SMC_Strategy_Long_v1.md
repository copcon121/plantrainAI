# SMC Strategy Long v1.0

Canonical long entry flow: **External CHoCH Down → Reclaim → MGann leg → FVG up → Retest → Pullback OK → Long**. Case A (Leg1 FVG) and Case B (Leg2 FVG) are unified into one rule.

## Required exporter fields
- `ext_choch_down`
- `fvg_up`
- `fvg_retest`
- `ext_dir`
- `mgann_leg_index`
- `pb_wave_strength_ok`
- Optional soft feature: `mgann_leg_first_fvg`

## Volume/Delta guardrails
- **Delta sell small** on retest (no aggressive selling).
- **Volume contraction** on retest vs. creation bar.
- **No bearish absorption** detected on retest candle.
- If any guardrail fails → treat as `skip`.

## Unified logic (Case A/B merged)
- `ext_choch_down = true`
- `ext_dir = 1`
- `mgann_leg_index <= 2`
- `fvg_up = true`
- `fvg_retest = true`
- `pb_wave_strength_ok = true`
- → Action: Long entry allowed (prefers `mgann_leg_first_fvg = true`).

## Flowchart (Mermaid)
```mermaid
flowchart TD
    A[ext_choch_down?] -->|no| SKIP1[Skip]
    A -->|yes| B[ext_dir = 1?]
    B -->|no| SKIP2[Skip]
    B -->|yes| C[mgann_leg_index <= 2?]
    C -->|no| SKIP3[Skip]
    C -->|yes| D[pb_wave_strength_ok?]
    D -->|no| SKIP4[Skip]
    D -->|yes| E[fvg_up?]
    E -->|no| SKIP5[Skip]
    E -->|yes| F[fvg_retest?]
    F -->|no| WAIT[Wait - no label]
    F -->|yes| G[Volume contraction?]
    G -->|no| SKIP6[Skip]
    G -->|yes| H[Delta sell small?]
    H -->|no| SKIP7[Skip]
    H -->|yes| I[No bearish absorption?]
    I -->|no| SKIP8[Skip]
    I -->|yes| L[Label/Enter Long]
```

## Version
- **v1.0** — unified long strategy aligned to architecture v3.
