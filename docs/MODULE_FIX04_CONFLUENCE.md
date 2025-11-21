# MODULE #04: CONFLUENCE SCORING

## VERSION: 1.0
## STATUS: New Spec
## PRIORITY: HIGH (Core FVG Enhancement)

---

## 1. MODULE OVERVIEW

### 1.1 Mục Đích
Tính **Confluence Score** cho FVG signal dựa trên sự kết hợp của nhiều yếu tố SMC xung quanh FVG. Confluence càng cao → Signal càng strong.

### 1.2 Nguyên Lý SMC
> "Institutional traders don't act on single signals - they wait for multiple confluences to align"

**Key Confluences trong SMC:**
- FVG nằm trong/gần Order Block
- FVG được hỗ trợ bởi cấu trúc (Structure Context)
- FVG align với MTF direction
- FVG gần Liquidity Pool
- FVG có Volume confirmation

### 1.3 Vị Trí Trong Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONFLUENCE PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [FVG Quality]     [Structure Context]    [MTF Alignment]       │
│       │                   │                     │               │
│       ▼                   ▼                     ▼               │
│  fvg_strength_score  context_multiplier   mtf_alignment_score   │
│       │                   │                     │               │
│       └───────────────────┼─────────────────────┘               │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │   CONFLUENCE ENGINE    │                        │
│              │                        │                        │
│              │  + OB Proximity Score  │                        │
│              │  + Liquidity Score     │                        │
│              │  + Volume Confirm      │                        │
│              │                        │                        │
│              │  = confluence_score    │                        │
│              │  = confluence_factors  │                        │
│              └────────────────────────┘                        │
│                           │                                     │
│                           ▼                                     │
│                    EventState.signal                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. CONFLUENCE FACTORS

### 2.1 Factor List (Weighted)

| Factor | Weight | Source | Description |
|--------|--------|--------|-------------|
| `ob_proximity` | 0.25 | Module #01 | FVG nằm trong/gần OB |
| `structure_context` | 0.25 | Module #03 | Expansion/Retracement/Continuation |
| `fvg_strength` | 0.20 | Module #02 | Strong/Medium/Weak FVG |
| `mtf_alignment` | 0.15 | Module #10 | Higher TF trend alignment |
| `liquidity_proximity` | 0.10 | Module #11 | Gần untested liquidity |
| `volume_confirm` | 0.05 | BarState | Volume spike on FVG creation |

**Total Weight = 1.0**

### 2.2 Factor Score Ranges

Mỗi factor trả về score từ **0.0 đến 1.0**:

```python
# Score interpretation
0.0 - 0.3  → Weak/No confluence
0.3 - 0.6  → Moderate confluence
0.6 - 0.8  → Good confluence
0.8 - 1.0  → Strong confluence
```

---

## 3. FACTOR CALCULATIONS

### 3.1 OB Proximity Score

FVG có giá trị cao hơn khi nằm trong hoặc gần Order Block:

```python
def calculate_ob_proximity_score(
    fvg_top: float,
    fvg_bottom: float,
    ob_top: float,
    ob_bottom: float,
    atr: float
) -> float:
    """
    Calculate proximity score between FVG and nearest relevant OB.

    Cases:
    - FVG inside OB: 1.0 (perfect confluence)
    - FVG overlaps OB: 0.7-0.9
    - FVG near OB (within 1 ATR): 0.4-0.7
    - FVG far from OB: 0.0-0.4

    Returns:
        float: Score 0.0 to 1.0
    """
    if ob_top is None or ob_bottom is None:
        return 0.0  # No nearby OB

    # Check if FVG is completely inside OB
    if fvg_top <= ob_top and fvg_bottom >= ob_bottom:
        return 1.0

    # Check overlap
    overlap_top = min(fvg_top, ob_top)
    overlap_bottom = max(fvg_bottom, ob_bottom)

    if overlap_top > overlap_bottom:
        # There is overlap
        overlap_size = overlap_top - overlap_bottom
        fvg_size = fvg_top - fvg_bottom
        overlap_ratio = overlap_size / fvg_size if fvg_size > 0 else 0
        return 0.7 + (0.3 * overlap_ratio)  # 0.7 to 1.0

    # Calculate distance
    if fvg_bottom > ob_top:
        distance = fvg_bottom - ob_top
    else:
        distance = ob_bottom - fvg_top

    # Score based on ATR distance
    distance_atr = distance / atr if atr > 0 else float('inf')

    if distance_atr <= 0.5:
        return 0.6  # Very close
    elif distance_atr <= 1.0:
        return 0.4  # Within 1 ATR
    elif distance_atr <= 2.0:
        return 0.2  # Within 2 ATR
    else:
        return 0.0  # Too far
```

