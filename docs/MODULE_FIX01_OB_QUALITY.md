# MODULE FIX #1: ORDER BLOCK QUALITY SCORING

**Module ID:** FIX01-OB-QUALITY
**Priority:** 🔴 CRITICAL
**Duration:** 1 day
**Status:** ⚪ NOT STARTED

---

## ⚠️ IMPORTANT DESIGN DECISION (Nov 2025)

### OB is CONTEXT, NOT SIGNAL

**Previous approach (deprecated):**
- OB retest was a separate signal type (`ob_ext_retest_bull`, `ob_ext_retest_bear`)
- Model learned both FVG and OB events separately

**New approach (current):**
- **OB retest is NOT a signal type** - only FVG retest is used as signal
- **OB provides CONTEXT** for FVG quality
- OB Quality Module still scores OBs, but output feeds into **FVG events as context features**

**Why this change?**
1. Entry thực tế phần lớn là **FVG retest**, không phải OB retest thuần
2. OB retest ~6% data nhưng pattern gần giống FVG → **data fragmentation**
3. Cùng 1 chart pattern nhưng label khác (FVG vs OB) → **model confusion**
4. OB thực tế là "nguồn gốc" của leg tạo FVG, không phải entry point riêng

**Module output usage:**
```python
# OLD: OB scores → separate OB retest events
# NEW: OB scores → context features in FVG events

# FVG event now includes:
{
    "signal_type": "fvg_retest_bull",  # NOT ob_retest_bull
    "has_ob_in_leg": true,              # OB context
    "ob_overlap_ratio": 0.7,            # How much FVG overlaps with OB
    "ob_is_m5_hl": true,                # OB at M5 HL (high quality)
    "ob_leg_bos_type": "BOS",           # BOS or CHOCH
    "ob_strength_score": 0.85           # From this module
}
```

---

## 📋 SPEC SUMMARY

### Objective
Tạo hệ thống scoring 0-1 để đánh giá chất lượng Order Block, **để làm context feature cho FVG events** (không phải signal riêng).

### Success Criteria
- [ ] `ob_strength_score` ranges 0-1
- [ ] OBs with score ≥ 0.7 have win rate ≥ 30%
- [ ] OBs with score < 0.5 have win rate < 20%
- [ ] Correlation coefficient > 0.5
- [ ] Module can be toggled on/off

---

## 🎯 DETAILED SPECIFICATION

### Input (from Indicator)
```json
{
  "ob_detected": true,
  "ob_direction": "bull",  // or "bear"
  "ob_high": 1.2345,
  "ob_low": 1.2320,
  "ob_volume": 1250,
  "ob_bar_index": 42,
  "swing_after_price": 1.2380,  // giá swing tiếp theo
  "buy_vol": 750,
  "sell_vol": 500
}
```

### Output (in BarState)
```python
{
  "ob_strength_score": 0.85,          # 0-1
  "ob_volume_factor": 2.3,            # volume / median
  "ob_delta_imbalance": 0.71,         # |buy-sell| / total
  "ob_displacement_rr": 3.2,          # move / risk
  "ob_liquidity_sweep": true          # có sweep không
}
```

---

## 🔧 CALCULATION LOGIC

### Step 1: OB Displacement RR

**Concept:** OB tốt phải tạo ra MOVE mạnh sau khi form

```python
def calculate_displacement_rr(ob_data):
    """
    Tính tỷ lệ displacement/risk của OB

    Displacement = Move từ OB đến swing tiếp theo
    Risk = Khoảng cách từ mid OB đến extreme
    """
    # Mid point của OB
    ob_mid = (ob_data['ob_high'] + ob_data['ob_low']) / 2.0

    # Extreme của OB (low cho bull, high cho bear)
    if ob_data['ob_direction'] == 'bull':
        ob_extreme = ob_data['ob_low']
        swing_after = ob_data['swing_after_price']
        # Move phải là upward
        if swing_after <= ob_mid:
            return 0.0  # Không có move mạnh
        ob_move = abs(swing_after - ob_mid)
    else:  # bear
        ob_extreme = ob_data['ob_high']
        swing_after = ob_data['swing_after_price']
        if swing_after >= ob_mid:
            return 0.0
        ob_move = abs(ob_mid - swing_after)

    # Risk = từ mid đến extreme
    ob_risk = abs(ob_mid - ob_extreme)

    if ob_risk < 1e-8:  # Avoid division by zero
        return 0.0

    # RR ratio
    displacement_rr = ob_move / ob_risk

    return displacement_rr
```

