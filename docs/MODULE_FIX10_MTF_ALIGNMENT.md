# Deprecated Module Doc — MTF Alignment

MTF alignment is no longer a standalone module. The v3 stack relies solely on the canonical exporter fields and unified label rules.

Use these references instead:
- Exporter spec: `docs/01_LAYER1_EXPORTER.md`
- Label rules: `docs/02_LAYER2_LABEL_RULES.md`
- Train loop: `docs/03_LAYER3_TRAIN_LOOP.md`
- Deploy/Infer: `docs/04_LAYER4_DEPLOY_INFER.md`
- Architecture: `docs/05_PROJECT_ARCHITECTURE_V3.md`

If higher-timeframe cues are needed, add them as new exporter fields and update all v3 docs together; do not resurrect module-specific flows.
