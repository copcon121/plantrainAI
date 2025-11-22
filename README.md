# SMC INDICATOR - MODULE-BASED ARCHITECTURE

**Version:** 2.1.0  
**Status:** In Development  
**Approach:** 12 independent modules

---

## IMPORTANT DESIGN DECISION (Nov 2025)

### Signal Type: FVG ONLY

**Previous (deprecated):**
- FVG retest và OB retest là hai loại tín hiệu riêng (`fvg_retest_bull/bear`, `ob_ext_retest_bull/bear`).

**Hiện tại:**
- **Chỉ dùng FVG retest làm tín hiệu.**
- **OB là ngữ cảnh, không phải tín hiệu** → cung cấp feature chất lượng cho sự kiện FVG.
- Model học: `fvg_retest_bull`, `fvg_retest_bear` + các trường context của OB.

**Lý do:**
1. Entry thực tế chủ yếu là FVG retest (OB là “nguồn” của leg, không phải điểm vào riêng).
2. OB retest chỉ ~6% dữ liệu và dễ gây phân mảnh nhãn.
3. Cùng một pattern nhưng nhãn khác làm model nhiễu.
4. Mục tiêu ML đơn giản hơn: FVG + long/short/skip.

**Ví dụ sự kiện FVG kèm context OB:**
```python
{
    "signal_type": "fvg_retest_bull",
    "has_ob_in_leg": true,
    "ob_overlap_ratio": 0.7,
    "ob_is_m5_hl": true,
    "ob_strength_score": 0.85
}
```

---

## OVERVIEW

Hệ thống SMC trading được tái cấu trúc theo kiến trúc module-based.

**Mục tiêu chính:** đạt win rate 35%+ thông qua quality scoring và filtering.  
**Kiến trúc 3 lớp:**
```
Layer 1: Lightweight Indicator (C# - real-time)
Layer 2: Data Processor (Python - batch/offline)
Layer 3: ML Training Pipeline (Python)
```

---

## FOLDER STRUCTURE

```
SMC_indicator/
├─ README.md                  (tệp này)
├─ ARCHITECTURE.md            (kiến trúc chi tiết)
├─ PROJECT_MASTER_PLAN.md     (kế hoạch tổng)
│
├─ indicators/                (Layer 1: NinjaTrader C#)
│   ├─ SMC_Structure_Lightweight.cs
│   ├─ Volumdelta.cs
│   └─ SMC_RawExporter.cs
│
├─ processor/                 (Layer 2: Python)
│   ├─ core/
│   │   ├─ bar_state.py       (BarState dataclass)
│   │   └─ event_state.py     (EventState dataclass)
│   ├─ smc_processor.py       (Main processor)
│   └─ modules/               (các module độc lập)
│       ├─ fix01_ob_quality.py
│       ├─ fix02_fvg_quality.py
│       ├─ fix03_choch_filters.py
│       └─ ... (tới fix11_liquidity_map.py)
```

---

## MODULE LIST (SUMMARY)

- **#01 OB Quality:** t?nh ?i?m ch?t l??ng OB l?m context cho FVG.
- **#02 FVG Quality (PRIMARY):** ph?t hi?n v? ch?m ?i?m FVG.
- **#03 Structure Context:** tag expansion/retracement/continuation.
- **#04 Confluence:** k?t h?p ?i?m c?a c?c module.
- **#05 Stop Placement:** ch?n stop t?i ?u (FVG edge/full, OB, structure).
- **#06 Target Placement:** ??t TP d?a swing/liquidity.
- **#07 Market Condition:** ph?n lo?i regime (trend/range, vol cao/th?p).
- **#08 Volume Divergence:** divergence delta t?i swing.
- **#09 Volume Profile:** VAH/VAL/POC ph?c v? thanh kho?n/target.
- **#10 MTF Alignment:** ki?m tra ??ng pha khung cao.
- **#11 Liquidity Map:** map thanh kho?n, sweep detection.
- **#12 FVG Retest Filter (NEW):** l?c/gate FVG retest (edge/shallow/deep/no_touch/break), xu?t `signal_type=fvg_retest_*`.

---

## DEFAULT PIPELINE ORDER (BACKTEST & PROCESSOR)

1) Volume Profile (#09)  
2) Liquidity Map (#11)  
3) Market Condition (#07)  
4) MTF Alignment (#10)  
5) OB Quality (#01)  
6) FVG Retest Filter (#12)  
7) FVG Quality (#02)  
8) Structure Context (#03)  
9) Stop Placement (#05)  
10) Target Placement (#06)  
11) Volume Divergence (#08)  
12) Confluence (#04)

Backtest runner `python -m processor.backtest.run_module_backtest` dùng thứ tự trên (đã cập nhật).

---

## NEXT STEPS BEFORE CODING

1. Sửa encoding UTF-8 cho toàn bộ docs, loại ký tự hỏng.  
2. Chốt hợp đồng dữ liệu export (thêm symbol/expiry/timezone/tick_size/point_value/session markers/EQH/EQL/VAH/VAL).  
3. Thêm JSON schema + validator cho `raw_smc_export.jsonl`.  
4. Dựng skeleton Python Layer 2/3 (core + modules + tests).  
5. Quyết định chiến lược labeling (Option A/B) bằng pilot nhỏ trước khi regen dataset.  
6. Đặt kỷ luật backtest/walk-forward cho từng thay đổi module.
