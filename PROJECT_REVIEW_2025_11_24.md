# PROJECT REVIEW: plantrainAI
**Date:** November 24, 2025
**Reviewer:** Claude Code
**Version Reviewed:** 3.0.0

---

## EXECUTIVE SUMMARY

plantrainAI is an Auto-Trading system using SMC (Smart Money Concepts) + MGannSwing + Machine Learning with a 4-layer architecture. The project has excellent documentation and a complete Layer 2 Python processor, but significant work remains on the NinjaTrader exporter, ML training pipeline, and inference server.

**Overall Progress: ~35%**

---

## PROJECT ARCHITECTURE

| Layer | Description | Status | Progress |
|-------|-------------|--------|----------|
| **Layer 1** | NinjaTrader C# Exporter | Partial | 20% |
| **Layer 2** | Python Data Processor (14 modules) | Complete | 100% |
| **Layer 3** | ML Training Loop (LoRA/Qwen) | Not Started | 0% |
| **Layer 4** | FastAPI Inference Server | Not Started | 0% |

---

## COMPLETED WORK

### 1. Documentation (95% Complete)
- Main docs: `README.md`, `ARCHITECTURE_V3.md`, `PROJECT_MASTER_PLAN.md`
- Layer specifications: `01_LAYER1_EXPORTER.md` through `04_LAYER4_DEPLOY_INFER.md`
- Field requirements: `NINJA_EXPORT_CHECKLIST.md`, `CTX_V3_Schema.md`
- 14 MODULE_FIX*.md documentation files
- Strategy docs: `SMC_Strategy_Long_v1.md`, `SMC_Strategy_Short_v1.md`

### 2. Layer 2 Python Processor (14/14 modules - 3,714 lines)

| Module | File | Lines | Purpose |
|--------|------|-------|---------|
| #01 | `fix01_ob_quality.py` | 248 | Order Block Quality Scoring |
| #02 | `fix02_fvg_quality.py` | 320 | FVG Quality Scoring |
| #03 | `fix03_structure_context.py` | 233 | Structure Context Analysis |
| #04 | `fix04_confluence.py` | 300 | Confluence Scoring |
| #05 | `fix05_stop_placement.py` | 290 | Stop Loss Placement |
| #06 | `fix06_target_placement.py` | 330 | Take Profit Placement |
| #07 | `fix07_market_condition.py` | 196 | Market Condition Detection |
| #08 | `fix08_volume_divergence.py` | 231 | Volume Divergence Analysis |
| #09 | `fix09_volume_profile.py` | 257 | Volume Profile Analysis |
| #10 | `fix10_mtf_alignment.py` | 170 | Multi-Timeframe Alignment |
| #11 | `fix11_liquidity_map.py` | 307 | Liquidity Mapping |
| #12 | `fix12_fvg_retest.py` | 262 | FVG Retest Detection |
| #13 | `fix13_wave_delta.py` | 177 | Wave Delta Accumulation |
| #14 | `fix14_mgann_swing.py` | 390 | MGann Swing Detection |

### 3. Core Infrastructure
- `processor/core/module_base.py` - BaseModule abstract class with validation helpers
- `processor/core/bar_state.py` - BarState dataclass
- `processor/core/event_state.py` - EventState dataclass
- `processor/smc_processor.py` - Module pipeline orchestrator
- `processor/validation/schema.py` - JSONL schema validation

### 4. Testing (17 test files)
- Unit tests for all 14 modules
- Integration tests (`test_integration.py`)
- Smoke tests (`test_modules_smoke.py`)
- Test fixtures and conftest.py

### 5. Backtest Tools
- `processor/backtest/run_module_backtest.py`
- `processor/backtest/eval_filtered_signals.py`
- `processor/backtest/eval_retest_raw.py`

### 6. Sample Data
- `deepseek_enhanced_GC 12-25_M1_20251103.jsonl` (~5.5MB) - Gold futures M1 data with rich bar context

### 7. NinjaTrader Components
- `indicators/Volumdelta.cs` - Volume Delta indicator (third-party adapted)

---

## PENDING WORK

### Priority 1: Critical

#### 1.1 Update Module #14 MGann Swing Output
**Current Issue:** Module doesn't output v3 required fields for Label Rule (A).

**Missing outputs:**
- `mgann_leg_index` (int) - Current leg 1, 2, 3...
- `mgann_leg_first_fvg` (dict) - First FVG in leg sequence
- `pb_wave_strength_ok` (bool) - Pullback wave strength gate

