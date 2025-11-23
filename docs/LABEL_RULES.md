# LABEL RULES - Layer Architecture V3

**Version:** 3.0.0
**Date:** November 23, 2025
**Layer:** 3 (ML Pipeline)
**Status:** Production Ready

---

## 1. Objective

### Problem Statement
ML models need consistent, rule-based labels to learn from historical data. Random or subjective labeling leads to poor model performance and inconsistent results.

### Solution
Implement **Label Rule (A)** - a deterministic labeling system that:
- Uses objective conditions from Layer 2 modules
- Integrates MGann swing analysis for entry timing
- Validates pullback wave strength before entry
- Produces consistent labels: `"long"`, `"short"`, or `"skip"`

### Success Criteria
- Label accuracy >= 70% (when validated against outcomes)
- Win rate >= 40% for labeled signals (after filtering)
- Consistent labeling across different market conditions

---

## 2. Input Schema

### Required Fields from EventState

```python
@dataclass
class LabelInput:
    # === CHoCH State ===
    ext_choch_down: bool      # External CHoCH from DOWN (for LONG)
    ext_choch_up: bool        # External CHoCH from UP (for SHORT)

    # === FVG State ===
    fvg_up: bool              # Bullish FVG exists
    fvg_down: bool            # Bearish FVG exists
    fvg_retest: bool          # FVG has been retested

    # === Direction ===
    ext_dir: int              # 1 = UP, -1 = DOWN, 0 = neutral

    # === MGann State ===
    mgann_leg_index: int      # Current leg index (1, 2, 3, ...)

    # === Wave Strength ===
    pb_wave_strength_ok: bool # Pullback wave strength confirmed
```

### Field Specifications

| Field | Type | Valid Values | Source |
|-------|------|--------------|--------|
| `ext_choch_down` | bool | True/False | Module #03 Structure Context |
| `ext_choch_up` | bool | True/False | Module #03 Structure Context |
| `fvg_up` | bool | True/False | Module #02 FVG Quality |
| `fvg_down` | bool | True/False | Module #02 FVG Quality |
| `fvg_retest` | bool | True/False | Module #12 FVG Retest |
| `ext_dir` | int | -1, 0, 1 | Module #03 Structure Context |
| `mgann_leg_index` | int | 1, 2, 3, ... | Module #14 MGann Swing |
| `pb_wave_strength_ok` | bool | True/False | Module #13 Wave Delta |

---

## 3. Output Schema

### Label Types

```python
LabelType = Literal["long", "short", "skip"]
```

### Output Fields

```python
@dataclass
class LabelOutput:
    label: str                    # "long" / "short" / "skip"
    label_confidence: float       # 0.0 - 1.0 (based on conditions met)
    label_reason: str             # Human-readable explanation
    conditions_met: List[str]     # List of satisfied conditions
    conditions_failed: List[str]  # List of failed conditions
```

---

## 4. Rule Logic

### 4.1 Label Rule (A) - LONG

```python
def apply_label_rule_long(event: dict) -> dict:
    """
    Apply Label Rule (A) for LONG signals.

    ALL conditions must be TRUE for label = "long"

    Args:
        event: EventState dictionary with required fields

    Returns:
        dict: {
            "label": "long" or "skip",
            "label_confidence": float,
            "label_reason": str,
            "conditions_met": list,
            "conditions_failed": list
        }
    """
    conditions = {
        "ext_choch_down": event.get("ext_choch_down", False) == True,
        "fvg_up": event.get("fvg_up", False) == True,
        "fvg_retest": event.get("fvg_retest", False) == True,
        "ext_dir_up": event.get("ext_dir", 0) == 1,
        "mgann_leg_early": event.get("mgann_leg_index", 99) <= 2,
        "pb_wave_ok": event.get("pb_wave_strength_ok", False) == True,
    }

    conditions_met = [k for k, v in conditions.items() if v]
    conditions_failed = [k for k, v in conditions.items() if not v]

    if all(conditions.values()):
        return {
            "label": "long",
            "label_confidence": 1.0,
            "label_reason": "All 6 LONG conditions satisfied",
            "conditions_met": conditions_met,
            "conditions_failed": []
        }
    else:
        confidence = len(conditions_met) / len(conditions)
        return {
            "label": "skip",
            "label_confidence": confidence,
            "label_reason": f"Failed: {', '.join(conditions_failed)}",
            "conditions_met": conditions_met,
            "conditions_failed": conditions_failed
        }
```

