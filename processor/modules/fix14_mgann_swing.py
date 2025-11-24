# ============================================================
# MODULE: FIX14_MGANN_SWING
# VERSION: v1.1.0
# PROJECT: SMC-AUTO-TRADING-L2
# AUTHOR: ChatGPT (for lala tr)
#
# DESCRIPTION:
#   MGannSwing-style INTERNAL swing detector using authentic
#   W.D. Gann 2-bar swing chart construction rules.
#   This module replaces all SMC internal swing logic.
#
#   Detects:
#       - Internal zigzag (Gann 2-bar rule)
#       - PB (Pullback)
#       - UT (UpThrust)
#       - SP (Shakeout)
#       - 3-push exhaustion
#       - Wave volume/delta strength
#       - Internal swing direction
#
# TAG: FIX14-MGANN-v1.1.0
#
# CHANGELOG v1.1.0:
#   - MAJOR: Replaced threshold-based with authentic Gann 2-bar rule
#   - Gann Rule: 2 bars with higher highs → start upswing
#   - Gann Rule: 2 bars with lower lows → start downswing
#   - Exception: bar high > swing high → start upswing
#   - Exception: bar low < swing low → start downswing
#   - threshold_ticks parameter now deprecated (kept for compatibility)
#
# CHANGELOG v1.0.2:
#   - REFINED: PB criteria relaxed (range < ATR*0.7, delta < vol*0.15)
#   - REFINED: UT tightened (volume > ATR*30, wick > 0.5*range)
#   - REFINED: SP tightened (volume > ATR*30, wick > 0.5*range)
#   - REFINED: EX3 requires increasing delta/volume + distance > ATR*0.5
# ============================================================

from processor.core.module_base import BaseModule

