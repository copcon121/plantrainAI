# MODULE #10: MTF ALIGNMENT (Multi-Timeframe)

## VERSION: 1.0
## STATUS: New Spec
## PRIORITY: HIGH (Signal Filter)

---

## 1. MODULE OVERVIEW

### 1.1 Mục Đích
Xác định **Higher Timeframe (HTF) Alignment** để:
- Filter signals against HTF trend
- Add confluence khi FVG align với HTF direction
- Improve win rate by trading with "the flow"

### 1.2 Nguyên Lý SMC
> "Trade with the higher timeframe flow - entries on LTF, direction from HTF"

**MTF Hierarchy trong Trading:**
- Entry TF: 5m / 15m
- Trend TF: 1H / 4H
- Bias TF: Daily

**Rule:** LTF signal PHẢI align với HTF trend để có edge cao nhất.

### 1.3 Vị Trí Trong Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     MTF ALIGNMENT FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [HTF Data: 1H/4H/Daily]                                       │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────┐       │
│  │           HTF TREND DETECTOR                        │       │
│  │                                                     │       │
│  │  - Structure-based (HH/HL vs LH/LL)                │       │
│  │  - Moving average alignment                         │       │
│  │  - Recent swing direction                          │       │
│  │                                                     │       │
│  └─────────────────────────────────────────────────────┘       │
│       │                                                         │
│       ▼                                                         │
│  [htf_trend, htf_strength, htf_bias]                           │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────┐       │
│  │           ALIGNMENT CALCULATOR                      │       │
│  │                                                     │       │
│  │  LTF Signal vs HTF Trend → alignment_score          │       │
│  │                                                     │       │
│  └─────────────────────────────────────────────────────┘       │
│       │                                                         │
│       ▼                                                         │
│  [mtf_alignment_score, mtf_aligned, mtf_filter_passed]        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. HTF TREND DETECTION

### 2.1 Trend States

| State | Description | LTF Signal Preference |
|-------|-------------|-----------------------|
| `bullish_strong` | Clear uptrend (HH/HL) | Bullish FVG only |
| `bullish_weak` | Uptrend but slowing | Bullish preferred |
| `bearish_strong` | Clear downtrend (LH/LL) | Bearish FVG only |
| `bearish_weak` | Downtrend but slowing | Bearish preferred |
| `neutral` | No clear trend | Both directions OK |
| `transitional` | Possible trend change | Caution, reduced size |

### 2.2 Detection Methods

**Method 1: Structure-Based (Primary)**
```
Bullish: Price making Higher Highs + Higher Lows
Bearish: Price making Lower Highs + Lower Lows
Neutral: Mixed structure
```

**Method 2: Moving Average**
```
Bullish: Price above 20 EMA, 20 EMA above 50 EMA
Bearish: Price below 20 EMA, 20 EMA below 50 EMA
```

**Method 3: Recent Swing Direction**
```
Bullish: Last swing was a Higher Low
Bearish: Last swing was a Lower High
```

---

## 3. CALCULATION LOGIC

### 3.1 Data Structures

```python
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class TrendState(Enum):
    BULLISH_STRONG = "bullish_strong"
    BULLISH_WEAK = "bullish_weak"
    BEARISH_STRONG = "bearish_strong"
    BEARISH_WEAK = "bearish_weak"
    NEUTRAL = "neutral"
    TRANSITIONAL = "transitional"


@dataclass
class HTFTrendInfo:
    """Higher timeframe trend information."""
    trend_state: TrendState
    trend_direction: int           # 1 = bullish, -1 = bearish, 0 = neutral
    trend_strength: float          # 0-1 strength score
    last_swing_type: str           # "HH", "HL", "LH", "LL"
    structure_score: float         # Based on swing sequence
    ma_score: float                # Based on MA alignment
    days_in_trend: int             # How long current trend has lasted


@dataclass
class MTFAlignmentResult:
    """Result of MTF alignment check."""
    mtf_aligned: bool              # Is LTF signal aligned with HTF?
    mtf_alignment_score: float     # 0-1 alignment score
    mtf_filter_passed: bool        # Should we take this signal?
    htf_trend: HTFTrendInfo
    alignment_bonus: float         # Multiplier for confluence
```