### 4.2 Label Rule (A) - SHORT

```python
def apply_label_rule_short(event: dict) -> dict:
    """
    Apply Label Rule (A) for SHORT signals.

    ALL conditions must be TRUE for label = "short"

    Args:
        event: EventState dictionary with required fields

    Returns:
        dict: {
            "label": "short" or "skip",
            "label_confidence": float,
            "label_reason": str,
            "conditions_met": list,
            "conditions_failed": list
        }
    """
    conditions = {
        "ext_choch_up": event.get("ext_choch_up", False) == True,
        "fvg_down": event.get("fvg_down", False) == True,
        "fvg_retest": event.get("fvg_retest", False) == True,
        "ext_dir_down": event.get("ext_dir", 0) == -1,
        "mgann_leg_early": event.get("mgann_leg_index", 99) <= 2,
        "pb_wave_ok": event.get("pb_wave_strength_ok", False) == True,
    }

    conditions_met = [k for k, v in conditions.items() if v]
    conditions_failed = [k for k, v in conditions.items() if not v]

    if all(conditions.values()):
        return {
            "label": "short",
            "label_confidence": 1.0,
            "label_reason": "All 6 SHORT conditions satisfied",
            "conditions_met": conditions_met,
            "conditions_failed": []
        }
    else:
        confidence = len(conditions_met) / len(conditions)
        return {
            "label": "skip",
            "label_confidence": confidence,
            "label_reason": f"Failed: {', '.join(conditions_failed)}",
            "conditions_met": conditions_met,
            "conditions_failed": conditions_failed
        }
```

### 4.3 Main Labeling Function

```python
def apply_label_rule_a(event: dict) -> dict:
    """
    Apply Label Rule (A) to determine signal label.

    Logic:
    1. Check if FVG is bullish or bearish
    2. Apply corresponding rule (LONG or SHORT)
    3. Return label and metadata

    Args:
        event: EventState dictionary

    Returns:
        dict: Labeling result
    """
    fvg_type = event.get("fvg_type", "unknown")

    if fvg_type == "bullish" or event.get("fvg_up", False):
        return apply_label_rule_long(event)
    elif fvg_type == "bearish" or event.get("fvg_down", False):
        return apply_label_rule_short(event)
    else:
        return {
            "label": "skip",
            "label_confidence": 0.0,
            "label_reason": "No valid FVG detected",
            "conditions_met": [],
            "conditions_failed": ["fvg_type"]
        }
```

---

## 5. Flowchart

### 5.1 Main Decision Flow

```
                    ┌──────────────────────┐
                    │   FVG Retest Event   │
                    │      Detected        │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  What type of FVG?   │
                    └──────────┬───────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
      ┌─────▼─────┐     ┌──────▼──────┐    ┌─────▼─────┐
      │  Bullish  │     │  Unknown/   │    │  Bearish  │
      │   FVG     │     │   None      │    │   FVG     │
      └─────┬─────┘     └──────┬──────┘    └─────┬─────┘
            │                  │                  │
            │           ┌──────▼──────┐           │
            │           │    SKIP     │           │
            │           │  (no FVG)   │           │
            │           └─────────────┘           │
            │                                     │
      ┌─────▼──────────────┐          ┌──────────▼─────┐
      │ Apply LONG Rule    │          │ Apply SHORT    │
      │ (6 conditions)     │          │ Rule (6 cond)  │
      └─────┬──────────────┘          └──────────┬─────┘
            │                                    │
    ┌───────▼───────┐                   ┌───────▼───────┐
    │ All TRUE?     │                   │ All TRUE?     │
    └───────┬───────┘                   └───────┬───────┘
            │                                   │
      ┌─────┴─────┐                       ┌─────┴─────┐
      │           │                       │           │
    ┌─▼──┐     ┌──▼─┐                  ┌──▼─┐     ┌──▼──┐
    │YES │     │ NO │                  │YES │     │ NO  │
    └─┬──┘     └──┬─┘                  └──┬─┘     └──┬──┘
      │           │                       │          │
    ┌─▼───┐    ┌──▼──┐                 ┌──▼───┐   ┌──▼──┐
    │LONG │    │SKIP │                 │SHORT │   │SKIP │
    └─────┘    └─────┘                 └──────┘   └─────┘
```

