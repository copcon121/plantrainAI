# ============================================================
# MODULE: FIX14_MGANN_SWING
# VERSION: v1.0.2
# PROJECT: SMC-AUTO-TRADING-L2
# AUTHOR: ChatGPT (for lala tr)
#
# DESCRIPTION:
#   MGannSwing-style INTERNAL swing detector (tick-based).
#   This module replaces all SMC internal swing logic.
#   GC-only version. tick_threshold = 6 ticks (TickSize = 0.1).
#
#   Detects:
#       - Internal zigzag (tick threshold)
#       - PB (Pullback)
#       - UT (UpThrust)
#       - SP (Shakeout)
#       - 3-push exhaustion
#       - Wave volume/delta strength
#       - Internal swing direction
#
# TAG: FIX14-MGANN-v1.0.2
#
# CHANGELOG v1.0.2:
#   - REFINED: PB criteria relaxed (range < ATR*0.7, delta < vol*0.15)
#   - REFINED: UT tightened (volume > ATR*30, wick > 0.5*range)
#   - REFINED: SP tightened (volume > ATR*30, wick > 0.5*range)
#   - REFINED: EX3 requires increasing delta/volume + distance > ATR*0.5
#
# CHANGELOG v1.0.1:
#   - FIX: push_count now resets when leg direction changes
#   - FIX: UT requires volume > atr14*20
#   - FIX: SP requires volume > atr14*20
#   - FIX: PB requires abs(delta_close) < volume*0.05 and range < atr14*0.4
#   - FIX: wave_strength returns 0 if leg_volume_sum < 1
# ============================================================

from processor.core.module_base import BaseModule

class Fix14MgannSwing(BaseModule):

    def __init__(self, threshold_ticks=6):
        """
        GC-only default: 6 ticks * TickSize(0.1) = 0.6 points
        This is MGann internal sensitivity.
        """
        super().__init__()
        self.threshold_ticks = threshold_ticks

        # internal memory
        self.last_swing_high = None
        self.last_swing_low = None
        self.last_swing_dir = 0   # 1 = up, -1 = down
        self.push_count = 0       # for 3-push exhaustion
        
        # v1.0.2: Track push quality for EX3
        self.push_delta_history = []    # Track delta sums per push
        self.push_volume_history = []   # Track volume sums per push
        self.push_distance_history = [] # Track swing distances per push


    # ------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------
    def _is_new_swing_high(self, bar_state, threshold_points):
        if self.last_swing_low is None:
            return False
        # price moved up enough from last known low
        return bar_state.get("high", 0) - self.last_swing_low >= threshold_points

    def _is_new_swing_low(self, bar_state, threshold_points):
        if self.last_swing_high is None:
            return False
        # price moved down enough from last known high
        return self.last_swing_high - bar_state.get("low", 0) >= threshold_points


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
        
        Args:
            bar_state: Current bar fields (dict)
            history: Optional recent bar_state list for context
            
        Returns:
            Updated bar_state dict
        """

        threshold_points = self.threshold_ticks * bar_state.get("tick_size", 0.1)
        atr14 = bar_state.get("atr14", bar_state.get("atr_14", 0.5))

        # Initialize first swings
        if self.last_swing_high is None and self.last_swing_low is None:
            self.last_swing_high = bar_state.get("high")
            self.last_swing_low = bar_state.get("low")

        # Track UT/SP/PB
        ut_flag = self._detect_UT(bar_state)
        sp_flag = self._detect_SP(bar_state)

        # Check swing creation
        created_high = False
        created_low = False
        
        # Store previous direction to detect changes
        prev_swing_dir = self.last_swing_dir
        
        # Get current bar data for push tracking
        current_delta = bar_state.get("delta", 0)
        current_volume = bar_state.get("volume", 0)

        # New swing high?
        if self._is_new_swing_high(bar_state, threshold_points):
            swing_distance = bar_state.get("high") - self.last_swing_low
            
            self.last_swing_high = bar_state.get("high")
            self.last_swing_dir = 1
            created_high = True
            
            # FIX v1.0.1: Reset push_count if direction changed
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

        # New swing low?
        elif self._is_new_swing_low(bar_state, threshold_points):
            swing_distance = self.last_swing_high - bar_state.get("low")
            
            self.last_swing_low = bar_state.get("low")
            self.last_swing_dir = -1
            created_low = True
            
            # FIX v1.0.1: Reset push_count if direction changed
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

        # Wave strength calc - use simple defaults if accumulation not available
        leg_delta = bar_state.get("delta", 0)
        leg_volume = bar_state.get("volume", 0)
        wave_strength = self._compute_wave_strength(bar_state, leg_delta, leg_volume)

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

        return bar_state
