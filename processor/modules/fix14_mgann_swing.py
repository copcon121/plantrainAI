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
        self.impulse_speed = 0.0
        self.impulse_bar_count = 0
        self.impulse_wave_strength_ok = False  # NEW: Impulse validation flag
        
        # Pullback leg tracking  
        self.pullback_delta = 0.0
        self.pullback_volume = 0.0
        self.pullback_strength = 0
        self.pullback_low = None           # For structure check (uptrend)
        self.pullback_high = None          # For structure check (downtrend)
        self.pullback_speed = 0.0
        self.pullback_bar_count = 0
        self.pb_wave_strength_flag = False # Result of refined validation
        
        # Structure anchors (leg1 levels)
        self.leg1_low = None               # Leg 1 low (uptrend)
        self.leg1_high = None              # Leg 1 high (downtrend)
        
        # FVG tracking per leg
        self.current_leg_fvg_seen = False  # Track if FVG seen in current leg
        self.active_leg_dir = 0            # Current active leg direction
        # Track prior trend extremes to validate new leg1 breaks
        self.prev_trend_high = None
        self.prev_trend_low = None
        self.leg1_cut_prev_extreme = False
        
        # === NEW: Rolling averages and speed tracking ===
        self.delta_history = []            # Last 20 bars
        self.volume_history = []           # Last 20 bars
        self.speed_history = []            # Last 5 waves
        self.avg_delta = 0.0
        self.avg_volume = 0.0
        self.avg_speed = 0.0

    def _hard_reset(self, new_dir, bar_low, bar_high, prev_swing_low=None, prev_swing_high=None):
        """
        Force reset leg counting when structure is taken out (BOS/CHOCH or pivot break).
        Sets trend_dir to new_dir (1=up, -1=down), leg index = 1, and anchors leg1.
        """
        if new_dir not in (1, -1):
            return

        # Store previous trend extremes to evaluate new leg1 break
        self.prev_trend_low = prev_swing_low
        self.prev_trend_high = prev_swing_high
        self.leg1_cut_prev_extreme = False

        self.trend_dir = new_dir
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
        self.impulse_wave_strength_ok = False
        self.current_leg_fvg_seen = False
        self.impulse_bar_count = 0
        self.pullback_bar_count = 0
        self.speed_history = []
        self.avg_speed = 0.0

        # Anchor leg1 extremes
        if self.trend_dir == 1:
            self.leg1_low = bar_low
            self.leg1_high = None
        else:
            self.leg1_high = bar_high
            self.leg1_low = None

        # Active leg dir starts with trend direction
        self.active_leg_dir = self.trend_dir
        self.current_leg_fvg_seen = False

    
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
        if inferred_dir in (1, -1):
            # New requirement: always reset legs on BOS/CHOCH, even if direction unchanged.
            if inferred_dir != self.trend_dir or choch_up or choch_down or bos_up or bos_down:
                self._hard_reset(inferred_dir, bar_low, bar_high, self.last_swing_low, self.last_swing_high)
    
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
    
    def _calculate_speed(self, price_start, price_end, bar_count):
        """
        Calculate wave speed (price change per bar).
        
        Args:
            price_start: Starting price
            price_end: Ending price
            bar_count: Number of bars in wave
            
        Returns:
            float: Speed (price change per bar)
        """
        if bar_count <= 0:
            return 0.0
        return abs(price_end - price_start) / bar_count
    
    def _update_averages(self, bar_state):
        """
        Update rolling averages for delta, volume.
        Uses 20-bar window.
        """
        delta = abs(bar_state.get('delta', 0))
        volume = bar_state.get('volume', 0)
        
        self.delta_history.append(delta)
        self.volume_history.append(volume)
        
        # Keep last 20 bars
        if len(self.delta_history) > 20:
            self.delta_history = self.delta_history[-20:]
        if len(self.volume_history) > 20:
            self.volume_history = self.volume_history[-20:]
        
        # Calculate averages
        self.avg_delta = sum(self.delta_history) / len(self.delta_history) if self.delta_history else 0
        self.avg_volume = sum(self.volume_history) / len(self.volume_history) if self.volume_history else 0
    
    def _evaluate_impulse_strength(self, bar_state):
        """
        Validate IMPULSE wave strength (Leg 1, 3, 5...).
        
        Criteria:
        1. delta > avg_delta * 1.5
        2. volume > avg_volume * 1.3
        3. speed > avg_speed * 1.2
        4. has_fvg == True
        
        Returns:
            bool: True if impulse is strong enough
        """
        if self.avg_delta <= 0 or self.avg_volume <= 0:
            return False
        
        # 1. Delta check
        delta_ok = abs(self.last_impulse_delta) > self.avg_delta * 1.5
        
        # 2. Volume check
        volume_ok = self.last_impulse_volume > self.avg_volume * 1.3
        
        # 3. Speed check
        if self.avg_speed > 0:
            speed_ok = self.impulse_speed > self.avg_speed * 1.2
        else:
            speed_ok = True  # Skip if no baseline yet
        
        # 4. FVG check - check if FVG was seen during this leg
        has_fvg = self.current_leg_fvg_seen
        
        return delta_ok and volume_ok and speed_ok and has_fvg
    
    def _evaluate_pullback_strength_refined(self, bar_state):
        """
        Refined pullback strength validation (Leg 2, 4, 6...).
        
        Criteria:
        1. abs(delta) < avg_delta * 0.7
        2. volume < avg_volume * 0.7
        3. speed < avg_speed * 0.7
        4. no_momentum_reverse == True
        
        Returns:
            bool: True if pullback is weak (good for entry)
        """
        if self.trend_dir == 0:
            return False
        
        if self.avg_delta <= 0 or self.avg_volume <= 0:
            return False
        
        # 1. Delta check
        delta_ok = abs(self.pullback_delta) < self.avg_delta * 0.7
        
        # 2. Volume check
        volume_ok = self.pullback_volume < self.avg_volume * 0.7
        
        # 3. Speed check
        if self.avg_speed > 0:
            speed_ok = self.pullback_speed < self.avg_speed * 0.7
        else:
            speed_ok = True
        
        # 4. No momentum reverse (structure + delta gate)
        if self.trend_dir == 1:  # Uptrend
            no_momentum = (
                self.pullback_delta >= -35 and
                (self.pullback_low is None or self.leg1_low is None or self.pullback_low > self.leg1_low)
            )
        else:  # Downtrend
            no_momentum = (
                self.pullback_delta <= 35 and
                (self.pullback_high is None or self.leg1_high is None or self.pullback_high < self.leg1_high)
            )
        
        return delta_ok and volume_ok and speed_ok and no_momentum
    
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
                # SAVE metrics BEFORE resetting!
                
                # Finalize previous leg
                if prev_dir == self.trend_dir and self.trend_dir != 0:
                    # Previous leg was IMPULSE - save and validate
                    self.last_impulse_delta = self.active_wave_delta
                    self.last_impulse_volume = self.active_wave_volume
                    self.last_impulse_strength = self._compute_wave_strength()
                    
                    # Calculate impulse speed
                    if self.trend_dir == 1:
                        impulse_start = self.leg1_low if self.leg1_low is not None else current_low
                        impulse_end = current_high
                    else:
                        impulse_start = self.leg1_high if self.leg1_high is not None else current_high
                        impulse_end = current_low
                    
                    self.impulse_speed = self._calculate_speed(
                        impulse_start, impulse_end, max(1, self.impulse_bar_count)
                    )
                    
                    # Validate impulse strength
                    self.impulse_wave_strength_ok = self._evaluate_impulse_strength(bar_state)
                    
                    # Update speed history
                    self.speed_history.append(self.impulse_speed)
                    if len(self.speed_history) > 5:
                        self.speed_history = self.speed_history[-5:]
                    self.avg_speed = sum(self.speed_history) / len(self.speed_history) if self.speed_history else 0
                    
                elif prev_dir == -self.trend_dir and self.trend_dir != 0:
                    # Previous leg was PULLBACK - save and evaluate
                    self.pullback_delta = self.active_wave_delta
                    self.pullback_volume = self.active_wave_volume
                    self.pullback_strength = self._compute_wave_strength()
                    self.pullback_low = current_low
                    self.pullback_high = current_high
                    
                    # Calculate pullback speed
                    if self.trend_dir == 1:
                        pb_start = self.pullback_high if self.pullback_high is not None else current_high
                        pb_end = current_low
                    else:
                        pb_start = self.pullback_low if self.pullback_low is not None else current_low
                        pb_end = current_high
                    
                    self.pullback_speed = self._calculate_speed(
                        pb_start, pb_end, max(1, self.pullback_bar_count)
                    )
                    
                    # Validate pullback strength (REFINED logic)
                    self.pb_wave_strength_flag = self._evaluate_pullback_strength_refined(bar_state)
                    
                    # Update speed history
                    self.speed_history.append(self.pullback_speed)
                    if len(self.speed_history) > 5:
                        self.speed_history = self.speed_history[-5:]
                    self.avg_speed = sum(self.speed_history) / len(self.speed_history) if self.speed_history else 0
                
                # NOW reset accumulators for new leg
                self.active_wave_delta = 0.0
                self.active_wave_volume = 0.0
                
                # Reset bar counts
                if self.last_swing_dir == self.trend_dir:
                    self.impulse_bar_count = 0
                else:
                    self.pullback_bar_count = 0
                
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
                # SAVE metrics BEFORE resetting!
                
                # Finalize previous leg
                if prev_dir == self.trend_dir and self.trend_dir != 0:
                    # Previous leg was IMPULSE - save and validate
                    self.last_impulse_delta = self.active_wave_delta
                    self.last_impulse_volume = self.active_wave_volume
                    self.last_impulse_strength = self._compute_wave_strength()
                    
                    # Calculate impulse speed
                    if self.trend_dir == 1:
                        impulse_start = self.leg1_low if self.leg1_low is not None else current_low
                        impulse_end = current_high
                    else:
                        impulse_start = self.leg1_high if self.leg1_high is not None else current_high
                        impulse_end = current_low
                    
                    self.impulse_speed = self._calculate_speed(
                        impulse_start, impulse_end, max(1, self.impulse_bar_count)
                    )
                    
                    # Validate impulse strength
                    self.impulse_wave_strength_ok = self._evaluate_impulse_strength(bar_state)
                    
                    # Update speed history
                    self.speed_history.append(self.impulse_speed)
                    if len(self.speed_history) > 5:
                        self.speed_history = self.speed_history[-5:]
                    self.avg_speed = sum(self.speed_history) / len(self.speed_history) if self.speed_history else 0
                    
                elif prev_dir == -self.trend_dir and self.trend_dir != 0:
                    # Previous leg was PULLBACK - save and evaluate
                    self.pullback_delta = self.active_wave_delta
                    self.pullback_volume = self.active_wave_volume
                    self.pullback_strength = self._compute_wave_strength()
                    self.pullback_low = current_low
                    self.pullback_high = current_high
                    
                    # Calculate pullback speed
                    if self.trend_dir == 1:
                        pb_start = self.pullback_high if self.pullback_high is not None else current_high
                        pb_end = current_low
                    else:
                        pb_start = self.pullback_low if self.pullback_low is not None else current_low
                        pb_end = current_high
                    
                    self.pullback_speed = self._calculate_speed(
                        pb_start, pb_end, max(1, self.pullback_bar_count)
                    )
                    
                    # Validate pullback strength (REFINED logic)
                    self.pb_wave_strength_flag = self._evaluate_pullback_strength_refined(bar_state)
                    
                    # Update speed history
                    self.speed_history.append(self.pullback_speed)
                    if len(self.speed_history) > 5:
                        self.speed_history = self.speed_history[-5:]
                    self.avg_speed = sum(self.speed_history) / len(self.speed_history) if self.speed_history else 0
                
                # NOW reset accumulators for new leg
                self.active_wave_delta = 0.0
                self.active_wave_volume = 0.0
                
                # Reset bar counts
                if self.last_swing_dir == self.trend_dir:
                    self.impulse_bar_count = 0
                else:
                    self.pullback_bar_count = 0
                
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
        
        # Update prev tracking
        self.prev_prev_high = self.prev_bar_high
        self.prev_prev_low = self.prev_bar_low
        self.prev_bar_high = current_high
        self.prev_bar_low = current_low
        
        # Accumulate delta and volume for active wave
        self.active_wave_delta += current_delta
        self.active_wave_volume += current_volume
        
        # === NEW: Update rolling averages ===
        self._update_averages(bar_state)
        
        # === NEW: Track bar counts ===
        # Increment appropriate counter based on leg direction
        if self.active_leg_dir == self.trend_dir and self.trend_dir != 0:
            self.impulse_bar_count += 1
        elif self.active_leg_dir == -self.trend_dir and self.trend_dir != 0:
            self.pullback_bar_count += 1
        
        # === CRITICAL: Structure Preservation Check ===
        # If pullback breaks leg 1 level, structure is invalid → RESET legs
        if self.mgann_leg_index >= 2 and self.trend_dir != 0:
            structure_broken = False
            
            if self.trend_dir == 1:  # Uptrend
                # Check if current low breaks below leg 1 low
                if self.leg1_low is not None and current_low < self.leg1_low:
                    structure_broken = True
            else:  # Downtrend (trend_dir == -1)
                # Check if current high breaks above leg 1 high
                if self.leg1_high is not None and current_high > self.leg1_high:
                    structure_broken = True
            
            if structure_broken:
                # Structure invalidated - RESET leg count but keep trend
                self.mgann_leg_index = 1
                self.last_impulse_delta = 0.0
                self.last_impulse_volume = 0.0
                self.pullback_delta = 0.0
                self.pullback_volume = 0.0
                self.pb_wave_strength_flag = False
                self.impulse_wave_strength_ok = False
                self.current_leg_fvg_seen = False
                self.impulse_bar_count = 0
                self.pullback_bar_count = 0
                # Update leg1 anchor to current level
                if self.trend_dir == 1:
                    self.leg1_low = current_low
                else:
                    self.leg1_high = current_high
        
        # Calculate wave strength (simple delta/volume ratio)
        wave_strength = self._compute_wave_strength()

        # === NEW: Check for first FVG in current leg ===
        mgann_leg_first_fvg = self._check_leg_first_fvg(bar_state)

        # === NEW: Track whether current leg1 breaks previous trend extreme ===
        if self.mgann_leg_index == 1 and self.trend_dir != 0:
            if self.trend_dir == 1 and self.prev_trend_high is not None and current_high > self.prev_trend_high:
                self.leg1_cut_prev_extreme = True
            elif self.trend_dir == -1 and self.prev_trend_low is not None and current_low < self.prev_trend_low:
                self.leg1_cut_prev_extreme = True

        # === NEW: Pivot-break reset (cutting prior swing extremes) ===
        # If current move takes out the opposite swing extreme, start a fresh leg 1 in that direction.
        if self.last_swing_high is not None and current_high > self.last_swing_high and self.trend_dir != 1:
            self._hard_reset(1, current_low, current_high, self.last_swing_low, self.last_swing_high)
            self.last_swing_high = current_high
            self.last_swing_dir = 1
        elif self.last_swing_low is not None and current_low < self.last_swing_low and self.trend_dir != -1:
            self._hard_reset(-1, current_low, current_high, self.last_swing_low, self.last_swing_high)
            self.last_swing_low = current_low
            self.last_swing_dir = -1
        
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
        
        # === NEW: Export wave strength validation fields (v1.3.0) ===
        bar_state["impulse_wave_strength_ok"] = bool(self.impulse_wave_strength_ok)
        bar_state["impulse_speed"] = round(self.impulse_speed, 4)
        bar_state["pullback_speed"] = round(self.pullback_speed, 4)
        bar_state["avg_delta"] = round(self.avg_delta, 2)
        bar_state["avg_volume"] = round(self.avg_volume, 2)
        bar_state["avg_speed"] = round(self.avg_speed, 4)
        # Export whether current leg1 has broken the previous trend extreme
        bar_state["leg1_breaks_prev_extreme"] = bool(self.leg1_cut_prev_extreme)

        
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
