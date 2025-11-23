# Layer 4 — Deploy / Infer

Inference serving layer for the v3 pipeline. Provides a FastAPI endpoint that NinjaTrader can call when a setup appears.

## API surface (FastAPI)
- `POST /predict`
- Request headers: `Content-Type: application/json`
- Response: JSON with `action`, `score`, `timestamp_utc`.

### Expected payload from NinjaTrader
```json
{
  "event_id": "6E-M1-20251123-12345",
  "symbol": "6E",
  "timeframe": "M1",
  "timestamp_utc": "2025-11-23T10:30:00Z",
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
  }
}
```
- Reject requests missing required Layer 2 fields; respond with `{"action":"skip","reason":"missing_field"}`.

### Prediction mapping
- Model output classes: `long`, `short`, `skip`.
- Action mapping:
  - `long`  → `EnterLong`
  - `short` → `EnterShort`
  - `skip`  → `Skip`
- Response example:
```json
{
  "event_id": "6E-M1-20251123-12345",
  "action": "EnterLong",
  "score": 0.71,
  "timestamp_utc": "2025-11-23T10:30:01Z"
}
```

## Timeout policy
- Default server timeout: 800ms.
- If inference exceeds timeout or raises exception: return `{"action":"Skip","reason":"timeout"}` and log the request.
- NinjaTrader side must treat `Skip` as a no-trade; do not retry the same event.

## Running on VPS
- **CPU mode:** use `--device cpu --threads auto`. Suitable for low-traffic; latency 300–800ms.
- **GPU mode:** use `--device cuda --gpu-mem 6GB+`; pre-load model at startup to avoid first-call penalty.
- Recommended process manager: `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1`.
- Enable health check endpoint `/healthz` returning `{status:"ok"}` for monitoring.

## Operational checklist
- Load `model_final.zip` from Layer 3; verify checksum before serving.
- Log `(event_id, action, score, latency_ms)` to rotating files for audit.
- Keep feature schema versioned (`schema_version: v3`) in responses for forward compatibility.
- Only one live model per symbol/timeframe set; disable any legacy v2 endpoints.
