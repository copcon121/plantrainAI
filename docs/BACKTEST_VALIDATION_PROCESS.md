# BACKTEST & WALK-FORWARD VALIDATION PROCESS

**Purpose:** Quy trình chuẩn để kiểm chứng từng module trước khi đưa vào hệ thống.  
**Scope:** Áp dụng cho mọi module `fix{nn}` (score/logic) và các thay đổi lớn.

---

## 1) PIPELINE TỔNG QUAN

```
+-----------------------------------------------------+
|              MODULE VALIDATION PIPELINE             |
+-----------------------------------------------------+
| Step 1: UNIT TEST (Code correctness)               |
|        |                                           |
|        v                                           |
| Step 2: IN-SAMPLE BACKTEST (Does it work?)         |
|        |  - 70% data                               |
|        |  - Check: corr > 0.3, PF > 1.2            |
|        v                                           |
| Step 3: OUT-OF-SAMPLE TEST (Generalize?)           |
|        |  - 30% data (never seen)                  |
|        |  - Check: metrics degrade <= 20%          |
|        v                                           |
| Step 4: WALK-FORWARD (Robust over time?)           |
|        |  - 5 folds, rolling                       |
|        |  - Check: consistent across folds         |
|        v                                           |
| Step 5: SIGN-OFF or REJECT                         |
+-----------------------------------------------------+
```

---

## 2) METRICS TỐI THIỂU

| Metric | Threshold | Ý nghĩa |
|--------|-----------|---------|
| Score-WinRate Corr | > 0.3 | Điểm module phải tương quan với outcome |
| Profit Factor (PF) | > 1.2 in-sample, > 1.0 OOS | Lợi nhuận gộp / lỗ gộp |
| Max Drawdown (DD) | < 25% | Giới hạn sụt giảm |
| Win Rate Delta | > +3% vs baseline | Cải thiện so với không dùng module |
| Sharpe Ratio | > 0.5 | Risk-adjusted return |

---

## 3) CHI TIẾT TỪNG BƯỚC

### Step 1: Unit Test
- Mỗi module PHẢI có unit test.
- Chạy:  
  `pytest tests/test_fix{nn}.py -v --cov=modules/fix{nn} --cov-fail-under=80`

### Step 2: In-Sample Backtest (70% data)
- Dữ liệu: `data/train_70pct.jsonl`
- Lệnh mẫu:  
  `python backtest/run_module_backtest.py --module fix{nn} --data data/train_70pct.jsonl --output results/fix{nn}_insample.json`
- Pass:
  - Corr(score, outcome) > 0.3
  - PF > 1.2
  - Win rate improvement > 3%

### Step 3: Out-of-Sample Test (30% data)
- Dữ liệu: `data/test_30pct.jsonl`
- Lệnh mẫu:  
  `python backtest/run_module_backtest.py --module fix{nn} --data data/test_30pct.jsonl --output results/fix{nn}_oos.json`
- Pass:
  - Metrics không giảm > 20% so với in-sample
  - PF > 1.0

### Step 4: Walk-Forward (5 folds)

Phiên đào tạo/kiểm thử cuốn chiếu:
```
Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5
Train  | Test   |        |        |        <- Round 1
Train  | Train  | Test   |        |        <- Round 2
Train  | Train  | Train  | Test   |        <- Round 3
Train  | Train  | Train  | Train  | Test   <- Round 4
```
- Lệnh mẫu:  
  `python backtest/walk_forward.py --module fix{nn} --folds 5 --output results/fix{nn}_wf.json`
- Pass:
  - PF dương ở >= 4/5 folds
  - Không fold nào PF < 0.8
  - Trung bình trong 1 std của mean

### Step 5: Sign-Off
- Quyết định: APPROVED / CONDITIONAL / REJECTED dựa trên checklist.

---

## 4) SIGN-OFF CHECKLIST (Module {nn})

### Unit Tests
- [ ] All tests pass
- [ ] Coverage >= 80%

### In-Sample (70%)
- [ ] Correlation > 0.3: ___
- [ ] PF > 1.2: ___
- [ ] Win Rate Delta > +3%: ___
- [ ] Max DD < 25%: ___

### Out-of-Sample (30%)
- [ ] Degradation < 20%: ___
- [ ] PF > 1.0: ___

### Walk-Forward (5 folds)
- [ ] 4/5 folds PF > 0
- [ ] No fold PF < 0.8
- [ ] Consistent across time: ___

### Decision
- [ ] APPROVED - Add to production
- [ ] CONDITIONAL - Need tuning (specify: ___)
- [ ] REJECTED - Does not improve system

Signed: _____________    Date: ___________

---

## 5) QUICK WORKFLOW (SAU KHI BUILD XONG MODULE)

1. **Export từ Ninja (C# exporter Enhanced)**  
   - Chạy chart, exporter viết JSONL theo ngày vào `NinjaTrader 8/smc_exports_enhanced` (đã có pulse `fvg_detected`, `fvg_active`, HTF/DI, sweep...).  

2. **Chạy pipeline Python (module #01-#12 đầy đủ)**  
   - Runner:  
     `python -m processor.backtest.run_module_backtest --inputs path/to/day.jsonl --output processor/backtest/results/day.enriched.jsonl --summary processor/backtest/results/day.summary.json`  
   - Kết quả: `.summary.json` (tỷ lệ FVG/sweep…), `.enriched.jsonl` (đủ field stop/target/confluence/mtf/retest...).  

3. **Lọc tín hiệu & tính PF/winrate nhanh**  
   - Script: `python -m processor.backtest.eval_filtered_signals --inputs processor/backtest/results/*.enriched.jsonl --max-lookahead 50`  
   - Filter mặc định: FVG Retest edge/shallow, `fvg_retest_quality_score >= 0.6`, `signal_type=fvg_retest_*`, yêu cầu `mtf_is_aligned`; confluence tối thiểu 0 (có thể siết lên 0.08–0.1), market_condition không ràng buộc (có thể giới hạn trend/balanced).  
   - TP/SL: dùng stop/target nếu có; nếu thiếu, fallback SL = mép FVG, TP = 3R.  

4. **Siết/giãn filter để tối ưu PF**  
   - Tăng `fvg_retest_quality_score`, `confluence_score`, giới hạn `market_condition`, hoặc nâng lookahead. Rerun script bước 3 để xem PF/winrate thay đổi.  

5. **Lặp lại khi cập nhật code/export**  
   - Sau khi chỉnh indicator/module, export lại, chạy pipeline (bước 2) rồi đánh giá (bước 3/4).  

> Mục tiêu: PF ≥ 1.5, winrate ~25–35% sau filter; nếu thấp, kiểm tra dữ liệu export (stop/target), ngưỡng filter, hoặc logic module.  

### Quick sanity check trước khi backtest
- **Pytest toàn bộ (bao gồm module #12):**  
  `python -m pytest processor/tests -v`  
  (hoặc chạy riêng test mới: `python -m pytest processor/tests/test_fix12_fvg_retest.py -v`)
- **Smoke pipeline trên file export mới:**  
  `python -m processor.tests.test_modules_smoke`  
  (hoặc đơn giản: `python -m pytest processor/tests/test_modules_smoke.py -v`)  
  Mục tiêu: không crash, các field chính (fvg/ob/htf/liquidity) không rỗng/0 bất thường.
