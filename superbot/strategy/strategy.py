"""
Strategy module for SuperBot Trading Unifié.
Defines the TradingStrategy class.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
import logging
from datetime import datetime

# Classificateur sémantique NLP pour les règles dynamiques
try:
    from superbot.strategy.semantic_classifier import SemanticRuleClassifier
    _SEMANTIC_AVAILABLE = True
except ImportError:
    _SEMANTIC_AVAILABLE = False

# Importer les modules necesarios
from superbot.indicators.technical_indicators import TechnicalIndicators
from superbot.strategy.knowledge_base import (
    calculate_kelly_fraction, calculate_risk_reward_ratio,
    is_market_trending
)

log = logging.getLogger("strategy")


class TradingStrategy:
    """
    Stratégie de trading unifiée qui combine les meilleures approches des bots existants
    avec un régime adaptatif (TRENDING vs RANGING) et un scoring multi-indicateurs.
    """

    def __init__(self, config: Dict[str, Any], indicators: Optional[TechnicalIndicators] = None):
        """
        Initialise la stratégie avec la configuration.

        Args:
            config: Dictionnaire contenant tous les paramètres de configuration
                   provenant de superbot.config
            indicators: Instance optionnelle de TechnicalIndicators pour éviter les redondances
        """
        self.config = config
        self.indicators = indicators if indicators is not None else TechnicalIndicators(config)

        # Historique des scores pour analyse
        self.score_history: List[Dict[str, Any]] = []

        # ML Scorer
        try:
            from superbot.ml.probabilistic_scorer import ProbabilisticScorer
            self.ml_scorer = ProbabilisticScorer()
        except ImportError:
            self.ml_scorer = None
            log.warning("ProbabilisticScorer non disponible, fallback sur le score linéaire.")

        # Seuils configurables
        self.score_min = config.get('SCORE_MIN', 6)
        self._base_score_min = self.score_min  # Référence pour détecter un ajustement externe
        self.risk_per_trade = config.get('RISK_PCT', 1.0)
        self.kelly_fraction = config.get('KELLY_FRACTION', 0.25)

        # Charger la base de connaissances dynamique v2 (crescendo : Murphy → Elder → Chan)
        try:
            from resources.learning_engine import load_knowledge_index, get_rules_by_level, get_filter_rules
            raw_rules = load_knowledge_index()
            self._filter_rules = get_filter_rules()  # Règles qui sont des filtres d'entrée obligatoires
            self._rules_by_level = {
                1: get_rules_by_level(1),  # Murphy — Fondations
                2: get_rules_by_level(2),  # Elder  — Systèmes
                3: get_rules_by_level(3),  # Chan   — Quantitatif
            }
            log.info(
                f"Base de connaissances chargée : {len(raw_rules)} règles | "
                f"L1={len(self._rules_by_level[1])} L2={len(self._rules_by_level[2])} L3={len(self._rules_by_level[3])} | "
                f"{len(self._filter_rules)} filtres obligatoires"
            )
        except Exception as e:
            raw_rules = []
            self._filter_rules = []
            self._rules_by_level = {1: [], 2: [], 3: []}
            log.warning(f"Impossible de charger la base de connaissances : {e}")

        # Classifier sémantiquement les règles (NLP ou fallback mots-clés)
        if _SEMANTIC_AVAILABLE and raw_rules:
            try:
                self._classifier = SemanticRuleClassifier()
                # Charger le cache si disponible et de la bonne version, sinon reclassifier
                cached = self._classifier.load_cache()
                if cached and len(cached) == len(raw_rules):
                    self.knowledge_rules = cached
                    log.info(f"Règles chargées depuis le cache sémantique v2 ({len(cached)} règles).")
                else:
                    log.info("Reconstruction du cache sémantique...")
                    self.knowledge_rules = self._classifier.classify_rules(raw_rules)
                    self._classifier.save_cache(self.knowledge_rules)
            except Exception as e:
                log.warning(f"Classificateur sémantique en erreur ({e}), utilisation des règles brutes.")
                self.knowledge_rules = raw_rules
        else:
            self.knowledge_rules = raw_rules

        log.info(
            f"TradingStrategy initialisée — "
            f"score_min={self.score_min}, risk={self.risk_per_trade}%, "
            f"kelly={self.kelly_fraction}, règles_actives={len(self.knowledge_rules)}"
        )

    def analyze_market(self, df: pd.DataFrame,
                       account_balance: float = 0.0,
                       real_win_rate: Optional[float] = None,
                       symbol: str = "",
                       btc_change_24h: Optional[float] = None,
                       sentiment_factor: float = 1.0,
                       news_filter_passed: bool = True) -> Dict[str, Any]:
        """
        Analyse complète du marché pour générer un signal de trading.

        Args:
            df: DataFrame avec données OHLCV et indicateurs déjà calculés (ou brut)
            account_balance: Solde réel du compte (0 = non fourni, estimation interne)
            real_win_rate: Win rate réel calculé par le RiskManager (None = estimation 0.55)
            symbol: Symbole de l'actif analysé (utilisé pour les filtres crypto)
            btc_change_24h: Variation BTC sur 24h en % (négatif = baisse, None = non disponible)
            sentiment_factor: Ajustement NLP du NewsManager (1.0 = neutre, >1 = positif)
            news_filter_passed: False si les nouvelles récentes interdisent de trader

        Returns:
            Dictionnaire contenant l'analyse complète et le signal de trading
        """
        if len(df) < 50:  # Minimum de données nécessaires pour les indicateurs
            log.warning(f"Données insuffisantes pour l'analyse: {len(df)} barres")
            return self._create_neutral_signal("INSUFFICIENT_DATA")

        # Bug#1 fix : ne recalculer les indicateurs que si le DataFrame est brut
        # (sans colonne 'rsi', donc pas encore enrichi par TechnicalIndicators)
        if 'rsi' not in df.columns:
            df_with_indicators = self.indicators.calculate_all_indicators(df.copy())
        else:
            df_with_indicators = df  # Déjà enrichi par main.py — évite le triple calcul

        # Obtenir les valeurs les plus récentes (On utilise les bougies clôturées pour éviter le repainting)
        current_candle = df_with_indicators.iloc[-1]
        latest = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else current_candle
        prev = df_with_indicators.iloc[-3] if len(df_with_indicators) >= 3 else latest

        # Déterminer le régime de marché (HMM si disponible, sinon ADX)
        market_regime, ml_confidence, hmm_state = self.indicators.get_market_regime_with_confidence(df_with_indicators)
        is_trending = market_regime == 'TRENDING'

        # Logguer le régime détecté avec la source de détection
        hmm_label = 'UNKNOWN'
        if hmm_state >= 0:
            hmm_label = self.indicators._regime_detector.get_state_label(hmm_state) if self.indicators._regime_detector else 'HMM'
            log.debug(f"[Regime] HMM: {market_regime} (etat={hmm_label}, confiance={ml_confidence:.1%})")
        else:
            log.debug(f"[Regime] ADX fallback: {market_regime} (confiance={ml_confidence:.1%})")

        # ── Détection de la classe d'actif ─────────────────────────────────────
        sym_upper = symbol.upper().replace("/", "").replace("-", "")
        broker_type = self.config.get('BROKER_TYPE', '')

        is_crypto = (
            broker_type == 'binance' or
            any(k in sym_upper for k in ["USDT", "BUSD"]) or
            (any(sym_upper.startswith(k) for k in ["BTC", "ETH", "SOL", "LTC", "XRP"]) and "USD" in sym_upper)
        )
        is_forex = broker_type == 'mt5' or (
            not is_crypto and
            len(sym_upper) == 6 and
            sym_upper[:3].isalpha() and sym_upper[3:].isalpha() and
            sym_upper not in ('XAUUSD', 'XAGUSD')
        )
        is_stock = broker_type == 'alpaca' or (not is_crypto and not is_forex)
        is_btc_pair = "BTC" in sym_upper and ("USDT" in sym_upper or "USD" in sym_upper)
        is_altcoin = is_crypto and not is_btc_pair

        # Hint d'actif pour le score par signaux (direction du filtre d'extension).
        asset_hint = ("BTC" if is_btc_pair else
                      "ALTCOIN" if is_altcoin else
                      "STOCK" if is_stock else
                      "FOREX" if is_forex else "")

        log.debug(f"[AssetType] {symbol} → crypto={is_crypto}, forex={is_forex}, stock={is_stock}")

        # ── Sélection des paramètres spécifiques à l'asset_type ────────────────
        if is_crypto:
            ema_fast_col  = 'ema_21'
            ema_slow_col  = 'ema_55'
            adx_threshold = self.config.get('ADX_TREND_CRYPTO', 25)
            effective_score_min = self.config.get('SCORE_MIN_CRYPTO', 7)
            sl_mult = self.config.get('SL_ATR_MULT_CRYPTO', 2.0)
            tp_mult = self.config.get('TP_ATR_MULT_CRYPTO', 4.0)
        elif is_forex:
            ema_fast_col  = 'ema_14'
            ema_slow_col  = 'ema_50'
            adx_threshold = self.config.get('ADX_TREND_FOREX', 18)
            effective_score_min = self.config.get('SCORE_MIN_FOREX', 5)
            sl_mult = self.config.get('SL_ATR_MULT_FOREX', 1.5)
            tp_mult = self.config.get('TP_ATR_MULT_FOREX', 3.0)
        else:  # stock / ETF
            ema_fast_col  = 'ema_20'
            ema_slow_col  = 'ema_50'
            adx_threshold = self.config.get('ADX_TREND_STOCK', 20)
            effective_score_min = self.config.get('SCORE_MIN_STOCK', 5)
            sl_mult = self.config.get('SL_ATR_MULT_STOCK', 1.5)
            tp_mult = self.config.get('TP_ATR_MULT_STOCK', 3.0)

        # Un ajustement externe du score_min global (cloud, walk-forward, adaptation)
        # remplace le seuil par classe d'actif.
        if self.score_min != self._base_score_min:
            effective_score_min = self.score_min

        # Vérifier la blacklist crypto
        crypto_blacklist = self.config.get('CRYPTO_BLACKLIST', [])
        is_blacklisted = symbol in crypto_blacklist or sym_upper in [b.upper().replace("/","") for b in crypto_blacklist]
        if is_blacklisted:
            log.info(f"[P0-2] {symbol} est dans la CRYPTO_BLACKLIST — signal neutre forçé.")
            return self._create_neutral_signal(f"BLACKLISTED:{symbol}")

        # Calculer les scores selon le régime
        if is_trending:
            trend_score, trend_details = self._calculate_trending_score(
                df_with_indicators, ema_fast_col, ema_slow_col, adx_threshold, asset_hint
            )
            ranging_score, ranging_details = 0, {}  # Pas utilisé en tendance
            total_score = trend_score
            details = {**trend_details, 'regime': 'TRENDING'}
        else:
            if is_crypto:
                log.info(f"🚫 Range trading désactivé pour la crypto {symbol} (Trend Following uniquement)")
                return self._create_neutral_signal(f"RANGING_CRYPTO_BLOCKED:{symbol}")
            if is_stock:
                log.info(f"🚫 Range trading désactivé pour l'ETF {symbol} (Momentum uniquement)")
                return self._create_neutral_signal(f"RANGING_STOCK_BLOCKED:{symbol}")

            # Seuil Hurst relevé à 0.65 pour les ETF/stocks : SPY/QQQ sont autour de
            # 0.52-0.58 et restaient systématiquement bloqués avec le seuil de 0.50.
            hurst_block_threshold = 0.65 if is_stock else 0.50
            try:
                import numpy as np
                prices = df_with_indicators['close'].values
                if len(prices) >= 50:
                    lags = range(2, 20)
                    # Calcul simplifié de Hurst
                    tau = [np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag]))) for lag in lags]
                    poly = np.polyfit(np.log(lags), np.log(tau), 1)
                    hurst = poly[0] * 2.0
                    if hurst >= hurst_block_threshold:
                        log.info(f"🚫 Range trading rejeté pour {symbol} : Marché non-stationnaire (Hurst = {hurst:.2f} >= {hurst_block_threshold:.2f})")
                        return self._create_neutral_signal(f"RANGING_NON_STATIONARY:{symbol}")
                    else:
                        log.debug(f"✅ Marché stationnaire validé pour {symbol} (Hurst = {hurst:.2f} < {hurst_block_threshold:.2f})")
            except Exception as e:
                log.warning(f"Erreur lors du calcul de Hurst pour {symbol} : {e}")

            ranging_score, ranging_details = self._calculate_ranging_score(df_with_indicators)
            trend_score, trend_details = 0, {}  # Pas utilisé en range
            
            # Bonus Ranging Forex : +1 point car le Forex mean-revert très bien
            if is_forex:
                ranging_score += 1.0
                log.debug(f"[Forex Ranging Bonus] +1.0 point au score Ranging ({symbol})")
                
            total_score = ranging_score
            details = {**ranging_details, 'regime': 'RANGING'}

        # Vérifier les triggers (conditions d'entrée) — avec les bons paramètres par asset_type
        trigger_long, trigger_short = self._check_entry_triggers(
            df_with_indicators, is_trending, ema_fast_col, ema_slow_col, adx_threshold,
            is_crypto=is_crypto, is_forex=is_forex, is_stock=is_stock
        )

        # Volume strict pour BNB/USDT
        bnb_vol_factor = self.config.get('CRYPTO_BNB_VOLUME_FACTOR', 1.5)
        if sym_upper == "BNBUSDT" and (trigger_long or trigger_short):
            latest_v = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else df_with_indicators.iloc[-1]
            volume = latest_v.get('volume', 0)
            volume_ma = latest_v.get('volume_ma', 0)
            if volume_ma > 0 and volume < volume_ma * bnb_vol_factor:
                log.info(
                    f"[P2-2] BNB/USDT : volume insuffisant ({volume:.0f} < {volume_ma * bnb_vol_factor:.0f}) "
                    f"— trigger annulé (overtrading prevention)."
                )
                trigger_long = False
                trigger_short = False

        # ── Blocage des SHORTs sur ETF/Stocks ────────────────────────────────
        # Les ETF sont des paniers long-only par nature. Les shorts nécessitent
        # un account margin, la PDT rule, et des coûts d'emprunt non modélisés.
        allow_short_stock = self.config.get('ALLOW_SHORT_STOCK', False)
        if is_stock and trigger_short and not allow_short_stock:
            log.info(f"🚫 SHORT {symbol} (ETF/Stock) bloqué — ALLOW_SHORT_STOCK=false")
            trigger_short = False

        # Calculer le ratio risque/rendement potentiel avec les multiplicateurs ATR spécifiques
        current_price = current_candle['close']
        rr_ratio, sl_price, tp_price = self._calculate_potential_rr(latest, current_price, sl_mult, tp_mult)

        # Ajuster les prix SL/TP si c'est un signal de vente (SHORT) pour qu'ils soient orientés correctement
        if trigger_short and not trigger_long:
            atr = latest.get('atr', 0)
            if atr > 0:
                sl_price = current_price + (atr * sl_mult)
                tp_price = current_price - (atr * tp_mult)
        
        # Ajuster le score avec le facteur de sentiment
        adjusted_score = total_score * sentiment_factor

        # Valeurs par défaut ajustables dynamiquement par les règles
        risk_pct = self.risk_per_trade
        kelly_frac = self.kelly_fraction

        # Appliquer les règles dynamiques de connaissances (par exemple, Ernest Chan, Bob Volman)
        adjusted_score, risk_pct, kelly_frac = self._apply_knowledge_rules(
            adjusted_score,
            risk_pct,
            kelly_frac,
            {
                'market_regime': market_regime,
                'is_trending': is_trending,
                'total_score': total_score,
                'trigger_long': trigger_long,
                'trigger_short': trigger_short,
                'latest_bar': latest,
                'ml_confidence': ml_confidence,   # confiance HMM
                'hmm_state': hmm_state,            # état brut HMM
            }
        )

        # Modulation du risque selon les régimes HMM
        if hmm_label == 'HIGH_VOL_RANGE':
            risk_pct = risk_pct / 2.0
            log.debug(f"[HMM-4] HIGH_VOL_RANGE détecté : réduction du risque à {risk_pct}%")
        elif hmm_label == 'LOW_VOL_RANGE':
            risk_pct = risk_pct * 1.5
            log.debug(f"[HMM-4] LOW_VOL_RANGE détecté : augmentation du risque à {risk_pct}%")

        # Bug#2 fix : utiliser le vrai solde si fourni, sinon 0 (le sizing réel est dans RiskManager)
        effective_balance = account_balance if account_balance > 0 else 10000.0
        risk_amount = effective_balance * (risk_pct / 100.0)

        # Inférence probabiliste ML et matrice E(R)
        from superbot.strategy.components.scorer import calculate_probabilistic_win_rate
        adx_val = latest.get('adx', 20.0)
        prob_meta = calculate_probabilistic_win_rate(adjusted_score, market_regime, adx_val, rr_ratio)

        win_proba = prob_meta['win_prob']
        if self.ml_scorer and self.ml_scorer.is_trained:
            ml_prob = self.ml_scorer.predict_proba(latest)
            win_proba = max(win_proba, ml_prob)
            log.debug(f"[ML Scoring] Probabilité de gain calculée: {win_proba:.1%}")

        # Le win rate réalisé récent n'est plus mélangé 50/50 à la probabilité :
        # c'était une boucle de rétroaction négative (WR faible -> proba faible ->
        # moins d'entrées -> WR qui ne remonte pas). Il reste ici à titre de
        # sanity-check (log), pas comme dénominateur de la décision.
        if real_win_rate is not None and 0.0 < real_win_rate < 1.0:
            log.info(f"[Sanity] Win rate réalisé récent = {real_win_rate:.1%} (informatif)")

        details['win_prob'] = win_proba
        details['expected_value'] = prob_meta['expected_value']

        # Validation Probabiliste : score >= minimum ET espérance positive.
        # Seuil de rentabilité P(Win) > 1/(1+RR), avec 2 pts de marge pour les coûts.
        breakeven_win_rate = 1.0 / (1.0 + rr_ratio) if rr_ratio > 0 else 0.60
        min_win_proba = min(max(breakeven_win_rate + 0.02, 0.20), 0.70)

        # La porte probabiliste n'est active que si le calibrateur est fitté sur un
        # historique réel. Avant calibration, le prior prudent (~0.30) est sous le
        # seuil de rentabilité et bloquerait 100% des signaux (bot inerte) : on
        # retombe alors sur les seuls garde-fous score + R:R.
        from superbot.ml.win_rate_calibrator import get_calibrator
        proba_gate_active = get_calibrator().is_fitted

        if proba_gate_active:
            is_valid_score = (adjusted_score >= effective_score_min) and (win_proba >= min_win_proba)
        else:
            is_valid_score = adjusted_score >= effective_score_min

        should_long = (
                is_valid_score and
                trigger_long and
                rr_ratio >= 1.5 and  # R:R minimum de 1.5:1
                news_filter_passed
        )

        should_short = (
                is_valid_score and
                trigger_short and
                rr_ratio >= 1.5 and  # R:R minimum de 1.5:1 (abaissé de 2.0 — conditions marché réelles)
                news_filter_passed
        )

        # Prevent simultaneous long and short signals
        if should_long and should_short:
            log.warning(f"Both long and short signals for {symbol}, disabling both")
            should_long = False
            should_short = False

        # Filtre tendance de fond via EMA200 D1 : pénalité progressive selon l'écart %.
        if is_crypto and should_long:
            latest_bar_p01 = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else df_with_indicators.iloc[-1]
            price_p01 = latest_bar_p01.get('close', 0)
            ema200_d1 = latest_bar_p01.get('ema_d1', 0)  # EMA200 D1 (EMA50 quotidien)

            if ema200_d1 > 0:
                gap_pct = (ema200_d1 - price_p01) / ema200_d1 * 100 if price_p01 < ema200_d1 else 0

                if gap_pct > 0:  # Seulement si le prix est sous l'EMA200 D1
                    # Pénalité proportionnelle à l'écart (max -3 points pour -10% ou plus)
                    penalty = min(3.0, max(0.0, (gap_pct / 10.0) * 3.0))  # -0.3 point pour chaque 1% d'écart
                    penalty = min(penalty, 3.0)  # Plafonner la pénalité à 3 points max

                    total_score = max(0, total_score - penalty)
                    adjusted_score = max(0, adjusted_score - penalty)

                    if penalty >= 2.0:  # Log significatif seulement pour pénalités importantes
                        log.info(
                            f"[P0-1] {symbol} : prix ({price_p01:.4f}) < EMA200 D1 ({ema200_d1:.4f}, "
                            f"écart={gap_pct:.1f}%) — pénalité appliquée: {-penalty:.1f} points"
                        )
                    else:
                        log.debug(
                            f"[P0-1] {symbol} : prix légèrement sous EMA200 D1 ({gap_pct:.1f}%) "
                            f"— pénalité mineure: {-penalty:.1f} points"
                        )

        # Si BTC a baissé de > CRYPTO_BUY_BLOCK_BTC_DROP% sur 24h, bloquer les BUY altcoins.
        if is_altcoin and should_long and btc_change_24h is not None:
            block_threshold = self.config.get('CRYPTO_BUY_BLOCK_BTC_DROP', 2.0)
            if btc_change_24h <= -block_threshold:
                log.info(
                    f"[P1-1] Régime BTC baissier détecté (BTC 24h: {btc_change_24h:+.2f}% < −{block_threshold}%) "
                    f"— BUY altcoin {symbol} BLOQUÉ."
                )
                should_long = False

        # Position sizing is handled by the risk manager in the signal executor
        entry_price = 0.0
        if should_long or should_short:
            entry_price = current_price

        # Mettre à jour l'historique des scores
        self.score_history.append({
            'timestamp': latest.name if hasattr(latest.name, 'isoformat') else datetime.now(),
            'score': total_score,
            'regime': market_regime,
            'trigger_long': trigger_long,
            'trigger_short': trigger_short,
            'rr_ratio': rr_ratio,
            'close_price': current_price
        })

        # Limiter la taille de l'historique
        if len(self.score_history) > 1000:
            self.score_history = self.score_history[-1000:]

        # Construire le signal de trading
        signal = {
            'timestamp': latest.name if hasattr(latest.name, 'isoformat') else datetime.now(),
            'symbol': 'UNKNOWN',  # À remplir par l'appelant
            'market_regime': market_regime,
            'hmm_label': hmm_label,  # Label HMM pour les multiplicateurs ATR
            'is_trending': is_trending,
            'trend_score': trend_score,
            'ranging_score': ranging_score,
            'total_score': total_score,
            'adjusted_score': adjusted_score,
            'score_min': effective_score_min,  # Score min effectif par asset_type
            'should_long': should_long,
            'should_short': should_short,
            'trigger_long': trigger_long,
            'trigger_short': trigger_short,
            'entry_price': current_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'rr_ratio': rr_ratio,
            'risk_amount': risk_amount,
            'sentiment_factor': sentiment_factor,
            'news_filter_passed': news_filter_passed,
            'indicators': self._extract_key_indicators(latest),
            'details': {**details, 'hmm_label': hmm_label}  # Aussi dans details pour rétro-compat
        }

        log.debug(f"Signal généré: {signal['market_regime']} | Score: {signal['total_score']:.1f}/{self.score_min} | "
                  f"Long: {signal['should_long']} | Short: {signal['should_short']} | RR: {signal['rr_ratio']:.2f}")

        return signal

    def _apply_knowledge_rules(
        self,
        current_score: float,
        risk_pct: float,
        kelly_frac: float,
        context: Dict[str, Any]
    ) -> Tuple[float, float, float]:
        from superbot.strategy.components.rule_engine import _apply_knowledge_rules
        return _apply_knowledge_rules(self, current_score, risk_pct, kelly_frac, context)


    def _create_neutral_signal(self, reason: str) -> Dict[str, Any]:
        """Génère un signal neutre en cas d'erreur ou d'absence de données."""
        return {
            'timestamp': datetime.now(),
            'symbol': 'UNKNOWN',
            'market_regime': 'UNKNOWN',
            'is_trending': False,
            'trend_score': 0,
            'ranging_score': 0,
            'total_score': 0,
            'adjusted_score': 0,
            'score_min': self.score_min,
            'should_long': False,
            'should_short': False,
            'trigger_long': False,
            'trigger_short': False,
            'entry_price': 0.0,
            'sl_price': 0.0,
            'tp_price': 0.0,
            'rr_ratio': 0.0,
            'position_size': 0.0,
            'risk_amount': 0.0,
            'sentiment_factor': 1.0,
            'news_filter_passed': False,
            'indicators': {},
            'details': {'reason': reason}
        }

    def _calculate_trending_score(self, df, ema_fast_col='ema_fast', ema_slow_col='ema_slow',
                                  adx_threshold=22.0, asset_hint=""):
        if self.config.get('SCORE_MODE', 'votes') == 'signals':
            from superbot.strategy.components.scorer import _calculate_trending_score_signals
            return _calculate_trending_score_signals(
                self, df, ema_fast_col, ema_slow_col, adx_threshold, asset_hint)
        from superbot.strategy.components.scorer import _calculate_trending_score
        return _calculate_trending_score(self, df, ema_fast_col, ema_slow_col, adx_threshold)

    def _calculate_ranging_score(self, df):
        from superbot.strategy.components.scorer import _calculate_ranging_score
        return _calculate_ranging_score(self, df)


    def _detect_candlestick_pattern(self, df: pd.DataFrame, lookback: int = 5) -> int:
        """
        Détecte des patterns de chandeliers simples.
        """
        if len(df) < lookback:
            return 0

        recent = df.iloc[-lookback:]
        if len(recent) < 1:
            return 0

        idx = len(recent) - 1
        open_price = recent.iloc[idx]['open']
        high_price = recent.iloc[idx]['high']
        low_price = recent.iloc[idx]['low']
        close_price = recent.iloc[idx]['close']

        body = abs(close_price - open_price)
        lower_shadow = min(open_price, close_price) - low_price
        upper_shadow = high_price - max(open_price, close_price)
        total_range = high_price - low_price

        if total_range == 0:
            return 0

        body_ratio = body / total_range
        lower_shadow_ratio = lower_shadow / total_range
        upper_shadow_ratio = upper_shadow / total_range

        is_hammer = (body_ratio < 0.3) and (lower_shadow_ratio > 0.6) and (upper_shadow_ratio < 0.1)
        is_shooting_star = (body_ratio < 0.3) and (upper_shadow_ratio > 0.6) and (lower_shadow_ratio < 0.1)

        if idx >= 1:
            prev_open = recent.iloc[idx-1]['open']
            prev_close = recent.iloc[idx-1]['close']
            prev_body = abs(prev_close - prev_open)
            bullish_engulfing = (close_price > open_price and
                               open_price <= prev_close and
                               close_price >= prev_open and
                               body > prev_body)

            bearish_engulfing = (close_price < open_price and
                               open_price >= prev_close and
                               close_price <= prev_open and
                               body > prev_body)

            if bullish_engulfing:
                return 1
            elif bearish_engulfing:
                return -1

        if is_hammer:
            return 1
        elif is_shooting_star:
            return -1

        return 0

    def _check_entry_triggers(
        self, df: pd.DataFrame, is_trending: bool,
        ema_fast_col: str = 'ema_fast', ema_slow_col: str = 'ema_slow',
        adx_threshold: float = 22.0,
        is_crypto: bool = False, is_forex: bool = False, is_stock: bool = False
    ) -> Tuple[bool, bool]:
        from superbot.strategy.components.signal_generator import _check_entry_triggers
        return _check_entry_triggers(
            self, df, is_trending, ema_fast_col, ema_slow_col, adx_threshold,
            is_crypto, is_forex, is_stock
        )

    def _calculate_potential_rr(
        self, latest: pd.Series, current_price: float,
        sl_mult: float = None, tp_mult: float = None
    ) -> Tuple[float, float, float]:
        """
        Calcule le ratio risque/rendement potentiel brut (sans déduire les frais).
        Les multiplicateurs SL/TP peuvent être passés en paramètre pour s'adapter
        à chaque classe d'actif (crypto sl=2.0, forex sl=1.5, stock sl=1.5).
        """
        atr = latest.get('atr', 0)
        if atr == 0 or pd.isna(atr):
            return 0.0, 0.0, 0.0

        # Utiliser les paramètres passés, sinon fallback sur le config global
        if sl_mult is None:
            sl_mult = self.config.get('SL_ATR_MULT', 1.5)
        if tp_mult is None:
            tp_mult = self.config.get('TP_ATR_MULT', 3.0)

        sl_price = current_price - (atr * sl_mult)
        tp_price = current_price + (atr * tp_mult)

        risk = current_price - sl_price    # = atr * sl_mult
        reward = tp_price - current_price  # = atr * tp_mult

        # NOTE: Le R:R est calculé BRUT (sans déduire les frais) pour la décision d'entrée.
        # Les coûts de transaction sont déjà pris en compte dans le sizing du RiskManager.
        # Déduire les coûts ici dégradait artificiellement un R:R théorique de 2.0 → ~1.3
        # et bloquait tous les trades sur crypto/stock en conditions de marché normales.
        if risk <= 0 or reward <= 0:
            return 0.0, sl_price, tp_price

        rr_ratio = round(reward / risk, 4)
        return rr_ratio, sl_price, tp_price

    def _extract_key_indicators(self, latest: pd.Series) -> Dict[str, float]:
        """
        Extrait les indicateurs clés pour le logging et le débogage.
        """
        return {
            'close': latest.get('close', 0),
            'ema_fast': latest.get('ema_fast', 0),
            'ema_slow': latest.get('ema_slow', 0),
            'ema_trend': latest.get('ema_trend', 0),
            'rsi': latest.get('rsi', 0),
            'macd': latest.get('macd', 0),
            'macd_signal': latest.get('macd_signal', 0),
            'macd_hist': latest.get('macd_histogram', 0),
            'adx': latest.get('adx', 0),
            'supertrend': latest.get('supertrend', 0),
            'supertrend_trend': latest.get('supertrend_trend', 0),
            'atr': latest.get('atr', 0),
            'bb_position': ((latest.get('close', 0) - latest.get('bb_lower', 0)) /
                          (latest.get('bb_upper', 0) - latest.get('bb_lower', 0))
                          if latest.get('bb_upper', 0) != latest.get('bb_lower', 0) else 0.5),
            'mfi': latest.get('mfi', 50),
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur la performance de la stratégie.
        """
        if not self.score_history:
            return {'total_signals': 0}

        df_scores = pd.DataFrame(self.score_history)
        long_signals = df_scores['should_long'].sum()
        short_signals = df_scores['should_short'].sum()
        total_signals = len(df_scores)

        avg_score = df_scores['total_score'].mean()
        score_std = df_scores['total_score'].std()

        regime_counts = df_scores['market_regime'].value_counts().to_dict()

        return {
            'total_signals': total_signals,
            'long_signals': long_signals,
            'short_signals': short_signals,
            'avg_score': avg_score,
            'score_std': score_std,
            'regime_distribution': regime_counts,
            'recent_avg_score': df_scores.tail(20)['total_score'].mean() if len(df_scores) >= 20 else avg_score
        }
