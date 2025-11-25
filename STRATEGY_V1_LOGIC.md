# STRATEGY V1 - LOGIC BREAKDOWN

**File:** `processor/modules/fix16_strategy_v1.py`
**Version:** v1.1.0
**Purpose:** Generate LONG/SHORT signals based on SMC + MGann Swing

---

## 📊 OVERVIEW

Strategy V1 tìm entry opportunities khi:
1. **CHoCH** xảy ra (cấu trúc thị trường thay đổi)
2. **Pullback** về vùng FVG trong **Leg 1** hoặc **Leg 2**
3. Price **retest FVG zone** = Entry signal

---

## 🎯 LONG SIGNAL LOGIC

### Visual Flow:

```
📉 DOWNTREND
    ↓
🔄 CHoCH DOWN (Structure break - reversal signal)
    ↓
📈 Price reclaims UP (starts uptrend)
    ↓
⬆️ LEG 1 Impulse UP (creates Bullish FVG)
    ↓
⬇️ Pullback (weak delta)
    ↓
🎯 Price enters FVG zone = ENTRY LONG!
```

### Code Logic (Lines 103-181):

```python
def _check_long_conditions(bar_state):
    """
    Returns (True, fvg_info) if LONG signal valid
    """

    # ✅ CONDITION 1: Must be in Leg 1 pullback
    leg = bar_state.get('mgann_leg_index', 0)
    if leg != 1:
        return False, None

    # ✅ CONDITION 1.5: Pullback zone filter
    # Entry must be ABOVE last_swing_low
    # (Ensures we enter in pullback, not at CHoCH breakout level)
    entry_price = bar_state.get('close', 0)
    last_swing_low = bar_state.get('last_swing_low', None)

    if last_swing_low and entry_price <= last_swing_low:
        return False, None  # Too close to breakout = rejected

    # ✅ CONDITION 2: Early leg (1 or 2)
    early_leg = 0 < leg <= 2
    if not early_leg:
        return False, None

    # NOTE: Condition 3 (pb_wave_strength_ok) DISABLED for testing

    # ✅ CONDITION 4: FVG Entry
    fvg_new = bar_state.get('fvg_detected', False)
    fvg_bullish = bar_state.get('fvg_type') == 'bullish'

    if fvg_new and fvg_bullish:
        # NEW FVG created = Immediate signal
        fvg_top = bar_state.get('fvg_top', 0)
        fvg_bottom = bar_state.get('fvg_bottom', 0)
        self._add_fvg(fvg_top, fvg_bottom, 'bullish')
        return True, {'top': fvg_top, 'bottom': fvg_bottom, 'new': True}

    # Check RETEST of existing FVG
    price = bar_state.get('close', 0)
    can_signal, fvg_zone = self._check_fvg_retest(price, 'bullish')

    if can_signal:
        return True, {'top': fvg_zone['top'], 'bottom': fvg_zone['bottom'], 'new': False}

    return False, None
```

### Real Example từ Test Results:

```
Signal #2: LONG
  Bar Index: 8
  Timestamp: 2025-10-23T00:08:00.000Z

  Setup:
    - Leg: 1 (early entry) ✅
    - FVG: NEW (first signal) ✅
    - FVG Zone: $4074.30 - $4079.10
    - Entry above last_swing_low ✅

  Trade:
    Entry: $4108.00
    SL:    $4074.10 (Leg low - 1 tick)
    TP:    $4209.70 (3R)
    Risk:  $33.90
```

---

## 🎯 SHORT SIGNAL LOGIC

### Visual Flow:

```
📈 UPTREND
    ↓
🔄 CHoCH UP (Structure break - reversal signal)
    ↓
📉 Price reclaims DOWN (starts downtrend)
    ↓
⬇️ LEG 1 Impulse DOWN (creates Bearish FVG)
    ↓
⬆️ Pullback (weak delta)
    ↓
🎯 Price enters FVG zone = ENTRY SHORT!
```

### Code Logic (Lines 183-238):

