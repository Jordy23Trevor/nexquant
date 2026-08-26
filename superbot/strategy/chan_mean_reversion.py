from __future__ import annotations
r"""
Stratégie 2 : Ernest Chan — Mean Reversion Quantitatif (Ornstein-Uhlenbeck & Hurst)
==================================================================================
Référence : Dr. Ernest P. Chan — *Algorithmic Trading: Winning Strategies and Their Rationale*

Fondements Théoriques :
1. Condition de stationnarité : Exposant de Hurst $H < 0.45$ et ADX < 20 (Régime Ranging).
2. Modélisation OU : $dy_t = \theta (\mu - y_t) dt + \sigma dW_t$.
   La demi-vie $\lambda = -\ln(2)/\beta$ fournit la durée moyenne estimée de retour à l'équilibre.
3. Signal d'entrée :
   - Écart normalisé (Z-Score) par rapport aux Bandes de Bollinger : $Z = (Close - SMA_{20}) / \sigma_{20}$.
   - Achat Long si $Z \le -2.0$ et $RSI \le 35$ (Survente statistique).
   - Vente Short si $Z \ge 2.0$ et $RSI \ge 65$ (Surachat statistique).
4. Objectifs :
   - TP : Retour à la moyenne $SMA_{20}$ (Bande médiane de Bollinger).
   - SL : 2.0 $\times$ ATR au-delà de l'extrême.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
import pandas as pd
import numpy as np

from superbot.strategy.base_strategy import BaseStrategy, SignalResult
if TYPE_CHECKING:
    from superbot.brain.regime_detector import RegimeResult


class ChanMeanReversionStrategy(BaseStrategy):
    """Stratégie quantitative de retour à la moyenne (Ernest Chan)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="CHAN_MEAN_REVERSION", config=config)
        self.zscore_threshold = float(self.config.get("CHAN_ZSCORE_THRESH", 1.8))
        self.sl_atr_mult = float(self.config.get("SL_ATR_MULT", 1.5))

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
        close = current_price if current_price > 0 else float(last['close'])
        atr = float(last.get('atr', 0.0))
        if atr <= 0:
            atr = abs(float(last['high']) - float(last['low']))

        bb_middle = float(last.get('bb_middle', 0.0))
        if bb_middle <= 0:
            bb_middle = float(df['close'].rolling(20).mean().iloc[-1])
            if np.isnan(bb_middle) or bb_middle <= 0:
                return SignalResult(strategy_name=self.name, market_regime=regime.regime)
        
        bb_upper = float(last.get('bb_upper', 0.0))
        bb_lower = float(last.get('bb_lower', 0.0))
        rsi = float(last.get('rsi', 50.0))
        adx = float(last.get('adx', 20.0))
        hurst = float(regime.hurst_exponent)
        half_life = float(regime.half_life)

        # Calcul du Z-Score
        bb_std = (bb_upper - bb_middle) / 2.0 if (bb_upper > bb_middle) else (atr * 0.5)
        zscore = (close - bb_middle) / bb_std if bb_std > 0 else 0.0

        # Conditions d'éligibilité stationnaire (Chan)
        is_mean_reverting_regime = (hurst < 0.50 or adx < 22 or regime.regime in ['ranging', 'choppy_noise', 'pre_breakout', 'high_volatility'])

        trigger_long = False
        trigger_short = False

        if is_mean_reverting_regime:
            # Long si sous la bande inférieure de Bollinger avec RSI bas
            if (zscore <= -self.zscore_threshold or close <= bb_lower) and rsi <= 40:
                trigger_long = True
            # Short si au-dessus de la bande supérieure de Bollinger avec RSI haut
            elif (zscore >= self.zscore_threshold or close >= bb_upper) and rsi >= 60:
                trigger_short = True

        score = 0.0
        if trigger_long:
            score += 4.0
            if hurst < 0.45:
                score += 2.5  # Forte stationnarité prouvée
            if zscore <= -1.8:
                score += 2.0
            if rsi <= 30:
                score += 1.5
        elif trigger_short:
            score += 4.0
            if hurst < 0.45:
                score += 2.5
            if zscore >= 1.8:
                score += 2.0
            if rsi >= 70:
                score += 1.5

        sl_price = 0.0
        tp_price = 0.0
        rr_ratio = 0.0

        if trigger_long:
            tp_price = bb_middle  # Sortie à la moyenne (Mean)
            sl_price = close - (self.sl_atr_mult * atr)
            stop_dist = max(close - sl_price, 1e-5)
            reward_dist = max(tp_price - close, 1e-5)
            rr_ratio = reward_dist / stop_dist

        elif trigger_short:
            tp_price = bb_middle
            sl_price = close + (self.sl_atr_mult * atr)
            stop_dist = max(sl_price - close, 1e-5)
            reward_dist = max(close - tp_price, 1e-5)
            rr_ratio = reward_dist / stop_dist

        return SignalResult(
            should_long=trigger_long and score >= 6.0 and rr_ratio >= 1.2,
            should_short=trigger_short and score >= 6.0 and rr_ratio >= 1.2,
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
            reason=f"Chan Mean Reversion (Z-Score={zscore:.2f}, Hurst={hurst:.2f}, HL={half_life:.1f} bars)",
            extra_data={
                "zscore": round(zscore, 2),
                "hurst": round(hurst, 3),
                "half_life_bars": round(half_life, 1),
                "target_mean": round(bb_middle, 5)
            }
        )