### 3.2 Structure Context Score

Dựa trên output từ Module #03:

```python
def calculate_structure_score(context_type: str, context_multiplier: float) -> float:
    """
    Convert structure context to confluence score.

    Args:
        context_type: "expansion", "retracement", "continuation"
        context_multiplier: 1.2, 1.0, 0.8 từ Module #03

    Returns:
        float: Score 0.0 to 1.0
    """
    score_map = {
        "expansion": 1.0,      # Best - new trend starting
        "continuation": 0.7,   # Good - trend continuing
        "retracement": 0.5,    # OK - counter-trend pullback
        "unknown": 0.3         # No clear context
    }

    base_score = score_map.get(context_type, 0.3)

    # Adjust by multiplier strength
    if context_multiplier >= 1.2:
        return min(1.0, base_score * 1.1)
    elif context_multiplier <= 0.8:
        return base_score * 0.9

    return base_score
```

### 3.3 FVG Strength Score

Trực tiếp từ Module #02:

```python
def calculate_fvg_strength_score(strength_class: str, strength_score: float) -> float:
    """
    Use FVG strength from Module #02 directly.

    Args:
        strength_class: "Strong", "Medium", "Weak"
        strength_score: 0-1 composite score từ Module #02

    Returns:
        float: Score 0.0 to 1.0
    """
    # Use the pre-calculated strength score directly
    return strength_score
```

### 3.4 MTF Alignment Score

Dựa trên output từ Module #10:

```python
def calculate_mtf_alignment_score(
    fvg_direction: int,  # 1 = bullish, -1 = bearish
    htf_trend: str,      # "bullish", "bearish", "neutral"
    htf_strength: float  # 0-1 trend strength
) -> float:
    """
    Score based on alignment with higher timeframe trend.

    Args:
        fvg_direction: Direction of FVG signal
        htf_trend: Higher timeframe trend direction
        htf_strength: Strength of HTF trend

    Returns:
        float: Score 0.0 to 1.0
    """
    # Map trend to direction
    trend_direction = {
        "bullish": 1,
        "bearish": -1,
        "neutral": 0
    }.get(htf_trend, 0)

    if trend_direction == 0:
        return 0.5  # Neutral - no bias

    if fvg_direction == trend_direction:
        # Aligned with HTF trend
        return 0.6 + (0.4 * htf_strength)  # 0.6 to 1.0
    else:
        # Against HTF trend
        return 0.4 - (0.3 * htf_strength)  # 0.1 to 0.4
```

### 3.5 Liquidity Proximity Score

Dựa trên output từ Module #11:

```python
def calculate_liquidity_score(
    fvg_direction: int,
    nearest_liquidity_distance: float,
    liquidity_type: str,  # "equal_highs", "equal_lows", "swing"
    atr: float
) -> float:
    """
    Score based on proximity to untested liquidity.

    Logic:
    - Bullish FVG gần liquidity phía trên (targets) = good
    - Bearish FVG gần liquidity phía dưới (targets) = good
    - FVG có clear liquidity target trong 3 ATR = good

    Returns:
        float: Score 0.0 to 1.0
    """
    if nearest_liquidity_distance is None:
        return 0.3  # No clear liquidity target

    distance_atr = nearest_liquidity_distance / atr if atr > 0 else float('inf')

    # Closer liquidity = better target
    if distance_atr <= 1.0:
        base_score = 1.0
    elif distance_atr <= 2.0:
        base_score = 0.8
    elif distance_atr <= 3.0:
        base_score = 0.6
    else:
        base_score = 0.3  # Too far to be meaningful target

    # Bonus for equal highs/lows (stronger liquidity)
    if liquidity_type in ["equal_highs", "equal_lows"]:
        base_score = min(1.0, base_score * 1.1)

    return base_score
```

### 3.6 Volume Confirmation Score

```python
def calculate_volume_score(
    fvg_creation_volume: int,
    median_volume_20: float,
    fvg_delta_alignment: int  # From Module #02
) -> float:
    """
    Score based on volume characteristics when FVG was created.

    Returns:
        float: Score 0.0 to 1.0
    """
    if median_volume_20 == 0:
        return 0.5  # No volume data

    vol_ratio = fvg_creation_volume / median_volume_20

    # Base score from volume ratio
    if vol_ratio >= 2.0:
        base_score = 1.0  # High volume FVG
    elif vol_ratio >= 1.5:
        base_score = 0.8
    elif vol_ratio >= 1.0:
        base_score = 0.6
    else:
        base_score = 0.4  # Low volume

    # Bonus for delta alignment
    if fvg_delta_alignment == 1:  # Delta aligned with FVG direction
        base_score = min(1.0, base_score * 1.1)
    elif fvg_delta_alignment == -1:  # Delta against FVG
        base_score = base_score * 0.8

    return base_score
```

---

## 4. CONFLUENCE ENGINE

### 4.1 Main Calculation

```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ConfluenceResult:
    """Result of confluence calculation."""
    confluence_score: float           # 0-1 weighted score
    confluence_class: str             # "Strong", "Moderate", "Weak"
    factor_scores: Dict[str, float]   # Individual factor scores
    factor_weights: Dict[str, float]  # Applied weights
    contributing_factors: List[str]   # Factors scoring > 0.6


# Factor weights - can be adjusted based on backtesting
CONFLUENCE_WEIGHTS = {
    "ob_proximity": 0.25,
    "structure_context": 0.25,
    "fvg_strength": 0.20,
    "mtf_alignment": 0.15,
    "liquidity_proximity": 0.10,
    "volume_confirm": 0.05
}


def calculate_confluence_score(
    # OB Proximity inputs
    fvg_top: float,
    fvg_bottom: float,
    nearest_ob_top: Optional[float],
    nearest_ob_bottom: Optional[float],

    # Structure Context inputs (from Module #03)
    structure_context_type: str,
    structure_context_multiplier: float,

    # FVG Strength inputs (from Module #02)
    fvg_strength_class: str,
    fvg_strength_score: float,

    # MTF Alignment inputs (from Module #10)
    fvg_direction: int,
    htf_trend: str,
    htf_strength: float,

    # Liquidity inputs (from Module #11)
    nearest_liquidity_distance: Optional[float],
    liquidity_type: Optional[str],

    # Volume inputs
    fvg_creation_volume: int,
    median_volume_20: float,
    fvg_delta_alignment: int,

    # Common
    atr: float
) -> ConfluenceResult:
    """
    Calculate comprehensive confluence score for FVG signal.

    Returns:
        ConfluenceResult with score, class, and breakdown
    """

    # Calculate individual factor scores
    factor_scores = {
        "ob_proximity": calculate_ob_proximity_score(
            fvg_top, fvg_bottom, nearest_ob_top, nearest_ob_bottom, atr
        ),
        "structure_context": calculate_structure_score(
            structure_context_type, structure_context_multiplier
        ),
        "fvg_strength": fvg_strength_score,  # Direct from Module #02
        "mtf_alignment": calculate_mtf_alignment_score(
            fvg_direction, htf_trend, htf_strength
        ),
        "liquidity_proximity": calculate_liquidity_score(
            fvg_direction, nearest_liquidity_distance, liquidity_type, atr
        ),
        "volume_confirm": calculate_volume_score(
            fvg_creation_volume, median_volume_20, fvg_delta_alignment
        )
    }

    # Calculate weighted score
    weighted_sum = sum(
        factor_scores[factor] * weight
        for factor, weight in CONFLUENCE_WEIGHTS.items()
    )

    # Classify confluence
    if weighted_sum >= 0.75:
        confluence_class = "Strong"
    elif weighted_sum >= 0.50:
        confluence_class = "Moderate"
    else:
        confluence_class = "Weak"

    # Find contributing factors (> 0.6)
    contributing = [
        factor for factor, score in factor_scores.items()
        if score >= 0.6
    ]

    return ConfluenceResult(
        confluence_score=round(weighted_sum, 3),
        confluence_class=confluence_class,
        factor_scores=factor_scores,
        factor_weights=CONFLUENCE_WEIGHTS,
        contributing_factors=contributing
    )
```

