# Deprecated Module Doc — MGann Swing

**Version:** 3.0.0 (Layer Architecture V3)
**Status:** Deprecated - Merged into unified architecture

This module spec is superseded by the unified architecture v3. MGann handling now lives in Layer 1 fields (`mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`) and the Layer 2 labeling rules.

## Canonical references:
- Exporter: `docs/LAYER1_EXPORTER.md`
- Label rules: `docs/LAYER2_Label_Rules_v1.md`
- Train loop: `docs/LAYER3_TRAIN_LOOP.md`
- Deploy/Infer: `docs/LAYER4_DEPLOY_INFER.md`
- Architecture overview: `docs/Project_Architecture_v3.md`

No alternate MGann logic is maintained here; use the single v3 flow only.

## Key V3 Fields (for reference)

| Field | Type | Description |
|-------|------|-------------|
| `mgann_leg_index` | int | Current leg index (1, 2, 3, ...) |
| `mgann_leg_first_fvg` | dict/null | First FVG in current leg sequence |
| `pb_wave_strength_ok` | bool | Pullback wave strength confirmed |
| `mgann_wave_strength` | int | Wave strength score 0-100 |

## Label Rule (A) Integration

```python
# MGann fields used in Label Rule (A)
conditions = [
    # ...
    event.mgann_leg_index <= 2,          # MGann leg 1 or 2 (early entry)
    event.pb_wave_strength_ok == True,   # Pullback wave strength confirmed
]
```

For full implementation details, see `docs/LAYER2_Label_Rules_v1.md`.
