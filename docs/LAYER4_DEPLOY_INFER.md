# Layer 4 — Deploy / Infer (v3)

FastAPI inference service that serves the unified classifier to NinjaTrader. Maps model predictions to `EnterLong`, `EnterShort`, or `Skip`.

## Request payload (from NinjaTrader)
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
    "wave_strength": 0.72,
    "atr": 0.00024,
    "session": "London"
  }
}
```

## Response mapping
- Model classes: `long`, `short`, `skip`.
- Actions:
  - `long` → `EnterLong`
  - `short` → `EnterShort`
  - `skip` → `Skip`
- Example response:
```json
{
  "event_id": "6E-M1-20251123-12345",
  "action": "EnterLong",
  "score": 0.71,
  "timestamp_utc": "2025-11-23T10:30:01Z",
  "schema_version": "v3"
}
```

## Timeout and errors
- Per-request timeout: **800 ms**. On timeout or exception, return `{"action":"Skip","reason":"timeout"}` and log the event.
- Validate presence of required fields; missing/invalid payload → respond with `Skip` + reason.
- NinjaTrader must not retry the same `event_id` after a skip/timeout.

## AutoBot integration
- Bind `EnterLong`/`EnterShort` to NinjaTrader strategy entry functions; respect `Skip`.
- Log `(event_id, action, score, latency_ms)` for audit.
- Keep one active model per symbol/timeframe; disable legacy endpoints.

## Serving guidelines
- Load `model_final.zip` at startup; verify checksum.
- CPU: `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 1`.
- GPU: pre-warm model; ensure GPU memory ≥6GB.
- Expose `/healthz` returning `{ "status": "ok" }` for monitoring.
