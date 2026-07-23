import time
import traceback
import logging

log = logging.getLogger('symbol_processor')

def process_symbol(bot, symbol: str):
    """
    Traite un symbole spécifique : récupère les données, analyse, génère des signaux, exécute des trades.

    Args:
        symbol: Symbole à traiter (ex: BTC/USDT)
    """
    try:
        # Mesurer le temps de traitement total pour profiling
        symbol_start_time = time.time()

        # 1. Récupérer les données de marché récentes
        fetch_start = time.time()
        df = bot._fetch_market_data(symbol)
        fetch_time = time.time() - fetch_start
        if df is None or len(df) < 50:  # Minimum de données nécessaires
            log.debug(f"Données insuffisantes pour {symbol} : {len(df) if df is not None else 0} barres")
            return

        # Vérifier si nous avons réellement de nouvelles données depuis le dernier traitement
        # Pour éviter de retraiter les mêmes données inutilement
        df_hash = hash(df.iloc[-1].to_string()) if len(df) > 0 else None
        last_hash = getattr(bot, '_last_data_hash', {}).get(symbol)
        if df_hash == last_hash and len(df) > 0:
            # Même dernière barre, on peut skip le traitement sauf si on a besoin de mettre à jour les positions
            # Mais on continue quand même pour la gestion des risques des positions ouvertes
            pass  # Continuer pour la gestion de risque
        else:
            # Nouveaux données, mettre à jour le hash
            if not hasattr(bot, '_last_data_hash'):
                bot._last_data_hash = {}
            bot._last_data_hash[symbol] = df_hash

        # 2. Calculer les indicateurs techniques (avec cache de cycle)
        indicators_start = time.time()
        with bot._lock:
            if not hasattr(bot, '_indicators_cache'):
                bot._indicators_cache = {}
            if symbol in bot._indicators_cache:
                df_with_indicators = bot._indicators_cache[symbol]
            else:
                df_with_indicators = bot.technical_indicators.calculate_all_indicators(df.copy())
                bot._indicators_cache[symbol] = df_with_indicators
            bot.market_data[symbol] = df_with_indicators
        indicators_time = time.time() - indicators_start

        # === GESTION DE RISQUE CONTINUE DES POSITIONS OUVERTES ===
        risk_start = time.time()
        bot._update_active_position_risk(symbol, df_with_indicators)
        risk_time = time.time() - risk_start

        # 🚫 BLOCAGE DYNAMIQUE : Skip si actif bloqué pour cette session
        if symbol in bot.blocked_symbols:
            log.info(f"⛔ {symbol} bloqué pour cette session (perte cumulée > seuil)")
            return

        # Si le courtier est crypto et que le symbole n'est pas parmi les actifs sélectionnés
        if bot.broker.get_asset_type() == "crypto":
            active_cryptos = getattr(bot, '_active_crypto_symbols', [])
            if active_cryptos and symbol not in active_cryptos:
                # Ne pas chercher à ouvrir de nouvelles positions sur cet actif
                return

        # 🕒 FILTRE SESSION US (Alpaca/Stocks)
        if bot.broker.get_asset_type() == "stock":
            market_is_open = True
            
            # Vérification API officielle Alpaca
            if hasattr(bot.broker, '_api') and hasattr(bot.broker._api, 'get_clock'):
                try:
                    clock = bot.broker._api.get_clock()
                    market_is_open = clock.is_open
                except Exception as e:
                    log.warning(f"Erreur vérification horloge Alpaca : {e}")
                    market_is_open = False # Par précaution
                    
            if not market_is_open:
                log.debug(f"Marché US fermé (Alpaca API) : skip {symbol}")
                return

        # 3. Analyser le marché et générer un signal de trading (avec cache de cycle)
        strategy_start = time.time()
        with bot._lock:
            if not hasattr(bot, '_strategy_cache'):
                bot._strategy_cache = {}
            if symbol in bot._strategy_cache:
                signal_data = bot._strategy_cache[symbol]
            else:
                signal_data = None
        if signal_data is None:
            # Passer le vrai solde et le Kelly réel calculé depuis l'historique au modèle
            _real_balance = getattr(bot, '_cached_balance', 0.0)
            _real_win_rate = None
            if bot.risk_manager and len(bot.risk_manager.trade_history) >= bot.risk_manager.MIN_TRADES_FOR_KELLY:
                _real_win_rate = bot.risk_manager._calculate_kelly_fraction()

            # P1-1 : Calculer la variation BTC 24h depuis les données de marché en cache
            _btc_change_24h = None
            if bot.broker.get_asset_type() == "crypto":
                btc_sym = 'BTC/USDT'
                btc_df_24h = bot.market_data.get(btc_sym)
                if btc_df_24h is not None and len(btc_df_24h) >= 24:
                    try:
                        price_now = float(btc_df_24h.iloc[-1]['close'])
                        price_24h = float(btc_df_24h.iloc[-24]['close'])  # 24 bougies H1 = 24h
                        if price_24h > 0:
                            _btc_change_24h = (price_now - price_24h) / price_24h * 100.0
                            log.debug(f"[P1-1] Variation BTC 24h: {_btc_change_24h:+.2f}%")
                    except Exception as _e:
                        log.debug(f"[P1-1] Impossible de calculer la variation BTC 24h: {_e}")

            # Récupérer les facteurs NLP et filtres depuis le NewsManager
            _sentiment_factor = 1.0
            _news_filter_passed = True
            if bot.news_manager:
                try:
                    _sentiment_factor = bot.news_manager.get_risk_factor()
                    _should_avoid, _ = bot.news_manager.should_avoid_trading_due_to_news(symbol)
                    _news_filter_passed = not _should_avoid
                except Exception as e:
                    log.debug(f"Erreur NewsManager: {e}")

            signal_data = bot.strategy.analyze_market(
                df_with_indicators,
                account_balance=_real_balance,
                real_win_rate=_real_win_rate,
                symbol=symbol,
                btc_change_24h=_btc_change_24h,
                sentiment_factor=_sentiment_factor,
                news_filter_passed=_news_filter_passed
            )
            signal_data['symbol'] = symbol
            with bot._lock:
                bot._strategy_cache[symbol] = signal_data
        strategy_time = time.time() - strategy_start

        # DEBUG: log signal details and pre-check news avoidance
        score_raw = signal_data['total_score']
        # Afficher le score_min effectif (par asset_type) plutôt que le global
        score_min = signal_data.get('score_min', bot.strategy.score_min)
        rr = signal_data['rr_ratio']
        if getattr(bot, 'news_manager', None):
            should_avoid, news_event = bot.news_manager.should_avoid_trading_due_to_news(symbol)
        else:
            should_avoid, news_event = False, None
        news_ok = not should_avoid
        log.info(
            f"Signal DEBUG {symbol}: regime={signal_data['market_regime']} "
            f"score_raw={score_raw:.1f} score_min={score_min} "
            f"should_long={signal_data['should_long']} should_short={signal_data['should_short']} "
            f"RR={rr:.2f} news_ok={news_ok}"
        )

        if should_avoid:
            log.info(f"Trading évité pour {symbol} à cause des nouvelles : {news_event.title if news_event else 'Unknown'}")
            return
        elif signal_data['should_long'] or signal_data['should_short']:
            # Exécuter le trade
            trade_start = time.time()
            bot._execute_signal_trade(symbol, signal_data, df_with_indicators)
            trade_time = time.time() - trade_start
        else:
            log.info(
                f"Scan {symbol} : {signal_data['market_regime']} | "
                f"Score: {score_raw:.1f}/{score_min} | "
                f"Pas de signal (Trigger L: {signal_data['trigger_long']}, S: {signal_data['trigger_short']}, R:R: {rr:.2f})"
            )

        # Log des temps de traitement pour profiling (en mode debug seulement)
        total_time = time.time() - symbol_start_time
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                f"Profiling {symbol}: "
                f"fetch={fetch_time:.3f}s, indicators={indicators_time:.3f}s, "
                f"risk={risk_time:.3f}s, strategy={strategy_time:.3f}s, "
                f"trade={trade_time if 'trade_time' in locals() else 0:.3f}s, "
                f"total={total_time:.3f}s"
            )

    except Exception as e:
        log.error(f"Erreur inattendue dans _process_symbol pour {symbol} : {e}")
        log.debug(traceback.format_exc())