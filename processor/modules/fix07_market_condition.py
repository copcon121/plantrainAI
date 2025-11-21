"""
Fix #07: Market Condition.
Implement per docs/MODULE_FIX07_MARKET_CONDITION.md.

Classifies market condition based on:
- ADX/DI for trend strength
- Volatility regime (ATR percentile)
- Trending vs Ranging classification
"""
from typing import Any, Dict, List

from processor.core.module_base import BaseModule


class MarketConditionModule(BaseModule):
    """Market Condition Classification Module."""

    name = "fix07_market_condition"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.config = {
            # ADX thresholds
            "strong_trend_adx": 25.0,
            "weak_trend_adx": 15.0,
            # DI thresholds
            "min_di_diff": 5.0,
            # Volatility percentile thresholds
            "high_vol_percentile": 75,
            "low_vol_percentile": 25,
            # ATR lookback windows
            "atr_lookback_short": 20,
            "atr_lookback_long": 50,
        }

    def process_bar(
        self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Process bar and classify market condition."""
        if not self.enabled:
            return bar_state

        history = history or []

        # Get indicator values
        adx = bar_state.get("adx_14", 0)
        di_plus = bar_state.get("di_plus_14", 0)
        di_minus = bar_state.get("di_minus_14", 0)
        atr = bar_state.get("atr_14", 0)

        # Classify trend/range
        trend_info = self._classify_trend(adx, di_plus, di_minus)

        # Classify volatility
        vol_info = self._classify_volatility(atr, history)

        # Determine overall market condition
        condition = self._determine_market_condition(trend_info, vol_info)

        data_complete = all([
            adx is not None and adx > 0,
            di_plus is not None and di_minus is not None,
            atr is not None and atr > 0,
        ])

        return {
            **bar_state,
            # Trend classification
            "market_trend": trend_info["trend"],
            "market_trend_strength": round(trend_info["strength"], 3),
            "market_trend_direction": trend_info["direction"],
            "adx_class": trend_info["adx_class"],
            # Volatility classification
            "volatility_regime": vol_info["regime"],
            "volatility_percentile": round(vol_info["percentile"], 1),
            "atr_vs_avg": round(vol_info["atr_vs_avg"], 3),
            # Overall condition
            "market_condition": condition["condition"],
            "market_condition_score": round(condition["score"], 3),
            "trade_environment": condition["environment"],
            "market_data_complete": data_complete,
        }

    def _classify_trend(
        self, adx: float, di_plus: float, di_minus: float
    ) -> Dict[str, Any]:
        """Classify trend using ADX and DI."""
        di_diff = abs(di_plus - di_minus)

        # Determine trend direction
        if di_plus > di_minus:
            direction = 1  # Bullish
        elif di_minus > di_plus:
            direction = -1  # Bearish
        else:
            direction = 0  # Neutral

        # Classify ADX strength
        if adx >= self.config["strong_trend_adx"]:
            adx_class = "strong"
            if di_diff >= self.config["min_di_diff"]:
                trend = "trending"
                strength = min(adx / 50.0, 1.0)  # Normalize to 0-1
            else:
                trend = "ranging"
                strength = 0.3
        elif adx >= self.config["weak_trend_adx"]:
            adx_class = "moderate"
            if di_diff >= self.config["min_di_diff"]:
                trend = "trending"
                strength = adx / 50.0
            else:
                trend = "ranging"
                strength = 0.4
        else:
            adx_class = "weak"
            trend = "ranging"
            strength = 0.2
            direction = 0

        return {
            "trend": trend,
            "strength": strength,
            "direction": direction,
            "adx_class": adx_class,
        }

    def _classify_volatility(
        self, current_atr: float, history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Classify volatility regime using ATR percentile."""
        short_vals = [b.get("atr_14", 0) for b in history[-self.config["atr_lookback_short"] :]]
        long_vals = [b.get("atr_14", 0) for b in history[-self.config["atr_lookback_long"] :]]
        values = [a for a in (short_vals + [current_atr]) if a and a > 0]
        if len(values) < 5:
            return {"regime": "normal", "percentile": 50.0, "atr_vs_avg": 1.0}

        sorted_atr = sorted(values)
        rank = sum(1 for a in sorted_atr if a <= current_atr)
        percentile = (rank / len(sorted_atr)) * 100

        # Average over long window if available
        avg_base = [a for a in long_vals if a and a > 0] or values
        avg_atr = sum(avg_base) / len(avg_base) if avg_base else 1.0
        atr_vs_avg = current_atr / avg_atr if avg_atr > 0 else 1.0

        # Classify regime
        if percentile >= self.config["high_vol_percentile"]:
            regime = "high"
        elif percentile <= self.config["low_vol_percentile"]:
            regime = "low"
        else:
            regime = "normal"

        return {"regime": regime, "percentile": percentile, "atr_vs_avg": atr_vs_avg}

    def _determine_market_condition(
        self, trend_info: Dict[str, Any], vol_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine overall market condition."""
        trend = trend_info["trend"]
        strength = trend_info["strength"]
        vol_regime = vol_info["regime"]

        # Score calculation
        score = 0.5  # Baseline

        if trend == "trending":
            score += 0.2 * strength
            if vol_regime == "normal":
                score += 0.1
            elif vol_regime == "high":
                score += 0.05  # High vol can be good for trends but risky

        # Determine condition and environment
        if trend == "trending" and strength >= 0.5:
            condition = "trending_strong"
            environment = "favorable"
        elif trend == "trending":
            condition = "trending_weak"
            environment = "neutral"
        elif vol_regime == "low":
            condition = "ranging_quiet"
            environment = "unfavorable"
        elif vol_regime == "high":
            condition = "ranging_volatile"
            environment = "risky"
        else:
            condition = "ranging_normal"
            environment = "neutral"

        return {
            "condition": condition,
            "score": score,
            "environment": environment,
        }