**Normalize to 0-1:**
```python
def normalize_displacement_score(displacement_rr):
    """
    Convert RR to 0-1 score

    RR = 0   → score = 0
    RR = 4   → score = 1
    RR > 4   → score = 1 (capped)
    """
    return min(displacement_rr / 4.0, 1.0)
```

**Example:**
```
OB mid = 1.2330
OB low = 1.2320 (extreme for bull)
Swing after = 1.2380

ob_risk = 1.2330 - 1.2320 = 0.0010 = 10 ticks
ob_move = 1.2380 - 1.2330 = 0.0050 = 50 ticks
displacement_rr = 50 / 10 = 5.0
normalized_score = min(5.0 / 4.0, 1.0) = 1.0 ✅ (perfect)
```

---

### Step 2: Volume Factor

**Concept:** OB tốt phải có VOLUME cao hơn average

```python
def calculate_volume_factor(ob_volume, historical_volumes):
    """
    So sánh volume OB với median 20 bars trước đó

    Args:
        ob_volume: Volume của bar OB
        historical_volumes: List volume của 20 bars trước

    Returns:
        volume_factor: Tỷ lệ volume / median
    """
    if len(historical_volumes) < 20:
        median_vol = np.mean(historical_volumes)
    else:
        median_vol = np.median(historical_volumes[-20:])

    if median_vol < 1:
        return 1.0

    volume_factor = ob_volume / median_vol
    return volume_factor
```

**Normalize to 0-1:**
```python
def normalize_volume_score(volume_factor):
    """
    Convert volume factor to score

    factor = 1.0x → score = 0   (average, nothing special)
    factor = 3.0x → score = 1   (3x median = excellent)
    factor > 3.0x → score = 1   (capped)
    """
    # Subtract 1 because 1x = baseline
    raw_score = (volume_factor - 1.0) / 2.0
    return min(max(raw_score, 0.0), 1.0)
```

**Example:**
```
ob_volume = 1500
median_vol_20 = 500

volume_factor = 1500 / 500 = 3.0
normalized_score = (3.0 - 1.0) / 2.0 = 1.0 ✅ (perfect)
```

---

### Step 3: Delta Imbalance

**Concept:** OB bull phải có BUY pressure, OB bear phải có SELL pressure

```python
def calculate_delta_imbalance(buy_vol, sell_vol, ob_direction):
    """
    Tính độ mất cân bằng buy/sell

    Bull OB: Muốn buy_vol >> sell_vol
    Bear OB: Muốn sell_vol >> buy_vol
    """
    total_vol = buy_vol + sell_vol

    if total_vol < 1:
        return 0.0

    # Raw imbalance
    raw_imbalance = abs(buy_vol - sell_vol) / total_vol

    # Check direction alignment
    if ob_direction == 'bull' and buy_vol > sell_vol:
        return raw_imbalance
    elif ob_direction == 'bear' and sell_vol > buy_vol:
        return raw_imbalance
    else:
        # Wrong direction: penalize
        return raw_imbalance * 0.3

    return raw_imbalance
```

**Example:**
```
Bull OB:
buy_vol = 900
sell_vol = 300

delta_imbalance = |900 - 300| / (900 + 300) = 600 / 1200 = 0.5

Since buy > sell for bull OB:
score = 0.5 ✅
```

---

### Step 4: Liquidity Sweep

**Concept:** OB tốt thường form sau khi sweep liquidity

