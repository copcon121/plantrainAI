# Deprecated Module Doc — Stop Placement

Stop-placement logic is not tracked separately in v3. The only supported flow is exporter → label → train → infer, producing `EnterLong/EnterShort/Skip`.

Canonical references:
- `docs/01_LAYER1_EXPORTER.md`
- `docs/02_LAYER2_LABEL_RULES.md`
- `docs/03_LAYER3_TRAIN_LOOP.md`
- `docs/04_LAYER4_DEPLOY_INFER.md`
- `docs/05_PROJECT_ARCHITECTURE_V3.md`

Document TP/SL conventions inside deployment if needed, but do not restore per-module specs.
