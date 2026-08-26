"""
NexQuant SuperBot — TradingStrategy Adaptative & Institutionnelle (MT5)
========================================================================
Adaptateur de haut niveau connectant le StrategyEngine, le MarketRegimeDetector
et la suite des 6 stratégies d'élite à l'orchestrateur.
"""

from typing import Dict, Any, Optional
import pandas as pd
import logging

from superbot.strategy.base_strategy import SignalResult
from superbot.broker.symbol_specs import get_asset_class, get_pip_size, get_active_sessions

log = logging.getLogger("nexquant.trading_strategy")


class TradingStrategy:
    """
    Stratégie de trading unifiée pour MT5 (Matières Premières & Devises).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, db=None, indicators=None, **kwargs):
        from superbot.brain.strategy_engine import StrategyEngine
        from superbot.brain.regime_detector import MarketRegimeDetector

        self.config = config or {}
        self.db = db
        self.indicators = indicators
        self.score_min = int(self.config.get('SCORE_MIN', 6))
        self.risk_per_trade = float(self.config.get('RISK_PCT', 1.0))

        self.regime_detector = MarketRegimeDetector(db=db)
        self.strategy_engine = StrategyEngine(config=self.config, db=db)
        log.info("TradingStrategy MT5 adaptative initialisée avec succès")

    def _calculate_potential_rr(self, latest: pd.Series, current_price: float, sl_atr_mult: float = 1.5, tp_atr_mult: float = 3.0, direction: str = 'long'):
        atr = float(latest.get('atr', 0.0))
        if direction == 'long':
            sl_price = current_price - (sl_atr_mult * atr)
            tp_price = current_price + (tp_atr_mult * atr)
            risk = current_price - sl_price
            reward = tp_price - current_price
        else:
            sl_price = current_price + (sl_atr_mult * atr)
            tp_price = current_price - (tp_atr_mult * atr)
            risk = sl_price - current_price
            reward = current_price - tp_price
            
        rr = reward / risk if risk > 0 else 0.0
        return rr, sl_price, tp_price

    def analyze_market(
        self,
        df: pd.DataFrame,
        account_balance: float = 10000.0,
        real_win_rate: float = 0.5,
        symbol: str = "EURUSD",
        btc_change_24h: Optional[float] = None,
        sentiment_factor: float = 1.0,
        news_filter_passed: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal pour l'analyse de marché sur un symbole.
        """
        if df is None or len(df) < 20:
            return {
                "symbol": symbol,
                "should_long": False,
                "should_short": False,
                "trigger_long": False,
                "trigger_short": False,
                "total_score": 0.0,
                "market_regime": "ranging",
                "strategy_used": "NONE",
                "confidence": 0.0,
                "entry_price": 0.0,
                "sl_price": 0.0,
                "tp_price": 0.0,
                "rr_ratio": 0.0,
                "score_min": self.score_min,
                "reason": "Données insuffisantes",
            }

        last = df.iloc[-1]
        current_price = float(last.get('close', 0.0))
        asset_class = get_asset_class(symbol)
        pip_size = get_pip_size(symbol)
        active_sessions = get_active_sessions()

        # 1. Détection automatique du régime de marché
        regime: RegimeResult = self.regime_detector.detect(
            df=df,
            symbol=symbol,
            asset_class=asset_class,
            store_in_db=bool(self.db is not None)
        )

        # 2. Évaluation des stratégies adaptatives par le moteur
        sig: SignalResult = self.strategy_engine.evaluate(
            df=df,
            symbol=symbol,
            regime=regime,
            asset_class=asset_class,
            current_price=current_price,
            pip_size=pip_size,
            active_sessions=active_sessions
        )

        result_dict = sig.to_dict()
        result_dict["symbol"] = symbol
        result_dict["score_min"] = self.score_min
        result_dict["strategy_used"] = sig.strategy_name
        result_dict["market_regime"] = regime.regime
        result_dict["brain_regime"] = regime.regime
        result_dict["regime_confidence"] = regime.confidence
        result_dict["hurst_exponent"] = regime.hurst_exponent
        result_dict["half_life_bars"] = regime.half_life
        result_dict["active_sessions"] = active_sessions

        return result_dict
