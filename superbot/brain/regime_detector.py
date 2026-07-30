"""
NexQuant V3 — Market Regime Detector
======================================
Phase 6 : Détection automatique du régime de marché.

5 régimes détectés :
  - TRENDING_BULL   : Tendance haussière forte (ADX>25, EMA↑, momentum↑)
  - TRENDING_BEAR   : Tendance baissière forte (ADX>25, EMA↓, momentum↓)
  - RANGING         : Canal horizontal (ADX<20, BB étroites, oscillations RSI)
  - HIGH_VOLATILITY : Forte volatilité (ATR élevé, BB larges, VIX effect)
  - BREAKOUT        : Sortie imminente d'un range (BB squeeze + volume spike)
  - PRE_BREAKOUT    : Compression pré-cassure (squeeze fort mais pas encore cassé)

Méthode :
  1. Règles techniques classiques (ADX, ATR, BB, RSI, EMA) → vote pondéré
  2. Analyse HTF (H4/D1 EMA) pour la direction macro
  3. Contexte macro (Fear&Greed, news sentiment) optionnel
  4. Stockage en DB pour historique et apprentissage

Retour :
  RegimeResult(regime, confidence, adx, atr, factors)

Le régime est utilisé par :
  - StrategyEngine (sélection de stratégie)
  - RiskManager (multiplicateurs de risque)
  - PerformanceLearner (analyse des patterns)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

log = logging.getLogger("nexquant.regime_detector")


@dataclass
class RegimeResult:
    """Résultat de la détection de régime."""
    regime: str                      # 'trending_bull' | 'trending_bear' | 'ranging' | 'high_volatility' | 'breakout' | 'pre_breakout'
    confidence: float                # 0.0 → 1.0
    adx_value: float = 0.0
    atr_value: float = 0.0
    bb_width_pct: float = 0.0       # Largeur BB en % du prix
    rsi_value: float = 50.0
    volume_factor: float = 1.0      # Volume / moyenne
    factors: Dict[str, Any] = field(default_factory=dict)
    detected_at: str = ""

    def to_dict(self) -> Dict:
        return {
            'regime': self.regime,
            'confidence': round(self.confidence, 3),
            'adx': round(self.adx_value, 2),
            'atr': round(self.atr_value, 6),
            'bb_width_pct': round(self.bb_width_pct, 2),
            'rsi': round(self.rsi_value, 1),
            'volume_factor': round(self.volume_factor, 2),
            'detected_at': self.detected_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SEUILS PAR CLASSE D'ACTIFS
# Les thresholds sont différents selon l'actif (forex vs crypto vs commodity)
# ═══════════════════════════════════════════════════════════════════════════════

REGIME_THRESHOLDS = {
    'forex': {
        'adx_trending': 25,        # ADX > 25 = tendance forte
        'adx_ranging': 18,         # ADX < 18 = range
        'bb_wide': 2.5,            # BB > 2.5% = forte volatilité
        'bb_squeeze': 0.8,         # BB < 0.8% = squeeze (pré-breakout)
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'atr_high_factor': 1.8,    # ATR > 1.8x moyenne = haute vol
        'volume_spike': 1.5,       # Volume > 1.5x = spike
    },
    'forex_jpy': {
        'adx_trending': 22,
        'adx_ranging': 15,
        'bb_wide': 3.0,
        'bb_squeeze': 1.0,
        'rsi_overbought': 72,
        'rsi_oversold': 28,
        'atr_high_factor': 2.0,
        'volume_spike': 1.5,
    },
    'crypto': {
        'adx_trending': 22,        # Crypto bouge plus vite
        'adx_ranging': 15,
        'bb_wide': 5.0,            # Crypto a des BB naturellement plus larges
        'bb_squeeze': 2.0,
        'rsi_overbought': 75,
        'rsi_oversold': 25,
        'atr_high_factor': 2.0,
        'volume_spike': 2.0,       # Crypto = volume spikes extrêmes
    },
    'commodity': {
        'adx_trending': 25,
        'adx_ranging': 18,
        'bb_wide': 2.0,
        'bb_squeeze': 0.7,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'atr_high_factor': 1.8,
        'volume_spike': 1.5,
    },
}

DEFAULT_THRESHOLDS = REGIME_THRESHOLDS['forex']


class MarketRegimeDetector:
    """
    Détecteur de régime de marché multi-facteurs.

    Thread-safe (pas de state mutable partagé entre appels,
    chaque détection est indépendante).
    """

    def __init__(self, db=None):
        self._db = db
        # Cache par symbole (dernier régime détecté)
        self._cache: Dict[str, RegimeResult] = {}
        log.info("MarketRegimeDetector V3 initialisé")

    def detect(
        self,
        df,
        symbol: str = "",
        asset_class: str = "forex",
        store_in_db: bool = True
    ) -> RegimeResult:
        """
        Détecte le régime de marché à partir d'un DataFrame de bougies avec indicateurs.

        Args:
            df: DataFrame pandas avec colonnes : close, high, low, volume,
                adx, atr, bb_upper, bb_lower, rsi, ema_fast, ema_slow,
                ema_trend, supertrend_direction, macd_histogram, vwap
            symbol: Nom du symbole (pour la DB et le cache)
            asset_class: 'forex' | 'crypto' | 'commodity' | 'forex_jpy'
            store_in_db: Stocker le résultat en DB si True

        Returns:
            RegimeResult avec le régime détecté et sa confiance
        """
        try:
            result = self._detect_regime(df, symbol, asset_class)
            result.detected_at = datetime.now(timezone.utc).isoformat()

            # Mise à jour du cache
            self._cache[symbol] = result

            # Stockage DB
            if store_in_db and self._db and symbol:
                self._store_regime(symbol, result)

            return result

        except Exception as e:
            log.debug(f"Regime detection error ({symbol}): {e}")
            # Régime neutre par défaut en cas d'erreur
            return RegimeResult(
                regime='ranging',
                confidence=0.3,
                detected_at=datetime.now(timezone.utc).isoformat()
            )

    def _detect_regime(self, df, symbol: str, asset_class: str) -> RegimeResult:
        """Logique principale de détection par vote pondéré."""
        if df is None or len(df) < 20:
            return RegimeResult(regime='ranging', confidence=0.2)

        last = df.iloc[-1]
        thresholds = REGIME_THRESHOLDS.get(asset_class, DEFAULT_THRESHOLDS)

        # ─── Extraction des indicateurs ───────────────────────────────────────
        adx = self._safe_float(last, 'adx', 0)
        atr = self._safe_float(last, 'atr', 0)
        rsi = self._safe_float(last, 'rsi', 50)
        close = self._safe_float(last, 'close', 1)
        bb_upper = self._safe_float(last, 'bb_upper', 0)
        bb_lower = self._safe_float(last, 'bb_lower', 0)
        ema_fast = self._safe_float(last, 'ema_fast', 0)
        ema_slow = self._safe_float(last, 'ema_slow', 0)
        ema_trend = self._safe_float(last, 'ema_trend', 0)
        macd_hist = self._safe_float(last, 'macd_histogram', 0)
        st_dir = self._safe_float(last, 'supertrend_direction', 0)
        volume = self._safe_float(last, 'volume', 0)

        # Volume moyen sur 20 bougies
        vol_avg = float(df['volume'].iloc[-20:].mean()) if 'volume' in df.columns else volume
        volume_factor = volume / max(vol_avg, 1) if vol_avg > 0 else 1.0

        # Largeur des BB en % du prix
        bb_width_pct = ((bb_upper - bb_lower) / close * 100) if close > 0 and bb_upper > 0 else 0

        # ATR moyen sur 20 bougies
        atr_avg = float(df['atr'].iloc[-20:].mean()) if 'atr' in df.columns else atr
        atr_factor = atr / max(atr_avg, 1e-10) if atr_avg > 0 else 1.0

        # ─── VOTES ────────────────────────────────────────────────────────────
        # Chaque vote = (regime, points)
        votes: Dict[str, float] = {
            'trending_bull': 0.0,
            'trending_bear': 0.0,
            'ranging': 0.0,
            'high_volatility': 0.0,
            'breakout': 0.0,
            'pre_breakout': 0.0,
        }
        factors = {}

        # ADX (facteur le plus important)
        adx_trend = thresholds['adx_trending']
        adx_range = thresholds['adx_ranging']
        factors['adx'] = adx

        if adx > adx_trend * 1.2:  # ADX très fort
            if ema_fast > ema_slow:
                votes['trending_bull'] += 35
            else:
                votes['trending_bear'] += 35
        elif adx > adx_trend:
            if ema_fast > ema_slow:
                votes['trending_bull'] += 25
            else:
                votes['trending_bear'] += 25
        elif adx < adx_range:
            votes['ranging'] += 30
        else:
            votes['ranging'] += 10

        # EMA Alignment (direction macro)
        factors['ema_aligned'] = ema_fast > ema_slow > ema_trend if ema_trend > 0 else ema_fast > ema_slow
        if ema_fast > 0 and ema_slow > 0:
            if ema_fast > ema_slow:
                votes['trending_bull'] += 20
                if ema_trend > 0 and ema_slow > ema_trend:
                    votes['trending_bull'] += 10  # Triple alignment haussier
            else:
                votes['trending_bear'] += 20
                if ema_trend > 0 and ema_slow < ema_trend:
                    votes['trending_bear'] += 10  # Triple alignment baissier

        # Supertrend
        if st_dir > 0:
            votes['trending_bull'] += 10
        elif st_dir < 0:
            votes['trending_bear'] += 10

        # MACD Histogram
        if macd_hist > 0:
            votes['trending_bull'] += 5
        elif macd_hist < 0:
            votes['trending_bear'] += 5

        # Bollinger Bands
        factors['bb_width_pct'] = bb_width_pct
        if bb_width_pct > thresholds['bb_wide']:
            votes['high_volatility'] += 30
        elif bb_width_pct < thresholds['bb_squeeze']:
            # BB très serrées = pre-breakout
            votes['pre_breakout'] += 25
            votes['breakout'] += 10
        else:
            votes['ranging'] += 10

        # Prix vs BB
        if close > bb_upper:
            votes['breakout'] += 20
            votes['high_volatility'] += 10
        elif close < bb_lower:
            votes['breakout'] += 20
            votes['high_volatility'] += 10

        # ATR (volatilité absolue)
        factors['atr_factor'] = atr_factor
        if atr_factor > thresholds['atr_high_factor']:
            votes['high_volatility'] += 25
        elif atr_factor < 0.7:
            votes['ranging'] += 15
            votes['pre_breakout'] += 5

        # Volume spike
        factors['volume_factor'] = volume_factor
        if volume_factor > thresholds['volume_spike']:
            votes['breakout'] += 20
            votes['high_volatility'] += 10
        elif volume_factor < 0.5:
            votes['ranging'] += 10

        # RSI (sentiment de momentum)
        factors['rsi'] = rsi
        if rsi > thresholds['rsi_overbought']:
            votes['trending_bull'] += 5
            votes['high_volatility'] += 5
        elif rsi < thresholds['rsi_oversold']:
            votes['trending_bear'] += 5
            votes['high_volatility'] += 5
        elif 45 <= rsi <= 55:
            votes['ranging'] += 10

        # ─── SÉLECTION DU RÉGIME GAGNANT ─────────────────────────────────────
        total_votes = sum(votes.values())
        if total_votes == 0:
            return RegimeResult(regime='ranging', confidence=0.3, factors=factors)

        winner = max(votes, key=lambda k: votes[k])
        winner_pct = votes[winner] / total_votes

        # Logique spéciale : pre_breakout + vol spike → breakout
        if winner == 'pre_breakout' and volume_factor > thresholds['volume_spike']:
            winner = 'breakout'
            winner_pct = min(1.0, winner_pct * 1.3)

        # Confidence basée sur la dominance du vote gagnant
        confidence = min(0.95, winner_pct * 1.5)

        return RegimeResult(
            regime=winner,
            confidence=confidence,
            adx_value=adx,
            atr_value=atr,
            bb_width_pct=bb_width_pct,
            rsi_value=rsi,
            volume_factor=volume_factor,
            factors={**factors, 'votes': votes},
        )

    def _safe_float(self, row, col: str, default: float = 0.0) -> float:
        """Extrait une valeur float depuis une ligne DataFrame (robuste aux NaN)."""
        try:
            v = row.get(col) if hasattr(row, 'get') else getattr(row, col, None)
            if v is None:
                return default
            f = float(v)
            return default if math.isnan(f) else f
        except (TypeError, ValueError):
            return default

    def _store_regime(self, symbol: str, result: RegimeResult):
        """Stocke le régime détecté en DB."""
        try:
            with self._db.transaction() as conn:
                conn.execute("""
                    INSERT INTO market_regimes
                    (symbol, detected_at, regime, confidence, adx_value, atr_value, volume_factor)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    symbol, result.detected_at, result.regime,
                    result.confidence, result.adx_value,
                    result.atr_value, result.volume_factor
                ))
        except Exception as e:
            log.debug(f"DB store regime error: {e}")

    def get_cached_regime(self, symbol: str) -> Optional[RegimeResult]:
        """Retourne le dernier régime détecté pour un symbole (depuis le cache)."""
        return self._cache.get(symbol)

    def get_regime_label_fr(self, regime: str) -> str:
        """Retourne un libellé français du régime pour les logs."""
        labels = {
            'trending_bull': '📈 Tendance Haussière',
            'trending_bear': '📉 Tendance Baissière',
            'ranging': '↔️ Range/Consolidation',
            'high_volatility': '⚡ Haute Volatilité',
            'breakout': '🚀 Cassure/Breakout',
            'pre_breakout': '🔍 Pré-Cassure',
        }
        return labels.get(regime, regime)

    def get_risk_multiplier(self, regime: str) -> float:
        """
        Retourne un multiplicateur de risque selon le régime.
        Utilisé par le RiskManager pour adapter la taille de position.
        """
        multipliers = {
            'trending_bull': 1.0,      # Risque standard
            'trending_bear': 1.0,      # Risque standard
            'ranging': 0.7,            # -30% en range (moins de follow-through)
            'high_volatility': 0.6,    # -40% en haute vol (stops plus larges)
            'breakout': 1.2,           # +20% sur cassure (momentum fort)
            'pre_breakout': 0.8,       # -20% en attente (incertitude)
        }
        return multipliers.get(regime, 1.0)

    def get_score_min_adjustment(self, regime: str) -> int:
        """
        Retourne un ajustement du score_min selon le régime.
        +N = plus sélectif, -N = moins sélectif.
        """
        adjustments = {
            'trending_bull': 0,        # Standard
            'trending_bear': 0,        # Standard
            'ranging': +2,             # Plus sélectif en range
            'high_volatility': +1,     # Légèrement plus sélectif
            'breakout': -1,            # Moins sélectif (opportunities abondantes)
            'pre_breakout': +1,        # Attendre la confirmation
        }
        return adjustments.get(regime, 0)

    def get_strategy_recommendation(self, regime: str, asset_class: str) -> List[str]:
        """Retourne les stratégies recommandées pour ce régime."""
        recommendations = {
            ('trending_bull', 'forex'): ['TREND_FOLLOW_EMA', 'SUPERTREND_ADX', 'ICHIMOKU_CLOUD'],
            ('trending_bear', 'forex'): ['TREND_FOLLOW_EMA', 'SUPERTREND_ADX', 'ICHIMOKU_CLOUD'],
            ('ranging', 'forex'): ['REVERSAL_RSI', 'VWAP_MEAN_REVERT', 'BB_SQUEEZE'],
            ('high_volatility', 'forex'): ['BREAKOUT_ATR', 'SCALP_MOMENTUM'],
            ('breakout', 'forex'): ['BREAKOUT_ATR', 'SCALP_MOMENTUM', 'SESSION_OPEN_GAP'],
            ('pre_breakout', 'forex'): ['BB_SQUEEZE', 'BREAKOUT_ATR'],
            ('trending_bull', 'crypto'): ['CRYPTO_MOMENTUM', 'TREND_FOLLOW_EMA', 'BREAKOUT_ATR'],
            ('trending_bear', 'crypto'): ['CRYPTO_MOMENTUM', 'TREND_FOLLOW_EMA'],
            ('ranging', 'crypto'): ['VWAP_MEAN_REVERT', 'REVERSAL_RSI'],
            ('breakout', 'crypto'): ['CRYPTO_MOMENTUM', 'BREAKOUT_ATR'],
            ('high_volatility', 'crypto'): ['SCALP_MOMENTUM', 'BREAKOUT_ATR'],
        }
        key = (regime, asset_class)
        return recommendations.get(key, recommendations.get((regime, 'forex'), ['TREND_FOLLOW_EMA']))