### 5.2 LONG Conditions Detail

```
┌─────────────────────────────────────────────────────────────┐
│                 LONG LABEL CONDITIONS                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐                                            │
│  │ Condition 1 │  ext_choch_down == True                    │
│  │             │  "External CHoCH from DOWN"                │
│  └──────┬──────┘                                            │
│         │ YES                                               │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ Condition 2 │  fvg_up == True                            │
│  │             │  "Bullish FVG exists"                      │
│  └──────┬──────┘                                            │
│         │ YES                                               │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ Condition 3 │  fvg_retest == True                        │
│  │             │  "FVG has been retested"                   │
│  └──────┬──────┘                                            │
│         │ YES                                               │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ Condition 4 │  ext_dir == 1                              │
│  │             │  "External direction is UP"                │
│  └──────┬──────┘                                            │
│         │ YES                                               │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ Condition 5 │  mgann_leg_index <= 2                      │
│  │             │  "Entry in early leg (1 or 2)"             │
│  └──────┬──────┘                                            │
│         │ YES                                               │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ Condition 6 │  pb_wave_strength_ok == True               │
│  │             │  "Pullback wave shows weakness"            │
│  └──────┬──────┘                                            │
│         │ YES                                               │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │   LABEL:    │                                            │
│  │    LONG     │                                            │
│  └─────────────┘                                            │
│                                                              │
│  * ANY condition fails → SKIP                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. ML Training Notes

### 6.1 Dataset Generation

```python
class LabelRuleAGenerator:
    """
    Generate ML training dataset using Label Rule (A).
    """

    def __init__(self, config: dict = None):
        self.config = config or {
            "min_events": 1000,
            "max_events": 1500,
            "train_ratio": 0.7,
            "include_skip": False,  # Set True to include skip labels
        }

    def generate(self, events: List[dict]) -> Tuple[List, List]:
        """
        Generate train/val datasets.

        Args:
            events: List of EventState dictionaries

        Returns:
            (train_data, val_data)
        """
        labeled = []

        for event in events:
            result = apply_label_rule_a(event)

            # Skip events with label="skip" unless configured
            if result["label"] == "skip" and not self.config["include_skip"]:
                continue

            labeled.append({
                **event,
                "label": result["label"],
                "label_confidence": result["label_confidence"],
                "label_reason": result["label_reason"],
            })

        # Enforce dataset size limits
        if len(labeled) > self.config["max_events"]:
            labeled = labeled[:self.config["max_events"]]

        # Split train/val
        split = int(len(labeled) * self.config["train_ratio"])
        return labeled[:split], labeled[split:]
```

### 6.2 Feature Importance

| Feature | Importance | Notes |
|---------|------------|-------|
| `pb_wave_strength_ok` | HIGH | Confirms exhaustion before entry |
| `mgann_leg_index` | HIGH | Early entry = better RR |
| `fvg_quality_score` | MEDIUM | Quality of entry zone |
| `ext_choch_*` | MEDIUM | Structural confirmation |
| `fvg_penetration_ratio` | MEDIUM | Entry precision |
| `market_condition_score` | LOW | Context (not in rule) |

### 6.3 Label Distribution Target

```
Target Distribution (1000-1500 events):
┌───────────┬────────────┬─────────────┐
│   Label   │  Target %  │   Count     │
├───────────┼────────────┼─────────────┤
│   long    │    ~45%    │   450-675   │
│   short   │    ~45%    │   450-675   │
│   skip    │    ~10%    │   100-150   │
└───────────┴────────────┴─────────────┘

Note: Skip events may be excluded from training
if include_skip=False in config.
```

### 6.4 Validation Metrics

```python
def validate_labels(predictions: List[str], actuals: List[str],
                   outcomes: List[dict]) -> dict:
    """
    Validate label accuracy against actual outcomes.

    Args:
        predictions: Model predicted labels
        actuals: Rule-based labels
        outcomes: Trade outcomes (hit, outcome_rr, etc.)

    Returns:
        Validation metrics
    """
    metrics = {
        "label_accuracy": accuracy_score(actuals, predictions),
        "long_win_rate": calculate_win_rate(outcomes, "long"),
        "short_win_rate": calculate_win_rate(outcomes, "short"),
        "profit_factor": calculate_profit_factor(outcomes),
        "sharpe_ratio": calculate_sharpe(outcomes),
    }

    return metrics
