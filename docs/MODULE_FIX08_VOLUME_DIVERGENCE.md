# MODULE #08: VOLUME DIVERGENCE (SIMPLIFIED)

## VERSION: 1.1
## STATUS: Updated Spec (Simplified)
## PRIORITY: MEDIUM (Confluence Factor)

---

## 1. MODULE OVERVIEW

### 1.1 Mục Đích
Detect **Volume/Delta Divergence** tại swing points để:
- Identify momentum exhaustion
- Add confluence to FVG signals
- Filter out weak momentum setups

### 1.2 Nguyên Lý
> "When price makes new extremes but delta doesn't confirm, momentum is exhausting"

**Simplified Approach (v1.1):**
- Focus ONLY on swing-delta divergence
- Remove approximate absorption (complex, noisy)
- Simple: Compare delta at consecutive swing points

### 1.3 Vị Trí Trong Pipeline

```
+-------------------------------------------------------------+
|            VOLUME DIVERGENCE FLOW (Simplified)              |
+-------------------------------------------------------------+
|  [Swing Points Detection]                                   |
|       |                                                     |
|       v                                                     |
|  +---------------- SWING-DELTA DIVERGENCE ----------------+ |
|  |  Bullish: Price LL + Delta less negative               | |
|  |  Bearish: Price HH + Delta less positive               | |
|  +--------------------------------------------------------+ |
|       |                                                     |
|       v                                                     |
|  [has_divergence, div_type, div_score]                      |
+-------------------------------------------------------------+
```

---

## 2. DIVERGENCE PATTERNS

### 2.1 Bullish Divergence

```
Price:  Higher Low (HL) or Lower Low (LL)
Delta:  Less negative than previous swing low
        (selling pressure weakening)

Signal: Potential reversal UP
```

**Example:**
```
Swing Low 1: Price = 100.00, Delta = -500 (strong selling)
Swing Low 2: Price = 99.80,  Delta = -200 (weaker selling)
             -> Lower price but less selling = BULLISH DIVERGENCE
```

### 2.2 Bearish Divergence

```
Price:  Lower High (LH) or Higher High (HH)
Delta:  Less positive than previous swing high
        (buying pressure weakening)

Signal: Potential reversal DOWN
```

**Example:**
```
Swing High 1: Price = 100.00, Delta = +500 (strong buying)
Swing High 2: Price = 100.20, Delta = +200 (weaker buying)
              -> Higher price but less buying = BEARISH DIVERGENCE
```

---

## 3. CALCULATION LOGIC

### 3.1 Data Structures

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SwingPoint:
    """A swing high or low with associated delta."""
    bar_index: int
    price: float
    delta: float              # Single bar delta at swing
    cumulative_delta: float   # Running cumulative delta
    swing_type: str           # "high" or "low"


@dataclass
class DivergenceResult:
    """Result of divergence detection."""
    has_divergence: bool
    div_type: str             # "bullish", "bearish", "none"
    div_score: float          # 0-1 strength
    div_bars_apart: int       # Bars between divergent swings
    swing1_price: Optional[float]
    swing2_price: Optional[float]
    swing1_delta: Optional[float]
    swing2_delta: Optional[float]
