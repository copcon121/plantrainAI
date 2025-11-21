# 🎯 SMC TRADING MODEL - MASTER PROJECT PLAN
## Dự Án Cải Thiện Chất Lượng Model & Signal Quality
**Version:** 1.0.0
**Date Started:** November 20, 2025
**Project Lead:** SMC & ML Expert (20 years experience)
**Status:** 🔴 IN PLANNING PHASE

---

## 📋 MỤC LỤC

1. [Tổng Quan Dự Án](#tổng-quan-dự-án)
2. [Vấn Đề Hiện Tại](#vấn-đề-hiện-tại)
3. [Kiến Trúc 3 Modules](#kiến-trúc-3-modules)
4. [Timeline & Milestones](#timeline--milestones)
5. [Quy Trình Review](#quy-trình-review)
6. [Success Metrics](#success-metrics)
7. [Dependencies & Prerequisites](#dependencies--prerequisites)
8. [Risk Management](#risk-management)

---

## 🎯 TỔNG QUAN DỰ ÁN

### Mục Tiêu Chính

**Cải thiện model accuracy từ 50.99% lên 75%+ thông qua:**
1. ✅ Tăng chất lượng signal từ NinjaTrader (win rate 22.7% → 35%+)
2. ✅ Sửa logic labeling để model học đúng cách
3. ✅ Tối ưu training pipeline với class weights và metrics tốt hơn

### Nguyên Tắc Làm Việc

```
🔵 MODULE-BASED APPROACH
├── Mỗi module độc lập, có thể test riêng
├── Complete một module trước khi chuyển sang module tiếp theo
├── Review kỹ lưỡng sau mỗi module
└── Document đầy đủ quyết định và thay đổi

🔵 EXPERT-DRIVEN METHODOLOGY
├── Dựa trên 20 năm kinh nghiệm SMC + ML
├── Ưu tiên chất lượng hơn tốc độ
├── Test thoroughly trước khi deploy
└── Maintain backward compatibility khi có thể

🔵 ITERATIVE IMPROVEMENT
├── Đo lường baseline trước khi thay đổi
├── A/B testing khi cần thiết
├── Track metrics liên tục
└── Rollback nhanh nếu có vấn đề
```

---

## 🚨 VẤN ĐỀ HIỆN TẠI

### Từ Dataset Audit Report

**CRITICAL FINDING #1: Labeling Logic Flawed**
```python
# Current (WRONG):
assistant = e["signal"] if e["label"] == "win" else "skip"

# Problem:
- 77% data labeled as "skip" (severe imbalance)
- Model learns to always predict "skip" (F1_long=0, F1_short=0)
- No learning from failure cases
```

**CRITICAL FINDING #2: Low Win Rate**
```
Source Data Stats:
├── WIN:     22.7% (2,266 trades) ❌
├── LOSS:    74.6% (7,456 trades) ❌
└── NEUTRAL:  2.8% (278 trades)

Professional Standard:
├── WIN:     35-45% ✅
└── LOSS:    50-60% ✅
```

### Current Results
```
Training Results (2 epochs, 182.8 min):
├── Accuracy:       50.99%
├── Macro F1:       0.2251
├── F1 Long:        0.0000 ❌
├── F1 Short:       0.0000 ❌
└── F1 Skip:        0.6754 ✅

Interpretation: Model only predicts SKIP class
```

---

## 🏗️ KIẾN TRÚC 3 MODULES

### Module Flow

```
┌─────────────────────────────────────────────────────────┐
│                   PROJECT MASTER PLAN                    │
│                  (This Document)                         │
└────────────┬────────────────────────────────────────────┘
             │
             ├──> MODULE 1: SIGNAL QUALITY FIX
             │    ├── Fix NinjaTrader Indicators
             │    ├── Improve Entry Logic
             │    ├── Better Stop/TP Placement
             │    └── Target: 35%+ win rate
             │
             ├──> MODULE 2: DATA LABELING FIX
             │    ├── Fix build_all_enhanced_optimized.py
             │    ├── Implement Option A/B/C
             │    ├── Regenerate Dataset
             │    └── Validate New Distribution
             │
             └──> MODULE 3: TRAINING PIPELINE
                  ├── Add Class Weights
                  ├── Improve Metrics
                  ├── Train New Model
                  └── Comprehensive Backtest
```

### Module Dependencies

```
MODULE 1 ──must complete──> MODULE 2 ──must complete──> MODULE 3
   │                            │                          │
   │                            │                          │
   v                            v                          v
35%+ win rate            Balanced dataset           75%+ accuracy
Good signals            Correct labels              Profitable model
```

---

## 📦 MODULE 1: SIGNAL QUALITY FIX
**Priority:** 🔴 HIGHEST
**Document:** [MODULE_1_SIGNAL_QUALITY.md](MODULE_1_SIGNAL_QUALITY.md)

### Scope
Fix NinjaTrader C# indicators để cải thiện win rate từ 22.7% → 35%+

### Components
```
1. SMC_Structure_OB_Only_v12_FVG_CHOCHFlags.cs
   ├── Review confluence requirements
   ├── Tighten CHoCH/BOS filters
   ├── Improve OB mitigation logic
   └── Better FVG quality scoring

2. SMCDeepSeekExporter_Enhanced.cs
   ├── Add confluence checker
   ├── Implement quality score calculator
   ├── Better risk/reward calculation
   └── Session/volatility filters

3. Volumdelta.cs
   ├── Validate delta calculations
   ├── Add divergence detection
   └── Volume profile integration
```

### Success Criteria
- [ ] Win rate ≥ 35% on backtest
- [ ] Average RR maintained at 2.5-3.0:1
- [ ] Quality score correlates with win rate
- [ ] Reduced false signals by 40%+

### Deliverables
1. ✅ Updated C# indicator files
2. ✅ Test report với before/after metrics
3. ✅ Documentation of changes
4. ✅ New export file for validation

---

## 📦 MODULE 2: DATA LABELING FIX
**Priority:** 🟠 HIGH
**Document:** [MODULE_2_DATA_LABELING.md](MODULE_2_DATA_LABELING.md)

### Scope
Fix labeling logic trong Python pipeline để model học đúng cách

### Components
```
1. build_all_enhanced_optimized.py
   ├── Fix line 797 labeling logic
   ├── Implement chosen option (A/B/C)
   ├── Add data quality checks
   └── Better prompt engineering

2. Data Regeneration
   ├── Run with new signal exports (from Module 1)
   ├── Apply new labeling logic
   ├── Validate distribution
   └── Create train/val splits

3. Data Validation
   ├── Check class balance
   ├── Verify signal-label consistency
   ├── Validate prompt quality
   └── Token length analysis
```

### Options to Choose
```
Option A (Recommended): Learn from ALL trades
  assistant = e["signal"]
  Pros: Maximum learning, natural distribution
  Cons: Includes low-quality setups

Option B: Quality-filtered
  assistant = e["signal"] if quality >= 85 else "skip"
  Pros: Higher quality data
  Cons: Smaller dataset

Option C: MFE-based filtering
  assistant = e["signal"] if mfe_rr >= 1.5 else "skip"
  Pros: Filters "bad luck" losses
  Cons: Complex logic
```

### Success Criteria
- [ ] Class distribution: LONG (30-35%), SHORT (30-35%), SKIP (30-40%)
- [ ] Signal-label consistency ≥ 80%
- [ ] No duplicate or malformed entries
- [ ] Token lengths within limits

### Deliverables
1. ✅ Updated build script
2. ✅ New train.jsonl & val.jsonl files
3. ✅ Data quality report
4. ✅ Labeling strategy justification document

---

## 📦 MODULE 3: TRAINING PIPELINE
**Priority:** 🟡 MEDIUM
**Document:** [MODULE_3_TRAINING_PIPELINE.md](MODULE_3_TRAINING_PIPELINE.md)

### Scope
Optimize training với class weights, better metrics, và comprehensive backtest

### Components
```
1. smc_train_optimized.py
   ├── Add class weights
   ├── Implement custom loss function
   ├── Add learning rate scheduler
   └── Better checkpoint strategy

2. Evaluation Metrics
   ├── Per-class precision/recall
   ├── Confusion matrix
   ├── ROC-AUC curves
   └── Confidence calibration

3. Backtesting
   ├── Simulate real trading
   ├── Calculate P&L metrics
   ├── Risk-adjusted returns
   └── Drawdown analysis
```

### Success Criteria
- [ ] Accuracy ≥ 70%
- [ ] F1 Long ≥ 0.60
- [ ] F1 Short ≥ 0.60
- [ ] Backtest Profit Factor ≥ 1.5
- [ ] Max Drawdown < 20%

### Deliverables
1. ✅ Updated training script
2. ✅ Trained model checkpoint
3. ✅ Comprehensive evaluation report
4. ✅ Backtest results với P&L curve

---

## 📅 TIMELINE & MILESTONES

### Phase 1: Planning & Setup (Current)
**Duration:** 1 day
**Status:** 🟡 IN PROGRESS

- [x] Complete dataset audit
- [x] Create master plan
- [x] Create module documents
- [x] Setup testing environment
- [ ] Baseline measurements

### Phase 2: Module 1 - Signal Quality (Critical)
**Duration:** 3-5 days
**Status:**  IN PROGRESS

- [x] Analyze current indicator logic
- [x] Design improvements
- [x] Implement changes (fix01-06 updated, tests passing)
- [ ] Test on historical data
- [ ] Validate win rate improvement
- [ ] **REVIEW CHECKPOINT #1**

### Phase 3: Module 2 - Data Labeling
**Duration:** 2-3 days
**Status:** ⚪ NOT STARTED

- [ ] Choose labeling strategy (A/B/C)
- [ ] Update build script
- [ ] Regenerate dataset
- [ ] Validate data quality
- [ ] **REVIEW CHECKPOINT #2**

### Phase 4: Module 3 - Training Pipeline
**Duration:** 3-4 days
**Status:** ⚪ NOT STARTED

- [ ] Implement class weights
- [ ] Setup new metrics
- [ ] Train model (multiple runs)
- [ ] Run backtests
- [ ] **REVIEW CHECKPOINT #3**

### Phase 5: Integration & Deployment
**Duration:** 1-2 days
**Status:** ⚪ NOT STARTED

- [ ] Final integration testing
- [ ] Documentation updates
- [ ] Deployment preparation
- [ ] **FINAL REVIEW**

**Total Estimated Duration:** 10-15 days

---

## ✅ QUY TRÌNH REVIEW

### Review Checkpoints

**Module Review Process:**
```
1. SELF-REVIEW (By Developer)
   ├── Code quality check
   ├── Test coverage validation
   ├── Documentation completeness
   └── Metrics vs. success criteria

2. TECHNICAL REVIEW (Expert Validation)
   ├── Logic correctness
   ├── Best practices compliance
   ├── Performance optimization
   └── Edge case handling

3. INTEGRATION TEST
   ├── Test with previous modules
   ├── End-to-end workflow
   ├── Data pipeline validation
   └── Performance benchmarks

4. SIGN-OFF
   ├── All success criteria met? ✅
   ├── Documentation complete? ✅
   ├── Ready for next module? ✅
   └── Approved to proceed
```

### Review Criteria Matrix

| Criteria | Module 1 | Module 2 | Module 3 |
|----------|----------|----------|----------|
| Code Quality | ✅ | ✅ | ✅ |
| Test Coverage | ✅ | ✅ | ✅ |
| Documentation | ✅ | ✅ | ✅ |
| Performance | ✅ | ✅ | ✅ |
| Metrics Hit | ✅ | ✅ | ✅ |

### Rollback Strategy

```
IF (module fails review) THEN:
  1. Document failure reasons
  2. Create fix plan
  3. Implement fixes
  4. Re-test
  5. Request re-review
ENDIF

IF (cannot fix in reasonable time) THEN:
  1. Rollback to previous stable version
  2. Re-evaluate approach
  3. Consider alternative solutions
ENDIF
```

---

## 📊 SUCCESS METRICS

### Baseline (Current State)
```
Signal Quality:
├── Win Rate:           22.7% ❌
├── Avg RR:             3:1 ✅
└── Quality Score:      75-95 (uncalibrated) ⚠️

Model Performance:
├── Accuracy:           50.99% ❌
├── F1 Long:            0.00 ❌
├── F1 Short:           0.00 ❌
├── F1 Skip:            0.68 ⚠️
└── Training Time:      182 min ✅

Data Quality:
├── Class Balance:      1:2:2 (skip:long:short) ⚠️
├── Win/Loss Ratio:     1:3.4 ❌
└── Dataset Size:       6,841 train, 761 val ✅
```

### Target (After All Modules)
```
Signal Quality:
├── Win Rate:           ≥35% ✅
├── Avg RR:             2.5-3.0:1 ✅
└── Quality Score:      Calibrated, correlated ✅

Model Performance:
├── Accuracy:           ≥70% ✅
├── F1 Long:            ≥0.60 ✅
├── F1 Short:           ≥0.60 ✅
├── Macro F1:           ≥0.60 ✅
└── Training Time:      <4 hours ✅

Backtest Results:
├── Profit Factor:      ≥1.5 ✅
├── Win Rate:           35-45% ✅
├── Avg Win/Loss:       ≥2.5:1 ✅
├── Max Drawdown:       <20% ✅
└── Sharpe Ratio:       ≥1.5 ✅
```

### Tracking Dashboard

```
Module 1 Target: Win Rate 35%+
├── Current: 22.7%
├── Target: 35.0%
 Progress: [###-------] 30%
 Status: IN PROGRESS

Module 2 Target: Balanced Dataset
├── Current: 77% skip (imbalanced)
├── Target: 30-40% each class
├── Progress: [░░░░░░░░░░░░░░░░░░░░] 0%
└── Status: NOT STARTED

Module 3 Target: 70%+ Accuracy
├── Current: 50.99%
├── Target: 70.0%
├── Progress: [░░░░░░░░░░░░░░░░░░░░] 0%
└── Status: NOT STARTED
```

---

## 🔧 DEPENDENCIES & PREREQUISITES

### Software Requirements
```
NinjaTrader 8:
├── Version: 8.0.28+
├── License: Active
└── Data: Historical tick data available

Python Environment:
├── Python: 3.9+
├── PyTorch: 2.0+
├── Transformers: 4.30+
├── NumPy, Pandas, etc.
└── CUDA: 11.8+ (for GPU training)

Development Tools:
├── VSCode or similar IDE
├── Git for version control
└── Testing framework (pytest)
```

### Data Requirements
```
Historical Data:
├── Symbols: 6E, 6B, ES, NQ, etc.
├── Timeframe: M1 (with M5, M15 context)
├── Period: Minimum 3 months
├── Quality: Clean, no gaps
└── Volume: Order flow data available

Export Files:
├── deepseek_smc_events.jsonl (source)
├── train.jsonl (processed)
├── val.jsonl (processed)
└── Backup of original data
```

### Knowledge Requirements
```
Domain Expertise:
├── SMC Trading Concepts ✅
├── NinjaTrader C# Development ✅
├── Python ML Pipeline ✅
├── DeepSeek Model Architecture ✅
└── Risk Management ✅

Technical Skills:
├── C# Programming ✅
├── Python Programming ✅
├── PyTorch/Transformers ✅
├── Data Analysis ✅
└── Backtesting ✅
```

---

## ⚠️ RISK MANAGEMENT

### Identified Risks

**RISK #1: Module 1 Cannot Achieve 35% Win Rate**
```
Impact: HIGH
Probability: MEDIUM
Mitigation:
  ├── Have fallback to 30% win rate
  ├── Consider longer data collection period
  ├── May need to adjust RR ratio
  └── Consult additional SMC experts

Contingency:
  IF win_rate < 30% AFTER 5 days THEN:
    → Pause project
    → Re-evaluate signal strategy
    → Consider alternative approaches
```

**RISK #2: Labeling Strategy Choice Wrong**
```
Impact: MEDIUM
Probability: LOW
Mitigation:
  ├── Test all 3 options (A/B/C)
  ├── Quick prototype before full regeneration
  ├── Validate on small sample first
  └── Keep old dataset as backup

Contingency:
  IF results poor AFTER labeling change THEN:
    → Try alternative option
    → A/B test different strategies
    → Hybrid approach
```

**RISK #3: Training Time Too Long**
```
Impact: LOW
Probability: MEDIUM
Mitigation:
  ├── Use smaller model initially
  ├── Optimize data loading
  ├── Consider cloud GPU (SaladCloud)
  └── Implement early stopping

Contingency:
  IF training > 6 hours PER epoch THEN:
    → Reduce sequence length
    → Use model distillation
    → Smaller batch size
```

**RISK #4: Overfitting on Training Data**
```
Impact: MEDIUM
Probability: MEDIUM
Mitigation:
  ├── Monitor train/val gap
  ├── Use dropout and regularization
  ├── More aggressive early stopping
  └── Cross-validation

Contingency:
  IF val_loss > train_loss * 1.2 THEN:
    → Increase dropout
    → Add more regularization
    → Get more diverse data
```

---

## 📚 DOCUMENTATION STRUCTURE

### Module Documents
```
MODULE_1_SIGNAL_QUALITY.md
├── Current State Analysis
├── Improvement Strategies
├── Implementation Plan
├── Testing Procedures
├── Success Metrics
└── Sign-Off Checklist

MODULE_2_DATA_LABELING.md
├── Labeling Strategy Options
├── Implementation Details
├── Data Regeneration Steps
├── Validation Procedures
├── Success Metrics
└── Sign-Off Checklist

MODULE_3_TRAINING_PIPELINE.md
├── Training Configuration
├── Evaluation Metrics
├── Backtesting Procedures
├── Performance Analysis
├── Success Metrics
└── Sign-Off Checklist
```

### Supporting Documents
```
├── DATASET_EXPERT_AUDIT_REPORT.md (Complete ✅)
├── PROJECT_MASTER_PLAN.md (This file ✅)
├── CHANGELOG.md (Track all changes)
├── LESSONS_LEARNED.md (Post-project review)
└── API_DOCUMENTATION.md (If needed)
```

---

## 🎬 GETTING STARTED

### Immediate Next Steps

**TODAY (November 20, 2025):**
1. ✅ Read this master plan thoroughly
2. ✅ Review the audit report again
3. ⬜ Read MODULE_1_SIGNAL_QUALITY.md
4. ⬜ Setup development environment
5. ⬜ Take baseline measurements

**TOMORROW:**
1. ⬜ Start Module 1 implementation
2. ⬜ Analyze current indicator logic
3. ⬜ Design improvement strategies
4. ⬜ Begin coding changes

### Communication Protocol
```
Daily Updates:
├── What was completed today
├── What will be done tomorrow
├── Any blockers or issues
└── Metrics update

Weekly Reviews:
├── Progress vs. timeline
├── Metrics vs. targets
├── Risk assessment update
└── Adjust plan if needed
```

---

## ✅ APPROVAL & SIGN-OFF

### Master Plan Approval

**Reviewed By:** _______________________
**Date:** _______________________
**Approved:** [ ] YES  [ ] NO
**Comments:**

---

### Module Completion Sign-Off

**Module 1:**
- [ ] All success criteria met
- [ ] Tests passed
- [ ] Documentation complete
- [ ] Ready for Module 2

**Module 2:**
- [ ] All success criteria met
- [ ] Tests passed
- [ ] Documentation complete
- [ ] Ready for Module 3

**Module 3:**
- [ ] All success criteria met
- [ ] Tests passed
- [ ] Documentation complete
- [ ] Ready for deployment

---

## 📞 CONTACT & SUPPORT

**Project Lead:** SMC & ML Expert
**Support:** Available 24/7 for critical issues
**Documentation:** All files in `/Trainmodel` directory

---

**Version History:**
- v1.0.0 (2025-11-20): Initial master plan created

**Last Updated:** November 20, 2025

---

## 🚀 LET'S BUILD A PROFITABLE TRADING MODEL!

Remember the golden rule:
> "Measure twice, cut once. Test thoroughly, deploy confidently."

Good luck! 💪