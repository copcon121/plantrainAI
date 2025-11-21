# MODULE #07: MARKET CONDITION

## VERSION: 1.0
## STATUS: New Spec
## PRIORITY: MEDIUM (Signal Filter)

---

## 1. MODULE OVERVIEW

### 1.1 Mục Đích
Xác định **Market Condition** hiện tại để:
- Filter signals không phù hợp với market regime
- Điều chỉnh parameters (stop width, target size)
- Improve ML feature set với market context

### 1.2 Nguyên Lý
> "Different market conditions require different trading approaches"

**Market Conditions trong SMC:**
- **Trending**: Clear directional bias, momentum plays
- **Ranging**: Sideways, mean reversion, liquidity sweeps
- **Volatile**: Wide swings, require wider stops
- **Quiet**: Low volatility, tight ranges

### 1.3 Vị Trí Trong Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                   MARKET CONDITION FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Price Data + ATR + Volume]                                    │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────┐       │
│  │           MARKET CONDITION DETECTOR                 │       │
│  │                                                     │       │
│  │  1. Trend Detection (ADX-based)                    │       │
│  │  2. Volatility Regime (ATR percentile)             │       │
│  │  3. Range Detection (price containment)            │       │
│  │                                                     │       │
│  └─────────────────────────────────────────────────────┘       │
│       │                                                         │
│       ▼                                                         │
│  [market_condition, volatility_regime, trend_strength]         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. MARKET CONDITIONS

### 2.1 Condition Types

| Condition | Description | Characteristics | Trade Approach |
|-----------|-------------|-----------------|----------------|
| `trending_bullish` | Strong uptrend | ADX > 25, DI+ > DI- | Bullish FVG preferred |
| `trending_bearish` | Strong downtrend | ADX > 25, DI- > DI+ | Bearish FVG preferred |
| `ranging` | Sideways market | ADX < 20, price in range | Both directions OK |
| `volatile_bullish` | Volatile uptrend | High ATR + uptrend | Wider stops |
| `volatile_bearish` | Volatile downtrend | High ATR + downtrend | Wider stops |
| `choppy` | No clear direction | Low ADX, erratic moves | Skip trades |

### 2.2 Volatility Regimes

| Regime | ATR Percentile | Description |
|--------|----------------|-------------|
| `low` | < 25th | Quiet market, tight ranges |
| `normal` | 25th - 75th | Normal volatility |
| `high` | > 75th | Elevated volatility |
| `extreme` | > 95th | Exceptional volatility, caution |

---

## 3. DETECTION ALGORITHMS

### 3.1 Trend Detection (ADX-based)

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TrendInfo:
    """Trend detection result."""
    is_trending: bool
    trend_direction: int      # 1 = bullish, -1 = bearish, 0 = neutral
    trend_strength: float     # 0-1 strength score
    adx_value: float
    di_plus: float
    di_minus: float


def calculate_adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> dict:
    """
    Calculate ADX, DI+, DI-.

    Note: Simplified calculation - use TA-Lib or similar in production.
    """
    # Calculate True Range
    tr_list = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_list.append(tr)

    # Calculate +DM and -DM
    plus_dm = []
    minus_dm = []
    for i in range(1, len(highs)):
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]

        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
        else:
            plus_dm.append(0)

        if down_move > up_move and down_move > 0:
            minus_dm.append(down_move)
        else:
            minus_dm.append(0)

    # Smooth with EMA
    def ema(data: List[float], period: int) -> List[float]:
        result = [sum(data[:period]) / period]
        multiplier = 2 / (period + 1)
        for i in range(period, len(data)):
            result.append((data[i] - result[-1]) * multiplier + result[-1])
        return result

    atr = ema(tr_list, period)
    smooth_plus_dm = ema(plus_dm, period)
    smooth_minus_dm = ema(minus_dm, period)

    # Calculate DI+ and DI-
    di_plus = (smooth_plus_dm[-1] / atr[-1]) * 100 if atr[-1] > 0 else 0
    di_minus = (smooth_minus_dm[-1] / atr[-1]) * 100 if atr[-1] > 0 else 0

    # Calculate DX and ADX
    dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100 if (di_plus + di_minus) > 0 else 0
    # ADX would need smoothing of DX over period - simplified here
    adx = dx  # In production, smooth DX over period

    return {
        "adx": adx,
        "di_plus": di_plus,
        "di_minus": di_minus
    }


