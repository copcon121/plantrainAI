# Deprecated Module Doc — Confluence

Confluence scoring is removed as a standalone module. The v3 classifier consumes only the canonical exporter fields and unified labels; no additional scoring stacks are supported.

See the authoritative documents:
- `docs/01_LAYER1_EXPORTER.md`
- `docs/02_LAYER2_LABEL_RULES.md`
- `docs/03_LAYER3_TRAIN_LOOP.md`
- `docs/04_LAYER4_DEPLOY_INFER.md`
- `docs/05_PROJECT_ARCHITECTURE_V3.md`

Keep the system on the single v3 flow; avoid parallel score pipelines.