**Required changes to `fix14_mgann_swing.py`:**
```python
# Need to track and output:
bar_state["mgann_leg_index"] = self.current_leg_index
bar_state["mgann_leg_first_fvg"] = self.first_fvg_in_leg
bar_state["pb_wave_strength_ok"] = self._check_pb_wave_strength()
```

#### 1.2 Create Labeling Script
**File to create:** `processor/labeler.py`

Implements Label Rule (A):
```python
def apply_label_rule_long(event):
    conditions = [
        event.get("ext_choch_down") == True,
        event.get("fvg_up") == True,
        event.get("fvg_retest") == True,
        event.get("ext_dir") == 1,
        event.get("mgann_leg_index", 999) <= 2,
        event.get("pb_wave_strength_ok") == True,
    ]
    return "long" if all(conditions) else "skip"
```

#### 1.3 Update Schema Validation
**File:** `processor/validation/schema.py`

Add missing v3 required fields:
- `mgann_leg_index`
- `mgann_leg_first_fvg`
- `pb_wave_strength_ok`
- `fvg_retest`

### Priority 2: High

#### 2.1 NinjaTrader Main Exporter (Layer 1)
Create main SMC indicator that exports `event.jsonl` with all required fields per `NINJA_EXPORT_CHECKLIST.md`.

#### 2.2 Training Pipeline (Layer 3)
- `processor/train_loop.py` - Main training script
- LoRA adapter training on Qwen models
- Class-weighted focal loss
- Oversampling for class balance
- `metrics.json` and `model_final.zip` output

#### 2.3 FastAPI Server (Layer 4)
- `main.py` - FastAPI application
- `/predict` endpoint with 800ms timeout
- `/healthz` health check
- Model loading and inference

### Priority 3: Medium

- Add integration tests for full pipeline
- Fix version inconsistencies (pyproject.toml vs README)
- Add proper module exports in `processor/modules/__init__.py`
- Improve error handling in SMCDataProcessor

---

## BUGS AND ISSUES FOUND

### Code Issues

| Issue | Location | Severity | Description |
|-------|----------|----------|-------------|
| Missing module exports | `processor/modules/__init__.py` | Low | Only 3 lines, no exports |
| Version mismatch | `pyproject.toml` vs `README.md` | Low | 2.1.0 vs 3.0.0 |
| Auto-add limited | `processor/smc_processor.py:22` | Medium | Only auto-adds WaveDeltaModule |
| Schema outdated | `processor/validation/schema.py` | High | Missing v3 required fields |
| MGann output incomplete | `fix14_mgann_swing.py` | Critical | Missing `mgann_leg_index`, `pb_wave_strength_ok` |

### Data Issues

Sample data (`deepseek_enhanced_GC 12-25_M1_20251103.jsonl`) is missing v3 required fields:
- `mgann_leg_index` - Not present
- `mgann_leg_first_fvg` - Not present
- `pb_wave_strength_ok` - Not present
- `fvg_retest` - Not present (has `fvg_fill_percentage` instead)

---

## RECOMMENDATIONS

### Immediate Actions (This Week)

1. **Fix Module #14** to output `mgann_leg_index` and `pb_wave_strength_ok`
2. **Create labeling script** implementing Label Rule (A)
3. **Update schema validation** with v3 fields
4. **Regenerate sample data** with complete fields (or enhance existing)

### Short-term (Next 2 Weeks)

5. **Implement training pipeline** with LoRA/Qwen
6. **Create FastAPI server** for inference
7. **End-to-end testing** from export → label → train → infer

### Medium-term (Next Month)

8. **NinjaTrader integration** - Full exporter indicator
9. **Performance optimization** - Latency targets < 800ms
10. **Production deployment** - VPS setup, monitoring

---

## METRICS SUMMARY

| Category | Count |
|----------|-------|
| Python modules | 14 |
| Lines of module code | 3,714 |
| Test files | 17 |
| Documentation files | 37 |
| Sample data size | 5.5 MB |
| NinjaTrader indicators | 1 |

---

## VERSION HISTORY

| Version | Date | Notes |
|---------|------|-------|
| 3.0.0 | 2025-11-24 | Layer Architecture V3, Label Rule (A), MGann V3 fields |
| 2.1.0 | 2025-11-21 | FVG Quality v2.0, Wave Delta module |
| 2.0.0 | 2025-11-20 | 14 module architecture |
| 1.0.0 | 2025-11-15 | Initial 3-layer design |

---

*Review completed by Claude Code on November 24, 2025*