```

### 3.2 Main Detection Logic

```python
class VolumeDivergenceModule:
    """
    Simplified Volume Divergence Detection.

    Only detects swing-delta divergence at swing points.
    Removed: Approximate absorption (too noisy for v1.0)
    """

    def __init__(
        self,
        lookback_swings: int = 5,
        min_swing_distance: int = 5,
        min_delta_diff_pct: float = 0.2  # 20% delta difference required
    ):
        self.lookback_swings = lookback_swings
        self.min_swing_distance = min_swing_distance
        self.min_delta_diff_pct = min_delta_diff_pct

        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []

    def process_bar(self, bar_state: dict) -> dict:
        """
        Process a bar and detect divergence.

        Args:
            bar_state: Bar data including is_swing_high/low, delta

        Returns:
            dict with divergence fields added
        """
        # Update swing history
        self._update_swings(bar_state)

        # Check for divergence
        result = self._detect_divergence()

        # Add to bar_state
        return {
            **bar_state,
            "has_divergence": result.has_divergence,
            "div_type": result.div_type,
            "div_score": result.div_score,
            "div_bars_apart": result.div_bars_apart
        }

    def _update_swings(self, bar_state: dict):
        """Update swing point history."""
        bar_index = bar_state.get("bar_index", 0)
        delta = bar_state.get("delta", 0)
        cumulative_delta = bar_state.get("cumulative_delta", 0)

        if bar_state.get("is_swing_high", False):
            swing = SwingPoint(
                bar_index=bar_index,
                price=bar_state["high"],
                delta=delta,
                cumulative_delta=cumulative_delta,
                swing_type="high"
            )
            self.swing_highs.append(swing)
            if len(self.swing_highs) > self.lookback_swings:
                self.swing_highs.pop(0)

        if bar_state.get("is_swing_low", False):
            swing = SwingPoint(
                bar_index=bar_index,
                price=bar_state["low"],
                delta=delta,
                cumulative_delta=cumulative_delta,
                swing_type="low"
            )
            self.swing_lows.append(swing)
            if len(self.swing_lows) > self.lookback_swings:
                self.swing_lows.pop(0)

    def _detect_divergence(self) -> DivergenceResult:
        """
        Detect divergence between last 2 swings.

        Returns:
            DivergenceResult with divergence info
        """
        # Check bearish divergence (at swing highs)
        bear_div = self._check_bearish_divergence()

        # Check bullish divergence (at swing lows)
        bull_div = self._check_bullish_divergence()

        # Return stronger divergence
        if bear_div.has_divergence and bull_div.has_divergence:
            return bear_div if bear_div.div_score > bull_div.div_score else bull_div
        elif bear_div.has_divergence:
            return bear_div
        elif bull_div.has_divergence:
            return bull_div
        else:
            return DivergenceResult(
                has_divergence=False,
                div_type="none",
                div_score=0.0,
                div_bars_apart=0,
                swing1_price=None,
                swing2_price=None,
                swing1_delta=None,
                swing2_delta=None
            )

    def _check_bearish_divergence(self) -> DivergenceResult:
        """
        Check for bearish divergence at swing highs.

        Pattern: Price HH + Delta weaker (less positive)
        """
        if len(self.swing_highs) < 2:
            return self._null_result()

        sh1 = self.swing_highs[-2]  # Previous
        sh2 = self.swing_highs[-1]  # Recent

        # Check minimum distance
        bars_apart = sh2.bar_index - sh1.bar_index
        if bars_apart < self.min_swing_distance:
            return self._null_result()

        # Price condition: Higher High (or equal)
        if sh2.price < sh1.price:
            return self._null_result()

        # Delta condition: Weaker (less positive or more negative)
        delta_weakening = sh1.cumulative_delta > sh2.cumulative_delta

        if not delta_weakening:
            return self._null_result()

        # Calculate score based on divergence magnitude
        delta_diff = sh1.cumulative_delta - sh2.cumulative_delta
        delta_base = abs(sh1.cumulative_delta) if sh1.cumulative_delta != 0 else 1
        delta_diff_pct = delta_diff / delta_base

        if delta_diff_pct < self.min_delta_diff_pct:
            return self._null_result()

        # Score: higher delta difference = stronger divergence
        score = min(delta_diff_pct / 0.5, 1.0)  # Cap at 50% diff = score 1.0

        return DivergenceResult(
            has_divergence=True,
            div_type="bearish",
            div_score=round(score, 3),
            div_bars_apart=bars_apart,
            swing1_price=sh1.price,
            swing2_price=sh2.price,
            swing1_delta=sh1.cumulative_delta,
            swing2_delta=sh2.cumulative_delta
        )

    def _check_bullish_divergence(self) -> DivergenceResult:
        """
        Check for bullish divergence at swing lows.

        Pattern: Price LL + Delta stronger (less negative)
        """
        if len(self.swing_lows) < 2:
            return self._null_result()

        sl1 = self.swing_lows[-2]
        sl2 = self.swing_lows[-1]

        bars_apart = sl2.bar_index - sl1.bar_index
        if bars_apart < self.min_swing_distance:
            return self._null_result()

        # Price condition: Lower Low (or equal)
        if sl2.price > sl1.price:
            return self._null_result()

        # Delta condition: Stronger (less negative)
        delta_strengthening = sl2.cumulative_delta > sl1.cumulative_delta

        if not delta_strengthening:
            return self._null_result()

        # Calculate score
        delta_diff = sl2.cumulative_delta - sl1.cumulative_delta
        delta_base = abs(sl1.cumulative_delta) if sl1.cumulative_delta != 0 else 1
        delta_diff_pct = delta_diff / delta_base

        if delta_diff_pct < self.min_delta_diff_pct:
            return self._null_result()

        score = min(delta_diff_pct / 0.5, 1.0)

        return DivergenceResult(
            has_divergence=True,
            div_type="bullish",
            div_score=round(score, 3),
            div_bars_apart=bars_apart,
            swing1_price=sl1.price,
            swing2_price=sl2.price,
            swing1_delta=sl1.cumulative_delta,
            swing2_delta=sl2.cumulative_delta
        )

    def _null_result(self) -> DivergenceResult:
        """Return null divergence result."""
        return DivergenceResult(
            has_divergence=False,
            div_type="none",
            div_score=0.0,
            div_bars_apart=0,
            swing1_price=None,
            swing2_price=None,
            swing1_delta=None,
            swing2_delta=None
        )