Tương tự LONG nhưng ngược lại:

```python
def _check_short_conditions(bar_state):
    """
    Returns (True, fvg_info) if SHORT signal valid
    """

    # ✅ CONDITION 1: Must be in Leg 1 pullback
    leg = bar_state.get('mgann_leg_index', 0)
    if leg != 1:
        return False, None

    # ✅ CONDITION 1.5: Pullback zone filter
    # Entry must be BELOW last_swing_high
    entry_price = bar_state.get('close', 0)
    last_swing_high = bar_state.get('last_swing_high', None)

    if last_swing_high and entry_price >= last_swing_high:
        return False, None  # Too close to breakout = rejected

    # ✅ CONDITION 2: Early leg (1 or 2)
    early_leg = 0 < leg <= 2
    if not early_leg:
        return False, None

    # ✅ CONDITION 4: FVG Entry
    fvg_new = bar_state.get('fvg_detected', False)
    fvg_bearish = bar_state.get('fvg_type') == 'bearish'

    if fvg_new and fvg_bearish:
        # NEW FVG = Immediate signal
        fvg_top = bar_state.get('fvg_top', 0)
        fvg_bottom = bar_state.get('fvg_bottom', 0)
        self._add_fvg(fvg_top, fvg_bottom, 'bearish')
        return True, {'top': fvg_top, 'bottom': fvg_bottom, 'new': True}

    # Check RETEST
    price = bar_state.get('close', 0)
    can_signal, fvg_zone = self._check_fvg_retest(price, 'bearish')

    if can_signal:
        return True, fvg_zone

    return False, None
```

### Real Example:

```
Signal #1: SHORT
  Bar Index: 3
  Timestamp: 2025-10-23T00:03:00.000Z

  Setup:
    - Leg: 1 (early entry) ✅
    - FVG: NEW (first signal) ✅
    - FVG Zone: $4138.30 - $4143.00
    - Entry below last_swing_high ✅

  Trade:
    Entry: $4110.90
    SL:    $4143.20 (Leg high + 1 tick)
    TP:    $4014.00 (3R)
    Risk:  $32.30
```

---

## 🔄 FVG TRACKING SYSTEM

### Purpose:
Limit số signals từ cùng 1 FVG zone = avoid over-trading

### Logic (Lines 66-101):

```python
# State management
self.active_fvgs = []  # Track all active FVG zones

def _add_fvg(self, top, bottom, fvg_type):
    """Add new FVG when detected"""
    self.active_fvgs.append({
        'top': top,
        'bottom': bottom,
        'type': fvg_type,
        'signal_count': 1,  # NEW FVG = first signal
        'bar_created': self.bar_count,
    })

def _check_fvg_retest(self, price, fvg_type):
    """
    Check if price retests existing FVG.
    Returns (can_signal, fvg_zone)
    """
    for fvg in self.active_fvgs:
        if fvg['type'] != fvg_type:
            continue

        # Price in FVG zone?
        if fvg['bottom'] <= price <= fvg['top']:
            if fvg['signal_count'] < 3:  # Max 3 signals per FVG
                fvg['signal_count'] += 1
                return True, fvg
            else:
                return False, fvg  # Already 3 signals = reject

    return False, None

def _cleanup_old_fvgs(self, max_age=100):
    """Remove FVGs older than 100 bars"""
    self.active_fvgs = [
        fvg for fvg in self.active_fvgs
        if self.bar_count - fvg['bar_created'] < max_age
    ]
```

### Example:

```
Bar 25: FVG Zone $4091.90 - $4096.40 created
  → Signal #5 (NEW) ✅ signal_count = 1

Bar 30: Price retests $4093.30 (in zone)
  → Signal #6 (RETEST) ✅ signal_count = 2

Bar 31: Price retests $4094.00 (still in zone)
  → Signal #7 (RETEST) ✅ signal_count = 3

Bar 35: Price retests $4095.00 (still in zone)
  → REJECTED ❌ (already 3 signals)
```