```python
def detect_liquidity_sweep(bars, ob_bar_index, ob_direction):
    """
    Check nếu OB bar hoặc bar ngay sau sweep swing high/low

    Liquidity sweep = giá đi qua swing, rồi reverse lại nhanh
    """
    if ob_bar_index < 5:
        return False

    # Lấy swing gần nhất trước OB
    recent_swing_high = max([bar['high'] for bar in bars[ob_bar_index-5:ob_bar_index]])
    recent_swing_low = min([bar['low'] for bar in bars[ob_bar_index-5:ob_bar_index]])

    ob_bar = bars[ob_bar_index]

    if ob_direction == 'bull':
        # Bull OB: Sweep low, then close higher
        if ob_bar['low'] <= recent_swing_low:
            if ob_bar['close'] > recent_swing_low:
                return True  # Swept low, then reversed up

    else:  # bear
        # Bear OB: Sweep high, then close lower
        if ob_bar['high'] >= recent_swing_high:
            if ob_bar['close'] < recent_swing_high:
                return True

    return False
```

**Example:**
```
Bull OB at bar 42:
- Recent swing low (bars 37-41): 1.2310
- Bar 42: low = 1.2305, close = 1.2320
- Sweep detected: low went below 1.2310, then closed above it
- ob_liquidity_sweep = True ✅
```

---

### Step 5: Final OB Strength Score

**Weighted combination:**

```python
def calculate_ob_strength_score(
    displacement_score,
    volume_score,
    delta_imbalance,
    liquidity_sweep
):
    """
    Combine all factors into final score 0-1

    Weights:
    - Displacement: 40% (most important)
    - Volume:       30%
    - Delta:        20%
    - Sweep:        10%
    """
    score = (
        0.4 * displacement_score +
        0.3 * volume_score +
        0.2 * delta_imbalance +
        0.1 * (1.0 if liquidity_sweep else 0.0)
    )

    return round(score, 3)
```

**Example:**
```
displacement_score = 1.0  (RR = 5.0)
volume_score = 1.0        (3x median)
delta_imbalance = 0.5     (50% imbalance)
liquidity_sweep = True    (swept low)

ob_strength_score = 0.4*1.0 + 0.3*1.0 + 0.2*0.5 + 0.1*1.0
                  = 0.4 + 0.3 + 0.1 + 0.1
                  = 0.9 ✅ (excellent OB!)
```

---

## 💻 IMPLEMENTATION

### File Structure
```
processor/modules/fix01_ob_quality.py
processor/tests/test_fix01.py
processor/backtest/backtest_fix01.py
```

### Module Code

