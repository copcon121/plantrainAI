# Deprecated Module Doc — Target Placement

Target/SL placement logic is not maintained as a separate module in v3. Execution decisions derive from the single ML classifier output (`EnterLong/EnterShort/Skip`) produced by the unified pipeline.

Authoritative documents:
- `docs/01_LAYER1_EXPORTER.md`
- `docs/02_LAYER2_LABEL_RULES.md`
- `docs/03_LAYER3_TRAIN_LOOP.md`
- `docs/04_LAYER4_DEPLOY_INFER.md`
- `docs/05_PROJECT_ARCHITECTURE_V3.md`

Any TP/SL conventions must be documented inside the deployment layer and aligned with these files; do not revive legacy module flows.
