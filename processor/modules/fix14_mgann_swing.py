# ============================================================================
# MODULE: FIX14_MGANN_SWING v1.2.0
# DESCRIPTION:
#   MGann Swing detector using authentic W.D. Gann 2-bar swing chart rules.
#   - Detects internal zigzag using 2-bar sequences
#   - Tracks wave delta/volume for strength calculation
#   - Leg management with CHoCH/BOS detection
#   - Pullback strength evaluation (Hybrid Rule v4)
#
# VERSION: 1.2.0 (Leg Management)
# TAG: FIX14-MGANN-v1.2.0
# CHANGELOG:
#   v1.2.0 (2025-11-24):
#     + Added mgann_leg_index (tracks leg number, resets on trend change)
#     + Added mgann_leg_first_fvg (detects first FVG per leg)
#     + Added pb_wave_strength_ok (Hybrid Rule v4 with 6 conditions)
#     + Implemented trend reset detection (CHoCH/BOS)
#     + Leg classification: impulse vs pullback
#     + Structure preservation checks
#   v1.1.0 (2025-11-23):
#     - Replaced threshold-based detection with Gann 2-bar rule
#     - Added prev bar tracking for 2-bar sequences
#     - Exception: break above/below swing high/low
#   v1.0.0: Initial threshold-based implementation
# ============================================================================

from processor.core.module_base import BaseModule


