# vis.py - MGann Swing Visualizer

**Location:** `C:\Users\Administrator\Desktop\plantrainAI\vis.py`  
**Type:** Visualization tool for Module 14 outputs  
**Status:** ✅ Working

---

## Overview

`vis.py` creates interactive Plotly charts visualizing MGann swing detection with:
- Price candlesticks
- Zigzag swing line
- Wave strength color coding (delta-based, separate normalization for up/down waves)
- Delta sum labels at swing pivots (filtered by significance)
- BOS/CHoCH horizontal lines at key levels

---

## Usage

```bash
python vis.py --input module14_results.json --start 0 --end 200
python vis.py --input module14_results.json --start 0 --end 200 --min-delta 100 --min-bars 10
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--input` | str | **required** | Path to JSON file with bar data (must have Module 14 outputs) |
| `--start` | int | 0 | Start bar index |
| `--end` | int | all | End bar index |
| `--min-delta` | int | 50 | Minimum absolute delta to show label on chart |
| `--min-bars` | int | 5 | Minimum bars in wave to show label |

---

## Required Input Fields

Data file must contain Module 14 processed bars with:

**Swing Detection:**
- `mgann_internal_swing_high` - Swing high levels
- `mgann_internal_swing_low` - Swing low levels
- `mgann_internal_leg_dir` - Leg direction (1/-1/0)

**Structure Events:**
- `ext_bos_up` / `ext_bos_down` - Break of Structure markers
- `ext_choch_up` / `ext_choch_down` - Change of Character markers

**Delta Data:**
- `delta` - Bar delta (buy - sell volume)

**OHLC:**
- `open`, `high`, `low`, `close`, `timestamp`

---

## Chart Output

### Features

1. **Candlesticks** - Green/Red price bars
2. **Zigzag Line** - Orange line connecting swing pivots
3. **Wave Strength Markers** - Color-coded dots at pivots:
   - Red (0) → Yellow (50) → Green (100)
   - Separate normalization for upwaves vs downwaves
4. **Delta Labels** - Shows accumulated delta for each wave (filtered)
   - Blue labels = Upward waves (positive delta)
   - Red labels = Downward waves (negative delta)
5. **BOS/CHoCH Lines** - Horizontal dashed lines at breakout levels
   - Green = BOS Up
   - Red = BOS Down
   - Cyan = CHoCH Up
   - Orange = CHoCH Down

### Output Location

Charts saved to: `charts/visual_mgann_{start}_{end}.html`

---

## Delta Label Filtering

Only significant waves are labeled to avoid chart clutter:

```python
# Show label only if:
abs(delta_sum) >= min_delta AND wave_length >= min_bars

# Example:
--min-delta 50   # Only show waves with |delta| >= 50
--min-bars 5     # Only show waves >= 5 bars long
```

**Recommended filters:**
- Scalping/1min: `--min-delta 30 --min-bars 3`
- Day trading/5min: `--min-delta 50 --min-bars 5` (default)
- Swing/15min+: `--min-delta 100 --min-bars 10`

---

## Wave Strength Calculation

```python
# For each wave (swing to swing):
delta_sum = sum(bar['delta'] for bar in wave_bars)
wave_type = 'up' if delta_sum > 0 else 'down'

# Normalize SEPARATELY for up and down waves
if wave_type == 'up':
    strength = (delta_sum / max_upwave_delta) * 100
else:
    strength = (abs(delta_sum) / max_downwave_delta) * 100
```

**Why separate normalization?**
- Upwaves and downwaves have different characteristics
- Prevents one type dominating the color scale
- More accurate representation of relative strength within wave type

---

## Example Output

```
✓ Loaded 200 bars
✅ Saved: charts/visual_mgann_0_200.html
   Filter: delta ≥ 50, wave ≥ 5 bars
```

---

## Integration with Module 14

`vis.py` reads directly from Module 14 outputs:

```python
# Module 14 processes raw data:
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

mgann = Fix14MgannSwing()
for bar in raw_data:
    bar = mgann.process_bar(bar)
    
# Save to JSON:
with open('module14_results.json', 'w') as f:
    json.dump(processed_data, f)

# Visualize:
python vis.py --input module14_results.json --start 0 --end 500
```

---

## Comparison with Other Visualizers

| Tool | Purpose | Features |
|------|---------|----------|
| `vis.py` | **Main visualizer** | Zigzag + delta labels + BOS/CH lines + filters |
| `visualize_module14_wave_strength.py` | Debug table | Text table of leg progression, wave metrics |
| ~~`visualizer_mgann_plotly.py`~~ | *Deprecated* | Deleted (corrupted file) |

Use `vis.py` as the **primary visualization tool**.

---

## Troubleshooting

### "No zigzag drawn"
- Check data has `mgann_internal_leg_dir` field
- Verify Module 14 processed the data
- Check if leg_dir values are non-zero

### "No delta labels shown"
- Reduce `--min-delta` threshold
- Reduce `--min-bars` threshold
- Check data has `delta` field populated

### "Missing BOS/CHoCH lines"
- Verify data has `ext_bos_up/down`, `ext_choch_up/down` fields
- Check if structure events exist in selected range

---

## Future Enhancements

Potential additions:
- [ ] Leg number annotations (1, 2, 3...) at pivots
- [ ] pb_wave_strength_ok markers (gold diamonds)
- [ ] FVG zone rectangles
- [ ] Multi-timeframe overlay (M5 context on M1 chart)

---

**Status:** Production ready  
**Version:** 1.0  
**Last Updated:** 2025-11-25