### 3.2 HTF Trend Detection

```python
class MTFAlignmentModule:
    """
    Multi-Timeframe Alignment Detection.

    Determines HTF trend and calculates alignment with LTF signals.
    """

    def __init__(
        self,
        structure_lookback: int = 50,     # Bars to look back for structure
        swing_strength: int = 5,          # Bars left/right for swing detection
        strong_trend_threshold: float = 0.7
    ):
        self.structure_lookback = structure_lookback
        self.swing_strength = swing_strength
        self.strong_trend_threshold = strong_trend_threshold

    def detect_htf_trend(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        ema_20: Optional[List[float]] = None,
        ema_50: Optional[List[float]] = None
    ) -> HTFTrendInfo:
        """
        Detect higher timeframe trend using multiple methods.

        Args:
            highs, lows, closes: HTF price data
            ema_20, ema_50: Optional MA data (can calculate if not provided)

        Returns:
            HTFTrendInfo with trend details
        """
        # Method 1: Structure analysis
        structure_result = self._analyze_structure(highs, lows)

        # Method 2: MA analysis (if available)
        if ema_20 and ema_50:
            ma_result = self._analyze_ma_alignment(closes, ema_20, ema_50)
        else:
            ma_result = {"score": 0.5, "direction": 0}  # Neutral if no MA

        # Combine scores
        structure_weight = 0.7
        ma_weight = 0.3

        combined_score = (
            structure_result["score"] * structure_weight +
            ma_result["score"] * ma_weight
        )

        # Determine trend state
        trend_direction = structure_result["direction"]
        trend_strength = abs(combined_score - 0.5) * 2  # Convert 0-1 to strength

        if trend_direction == 1:
            if trend_strength >= self.strong_trend_threshold:
                trend_state = TrendState.BULLISH_STRONG
            else:
                trend_state = TrendState.BULLISH_WEAK
        elif trend_direction == -1:
            if trend_strength >= self.strong_trend_threshold:
                trend_state = TrendState.BEARISH_STRONG
            else:
                trend_state = TrendState.BEARISH_WEAK
        else:
            trend_state = TrendState.NEUTRAL

        return HTFTrendInfo(
            trend_state=trend_state,
            trend_direction=trend_direction,
            trend_strength=round(trend_strength, 3),
            last_swing_type=structure_result["last_swing"],
            structure_score=structure_result["score"],
            ma_score=ma_result["score"],
            days_in_trend=structure_result.get("trend_duration", 0)
        )

    def _analyze_structure(
        self,
        highs: List[float],
        lows: List[float]
    ) -> dict:
        """
        Analyze price structure for HH/HL/LH/LL pattern.

        Returns:
            dict with score, direction, last_swing
        """
        # Find swing points
        swing_highs = self._find_swings(highs, "high")
        swing_lows = self._find_swings(lows, "low")

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"score": 0.5, "direction": 0, "last_swing": "unknown"}

        # Analyze last 4 swings
        recent_highs = swing_highs[-2:]
        recent_lows = swing_lows[-2:]

        # Check for HH/HL (bullish) or LH/LL (bearish)
        hh = recent_highs[-1] > recent_highs[-2]  # Higher High
        hl = recent_lows[-1] > recent_lows[-2]    # Higher Low
        lh = recent_highs[-1] < recent_highs[-2]  # Lower High
        ll = recent_lows[-1] < recent_lows[-2]    # Lower Low

        # Score calculation
        if hh and hl:  # Clear uptrend
            score = 0.9
            direction = 1
            last_swing = "HH" if swing_highs[-1] > swing_lows[-1] else "HL"
        elif lh and ll:  # Clear downtrend
            score = 0.1
            direction = -1
            last_swing = "LH" if swing_highs[-1] < swing_lows[-1] else "LL"
        elif hh and ll:  # Mixed (expansion)
            score = 0.6
            direction = 1
            last_swing = "HH"
        elif lh and hl:  # Mixed (compression)
            score = 0.4
            direction = -1
            last_swing = "LH"
        else:  # Neutral
            score = 0.5
            direction = 0
            last_swing = "unknown"

        return {
            "score": score,
            "direction": direction,
            "last_swing": last_swing,
            "trend_duration": self._estimate_trend_duration(highs, lows, direction)
        }

    def _find_swings(
        self,
        prices: List[float],
        swing_type: str
    ) -> List[float]:
        """
        Find swing highs or lows.

        Simplified: uses local max/min with lookback.
        """
        swings = []
        n = len(prices)

        for i in range(self.swing_strength, n - self.swing_strength):
            window = prices[i - self.swing_strength:i + self.swing_strength + 1]

            if swing_type == "high":
                if prices[i] == max(window):
                    swings.append(prices[i])
            else:  # low
                if prices[i] == min(window):
                    swings.append(prices[i])

        return swings if swings else prices[-2:]  # Fallback

    def _analyze_ma_alignment(
        self,
        closes: List[float],
        ema_20: List[float],
        ema_50: List[float]
    ) -> dict:
        """
        Analyze MA alignment for trend direction.

        Returns:
            dict with score, direction
        """
        if not ema_20 or not ema_50:
            return {"score": 0.5, "direction": 0}

        current_price = closes[-1]
        current_ema20 = ema_20[-1]
        current_ema50 = ema_50[-1]

        # Bullish: price > ema20 > ema50
        # Bearish: price < ema20 < ema50

        price_above_ema20 = current_price > current_ema20
        ema20_above_ema50 = current_ema20 > current_ema50

        if price_above_ema20 and ema20_above_ema50:
            return {"score": 0.9, "direction": 1}
        elif not price_above_ema20 and not ema20_above_ema50:
            return {"score": 0.1, "direction": -1}
        elif price_above_ema20:
            return {"score": 0.6, "direction": 1}
        elif ema20_above_ema50:
            return {"score": 0.4, "direction": 0}
        else:
            return {"score": 0.5, "direction": 0}

    def _estimate_trend_duration(
        self,
        highs: List[float],
        lows: List[float],
        direction: int
    ) -> int:
        """Estimate how many bars the current trend has lasted."""
        if direction == 0:
            return 0

        count = 0
        for i in range(len(highs) - 1, 0, -1):
            if direction == 1:  # Bullish
                if lows[i] < lows[i-1]:  # Lower low breaks uptrend
                    break
            else:  # Bearish
                if highs[i] > highs[i-1]:  # Higher high breaks downtrend
                    break
            count += 1

        return count
```