def detect_trend(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    adx_trending_threshold: float = 25.0,
    adx_strong_threshold: float = 40.0
) -> TrendInfo:
    """
    Detect market trend using ADX.

    Args:
        highs, lows, closes: Price data
        adx_trending_threshold: ADX above this = trending
        adx_strong_threshold: ADX above this = strong trend

    Returns:
        TrendInfo with trend details
    """
    adx_data = calculate_adx(highs, lows, closes)
    adx = adx_data["adx"]
    di_plus = adx_data["di_plus"]
    di_minus = adx_data["di_minus"]

    # Determine if trending
    is_trending = adx >= adx_trending_threshold

    # Determine direction
    if di_plus > di_minus:
        trend_direction = 1  # Bullish
    elif di_minus > di_plus:
        trend_direction = -1  # Bearish
    else:
        trend_direction = 0  # Neutral

    # Calculate strength (0-1)
    if adx >= adx_strong_threshold:
        trend_strength = 1.0
    elif adx >= adx_trending_threshold:
        trend_strength = 0.5 + 0.5 * (adx - adx_trending_threshold) / (adx_strong_threshold - adx_trending_threshold)
    else:
        trend_strength = adx / adx_trending_threshold * 0.5

    return TrendInfo(
        is_trending=is_trending,
        trend_direction=trend_direction if is_trending else 0,
        trend_strength=round(trend_strength, 3),
        adx_value=round(adx, 2),
        di_plus=round(di_plus, 2),
        di_minus=round(di_minus, 2)
    )
```

### 3.2 Volatility Regime Detection

```python
@dataclass
class VolatilityInfo:
    """Volatility regime detection result."""
    regime: str                # "low", "normal", "high", "extreme"
    current_atr: float
    atr_percentile: float      # 0-100
    volatility_score: float    # 0-1


def detect_volatility_regime(
    atr_values: List[float],
    lookback: int = 100
) -> VolatilityInfo:
    """
    Detect volatility regime using ATR percentile.

    Args:
        atr_values: Historical ATR values
        lookback: Number of periods to use for percentile calculation

    Returns:
        VolatilityInfo with regime details
    """
    if len(atr_values) < lookback:
        lookback = len(atr_values)

    current_atr = atr_values[-1]
    historical_atr = atr_values[-lookback:]

    # Calculate percentile
    sorted_atr = sorted(historical_atr)
    rank = sum(1 for x in sorted_atr if x <= current_atr)
    percentile = (rank / len(sorted_atr)) * 100

    # Determine regime
    if percentile < 25:
        regime = "low"
        volatility_score = percentile / 25 * 0.25
    elif percentile < 75:
        regime = "normal"
        volatility_score = 0.25 + (percentile - 25) / 50 * 0.5
    elif percentile < 95:
        regime = "high"
        volatility_score = 0.75 + (percentile - 75) / 20 * 0.2
    else:
        regime = "extreme"
        volatility_score = 0.95 + (percentile - 95) / 5 * 0.05

    return VolatilityInfo(
        regime=regime,
        current_atr=round(current_atr, 5),
        atr_percentile=round(percentile, 1),
        volatility_score=round(volatility_score, 3)
    )
```

### 3.3 Range Detection

```python
@dataclass
class RangeInfo:
    """Range detection result."""
    is_ranging: bool
    range_high: Optional[float]
    range_low: Optional[float]
    range_size: Optional[float]
    containment_ratio: float   # % of bars within range


def detect_range(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    lookback: int = 20,
    containment_threshold: float = 0.8
) -> RangeInfo:
    """
    Detect if price is in a range.

    Range = High and low boundaries where most price action is contained.

    Args:
        highs, lows, closes: Price data
        lookback: Bars to analyze
        containment_threshold: % of bars that must be in range to confirm

    Returns:
        RangeInfo with range details
    """
    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    recent_closes = closes[-lookback:]

    # Find potential range boundaries
    range_high = max(recent_highs)
    range_low = min(recent_lows)
    range_size = range_high - range_low

    # Calculate containment (how many bars stay within 90% of range)
    inner_high = range_low + range_size * 0.95
    inner_low = range_low + range_size * 0.05

    contained_bars = sum(
        1 for h, l in zip(recent_highs, recent_lows)
        if l >= inner_low and h <= inner_high
    )
    containment_ratio = contained_bars / lookback

    # Determine if ranging
    is_ranging = containment_ratio >= containment_threshold

    return RangeInfo(
        is_ranging=is_ranging,
        range_high=round(range_high, 5) if is_ranging else None,
        range_low=round(range_low, 5) if is_ranging else None,
        range_size=round(range_size, 5) if is_ranging else None,
        containment_ratio=round(containment_ratio, 3)
    )
