import logging
import time
from datetime import datetime, timezone
from superbot.config import MAX_SPREAD_PIPS, MAX_FOREX_CURRENCY_EXPOSURE, BROKER_TYPE

# BUG-M3 FIX: Imports déplacés depuis la hot path (execute_signal_trade) vers le haut du fichier
from superbot.risk.modules.risk_monitor import _is_night_session
try:
    from superbot.config import SCORE_MIN_NIGHT, NIGHT_SESSION_START_UTC, NIGHT_SESSION_END_UTC
except ImportError:
    SCORE_MIN_NIGHT, NIGHT_SESSION_START_UTC, NIGHT_SESSION_END_UTC = 8, 20, 6

log = logging.getLogger("signal_executor")

def execute_signal_trade(bot, symbol: str, signal_data: dict, df_with_indicators):
    """
    Valide les filtres macro, calcule la taille de position de manière sécurisée et exécute l'ordre.
    """
    bot.stats['signals_generated'] += 1
    log.info(
        f"Signal pour {symbol} : {signal_data['market_regime']} | "
        f"Score: {signal_data['total_score']:.1f} | "
        f"Long: {signal_data['should_long']} | Short: {signal_data['should_short']} | "
        f"RR: {signal_data['rr_ratio']:.2f}"
    )

    # 0. Vérifier le cooldown de l'actif suite à un échec d'exécution
    with bot._state_lock:
        in_cooldown = symbol in bot.failed_execution_cooldowns
        time_since_failure = time.time() - bot.failed_execution_cooldowns.get(symbol, 0) if in_cooldown else 0

    if in_cooldown:
        if time_since_failure < 900:  # 15 minutes cooldown
            log.info(f"🚫 Trade {symbol} rejeté : Cooldown d'échec actif (reste {int(900 - time_since_failure)}s)")
            return
        else:
            with bot._state_lock:
                del bot.failed_execution_cooldowns[symbol]
            bot._save_cooldowns()
            
    # QW-3: Bloquer le pyramidage (Spam BTC) si une position existe déjà
    if bot.positions.get(symbol, {}).get('size', 0) > 0:
        log.info(f"🚫 Trade {symbol} rejeté : Position déjà ouverte (pyramidage bloqué).")
        return

    # ── Audit post-freeze (fix 24/07/2026) ──────────────────────────────────
    # Après un freeze long du cycle (ex: 6h26 à cause d'une erreur DNS),
    # le bot attend N cycles d'observation avant d'ouvrir de nouveaux trades.
    # Ceci évite d'entrer sur un marché qui a drastiquement changé de régime.
    post_freeze_remaining = getattr(bot, '_post_freeze_cooldown_cycles', 0)
    if post_freeze_remaining > 0:
        bot._post_freeze_cooldown_cycles = max(0, post_freeze_remaining - 1)
        log.warning(
            f"🔍 [Post-Freeze] Trade {symbol} rejeté — mode audit actif "
            f"({post_freeze_remaining} cycle(s) restant(s)). "
            f"Le bot observe le marché sans ouvrir de nouvelles positions."
        )
        return
    # ─────────────────────────────────────────────────────────────────────────

    # 0b. Vérifier le Trailing Profit Circuit Breaker (Formulation 2)
    if getattr(bot, '_circuit_breaker_paused', False):
        log.info(f"⏸️ [CircuitBreaker] Trade sur {symbol} rejeté — trading en pause automatique par protection des gains.")
        return

    # 1. Vérifier les filtres de nouvelles et de sentiment
    if getattr(bot, 'news_manager', None):
        should_avoid, news_event = bot.news_manager.should_avoid_trading_due_to_news(symbol)
    else:
        should_avoid, news_event = False, None
    if should_avoid:
        log.info(f"Trading évité pour {symbol} à cause des nouvelles : {news_event.title if news_event else 'Unknown'}")
        return

    # 1b. Filtre de score nocturne (fix sur-exposition 23-24/07/2026) ─────────
    # En session nocturne (20h-06h UTC), exiger un score minimum plus élevé
    # pour éviter les entrées sur des signaux de qualité marginale.

    if _is_night_session(NIGHT_SESSION_START_UTC, NIGHT_SESSION_END_UTC):
        current_score = signal_data.get('total_score', 0)
        if current_score < SCORE_MIN_NIGHT:
            log.info(
                f"🌙 [NightFilter] Trade {symbol} rejeté — score {current_score:.1f} < "
                f"{SCORE_MIN_NIGHT} requis en session nocturne (20h-06h UTC)"
            )
            return
    # ─────────────────────────────────────────────────────────────────────────

    # 2. Récupérer le solde et le prix d'entrée
    # BUG-C2 FIX: get_balance() protégé contre les timeouts réseau/déconnexion broker.
    # En cas d'échec, on utilise le cache du cycle précédent plutôt que de crasher tout le cycle.
    try:
        account_balance = float(bot.broker.get_balance())
        if account_balance <= 0:
            raise ValueError(f"Solde invalide reçu du broker: {account_balance}")
        bot._cached_balance = account_balance
    except Exception as e:
        log.error(f"⚠️ [BUG-C2] get_balance() a échoué pour {symbol}: {e}")
        account_balance = bot._cached_balance
        if account_balance <= 0:
            log.error(f"⚠️ [BUG-C2] Aucun solde disponible (cache vide). Trade {symbol} annulé.")
            return
        log.warning(f"↩️ [BUG-C2] Utilisation du solde cache: {account_balance:.2f} pour {symbol}")
    entry_price = float(signal_data['entry_price'])

    # 2d. Filtres avancés Forex (Session, Spread, Corrélation, Pivots Obstacles, News)
    if bot.broker.get_asset_type() == 'forex':
        from superbot.components.forex_filters import (
            is_market_open, check_spread,
            check_currency_correlation, check_pivot_obstacle,
            check_major_news_window
        )

        # A. Session horaire (H24 Forex : Tokyo + Londres + New York)
        if not is_market_open():
            return

        # B. Garde-fou Spread
        if not check_spread(bot.broker, symbol, MAX_SPREAD_PIPS):
            return

        # C. Corrélation de devises
        cand_side = 'LONG' if signal_data.get('should_long') else 'SHORT'
        if not check_currency_correlation(symbol, bot.positions, MAX_FOREX_CURRENCY_EXPOSURE, cand_side):
            return

        # D. Obstacle pivot
        atr_value = df_with_indicators.iloc[-1].get('atr', 0)
        sl_price, _ = bot.risk_manager.calculate_sl_tp_levels(
            entry_price, atr_value,
            "LONG" if signal_data.get('should_long') else "SHORT",
            asset_type="forex", symbol=symbol
        )
        if not check_pivot_obstacle(entry_price, sl_price, df_with_indicators, signal_data.get('should_long', False), symbol):
            return

        # E. Filtre news économiques majeures (NFP, BCE, FOMC) — NOUVEAU
        avoid_minutes = bot.config.get('FOREX_NEWS_AVOID_MINUTES', 30) if hasattr(bot, 'config') else 30
        news_events = bot.news_manager.get_high_impact_events() if bot.news_manager and hasattr(bot.news_manager, 'get_high_impact_events') else None
        if not check_major_news_window(symbol, avoid_minutes=avoid_minutes, news_events=news_events):
            return


    # 2b. Filtre volume minimum (protection contre le slippage sur actifs illiquides)
    if bot.broker.get_asset_type() == "crypto":
        from superbot.components.crypto_filters import check_crypto_volume
        if not check_crypto_volume(symbol, df_with_indicators):
            return

    # 2c. Filtre de dominance BTC pour les altcoins
    # Ne pas ouvrir un SHORT sur un altcoin si BTC est en tendance haussière forte
    if bot.broker.get_asset_type() == "crypto" and 'BTC' not in symbol.upper():
        btc_symbol = 'BTC/USDT'
        if btc_symbol in bot.market_data and not bot.market_data[btc_symbol].empty:
            btc_df = bot.market_data[btc_symbol]
            btc_last = btc_df.iloc[-1]
            btc_ema_fast = btc_last.get('ema_21', btc_last.get('ema_fast', 0))
            btc_ema_slow = btc_last.get('ema_55', btc_last.get('ema_slow', 0))
            btc_adx = btc_last.get('adx', 0)
            btc_bullish_trend = btc_ema_fast > btc_ema_slow and btc_adx > 25
            btc_bearish_trend = btc_ema_fast < btc_ema_slow and btc_adx > 25

            if signal_data['should_short'] and btc_bullish_trend:
                log.info(f"🚨 Filtre dominance BTC : SHORT {symbol} rejeté — BTC est en tendance haussière forte (ADX={btc_adx:.1f})")
                return
            if signal_data['should_long'] and btc_bearish_trend:
                log.info(f"🚨 Filtre dominance BTC : LONG {symbol} rejeté — BTC est en tendance baissière forte (ADX={btc_adx:.1f})")
                return

    # 2e. Blocage double-filet des SHORTs sur ETF/Stocks (Alpaca)
    # Même si la stratégie laisse passer un SHORT, l'executor bloque en dernière ligne
    if bot.broker.get_asset_type() in ('stock', 'alpaca', 'equity'):
        allow_short = getattr(bot, 'config', {}).get('ALLOW_SHORT_STOCK', False)
        if signal_data.get('should_short') and not allow_short:
            log.info(f"🚫 SHORT {symbol} bloqué au niveau executor (ETF/Stock — ALLOW_SHORT_STOCK=false)")
            return

    # 3. Déterminer le stop loss et take profit via le Risk Manager
    atr_value = float(df_with_indicators.iloc[-1].get('atr', 0))
    if atr_value > 0 and bot.risk_manager:
        position_side = "LONG" if signal_data['should_long'] else "SHORT"
        # ── Phase 3 §2 — Passer le régime HMM pour les multiplicateurs adaptatifs
        # hmm_label est le label HMM détaillé (ex: 'HIGH_VOL_RANGE') stocké dans signal_data
        hmm_label = signal_data.get('hmm_label', signal_data.get('market_regime', ''))
        sl_price, tp_price = bot.risk_manager.calculate_sl_tp_levels(
            entry_price, atr_value, position_side,
            asset_type=bot.broker.get_asset_type(),
            symbol=symbol,
            hmm_regime=hmm_label
        )
    else:
        # Fallback : utiliser les valeurs calculées par la stratégie
        sl_price = signal_data.get('sl_price') or (entry_price * 0.98 if signal_data['should_long'] else entry_price * 1.02)
        tp_price = signal_data.get('tp_price') or (entry_price * 1.04 if signal_data['should_long'] else entry_price * 0.96)

    # BUG-05 FIX: Vérifier les limites de risque AVANT le calcul de position size (corrélation + broker margin)
    # Cela évite des appels API broker coûteux si le trade va être rejeté de toute façon.
    if not bot.risk_manager._can_take_new_trade(account_balance, symbol):
        log.info(f"Limites de risque ou limite par symbole atteintes, pas de nouvel ordre pour {symbol}")
        return

    # ── Phase 3 §4 : Corrélation dynamique avancée ──
    # Bloquer ou réduire la taille si corrélation > 70% avec une position ouverte
    max_open_corr = 0.0
    corr_data = None
    try:
        import pandas as pd
        if len(df_with_indicators) >= 50:
            current_close = df_with_indicators['close'].tail(50)
            current_returns = current_close.pct_change().dropna()
            
            for open_sym, pos in bot.positions.items():
                if open_sym != symbol and pos.get('size', 0) > 0:
                    open_df = bot.market_data.get(open_sym)
                    if open_df is not None and len(open_df) >= 50:
                        open_close = open_df['close'].tail(50)
                        open_returns = open_close.pct_change().dropna()
                        
                        min_len = min(len(current_returns), len(open_returns))
                        if min_len >= 30:
                            corr = current_returns.tail(min_len).corr(open_returns.tail(min_len))
                            
                            # Si sens opposé, corrélation effective inversée
                            prop_side = "LONG" if signal_data.get('should_long') else "SHORT"
                            open_side = pos.get('side', 'LONG').upper()
                            effective_corr = corr if prop_side == open_side else -corr
                            
                            if pd.notna(effective_corr) and effective_corr > max_open_corr:
                                max_open_corr = effective_corr
    except Exception as e:
        log.warning(f"Erreur lors du calcul de corrélation avancée pour {symbol} : {e}")

    if max_open_corr >= 0.90:
        log.info(f"🚫 Trade {symbol} rejeté : Corrélation extrême ({max_open_corr:.2f} >= 0.90) avec une position ouverte.")
        return
    elif max_open_corr > 0.70:
        corr_data = {'average_correlation': max_open_corr}
        log.info(f"⚠️ Corrélation élevée ({max_open_corr:.2f} > 0.70) détectée pour {symbol} : taille sera réduite.")

    # ── CONVICTION BOOST ─────────────────────────────────────────────────────
    # Augmente dynamiquement la taille de position quand TOUTES les conditions
    # suivantes sont réunies, indiquant une opportunité de haute qualité :
    #   1. Score ≥ score_min + 2 (signal très solide, pas juste au seuil)
    #   2. ADX ≥ 30 (tendance forte confirmée)
    #   3. Régime TRENDING (pas de range / pas de haute volatilité chaotique)
    #   4. Corrélation avec les positions ouvertes faible (< 0.70)
    # Le multiplicateur est plafonné à ×1.5 pour rester dans les limites
    # du risk management (le sizing final est toujours borné par la marge dispo).
    conviction_boost = 1.0
    score_raw_val = signal_data.get('total_score', 0)
    # BUG-I2 FIX: score_min peut être None si PerformanceLearner l'a modifié sans mettre à jour strategy.
    # Fallback explicite sur 6 pour éviter TypeError dans la comparaison.
    _raw_score_min = signal_data.get('score_min', None)
    if _raw_score_min is None:
        _raw_score_min = getattr(bot.strategy, 'score_min', None)
    score_min_val = int(_raw_score_min) if _raw_score_min is not None else 6
    adx_val = float(df_with_indicators.iloc[-1].get('adx', 0))
    regime_val = signal_data.get('market_regime', '').upper()

    high_score = score_raw_val >= (score_min_val + 1)
    strong_trend = adx_val >= 25
    trending_regime = 'TRENDING' in regime_val
    low_correlation = max_open_corr < 0.70

    if high_score and strong_trend and trending_regime and low_correlation:
        # Boost progressif selon le niveau du score
        score_excess = score_raw_val - score_min_val
        conviction_boost = min(1.15 + (score_excess * 0.10) + ((adx_val - 25) * 0.008), 1.50)
        log.info(
            f"🚀 [ConvictionBoost] {symbol} — Conditions probabilistes supérieures détectées "
            f"(Score={score_raw_val:.1f}/{score_min_val}, ADX={adx_val:.1f}, Régime={regime_val}). "
            f"Boost de taille : ×{conviction_boost:.2f}"
        )

    # 3. Calculer la taille de position avec le Risk Manager
    position_size, size_details = bot.risk_manager.calculate_position_size(
        account_balance=account_balance,
        entry_price=entry_price,
        stop_loss=sl_price,
        symbol=symbol,
        sentiment_factor=bot.news_manager.get_risk_factor() if bot.news_manager else 1.0,
        correlation_data=corr_data,
        broker=bot.broker,
        hmm_regime=hmm_label  # Phase 3 §1 — dimensionnement selon le régime HMM
    )

    # Appliquer le boost de conviction (après le calcul de base)
    if conviction_boost > 1.0 and position_size > 0:
        size_before_boost = position_size
        boosted_size = position_size * conviction_boost
        # BUG-16 FIX: Le boost sera cappé par max_size_by_margin dans position_sizer
        # On logue la taille demandée vs ce qui sera réellement appliqué après le sizing final
        # BUG-A10 FIX: Re-capper après boost par MAX_POSITION_SIZE pour éviter les ordres surdimensionnés
        boosted_size = min(boosted_size, bot.risk_manager.MAX_POSITION_SIZE)
        log.info(
            f"[ConvictionBoost] Taille {symbol} demandée : {size_before_boost:.6f} × {conviction_boost:.2f} = "
            f"{boosted_size:.6f} (cappé à MAX_POSITION_SIZE={bot.risk_manager.MAX_POSITION_SIZE})"
        )
        position_size = boosted_size

    log.info(f"Risk sizing {symbol}: size={position_size:.6f} | details={size_details}")

    if position_size <= 0:
        log.debug(f"Taille de position nulle ou rejetée pour {symbol}, pas d'action")
        return

    log.info(f"Taille de position calculée pour {symbol} : {position_size:.6f} | Risque : {size_details.get('actual_risk_pct', 0.0):.2f}% du compte")

    # 4. (Anciennement) Vérification des limites de risque globales — maintenant effectuée AVANT le sizing (BUG-05 FIX)
    # La vérification a déjà eu lieu à la ligne 180, on ne la répète pas ici.

    # 5. Exécuter le trade chez le courtier
    side = "buy" if signal_data['should_long'] else "sell"
    log.info(f"Exécution du trade : {side.upper()} {position_size:.6f} {symbol} @ {entry_price:.4f} | SL: {sl_price:.4f} | TP: {tp_price:.4f}")

    # Placer l'ordre
    try:
        order_result = bot.broker.place_order(
            symbol=symbol,
            side=side,
            amount=position_size,
            sl=sl_price,
            tp=tp_price,
            comment=f"SuperBot signal - {signal_data['market_regime']} - Score:{signal_data['total_score']:.1f}"
        )
    except Exception as e:
        log.error(f"⚠️ Chaos intercepté : Exception lors du placement d'ordre pour {symbol} : {e}")
        order_result = None

    if order_result:
        bot.stats['trades_executed'] += 1
        log.info(f"Trade exécuté avec succès pour {symbol}")
        
        # ── Phase 3.3 : Alimentation Prometheus ──────────────────────────────
        if getattr(bot, 'prometheus', None):
            try:
                bot.prometheus.bot_trades_executed_total.labels(
                    symbol=symbol,
                    side=side.upper()
                ).inc()
            except Exception as e:
                log.debug(f"Erreur incrémentation métrique trades_executed: {e}")

        # Collecter les features techniques pour l'entraînement ultérieur du ML
        latest_row = df_with_indicators.iloc[-1]
        close = latest_row.get('close', 1)
        bb_upper = latest_row.get('bb_upper', close * 1.01)
        bb_lower = latest_row.get('bb_lower', close * 0.99)
        bb_pos = (close - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
        atr_pct = (latest_row.get('atr', 0) / close) * 100 if close > 0 else 0

        features_dict = {
            'rsi': float(latest_row.get('rsi', 50)),
            # ── Fix P4 — La colonne s'appelle 'macd_histogram' dans TechnicalIndicators,
            # mais le trade log utilisait 'macd_hist' (toujours 0).
            'macd_hist': float(latest_row.get('macd_histogram', latest_row.get('macd_hist', 0))),
            'adx': float(latest_row.get('adx', 20)),
            'bb_pos': float(bb_pos),
            'atr_pct': float(atr_pct)
        }

        # Enregistrer le trade pour le suivi du risque
        trade_record = {
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'position_size': position_size,
            'stop_loss': sl_price,
            'take_profit': tp_price,
            'initial_risk_amount': abs(entry_price - sl_price) * position_size,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'signal_score': signal_data['total_score'],
            'market_regime': signal_data['market_regime'],
            'broker': BROKER_TYPE
        }
        # Inclure les indicateurs pour le Walk-Forward et la traçabilité des paramètres
        trade_record.update(features_dict)
        # Log les paramètres actifs de la stratégie
        trade_record['score_min'] = float(bot.strategy.config.get('SCORE_MIN', 6))
        trade_record['RSI_OB'] = float(bot.strategy.config.get('RSI_OB', 70))
        trade_record['ADX_TREND'] = float(bot.strategy.config.get('ADX_TREND', 25))

        bot.risk_manager.record_trade(trade_record)

        # Mettre à jour la position suivie
        bot._update_position_tracking(symbol, side, position_size, entry_price, sl_price, tp_price,
                                        market_regime=signal_data.get('market_regime', 'UNKNOWN'),
                                        features=features_dict)

    else:
        log.error(f"Échec de l'exécution du trade pour {symbol}. Activation du cooldown de 15 minutes.")
        with bot._state_lock:
            bot.failed_execution_cooldowns[symbol] = time.time()
        bot._save_cooldowns()
