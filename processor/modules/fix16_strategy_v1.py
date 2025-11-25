#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Module v1 - Label Rules v3 Implementation

Implements trade signal generation based on Label Rules v3:
- M1 structure context (ext_dir)
- Early leg (1-2)
- PB wave strength OK (LOOSE v0.1)
- FVG entry (NEW or retest, max 3 signals)

Risk Management:
- Entry: Close price at signal bar
- SL: FVG bottom - 2 ticks (LONG) or FVG top + 2 ticks (SHORT)
- TP: 3R (3x risk)
"""

from processor.core.module_base import BaseModule


TAG = "fix16_strategy_v1"
VERSION = "v1.1.0"

CHANGELOG = """
v1.1.0 (2024-11-24):
- Added M5 directional filter (Condition 0)
- LONG: requires M5 BOS/CHoCH UP
- SHORT: requires M5 BOS/CHoCH DOWN
- Filters out counter-trend M1 setups

v1.0.0 (2024-11-24):
- Initial implementation of Label Rules v3
- 4 conditions: M1 context + early leg + pb_ok (STRICT v0.2) + FVG
- FVG retest tracking (max 3 signals per FVG)
- Risk management: SL = FVG bottom - 2 ticks, TP = 3R
"""


class Fix16StrategyV1(BaseModule):
    """
    Strategy Module v1 - Label Rules v3 signal generator.
    
    Generates trade signals based on:
    1. M1 structure (ext_dir)
    2. Early leg (mgann_leg_index 1-2)
    3. PB wave strength OK (LOOSE v0.1)
    4. FVG entry (NEW or retest)
    """
    
    def __init__(self, tick_size=0.1, risk_reward_ratio=3.0, sl_buffer_ticks=2):
        """
        Args:
            tick_size: Price tick size (default 0.1 for GC)
            risk_reward_ratio: R:R ratio for TP (default 3.0)
            sl_buffer_ticks: Ticks beyond FVG for SL (default 2)
        """
        super().__init__()
        self.tick_size = tick_size
        self.rr_ratio = risk_reward_ratio
        self.sl_buffer = sl_buffer_ticks * tick_size
        
        # FVG tracking for retest limit
        self.active_fvgs = []  # List of {top, bottom, type, signal_count, bar_created}
        self.bar_count = 0
    
    def _add_fvg(self, top, bottom, fvg_type):
        """Add new FVG zone to tracking."""
        self.active_fvgs.append({
            'top': top,
            'bottom': bottom,
            'type': fvg_type,
            'signal_count': 1,  # NEW FVG = signal #1
            'bar_created': self.bar_count,
        })
    
    def _check_fvg_retest(self, price, fvg_type):
        """
        Check if price retests any active FVG.
        Returns (can_signal, fvg_zone) where can_signal = True if signal_count < 3.
        """
        for fvg in self.active_fvgs:
            if fvg['type'] != fvg_type:
                continue
            
            # Check if price is in FVG zone
            if fvg['bottom'] <= price <= fvg['top']:
                if fvg['signal_count'] < 3:  # Allow max 3 signals
                    fvg['signal_count'] += 1
                    return True, fvg
                else:
                    # Already 3 signals, invalid
                    return False, fvg
        
        return False, None
    
    def _cleanup_old_fvgs(self, max_age=100):
        """Remove FVGs older than max_age bars."""
        self.active_fvgs = [
            fvg for fvg in self.active_fvgs
            if self.bar_count - fvg['bar_created'] < max_age
        ]
    
    def _check_long_conditions(self, bar_state):
        """
        Check LONG signal conditions.
        
        Returns:
            (bool, dict): (signal_valid, fvg_info)
        """
        # === DISABLED: M5 filter (testing CHoCH range filter in isolation) ===
        # m5_bullish = bar_state.get('m5_ext_dir', 0) == 1
        # if not m5_bullish:
        #     return False, None
        
        # === Condition 1: Leg 1 pullback (after CHoCH) ===
        # CHoCH already happened, we're in Leg 1 pullback zone
        leg = bar_state.get('mgann_leg_index', 0)
        if leg != 1:
            return False, None
        
        # === Condition 1.5: Pullback zone entry filter ===
        # LONG (after CHoCH DOWN): entry must be ABOVE last_swing_low
        # This ensures we enter in the PULLBACK zone, not at breakout level
        entry_price = bar_state.get('close', 0)
        last_swing_low = bar_state.get('last_swing_low', None)
        
        if last_swing_low is not None and entry_price <= last_swing_low:
            # Entry at or below CHoCH level = too close to breakout
            return False, None
        
        # Condition 2: Early leg
        leg = bar_state.get('mgann_leg_index', 0)
        early_leg = 0 < leg <= 2
        if not early_leg:
            return False, None
        
        # Condition 3: PB wave strength OK (STRICT v0.2)
        # DISABLED FOR TESTING
        # pb_ok = bar_state.get('pb_wave_strength_ok', False)
        # if not pb_ok:
        #     return False, None
        
        # === Condition 4: FVG entry ===
        # Read from ROOT level (pipeline flattens bar fields)
        fvg_new = bar_state.get('fvg_detected', False)
        fvg_bullish = bar_state.get('fvg_type') == 'bullish'
        
        if fvg_new and fvg_bullish:
            # NEW FVG detected
            fvg_top = bar_state.get('fvg_top', 0)
            fvg_bottom = bar_state.get('fvg_bottom', 0)
            self._add_fvg(fvg_top, fvg_bottom, 'bullish')
            
            # === DISABLED FOR ML TRAINING: Risk filter ===
            # Let ML model learn when high-risk LONG fails
            # entry_price = bar_state.get('close', 0)
            # leg_low = bar_state.get('mgann_leg_low')
            # if leg_low is not None:
            #     potential_sl = leg_low - (1 * self.tick_size)
            #     potential_risk = entry_price - potential_sl
            #     if potential_risk > 8.0:
            #         return False, None
            
            return True, {'top': fvg_top, 'bottom': fvg_bottom, 'new': True}
        
        # Check retest of existing FVG
        price = bar_state.get('close', 0)
        can_signal, fvg_zone = self._check_fvg_retest(price, 'bullish')
        
        if can_signal:
            # === DISABLED FOR ML TRAINING: Risk filter ===
            # leg_low = bar_state.get('mgann_leg_low')
            # if leg_low is not None:
            #     potential_sl = leg_low - (1 * self.tick_size)
            #     potential_risk = price - potential_sl
            #     if potential_risk > 8.0:
            #         return False, None
            
            return True, {'top': fvg_zone['top'], 'bottom': fvg_zone['bottom'], 'new': False}
        
        return False, None
    
    def _check_short_conditions(self, bar_state):
        """
        Check SHORT signal conditions.
        
        Returns:
            (bool, dict): (signal_valid, fvg_info)
        """
        # === Condition 1: Leg 1 pullback (after CHoCH) ===
        # CHoCH already happened, we're in Leg 1 pullback zone
        leg = bar_state.get('mgann_leg_index', 0)
        if leg != 1:
            return False, None
        
        # === Condition 1.5: Pullback zone entry filter ===
        # SHORT (after CHoCH UP): entry must be BELOW last_swing_high
        # This ensures we enter in the PULLBACK zone, not at breakout level
        entry_price = bar_state.get('close', 0)
        last_swing_high = bar_state.get('last_swing_high', None)
        
        if last_swing_high is not None and entry_price >= last_swing_high:
            # Entry at or above CHoCH level = too close to breakout
            return False, None
        
        # Condition 2: Early leg
        leg = bar_state.get('mgann_leg_index', 0)
        early_leg = 0 < leg <= 2
        if not early_leg:
            return False, None
        
        # Condition 3: PB wave strength OK (STRICT v0.2)
        # DISABLED FOR TESTING
        # pb_ok = bar_state.get('pb_wave_strength_ok', False)
        # if not pb_ok:
        #     return False, None
        
        # Condition 4: FVG entry
        # Read from ROOT level (pipeline flattens bar fields)
        fvg_new = bar_state.get('fvg_detected', False)
        fvg_bearish = bar_state.get('fvg_type') == 'bearish'
        
        if fvg_new and fvg_bearish:
            # NEW FVG detected
            fvg_top = bar_state.get('fvg_top', 0)
            fvg_bottom = bar_state.get('fvg_bottom', 0)
            self._add_fvg(fvg_top, fvg_bottom, 'bearish')
            
            return True, {'top': fvg_top, 'bottom': fvg_bottom, 'new': True}
        
        # Check retest
        price = bar_state.get('close', 0)
        can_signal, fvg_zone = self._check_fvg_retest(price, 'bearish')
        
        if can_signal:
            return True, {'top': fvg_zone['top'], 'bottom': fvg_zone['bottom'], 'new': False}
        
        return False, None
    
    def _calculate_long_trade(self, bar_state, fvg_info):
        """
        Calculate LONG trade parameters.
        
        Entry: Close price
        SL: Leg low - 1 tick (leg extreme, not FVG edge)
        TP: Entry + 3R
        """
        entry = bar_state.get('close', 0)
        
        # === NEW: SL at leg extreme (not FVG) ===
        leg_low = bar_state.get('mgann_leg_low')
        
        if leg_low is not None:
            sl = leg_low - (1 * self.tick_size)  # 1 tick below leg low
        else:
            # Fallback to FVG if leg_low not available
            sl = fvg_info['bottom'] - self.sl_buffer
        
        risk = entry - sl
        tp = entry + (risk * self.rr_ratio)
        
        return {
            'direction': 'LONG',
            'entry': round(entry, 2),
            'sl': round(sl, 2),
            'tp': round(tp, 2),
            'risk': round(risk, 2),
            'reward': round(risk * self.rr_ratio, 2),
            'rr_ratio': self.rr_ratio,
        }
    
    def _calculate_short_trade(self, bar_state, fvg_info):
        """
        Calculate SHORT trade parameters.
        
        Entry: Close price
        SL: Leg high + 1 tick (leg extreme, not FVG edge)
        TP: Entry - 3R
        """
        entry = bar_state.get('close', 0)
        
        # === NEW: SL at leg extreme (not FVG) ===
        leg_high = bar_state.get('mgann_leg_high')
        
        if leg_high is not None:
            sl = leg_high + (1 * self.tick_size)  # 1 tick above leg high
        else:
            # Fallback to FVG if leg_high not available
            sl = fvg_info['top'] + self.sl_buffer
        
        risk = sl - entry
        tp = entry - (risk * self.rr_ratio)
        
        return {
            'direction': 'SHORT',
            'entry': round(entry, 2),
            'sl': round(sl, 2),
            'tp': round(tp, 2),
            'risk': round(risk, 2),
            'reward': round(risk * self.rr_ratio, 2),
            'rr_ratio': self.rr_ratio,
        }
    
    def process_bar(self, bar_state):
        """
        Process bar and generate trade signal if conditions met.
        
        Args:
            bar_state: Bar data with all required fields
        
        Returns:
            dict: Bar state with 'signal' field added if signal generated
        """
        self.bar_count += 1
        
        # Cleanup old FVGs periodically
        if self.bar_count % 50 == 0:
            self._cleanup_old_fvgs(max_age=100)
        
        # Check LONG conditions
        long_valid, fvg_info = self._check_long_conditions(bar_state)
        if long_valid:
            trade = self._calculate_long_trade(bar_state, fvg_info)
            
            bar_state['signal'] = {
                'timestamp': bar_state.get('timestamp', ''),
                'bar_index': self.bar_count - 1,
                'signal_type': 'ENTRY',
                'direction': 'LONG',
                'leg': bar_state.get('mgann_leg_index', 0),
                'fvg_new': fvg_info['new'],
                'fvg_zone': {'top': fvg_info['top'], 'bottom': fvg_info['bottom']},
                'trade': trade,
            }
            return bar_state
        
        # Check SHORT conditions
        short_valid, fvg_info = self._check_short_conditions(bar_state)
        if short_valid:
            trade = self._calculate_short_trade(bar_state, fvg_info)
            
            bar_state['signal'] = {
                'timestamp': bar_state.get('timestamp', ''),
                'bar_index': self.bar_count - 1,
                'signal_type': 'ENTRY',
                'direction': 'SHORT',
                'leg': bar_state.get('mgann_leg_index', 0),
                'fvg_new': fvg_info['new'],
                'fvg_zone': {'top': fvg_info['top'], 'bottom': fvg_info['bottom']},
                'trade': trade,
            }
            return bar_state
        
        # No signal
        return bar_state
    
    def get_state(self):
        """Return current module state."""
        return {
            'bar_count': self.bar_count,
            'active_fvgs': len(self.active_fvgs),
        }
