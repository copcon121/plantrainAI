# Module Fix14: MGann Swing Engine

**Version:** 1.2.0  
**Status:** Active  
**Purpose:** Gann-style swing detection with leg tracking and wave strength analysis

---

## Overview

Module 14 implements W.D. Gann 2-bar swing chart construction rules to detect internal market structure. It tracks leg progression, measures wave strength via delta/volume ratios, and validates pullback quality for high-probability continuation entries.

**Key Innovation:** Combines classic Gann swing detection with modern volume delta analysis to filter weak pullbacks and identify high-quality entry zones.

---

## Input Fields Required

Module 14 reads structure signals from **nested `bar` object** in exported data:

### Structure Signals (from C# Indicator)
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `bar.ext_dir` | int | `ExtStructureDir` | External structure direction: 1=up, -1=down, 0=flat |
| `bar.ext_choch_up` | bool | `ExtChochUpPulse` | External CHoCH up pulse (one-time signal) |
| `bar.ext_choch_down` | bool | `ExtChochDownPulse` | External CHoCH down pulse (one-time signal) |
| `bar.ext_bos_up` | bool | `ExtBosUpPulse` | External BOS up pulse |
| `bar.ext_bos_down` | bool | `ExtBosDownPulse` | External BOS down pulse |

### Volume/Delta Data
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `bar.volume_stats.delta_close` | float | Volumdelta indicator | Bar delta (buy - sell volume) |
| `bar.volume_stats.total_volume` | float | Volumdelta indicator | Total bar volume |

### OHLC Data (Root Level)
| Field | Type | Description |
|-------|------|-------------|
| `high` | float | Bar high price |
| `low` | float | Bar low price |
| `volume` | float | Bar volume (fallback if volume_stats missing) |
| `delta` | float | Bar delta (fallback if volume_stats missing) |

---

## Output Fields Generated

Module 14 writes fields to **root level** of bar_state:

### Swing Detection Fields  
| Field | Type | Description |
|-------|------|-------------|
| `mgann_internal_swing_high` | float | Current swing high level |
| `mgann_internal_swing_low` | float | Current swing low level |
| `mgann_internal_leg_dir` | int | Current leg direction (1=up, -1=down, 0=init) |
| `mgann_internal_dir` | int | Alias for leg_dir (backward compatibility) |
| `mgann_wave_strength` | int | Current wave strength 0-100 (delta/volume ratio) |

### Leg Tracking Fields (v1.2.0)
| Field | Type | Description |
|-------|------|-------------|
| `mgann_leg_index` | int | Current leg number (1, 2, 3...) - resets on trend change |
| `mgann_leg_first_fvg` | bool | True only for FIRST FVG in current leg |
| `pb_wave_strength_ok` | bool | **Pullback wave strength validated** (Hybrid Rule v4) |
| `mgann_leg_low` | float | Lowest price in current leg (for SL calculation) |
| `mgann_leg_high` | float | Highest price in current leg (for SL calculation) |

### Legacy Fields (Deprecated)
| Field | Type | Description |
|-------|------|-------------|
| `mgann_behavior` | dict | Pattern flags (UT/SP/PB/EX3) - always False in v1.2.0 |

---

## Gann Swing Rules

### Upswing Detection
1. **Exception Rule:** Current high > last swing high → immediate upswing
2. **Standard Rule:** 2 consecutive bars with higher highs → upswing

### Downswing Detection
1. **Exception Rule:** Current low < last swing low → immediate downswing
2. **Standard Rule:** 2 consecutive bars with lower lows → downswing

---

## Leg Progression Logic

### Trend Reset (CHoCH/BOS Detection)
When `ext_choch_up/down` or `ext_bos_up/down` fires:
1. Infer new trend direction from signal type
2. Reset `mgann_leg_index = 1`
3. Clear impulse/pullback accumulators
4. Set leg1 anchor levels (for structure preservation check)

### Leg Transition
- **Impulse → Pullback:** Direction reverses AGAINST trend → start tracking pullback metrics
- **Pullback → Impulse:** Direction reverses WITH trend → increment leg index, evaluate pullback strength

---

## Wave Strength Calculation

Module 14 tracks wave strength for each leg using delta/volume ratio:

```python
wave_strength = (|delta| / volume) * 100
# Capped at 100
```

### Wave Types by Leg Number

**IMPULSE WAVE STRENGTH (Leg 1, 3, 5... - odd legs):**
- First leg after CHoCH/BOS
- Price moves WITH trend direction
- **Should be STRONG** (high delta/volume ratio)
- Indicates institutional buying/selling pressure
- Creates FVG zone
- Target: wave_strength > 60 for valid impulse