class Fix14MgannSwing(BaseModule):
    """
    MGann Swing Detector using W.D. Gann 2-bar swing chart construction rules.
    
    Gann Rules:
    - UPSWING: 2 consecutive bars with higher highs OR bar high > last swing high
    - DOWNSWING: 2 consecutive bars with lower lows OR bar low < last swing low
    """
    
    def __init__(self, threshold_ticks=6):
        """
        Args:
            threshold_ticks: Kept for compatibility (not used in v1.1.0)
        """
        super().__init__()
        self.threshold_ticks = threshold_ticks
        
        # Swing state
        self.last_swing_high = None
        self.last_swing_low = None
        self.last_swing_dir = 0  # 1=up, -1=down, 0=init
        
        # Previous bar tracking for 2-bar sequences
        self.prev_bar_high = None
        self.prev_bar_low = None
        self.prev_prev_high = None
        self.prev_prev_low = None
        
        # Active wave accumulation
        self.active_wave_delta = 0.0
        self.active_wave_volume = 0.0
        
        # === NEW: Leg management (v1.2.0) ===
        self.mgann_leg_index = 0           # Current leg number (1, 2, 3...)
        self.trend_dir = 0                 # External trend direction (1=up, -1=down)
        
        # Impulse leg tracking
        self.last_impulse_delta = 0.0
        self.last_impulse_volume = 0.0
        self.last_impulse_strength = 0
        
        # Pullback leg tracking  
        self.pullback_delta = 0.0
        self.pullback_volume = 0.0
        self.pullback_strength = 0
        self.pullback_low = None           # For structure check (uptrend)
        self.pullback_high = None          # For structure check (downtrend)
        self.pb_wave_strength_flag = False # Result of Hybrid Rule v4
        
        # Structure anchors (leg1 levels)
        self.leg1_low = None               # Leg 1 low (uptrend)
        self.leg1_high = None              # Leg 1 high (downtrend)
        
        # FVG tracking per leg
        self.current_leg_fvg_seen = False  # Track if FVG seen in current leg
        self.active_leg_dir = 0            # Current active leg direction

    
    def _check_gann_upswing(self, current_high, prev_high, prev_prev_high):
        """
        Gann Rule for UPSWING:
        1. Exception: current high > last swing high → start upswing
        2. Standard: 2 consecutive bars with higher highs → start upswing
        """
        # Exception rule
        if self.last_swing_high is not None and current_high > self.last_swing_high:
            return True
        
        # 2-bar rule
        if prev_high is not None and prev_prev_high is not None:
            if current_high > prev_high and prev_high > prev_prev_high:
                return True
        
        return False
    
    def _check_gann_downswing(self, current_low, prev_low, prev_prev_low):
        """
        Gann Rule for DOWNSWING:
        1. Exception: current low < last swing low → start downswing
        2. Standard: 2 consecutive bars with lower lows → start downswing
        """
        # Exception rule
        if self.last_swing_low is not None and current_low < self.last_swing_low:
            return True
        
        # 2-bar rule
        if prev_low is not None and prev_prev_low is not None:
            if current_low < prev_low and prev_low < prev_prev_low:
                return True
        
        return False
    
    # === NEW METHODS (v1.2.0) ===
    
    def _reset_trend(self, bar_state, bar_low, bar_high):
        """
        Detect trend change from CHoCH/BOS and reset leg tracking.
        
        Args:
            bar_state: Current bar data
            bar_low: Current bar low
            bar_high: Current bar high
        """
        # Read external SMC signals
        ext_dir = bar_state.get("ext_dir", 0)
        choch_up = bar_state.get("ext_choch_up", False)
        choch_down = bar_state.get("ext_choch_down", False)
        bos_up = bar_state.get("ext_bos_up", False)
        bos_down = bar_state.get("ext_bos_down", False)
        
        # Infer trend direction
        inferred_dir = self.trend_dir
        if ext_dir in (1, -1):
            inferred_dir = ext_dir
        elif choch_down or bos_down:
            inferred_dir = 1  # Downward CHoCH/BOS indicates uptrend
        elif choch_up or bos_up:
            inferred_dir = -1  # Upward CHoCH/BOS indicates downtrend
        
        # Reset on trend change
        if inferred_dir in (1, -1) and inferred_dir != self.trend_dir:
            self.trend_dir = inferred_dir
            self.mgann_leg_index = 1
            
            # Reset accumulators
            self.last_impulse_delta = 0.0
            self.last_impulse_volume = 0.0
            self.last_impulse_strength = 0
            self.pullback_delta = 0.0
            self.pullback_volume = 0.0
            self.pullback_strength = 0
            self.pullback_low = None
            self.pullback_high = None
            self.pb_wave_strength_flag = False
            
            # Set leg1 anchor levels
            if self.trend_dir == 1:
                self.leg1_low = bar_low
            else:
                self.leg1_high = bar_high
            
            # Reset active leg
            self.active_leg_dir = self.trend_dir
            self.current_leg_fvg_seen = False
    
    def _evaluate_pullback_strength(self, bar_state, history):
        """
        Hybrid Rule v4 for pullback strength evaluation.
        
        Returns:
            bool: True if pullback is healthy (weak enough)
        
        Conditions:
        1. pullback_strength < 40
        2. pullback_delta < impulse_delta * 0.3
        3. pullback_volume < impulse_volume * 0.6
        4. delta_pb >= -35 (uptrend) or <= 35 (downtrend)
        5. volume_pb <= avg_volume * 1.0
        6. pb_low > leg1_low (uptrend) or pb_high < leg1_high (downtrend)
        """
        if self.trend_dir == 0:
            return False
        
        impulse_vol = self.last_impulse_volume
        impulse_delta = self.last_impulse_delta
        pb_vol = self.pullback_volume
        pb_delta = self.pullback_delta
        
        if impulse_vol <= 0 or pb_vol <= 0:
            return False
        
        # Get average volume
        avg_vol = bar_state.get("avg_volume")
        if avg_vol is None:
            # Calculate from history if available
            if history and len(history) > 0:
                recent_vols = [float(b.get("volume", 0) or 0) for b in history[-20:]]
                avg_vol = sum(recent_vols) / len(recent_vols) if recent_vols else pb_vol
            else:
                avg_vol = pb_vol
        
        if avg_vol <= 0:
            avg_vol = pb_vol
        
        # 6 Conditions of Hybrid Rule v4
        pb_strength = self.pullback_strength
        
        # 1. Wave strength check
        strength_ok = pb_strength < 40
        
        # 2. Delta ratio check
        delta_ratio_ok = abs(pb_delta) <= abs(impulse_delta) * 0.3
        
        # 3. Volume ratio check
        volume_ratio_ok = pb_vol <= impulse_vol * 0.6
        
        # 4. Absolute delta gate
        if self.trend_dir == 1:
            delta_gate = pb_delta >= -35
        else:
            delta_gate = pb_delta <= 35
        
        # 5. Volume vs average check
        volume_gate = pb_vol <= avg_vol * 1.0
        
        # 6. Structure preservation
        structure_ok = True
        if self.trend_dir == 1 and self.leg1_low is not None and self.pullback_low is not None:
            structure_ok = self.pullback_low > self.leg1_low
        elif self.trend_dir == -1 and self.leg1_high is not None and self.pullback_high is not None:
            structure_ok = self.pullback_high < self.leg1_high
        
        # All conditions must pass
        return (
            strength_ok
            and delta_ratio_ok
            and volume_ratio_ok
            and delta_gate
            and volume_gate
            and structure_ok
        )
    
    def _check_leg_first_fvg(self, bar_state):
        """
        Detect the first FVG within the current leg.
        
        Returns:
            bool: True only for FIRST FVG in current leg
        """
        # Check if FVG detected
        fvg_detected = bool(
            bar_state.get("fvg_detected")
            or bar_state.get("fvg_up")
            or bar_state.get("fvg_down")
        )
        
        if not fvg_detected:
            return False
        
        # Determine FVG direction
        fvg_dir = 0
        if bar_state.get("fvg_up") or bar_state.get("fvg_type") == "bullish":
            fvg_dir = 1
        elif bar_state.get("fvg_down") or bar_state.get("fvg_type") == "bearish":
            fvg_dir = -1
        
        # Check if this is first FVG in current leg
        if fvg_dir != 0 and fvg_dir == self.active_leg_dir and not self.current_leg_fvg_seen:
            self.current_leg_fvg_seen = True
            return True
        
        return False

    
    def process_bar(self, bar_state, history=None):
        """
        Process bar and update MGann swing fields.
        
        Updates bar_state with:
        - mgann_internal_swing_high: Current swing high level
        - mgann_internal_swing_low: Current swing low level
        - mgann_internal_leg_dir: Direction (1=up, -1=down)
        - mgann_wave_strength: Delta/volume ratio (0-100)
        """
        current_high = bar_state.get("high", 0)
        current_low = bar_state.get("low", 0)
        current_delta = bar_state.get("delta", 0)
        current_volume = bar_state.get("volume", 0)
        
        # Initialize on first bar
        if self.last_swing_high is None:
            self.last_swing_high = current_high
            self.last_swing_low = current_low
            self.prev_bar_high = current_high
            self.prev_bar_low = current_low
            self.active_wave_delta = current_delta
            self.active_wave_volume = current_volume
            
            bar_state["mgann_internal_swing_high"] = self.last_swing_high
            bar_state["mgann_internal_swing_low"] = self.last_swing_low
            bar_state["mgann_internal_leg_dir"] = 0
            bar_state["mgann_internal_dir"] = 0
            bar_state["mgann_wave_strength"] = 0
            bar_state["mgann_behavior"] = {"UT": False, "SP": False, "PB": False, "EX3": False}
            return bar_state
        
        prev_dir = self.last_swing_dir
        
        # === NEW: Check for trend reset (CHoCH/BOS) ===
        self._reset_trend(bar_state, current_low, current_high)
        
        # Check Gann upswing
        if self._check_gann_upswing(current_high, self.prev_bar_high, self.prev_prev_high):
            self.last_swing_high = current_high
            self.last_swing_dir = 1
            
            # === NEW: Leg transition handling ===
            if prev_dir != 1:
                # Direction changed to UP
                self.active_wave_delta = 0.0
                self.active_wave_volume = 0.0
                
                # Finalize previous leg (if it was a pullback)
                if prev_dir == -self.trend_dir and self.trend_dir != 0:
                    # Previous leg was pullback, evaluate it
                    self.pullback_delta = self.active_wave_delta
                    self.pullback_volume = self.active_wave_volume
                    self.pullback_strength = self._compute_wave_strength()
                    self.pullback_low = current_low
                    self.pullback_high = current_high
                    self.pb_wave_strength_flag = self._evaluate_pullback_strength(bar_state, history)
                
                # Start new leg
                if self.last_swing_dir == self.trend_dir:
                    # New impulse leg
                    self.mgann_leg_index += 1
                    self.current_leg_fvg_seen = False
                elif self.last_swing_dir == -self.trend_dir:
                    # Pullback leg starting
                    self.current_leg_fvg_seen = False
                
                self.active_leg_dir = self.last_swing_dir
        
        # Check Gann downswing
        elif self._check_gann_downswing(current_low, self.prev_bar_low, self.prev_prev_low):
            self.last_swing_low = current_low
            self.last_swing_dir = -1
            
            # === NEW: Leg transition handling ===
            if prev_dir != -1:
                # Direction changed to DOWN
                self.active_wave_delta = 0.0
                self.active_wave_volume = 0.0
                
                # Finalize previous leg (if it was a pullback)
                if prev_dir == -self.trend_dir and self.trend_dir != 0:
                    # Previous leg was pullback, evaluate it
                    self.pullback_delta = self.active_wave_delta
                    self.pullback_volume = self.active_wave_volume
                    self.pullback_strength = self._compute_wave_strength()
                    self.pullback_low = current_low
                    self.pullback_high = current_high
                    self.pb_wave_strength_flag = self._evaluate_pullback_strength(bar_state, history)
                
                # Start new leg
                if self.last_swing_dir == self.trend_dir:
                    # New impulse leg
                    self.mgann_leg_index += 1
                    self.current_leg_fvg_seen = False
                elif self.last_swing_dir == -self.trend_dir:
                    # Pullback leg starting
                    self.current_leg_fvg_seen = False
                
                self.active_leg_dir = self.last_swing_dir
        
        # Update trailing swing levels
        else:
            if self.last_swing_dir == 1:
                # In uptrend, update trailing high
                if current_high > self.last_swing_high:
                    self.last_swing_high = current_high
            elif self.last_swing_dir == -1:
                # In downtrend, update trailing low
                if current_low < self.last_swing_low:
                    self.last_swing_low = current_low
        
        # Update previous bar tracking for next iteration
        self.prev_prev_high = self.prev_bar_high
        self.prev_prev_low = self.prev_bar_low
        self.prev_bar_high = current_high
        self.prev_bar_low = current_low
        
        # Accumulate wave delta/volume
        self.active_wave_delta += current_delta
        self.active_wave_volume += current_volume
        
        # Calculate wave strength (simple delta/volume ratio)
        wave_strength = self._compute_wave_strength()
        
        # === NEW: Check for first FVG in current leg ===
        mgann_leg_first_fvg = self._check_leg_first_fvg(bar_state)
        
        # Update bar_state with original fields
        bar_state["mgann_internal_swing_high"] = self.last_swing_high
        bar_state["mgann_internal_swing_low"] = self.last_swing_low
        bar_state["mgann_internal_leg_dir"] = self.last_swing_dir
        bar_state["mgann_internal_dir"] = self.last_swing_dir
        bar_state["mgann_wave_strength"] = wave_strength
        
        # === NEW: Export 3 new fields (v1.2.0) ===
        bar_state["mgann_leg_index"] = int(self.mgann_leg_index) if self.mgann_leg_index else 0
        bar_state["mgann_leg_first_fvg"] = mgann_leg_first_fvg
        bar_state["pb_wave_strength_ok"] = bool(self.pb_wave_strength_flag)

        
        # No patterns (all False)
        bar_state["mgann_behavior"] = {
            "UT": False,
            "SP": False,
            "PB": False,
            "EX3": False,
        }
        
        return bar_state
    
    def _compute_wave_strength(self):
        """
        Calculate wave strength from delta/volume ratio.
        Returns: int 0-100
        """
        if self.active_wave_volume <= 0:
            return 0
        
        # Delta efficiency: |delta| / (volume + epsilon)
        delta_ratio = abs(self.active_wave_delta) / (self.active_wave_volume + 1e-9)
        
        # Scale to 0-100 (cap at 1.0 ratio)
        strength = min(1.0, delta_ratio) * 100
        
        return int(strength)