### 3.3 Alignment Calculation

```python
def calculate_alignment(
    self,
    ltf_signal_direction: int,   # 1 = bullish FVG, -1 = bearish FVG
    htf_trend: HTFTrendInfo
) -> MTFAlignmentResult:
    """
    Calculate alignment between LTF signal and HTF trend.

    Args:
        ltf_signal_direction: Direction of the LTF FVG signal
        htf_trend: HTF trend information

    Returns:
        MTFAlignmentResult with alignment details
    """
    htf_direction = htf_trend.trend_direction
    htf_strength = htf_trend.trend_strength

    # Calculate alignment score
    if htf_direction == 0:  # Neutral HTF
        alignment_score = 0.5
        aligned = True  # OK to trade either direction
        filter_passed = True
        alignment_bonus = 1.0
    elif ltf_signal_direction == htf_direction:  # Aligned
        alignment_score = 0.5 + (htf_strength * 0.5)  # 0.5 to 1.0
        aligned = True
        filter_passed = True
        alignment_bonus = 1.0 + (htf_strength * 0.3)  # 1.0 to 1.3
    else:  # Counter-trend
        alignment_score = 0.5 - (htf_strength * 0.5)  # 0.0 to 0.5
        aligned = False
        # Filter: only pass if HTF trend is weak
        filter_passed = htf_strength < 0.5
        alignment_bonus = 0.7  # Penalty for counter-trend

    return MTFAlignmentResult(
        mtf_aligned=aligned,
        mtf_alignment_score=round(alignment_score, 3),
        mtf_filter_passed=filter_passed,
        htf_trend=htf_trend,
        alignment_bonus=round(alignment_bonus, 2)
    )
```

