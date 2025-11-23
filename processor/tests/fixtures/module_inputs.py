"""
Sample per-module input bars to exercise required fields and typical values.
These are lightweight fixtures, not exhaustive edge cases.
"""

BASE_BAR = {
    "bar_index": 1250,
    "timestamp": "2024-01-15T10:45:00Z",
    "open": 100.15,
    "high": 100.55,
    "low": 100.05,
    "close": 100.45,
    "volume": 4500,
    "buy_volume": 2800,
    "sell_volume": 1700,
    "delta": 1100,
    "cumulative_delta": 18500,
    "atr_14": 0.22,
}

MODULE_FIX02 = {
    **BASE_BAR,
    "fvg_detected": True,
    "fvg_type": "bullish",
    "fvg_top": 100.40,
    "fvg_bottom": 100.20,
    "fvg_gap_size": 0.20,
    "fvg_filled": False,
    "fvg_fill_percentage": 0.0,
    "fvg_creation_volume": 5200,
    "fvg_creation_delta": 1800,
}

MODULE_FIX03 = {
    **BASE_BAR,
    "choch_detected": False,
    "choch_type": None,
    "choch_bars_ago": 15,
    "bos_detected": True,
    "bos_type": "bullish",
    "bos_bars_ago": 5,
    "current_trend": "bullish",
    "last_structure_break": "bos",
}

MODULE_FIX05 = {
    **MODULE_FIX02,
    "nearest_ob_top": 100.80,
    "nearest_ob_bottom": 100.50,
    "last_swing_high": 100.70,
    "last_swing_low": 99.80,
}

MODULE_FIX06 = {
    **BASE_BAR,
    "last_swing_high": 100.70,
    "last_swing_low": 99.80,
    "recent_swing_high": 100.70,
    "recent_swing_low": 99.80,
    "nearest_liquidity_high": 100.90,
    "nearest_liquidity_low": 99.40,
    "prev_session_high": 101.00,
    "prev_session_low": 99.20,
}

MODULE_FIX07 = {
    **BASE_BAR,
    "adx_14": 32.5,
    "di_plus_14": 25.0,
    "di_minus_14": 12.0,
    "current_trend": "bullish",
}

MODULE_FIX08 = {
    **BASE_BAR,
    "is_swing_high": False,
    "is_swing_low": True,
}

MODULE_FIX10 = {
    **BASE_BAR,
    "fvg_type": "bullish",
    "current_trend": "bullish",
    "htf_high": 101.00,
    "htf_low": 99.50,
    "htf_close": 100.40,
    "htf_ema_20": 100.20,
    "htf_ema_50": 99.90,
    "htf_is_swing_high": False,
    "htf_is_swing_low": False,
}

MODULE_FIX11 = {
    **BASE_BAR,
    "nearest_liquidity_high": 100.90,
    "nearest_liquidity_low": 99.40,
    "liquidity_high_type": "swing",
    "liquidity_low_type": "equal_lows",
}

MODULE_FIX13 = {
    **BASE_BAR,
    "is_swing_low": True,
    "last_swing_low": 99.00,
    "low": 100.00,
}