```

---

## 7. Integration

### 7.1 Dependencies

```
Module #02 (FVG Quality)      → fvg_up, fvg_down, fvg_type
Module #03 (Structure Context) → ext_choch_down, ext_choch_up, ext_dir
Module #12 (FVG Retest)       → fvg_retest
Module #13 (Wave Delta)       → pb_wave_strength_ok
Module #14 (MGann Swing)      → mgann_leg_index
```

### 7.2 Execution Order

```python
# Label Rule (A) runs AFTER all Layer 2 modules
# It is part of Layer 3 (ML Pipeline)

def process_for_ml(events: List[EventState]) -> List[dict]:
    """
    Process events for ML training.

    Pipeline:
    1. Layer 2 modules process raw data → EventState
    2. Label Rule (A) applies labels
    3. Generate train/val datasets
    """
    labeled_events = []

    for event in events:
        # Apply Label Rule (A)
        label_result = apply_label_rule_a(event.__dict__)

        labeled_events.append({
            **event.__dict__,
            **label_result
        })

    return labeled_events
```

### 7.3 API Example

```python
from processor.ml.label_rules import apply_label_rule_a

# Example usage
event = {
    "ext_choch_down": True,
    "fvg_up": True,
    "fvg_retest": True,
    "ext_dir": 1,
    "mgann_leg_index": 1,
    "pb_wave_strength_ok": True,
}

result = apply_label_rule_a(event)
# result = {
#     "label": "long",
#     "label_confidence": 1.0,
#     "label_reason": "All 6 LONG conditions satisfied",
#     "conditions_met": ["ext_choch_down", "fvg_up", "fvg_retest",
#                        "ext_dir_up", "mgann_leg_early", "pb_wave_ok"],
#     "conditions_failed": []
# }
```

---

## 8. Testing

### 8.1 Unit Tests

```python
# processor/tests/test_label_rules.py

def test_label_rule_long_all_conditions():
    """Test LONG label when all conditions met."""
    event = {
        "ext_choch_down": True,
        "fvg_up": True,
        "fvg_retest": True,
        "ext_dir": 1,
        "mgann_leg_index": 1,
        "pb_wave_strength_ok": True,
    }

    result = apply_label_rule_a(event)
    assert result["label"] == "long"
    assert result["label_confidence"] == 1.0
    assert len(result["conditions_failed"]) == 0


def test_label_rule_long_missing_choch():
    """Test SKIP when ext_choch_down is False."""
    event = {
        "ext_choch_down": False,  # Missing!
        "fvg_up": True,
        "fvg_retest": True,
        "ext_dir": 1,
        "mgann_leg_index": 1,
        "pb_wave_strength_ok": True,
    }

    result = apply_label_rule_a(event)
    assert result["label"] == "skip"
    assert "ext_choch_down" in result["conditions_failed"]


def test_label_rule_short_all_conditions():
    """Test SHORT label when all conditions met."""
    event = {
        "ext_choch_up": True,
        "fvg_down": True,
        "fvg_retest": True,
        "ext_dir": -1,
        "mgann_leg_index": 2,
        "pb_wave_strength_ok": True,
    }

    result = apply_label_rule_a(event)
    assert result["label"] == "short"
    assert result["label_confidence"] == 1.0


def test_label_rule_late_leg():
    """Test SKIP when mgann_leg_index > 2."""
    event = {
        "ext_choch_down": True,
        "fvg_up": True,
        "fvg_retest": True,
        "ext_dir": 1,
        "mgann_leg_index": 3,  # Too late!
        "pb_wave_strength_ok": True,
    }

    result = apply_label_rule_a(event)
    assert result["label"] == "skip"
    assert "mgann_leg_early" in result["conditions_failed"]
```

### 8.2 Backtest Validation

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Label accuracy | >= 70% | TBD | Pending |
| LONG win rate | >= 40% | TBD | Pending |
| SHORT win rate | >= 40% | TBD | Pending |
| Profit Factor | >= 1.5 | TBD | Pending |

---

## 9. Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | 2025-11-23 | Initial Label Rule (A) specification |

---

**Status:** Production Ready
**Dependencies:** Module #02, #03, #12, #13, #14
**Next Steps:** Implement in processor/ml/label_rules.py
