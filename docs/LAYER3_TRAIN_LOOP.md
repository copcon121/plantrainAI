# Layer 3 — Train Loop (v3)

Training pipeline for the unified classifier using LoRA/Qwen. Designed for datasets of 1000–1500 events labeled by the merged rules.

## Pipeline steps
1. **Load data:** parse `train.jsonl` / `val.jsonl`; validate required features.
2. **Oversample:** rebalance classes if any share <25%; keep post-oversample near 30–40% each.
3. **Loss:** class-weighted focal loss (gamma start 1.5) with weights from class counts.
4. **Model:** Qwen base with LoRA adapters; last-token classification head.
5. **Training:** 3–5 epochs with early stop on `val_macro_f1`; gradient accumulation for CPU if needed.
6. **Evaluation:** accuracy, macro-F1, per-class F1, confusion matrix; save `metrics.json`.
7. **Packaging:** export adapters/tokenizer/config as `model_final.zip`.

## Required feature keys
`ext_dir`, `int_dir`, `ext_choch_up/down`, `fvg_up/down`, `fvg_retest`, `mgann_leg_index`, `mgann_leg_first_fvg`, `pb_wave_strength_ok`, `wave_strength`, `atr`, `session`.

## Command examples
```bash
python -m processor.train_loop ^
  --train-file data/train.jsonl ^
  --val-file data/val.jsonl ^
  --model qwen-base ^
  --lora-r 32 --lora-alpha 64 ^
  --batch-size 64 --lr 3e-4 ^
  --gamma 1.5 --class-weights auto ^
  --max-epochs 5 --early-stop-metric val_macro_f1 ^
  --output-dir outputs/v3_run1
```

CPU-friendly:
```bash
python -m processor.train_loop ^
  --train-file data/train.jsonl ^
  --val-file data/val.jsonl ^
  --model qwen-base ^
  --batch-size 8 --grad-accum 8 --device cpu ^
  --gamma 1.5 --class-weights auto ^
  --output-dir outputs/v3_cpu
```

## Config template (YAML)
```yaml
model: qwen-base
lora:
  r: 32
  alpha: 64
  dropout: 0.05
training:
  batch_size: 64
  lr: 3.0e-4
  epochs: 5
  early_stop_metric: val_macro_f1
loss:
  type: focal
  gamma: 1.5
  class_weights: auto
data:
  train_file: data/train.jsonl
  val_file: data/val.jsonl
  oversample: true
packaging:
  output_dir: outputs/v3_run1
  zip_final: model_final.zip
```

## Checks before shipping
- Class balance after oversample within 30–40% per class.
- `val_macro_f1 >= 0.60` and per-class F1 (long/short) ≥ 0.55.
- `metrics.json` and `model_final.zip` both present.
- Feature schema matches exporter/labeler (no extra keys).
