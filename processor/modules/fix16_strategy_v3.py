#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy V3 - With CHoCH Event Tracking

Logic:
1. CHoCH DOWN/UP event occurs (marks trend change)
2. Leg 1 pullback begins AFTER CHoCH
3. FVG detected during Leg 1
4. Signal generated

SL at Leg 1 low, TP at 3R
"""

from processor.core.module_base import BaseModule


class Fix16StrategyV3(BaseModule):
    """Strategy with CHoCH event tracking."""
    
    def __init__(self, tick_size=0.1, risk_reward_ratio=3.0):
        super().__init__()
        self.tick_size = tick_size
        self.rr_ratio = risk_reward_ratio
        self.bar_count = 0
        self.signal_count = 0
        
        # Track CHoCH events
        self.last_choch_type = None  # 'UP' or 'DOWN'
        self.last_choch_bar = None
    
    def process_bar(self, bar_state):
        """Generate signal with CHoCH confirmation."""
        self.bar_count += 1
        
        # Update CHoCH tracking
        if bar_state.get('ext_choch_up'):
            self.last_choch_type = 'UP'
            self.last_choch_bar = self.bar_count
        elif bar_state.get('ext_choch_down'):
            self.last_choch_type = 'DOWN'
            self.last_choch_bar = self.bar_count
        
        # Extract fields
        leg = bar_state.get('mgann_leg_index', 0)
        close = bar_state.get('close', 0)
        last_swing_low = bar_state.get('last_swing_low')
        last_swing_high = bar_state.get('last_swing_high')
        fvg_detected = bar_state.get('fvg_detected', False)
        fvg_type = bar_state.get('fvg_type')
        fvg_top = bar_state.get('fvg_top')
        fvg_bottom = bar_state.get('fvg_bottom')
        
        # === LONG SIGNAL ===
        # Requires: CHoCH UP occurred (new UPTREND) + Leg 1 + pullback zone + FVG bullish
        if (self.last_choch_type == 'UP' and
            leg == 1 and 
            last_swing_low is not None and close > last_swing_low and
            fvg_detected and fvg_type == 'bullish' and
            fvg_top is not None and fvg_bottom is not None):
            
            # Calculate trade params
            entry = close
            sl = last_swing_low - self.tick_size
            risk = entry - sl
            tp = entry + (risk * self.rr_ratio)
            
            self.signal_count += 1
            bar_state['signal_type'] = 'LONG'
            bar_state['entry_price'] = round(entry, 2)
            bar_state['sl'] = round(sl, 2)
            bar_state['tp'] = round(tp, 2)
            bar_state['risk'] = round(risk, 2)
            bar_state['reward'] = round(risk * self.rr_ratio, 2)
            bar_state['choch_bars_ago'] = self.bar_count - self.last_choch_bar if self.last_choch_bar else None
            
            return bar_state
        
        # === SHORT SIGNAL ===
        # Requires: CHoCH DOWN occurred (new DOWNTREND) + Leg 1 + pullback zone + FVG bearish
        if (self.last_choch_type == 'DOWN' and
            leg == 1 and
            last_swing_high is not None and close < last_swing_high and
            fvg_detected and fvg_type == 'bearish' and
            fvg_top is not None and fvg_bottom is not None):
            
            # Calculate trade params
            entry = close
            sl = last_swing_high + self.tick_size
            risk = sl - entry
            tp = entry - (risk * self.rr_ratio)
            
            self.signal_count += 1
            bar_state['signal_type'] = 'SHORT'
            bar_state['entry_price'] = round(entry, 2)
            bar_state['sl'] = round(sl, 2)
            bar_state['tp'] = round(tp, 2)
            bar_state['risk'] = round(risk, 2)
            bar_state['reward'] = round(risk * self.rr_ratio, 2)
            bar_state['choch_bars_ago'] = self.bar_count - self.last_choch_bar if self.last_choch_bar else None
            
            return bar_state
        
        # No signal
        bar_state['signal_type'] = None
        return bar_state
    
    def get_state(self):
        return {
            'bar_count': self.bar_count,
            'signal_count': self.signal_count,
            'last_choch_type': self.last_choch_type,
        }
