# Layer 3 — Train Loop (LoRA/Qwen)

Training pipeline for the v3 classifier using LoRA on Qwen-class models. Input is labeled events from Layer 2; output is a zipped model artifact ready for inference.

## Data format
- Two files: `train.jsonl` and `val.jsonl`.
- Each line is a JSON object:
```json
{
  "id": "6E-M1-20251123-12345",
  "features": {
    "ext_dir": 1,
    "int_dir": 1,
    "ext_choch_down": true,
    "fvg_up": true,
    "fvg_retest": true,
    "mgann_leg_index": 2,
    "mgann_leg_first_fvg": true,
    "pb_wave_strength_ok": true,
    "wave_strength": 0.71,
    "atr": 0.00025,
    "session": "London"
  },
  "label": "long"
}
```
- Keep labels restricted to `["long","short","skip"]`.
- Maintain ASCII keys; avoid nested objects beyond `features`.

## Pipeline steps
1) **Load dataset**: Parse JSONL, validate required fields, drop malformed rows.
2) **Oversample**: Apply class-balanced oversampling if any class <25% after cleaning.
3) **Class-weighted focal loss**: Compute weights from class counts; use focal loss with gamma tuned per run (start with 1.5).
4) **Training loop**:
   - Base model: Qwen (7B or smaller) with LoRA adapters.
   - Input template: `json.dumps(features)` → encoder; label as target class id.
   - Epoch budget: 3–5, early-stop on `val_macro_f1`.
5) **Evaluation**: Track accuracy, macro-F1, per-class F1, confusion matrix; save `metrics.json`.
6) **Auto-zip model final**: Package adapter weights + tokenizer + config into `model_final.zip`.

## Running the full loop (reference script)
```
python -m processor.train_loop \
  --train-file data/train.jsonl \
  --val-file data/val.jsonl \
  --model qwen-base \
  --lora-r 32 --lora-alpha 64 \
  --batch-size 64 --lr 3e-4 \
  --gamma 1.5 --class-weights auto \
  --output-dir outputs/v3_run1
```
- The script should emit: `metrics.json`, `checkpoint_best`, `model_final.zip`.
- CPU-only: reduce `batch-size` and enable gradient accumulation.

## Validation gates
- `val_macro_f1 >= 0.60` target; stop training if plateau after one epoch.
- Long/short F1 must both exceed 0.55; if not, re-check oversampling and focal gamma.
- Ensure `model_final.zip` exists and is <500MB for VPS deployment.

## Notes
- Keep feature ordering stable; sorting keys before serialization reduces noise.
- Do not embed raw price series; only engineered fields from exporter/labeler.
- Log class distribution before/after oversample for every run.