---

## 💰 RISK MANAGEMENT

### LONG Trade Calculation (Lines 240-270):

```python
def _calculate_long_trade(bar_state, fvg_info):
    """
    Entry: Close price at signal bar
    SL: Leg low - 1 tick
    TP: Entry + 3R
    """
    entry = bar_state.get('close', 0)

    # Stop Loss at leg extreme (NOT FVG edge)
    leg_low = bar_state.get('mgann_leg_low')

    if leg_low is not None:
        sl = leg_low - (1 * 0.1)  # 1 tick below leg low
    else:
        # Fallback to FVG if no leg data
        sl = fvg_info['bottom'] - (2 * 0.1)  # 2 ticks below FVG

    # Calculate TP at 3:1 reward:risk
    risk = entry - sl
    tp = entry + (risk * 3.0)

    return {
        'direction': 'LONG',
        'entry': round(entry, 2),
        'sl': round(sl, 2),
        'tp': round(tp, 2),
        'risk': round(risk, 2),
        'reward': round(risk * 3.0, 2),
        'rr_ratio': 3.0,
    }
```

### SHORT Trade Calculation (Lines 272-302):

```python
def _calculate_short_trade(bar_state, fvg_info):
    """
    Entry: Close price
    SL: Leg high + 1 tick
    TP: Entry - 3R
    """
    entry = bar_state.get('close', 0)

    # Stop Loss at leg extreme
    leg_high = bar_state.get('mgann_leg_high')

    if leg_high is not None:
        sl = leg_high + (1 * 0.1)  # 1 tick above leg high
    else:
        sl = fvg_info['top'] + (2 * 0.1)

    risk = sl - entry
    tp = entry - (risk * 3.0)

    return {
        'direction': 'SHORT',
        'entry': round(entry, 2),
        'sl': round(sl, 2),
        'tp': round(tp, 2),
        'risk': round(risk, 2),
        'reward': round(risk * 3.0, 2),
        'rr_ratio': 3.0,
    }
```

### Visual Example:

```
LONG Setup:
                    TP: $4209.70 (3R) 🎯
                        ↑
                   +$101.70 profit
                        ↑
    Entry: $4108.00 ───┼───── (Close price)
                        ↓
                    -$33.90 risk
                        ↓
                    SL: $4074.10 (Leg low - 1 tick) 🛑

Risk:Reward = 1:3 (Need 33.4% win rate to break even)
```

---

## 🔄 MAIN PROCESS FLOW

### process_bar() Method (Lines 304-355):

```python
def process_bar(bar_state):
    """
    Main entry point - called for each bar
    """
    self.bar_count += 1

    # Cleanup old FVGs every 50 bars
    if self.bar_count % 50 == 0:
        self._cleanup_old_fvgs(max_age=100)

    # Check LONG conditions
    long_valid, fvg_info = self._check_long_conditions(bar_state)
    if long_valid:
        trade = self._calculate_long_trade(bar_state, fvg_info)

        bar_state['signal'] = {
            'timestamp': bar_state.get('timestamp', ''),
            'bar_index': self.bar_count - 1,
            'signal_type': 'ENTRY',
            'direction': 'LONG',
            'leg': bar_state.get('mgann_leg_index', 0),
            'fvg_new': fvg_info['new'],
            'fvg_zone': {'top': fvg_info['top'], 'bottom': fvg_info['bottom']},
            'trade': trade,
        }
        return bar_state

    # Check SHORT conditions
    short_valid, fvg_info = self._check_short_conditions(bar_state)
    if short_valid:
        trade = self._calculate_short_trade(bar_state, fvg_info)

        bar_state['signal'] = {
            'timestamp': bar_state.get('timestamp', ''),
            'bar_index': self.bar_count - 1,
            'signal_type': 'ENTRY',
            'direction': 'SHORT',
            'leg': bar_state.get('mgann_leg_index', 0),
            'fvg_new': fvg_info['new'],
            'fvg_zone': {'top': fvg_info['top'], 'bottom': fvg_info['bottom']},
            'trade': trade,
        }
        return bar_state

    # No signal
    return bar_state
```