### 4.2 Classification Thresholds

```python
# Confluence classification
CONFLUENCE_THRESHOLDS = {
    "Strong": 0.75,      # 3+ strong factors aligned
    "Moderate": 0.50,    # Some confluence present
    "Weak": 0.0          # Minimal/no confluence
}

# Minimum confluence for signal generation
MIN_CONFLUENCE_FOR_SIGNAL = 0.40  # Below this = skip
```

---

## 5. OUTPUT FIELDS

### 5.1 EventState Fields (Python Layer 2)

```python
# === CONFLUENCE (Module #04) ===
confluence_score: float              # 0-1 weighted score
confluence_class: str                # "Strong" / "Moderate" / "Weak"

# Factor breakdown
conf_ob_proximity: float             # 0-1 OB proximity score
conf_structure: float                # 0-1 structure context score
conf_fvg_strength: float             # 0-1 FVG strength score
conf_mtf_alignment: float            # 0-1 MTF alignment score
conf_liquidity: float                # 0-1 liquidity proximity score
conf_volume: float                   # 0-1 volume confirmation score

# Factor count
confluence_factor_count: int         # Number of factors > 0.6
confluence_factors_list: List[str]   # Names of contributing factors
```

### 5.2 Sample Output

```json
{
    "confluence_score": 0.78,
    "confluence_class": "Strong",

    "conf_ob_proximity": 0.85,
    "conf_structure": 0.90,
    "conf_fvg_strength": 0.72,
    "conf_mtf_alignment": 0.65,
    "conf_liquidity": 0.70,
    "conf_volume": 0.80,

    "confluence_factor_count": 6,
    "confluence_factors_list": ["ob_proximity", "structure_context", "fvg_strength", "mtf_alignment", "liquidity_proximity", "volume_confirm"]
}
```

---

## 6. INTEGRATION WITH OTHER MODULES

### 6.1 Input Dependencies

| Module | Field Used | Purpose |
|--------|-----------|---------|
| #01 OB Quality | `nearest_ob_top/bottom` | OB proximity calculation |
| #02 FVG Quality | `fvg_strength_score`, `fvg_delta_alignment` | Direct FVG strength |
| #03 Structure Context | `context_type`, `context_multiplier` | Structure score |
| #10 MTF Alignment | `htf_trend`, `htf_strength` | Trend alignment |
| #11 Liquidity Map | `nearest_liquidity_distance`, `liquidity_type` | Target proximity |

### 6.2 Output Usage

Confluence score được sử dụng trong:
- **Signal filtering**: Skip signals với confluence < 0.40
- **Position sizing** (future): Higher confluence = larger position
- **ML features**: confluence_score là feature quan trọng cho model

---

## 7. NINJA EXPORT REQUIREMENTS

### 7.1 Fields Needed from Layer 1 (NinjaTrader)

