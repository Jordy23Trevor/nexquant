from __future__ import annotations
"""
Stratégie 4 : Bob Volman — Forex & Commodity Price Action Scalping (21 EMA)
===========================================================================
Référence : Bob Volman — *Forex Price Action Scalping* & *Understanding Price Action*

Principes Clés de Bob Volman :
1. La moyenne mobile 21 EMA sert de support/résistance dynamique institutionnel.
2. Configuration 'Build-Up' : Compression de 3 à 6 bougies directement contre la 21 EMA.
3. Configuration 'Rebond / Pullback 21 EMA' : Test propre de la 21 EMA avec rejet par mèche.
4. Configuration 'Faux Breakout (False Breakout Reversal)' : Fausse cassure de la 21 EMA
   réintégrée violemment.
5. Gestion stricte du risque : Stop très serré derrière la compression (1.0 ATR).
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
import pandas as pd

from superbot.strategy.base_strategy import BaseStrategy, SignalResult
if TYPE_CHECKING:
    from superbot.brain.regime_detector import RegimeResult


class VolmanPriceActionStrategy(BaseStrategy):
    """Stratégie Price Action sur la 21 EMA (Bob Volman)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="VOLMAN_PRICE_ACTION", config=config)
        self.sl_atr_mult = float(self.config.get("SL_ATR_MULT", 1.0))
        self.tp_atr_mult = float(self.config.get("TP_ATR_MULT", 2.2))

    def analyze(
        self,
        df: pd.DataFrame,
        symbol: str,
        regime: RegimeResult,
        asset_class: str,
        current_price: float,
        pip_size: float = 0.0001
    ) -> SignalResult:
        if df is None or len(df) < 25:
            return SignalResult(strategy_name=self.name, market_regime=regime.regime)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]
        close = current_price if current_price > 0 else float(last['close'])
        atr = float(last.get('atr', 0.0))
        if atr <= 0:
            atr = abs(float(last['high']) - float(last['low']))

        ema_21 = float(last.get('ema_21', last.get('ema_fast', 0.0)))
        prev_ema_21 = float(prev.get('ema_21', prev.get('ema_fast', 0.0)))

        # Pente de l'EMA 21
        ema_slope_up = ema_21 > prev_ema_21
        ema_slope_down = ema_21 < prev_ema_21

        # Test des dernières bougies pour détecter le "Build-up" contre l'EMA 21
        recent_bars = df.iloc[-4:]
        max_dist_from_ema = (recent_bars['close'] - ema_21).abs().max()
        is_buildup = max_dist_from_ema < (atr * 0.8)

        # Rejet par mèche (Pullback bounce)
        bullish_bounce = (float(prev['low']) <= ema_21 and float(prev['close']) >= ema_21 and close > float(prev['high']))
        bearish_bounce = (float(prev['high']) >= ema_21 and float(prev['close']) <= ema_21 and close < float(prev['low']))

        # Faux breakout réintégré
        false_breakout_long = (float(prev2['close']) < ema_21 and float(prev['close']) > ema_21 and close > float(prev['high']))
        false_breakout_short = (float(prev2['close']) > ema_21 and float(prev['close']) < ema_21 and close < float(prev['low']))

        trigger_long = False
        trigger_short = False

        if ema_slope_up:
            if (is_buildup and close > float(prev['high'])) or bullish_bounce or false_breakout_long:
                trigger_long = True

        if ema_slope_down:
            if (is_buildup and close < float(prev['low'])) or bearish_bounce or false_breakout_short:
                trigger_short = True

        score = 0.0
        if regime.regime in ['breakout']:
            score += 2.0

        if trigger_long:
            score += 4.0
            if is_buildup:
                score += 2.5
            if false_breakout_long:
                score += 2.0
            if regime.regime in ['trending_bull', 'pre_breakout']:
                score += 1.5
        elif trigger_short:
            score += 4.0
            if is_buildup:
                score += 2.5
            if false_breakout_short:
                score += 2.0
            if regime.regime in ['trending_bear', 'pre_breakout']:
                score += 1.5

        sl_price = 0.0
        tp_price = 0.0
        rr_ratio = 0.0

        if trigger_long:
            sl_price = min(float(prev['low']), ema_21 - 0.3 * atr) if ema_21 > 0 else (close - self.sl_atr_mult * atr)
            sl_price = max(sl_price, close - (self.sl_atr_mult * atr))
            sl_price = min(sl_price, close - 0.5 * atr)
            stop_dist = max(close - sl_price, 1e-5)
            tp_price = close + (stop_dist * (self.tp_atr_mult / self.sl_atr_mult))
            rr_ratio = (tp_price - close) / stop_dist

        elif trigger_short:
            sl_price = max(float(prev['high']), ema_21 + 0.3 * atr) if ema_21 > 0 else (close + self.sl_atr_mult * atr)
            sl_price = min(sl_price, close + (self.sl_atr_mult * atr))
            sl_price = max(sl_price, close + 0.5 * atr)
            stop_dist = max(sl_price - close, 1e-5)
            tp_price = close - (stop_dist * (self.tp_atr_mult / self.sl_atr_mult))
            rr_ratio = (close - tp_price) / stop_dist
            
        else:
            if regime.regime in ['trending_bull', 'pre_breakout', 'breakout']:
                sl_price = min(float(prev['low']), ema_21 - 0.3 * atr) if ema_21 > 0 else (close - self.sl_atr_mult * atr)
                sl_price = max(sl_price, close - (self.sl_atr_mult * atr))
                sl_price = min(sl_price, close - 0.5 * atr)
                stop_dist = max(close - sl_price, 1e-5)
                tp_price = close + (stop_dist * (self.tp_atr_mult / self.sl_atr_mult))
                rr_ratio = (tp_price - close) / stop_dist
            elif regime.regime in ['trending_bear']:
                sl_price = max(float(prev['high']), ema_21 + 0.3 * atr) if ema_21 > 0 else (close + self.sl_atr_mult * atr)
                sl_price = min(sl_price, close + (self.sl_atr_mult * atr))
                sl_price = max(sl_price, close + 0.5 * atr)
                stop_dist = max(sl_price - close, 1e-5)
                tp_price = close - (stop_dist * (self.tp_atr_mult / self.sl_atr_mult))
                rr_ratio = (close - tp_price) / stop_dist

        return SignalResult(
            should_long=trigger_long and score >= 6.0 and rr_ratio >= 1.5,
            should_short=trigger_short and score >= 6.0 and rr_ratio >= 1.5,
            trigger_long=trigger_long,
            trigger_short=trigger_short,
            total_score=score,
            strategy_name=self.name,
            market_regime=regime.regime,
            confidence=regime.confidence if (trigger_long or trigger_short) else 0.0,
            entry_price=close,
            sl_price=sl_price,
            tp_price=tp_price,
            rr_ratio=rr_ratio,
            reason=f"Volman 21 EMA Price Action (Buildup={is_buildup}, Bounce={bullish_bounce or bearish_bounce})",
            extra_data={
                "is_buildup": is_buildup,
                "ema_21": ema_21
            }
        )