class Fix14MgannSwing(BaseModule):

    def __init__(self, threshold_ticks=6):
        """
        v1.1.0: Uses authentic Gann 2-bar rule (threshold_ticks deprecated)
        threshold_ticks parameter kept for backward compatibility but not used.
        """
        super().__init__()
        self.threshold_ticks = threshold_ticks  # Deprecated in v1.1.0

        # Gann swing memory
        self.last_swing_high = None
        self.last_swing_low = None
        self.last_swing_dir = 0   # 1 = up, -1 = down
        self.push_count = 0       # for 3-push exhaustion
        
        # Previous bar tracking for Gann 2-bar rule
        self.prev_bar_high = None
        self.prev_bar_low = None
        self.prev_prev_high = None  # For 2-bar sequence
        self.prev_prev_low = None   # For 2-bar sequence
        
        # v1.0.2: Track push quality for EX3
        self.push_delta_history = []    # Track delta sums per push
        self.push_volume_history = []   # Track volume sums per push
        self.push_distance_history = [] # Track swing distances per push

        # MGann leg tracking
        self.trend_dir = 0              # External/trend direction (1 / -1)
        self.mgann_leg_index = 0        # Current leg counter (1,2,3,...)
        self.active_leg_dir = 0         # Direction of active internal leg
        self.active_leg_delta = 0.0     # Delta accumulated for active leg
        self.active_leg_volume = 0.0    # Volume accumulated for active leg
        self.current_leg_low = None     # Low of active leg
        self.current_leg_high = None    # High of active leg
        self.current_leg_fvg_seen = False  # First FVG flag per leg

        # Impulse/pullback bookkeeping
        self.last_impulse_delta = 0.0
        self.last_impulse_volume = 0.0
        self.last_impulse_strength = 0
        self.pullback_delta = 0.0
        self.pullback_volume = 0.0
        self.pullback_strength = 0
        self.pullback_low = None
        self.pullback_high = None
        self.pb_wave_strength_flag = False
        self.leg1_low = None
        self.leg1_high = None


    # ------------------------------------------------------------
    # Gann 2-Bar Swing Logic
    # ------------------------------------------------------------
    def _check_gann_upswing(self, current_high, prev_high, prev_prev_high):
        """
        Gann Rule for UPSWING:
        - 2 bars with higher highs → start upswing
        - Exception: bar high > previous swing high → start upswing
        """
        # Exception: break above swing high
        if self.last_swing_high is not None and current_high > self.last_swing_high:
            return True
        
        # 2-bar rule: need sequential higher highs
        if prev_high is not None and prev_prev_high is not None:
            if current_high > prev_high and prev_high > prev_prev_high:
                return True
        
        return False
    
    def _check_gann_downswing(self, current_low, prev_low, prev_prev_low):
        """
        Gann Rule for DOWNSWING:
        - 2 bars with lower lows → start downswing
        - Exception: bar low < previous swing low → start downswing
        """
        # Exception: break below swing low
        if self.last_swing_low is not None and current_low < self.last_swing_low:
            return True
        
        # 2-bar rule: need sequential lower lows
        if prev_low is not None and prev_prev_low is not None:
            if current_low < prev_low and prev_low < prev_prev_low:
                return True
        
        return False


    # ------------------------------------------------------------
    # Volume/Delta behavior signatures (MGann style)
    # ------------------------------------------------------------
    def _detect_UT(self, bar_state):
        """
        UpThrust = new high wick + weak delta + close back inside.
        
        v1.0.2 criteria (tightened):
        - wick_up > range * 0.5 (from 0.4)
        - volume > atr14 * 30 (from 20)
        - delta_close < 0
        """
        high = bar_state.get("high", 0)
        open_price = bar_state.get("open", 0)
        close = bar_state.get("close", 0)
        delta_close = bar_state.get("delta_close", 0)
        bar_range = bar_state.get("range", 0)
        volume = bar_state.get("volume", 0)
        atr14 = bar_state.get("atr14", bar_state.get("atr_14", 0.5))
        
        if high > open_price and high > close:
            if delta_close < 0:
                wick_up = high - max(open_price, close)
                # v1.0.2: Stricter thresholds
                if wick_up > (bar_range * 0.5) and volume > (atr14 * 30):
                    return True
        return False

    def _detect_SP(self, bar_state):
        """
        Shakeout = sweep low + strong buy delta + close strong.
        
        v1.0.2 criteria (tightened):
        - wick_down > range * 0.5 (from 0.4)
        - delta_close > 0
        - volume > atr14 * 30 (from 20)
        """
        low = bar_state.get("low", 0)
        open_price = bar_state.get("open", 0)
        close = bar_state.get("close", 0)
        delta_close = bar_state.get("delta_close", 0)
        bar_range = bar_state.get("range", 0)
        volume = bar_state.get("volume", 0)
        atr14 = bar_state.get("atr14", bar_state.get("atr_14", 0.5))
        
        if low < min(open_price, close):
            if delta_close > 0:
                wick_down = min(open_price, close) - low
                # v1.0.2: Stricter thresholds
                if wick_down > (bar_range * 0.5) and volume > (atr14 * 30):
                    return True
        return False

    def _detect_PB(self, bar_state, swing_dir):
        """
        Pullback = shallow retrace + low volume/delta.
        
        v1.0.2 criteria (relaxed):
        - abs(delta_close) < volume * 0.15 (from 0.05)
        - range < atr14 * 0.7 (from 0.4)
        - counter-trend move relative to leg direction
        """
        close = bar_state.get("close", 0)
        open_price = bar_state.get("open", 0)
        delta_close = bar_state.get("delta_close", 0)
        volume = bar_state.get("volume", 1)
        bar_range = bar_state.get("range", 0)
        atr14 = bar_state.get("atr14", bar_state.get("atr_14", 0.5))
        
        # v1.0.2: Relaxed criteria for more PB detections
        if abs(delta_close) >= (volume * 0.15):
            return False
        if bar_range >= (atr14 * 0.7):
            return False
        
        if swing_dir == 1:  # up leg
            # small down move + weak selling
            return close < open_price
        else:  # down leg
            return close > open_price


    # ------------------------------------------------------------
    # Wave strength scoring
    # ------------------------------------------------------------
    def _compute_wave_strength(self, bar_state, leg_delta_sum, leg_volume_sum):
        """
        Simple scoring v1.0.1:
            40% delta strength
            40% volume strength
            20% body/momentum
            
        v1.0.1: Returns 0 if leg_volume_sum < 1 to avoid division errors
        """
        # Guard: return 0 if no volume
        if leg_volume_sum < 1:
            return 0
        
        delta_score = min(1.0, abs(leg_delta_sum) / (leg_volume_sum + 1e-9))
        atr14 = bar_state.get("atr14", bar_state.get("atr_14", 0.5))
        vol_score = min(1.0, leg_volume_sum / (atr14 * 50 + 1e-9))

        close = bar_state.get("close", 0)
        open_price = bar_state.get("open", 0)
        bar_range = bar_state.get("range", 1)
        body = abs(close - open_price)
        momentum_score = min(1.0, body / (bar_range + 1e-9))

        return int((delta_score * 0.4 + vol_score * 0.4 + momentum_score * 0.2) * 100)

    def _check_valid_push(self, current_delta, current_volume, current_distance, atr14):
        """
        v1.0.2: Validate if current push is a valid continuation.
        
        Criteria:
        - delta_sum increasing compared to previous push
        - volume_sum increasing compared to previous push
        - swing_distance > ATR * 0.5
        """
        # Check distance first
        if current_distance < (atr14 * 0.5):
            return False
        
        # If no previous pushes, accept first one with sufficient distance
        if not self.push_delta_history or not self.push_volume_history:
            return True
        
        # Compare with last push
        last_delta = abs(self.push_delta_history[-1])
        last_volume = self.push_volume_history[-1]
        
        # Require increasing delta AND volume
        if abs(current_delta) > last_delta and current_volume > last_volume:
            return True
        
        return False


    # ------------------------------------------------------------
    # MAIN EXECUTION
    # ------------------------------------------------------------
    def process_bar(self, bar_state, history=None):
        """
        Called per bar.
        Must update bar_state fields and return updated dict.
        
        v1.1.0: Uses Gann 2-bar rule for swing detection.
        
        Args:
            bar_state: Current bar fields (dict)
            history: Optional recent bar_state list for context
            
        Returns:
            Updated bar_state dict
        """
        
        # Get current bar prices
        current_high = bar_state.get("high", 0)
        current_low = bar_state.get("low", 0)
        atr14 = bar_state.get("atr14", bar_state.get("atr_14", 0.5))

        # Initialize first swings
        if self.last_swing_high is None and self.last_swing_low is None:
            self.last_swing_high = current_high
            self.last_swing_low = current_low
            self.prev_bar_high = current_high
            self.prev_bar_low = current_low

        # Track UT/SP/PB
        ut_flag = self._detect_UT(bar_state)
        sp_flag = self._detect_SP(bar_state)

        # Trend / CHoCH reset (use ext_dir/ext_choch if provided)
        self._maybe_reset_trend(bar_state, current_low, current_high)

        # Check swing creation using Gann 2-bar rule
        created_high = False
        created_low = False
        
        # Store previous direction to detect changes
        prev_swing_dir = self.last_swing_dir
        
        # Get current bar data for push tracking
        current_delta = bar_state.get("delta", 0)
        current_volume = bar_state.get("volume", 0)

        # Check for Gann UPSWING
        if self._check_gann_upswing(current_high, self.prev_bar_high, self.prev_prev_high):
            swing_distance = current_high - self.last_swing_low
            
            self.last_swing_high = current_high
            self.last_swing_dir = 1
            created_high = True
            
            # Reset push_count if direction changed
            if prev_swing_dir != 1:
                self.push_count = 0
                self.push_delta_history = []
                self.push_volume_history = []
                self.push_distance_history = []
            
            # v1.0.2: Only increment push_count if valid push
            if self._check_valid_push(current_delta, current_volume, swing_distance, atr14):
                self.push_count += 1
                self.push_delta_history.append(current_delta)
                self.push_volume_history.append(current_volume)
                self.push_distance_history.append(swing_distance)
                
                # Keep only last 3 pushes in history
                if len(self.push_delta_history) > 3:
                    self.push_delta_history = self.push_delta_history[-3:]
                    self.push_volume_history = self.push_volume_history[-3:]
                    self.push_distance_history = self.push_distance_history[-3:]

        # Check for Gann DOWNSWING (elif to avoid both triggers)
        elif self._check_gann_downswing(current_low, self.prev_bar_low, self.prev_prev_low):
            swing_distance = self.last_swing_high - current_low
            
            self.last_swing_low = current_low
            self.last_swing_dir = -1
            created_low = True
            
            # Reset push_count if direction changed
            if prev_swing_dir != -1:
                self.push_count = 0
                self.push_delta_history = []
                self.push_volume_history = []
                self.push_distance_history = []
            
            # v1.0.2: Only increment push_count if valid push
            if self._check_valid_push(current_delta, current_volume, swing_distance, atr14):
                self.push_count += 1
                self.push_delta_history.append(current_delta)
                self.push_volume_history.append(current_volume)
                self.push_distance_history.append(swing_distance)
                
                # Keep only last 3 pushes in history
                if len(self.push_delta_history) > 3:
                    self.push_delta_history = self.push_delta_history[-3:]
                    self.push_volume_history = self.push_volume_history[-3:]
                    self.push_distance_history = self.push_distance_history[-3:]

        # Update prev bar tracking for next iteration
        self.prev_prev_high = self.prev_bar_high
        self.prev_prev_low = self.prev_bar_low
        self.prev_bar_high = current_high
        self.prev_bar_low = current_low

        # Pullback detection
        pb_flag = self._detect_PB(bar_state, self.last_swing_dir)

        # 3-push exhaustion - check BEFORE resetting
        exhaustion_flag = (self.push_count >= 3)
        
        # Reset counter after exhaustion is detected
        if exhaustion_flag:
            self.push_count = 0
            self.push_delta_history = []
            self.push_volume_history = []
            self.push_distance_history = []

        history = history or []

        # ---- Leg accounting and pb_wave_strength_ok evaluation -----------
        # Detect leg direction change and finalize the previous leg before adding this bar.
        new_leg_dir = self.last_swing_dir or self.active_leg_dir or self.trend_dir
        if new_leg_dir != 0 and new_leg_dir != self.active_leg_dir:
            # Finalize the previous leg with its accumulated stats
            self._finalize_leg(self.active_leg_dir, bar_state)

            # If we just completed a pullback and resumed trend, evaluate hybrid PB rule
            if new_leg_dir == self.trend_dir and self.active_leg_dir == -self.trend_dir:
                self.pb_wave_strength_flag = self._evaluate_pullback_strength(bar_state, history)
                # Increment leg index when rejoining the trend after pullback
                self.mgann_leg_index = max(self.mgann_leg_index, 1) + 1
            elif self.mgann_leg_index == 0 and new_leg_dir == self.trend_dir:
                self.mgann_leg_index = 1
            elif new_leg_dir == -self.trend_dir:
                # New pullback starts; clear prior PB assessment until evaluated again
                self.pb_wave_strength_flag = False

            # Start a fresh leg accumulator for the new direction
            self._reset_active_leg(new_leg_dir, current_low, current_high)

        # Accumulate current bar into active leg
        if self.active_leg_dir == 0:
            self.active_leg_dir = new_leg_dir
        self.active_leg_delta += current_delta
        self.active_leg_volume += current_volume
        self.current_leg_low = current_low if self.current_leg_low is None else min(self.current_leg_low, current_low)
        self.current_leg_high = current_high if self.current_leg_high is None else max(self.current_leg_high, current_high)

        # Wave strength calc using active leg accumulation
        wave_strength = self._compute_wave_strength(bar_state, self.active_leg_delta, self.active_leg_volume)

        # ------------------------------------------------------------
        # Update bar_state with new fields
        # ------------------------------------------------------------
        bar_state["mgann_internal_swing_high"] = self.last_swing_high
        bar_state["mgann_internal_swing_low"] = self.last_swing_low
        bar_state["mgann_internal_leg_dir"] = self.last_swing_dir

        bar_state["mgann_pb"] = pb_flag
        bar_state["mgann_ut"] = ut_flag
        bar_state["mgann_sp"] = sp_flag
        bar_state["mgann_exhaustion_3push"] = exhaustion_flag

        bar_state["mgann_wave_strength"] = wave_strength
        bar_state["mgann_internal_dir"] = self.last_swing_dir
        bar_state["mgann_behavior"] = {
            "PB": pb_flag,
            "UT": ut_flag,
            "SP": sp_flag,
            "EX3": exhaustion_flag,
        }

        # ---- MGann leg exports (new fields) -------------------------------
        mgann_leg_first_fvg = self._check_leg_first_fvg(bar_state)
        bar_state["mgann_leg_index"] = int(self.mgann_leg_index) if self.mgann_leg_index else 0
        bar_state["mgann_leg_first_fvg"] = mgann_leg_first_fvg
        bar_state["pb_wave_strength_ok"] = bool(self.pb_wave_strength_flag)

        return bar_state

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _reset_active_leg(self, new_dir, bar_low, bar_high):
        """Reset accumulators for a new leg direction."""
        self.active_leg_dir = new_dir
        self.active_leg_delta = 0.0
        self.active_leg_volume = 0.0
        self.current_leg_low = bar_low
        self.current_leg_high = bar_high
        self.current_leg_fvg_seen = False

    def _maybe_reset_trend(self, bar_state, bar_low, bar_high):
        """Reset trend/leg index on CHoCH/BOS or ext_dir change."""
        ext_dir = bar_state.get("ext_dir_after_reclaim", bar_state.get("ext_dir", 0))
        choch_up = bar_state.get("ext_choch_up") or bar_state.get("ext_bos_up")
        choch_down = bar_state.get("ext_choch_down") or bar_state.get("ext_bos_down")

        inferred_dir = self.trend_dir
        if ext_dir in (1, -1):
            inferred_dir = ext_dir
        elif choch_down:
            inferred_dir = 1
        elif choch_up:
            inferred_dir = -1

        if inferred_dir in (1, -1) and inferred_dir != self.trend_dir:
            self.trend_dir = inferred_dir
            self.mgann_leg_index = 1
            self.last_impulse_delta = 0.0
            self.last_impulse_volume = 0.0
            self.last_impulse_strength = 0
            self.pullback_delta = 0.0
            self.pullback_volume = 0.0
            self.pullback_strength = 0
            self.pullback_low = None
            self.pullback_high = None
            self.pb_wave_strength_flag = False
            # Capture leg1 anchor for structure guard
            if self.trend_dir == 1:
                self.leg1_low = bar_low
            else:
                self.leg1_high = bar_high
            self._reset_active_leg(self.trend_dir, bar_low, bar_high)

    def _finalize_leg(self, prev_dir, bar_state):
        """Store stats for the leg that just completed."""
        if prev_dir == 0:
            return
        if prev_dir == self.trend_dir:
            self.last_impulse_delta = self.active_leg_delta
            self.last_impulse_volume = self.active_leg_volume
            self.last_impulse_strength = self._compute_wave_strength(
                bar_state, self.active_leg_delta, self.active_leg_volume
            )
            # Keep leg1 anchors for structure validation
            if self.mgann_leg_index == 1:
                if self.trend_dir == 1 and self.current_leg_low is not None:
                    self.leg1_low = self.current_leg_low if self.leg1_low is None else min(self.leg1_low, self.current_leg_low)
                if self.trend_dir == -1 and self.current_leg_high is not None:
                    self.leg1_high = self.current_leg_high if self.leg1_high is None else max(self.leg1_high, self.current_leg_high)
        elif prev_dir == -self.trend_dir:
            self.pullback_delta = self.active_leg_delta
            self.pullback_volume = self.active_leg_volume
            self.pullback_strength = self._compute_wave_strength(
                bar_state, self.active_leg_delta, self.active_leg_volume
            )
            self.pullback_low = self.current_leg_low
            self.pullback_high = self.current_leg_high

    def _get_avg_volume(self, history, lookback=20, fallback=0.0):
        vols = [float(b.get("volume", 0.0) or 0.0) for b in history[-lookback:]]
        if vols:
            return sum(vols) / len(vols)
        return fallback or 0.0

    def _evaluate_pullback_strength(self, bar_state, history):
        """Hybrid Rule v4 evaluation for pullback health."""
        if self.trend_dir == 0:
            return False

        impulse_vol = self.last_impulse_volume
        impulse_delta = self.last_impulse_delta
        pb_vol = self.pullback_volume
        pb_delta = self.pullback_delta
        if impulse_vol <= 0 or pb_vol <= 0:
            return False

        avg_vol = bar_state.get("avg_volume")
        if avg_vol is None:
            avg_vol = self._get_avg_volume(history, fallback=bar_state.get("volume", 0.0))
        if avg_vol <= 0:
            avg_vol = pb_vol

        pb_strength = self.pullback_strength
        delta_ratio_ok = abs(pb_delta) <= abs(impulse_delta) * 0.3
        volume_ratio_ok = pb_vol <= impulse_vol * 0.6
        delta_gate = pb_delta >= -35 if self.trend_dir == 1 else pb_delta <= 35
        volume_gate = pb_vol <= avg_vol * 1.0

        structure_ok = True
        if self.trend_dir == 1 and self.leg1_low is not None and self.pullback_low is not None:
            structure_ok = self.pullback_low > self.leg1_low
        elif self.trend_dir == -1 and self.leg1_high is not None and self.pullback_high is not None:
            structure_ok = self.pullback_high < self.leg1_high

        return (
            pb_strength < 40
            and delta_ratio_ok
            and volume_ratio_ok
            and delta_gate
            and volume_gate
            and structure_ok
        )

    def _check_leg_first_fvg(self, bar_state):
        """Detect the first FVG within the current leg."""
        fvg_detected = bool(
            bar_state.get("fvg_detected")
            or bar_state.get("fvg_up")
            or bar_state.get("fvg_down")
        )
        if not fvg_detected:
            return False

        fvg_dir = 0
        if bar_state.get("fvg_up") or bar_state.get("fvg_type") == "bullish":
            fvg_dir = 1
        elif bar_state.get("fvg_down") or bar_state.get("fvg_type") == "bearish":
            fvg_dir = -1

        if fvg_dir != 0 and fvg_dir == self.active_leg_dir and not self.current_leg_fvg_seen:
            self.current_leg_fvg_seen = True
            return True
        return False
