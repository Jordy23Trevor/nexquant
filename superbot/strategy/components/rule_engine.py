import logging
import pandas as pd
from typing import Dict, Any, Tuple
log = logging.getLogger("rule_engine")

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