---

## 4. OUTPUT FIELDS

### 4.1 BarState Fields (Python Layer 2)

```python
# === MTF ALIGNMENT (Module #10) ===

# HTF Trend Info
htf_trend_state: str             # "bullish_strong", "bearish_weak", etc.
htf_trend_direction: int         # 1, -1, 0
htf_trend_strength: float        # 0-1
htf_last_swing: str              # "HH", "HL", "LH", "LL"
htf_structure_score: float       # 0-1
htf_ma_score: float              # 0-1

# Alignment (calculated per FVG signal)
mtf_aligned: bool                # Is signal aligned with HTF?
mtf_alignment_score: float       # 0-1
mtf_filter_passed: bool          # Should we take signal?
mtf_alignment_bonus: float       # Multiplier for confluence
```

### 4.2 Sample Output

```json
{
    "htf_trend_state": "bullish_strong",
    "htf_trend_direction": 1,
    "htf_trend_strength": 0.82,
    "htf_last_swing": "HL",
    "htf_structure_score": 0.85,
    "htf_ma_score": 0.78,

    "mtf_aligned": true,
    "mtf_alignment_score": 0.91,
    "mtf_filter_passed": true,
    "mtf_alignment_bonus": 1.25
}
```

---

## 5. TIMEFRAME CONFIGURATION

### 5.1 Typical Configurations

| Entry TF | HTF for Trend | HTF Ratio |
|----------|---------------|-----------|
| 1m | 15m | 15:1 |
| 5m | 1H | 12:1 |
| 15m | 4H | 16:1 |
| 1H | Daily | 24:1 |

### 5.2 Data Requirements

```python
# For each bar on Entry TF, need:
htf_data = {
    "htf_high": float,           # HTF bar high
    "htf_low": float,            # HTF bar low
    "htf_close": float,          # HTF bar close
    "htf_ema_20": float,         # Optional: HTF 20 EMA
    "htf_ema_50": float,         # Optional: HTF 50 EMA
    "htf_last_swing_high": float,
    "htf_last_swing_low": float
}
```

---

## 6. NINJA EXPORT REQUIREMENTS

### 6.1 Fields Needed from Layer 1 (NinjaTrader)

| Field | Type | Description |
|-------|------|-------------|
| `htf_high` | float | Higher TF bar high |
| `htf_low` | float | Higher TF bar low |
| `htf_close` | float | Higher TF bar close |
| `htf_ema_20` | float | Higher TF 20 EMA (optional) |
| `htf_ema_50` | float | Higher TF 50 EMA (optional) |
| `htf_is_swing_high` | bool | HTF swing high detection |
| `htf_is_swing_low` | bool | HTF swing low detection |

### 6.2 Implementation Options

**Option A: Export HTF OHLC (Recommended)**
- NinjaTrader exports HTF bar data for each LTF bar
- Python calculates everything else
- Simpler Ninja indicator

**Option B: Export HTF Indicators**
- NinjaTrader exports pre-calculated EMAs, swings
- Less Python computation
- More complex Ninja indicator

### 6.3 Computation Location