---

## 📊 STRATEGY PARAMETERS

```python
def __init__(
    tick_size=0.1,           # GC Gold tick size
    risk_reward_ratio=3.0,   # 1:3 R:R for all trades
    sl_buffer_ticks=2        # SL buffer (only if leg data unavailable)
):
```

### Parameter Tuning:

| Parameter | Current | Alternative | Effect |
|-----------|---------|-------------|--------|
| `risk_reward_ratio` | 3.0 | 2.0, 4.0 | Lower TP = higher win rate |
| `sl_buffer_ticks` | 2 | 1, 3 | Tighter/wider SL |
| `max_fvg_signals` | 3 | 2, 5 | Fewer/more retests |
| `fvg_max_age` | 100 bars | 50, 200 | Forget old zones faster/slower |

---

## ✅ REQUIRED FIELDS

Strategy V1 cần các fields sau từ data:

### Must Have:
- `mgann_leg_index` - Leg number (1, 2, 3, ...)
- `fvg_detected` - FVG creation flag
- `fvg_type` - 'bullish' or 'bearish'
- `fvg_top`, `fvg_bottom` - FVG zone boundaries
- `last_swing_high`, `last_swing_low` - Pullback zone filter
- `close` - Entry price

### Optional (used if available):
- `mgann_leg_low`, `mgann_leg_high` - For better SL placement
- `pb_wave_strength_ok` - Pullback confirmation (currently DISABLED)
- `m5_ext_dir` - M5 directional filter (currently DISABLED)

---

## 🎯 PERFORMANCE METRICS (From Test)

### Test Results (500 bars):
```
Total Signals: 9
  LONG: 4 (44.4%)
  SHORT: 5 (55.6%)

Average Risk: $24.69
Risk Range: $2.60 - $34.10

If win rate = 40%:
  - Winners: 3.6 signals × 3R = 10.8R profit
  - Losers: 5.4 signals × 1R = -5.4R loss
  - Net: +5.4R profit
  - Profit Factor: 2.0
```

---

## 🔧 DISABLED FEATURES

### Currently DISABLED for testing:

1. **M5 Directional Filter** (Lines 110-113)
   ```python
   # m5_bullish = bar_state.get('m5_ext_dir', 0) == 1
   # if not m5_bullish:
   #     return False, None
   ```
   - Purpose: Filter counter-trend setups
   - When enabled: Only LONG when M5 is bullish

2. **Pullback Wave Strength** (Lines 137-141, 212-216)
   ```python
   # pb_ok = bar_state.get('pb_wave_strength_ok', False)
   # if not pb_ok:
   #     return False, None
   ```
   - Purpose: Confirm pullback exhaustion
   - When enabled: More selective entries

3. **Risk Filter** (Lines 154-162, 171-177)
   ```python
   # if potential_risk > 8.0:
   #     return False, None
   ```
   - Purpose: Skip high-risk setups (>$8 risk)
   - Disabled to let ML learn from all scenarios

---

## 📝 SUMMARY

### Strategy V1 trong 3 câu:

1. **Wait for CHoCH** (structure reversal)
2. **Enter on Leg 1/2 FVG retest** (pullback entry)
3. **Target 3R** with SL at leg extreme

### Key Features:

✅ **Simple & Clear Rules** - Easy to backtest
✅ **FVG Retest Tracking** - Max 3 signals per zone
✅ **Fixed 1:3 R:R** - Consistent risk management
✅ **Leg-based SL** - Better than arbitrary stops
✅ **Pullback Zone Filter** - Avoid breakout entries

### Philosophy:

> "Enter in pullback zones (FVG retest) after structure break (CHoCH),
> with tight stop (leg extreme) and big target (3R)."

---

**File:** `/home/user/plantrainAI/STRATEGY_V1_LOGIC.md`
**Generated:** 2025-11-25