```python
# processor/modules/fix01_ob_quality.py

import numpy as np
from typing import Dict, List, Optional

class OBQualityModule:
    """
    Fix #1: Order Block Quality Scoring

    Tính ob_strength_score từ 0-1 dựa trên:
    - Displacement RR
    - Volume factor
    - Delta imbalance
    - Liquidity sweep
    """

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.name = "Fix01_OB_Quality"

    def process(self, bar_data: Dict, historical_data: List[Dict]) -> Dict:
        """
        Process bar để tính OB quality scores

        Args:
            bar_data: Current bar với raw OB data
            historical_data: 20 bars trước đó

        Returns:
            Dict với các field:
            - ob_strength_score
            - ob_volume_factor
            - ob_delta_imbalance
            - ob_displacement_rr
            - ob_liquidity_sweep
        """
        if not self.enabled:
            return self._default_output()

        # Check if OB detected
        if not bar_data.get('ob_detected', False):
            return self._default_output()

        # Calculate each component
        displacement_rr = self._calculate_displacement_rr(bar_data)
        displacement_score = min(displacement_rr / 4.0, 1.0)

        volume_factor = self._calculate_volume_factor(
            bar_data['ob_volume'],
            [b['volume'] for b in historical_data]
        )
        volume_score = min(max((volume_factor - 1.0) / 2.0, 0.0), 1.0)

        delta_imbalance = self._calculate_delta_imbalance(
            bar_data['buy_vol'],
            bar_data['sell_vol'],
            bar_data['ob_direction']
        )

        liquidity_sweep = self._detect_liquidity_sweep(
            historical_data + [bar_data],
            len(historical_data),
            bar_data['ob_direction']
        )

        # Final score
        ob_strength_score = (
            0.4 * displacement_score +
            0.3 * volume_score +
            0.2 * delta_imbalance +
            0.1 * (1.0 if liquidity_sweep else 0.0)
        )

        return {
            'ob_strength_score': round(ob_strength_score, 3),
            'ob_volume_factor': round(volume_factor, 2),
            'ob_delta_imbalance': round(delta_imbalance, 3),
            'ob_displacement_rr': round(displacement_rr, 2),
            'ob_liquidity_sweep': liquidity_sweep
        }

    def _calculate_displacement_rr(self, ob_data: Dict) -> float:
        """Calculate OB displacement RR"""
        ob_mid = (ob_data['ob_high'] + ob_data['ob_low']) / 2.0

        if ob_data['ob_direction'] == 'bull':
            ob_extreme = ob_data['ob_low']
            swing_after = ob_data['swing_after_price']
            if swing_after <= ob_mid:
                return 0.0
            ob_move = abs(swing_after - ob_mid)
        else:
            ob_extreme = ob_data['ob_high']
            swing_after = ob_data['swing_after_price']
            if swing_after >= ob_mid:
                return 0.0
            ob_move = abs(ob_mid - swing_after)

        ob_risk = abs(ob_mid - ob_extreme)
        if ob_risk < 1e-8:
            return 0.0

        return ob_move / ob_risk

    def _calculate_volume_factor(self, ob_volume: float, historical_volumes: List[float]) -> float:
        """Calculate volume factor vs median"""
        if len(historical_volumes) < 20:
            median_vol = np.mean(historical_volumes) if historical_volumes else 1
        else:
            median_vol = np.median(historical_volumes[-20:])

        if median_vol < 1:
            return 1.0

        return ob_volume / median_vol

    def _calculate_delta_imbalance(self, buy_vol: float, sell_vol: float, direction: str) -> float:
        """Calculate delta imbalance score"""
        total_vol = buy_vol + sell_vol
        if total_vol < 1:
            return 0.0

        raw_imbalance = abs(buy_vol - sell_vol) / total_vol

        # Check direction alignment
        if direction == 'bull' and buy_vol > sell_vol:
            return raw_imbalance
        elif direction == 'bear' and sell_vol > buy_vol:
            return raw_imbalance
        else:
            return raw_imbalance * 0.3  # Wrong direction penalty

    def _detect_liquidity_sweep(self, bars: List[Dict], ob_index: int, direction: str) -> bool:
        """Detect if OB formed after liquidity sweep"""
        if ob_index < 5:
            return False

        recent_swing_high = max([bar['high'] for bar in bars[ob_index-5:ob_index]])
        recent_swing_low = min([bar['low'] for bar in bars[ob_index-5:ob_index]])

        ob_bar = bars[ob_index]

        if direction == 'bull':
            if ob_bar['low'] <= recent_swing_low and ob_bar['close'] > recent_swing_low:
                return True
        else:
            if ob_bar['high'] >= recent_swing_high and ob_bar['close'] < recent_swing_high:
                return True

        return False

    def _default_output(self) -> Dict:
        """Default output when module disabled or no OB"""
        return {
            'ob_strength_score': 0.0,
            'ob_volume_factor': 0.0,
            'ob_delta_imbalance': 0.0,
            'ob_displacement_rr': 0.0,
            'ob_liquidity_sweep': False
        }
```

---

## 🧪 TESTING

### Unit Tests

