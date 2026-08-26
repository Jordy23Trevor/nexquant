"""
NexQuant SuperBot — Strategy Engine Institutionnel & Adaptatif (Forex & Commodities)
=====================================================================================
Orchestration dynamique des 6 stratégies adaptatives de haut niveau :
1. ELDER_TRIPLE_SCREEN     : Système Triple Écran + Impulsion (Dr. Alexander Elder)
2. CHAN_MEAN_REVERSION     : Retour à la moyenne quantitatif OU + Hurst (Dr. Ernest Chan)
3. MURPHY_TREND            : Suivi de tendance multitemporel + Donchian (John J. Murphy)
4. VOLMAN_PRICE_ACTION     : Scalping Price Action 21 EMA & Buildups (Bob Volman)
5. LONDON_BREAKOUT         : Cassure de la boîte asiatique à l'ouverture de Londres
6. INTERMARKET_MOMENTUM    : Consensus de momentum multi-horizons (TSMOM / Murphy)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd

from superbot.strategy.base_strategy import BaseStrategy, SignalResult
from superbot.strategy.elder_triple_screen import ElderTripleScreenStrategy
from superbot.strategy.chan_mean_reversion import ChanMeanReversionStrategy
from superbot.strategy.murphy_trend import MurphyTrendStrategy
from superbot.strategy.volman_price_action import VolmanPriceActionStrategy
from superbot.strategy.london_breakout import LondonBreakoutStrategy
from superbot.strategy.intermarket_momentum import IntermarketMomentumStrategy
from superbot.brain.regime_detector import RegimeResult

log = logging.getLogger("nexquant.strategy_engine")


class StrategyEngine:
    """
    Moteur de sélection dynamique et exécution des stratégies.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, db=None, session_manager=None, **kwargs):
        self.config = config or {}
        self.db = db
        self.session_manager = session_manager

        # Instanciation de la suite des 6 stratégies
        self.strategies: Dict[str, BaseStrategy] = {
            "ELDER_TRIPLE_SCREEN": ElderTripleScreenStrategy(self.config),
            "CHAN_MEAN_REVERSION": ChanMeanReversionStrategy(self.config),
            "MURPHY_TREND": MurphyTrendStrategy(self.config),
            "VOLMAN_PRICE_ACTION": VolmanPriceActionStrategy(self.config),
            "LONDON_BREAKOUT": LondonBreakoutStrategy(self.config),
            "INTERMARKET_MOMENTUM": IntermarketMomentumStrategy(self.config),
        }
        log.info("StrategyEngine MT5 initialisé avec 6 stratégies d'élite")

    def select_best_strategy(self, regime: str, session_name: Optional[str] = None, **kwargs) -> Tuple[str, float]:
        """Sélectionne le nom de la meilleure stratégie pour un régime et une session donnés."""
        candidates = self._get_candidate_strategies(regime, [session_name] if session_name else ["LONDON"])
        if not candidates:
            return ('MURPHY_TREND', 0.5)
        return (candidates[0], 1.0)

    def evaluate(
        self,
        df: pd.DataFrame,
        symbol: str,
        regime: RegimeResult,
        asset_class: str = "forex",
        current_price: float = 0.0,
        pip_size: float = 0.0001,
        active_sessions: Optional[List[str]] = None
    ) -> SignalResult:
        """
        Évalue les données de marché avec la ou les stratégies les plus pertinentes
        selon le régime de marché et la session active.
        """
        if df is None or len(df) < 20:
            return SignalResult(
                strategy_name="NONE",
                market_regime=regime.regime,
                reason="Données insuffisantes"
            )

        active_sessions = active_sessions or ["LONDON"]
        regime_type = regime.regime

        # Déterminer la liste ordonnée des stratégies candidates selon le régime
        candidates: List[str] = self._get_candidate_strategies(regime_type, active_sessions)

        best_signal: Optional[SignalResult] = None
        highest_score = -1.0

        for strat_name in candidates:
            strat = self.strategies.get(strat_name)
            if not strat:
                continue

            try:
                sig = strat.analyze(
                    df=df,
                    symbol=symbol,
                    regime=regime,
                    asset_class=asset_class,
                    current_price=current_price,
                    pip_size=pip_size
                )

                # Vérifier si un signal valide d'entrée est généré
                if (sig.should_long or sig.should_short) and sig.total_score > highest_score:
                    highest_score = sig.total_score
                    best_signal = sig

            except Exception as e:
                log.debug(f"Erreur d'analyse stratégie {strat_name} ({symbol}): {e}")

        # Si aucune stratégie ne déclenche avec 'should_long/should_short', on prend la première candidate par défaut
        if best_signal is None:
            if not candidates:
                first_strat = self.strategies["MURPHY_TREND"]
            else:
                first_strat = self.strategies.get(candidates[0], self.strategies["MURPHY_TREND"])
            best_signal = first_strat.analyze(
                df=df,
                symbol=symbol,
                regime=regime,
                asset_class=asset_class,
                current_price=current_price,
                pip_size=pip_size
            )

        return best_signal

    def _get_candidate_strategies(self, regime_type: str, active_sessions: List[str]) -> List[str]:
        """
        Sélectionne les stratégies prioritaires selon le régime et la session.
        """
        candidates: List[str] = []

        # 1. Régimes de Tendance forte (Bullish / Bearish)
        if regime_type in ["trending_bull", "trending_bear"]:
            candidates = [
                "ELDER_TRIPLE_SCREEN",
                "MURPHY_TREND",
                "INTERMARKET_MOMENTUM",
                "VOLMAN_PRICE_ACTION"
            ]

        # 2. Régimes de Range / Oscillations
        elif regime_type in ["ranging", "choppy_noise"]:
            candidates = [
                "CHAN_MEAN_REVERSION",
                "VOLMAN_PRICE_ACTION"
            ]

        # 3. Régimes de Compression / Breakout
        elif regime_type in ["pre_breakout", "breakout"]:
            if "LONDON" in active_sessions or "OVERLAP" in active_sessions:
                candidates = [
                    "LONDON_BREAKOUT",
                    "VOLMAN_PRICE_ACTION",
                    "MURPHY_TREND"
                ]
            else:
                candidates = [
                    "VOLMAN_PRICE_ACTION",
                    "MURPHY_TREND",
                    "CHAN_MEAN_REVERSION"
                ]

        # 4. Haute volatilité
        elif regime_type == "high_volatility":
            candidates = [
                "CHAN_MEAN_REVERSION",
                "INTERMARKET_MOMENTUM",
                "ELDER_TRIPLE_SCREEN"
            ]

        else:
            candidates = [
                "MURPHY_TREND",
                "ELDER_TRIPLE_SCREEN",
                "CHAN_MEAN_REVERSION"
            ]

        return candidates

    def get_strategy_leaderboard(self) -> list:
        return sorted(
            [{'name': name, 'trades': 0, 'win_rate': 0.0, 'pnl': 0.0}
             for name in self.strategies],
            key=lambda x: x.get('pnl', 0), reverse=True
        )