```

---

## 4. MARKET CONDITION ENGINE

### 4.1 Main Classification

```python
@dataclass
class MarketConditionResult:
    """Complete market condition analysis."""
    # Primary condition
    market_condition: str        # Main condition type
    condition_confidence: float  # 0-1 confidence

    # Sub-components
    trend_info: TrendInfo
    volatility_info: VolatilityInfo
    range_info: RangeInfo

    # Trading implications
    trade_bias: int              # 1 = bullish, -1 = bearish, 0 = neutral
    stop_multiplier: float       # Multiply default stop by this
    should_trade: bool           # Is condition tradeable?


def classify_market_condition(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    atr_values: List[float]
) -> MarketConditionResult:
    """
    Classify overall market condition.

    Combines trend, volatility, and range analysis.

    Returns:
        MarketConditionResult with full analysis
    """
    # Detect components
    trend = detect_trend(highs, lows, closes)
    volatility = detect_volatility_regime(atr_values)
    range_info = detect_range(highs, lows, closes)

    # Classify main condition
    if trend.is_trending and volatility.regime in ["low", "normal"]:
        if trend.trend_direction == 1:
            market_condition = "trending_bullish"
            trade_bias = 1
        else:
            market_condition = "trending_bearish"
            trade_bias = -1
        condition_confidence = trend.trend_strength
        should_trade = True
        stop_multiplier = 1.0

    elif trend.is_trending and volatility.regime in ["high", "extreme"]:
        if trend.trend_direction == 1:
            market_condition = "volatile_bullish"
            trade_bias = 1
        else:
            market_condition = "volatile_bearish"
            trade_bias = -1
        condition_confidence = trend.trend_strength * 0.8  # Lower confidence
        should_trade = volatility.regime != "extreme"  # Skip extreme
        stop_multiplier = 1.5 if volatility.regime == "high" else 2.0

    elif range_info.is_ranging and volatility.regime in ["low", "normal"]:
        market_condition = "ranging"
        trade_bias = 0
        condition_confidence = range_info.containment_ratio
        should_trade = True
        stop_multiplier = 0.8  # Tighter stops in range

    else:
        market_condition = "choppy"
        trade_bias = 0
        condition_confidence = 0.3
        should_trade = False  # Skip choppy markets
        stop_multiplier = 1.0

    return MarketConditionResult(
        market_condition=market_condition,
        condition_confidence=round(condition_confidence, 3),
        trend_info=trend,
        volatility_info=volatility,
        range_info=range_info,
        trade_bias=trade_bias,
        stop_multiplier=stop_multiplier,
        should_trade=should_trade
    )
```

---

## 5. SIGNAL FILTERING

### 5.1 Filter Logic

```python
def filter_signal_by_market_condition(
    fvg_direction: int,
    market_condition: MarketConditionResult
) -> tuple[bool, str]:
    """
    Filter FVG signal based on market condition.

    Args:
        fvg_direction: 1 = bullish, -1 = bearish
        market_condition: Current market condition

    Returns:
        (should_take_signal, reason)
    """
    # Skip choppy markets
    if not market_condition.should_trade:
        return False, "market_choppy"

    # In trending market, prefer signals aligned with trend
    if market_condition.market_condition.startswith("trending"):
        if fvg_direction != market_condition.trade_bias:
            return False, "against_trend"
        return True, "aligned_with_trend"

    # In volatile trending market, same logic but more caution
    if market_condition.market_condition.startswith("volatile"):
        if fvg_direction != market_condition.trade_bias:
            return False, "against_volatile_trend"
        if market_condition.condition_confidence < 0.5:
            return False, "low_confidence_volatile"
        return True, "aligned_volatile_trend"

    # In ranging market, both directions OK
    if market_condition.market_condition == "ranging":
        return True, "ranging_both_ok"

    return False, "unknown_condition"
```

---

## 6. OUTPUT FIELDS

### 6.1 BarState Fields (Python Layer 2)

```python
# === MARKET CONDITION (Module #07) ===
market_condition: str            # "trending_bullish", "ranging", etc.
condition_confidence: float      # 0-1 confidence score

# Trend
trend_is_trending: bool
trend_direction: int             # 1, -1, 0
trend_strength: float            # 0-1
trend_adx: float

# Volatility
volatility_regime: str           # "low", "normal", "high", "extreme"
volatility_percentile: float     # 0-100
volatility_score: float          # 0-1