```python
# processor/tests/test_fix01.py

import pytest
from processor.modules.fix01_ob_quality import OBQualityModule

def test_displacement_rr_calculation():
    """Test displacement RR calculation"""
    module = OBQualityModule()

    # Perfect bull OB: 5:1 RR
    ob_data = {
        'ob_detected': True,
        'ob_direction': 'bull',
        'ob_high': 1.2340,
        'ob_low': 1.2320,
        'swing_after_price': 1.2380,
        'ob_volume': 1000,
        'buy_vol': 700,
        'sell_vol': 300
    }

    rr = module._calculate_displacement_rr(ob_data)
    assert rr == 5.0, f"Expected 5.0, got {rr}"

def test_volume_factor():
    """Test volume factor calculation"""
    module = OBQualityModule()

    historical_volumes = [500] * 20
    ob_volume = 1500

    factor = module._calculate_volume_factor(ob_volume, historical_volumes)
    assert factor == 3.0, f"Expected 3.0, got {factor}"

def test_delta_imbalance_bull():
    """Test delta imbalance for bull OB"""
    module = OBQualityModule()

    # Bull OB với buy dominance
    imbalance = module._calculate_delta_imbalance(
        buy_vol=900,
        sell_vol=300,
        direction='bull'
    )
    assert imbalance == 0.5, f"Expected 0.5, got {imbalance}"

def test_liquidity_sweep_detection():
    """Test liquidity sweep detection"""
    module = OBQualityModule()

    bars = [
        {'high': 1.2330, 'low': 1.2310, 'close': 1.2320},
        {'high': 1.2335, 'low': 1.2315, 'close': 1.2325},
        {'high': 1.2340, 'low': 1.2320, 'close': 1.2330},
        {'high': 1.2338, 'low': 1.2318, 'close': 1.2328},
        {'high': 1.2335, 'low': 1.2315, 'close': 1.2325},
        # OB bar: sweep low then close higher
        {'high': 1.2330, 'low': 1.2305, 'close': 1.2325}
    ]

    sweep = module._detect_liquidity_sweep(bars, 5, 'bull')
    assert sweep == True, "Should detect liquidity sweep"

def test_final_score_excellent_ob():
    """Test final score for excellent OB"""
    module = OBQualityModule()

    bar_data = {
        'ob_detected': True,
        'ob_direction': 'bull',
        'ob_high': 1.2340,
        'ob_low': 1.2320,
        'swing_after_price': 1.2380,
        'ob_volume': 1500,
        'buy_vol': 900,
        'sell_vol': 300
    }

    historical = [
        {'volume': 500, 'high': 1.23, 'low': 1.22, 'close': 1.225}
        for _ in range(20)
    ]

    result = module.process(bar_data, historical)

    assert result['ob_strength_score'] >= 0.8, \
        f"Excellent OB should score >= 0.8, got {result['ob_strength_score']}"
```

---

## 📊 BACKTESTING

### Backtest Script