**PB WAVE STRENGTH (Leg 2, 4, 6... - even legs):**
- Pullback/retracement leg
- Price moves AGAINST trend direction (tests FVG)
- **Should be WEAK** (low delta/volume ratio)
- Indicates retail retracement, not institutional reversal
- Validated by `pb_wave_strength_ok` flag
- Target: wave_strength < 40 for valid pullback

**Interpretation:**
- 0-30: Weak wave (low conviction)
- 30-60: Moderate wave
- 60-100: Strong wave (high buying/selling pressure)

---

## Pullback Wave Strength Validation (Hybrid Rule v4)

`pb_wave_strength_ok = True` ON LEG 2 when **ALL 6 conditions** pass:

### Condition 1: Wave Strength
```python
pullback_strength < 40  # Weak pullback (not aggressive counter-move)
```

### Condition 2: Delta Ratio
```python
|pullback_delta| <= |impulse_delta| * 0.3  # PB delta < 30% of impulse
```

### Condition 3: Volume Ratio
```python
pullback_volume <= impulse_volume * 0.6  # PB volume < 60% of impulse
```

### Condition 4: Absolute Delta Gate
```python
# Uptrend
pullback_delta >= -35  # Not too much selling

# Downtrend
pullback_delta <= 35  # Not too much buying
```

### Condition 5: Volume vs Average
```python
pullback_volume <= avg_volume * 1.0  # Not excessive volume
```

### Condition 6: Structure Preservation
```python
# Uptrend
pullback_low > leg1_low  # Didn't break structure

# Downtrend
pullback_high < leg1_high  # Didn't break structure
```

---

## CHoCH/BOS Export Structure (C# Indicator)

### Exporter Field Mapping
C# Indicator exports structure signals in **BOTH locations**:

#### Root Level (for backward compatibility)
```json
{
  "ext_choch_up": false,
  "ext_choch_down": false,
  "fvg_detected": false,
  ...
}
```

#### Nested `bar` Object (primary location)
```json
{
  "bar": {
    "ext_dir": 0,
    "ext_choch_up": false,
    "ext_choch_down": false,
    "ext_bos_up": false,
    "ext_bos_down": false,
    "fvg_detected": false,
    "fvg_type": "bullish",
    "volume_stats": {
      "delta_close": 1234.5,
      "total_volume": 5000
    }
  }
}
```

**Module 14 Requirement:** Modules must read from `bar` object as it contains the most complete data with volume stats nested properly.

---

## Usage Example

```python
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

mgann = Fix14MgannSwing()

# Flatten nested bar fields (required preprocessing)
bar_data = bar_state.get("bar", {})
bar_state['ext_dir'] = bar_data.get("ext_dir", 0)
bar_state['ext_choch_up'] = bar_data.get("ext_choch_up", False)
bar_state['ext_choch_down'] = bar_data.get("ext_choch_down", False)
vol_stats = bar_data.get("volume_stats", {})
bar_state['delta'] = vol_stats.get("delta_close", 0)
bar_state['volume'] = vol_stats.get("total_volume", 0)

# Process bar
bar_state = mgann.process_bar(bar_state, history=[...])

# Read outputs
leg_index = bar_state['mgann_leg_index']  # 1, 2, 3...
pb_ok = bar_state['pb_wave_strength_ok']  # True/False
wave_strength = bar_state['mgann_wave_strength']  # 0-100
```

---

## Integration with Strategy

Strategy modules use Module 14 outputs for entry filtering:

```python
# Example: Strategy V1 conditions
leg_ok = 0 < bar_state.get('mgann_leg_index', 0) <= 2  # Early legs only
pb_ok = bar_state.get('pb_wave_strength_ok', False)    # Validated pullback
fvg_ok = bar_state.get('fvg_detected', False)          # FVG present

if leg_ok and pb_ok and fvg_ok:
    # High-quality entry setup
    generate_signal()
```

---

## Module Dependencies

**Depends on:**
- Layer 1 Exporter (C# indicator) for structure signals
- Volumdelta indicator for volume/delta data

**Used by:**
- fix16_strategy_v1.py (primary consumer)
- fix12_fvg_retest.py (leg context for FVG quality)

---

## Version History

### v1.2.0 (Current)
- Added leg tracking (`mgann_leg_index`)
- Added pullback strength validation (`pb_wave_strength_ok`)
- Added first FVG detection per leg (`mgann_leg_first_fvg`)
- Added leg extremes for SL calculation
- Removed pattern detection (UT/SP/PB/EX3) - deprecated

### v1.1.0
- Implemented Hybrid Rule v4 for pullback strength
- Added volume delta integration
- Improved swing detection accuracy

### v1.0.0
- Initial Gann 2-bar swing detection
- Basic wave strength calculation
