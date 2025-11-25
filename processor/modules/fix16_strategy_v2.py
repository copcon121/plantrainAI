#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy V2 - Clean Rebuild

Simple logic:
- Leg 1 pullback (after CHoCH)
- Pullback zone entry (above last_swing_low for LONG, below last_swing_high for SHORT)
- FVG detected
- SL at Leg 1 low + 1 tick, TP at 3R
"""

from processor.core.module_base import BaseModule


class Fix16StrategyV2(BaseModule):
    """Clean strategy rebuild - minimal conditions."""
    
    def __init__(self, tick_size=0.1, risk_reward_ratio=3.0):
        super().__init__()
        self.tick_size = tick_size
        self.rr_ratio = risk_reward_ratio
        self.bar_count = 0
        self.signal_count = 0
    
    def process_bar(self, bar_state):
        """
        Generate signal if all conditions met:
        1. Leg 1 (pullback after CHoCH)
        2. In pullback zone (close > last_swing_low for LONG)
        3. FVG detected
        """
        self.bar_count += 1
        
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
        if (leg == 1 and 
            last_swing_low is not None and close > last_swing_low and
            fvg_detected and fvg_type == 'bullish' and
            fvg_top is not None and fvg_bottom is not None):
            
            # Calculate trade params
            entry = close
            sl = last_swing_low - self.tick_size  # 1 tick below Leg 1 low
            risk = entry - sl
            tp = entry + (risk * self.rr_ratio)
            
            self.signal_count += 1
            bar_state['signal_type'] = 'LONG'
            bar_state['entry_price'] = round(entry, 2)
            bar_state['sl'] = round(sl, 2)
            bar_state['tp'] = round(tp, 2)
            bar_state['risk'] = round(risk, 2)
            bar_state['reward'] = round(risk * self.rr_ratio, 2)
            
            return bar_state
        
        # === SHORT SIGNAL ===
        if (leg == 1 and
            last_swing_high is not None and close < last_swing_high and
            fvg_detected and fvg_type == 'bearish' and
            fvg_top is not None and fvg_bottom is not None):
            
            # Calculate trade params
            entry = close
            sl = last_swing_high + self.tick_size  # 1 tick above Leg 1 high
            risk = sl - entry
            tp = entry - (risk * self.rr_ratio)
            
            self.signal_count += 1
            bar_state['signal_type'] = 'SHORT'
            bar_state['entry_price'] = round(entry, 2)
            bar_state['sl'] = round(sl, 2)
            bar_state['tp'] = round(tp, 2)
            bar_state['risk'] = round(risk, 2)
            bar_state['reward'] = round(risk * self.rr_ratio, 2)
            
            return bar_state
        
        # No signal
        bar_state['signal_type'] = None
        return bar_state
    
    def get_state(self):
        return {
            'bar_count': self.bar_count,
            'signal_count': self.signal_count,
        }
