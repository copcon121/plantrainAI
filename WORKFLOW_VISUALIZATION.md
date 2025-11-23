# Workflow Visualization — v3 Unified Flow

## End-to-end pipeline
```
[NinjaTrader Indicator]
    |  emit structured fields (ext_dir, fvg_up/down, mgann_leg_index, pb_wave_strength_ok, ...)
    v
[Layer 1 Exporter] --> event.jsonl
    v
[Layer 2 Labeler] --(rules A+B merged)--> train.jsonl / val.jsonl
    v
[Layer 3 Train Loop (LoRA/Qwen)] --> model_final.zip + metrics.json
    v
[Layer 4 FastAPI Inference] --> EnterLong / EnterShort / Skip
    v
[Autobot Execution on NinjaTrader]
```

## Labeling decision flow (text chart)
```
ext_choch_down/up? -> no -> SKIP
           yes
ext_dir matches side? -> no -> SKIP
           yes
mgann_leg_index <= 2? -> no -> SKIP
           yes
pb_wave_strength_ok? -> no -> SKIP
           yes
fvg_up/down? -> no -> SKIP
           yes
fvg_retest? -> no -> WAIT
           yes
LABEL long/short (prefer mgann_leg_first_fvg=true)
```

## Train/eval loop (high level)
```
Load train.jsonl / val.jsonl
    |
Oversample minority classes
    |
Class-weighted focal loss
    |
Train LoRA on Qwen (3-5 epochs, early stop on val_macro_f1)
    |
Save metrics.json + model_final.zip
```

## Deployment surface
```
POST /predict
  payload: {event_id, features{ext_dir, int_dir, ext_choch_*, fvg_*, mgann_leg_index, mgann_leg_first_fvg, pb_wave_strength_ok, wave_strength, atr, session}}
  response: {event_id, action: EnterLong|EnterShort|Skip, score, timestamp_utc}
  timeout: 800ms -> action=Skip
```