# Range
is_ranging: bool
range_high: Optional[float]
range_low: Optional[float]

# Trading
trade_bias: int                  # 1, -1, 0
stop_multiplier: float           # Adjust stops
should_trade: bool               # Is market tradeable
```

### 6.2 Sample Output

```json
{
    "market_condition": "trending_bullish",
    "condition_confidence": 0.75,

    "trend_is_trending": true,
    "trend_direction": 1,
    "trend_strength": 0.75,
    "trend_adx": 32.5,

    "volatility_regime": "normal",
    "volatility_percentile": 55.0,
    "volatility_score": 0.55,

    "is_ranging": false,
    "range_high": null,
    "range_low": null,

    "trade_bias": 1,
    "stop_multiplier": 1.0,
    "should_trade": true
}
```

---

## 7. NINJA EXPORT REQUIREMENTS

### 7.1 Fields Needed from Layer 1 (NinjaTrader)

| Field | Type | Description |
|-------|------|-------------|
| `atr_14` | float | 14-period ATR (đã có) |
| `high` | float | Bar high (đã có) |
| `low` | float | Bar low (đã có) |
| `close` | float | Bar close (đã có) |

### 7.2 New Fields Required

```
# ADX INDICATORS (optional - can calculate in Python)
adx_14: float          # 14-period ADX
di_plus_14: float      # 14-period DI+
di_minus_14: float     # 14-period DI-
```

**Note**: ADX có thể tính trong Python từ OHLC data, nhưng nếu NinjaTrader đã có indicator thì export để tiết kiệm computation.

### 7.3 Computation Location

| Calculation | Location | Reason |
|-------------|----------|--------|
| ADX/DI | Ninja or Python | Built-in indicator in Ninja |
| ATR Percentile | Python | Needs historical comparison |
| Range Detection | Python | Dynamic lookback analysis |
| **Condition Classification** | Python | Complex logic |

---

## 8. UNIT TESTS

```python
def test_trending_bullish_detection():
    """Test detection of bullish trend."""
    # Mock data showing clear uptrend
    highs = [100 + i * 0.5 for i in range(20)]  # Rising highs
    lows = [99 + i * 0.5 for i in range(20)]    # Rising lows
    closes = [99.5 + i * 0.5 for i in range(20)]
    atr_values = [0.5] * 100

    result = classify_market_condition(highs, lows, closes, atr_values)

    assert result.market_condition == "trending_bullish"
    assert result.trade_bias == 1
    assert result.should_trade is True


def test_ranging_detection():
    """Test detection of ranging market."""
    # Mock data showing sideways movement
    import math
    highs = [100 + 0.5 * math.sin(i * 0.5) for i in range(30)]
    lows = [99 + 0.5 * math.sin(i * 0.5) for i in range(30)]
    closes = [99.5 + 0.5 * math.sin(i * 0.5) for i in range(30)]
    atr_values = [0.3] * 100

    result = classify_market_condition(highs, lows, closes, atr_values)

    assert result.market_condition == "ranging"
    assert result.trade_bias == 0


def test_high_volatility_detection():
    """Test detection of high volatility."""
    atr_values = [0.5] * 90 + [1.2] * 10  # Recent ATR spike

    result = detect_volatility_regime(atr_values)

    assert result.regime in ["high", "extreme"]
    assert result.atr_percentile > 75


def test_signal_filter_against_trend():
    """Test that counter-trend signals are filtered."""
    # Create bullish trending market
    highs = [100 + i * 0.5 for i in range(20)]
    lows = [99 + i * 0.5 for i in range(20)]
    closes = [99.5 + i * 0.5 for i in range(20)]
    atr_values = [0.5] * 100

    market_condition = classify_market_condition(highs, lows, closes, atr_values)

    # Bearish FVG in bullish market
    should_trade, reason = filter_signal_by_market_condition(-1, market_condition)

    assert should_trade is False
    assert reason == "against_trend"
```

---

## 9. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial spec - ADX trend + ATR volatility + Range detection |

---

## 10. NOTES

### 10.1 Simplifications for v1.0
- ADX-based trend detection (simple, reliable)
- ATR percentile for volatility (no complex models)
- Basic range detection (containment ratio)

### 10.2 Future Enhancements (v2.0)
- Multi-timeframe market condition
- Volume-based regime detection
- Session-based adjustments (Asian/London/NY)
- News event impact detection

### 10.3 Integration with ML
Market condition là feature quan trọng cho ML model:
- Model có thể học different patterns per condition
- Feature engineering: encode condition as categorical
- Stratified training by market condition