```python
# processor/backtest/backtest_fix01.py

import pandas as pd
import numpy as np
from processor.modules.fix01_ob_quality import OBQualityModule

class Fix01Backtest:
    """
    Backtest Fix #1: OB Quality Module

    Goals:
    1. Validate ob_strength_score correlates with win rate
    2. Find optimal threshold (likely 0.7)
    3. Measure improvement vs baseline
    """

    def __init__(self, data_file):
        self.data_file = data_file
        self.module = OBQualityModule()
        self.results = []

    def load_data(self):
        """Load raw OB data với outcomes"""
        # TODO: Load from actual export
        pass

    def run(self):
        """Run backtest on historical OBs"""
        data = self.load_data()

        for i, bar in enumerate(data):
            if not bar.get('ob_detected'):
                continue

            # Get historical context
            historical = data[max(0, i-20):i]

            # Calculate OB score
            scores = self.module.process(bar, historical)

            # Record result
            self.results.append({
                'bar_index': i,
                'ob_score': scores['ob_strength_score'],
                'volume_factor': scores['ob_volume_factor'],
                'delta_imbalance': scores['ob_delta_imbalance'],
                'displacement_rr': scores['ob_displacement_rr'],
                'liquidity_sweep': scores['ob_liquidity_sweep'],
                'actual_outcome': bar['hit'],  # 'tp' or 'sl'
                'win': bar['hit'] == 'tp'
            })

        return self.analyze_results()

    def analyze_results(self):
        """Analyze correlation between score and win rate"""
        df = pd.DataFrame(self.results)

        # Overall stats
        total_obs = len(df)
        overall_win_rate = df['win'].mean()

        # Score buckets
        buckets = {
            '0.0-0.3': (0.0, 0.3),
            '0.3-0.5': (0.3, 0.5),
            '0.5-0.7': (0.5, 0.7),
            '0.7-0.9': (0.7, 0.9),
            '0.9-1.0': (0.9, 1.0)
        }

        bucket_stats = {}
        for name, (low, high) in buckets.items():
            mask = (df['ob_score'] >= low) & (df['ob_score'] < high)
            bucket_df = df[mask]

            if len(bucket_df) > 0:
                bucket_stats[name] = {
                    'count': len(bucket_df),
                    'win_rate': bucket_df['win'].mean(),
                    'avg_score': bucket_df['ob_score'].mean()
                }

        # Correlation
        correlation = df['ob_score'].corr(df['win'].astype(float))

        report = {
            'total_obs': total_obs,
            'overall_win_rate': overall_win_rate,
            'bucket_stats': bucket_stats,
            'correlation': correlation
        }

        self.print_report(report)
        return report

    def print_report(self, report):
        """Print backtest report"""
        print("=" * 80)
        print("FIX #1: OB QUALITY - BACKTEST REPORT")
        print("=" * 80)
        print()
        print(f"Total OBs analyzed: {report['total_obs']}")
        print(f"Overall win rate: {report['overall_win_rate']:.1%}")
        print(f"Score-Win correlation: {report['correlation']:.3f}")
        print()
        print("Win Rate by Score Bucket:")
        print("-" * 80)

        for bucket, stats in report['bucket_stats'].items():
            print(f"{bucket}: {stats['count']:4d} OBs, "
                  f"Win Rate: {stats['win_rate']:.1%}, "
                  f"Avg Score: {stats['avg_score']:.2f}")

        print()
        print("=" * 80)
```

---

## ✅ ACCEPTANCE CRITERIA

### Functional Requirements
- [ ] Module can be enabled/disabled via flag
- [ ] All scores output correctly (0-1 range)
- [ ] No crashes on edge cases (zero volume, etc.)
- [ ] Runs in < 1ms per bar

### Performance Requirements
- [ ] Scores ≥ 0.7 have win rate ≥ 30%
- [ ] Scores < 0.5 have win rate < 20%
- [ ] Correlation > 0.5
- [ ] Clear separation between high/low scores

### Quality Requirements
- [ ] Code passes pylint
- [ ] 100% test coverage
- [ ] Documented with examples
- [ ] Backtest report generated

---

## 📝 CHECKLIST

### Development
- [ ] Implement `OBQualityModule` class
- [ ] Write all helper methods
- [ ] Add error handling
- [ ] Add logging

### Testing
- [ ] Write unit tests (all methods)
- [ ] Test edge cases
- [ ] Test with real data samples
- [ ] All tests pass

### Backtesting
- [ ] Load historical OB data
- [ ] Run backtest script
- [ ] Generate report
- [ ] Validate correlation > 0.5

### Documentation
- [ ] Code comments complete
- [ ] Docstrings for all methods
- [ ] Update CHANGELOG
- [ ] Create example usage

### Integration
- [ ] Integrate with main processor
- [ ] Test with other modules
- [ ] Verify BarState output correct
- [ ] Ready for Fix #2

---

## 🚀 GETTING STARTED

1. Read this spec thoroughly
2. Implement `processor/modules/fix01_ob_quality.py`
3. Write tests in `processor/tests/test_fix01.py`
4. Run tests: `pytest processor/tests/test_fix01.py -v`
5. Backtest: `python processor/backtest/backtest_fix01.py`
6. Review results and iterate
7. Sign off when criteria met

---

**Status:** ⚪ Ready for Implementation
**Estimated Time:** 1 day
**Next Module:** Fix #2 (FVG Quality)

---

## 🔗 OB CONTEXT FIELDS FOR FVG EVENTS

### Additional Output (for FVG Event Context)

Ngoài `ob_strength_score`, module này cần output thêm các fields để làm context cho FVG events:

```python
{
    # Core OB scoring (existing)
    "ob_strength_score": 0.85,
    "ob_volume_factor": 2.3,
    "ob_delta_imbalance": 0.71,
    "ob_displacement_rr": 3.2,
    "ob_liquidity_sweep": true,

    # NEW: OB Context for FVG (added)
    "ob_is_m5_hl": true,           # OB at M5 swing high/low?
    "ob_leg_bos_type": "BOS",      # "BOS" (ext), "CHOCH" (int), "None"
    "ob_high": 1.2345,             # For overlap calculation
    "ob_low": 1.2320               # For overlap calculation
}
```

### OB-FVG Overlap Calculation

```python
def calculate_ob_fvg_overlap(ob_high, ob_low, fvg_high, fvg_low):
    """
    Calculate how much FVG overlaps with OB zone.

    Returns:
        overlap_ratio: 0.0-1.0 (ratio of FVG inside OB)
    """
    if ob_high is None or ob_low is None:
        return 0.0

    # Calculate intersection
    overlap_high = min(ob_high, fvg_high)
    overlap_low = max(ob_low, fvg_low)

    if overlap_high <= overlap_low:
        return 0.0  # No overlap

    overlap_size = overlap_high - overlap_low
    fvg_size = fvg_high - fvg_low

    if fvg_size <= 0:
        return 0.0

    return min(overlap_size / fvg_size, 1.0)
```

### OB-FVG Distance Calculation

```python
def calculate_ob_fvg_distance(ob_bar_index, fvg_bar_index, atr):
    """
    Calculate normalized distance from OB source to FVG.

    FVG gần OB source → higher quality (fresh demand/supply)
    FVG xa OB source → lower quality (stale zone)

    Returns:
        normalized_distance: in ATR units
    """
    bar_distance = abs(fvg_bar_index - ob_bar_index)

    # Assume average bar = 0.1 ATR movement
    price_distance_approx = bar_distance * 0.1 * atr

    return round(price_distance_approx / atr, 2)
```

### Integration with FVG Event Builder

```python
# In event_detector.py
def build_fvg_event(fvg_bar_state, ob_context):
    """
    Build FVG event with OB context fields.
    """
    event = {
        "signal_type": f"fvg_retest_{fvg_bar_state['fvg_type']}",

        # FVG quality (from Module #2)
        "fvg_quality_score": fvg_bar_state["fvg_quality_score"],
        "fvg_value_class": fvg_bar_state["fvg_value_class"],

        # OB context (from this module)
        "has_ob_in_leg": ob_context.get("ob_detected", False),
        "ob_overlap_ratio": calculate_ob_fvg_overlap(
            ob_context.get("ob_high"),
            ob_context.get("ob_low"),
            fvg_bar_state["fvg_high"],
            fvg_bar_state["fvg_low"]
        ),
        "ob_is_m5_hl": ob_context.get("ob_is_m5_hl", False),
        "ob_leg_bos_type": ob_context.get("ob_leg_bos_type", "None"),
        "ob_distance_from_source": calculate_ob_fvg_distance(
            ob_context.get("ob_bar_index", 0),
            fvg_bar_state["bar_index"],
            fvg_bar_state["atr_14"]
        ),
        "ob_strength_score": ob_context.get("ob_strength_score", 0.0),

        # ... other fields
    }
    return event
```

### High-Quality FVG Profile

FVG được coi là "đẹp kiểu thực chiến" khi có OB context mạnh:

| Field | Ideal Value | Rationale |
|-------|-------------|-----------|
| `has_ob_in_leg` | `true` | Leg tạo FVG đi qua OB |
| `ob_overlap_ratio` | `>= 0.5` | FVG nằm sâu trong OB zone |
| `ob_is_m5_hl` | `true` | OB tại chân HL M5 (structure) |
| `ob_leg_bos_type` | `"BOS"` | Breakout structure (stronger) |
| `ob_strength_score` | `>= 0.7` | OB quality score cao |
| `ob_distance_from_source` | `< 2.0` | FVG gần OB source (fresh) |

**Expected impact when OB context matches profile:**
- FVG with strong OB backing: 45-55% win rate
- FVG without OB backing: 28-35% win rate
