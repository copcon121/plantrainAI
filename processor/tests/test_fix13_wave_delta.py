"""Tests for Fix #13: Wave Delta Module."""
from processor.modules.fix13_wave_delta import WaveDeltaModule


def test_wave_closes_on_delayed_swing_uses_smc_prices():
    """
    Swing confirmation arrives late in SMC; ensure wave closes on the signal bar but
    uses SMC swing prices (not the signal bar high/low) and includes the signal bar's delta.
    """
    module = WaveDeltaModule()

    # First swing low confirmed late: SMC provides last_swing_low=99, bar's low=100.
    bar_low = {
        "bar_index": 10,
        "delta": 10,
        "volume": 100,
        "buy_volume": 60,
        "sell_volume": 40,
        "is_swing_low": True,
        "is_swing_high": False,
        "last_swing_low": 99.0,
        "low": 100.0,
    }
    out_low = module.process_bar(bar_low, history=[])
    assert out_low["active_wave_delta"] == 0
    assert out_low["last_wave_delta"] == 0

    # Mid-leg bar accumulates into active wave.
    bar_mid = {
        "bar_index": 11,
        "delta": 5,
        "volume": 80,
        "buy_volume": 50,
        "sell_volume": 30,
        "is_swing_low": False,
        "is_swing_high": False,
    }
    module.process_bar(bar_mid, history=[])

    # Swing high confirmed late: SMC provides last_swing_high=101, bar's high=102.
    bar_high = {
        "bar_index": 12,
        "delta": 7,
        "volume": 90,
        "buy_volume": 40,
        "sell_volume": 50,
        "is_swing_high": True,
        "is_swing_low": False,
        "last_swing_high": 101.0,
        "high": 102.0,
    }
    out_high = module.process_bar(bar_high, history=[])

    # Wave closed on bar 12: delta includes mid + signal bar, prices use SMC pivots.
    assert out_high["last_wave_delta"] == 12  # 5 + 7
    assert out_high["last_wave_direction"] == 1
    assert out_high["last_wave_start_bar"] == 10
    assert out_high["last_wave_end_bar"] == 12
    assert out_high["last_wave_start_price"] == 99.0
    assert out_high["last_wave_end_price"] == 101.0
