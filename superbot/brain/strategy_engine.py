"""
NexQuant V3 — Strategy Engine Dynamique
==========================================
Phase 4 : 12 stratégies adaptées dynamiquement au régime de marché.

Architecture :
  - StrategyEngine sélectionne la meilleure stratégie selon :
    1. Régime de marché (trend/range/volatile/breakout)
    2. Session active (London/NY/Asia)
    3. Performances historiques par stratégie/symbole
    4. Données de sentiment (Fear&Greed, news)
  
  - 12 stratégies implémentées :
    1. TREND_FOLLOW_EMA     : Suivi de tendance EMA croisées
    2. BREAKOUT_ATR         : Cassure de range + ATR
    3. SCALP_MOMENTUM       : Scalping momentum RSI+MACD
    4. REVERSAL_RSI         : Retournement sur zones extrêmes RSI
    5. ICHIMOKU_CLOUD       : Cloud Ichimoku complet
    6. SUPERTREND_ADX       : Supertrend + filtre ADX
    7. BB_SQUEEZE           : Bollinger Squeeze breakout
    8. VWAP_MEAN_REVERT     : Retour vers VWAP intraday
    9. SESSION_OPEN_GAP     : Gaps à l'ouverture de session
    10. CARRY_TRADE         : Positions de carry (différentiel de taux)
    11. CRYPTO_FUNDING      : Stratégie funding rates crypto (MT5 CFD)
    12. MACRO_EVENT         : Avant/après événements macro majeurs (NFP, CPI)

Chaque stratégie retourne :
  {
    'should_long': bool,
    'should_short': bool,
    'trigger_long': bool,
    'trigger_short': bool,
    'total_score': float (0-10),
    'market_regime': str,
    'strategy_used': str,
    'confidence': float (0-1),
    'rr_ratio': float,
    'score_min': int,
    ...
  }
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

log = logging.getLogger("nexquant.strategy_engine")

# ═══════════════════════════════════════════════════════════════════════════════
# DÉFINITION DES STRATÉGIES
# ═══════════════════════════════════════════════════════════════════════════════

STRATEGY_REGISTRY = {
    "TREND_FOLLOW_EMA": {
        "description": "Suivi de tendance via croisement EMA court/long + filtre ADX",
        "best_regime": ["trending_bull", "trending_bear"],
        "best_sessions": ["LONDON", "OVERLAP", "NEW_YORK"],
        "best_assets": ["forex", "crypto"],
        "risk_profile": "moderate",
        "min_adx": 22,
    },
    "BREAKOUT_ATR": {
        "description": "Cassure de range avec confirmation ATR (volatilité)",
        "best_regime": ["breakout", "trending_bull", "trending_bear"],
        "best_sessions": ["LONDON", "OVERLAP"],
        "best_assets": ["forex", "crypto"],
        "risk_profile": "moderate",
        "min_adx": 18,
    },
    "SCALP_MOMENTUM": {
        "description": "Scalping momentum court terme RSI+MACD (timeframe court)",
        "best_regime": ["trending_bull", "trending_bear"],
        "best_sessions": ["OVERLAP", "NEW_YORK"],
        "best_assets": ["forex", "crypto"],
        "risk_profile": "aggressive",
        "min_adx": 20,
    },
    "REVERSAL_RSI": {
        "description": "Retournement sur RSI extrême (<25 oversold, >75 overbought)",
        "best_regime": ["ranging", "high_volatility"],
        "best_sessions": ["LONDON", "NEW_YORK", "ASIA"],
        "best_assets": ["forex", "commodity"],
        "risk_profile": "conservative",
        "min_adx": 0,
    },
    "ICHIMOKU_CLOUD": {
        "description": "Ichimoku complet : Cloud + TK cross + Chikou confirmation",
        "best_regime": ["trending_bull", "trending_bear", "breakout"],
        "best_sessions": ["LONDON", "OVERLAP"],
        "best_assets": ["forex", "crypto"],
        "risk_profile": "moderate",
        "min_adx": 15,
    },
    "SUPERTREND_ADX": {
        "description": "Supertrend avec filtre ADX fort (> 25)",
        "best_regime": ["trending_bull", "trending_bear"],
        "best_sessions": ["LONDON", "OVERLAP", "NEW_YORK"],
        "best_assets": ["forex", "crypto", "commodity"],
        "risk_profile": "moderate",
        "min_adx": 25,
    },
    "BB_SQUEEZE": {
        "description": "Bollinger Bands Squeeze : compression puis expansion explosive",
        "best_regime": ["breakout", "pre_breakout"],
        "best_sessions": ["LONDON", "NEW_YORK"],
        "best_assets": ["forex", "crypto"],
        "risk_profile": "aggressive",
        "min_adx": 0,
    },
    "VWAP_MEAN_REVERT": {
        "description": "Mean reversion vers VWAP intraday (sur-extension puis retour)",
        "best_regime": ["ranging", "mean_reverting"],
        "best_sessions": ["LONDON", "OVERLAP", "NEW_YORK"],
        "best_assets": ["forex", "crypto"],
        "risk_profile": "moderate",
        "min_adx": 0,
    },
    "SESSION_OPEN_GAP": {
        "description": "Gaps / momentum à l'ouverture des sessions London et NY",
        "best_regime": ["breakout", "trending_bull", "trending_bear"],
        "best_sessions": ["PRE_LONDON", "LONDON"],
        "best_assets": ["forex"],
        "risk_profile": "aggressive",
        "min_adx": 0,
    },
    "CARRY_TRADE": {
        "description": "Carry trade : vendre low-yield / acheter high-yield (USDJPY, AUDUSD)",
        "best_regime": ["trending_bull", "ranging"],
        "best_sessions": ["ASIA", "LONDON"],
        "best_assets": ["forex"],
        "risk_profile": "conservative",
        "min_adx": 10,
    },
    "CRYPTO_MOMENTUM": {
        "description": "Momentum crypto basé sur BTC dominance + Fear&Greed + volume",
        "best_regime": ["trending_bull", "trending_bear", "breakout"],
        "best_sessions": ["OVERLAP", "NEW_YORK", "ASIA"],
        "best_assets": ["crypto"],
        "risk_profile": "aggressive",
        "min_adx": 20,
    },
    "MACRO_EVENT": {
        "description": "Trading autour des événements macro (NFP, CPI, Fed) — fade ou follow",
        "best_regime": ["high_volatility", "breakout"],
        "best_sessions": ["NEW_YORK", "OVERLAP"],
        "best_assets": ["forex", "crypto"],
        "risk_profile": "aggressive",
        "min_adx": 0,
    },
}


class StrategyEngine:
    """
    Moteur de sélection dynamique de stratégie.
    
    À chaque analyse, sélectionne automatiquement la stratégie
    la plus adaptée au régime de marché, à la session et à l'historique.
    
    Intégration avec la stratégie existante (TradingStrategy) :
    - Ajoute une couche de sélection intelligente
    - Enrichit le signal_data avec 'strategy_used' et 'confidence'
    - Stocke les résultats dans la DB pour l'apprentissage
    """

    def __init__(self, db=None, session_manager=None):
        self._db = db
        self._session_manager = session_manager
        self._lock = __import__('threading').RLock()

        # Performance par stratégie (win_rate, avg_rr)
        self._strategy_perf: Dict[str, Dict] = {name: {'wins': 0, 'total': 0, 'avg_rr': 2.0}
                                                  for name in STRATEGY_REGISTRY}

        # Cooldown par stratégie/symbole pour éviter la sur-utilisation
        self._strategy_cooldowns: Dict[str, float] = {}

        log.info(f"StrategyEngine V3 initialisé | {len(STRATEGY_REGISTRY)} stratégies disponibles")

    def select_best_strategy(
        self,
        regime: str,
        session_name: str,
        asset_class: str,
        symbol: str,
        adx_value: float = 0,
        sentiment: Dict = None
    ) -> Tuple[str, float]:
        """
        Sélectionne la meilleure stratégie selon le contexte.
        
        Returns:
            (strategy_name, confidence_score)
        """
        scores: Dict[str, float] = {}
        import time as _time

        for name, meta in STRATEGY_REGISTRY.items():
            score = 0.0

            # 1. Score régime de marché (0-40 pts)
            if regime in meta['best_regime']:
                score += 40
            elif any(r.startswith(regime[:5]) for r in meta['best_regime']):
                score += 20

            # 2. Score session (0-25 pts)
            if session_name in meta['best_sessions']:
                score += 25
            elif session_name == 'PRE_LONDON' and 'LONDON' in meta['best_sessions']:
                score += 10

            # 3. Score asset class (0-20 pts)
            if asset_class in meta['best_assets']:
                score += 20

            # 4. Score ADX (0-10 pts)
            min_adx = meta.get('min_adx', 0)
            if adx_value >= min_adx:
                score += 10 * min(1.0, (adx_value - min_adx) / max(1, 30 - min_adx))

            # 5. Score performance historique (0-15 pts)
            perf = self._strategy_perf.get(name, {})
            total = perf.get('total', 0)
            if total >= 5:
                wr = perf.get('wins', 0) / total
                score += 15 * wr

            # 6. Pénalité cooldown
            cooldown_key = f"{name}_{symbol}"
            last_used = self._strategy_cooldowns.get(cooldown_key, 0)
            elapsed = _time.time() - last_used
            if elapsed < 3600:  # Cooldown 1h
                score *= 0.7  # -30% si utilisée récemment

            scores[name] = score

        if not scores:
            return "TREND_FOLLOW_EMA", 0.5

        # Sélectionner la meilleure
        best_name = max(scores, key=lambda k: scores[k])
        best_score = scores[best_name]
        max_possible = 110  # 40 + 25 + 20 + 10 + 15
        confidence = min(1.0, best_score / max_possible)

        return best_name, confidence

    def compute_strategy_score(
        self,
        strategy_name: str,
        df,
        config: Dict,
        asset_class: str = 'forex',
        sentiment_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calcule le score de signal pour une stratégie donnée.
        
        Enrichit le signal standard avec :
        - strategy_used : nom de la stratégie
        - confidence : score de confiance
        - score_bonus : bonus de score selon la stratégie
        
        Le signal est ensuite passé à TradingStrategy.analyze_market()
        qui applique tous les filtres standard.
        """
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else last

            result = {
                'strategy_used': strategy_name,
                'confidence': 0.5,
                'score_bonus': 0.0,
                'additional_filters_passed': True,
                'strategy_meta': STRATEGY_REGISTRY.get(strategy_name, {}),
            }

            # Scores additionnels selon la stratégie
            if strategy_name == "TREND_FOLLOW_EMA":
                result.update(self._score_trend_ema(last, prev, config))
            elif strategy_name == "BREAKOUT_ATR":
                result.update(self._score_breakout_atr(df, last, config))
            elif strategy_name == "SCALP_MOMENTUM":
                result.update(self._score_scalp_momentum(last, prev, config))
            elif strategy_name == "REVERSAL_RSI":
                result.update(self._score_reversal_rsi(last, prev, config))
            elif strategy_name == "ICHIMOKU_CLOUD":
                result.update(self._score_ichimoku(last, prev, config))
            elif strategy_name == "SUPERTREND_ADX":
                result.update(self._score_supertrend_adx(last, prev, config))
            elif strategy_name == "BB_SQUEEZE":
                result.update(self._score_bb_squeeze(df, last, config))
            elif strategy_name == "VWAP_MEAN_REVERT":
                result.update(self._score_vwap_mean_revert(last, prev, config))
            elif strategy_name == "CRYPTO_MOMENTUM":
                result.update(self._score_crypto_momentum(last, prev, config, sentiment_factor))
            elif strategy_name == "MACRO_EVENT":
                result.update(self._score_macro_event(last, config, sentiment_factor))
            else:
                # Stratégies non implémentées : retour neutre
                result['score_bonus'] = 0.0
                result['additional_filters_passed'] = True

            return result

        except Exception as e:
            log.debug(f"StrategyEngine score error ({strategy_name}): {e}")
            return {
                'strategy_used': strategy_name,
                'confidence': 0.4,
                'score_bonus': 0.0,
                'additional_filters_passed': True,
            }

    def _get_col(self, row, *names, default=0.0):
        """Récupère une colonne avec plusieurs noms alternatifs."""
        for name in names:
            v = row.get(name) if hasattr(row, 'get') else getattr(row, name, None)
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                return float(v)
        return default

    # ─────────────────────────────────────────────────────────────────────────
    # IMPLÉMENTATIONS DES STRATÉGIES
    # ─────────────────────────────────────────────────────────────────────────

    def _score_trend_ema(self, last, prev, config) -> Dict:
        """TREND_FOLLOW_EMA : EMA cross + ADX + Supertrend."""
        ema_fast = self._get_col(last, 'ema_fast', 'ema_9', 'ema_14')
        ema_slow = self._get_col(last, 'ema_slow', 'ema_21', 'ema_50')
        adx = self._get_col(last, 'adx', default=0)
        supertrend_dir = self._get_col(last, 'supertrend_direction', 'st_dir', default=0)

        bonus = 0.0
        if ema_fast > ema_slow and adx > 22:
            bonus += 1.5  # Tendance haussière confirmée ADX
        elif ema_fast < ema_slow and adx > 22:
            bonus -= 1.5  # Tendance baissière

        if supertrend_dir > 0:
            bonus += 0.5
        elif supertrend_dir < 0:
            bonus -= 0.5

        return {'score_bonus': bonus, 'additional_filters_passed': adx > 18}

    def _score_breakout_atr(self, df, last, config) -> Dict:
        """BREAKOUT_ATR : Cassure de la range des 20 dernières bougies."""
        atr = self._get_col(last, 'atr', default=0)
        close = self._get_col(last, 'close')
        if len(df) >= 20:
            high_20 = df['high'].iloc[-20:].max()
            low_20 = df['low'].iloc[-20:].min()
            range_pct = (high_20 - low_20) / low_20 * 100 if low_20 > 0 else 0
            if close > high_20 * 1.001:  # Cassure à la hausse (>0.1%)
                return {'score_bonus': 2.0, 'additional_filters_passed': True, 'breakout_dir': 'UP'}
            elif close < low_20 * 0.999:  # Cassure à la baisse
                return {'score_bonus': -2.0, 'additional_filters_passed': True, 'breakout_dir': 'DOWN'}
        return {'score_bonus': 0.0, 'additional_filters_passed': True}

    def _score_scalp_momentum(self, last, prev, config) -> Dict:
        """SCALP_MOMENTUM : RSI momentum + MACD histogramme croissant."""
        rsi = self._get_col(last, 'rsi', default=50)
        rsi_prev = self._get_col(prev, 'rsi', default=50)
        macd_hist = self._get_col(last, 'macd_histogram', 'macd_hist', default=0)
        macd_hist_prev = self._get_col(prev, 'macd_histogram', 'macd_hist', default=0)

        bonus = 0.0
        # RSI en zone de momentum (pas extrême)
        if 50 < rsi < 70 and rsi > rsi_prev:
            bonus += 1.5  # Momentum haussier
        elif 30 < rsi < 50 and rsi < rsi_prev:
            bonus -= 1.5  # Momentum baissier

        # MACD histogramme croissant
        if macd_hist > macd_hist_prev and macd_hist > 0:
            bonus += 0.5
        elif macd_hist < macd_hist_prev and macd_hist < 0:
            bonus -= 0.5

        return {'score_bonus': bonus, 'additional_filters_passed': True}

    def _score_reversal_rsi(self, last, prev, config) -> Dict:
        """REVERSAL_RSI : Retournement sur RSI extrême avec divergence."""
        rsi = self._get_col(last, 'rsi', default=50)
        rsi_prev = self._get_col(prev, 'rsi', default=50)

        if rsi < 25 and rsi > rsi_prev:  # Survente + retournement
            return {'score_bonus': 2.5, 'additional_filters_passed': True}
        elif rsi > 75 and rsi < rsi_prev:  # Surachat + retournement
            return {'score_bonus': -2.5, 'additional_filters_passed': True}
        elif rsi < 30:
            return {'score_bonus': 1.0, 'additional_filters_passed': True}
        elif rsi > 70:
            return {'score_bonus': -1.0, 'additional_filters_passed': True}
        return {'score_bonus': 0.0, 'additional_filters_passed': False}

    def _score_ichimoku(self, last, prev, config) -> Dict:
        """ICHIMOKU_CLOUD : Signal complet Ichimoku."""
        tenkan = self._get_col(last, 'ichimoku_tenkan', 'tenkan', default=0)
        kijun = self._get_col(last, 'ichimoku_kijun', 'kijun', default=0)
        span_a = self._get_col(last, 'ichimoku_span_a', 'span_a', default=0)
        span_b = self._get_col(last, 'ichimoku_span_b', 'span_b', default=0)
        close = self._get_col(last, 'close', default=0)

        bonus = 0.0
        # TK Cross haussier
        if tenkan > kijun:
            bonus += 1.0
        elif tenkan < kijun:
            bonus -= 1.0

        # Prix au-dessus/en dessous du cloud
        cloud_top = max(span_a, span_b) if span_a and span_b else 0
        cloud_bot = min(span_a, span_b) if span_a and span_b else 0
        if cloud_top > 0 and close > cloud_top:
            bonus += 1.5  # Au-dessus du cloud = bullish
        elif cloud_bot > 0 and close < cloud_bot:
            bonus -= 1.5  # En dessous = bearish

        return {'score_bonus': bonus, 'additional_filters_passed': True}

    def _score_supertrend_adx(self, last, prev, config) -> Dict:
        """SUPERTREND_ADX : Supertrend avec ADX fort."""
        supertrend = self._get_col(last, 'supertrend', 'st', default=0)
        close = self._get_col(last, 'close', default=0)
        adx = self._get_col(last, 'adx', default=0)
        st_dir = self._get_col(last, 'supertrend_direction', 'st_dir', default=0)

        if adx < 25:
            return {'score_bonus': 0.0, 'additional_filters_passed': False}

        bonus = 0.0
        if st_dir > 0:  # Supertrend haussier
            bonus = 2.0 * min(1.0, adx / 40)
        elif st_dir < 0:  # Bearish
            bonus = -2.0 * min(1.0, adx / 40)

        return {'score_bonus': bonus, 'additional_filters_passed': adx >= 25}

    def _score_bb_squeeze(self, df, last, config) -> Dict:
        """BB_SQUEEZE : Compression des Bandes de Bollinger avant explosion."""
        bb_upper = self._get_col(last, 'bb_upper', 'bollinger_upper', default=0)
        bb_lower = self._get_col(last, 'bb_lower', 'bollinger_lower', default=0)
        close = self._get_col(last, 'close', default=0)

        if bb_upper <= bb_lower or close <= 0:
            return {'score_bonus': 0.0, 'additional_filters_passed': False}

        bb_width = (bb_upper - bb_lower) / close * 100  # En % du prix

        # Squeeze : largeur < 2% = compression forte
        if bb_width < 2.0:
            if close > (bb_upper + bb_lower) / 2:
                return {'score_bonus': 1.5, 'additional_filters_passed': True}
            else:
                return {'score_bonus': -1.5, 'additional_filters_passed': True}
        # Expansion : signal de cassure
        elif bb_width > 4.0 and close > bb_upper:
            return {'score_bonus': 2.0, 'additional_filters_passed': True}
        elif bb_width > 4.0 and close < bb_lower:
            return {'score_bonus': -2.0, 'additional_filters_passed': True}

        return {'score_bonus': 0.0, 'additional_filters_passed': False}

    def _score_vwap_mean_revert(self, last, prev, config) -> Dict:
        """VWAP_MEAN_REVERT : Retour vers VWAP après sur-extension."""
        vwap = self._get_col(last, 'vwap', default=0)
        close = self._get_col(last, 'close', default=0)

        if vwap <= 0 or close <= 0:
            return {'score_bonus': 0.0, 'additional_filters_passed': False}

        deviation_pct = (close - vwap) / vwap * 100

        # Sur-vendu sous VWAP → achat
        if deviation_pct < -0.5:
            return {'score_bonus': min(2.0, abs(deviation_pct)), 'additional_filters_passed': True}
        # Sur-acheté au-dessus VWAP → vente
        elif deviation_pct > 0.5:
            return {'score_bonus': -min(2.0, deviation_pct), 'additional_filters_passed': True}

        return {'score_bonus': 0.0, 'additional_filters_passed': False}

    def _score_crypto_momentum(self, last, prev, config, sentiment_factor: float = 1.0) -> Dict:
        """CRYPTO_MOMENTUM : Volume + momentum + sentiment."""
        rsi = self._get_col(last, 'rsi', default=50)
        volume = self._get_col(last, 'volume', default=0)
        volume_prev = self._get_col(prev, 'volume', default=1)
        adx = self._get_col(last, 'adx', default=0)

        volume_ratio = volume / max(volume_prev, 1)
        bonus = 0.0

        # Volume spike (> 1.5x la moyenne)
        if volume_ratio > 1.5:
            if rsi > 55:  # Momentum haussier + volume
                bonus += 1.5 * sentiment_factor
            elif rsi < 45:  # Momentum baissier + volume
                bonus -= 1.5 * sentiment_factor

        # ADX confirme la tendance
        if adx > 25:
            bonus *= 1.2

        return {'score_bonus': round(bonus, 2), 'additional_filters_passed': adx > 15 or volume_ratio > 1.2}

    def _score_macro_event(self, last, config, sentiment_factor: float = 1.0) -> Dict:
        """MACRO_EVENT : Signal fort basé sur le sentiment/news."""
        # Si sentiment très bullish ou bearish → signal
        if sentiment_factor > 1.2:
            return {'score_bonus': 1.5, 'additional_filters_passed': True}
        elif sentiment_factor < 0.8:
            return {'score_bonus': -1.5, 'additional_filters_passed': True}
        return {'score_bonus': 0.0, 'additional_filters_passed': False}

    # ─────────────────────────────────────────────────────────────────────────
    # APPRENTISSAGE
    # ─────────────────────────────────────────────────────────────────────────

    def record_trade_result(self, strategy_name: str, symbol: str, pnl: float, rr_ratio: float = 0):
        """Met à jour les statistiques de performance par stratégie."""
        with self._lock:
            if strategy_name not in self._strategy_perf:
                self._strategy_perf[strategy_name] = {'wins': 0, 'total': 0, 'avg_rr': 2.0}

            perf = self._strategy_perf[strategy_name]
            perf['total'] += 1
            if pnl > 0:
                perf['wins'] += 1
            # Mise à jour avg_rr (EMA pour être réactif)
            alpha = 0.1
            perf['avg_rr'] = (1 - alpha) * perf['avg_rr'] + alpha * rr_ratio

        # Log toutes les 10 trades
        perf = self._strategy_perf.get(strategy_name, {})
        total = perf.get('total', 0)
        if total % 10 == 0 and total > 0:
            wr = perf.get('wins', 0) / total * 100
            log.info(f"📊 Stratégie {strategy_name} : {total} trades | WR={wr:.0f}% | avg_RR={perf.get('avg_rr', 0):.2f}")

    def get_strategy_leaderboard(self) -> List[Dict]:
        """Retourne le classement des stratégies par performance."""
        leaderboard = []
        for name, perf in self._strategy_perf.items():
            total = perf.get('total', 0)
            wins = perf.get('wins', 0)
            wr = (wins / total * 100) if total > 0 else 0
            leaderboard.append({
                'strategy': name,
                'total_trades': total,
                'win_rate': round(wr, 1),
                'avg_rr': round(perf.get('avg_rr', 0), 2),
                'description': STRATEGY_REGISTRY.get(name, {}).get('description', ''),
            })
        leaderboard.sort(key=lambda x: (x['total_trades'] > 0, x['win_rate']), reverse=True)
        return leaderboard