Module này **KHÔNG cần thêm fields mới** từ NinjaTrader.

Tất cả inputs đều đến từ:
- Existing FVG/OB detection (đã có)
- Other Python modules (#01, #02, #03, #10, #11)
- BarState fields đã có (volume, ATR)

### 7.2 Computation Location

| Calculation | Location | Reason |
|-------------|----------|--------|
| OB Proximity | Python | Needs FVG + OB comparison |
| Structure Context | Python | Module #03 output |
| FVG Strength | Python | Module #02 output |
| MTF Alignment | Python | Module #10 output |
| Liquidity Proximity | Python | Module #11 output |
| Volume Confirm | Python | Simple ratio calculation |
| **Final Score** | Python | Weighted aggregation |

---

## 8. UNIT TESTS

```python
def test_confluence_strong():
    """Test strong confluence scenario."""
    result = calculate_confluence_score(
        fvg_top=100.5, fvg_bottom=100.0,
        nearest_ob_top=101.0, nearest_ob_bottom=99.5,  # FVG inside OB
        structure_context_type="expansion",
        structure_context_multiplier=1.2,
        fvg_strength_class="Strong",
        fvg_strength_score=0.85,
        fvg_direction=1,
        htf_trend="bullish",
        htf_strength=0.8,
        nearest_liquidity_distance=1.5,
        liquidity_type="equal_highs",
        fvg_creation_volume=5000,
        median_volume_20=2500,
        fvg_delta_alignment=1,
        atr=1.0
    )

    assert result.confluence_score >= 0.75
    assert result.confluence_class == "Strong"
    assert len(result.contributing_factors) >= 4


def test_confluence_weak():
    """Test weak confluence scenario."""
    result = calculate_confluence_score(
        fvg_top=100.5, fvg_bottom=100.0,
        nearest_ob_top=None, nearest_ob_bottom=None,  # No nearby OB
        structure_context_type="unknown",
        structure_context_multiplier=1.0,
        fvg_strength_class="Weak",
        fvg_strength_score=0.3,
        fvg_direction=1,
        htf_trend="bearish",  # Against FVG
        htf_strength=0.7,
        nearest_liquidity_distance=None,  # No clear target
        liquidity_type=None,
        fvg_creation_volume=1000,
        median_volume_20=2500,  # Low volume
        fvg_delta_alignment=-1,
        atr=1.0
    )

    assert result.confluence_score < 0.50
    assert result.confluence_class == "Weak"
    assert len(result.contributing_factors) <= 1


def test_confluence_moderate():
    """Test moderate confluence scenario."""
    result = calculate_confluence_score(
        fvg_top=100.5, fvg_bottom=100.0,
        nearest_ob_top=101.5, nearest_ob_bottom=101.0,  # OB near but not overlapping
        structure_context_type="continuation",
        structure_context_multiplier=1.0,
        fvg_strength_class="Medium",
        fvg_strength_score=0.55,
        fvg_direction=1,
        htf_trend="bullish",
        htf_strength=0.5,
        nearest_liquidity_distance=2.5,
        liquidity_type="swing",
        fvg_creation_volume=3000,
        median_volume_20=2500,
        fvg_delta_alignment=0,
        atr=1.0
    )

    assert 0.50 <= result.confluence_score < 0.75
    assert result.confluence_class == "Moderate"
```

---

## 9. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial spec - 6 factor confluence engine |

---

## 10. NOTES

### 10.1 Weight Tuning
Weights có thể điều chỉnh dựa trên backtesting results. Các candidates để tăng weight:
- `ob_proximity` - nếu OB confluence cho win rate cao hơn
- `fvg_strength` - nếu strong FVG tự nó đã đủ predictive

### 10.2 Future Enhancements
- **Dynamic weights**: Adjust weights based on market condition
- **Confluence decay**: Score giảm theo thời gian nếu FVG chưa được test
- **Confluence clusters**: Detect areas với nhiều confluences