```

---

## 4. OUTPUT FIELDS

### 4.1 BarState Fields (Python Layer 2)

```python
# === VOLUME DIVERGENCE (Module #08) ===
has_divergence: bool         # Is divergence present
div_type: str                # "bullish", "bearish", "none"
div_score: float             # 0-1 divergence strength
div_bars_apart: int          # Bars between divergent swings
```

### 4.2 Sample Output

```json
{
    "has_divergence": true,
    "div_type": "bullish",
    "div_score": 0.65,
    "div_bars_apart": 12
}
```

---

## 5. INTEGRATION WITH CONFLUENCE

### 5.1 Confluence Score Contribution

```python
def calculate_divergence_confluence(
    has_divergence: bool,
    div_type: str,
    div_score: float,
    fvg_direction: int
) -> float:
    """
    Calculate confluence score from divergence.

    Divergence aligned with FVG direction = positive confluence.

    Returns:
        float: 0-1 confluence contribution
    """
    if not has_divergence:
        return 0.0

    # Check alignment
    if div_type == "bullish" and fvg_direction == 1:
        return div_score * 0.8  # Good confluence
    elif div_type == "bearish" and fvg_direction == -1:
        return div_score * 0.8
    elif div_type == "bullish" and fvg_direction == -1:
        return 0.2  # Counter signal - slight penalty
    elif div_type == "bearish" and fvg_direction == 1:
        return 0.2

    return 0.0
```

---

## 6. NINJA EXPORT REQUIREMENTS

### 6.1 Fields Needed from Layer 1 (NinjaTrader)

| Field | Type | Description |
|-------|------|-------------|
| `is_swing_high` | bool | Is this bar a swing high? |
| `is_swing_low` | bool | Is this bar a swing low? |
| `delta` | int | Bar delta (buy_vol - sell_vol) |
| `cumulative_delta` | int | Running cumulative delta |
| `high` | float | Bar high price |
| `low` | float | Bar low price |

**Note**: All these fields should already be in Phase 1 export.

### 6.2 Computation Location

| Calculation | Location | Reason |
|-------------|----------|--------|
| Swing Detection | NinjaTrader | Use built-in swing indicator |
| Delta | NinjaTrader | Volume delta calculation |
| Divergence Logic | Python | Compare swings with history |

---

## 7. UNIT TESTS

```python
def test_bullish_divergence():
    """Test bullish divergence detection."""
    module = VolumeDivergenceModule()

    # Setup: 2 swing lows, price LL, delta strengthening
    module.swing_lows = [
        SwingPoint(100, 100.0, -500, -1000, "low"),  # SL1
        SwingPoint(115, 99.5, -200, -700, "low")     # SL2: LL, delta less negative
    ]

    result = module._check_bullish_divergence()

    assert result.has_divergence is True
    assert result.div_type == "bullish"
    assert result.div_score > 0


def test_bearish_divergence():
    """Test bearish divergence detection."""
    module = VolumeDivergenceModule()

    # Setup: 2 swing highs, price HH, delta weakening
    module.swing_highs = [
        SwingPoint(100, 100.0, 500, 1000, "high"),  # SH1
        SwingPoint(115, 100.5, 200, 700, "high")    # SH2: HH, delta less positive
    ]

    result = module._check_bearish_divergence()

    assert result.has_divergence is True
    assert result.div_type == "bearish"
    assert result.div_score > 0


def test_no_divergence_not_enough_swings():
    """Test no divergence when insufficient swings."""
    module = VolumeDivergenceModule()

    module.swing_highs = [
        SwingPoint(100, 100.0, 500, 1000, "high")
    ]

    result = module._check_bearish_divergence()
    assert result.has_divergence is False


def test_no_divergence_delta_confirms():
    """Test no divergence when delta confirms price."""
    module = VolumeDivergenceModule()

    # Price HH, delta also stronger = NO divergence
    module.swing_highs = [
        SwingPoint(100, 100.0, 300, 800, "high"),
        SwingPoint(115, 100.5, 500, 1200, "high")  # HH with stronger delta
    ]

    result = module._check_bearish_divergence()
    assert result.has_divergence is False
```

---

## 8. WHAT WAS REMOVED (v1.1)

### 8.1 Approximate Absorption (Removed)

**Reason for removal:**
- Too noisy without proper order flow data
- Multiple conditions hard to tune
- Added complexity without clear benefit
- Can add back in v2.0 with better data

### 8.2 Complex Scoring (Simplified)

**Before:** Complex score with multiple factors
**After:** Simple percentage-based score

---

## 9. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial spec with absorption |
| 1.1 | 2024-XX-XX | Simplified - removed absorption, focus on swing divergence |

---

## 10. NOTES

### 10.1 When Divergence is Most Useful
- At extended moves (after 3+ swings in one direction)
- Near key structure levels (OB, FVG zones)
- In ranging markets (less reliable in strong trends)

### 10.2 Future Enhancements (v2.0)
- Add hidden divergence detection
- Multi-timeframe divergence
- Absorption with proper footprint data
- Volume profile integration at divergence points