| Calculation | Location | Reason |
|-------------|----------|--------|
| HTF Bar Data | NinjaTrader | Multi-series access |
| Swing Detection | NinjaTrader or Python | Built-in indicator vs custom |
| EMA | NinjaTrader or Python | Built-in indicator |
| Trend Classification | Python | Complex logic |
| Alignment Score | Python | Signal comparison |

---

## 7. UNIT TESTS

```python
def test_bullish_strong_trend():
    """Test detection of strong bullish trend."""
    module = MTFAlignmentModule()

    # Mock data: clear uptrend
    highs = [100, 101, 102, 103, 104, 105]  # Rising highs
    lows = [99, 100, 101, 102, 103, 104]    # Rising lows
    closes = [99.5, 100.5, 101.5, 102.5, 103.5, 104.5]

    result = module.detect_htf_trend(highs, lows, closes)

    assert result.trend_state == TrendState.BULLISH_STRONG
    assert result.trend_direction == 1
    assert result.trend_strength >= 0.7


def test_alignment_with_trend():
    """Test bullish signal aligned with bullish HTF."""
    module = MTFAlignmentModule()

    htf_trend = HTFTrendInfo(
        trend_state=TrendState.BULLISH_STRONG,
        trend_direction=1,
        trend_strength=0.8,
        last_swing_type="HL",
        structure_score=0.85,
        ma_score=0.8,
        days_in_trend=10
    )

    result = module.calculate_alignment(
        ltf_signal_direction=1,  # Bullish FVG
        htf_trend=htf_trend
    )

    assert result.mtf_aligned is True
    assert result.mtf_filter_passed is True
    assert result.mtf_alignment_score > 0.8
    assert result.alignment_bonus > 1.0


def test_counter_trend_filtered():
    """Test bearish signal filtered in strong bullish HTF."""
    module = MTFAlignmentModule()

    htf_trend = HTFTrendInfo(
        trend_state=TrendState.BULLISH_STRONG,
        trend_direction=1,
        trend_strength=0.85,
        last_swing_type="HL",
        structure_score=0.9,
        ma_score=0.85,
        days_in_trend=15
    )

    result = module.calculate_alignment(
        ltf_signal_direction=-1,  # Bearish FVG (counter-trend)
        htf_trend=htf_trend
    )

    assert result.mtf_aligned is False
    assert result.mtf_filter_passed is False  # Strong HTF = filter counter-trend


def test_counter_trend_allowed_weak_htf():
    """Test counter-trend signal allowed in weak HTF."""
    module = MTFAlignmentModule()

    htf_trend = HTFTrendInfo(
        trend_state=TrendState.BULLISH_WEAK,
        trend_direction=1,
        trend_strength=0.3,  # Weak
        last_swing_type="HL",
        structure_score=0.6,
        ma_score=0.55,
        days_in_trend=3
    )

    result = module.calculate_alignment(
        ltf_signal_direction=-1,  # Bearish FVG
        htf_trend=htf_trend
    )

    assert result.mtf_aligned is False
    assert result.mtf_filter_passed is True  # Weak HTF = allow counter-trend
    assert result.alignment_bonus < 1.0  # But with penalty
```

---

## 8. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial spec - structure + MA based trend detection |

---

## 9. NOTES

### 9.1 Why Structure-Based (not just MA)?
- MA lags significantly
- Structure (HH/HL/LH/LL) is real-time
- SMC naturally uses structure for trend

### 9.2 Counter-Trend Trading
- Not completely disabled
- Allowed when HTF trend is weak
- Uses reduced size (via alignment_bonus < 1.0)
- Better to miss some good counter-trend trades than take many bad ones

### 9.3 Future Enhancements (v2.0)
- Multiple HTF analysis (1H + 4H + Daily)
- Trend change detection (CHoCH on HTF)
- Momentum divergence between TFs
- Session-based HTF bias (overnight gap, opening range)
