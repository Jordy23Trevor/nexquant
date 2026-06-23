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

        # Historique des scores pouranalyse
        self.score_history: List[Dict[str, Any]] = []

        # Seuils configurables
        self.score_min = config.get('SCORE_MIN', 6)  # Score minimum pour entrer
        self.risk_per_trade = config.get('RISK_PCT', 1.0)  # % du compte à risquer par trade
        self.kelly_fraction = config.get('KELLY_FRACTION', 0.25)  # Fraction de Kelly à utiliser

        # Charger la base de connaissances dynamique (connaissances extraites des livres)
        try:
            from resources.learning_engine import load_knowledge_index
            raw_rules = load_knowledge_index()
            log.info(f"Chargé {len(raw_rules)} règles brutes de la base de connaissances.")
        except Exception as e:
            raw_rules = []
            log.warning(f"Impossible de charger la base de connaissances dynamiques : {e}")

        # Classifier sémantiquement les règles (NLP ou fallback mots-clés)
        if _SEMANTIC_AVAILABLE and raw_rules:
            try:
                self._classifier = SemanticRuleClassifier()
                # Charger le cache si disponible, sinon classifier et sauvegarder
                cached = self._classifier.load_cache()
                if cached and len(cached) == len(raw_rules):
                    self.knowledge_rules = cached
                    log.info(f"Règles chargées depuis le cache sémantique ({len(cached)} règles).")
                else:
                    self.knowledge_rules = self._classifier.classify_rules(raw_rules)
                    self._classifier.save_cache(self.knowledge_rules)
            except Exception as e:
                log.warning(f"Classificateur sémantique en erreur ({e}), utilisation des règles brutes.")
                self.knowledge_rules = raw_rules
        else:
            self.knowledge_rules = raw_rules

        log.info(f"TradingStrategy initialisée avec score_min={self.score_min}, risk_per_trade={self.risk_per_trade}%")

    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse complète du marché pour générer un signal de trading.

        Args:
            df: DataFrame avec données OHLCV brutes

        Returns:
            Dictionnaire contenant l'analyse complète et le signal de trading
        """
        if len(df) < 50:  # Minimum de données nécessaires pour les indicateurs
            log.warning(f"Données insuffisantes pour l'analyse: {len(df)} barres")
            return self._create_neutral_signal("INSUFFICIENT_DATA")

        # Calculer tous les indicateurs
        df_with_indicators = self.indicators.calculate_all_indicators(df.copy())

        # Obtenir les valeurs les plus récentes
        latest = df_with_indicators.iloc[-1]
        prev = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else latest

        # Déterminer le régime de marché
        market_regime = self.indicators.get_market_regime(df_with_indicators)
        is_trending = market_regime == 'TRENDING'

        # Calculer les scores selon le régime
        if is_trending:
            trend_score, trend_details = self._calculate_trending_score(df_with_indicators)
            ranging_score, ranging_details = 0, {}  # Pas utilisé en tendance
            total_score = trend_score
            details = {**trend_details, 'regime': 'TRENDING'}
        else:
            ranging_score, ranging_details = self._calculate_ranging_score(df_with_indicators)
            trend_score, trend_details = 0, {}  # Pas utilisé en range
            total_score = ranging_score
            details = {**ranging_details, 'regime': 'RANGING'}

        # Vérifier les triggers (conditions d'entrée)
        trigger_long, trigger_short = self._check_entry_triggers(df_with_indicators, is_trending)

        # Calculer le ratio risque/rendement potentiel (LONG par défaut)
        rr_ratio, sl_price, tp_price = self._calculate_potential_rr(df_with_indicators, latest)

        # Ajuster les prix SL/TP si c'est un signal de vente (SHORT) pour qu'ils soient orientés correctement
        if trigger_short and not trigger_long:
            atr = latest.get('atr', 0)
            if atr > 0:
                sl_price = latest['close'] + (atr * self.config.get('SL_ATR_MULT', 1.5))
                tp_price = latest['close'] - (atr * self.config.get('TP_ATR_MULT', 3.0))

        # Appliquer les filtres de sentiment et de nouvelles (à venir dans la phase 4)
        sentiment_factor = 1.0  # À implémenter avec le news manager
        news_filter_passed = True  # À implémenter avec le news manager

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
                'latest_bar': latest
            }
        )

        # Calculer la taille de position basée sur le risque et Kelly
        account_balance = 10000.0  # Valeur par défaut, à remplacer par le vrai solde
        risk_amount = account_balance * (risk_pct / 100.0)

        # Déterminer si on prend le trade
        should_long = (
                adjusted_score >= self.score_min and
                trigger_long and
                rr_ratio >= 2.0 and  # R:R minimum de 2:1
                news_filter_passed
        )

        should_short = (
                adjusted_score >= self.score_min and
                trigger_short and
                rr_ratio >= 2.0 and  # R:R minimum de 2:1
                news_filter_passed
        )

        # Calculer la taille de position si on prend le trade
        position_size = 0.0
        if should_long or should_short:
            entry_price = latest['close']
            # Utiliser le SL calculé pour le potentiel RR, ou un SL par défaut basé sur ATR
            sl_for_size = sl_price if sl_price > 0 else entry_price - (latest['atr'] * self.config.get('SL_ATR_MULT', 1.5))
            tp_for_size = tp_price if tp_price > 0 else entry_price + (latest['atr'] * self.config.get('TP_ATR_MULT', 3.0))

            # Calculer la taille de base basée sur le risque
            base_size = calculate_position_size_from_risk(
                account_balance, risk_pct, entry_price, sl_for_size
            )

            # Appliquer la fraction de Kelly (méthode Kabbaj conservatrice)
            # Pour simplifier, on utilise un win rate estimé basé sur la performance historique
            # Dans une implémentation complète, ceci viendrait d'un suivi de performance
            estimated_win_rate = 0.55  # Estimation conservatrice
            avg_win = rr_ratio * (entry_price - sl_for_size) if sl_for_size < entry_price else (sl_for_size - entry_price) * rr_ratio
            avg_loss = abs(entry_price - sl_for_size)

            if avg_loss > 0 and rr_ratio > 0:
                kelly_fraction_raw = calculate_kelly_fraction(estimated_win_rate, avg_win, avg_loss)
                kelly_fraction_applied = min(kelly_fraction_raw * kelly_frac, 0.02)  # Plafonné à 2% comme dans le plan
                position_size = base_size * kelly_fraction_applied
            else:
                position_size = base_size * kelly_frac  # Fallback

        # Mettre à jour l'historique des scores
        self.score_history.append({
            'timestamp': latest.name if hasattr(latest.name, 'isoformat') else datetime.now(),
            'score': total_score,
            'regime': market_regime,
            'trigger_long': trigger_long,
            'trigger_short': trigger_short,
            'rr_ratio': rr_ratio,
            'position_size': position_size,
            'close_price': latest['close']
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
            'entry_price': latest['close'],
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

    def _apply_knowledge_rules(self, current_score: float, risk_pct: float, kelly_frac: float, context: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Applique les règles de la base de connaissances en utilisant les actions
        pré-classifiées par le SemanticRuleClassifier (NLP ou fallback mots-clés).
        Chaque règle porte un champ 'actions' contenant les catégories matchées.
        """
        adjusted_score = current_score
        adjusted_risk_pct = risk_pct
        adjusted_kelly_frac = kelly_frac

        for rule_info in self.knowledge_rules:
            rule_id = rule_info.get("id", "?")
            actions = rule_info.get("actions", [])

            for action_info in actions:
                action = action_info.get("action", "")
                modifier = action_info.get("modifier", 0)

                # --- GESTION DE RISQUE ---
                if action == "CAP_KELLY":
                    original = adjusted_kelly_frac
                    adjusted_kelly_frac = min(adjusted_kelly_frac, modifier)
                    if original != adjusted_kelly_frac:
                        log.info(f"🧠 NLP [{rule_id}] → CAP_KELLY à {adjusted_kelly_frac} (était {original})")

                elif action == "CAP_RISK_PCT":
                    original = adjusted_risk_pct
                    adjusted_risk_pct = min(adjusted_risk_pct, modifier)
                    if original != adjusted_risk_pct:
                        log.info(f"🧠 NLP [{rule_id}] → CAP_RISK à {adjusted_risk_pct}% (était {original}%)")

                # --- AJUSTEMENT DE SCORE PAR REGIME ---
                elif action == "BONUS_SCORE_RANGING":
                    if context.get('market_regime') == 'RANGING':
                        adjusted_score += modifier
                        log.info(f"🧠 NLP [{rule_id}] → BONUS Ranging +{modifier} (score={adjusted_score:.1f})")
                    elif context.get('market_regime') == 'TRENDING':
                        adjusted_score -= modifier
                        log.info(f"🧠 NLP [{rule_id}] → Pénalité anti-ranging en tendance -{modifier}")

                elif action == "BONUS_SCORE_TRENDING":
                    if context.get('market_regime') == 'TRENDING':
                        adjusted_score += modifier
                        log.info(f"🧠 NLP [{rule_id}] → BONUS Trending +{modifier} (score={adjusted_score:.1f})")

                # --- EMA SQUEEZE ---
                elif action == "BONUS_EMA_SQUEEZE":
                    latest_bar = context.get('latest_bar', {})
                    close = latest_bar.get('close', 0)
                    ema_fast = latest_bar.get('ema_fast', 0)
                    if close > 0 and ema_fast > 0:
                        diff_pct = abs(close - ema_fast) / close
                        if diff_pct < 0.0015:
                            adjusted_score += modifier
                            log.info(f"🧠 NLP [{rule_id}] → EMA Squeeze détecté +{modifier}")

                # --- FLAGS (logged but no parameter change) ---
                elif action in ("ENFORCE_STRICT_SL", "PSYCHOLOGY_FLAG"):
                    pass  # Acknowledged — no score/risk change

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
        ema_fast_slope = latest.get('ema_fast', 0) - prev.get('ema_fast', 0)
        if self.indicators.is_uptrend(df):
            if ema_fast_slope > 0:
                score += 1
                details['trend_momentum'] = 1
            else:
                details['trend_momentum'] = 0
        elif self.indicators.is_downtrend(df):
            if ema_fast_slope < 0:
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

                # --- RÈGLES ALEXANDER ELDER ---
                # Ne jamais acheter si le système d'impulsion est rouge (tendance et momentum contraires)
                elder_allow_long = latest.get('elder_impulse', 0) != -1
                # Tendance de fond Triple Screen (Screen 1) doit être haussière
                elder_screen1_ok = latest.get('elder_screen1_up', True)

                trigger_long = (ema_cross or macd_cross or supertrend_up) and elder_allow_long and elder_screen1_ok

            elif self.indicators.is_downtrend(df):
                ema_cross = (latest.get('ema_fast', 0) < latest.get('ema_slow', 0) and
                           prev.get('ema_fast', 0) >= prev.get('ema_slow', 0))
                macd_cross = (latest.get('macd', 0) < latest.get('macd_signal', 0) and
                            prev.get('macd', 0) >= prev.get('macd_signal', 0))
                supertrend_down = latest.get('supertrend_trend', 0) < 0 and prev.get('supertrend_trend', 0) >= 0

                # --- RÈGLES ALEXANDER ELDER ---
                # Ne jamais vendre si le système d'impulsion est vert (tendance et momentum contraires)
                elder_allow_short = latest.get('elder_impulse', 0) != 1
                # Tendance de fond Triple Screen (Screen 1) doit être baissière
                elder_screen1_ok = latest.get('elder_screen1_down', True)

                trigger_short = (ema_cross or macd_cross or supertrend_down) and elder_allow_short and elder_screen1_ok
        else:
            rsi = latest.get('rsi', 50)
            rsi_os = self.config.get('RSI_OS', 30)
            stoch_k = latest.get('stoch_k', 50)
            stoch_d = latest.get('stoch_d', 50)

            oversold = rsi < rsi_os or (stoch_k < 20 and stoch_d < 20)
            candle_bullish = self._detect_candlestick_pattern(df) == 1

            support, _ = self.indicators.get_support_resistance_levels(df)
            near_support = self.indicators.is_price_near_level(latest['close'], support, threshold_pct=0.003)

            # --- RÈGLES THAMI KABBAJ (Squeeze Breakout) ---
            # Sortie haussière d'une compression de volatilité (Bollinger Bands expansion)
            kabbaj_squeeze_breakout_long = prev.get('kabbaj_squeeze', False) and latest['close'] > latest.get('bb_upper', 0)

            if (oversold and (candle_bullish or near_support)) or kabbaj_squeeze_breakout_long:
                trigger_long = True

            rsi_ob = self.config.get('RSI_OB', 70)
            overbought = rsi > rsi_ob or (stoch_k > 80 and stoch_d > 80)
            candle_bearish = self._detect_candlestick_pattern(df) == -1

            _, resistance = self.indicators.get_support_resistance_levels(df)
            near_resistance = self.indicators.is_price_near_level(latest['close'], resistance, threshold_pct=0.003)

            # --- RÈGLES THAMI KABBAJ (Squeeze Breakout) ---
            # Sortie baissière d'une compression de volatilité
            kabbaj_squeeze_breakout_short = prev.get('kabbaj_squeeze', False) and latest['close'] < latest.get('bb_lower', 0)

            if (overbought and (candle_bearish or near_resistance)) or kabbaj_squeeze_breakout_short:
                trigger_short = True

        return trigger_long, trigger_short

    def _calculate_potential_rr(self, df: pd.DataFrame, latest: pd.Series) -> Tuple[float, float, float]:
        """
        Calcule le ratio risque/rendement potentiel basé sur les niveaux ATR.
        """
        atr = latest.get('atr', 0)
        if atr == 0:
            return 0.0, 0.0, 0.0

        price = latest['close']
        sl_mult = self.config.get('SL_ATR_MULT', 1.5)
        tp_mult = self.config.get('TP_ATR_MULT', 3.0)

        sl_price = price - (atr * sl_mult)
        tp_price = price + (atr * tp_mult)

        risk = price - sl_price
        reward = tp_price - price

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
