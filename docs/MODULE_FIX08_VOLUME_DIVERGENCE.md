# Deprecated Module Doc — Volume Divergence

Volume divergence is not tracked as a standalone module in v3. The ML stack now depends only on the canonical exporter fields and merged labeling rules.

Use the v3 documents:
- Exporter: `docs/01_LAYER1_EXPORTER.md`
- Label rules: `docs/02_LAYER2_LABEL_RULES.md`
- Train loop: `docs/03_LAYER3_TRAIN_LOOP.md`
- Deploy/Infer: `docs/04_LAYER4_DEPLOY_INFER.md`
- Architecture: `docs/05_PROJECT_ARCHITECTURE_V3.md`

Do not maintain divergence-specific logic outside the unified flow.
