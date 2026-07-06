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
    calculate_position_size_from_risk, is_market_trending
)

log = logging.getLogger("strategy")


class TradingStrategy:
    """
    Stratégie de trading unifiée qui combine les meilleures approches des bots existants
    avec un régime adaptatif (TRENDING vs RANGING) et un scoring multi-indicateurs.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise la stratégie avec la configuration.

        Args:
            config: Dictionnaire contenant tous les paramètres de configuration
                   provenant de superbot.config
        """
        self.config = config
        self.indicators = TechnicalIndicators(config)

        # Historique des scores pour analyse
        self.score_history: List[Dict[str, Any]] = []

        # Seuils configurables
        self.score_min = config.get('SCORE_MIN', 6)  # Score minimum pour entrer
        self.risk_per_trade = config.get('RISK_PCT', 1.0)  # % du compte à risquer par trade
        self.kelly_fraction = config.get('KELLY_FRACTION', 0.25)  # Fraction de Kelly à utiliser

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

        # Déterminer le régime de marché (HMM Phase 2 si modèle disponible, sinon ADX)
        market_regime, ml_confidence, hmm_state = self.indicators.get_market_regime_with_confidence(df_with_indicators)
        is_trending = market_regime == 'TRENDING'

        # Logguer le régime détecté avec la source de détection
        if hmm_state >= 0:
            hmm_label = self.indicators._regime_detector.get_state_label(hmm_state) if self.indicators._regime_detector else 'HMM'
            log.debug(f"[Regime] HMM: {market_regime} (etat={hmm_label}, confiance={ml_confidence:.1%})")
        else:
            log.debug(f"[Regime] ADX fallback: {market_regime} (confiance={ml_confidence:.1%})")

        # ── Détecter si l'actif est une crypto ───────────────────────────
        sym_upper = symbol.upper().replace("/", "").replace("-", "")
        is_crypto = (
            self.config.get('BROKER_TYPE') == 'binance' or
            any(k in sym_upper for k in ["USDT", "BUSD"]) or
            (any(sym_upper.startswith(k) for k in ["BTC", "ETH", "SOL", "LTC", "XRP"]) and "USD" in sym_upper)
        )
        is_btc_pair = "BTC" in sym_upper and ("USDT" in sym_upper or "USD" in sym_upper)
        is_altcoin = is_crypto and not is_btc_pair

        # ── P0-2 : Vérifier la blacklist crypto ─────────────────────────────
        crypto_blacklist = self.config.get('CRYPTO_BLACKLIST', [])
        is_blacklisted = symbol in crypto_blacklist or sym_upper in [b.upper().replace("/","") for b in crypto_blacklist]
        if is_blacklisted:
            log.info(f"[P0-2] {symbol} est dans la CRYPTO_BLACKLIST — signal neutre forçé.")
            return self._create_neutral_signal(f"BLACKLISTED:{symbol}")

        # Calculer les scores selon le régime
        if is_trending:
            trend_score, trend_details = self._calculate_trending_score(df_with_indicators)
            ranging_score, ranging_details = 0, {}  # Pas utilisé en tendance
            total_score = trend_score
            details = {**trend_details, 'regime': 'TRENDING'}
        else:
            if is_crypto:
                log.info(f"🚫 Range trading désactivé pour la crypto {symbol} (Trend Following uniquement)")
                return self._create_neutral_signal(f"RANGING_CRYPTO_BLOCKED:{symbol}")
            ranging_score, ranging_details = self._calculate_ranging_score(df_with_indicators)
            trend_score, trend_details = 0, {}  # Pas utilisé en range
            total_score = ranging_score
            details = {**ranging_details, 'regime': 'RANGING'}


        # Vérifier les triggers (conditions d'entrée)
        trigger_long, trigger_short = self._check_entry_triggers(df_with_indicators, is_trending)

        # ── P2-2 : Volume strict pour BNB/USDT ───────────────────────────────
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

        # Calculer le ratio risque/rendement potentiel (basé sur le prix d'entrée actuel)
        current_price = current_candle['close']
        rr_ratio, sl_price, tp_price = self._calculate_potential_rr(latest, current_price)

        # Ajuster les prix SL/TP si c'est un signal de vente (SHORT) pour qu'ils soient orientés correctement
        if trigger_short and not trigger_long:
            atr = latest.get('atr', 0)
            if atr > 0:
                sl_price = current_price + (atr * self.config.get('SL_ATR_MULT', 1.5))
                tp_price = current_price - (atr * self.config.get('TP_ATR_MULT', 3.0))

        # Le sentiment_factor est passé depuis le NewsManager dans main.py
        # news_filter_passed est également propagé
        
        # Ajuster le score avec le facteur de sentiment (Phase 3)
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
                'ml_confidence': ml_confidence,   # Phase 2 : confiance HMM
                'hmm_state': hmm_state,            # Phase 2 : état brut HMM
            }
        )

        # Bug#2 fix : utiliser le vrai solde si fourni, sinon 0 (le sizing réel est dans RiskManager)
        effective_balance = account_balance if account_balance > 0 else 10000.0
        risk_amount = effective_balance * (risk_pct / 100.0)

        # Déterminer si on prend le trade
        # ── P1-2 : Score minimum 7 pour crypto en ADX faible ────────────────────
        effective_score_min = self.score_min
        if is_crypto:
            latest_bar = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else df_with_indicators.iloc[-1]
            adx_val = latest_bar.get('adx', 999)
            adx_threshold = self.config.get('ADX_TREND', 22)
            if adx_val < adx_threshold:
                crypto_score_min = self.config.get('CRYPTO_SCORE_MIN', 7)
                if crypto_score_min > effective_score_min:
                    log.debug(
                        f"[P1-2] ADX={adx_val:.1f} < {adx_threshold} sur crypto {symbol} "
                        f"— score_min élevé à {crypto_score_min} (vs {effective_score_min})."
                    )
                    effective_score_min = crypto_score_min

        should_long = (
                adjusted_score >= effective_score_min and
                trigger_long and
                rr_ratio >= 2.0 and  # R:R minimum de 2:1
                news_filter_passed
        )

        should_short = (
                adjusted_score >= effective_score_min and
                trigger_short and
                rr_ratio >= 2.0 and  # R:R minimum de 2:1
                news_filter_passed
        )

        # ── P0-1 : Bloquer les BUY crypto si tendance D1 BTC baissière ───────────
        # Stratégie : utiliser l'EMA200 de la paire elle-même comme proxy de la tendance D1.
        # Si le prix est sous l'EMA200 H1, la tendance de fond est baissière — bloquer les BUY.
        if is_crypto and should_long:
            latest_bar_p01 = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else df_with_indicators.iloc[-1]
            price_p01 = latest_bar_p01.get('close', 0)
            ema200_p01 = latest_bar_p01.get('ema_trend', 0)  # EMA200
            if ema200_p01 > 0 and price_p01 < ema200_p01:
                log.info(
                    f"[P0-1] {symbol} : prix ({price_p01:.4f}) < EMA200 ({ema200_p01:.4f}) "
                    f"— tendance D1 baissière, BUY BLOQUÉ."
                )
                should_long = False

        # ── P1-1 : Détecteur de régime inter-sessions (variation BTC 24h) ──────
        # Si BTC a baissé de > CRYPTO_BUY_BLOCK_BTC_DROP% sur 24h,
        # bloquer les signaux BUY sur TOUS les altcoins (copycat crash pattern).
        if is_altcoin and should_long and btc_change_24h is not None:
            block_threshold = self.config.get('CRYPTO_BUY_BLOCK_BTC_DROP', 2.0)
            if btc_change_24h <= -block_threshold:
                log.info(
                    f"[P1-1] Régime BTC baissier détecté (BTC 24h: {btc_change_24h:+.2f}% < −{block_threshold}%) "
                    f"— BUY altcoin {symbol} BLOQUÉ."
                )
                should_long = False

        # Calculer la taille de position si on prend le trade
        position_size = 0.0
        if should_long or should_short:
            entry_price = current_price
            sl_for_size = sl_price if sl_price > 0 else entry_price - (latest['atr'] * self.config.get('SL_ATR_MULT', 1.5))
            tp_for_size = tp_price if tp_price > 0 else entry_price + (latest['atr'] * self.config.get('TP_ATR_MULT', 3.0))

            base_size = calculate_position_size_from_risk(
                effective_balance, risk_pct, entry_price, sl_for_size
            )

            # Bug#5 fix : utiliser le win rate réel du RiskManager si disponible
            estimated_win_rate = real_win_rate if real_win_rate is not None else 0.55
            avg_win = rr_ratio * abs(entry_price - sl_for_size)
            avg_loss = abs(entry_price - sl_for_size)

            if avg_loss > 0 and rr_ratio > 0:
                kelly_fraction_raw = calculate_kelly_fraction(estimated_win_rate, avg_win, avg_loss)
                kelly_fraction_applied = min(kelly_fraction_raw * kelly_frac, 0.02)
                position_size = base_size * kelly_fraction_applied
            else:
                position_size = base_size * kelly_frac

        # Mettre à jour l'historique des scores
        self.score_history.append({
            'timestamp': latest.name if hasattr(latest.name, 'isoformat') else datetime.now(),
            'score': total_score,
            'regime': market_regime,
            'trigger_long': trigger_long,
            'trigger_short': trigger_short,
            'rr_ratio': rr_ratio,
            'position_size': position_size,
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
            'is_trending': is_trending,
            'trend_score': trend_score,
            'ranging_score': ranging_score,
            'total_score': total_score,
            'adjusted_score': adjusted_score,
            'score_min': self.score_min,
            'should_long': should_long,
            'should_short': should_short,
            'trigger_long': trigger_long,
            'trigger_short': trigger_short,
            'entry_price': current_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'rr_ratio': rr_ratio,
            'position_size': position_size,
            'risk_amount': risk_amount,
            'sentiment_factor': sentiment_factor,
            'news_filter_passed': news_filter_passed,
            'indicators': self._extract_key_indicators(latest),
            'details': details
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
        """
        Applique les règles de la base de connaissances crescendo :

        Niveau 1 (Murphy) — Filtres de lecture du marché :
          Les règles de type filter=True sont des conditions nécessaires.
          Elles pénalisent le score si les fondations sont absentes.

        Niveau 2 (Elder) — Modificateurs de score :
          Triple Screen, Impulse System, divergences — ajustent le score.

        Niveau 3 (Chan) — Ajusteurs de sizing :
          Kelly, volatility scaling, fat tails — ajustent le sizing mathématique.

        Chaque règle porte un champ 'actions' classifié par le SemanticRuleClassifier.
        """
        adjusted_score = current_score
        adjusted_risk_pct = risk_pct
        adjusted_kelly_frac = kelly_frac
        market_regime = context.get('market_regime', 'UNKNOWN')
        latest_bar = context.get('latest_bar', {})

        for rule_info in self.knowledge_rules:
            rule_id = rule_info.get("id", "?")
            rule_level = rule_info.get("level", 2)
            actions = rule_info.get("actions", [])

            for action_info in actions:
                action = action_info.get("action", "")
                modifier = action_info.get("modifier", 0)

                # ── NIVEAU 1 & 2 — GESTION DU RISQUE ──────────────────────
                if action == "CAP_KELLY":
                    original = adjusted_kelly_frac
                    adjusted_kelly_frac = min(adjusted_kelly_frac, modifier)
                    if original != adjusted_kelly_frac:
                        log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → CAP_KELLY → {adjusted_kelly_frac}")

                elif action == "CAP_RISK_PCT":
                    original = adjusted_risk_pct
                    adjusted_risk_pct = min(adjusted_risk_pct, modifier)
                    if original != adjusted_risk_pct:
                        log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → CAP_RISK_PCT → {adjusted_risk_pct}%")

                # ── NIVEAU 1 & 2 — BONUS DE SCORE PAR RÉGIME ─────────────
                elif action == "BONUS_SCORE_RANGING":
                    if market_regime == 'RANGING':
                        adjusted_score += modifier
                        log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → +{modifier} (RANGING, score={adjusted_score:.1f})")
                    elif market_regime == 'TRENDING':
                        # Pénaliser les stratégies de range en tendance
                        adjusted_score -= modifier * 0.5

                elif action == "BONUS_SCORE_TRENDING":
                    if market_regime == 'TRENDING':
                        adjusted_score += modifier
                        log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → +{modifier} (TRENDING, score={adjusted_score:.1f})")

                # ── NIVEAU 1 & 2 — EMA SQUEEZE ───────────────────────────
                elif action == "BONUS_EMA_SQUEEZE":
                    close = latest_bar.get('close', 0)
                    ema_fast = latest_bar.get('ema_fast', 0)
                    if close > 0 and ema_fast > 0:
                        diff_pct = abs(close - ema_fast) / close
                        if diff_pct < 0.0015:
                            adjusted_score += modifier
                            log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → EMA Squeeze +{modifier}")

                # ── NIVEAU 1 & 2 — PÉNALITÉ CONTRE-TENDANCE ─────────────
                elif action == "PENALTY_COUNTER_TREND":
                    is_trending = context.get('is_trending', False)
                    trigger_long = context.get('trigger_long', False)
                    trigger_short = context.get('trigger_short', False)
                    # Détecter si le signal est contre-tendance
                    trend_up = self.indicators.is_uptrend if hasattr(self.indicators, 'is_uptrend') else lambda x: False
                    ema_fast_v = latest_bar.get('ema_fast', 0)
                    ema_slow_v = latest_bar.get('ema_slow', 0)
                    if is_trending:
                        bullish_trend = ema_fast_v > ema_slow_v
                        if (trigger_short and bullish_trend) or (trigger_long and not bullish_trend):
                            adjusted_score += modifier  # modifier est négatif
                            log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → PENALTY_COUNTER_TREND {modifier}")

                # ── NIVEAU 2 — CONFIRMATION VOLUME ───────────────────────
                elif action == "REQUIRE_VOLUME_CONFIRM":
                    # Si le volume n'est pas au-dessus de la moyenne, pénaliser légèrement
                    volume = latest_bar.get('volume', 0)
                    volume_ma = latest_bar.get('volume_ma', volume)  # fallback = volume actuel
                    if volume_ma > 0 and volume < volume_ma * 1.2:
                        adjusted_score -= 0.3
                        log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → Volume insuffisant -0.3")

                # ── NIVEAU 2 — MULTI-TIMEFRAME ────────────────────────────
                elif action == "ENFORCE_MULTI_TIMEFRAME":
                    # Vérifier l'alignement HTF si disponible
                    ema_htf = latest_bar.get('ema_htf', 0)
                    ema_d1 = latest_bar.get('ema_d1', 0)
                    if ema_htf > 0 and ema_d1 > 0:
                        ema_fast_v = latest_bar.get('ema_fast', 0)
                        ema_slow_v = latest_bar.get('ema_slow', 0)
                        htf_bullish = ema_htf > ema_d1
                        trend_bullish = ema_fast_v > ema_slow_v
                        if htf_bullish != trend_bullish:  # Misalignement HTF
                            adjusted_score -= 1.0
                            log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → HTF misaligned -1.0")

                # ── NIVEAU 3 — REJET SANS EDGE (Kelly < 0) ───────────────
                elif action == "REJECT_NEGATIVE_KELLY":
                    # Calculer rapidement si Kelly est négatif
                    total_score_val = context.get('total_score', 0)
                    if total_score_val <= 0:
                        adjusted_score = -99  # Force le rejet du trade
                        log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → Pas d'edge → rejet")

                # ── NIVEAU 3 — SCALING PAR VOLATILITÉ ────────────────────
                elif action == "SCALE_SIZE_BY_VOLATILITY":
                    atr = latest_bar.get('atr', 0)
                    close = latest_bar.get('close', 1)
                    if atr > 0 and close > 0:
                        atr_pct = atr / close
                        if atr_pct > 0.03:  # ATR > 3% du prix = haute volatilité
                            adjusted_kelly_frac *= modifier  # Réduire de 50%
                            log.debug(f"🧠 [Niv.{rule_level}][{rule_id}] → Vol élevée → kelly * {modifier}")

                # ── FLAGS (loggues, pas de changement de parametres) ──────
                elif action in ("ENFORCE_STRICT_SL", "PSYCHOLOGY_FLAG"):
                    pass  # Acknowledged -- no direct parameter change

                # ── NOUVELLES ACTIONS (Livres 4-11) ──────────────────────

                # ── CONTRARIAN SIGNAL (Montier, Contrarian Trading) ───────
                elif action == "CONTRARIAN_SIGNAL":
                    # Bonus si conditions contrarian : RSI extremes + regime ranging
                    rsi = latest_bar.get('rsi', 50)
                    if market_regime == 'RANGING':
                        is_extreme = rsi < 25 or rsi > 75
                        if is_extreme:
                            adjusted_score += modifier
                            log.debug(f"[Niv.{rule_level}][{rule_id}] CONTRARIAN_SIGNAL RSI={rsi:.0f} +{modifier}")

                # ── VOLATILITY BREAKOUT (Kabbaj, Volman) ─────────────────
                elif action == "VOLATILITY_BREAKOUT":
                    # Bonus si BB squeeze detecte (bb_width_pct < percentile bas)
                    bb_width = latest_bar.get('bb_width', 0)
                    bb_width_pct = latest_bar.get('bb_width_pct', 0.5)
                    if bb_width > 0 and bb_width_pct < 0.20:  # dans les 20% les plus etroits
                        adjusted_score += modifier
                        log.debug(f"[Niv.{rule_level}][{rule_id}] VOLATILITY_BREAKOUT squeeze +{modifier}")

                # ── CRYPTO FUNDAMENTAL (Burniske) ─────────────────────────
                elif action == "CRYPTO_FUNDAMENTAL_FILTER":
                    # Informatif : si l'instrument est crypto, appliquer le filtre
                    symbol = context.get('symbol', '')
                    is_crypto = any(c in symbol.upper() for c in ['BTC', 'ETH', 'BNB', 'USDT', 'SOL'])
                    if is_crypto:
                        adjusted_score += modifier * 0.5  # influence moderee
                        log.debug(f"[Niv.{rule_level}][{rule_id}] CRYPTO_FUNDAMENTAL_FILTER applied")

                # ── ML CONFIDENCE BOOST (Jansen, Bissette) ───────────────
                elif action == "ML_CONFIDENCE_BOOST":
                    # Bonus si composite score depasse le seuil de confiance
                    ml_confidence = context.get('ml_confidence', 0)
                    if ml_confidence > 0.65:
                        boost = modifier * ml_confidence
                        adjusted_score += boost
                        log.debug(f"[Niv.{rule_level}][{rule_id}] ML_CONFIDENCE {ml_confidence:.2f} +{boost:.2f}")

                # ── BEHAVIORAL BIAS PENALTY (Montier, Steenbarger) ────────
                elif action == "BEHAVIORAL_BIAS_PENALTY":
                    # Penalite si overconfidence detectee (win streak recente)
                    recent_wins = context.get('recent_consecutive_wins', 0)
                    if recent_wins >= 5:
                        adjusted_kelly_frac *= 0.75  # Reduire de 25% (surconfiance)
                        log.debug(f"[Niv.{rule_level}][{rule_id}] OVERCONFIDENCE {recent_wins} wins, kelly*0.75")
                    adjusted_score += modifier  # Penalite generale pour biais detecte

                # ── LOSING STREAK PROTECTION (Steenbarger) ────────────────
                elif action == "LOSING_STREAK_PROTECTION":
                    consecutive_losses = context.get('consecutive_losses', 0)
                    if consecutive_losses >= 3:
                        # Reduire la taille proportionnellement aux pertes consecutives
                        reduction = min(modifier * (consecutive_losses / 3), modifier)
                        adjusted_kelly_frac *= reduction
                        log.debug(f"[Niv.{rule_level}][{rule_id}] LOSING_STREAK {consecutive_losses}x kelly*{reduction:.2f}")

        return adjusted_score, adjusted_risk_pct, adjusted_kelly_frac


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

    def _calculate_trending_score(self, df: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
        """
        Calcule le score pour un marché en tendance (basé sur les deux bots existants).

        Returns:
            Tuple de (score, détails)
        """
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        score = 0
        details = {}

        # 1. EMA croisée (prix vs EMA50 ou EMA9/21 cross) - 1 point
        ema_fast = latest.get('ema_fast', 0)
        ema_slow = latest.get('ema_slow', 0)
        price = latest['close']
        ema_cross_bullish = ema_fast > ema_slow
        ema_cross_bearish = ema_fast < ema_slow
        price_above_ema = price > ema_slow
        price_below_ema = price < ema_slow

        # Dans une tendance haussière, on veut prix > EMA lente et EMA rapide > EMA lente
        # Dans une tendance baissière, on veut prix < EMA lente et EMA rapide < EMA lente
        if self.indicators.is_uptrend(df):
            if price_above_ema and ema_cross_bullish:
                score += 1
                details['ema_cross'] = 1
            else:
                details['ema_cross'] = 0
        elif self.indicators.is_downtrend(df):
            if price_below_ema and ema_cross_bearish:
                score += 1
                details['ema_cross'] = 1
            else:
                details['ema_cross'] = 0
        else:
            details['ema_cross'] = 0

        # 2. Prix vs EMA200 (tendance de long terme) - 1 point
        ema_trend = latest.get('ema_trend', 0)
        if self.indicators.is_uptrend(df):
            if price > ema_trend:
                score += 1
                details['price_vs_ema200'] = 1
            else:
                details['price_vs_ema200'] = 0
        elif self.indicators.is_downtrend(df):
            if price < ema_trend:
                score += 1
                details['price_vs_ema200'] = 1
            else:
                details['price_vs_ema200'] = 0
        else:
            details['price_vs_ema200'] = 0

        # 3. Alignement HTF (EMA50 4h > EMA50 daily) - 1 point
        ema_htf = latest.get('ema_htf', 0)  # EMA 50 sur timeframe supérieur
        ema_d1 = latest.get('ema_d1', 0)    # EMA 50 daily
        if ema_htf > 0 and ema_d1 > 0:
            htf_aligned = ema_htf > ema_d1 if self.indicators.is_uptrend(df) else ema_htf < ema_d1
            if htf_aligned:
                score += 1
                details['htf_alignment'] = 1
            else:
                details['htf_alignment'] = 0
        else:
            details['htf_alignment'] = 0

        # 4. MACD croisée - 1 point
        macd = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        macd_cross_bullish = macd > macd_signal and prev.get('macd', 0) <= prev.get('macd_signal', 0)
        macd_cross_bearish = macd < macd_signal and prev.get('macd', 0) >= prev.get('macd_signal', 0)

        if self.indicators.is_uptrend(df):
            if macd_cross_bullish or (macd > 0 and macd_signal > 0):
                score += 1
                details['macd_cross'] = 1
            else:
                details['macd_cross'] = 0
        elif self.indicators.is_downtrend(df):
            if macd_cross_bearish or (macd < 0 and macd_signal < 0):
                score += 1
                details['macd_cross'] = 1
            else:
                details['macd_cross'] = 0
        else:
            details['macd_cross'] = 0

        # 5. Supertrend direction - 1 point
        supertrend_trend = latest.get('supertrend_trend', 0)
        if self.indicators.is_uptrend(df):
            if supertrend_trend > 0:
                score += 1
                details['supertrend'] = 1
            else:
                details['supertrend'] = 0
        elif self.indicators.is_downtrend(df):
            if supertrend_trend < 0:
                score += 1
                details['supertrend'] = 1
            else:
                details['supertrend'] = 0
        else:
            details['supertrend'] = 0

        # 6. ADX strength (confirmation de tendance) - 1 point
        adx = latest.get('adx', 0)
        adx_threshold = self.config.get('ADX_TREND', 22.0)
        if adx > adx_threshold:
            score += 1
            details['adx_strength'] = 1
        else:
            details['adx_strength'] = 0

        # 7. DI+ > DI- (pour tendance haussière) ou DI- > DI+ (pour tendance baissière) - 1 point
        plus_di = latest.get('plus_di', 0)
        minus_di = latest.get('minus_di', 0)
        if self.indicators.is_uptrend(df):
            if plus_di > minus_di:
                score += 1
                details['trend_momentum'] = 1
            else:
                details['trend_momentum'] = 0
        elif self.indicators.is_downtrend(df):
            if minus_di > plus_di:
                score += 1
                details['trend_momentum'] = 1
            else:
                details['trend_momentum'] = 0
        else:
            details['trend_momentum'] = 0

        # 8. Chaikin Money Flow ou MFI confirmation (volume) - 1 point bonus
        mfi = latest.get('mfi', 50)
        if self.indicators.is_uptrend(df):
            if mfi > 50:  # Pression d'achat
                score += 1
                details['volume_confirmation'] = 1
            else:
                details['volume_confirmation'] = 0
        elif self.indicators.is_downtrend(df):
            if mfi < 50:  # Pression de vente
                score += 1
                details['volume_confirmation'] = 1
            else:
                details['volume_confirmation'] = 0
        else:
            details['volume_confirmation'] = 0

        # 9. Alexander Elder Impulse System confirmation - 1 point bonus
        elder_impulse = latest.get('elder_impulse', 0)
        if self.indicators.is_uptrend(df):
            if elder_impulse == 1:  # Vert (EMA13 en hausse et MACD histogramme en hausse)
                score += 1
                details['elder_impulse_confirm'] = 1
            else:
                details['elder_impulse_confirm'] = 0
        elif self.indicators.is_downtrend(df):
            if elder_impulse == -1:  # Rouge (EMA13 en baisse et MACD histogramme en baisse)
                score += 1
                details['elder_impulse_confirm'] = 1
            else:
                details['elder_impulse_confirm'] = 0
        else:
            details['elder_impulse_confirm'] = 0

        # 9-10. Bonus pour divergences
        rsi_div_bull = latest.get('rsi_divergence_bullish', False)
        rsi_div_bear = latest.get('rsi_divergence_bearish', False)
        macd_div_bull = latest.get('macd_divergence_bullish', False)
        macd_div_bear = latest.get('macd_divergence_bearish', False)
        obv_div_bull = latest.get('obv_divergence_bullish', False)
        obv_div_bear = latest.get('obv_divergence_bearish', False)

        bonus_score = 0
        if self.indicators.is_uptrend(df):
            if rsi_div_bull or macd_div_bull or obv_div_bull:
                bonus_score += 1
        elif self.indicators.is_downtrend(df):
            if rsi_div_bear or macd_div_bear or obv_div_bear:
                bonus_score += 1

        # Deuxième bonus: tendance forte avec ADX élevé
        if adx > 25:  # ADX très fort
            bonus_score += 1

        score += bonus_score
        details['divergence_bonus'] = bonus_score

        # S'assurer que le score ne dépasse pas 10
        score = min(score, 10)

        return score, details

    def _calculate_ranging_score(self, df: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
        """
        Calcule le score pour un marché en range (basé sur les deux bots existants).

        Returns:
            Tuple de (score, détails)
        """
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        score = 0
        details = {}

        # 1. Rejet RSI (RSI < 30 pour achat, RSI > 70 pour vente)
        rsi = latest.get('rsi', 50)
        rsi_ob = self.config.get('RSI_OB', 70)
        rsi_os = self.config.get('RSI_OS', 30)

        rsi_oversold = rsi < rsi_os
        rsi_overbought = rsi > rsi_ob

        details['rsi_extreme'] = 1 if (rsi_oversold or rsi_overbought) else 0

        # 2. Stoch RSI croisement
        stoch_k = latest.get('stoch_k', 50)
        stoch_d = latest.get('stoch_d', 50)
        stoch_k_prev = prev.get('stoch_k', 50)
        stoch_d_prev = prev.get('stoch_d', 50)

        stoch_cross_up = stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev
        stoch_cross_down = stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev

        details['stoch_rsi_cross'] = 1 if (stoch_cross_up or stoch_cross_down) else 0

        # 3. Position vs BB Middle - 1 point
        bb_middle = latest.get('bb_middle', 0)
        bb_upper = latest.get('bb_upper', 0)
        bb_lower = latest.get('bb_lower', 0)
        price = latest['close']

        bb_position = (price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        if 0.2 <= bb_position <= 0.8:
            score += 1
            details['bb_position'] = 1
        else:
            details['bb_position'] = 0

        # 4. Chandeliers Price Action - 1 point
        candle_signal = self._detect_candlestick_pattern(df)
        if candle_signal != 0:
            score += 1
            details['price_action'] = 1
        else:
            details['price_action'] = 0

        # 5. Proximité S/R - 1 point
        support, resistance = self.indicators.get_support_resistance_levels(df, lookback=20)
        price_near_support = self.indicators.is_price_near_level(price, support, threshold_pct=0.002)
        price_near_resistance = self.indicators.is_price_near_level(price, resistance, threshold_pct=0.002)

        if price_near_support or price_near_resistance:
            score += 1
            details['sr_proximity'] = 1
        else:
            details['sr_proximity'] = 0

        # 6. Croisement histogramme MACD - 1 point
        macd_hist = latest.get('macd_histogram', 0)
        macd_hist_prev = prev.get('macd_histogram', 0)
        macd_hist_cross = (macd_hist > 0 and macd_hist_prev <= 0) or (macd_hist < 0 and macd_hist_prev >= 0)

        if macd_hist_cross:
            score += 1
            details['macd_hist_cross'] = 1
        else:
            details['macd_hist_cross'] = 0

        # 7. Épuisement volume MFI - 1 point
        mfi = latest.get('mfi', 50)
        mfi_exhaustion_high = mfi > 80
        mfi_exhaustion_low = mfi < 20

        if mfi_exhaustion_high or mfi_exhaustion_low:
            score += 1
            details['mfi_exhaustion'] = 1
        else:
            details['mfi_exhaustion'] = 0

        # 8. Proximité pivots - 1 point
        if len(df) >= 2:
            prev_high = df.iloc[-2]['high']
            prev_low = df.iloc[-2]['low']
            prev_close = df.iloc[-2]['close']
            pivots = self.indicators.calculate_pivot_points(prev_high, prev_low, prev_close)
            pivot_levels = [pivots['pivot'], pivots['r1'], pivots['s1'], pivots['r2'], pivots['s2']]

            near_pivot = any(self.indicators.is_price_near_level(price, level, threshold_pct=0.0015)
                           for level in pivot_levels)

            if near_pivot:
                score += 1
                details['pivot_proximity'] = 1
            else:
                details['pivot_proximity'] = 0
        else:
            details['pivot_proximity'] = 0

        # 9-10. Bonus pour divergences
        rsi_div_bull = latest.get('rsi_divergence_bullish', False)
        rsi_div_bear = latest.get('rsi_divergence_bearish', False)
        macd_div_bull = latest.get('macd_divergence_bullish', False)
        macd_div_bear = latest.get('macd_divergence_bearish', False)
        obv_div_bull = latest.get('obv_divergence_bullish', False)
        obv_div_bear = latest.get('obv_divergence_bearish', False)

        bonus_score = 0
        if price_near_support and (rsi_div_bull or macd_div_bull or obv_div_bull):
            bonus_score += 1
        elif price_near_resistance and (rsi_div_bear or macd_div_bear or obv_div_bear):
            bonus_score += 1

        # Deuxième bonus: compression de volatilité (Bandwidth des BB faible)
        bb_width = latest.get('bb_width', 1)
        if bb_width < 0.02:
            bonus_score += 1

        score += bonus_score
        details['divergence_bonus'] = bonus_score

        # S'assurer que le score ne dépasse pas 10
        score = min(score, 10)

        return score, details

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

    def _check_entry_triggers(self, df: pd.DataFrame, is_trending: bool) -> Tuple[bool, bool]:
        """
        Vérifie les conditions de déclenchement pour entrer en position.
        """
        if len(df) < 2:
            return False, False

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        trigger_long = False
        trigger_short = False

        if is_trending:
            if self.indicators.is_uptrend(df):
                ema_cross = (latest.get('ema_fast', 0) > latest.get('ema_slow', 0) and
                           prev.get('ema_fast', 0) <= prev.get('ema_slow', 0))
                macd_cross = (latest.get('macd', 0) > latest.get('macd_signal', 0) and
                            prev.get('macd', 0) <= prev.get('macd_signal', 0))
                supertrend_up = latest.get('supertrend_trend', 0) > 0 and prev.get('supertrend_trend', 0) <= 0

                # Pullback event: price touched EMA_slow and closed above it, while trend is still up
                pullback_long = (latest.get('ema_fast', 0) > latest.get('ema_slow', 0) and
                                 prev['low'] <= prev.get('ema_slow', 0) and
                                 latest['close'] > latest.get('ema_slow', 0) and
                                 latest.get('supertrend_trend', 0) > 0 and
                                 latest.get('rsi', 50) < 65)  # Avoid buying when overextended

                # --- RÈGLES ALEXANDER ELDER ---
                # Ne jamais acheter si le système d'impulsion est rouge (tendance et momentum contraires)
                elder_allow_long = latest.get('elder_impulse', 0) != -1
                # Bug#3 fix : elder_screen1_ok est True SEULEMENT si l'indicateur existe ET est positif
                # Si l'indicateur est absent, on ne bloque pas mais on ne le valide pas non plus
                _screen1_val = latest.get('elder_screen1_up', None)
                elder_screen1_ok = (_screen1_val is None) or bool(_screen1_val)

                trigger_long = (ema_cross or macd_cross or supertrend_up or pullback_long) and elder_allow_long and elder_screen1_ok

            elif self.indicators.is_downtrend(df):
                ema_cross = (latest.get('ema_fast', 0) < latest.get('ema_slow', 0) and
                           prev.get('ema_fast', 0) >= prev.get('ema_slow', 0))
                macd_cross = (latest.get('macd', 0) < latest.get('macd_signal', 0) and
                            prev.get('macd', 0) <= prev.get('macd_signal', 0))
                supertrend_down = latest.get('supertrend_trend', 0) < 0 and prev.get('supertrend_trend', 0) >= 0

                # Pullback event: price touched EMA_slow and closed below it, while trend is still down
                pullback_short = (latest.get('ema_fast', 0) < latest.get('ema_slow', 0) and
                                  prev['high'] >= prev.get('ema_slow', 0) and
                                  latest['close'] < latest.get('ema_slow', 0) and
                                  latest.get('supertrend_trend', 0) < 0 and
                                  latest.get('rsi', 50) > 35)  # Avoid selling when oversold

                # --- RÈGLES ALEXANDER ELDER ---
                # Ne jamais vendre si le système d'impulsion est vert (tendance et momentum contraires)
                elder_allow_short = latest.get('elder_impulse', 0) != 1
                # Bug#3 fix : même logique de sécurité pour l'écran baissier
                _screen1_down_val = latest.get('elder_screen1_down', None)
                elder_screen1_ok = (_screen1_down_val is None) or bool(_screen1_down_val)

                trigger_short = (ema_cross or macd_cross or supertrend_down or pullback_short) and elder_allow_short and elder_screen1_ok
        else:
            rsi = latest.get('rsi', 50)
            rsi_prev = prev.get('rsi', 50)
            rsi_os = self.config.get('RSI_OS', 30)
            rsi_ob = self.config.get('RSI_OB', 70)
            
            stoch_k = latest.get('stoch_k', 50)
            stoch_k_prev = prev.get('stoch_k', 50)

            # Événements de croisement pour le range (sortie de zone extrême)
            rsi_cross_up = rsi > rsi_os and rsi_prev <= rsi_os
            stoch_cross_up = stoch_k > 20 and stoch_k_prev <= 20
            
            rsi_cross_down = rsi < rsi_ob and rsi_prev >= rsi_ob
            stoch_cross_down = stoch_k < 80 and stoch_k_prev >= 80

            candle_bullish = self._detect_candlestick_pattern(df) == 1
            candle_bearish = self._detect_candlestick_pattern(df) == -1

            support, resistance = self.indicators.get_support_resistance_levels(df)
            near_support = self.indicators.is_price_near_level(latest['close'], support, threshold_pct=0.003)
            near_resistance = self.indicators.is_price_near_level(latest['close'], resistance, threshold_pct=0.003)

            # --- RÈGLES THAMI KABBAJ (Squeeze Breakout) ---
            kabbaj_squeeze_breakout_long = prev.get('kabbaj_squeeze', False) and latest['close'] > latest.get('bb_upper', 0)
            kabbaj_squeeze_breakout_short = prev.get('kabbaj_squeeze', False) and latest['close'] < latest.get('bb_lower', 0)

            # Bug#4 fix : parenthèses explicites + filtre volume obligatoire sur le squeeze Kabbaj
            # Sans parenthèses, Python évaluait : (A and B) or C — le squeeze seul suffisait à entrer
            volume = latest.get('volume', 0)
            volume_ma = latest.get('volume_ma', volume)
            volume_above_avg = volume >= volume_ma * 1.1 if volume_ma > 0 else True

            kabbaj_squeeze_breakout_long = kabbaj_squeeze_breakout_long and volume_above_avg
            kabbaj_squeeze_breakout_short = kabbaj_squeeze_breakout_short and volume_above_avg

            if ((rsi_cross_up or stoch_cross_up) and (candle_bullish or near_support)) or kabbaj_squeeze_breakout_long:
                trigger_long = True

            if ((rsi_cross_down or stoch_cross_down) and (candle_bearish or near_resistance)) or kabbaj_squeeze_breakout_short:
                trigger_short = True

        return trigger_long, trigger_short

    def _calculate_potential_rr(self, latest: pd.Series, current_price: float) -> Tuple[float, float, float]:
        """
        Calcule le ratio risque/rendement potentiel basé sur les niveaux ATR.
        """
        atr = latest.get('atr', 0)
        if atr == 0:
            return 0.0, 0.0, 0.0

        sl_mult = self.config.get('SL_ATR_MULT', 1.5)
        tp_mult = self.config.get('TP_ATR_MULT', 3.0)

        sl_price = current_price - (atr * sl_mult)
        tp_price = current_price + (atr * tp_mult)

        risk = current_price - sl_price
        reward = tp_price - current_price

        if risk <= 0:
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
