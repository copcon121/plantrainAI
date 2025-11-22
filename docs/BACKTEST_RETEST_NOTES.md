# FVG Retest - Raw Export Evaluation Notes

## Run: eval_retest_raw (TP=3R, SL = fvg_creation_high/low ±1 tick, lookahead 50)
Date: latest re-export after adding sweep & HTF BOS/CHOCH to exporter.

| File | Trades | Wins | Losses | Open | Winrate % | PF | Avg RR |
|------|--------|------|--------|------|-----------|----|--------|
| 2025-09-01 | 11 | 1 | 10 | 0 | 9.09 | 0.30 | -0.636 |
| 2025-09-02 | 49 | 16 | 33 | 0 | 32.65 | 1.455 | 0.306 |
| 2025-09-03 | 53 | 14 | 37 | 2 | 26.42 | 1.135 | 0.094 |
| 2025-09-04 | 72 | 22 | 50 | 0 | 30.56 | 1.320 | 0.222 |
| 2025-09-05 | (no signals / not exported in this run) |

Notes:
- SL dùng low/high nến tạo gap +1 tick; TP = 3R. Only BOS/CHOCH opposite direction as context (module #12).
- 09/02 cải thiện PF (~1.45), các ngày khác trung bình, 09/01 yếu.
- Chưa có stop/TP chuẩn từ module 05/06 (fallback 3R).

Next ideas to try:
- Xuất stop/TP chuẩn (module #05/06) và dùng thay fallback 3R.
- Thêm filter market_condition/confluence ngay trên raw.
- Điều chỉnh lookahead hoặc R-multiple nếu cần.
