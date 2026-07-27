import logging
import time
import traceback
import threading
import random
from datetime import datetime, timezone

log = logging.getLogger("cycle_runner")


def _start_cycle_watchdog(bot, watchdog_timeout: int = 300):
    """
    Lance un thread watchdog qui surveille le heartbeat du cycle principal.

    Si aucun cycle ne s'est terminé depuis plus de `watchdog_timeout` secondes,
    une alerte critique est loggée. Ceci permet de détecter les freezes du type
    '⚠️ Cycle trop long : 23177s' qui ont causé la perte du 24/07/2026.

    Args:
        bot: Instance du SuperBot
        watchdog_timeout: Délai max entre deux cycles avant alerte (secondes)
    """
    def _watchdog_loop():
        log.info(f"⏱️ [Watchdog] Démarré — alerte si aucun cycle après {watchdog_timeout}s")
        while getattr(bot, 'running', False) and not bot.shutdown_event.is_set():
            time.sleep(30)  # vérifier toutes les 30 secondes
            last_hb = getattr(bot, '_last_cycle_heartbeat', None)
            if last_hb is None:
                continue
            elapsed = time.time() - last_hb
            if elapsed > watchdog_timeout:
                log.critical(
                    f"🚨 [Watchdog] CYCLE GELÉ DEPUIS {elapsed:.0f}s (seuil: {watchdog_timeout}s) — "
                    f"des positions ouvertes ne sont peut-être plus surveillées ! "
                    f"Vérifier la connexion réseau et l'état du broker."
                )
            elif elapsed > watchdog_timeout * 0.6:
                log.warning(
                    f"⚠️ [Watchdog] Cycle lent : {elapsed:.0f}s sans heartbeat "
                    f"(seuil critique: {watchdog_timeout}s)"
                )

    t = threading.Thread(target=_watchdog_loop, name="cycle_watchdog", daemon=True)
    t.start()
    return t

def run_main_loop(bot):
    """
    Boucle principale de trading.
    Cette boucle exécute le cycle de trading pour chaque instrument.
    """
    log.info("Démarrage de la boucle principale de trading")

    cycle_count = 0
    last_news_update = 0
    news_update_interval = 300  # 5 minutes

    # ── Watchdog de cycle (fix freeze 24/07/2026) ─────────────────────────────
    # Initialiser le heartbeat avant de lancer le watchdog
    bot._last_cycle_heartbeat = time.time()
    bot._post_freeze_cooldown_cycles = 0
    try:
        from superbot.config import CYCLE_WATCHDOG_TIMEOUT, POST_FREEZE_THRESHOLD_SECONDS, POST_FREEZE_COOLDOWN_CYCLES as _PF_CYCLES
    except ImportError:
        CYCLE_WATCHDOG_TIMEOUT = 300
        POST_FREEZE_THRESHOLD_SECONDS = 120
        _PF_CYCLES = 2
    _start_cycle_watchdog(bot, watchdog_timeout=CYCLE_WATCHDOG_TIMEOUT)
    # ─────────────────────────────────────────────────────────────────────────

    while bot.running and not bot.shutdown_event.is_set():
        cycle_start_time = time.time()

        try:
            # ── Heartbeat watchdog ────────────────────────────────────────────
            # Mis à jour au tout début du cycle pour que le watchdog sache
            # que le bot est vivant même pendant les longs cycles.
            bot._last_cycle_heartbeat = time.time()
            # ─────────────────────────────────────────────────────────────────

            # Réinitialiser le cache des données de marché pour ce cycle
            bot._market_data_cache = {}
            bot._indicators_cache = {}
            bot._strategy_cache = {}
            bot._cached_balance = 0.0  # sera mis à jour au premier appel get_balance()

            now_time = time.time()
            
            # Phase 3.2 : Déclencheur Walk-Forward Adaptatif Asynchrone
            if not hasattr(bot, 'walk_forward_optimizer'):
                try:
                    from superbot.ml.walk_forward import WalkForwardOptimizer
                    bot.walk_forward_optimizer = WalkForwardOptimizer()
                except ImportError:
                    bot.walk_forward_optimizer = None

            if getattr(bot, 'walk_forward_optimizer', None):
                wf = bot.walk_forward_optimizer
                # Recalibrer tous les 30 jours (2592000 secondes)
                if now_time - wf.last_calibration_time > 2592000 and not wf.is_optimizing:
                    def walk_forward_task():
                        if bot.risk_manager and hasattr(bot.risk_manager, 'trade_history'):
                            import pandas as pd
                            trades_df = pd.DataFrame(bot.risk_manager.trade_history)
                            new_params = wf.optimize(trades_df)
                            # Mettre à jour la stratégie à chaud
                            if hasattr(bot, 'strategy'):
                                bot.strategy.score_min = new_params.get('SCORE_MIN', bot.strategy.score_min)
                                bot.adaptive_score_min = bot.strategy.score_min
                    
                    threading.Thread(target=walk_forward_task, daemon=True).start()
            # 📡 TÉLÉMÉTRIE CLOUD : Synchronisation et heartbeat (fréquence réduite)
            if bot.telemetry.enabled and (now_time - bot._last_cloud_sync >= bot.CLOUD_SYNC_INTERVAL):
                def sync_config_task():
                    res = bot.telemetry.sync_config(current_version="v1.0.0")
                    if res:
                        if res.get("is_expired"):
                            log.error("❌ Licence expirée ou inactive détectée. Arrêt automatique du bot.")
                            bot.stop()
                            return

                        cloud_cfg = res.get("config", {})
                        old_risk_pct = bot.adaptive_risk_pct
                        old_score_min = bot.adaptive_score_min
                        bot.adaptive_risk_pct = cloud_cfg.get("risk_pct", bot.adaptive_risk_pct)
                        bot.adaptive_score_min = cloud_cfg.get("score_min", bot.adaptive_score_min)

                        cloud_running = cloud_cfg.get("is_running", True)
                        if not cloud_running and not bot.is_paused:
                            log.info("⏸️ Commande de PAUSE reçue depuis le Cloud.")
                            bot.is_paused = True
                        elif cloud_running and bot.is_paused:
                            log.info("▶️ Commande de REPRISE reçue depuis le Cloud.")
                            bot.is_paused = False

                        bot._last_cloud_sync = now_time

                        if old_risk_pct != bot.adaptive_risk_pct or old_score_min != bot.adaptive_score_min:
                            log.info(f"Configuration cloud mise à jour : risque {old_risk_pct:.2f}% -> {bot.adaptive_risk_pct:.2f}%, score min {old_score_min:.1f} -> {bot.adaptive_score_min:.1f}")

                sync_thread = threading.Thread(target=sync_config_task, daemon=True)
                sync_thread.start()

                bot.telemetry.push_heartbeat(
                    is_running=bot.running and not bot.is_paused,
                    broker_type=bot.broker.get_asset_type(),
                    testnet=getattr(bot.broker, 'testnet', True) or getattr(bot.broker, 'account_type', 'PAPER') == 'PAPER' or 'demo' in str(getattr(bot.broker, 'server', '')).lower() or 'demo' in str(getattr(bot.broker, 'company', '')).lower()
                )
            
            # 📡 TÉLÉMÉTRIE CLOUD : Envoi périodique des métriques du compte et des positions actives
            if bot.telemetry.enabled and (now_time - bot._last_telemetry_push >= bot.TELEMETRY_INTERVAL):
                bot._last_telemetry_push = now_time
                try:
                    acc_summary = bot.broker.get_account_summary()
                    equity = 0.0
                    if acc_summary:
                        equity = float(acc_summary.get("equity") or acc_summary.get("balance") or 0.0)
                    
                    if equity <= 0.0:
                        bal = bot.broker.get_balance()
                        if bal > 0.0:
                            equity = bal
                            
                    if equity > 0.0:
                        pnl_total = equity - bot.initial_balance
                        bot.telemetry.push_equity(equity=equity, pnl_total=pnl_total, drawdown=0.0)
                        
                        # 🛑 Phase 3 : Kill-Switch Drawdown Journalier
                        if bot.risk_manager:
                            bot.risk_manager.update_account_balance(equity)
                            if bot.risk_manager.check_kill_switch(equity):
                                log.critical("🛑 KILL-SWITCH ACTIVÉ : Auto-pause d'urgence déclenchée pour protéger le capital.")
                                bot.is_paused = True
                                bot._save_cooldowns()
                                
                    else:
                        log.warning("⚠️ Impossible de pousser l'équité à la télémétrie : valeur invalide ou nulle.")
                except Exception as e:
                    log.debug(f"Erreur télémétrie/kill-switch : {e}")

                try:
                    for symbol, pos in bot.positions.items():
                        pnl = pos.get("unrealized_pnl", 0.0)
                        entry = pos.get("entry_price", 0.0)
                        current = pos.get("mark_price", entry)
                        pnl_pct = ((current - entry) / entry * 100) if entry > 0 else 0.0
                        if pos.get("side") == "SHORT":
                            pnl_pct = -pnl_pct
                        
                        bot.telemetry.push_position(
                            symbol=symbol,
                            side=pos.get("side", "LONG"),
                            qty=pos.get("size", 0.0),
                            entry_price=entry,
                            current_price=current,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            status="open",
                            broker=bot.broker.get_asset_type()
                        )
                except Exception as e:
                    log.debug(f"Erreur envoi positions télémétrie : {e}")

            # ── Trailing Profit Circuit Breaker (Formulation 2) ──────────────
            if getattr(bot, 'profit_circuit_breaker', None):
                try:
                    cb_balance = getattr(bot, '_cached_balance', 0.0)
                    if cb_balance <= 0.0:
                        if bot.risk_manager and getattr(bot.risk_manager, 'current_balance', 0.0) > 0:
                            cb_balance = bot.risk_manager.current_balance
                        else:
                            try:
                                cb_balance = bot.broker.get_balance()
                            except Exception:
                                cb_balance = 0.0
                    if cb_balance > 0:
                        cb_paused = bot.profit_circuit_breaker.check(cb_balance)
                        bot._circuit_breaker_paused = cb_paused
                        if cb_paused:
                            log.info("⏸️ [CircuitBreaker] Trading suspendu par protection de profit. Analyse en cours sans exécution.")
                except Exception as e:
                    log.debug(f"Erreur vérification ProfitCircuitBreaker : {e}")
            # ─────────────────────────────────────────────────────────────────

            if bot.is_paused:
                log.info("😴 Bot en pause. En attente du signal de démarrage depuis la plateforme web...")
                cycle_duration = time.time() - cycle_start_time
                target_cycle_time = 60
                if cycle_duration < target_cycle_time:
                    sleep_time = target_cycle_time - cycle_duration
                    slept = 0
                    while slept < sleep_time and bot.running and not bot.shutdown_event.is_set():
                        time.sleep(min(1, sleep_time - slept))
                        slept += 1
                continue

            # 📅 RESET QUOTIDIEN DES BLOCAGES D'ACTIFS
            today = datetime.now().date()
            if today != bot.session_date:
                blocked_count = len(bot.blocked_symbols)
                bot.blocked_symbols.clear()
                bot.session_pnl_by_symbol.clear()
                bot.session_date = today
                if getattr(bot, 'profit_circuit_breaker', None):
                    bot.profit_circuit_breaker.reset_daily()
                if blocked_count > 0:
                    log.info(f"📅 Reset quotidien : {blocked_count} actifs débloqués pour nouvelle session")
                else:
                    log.debug("📅 Reset quotidien des blocages d'actifs")

            cycle_count += 1
            
            if cycle_count > 0 and cycle_count % 10 == 0:
                if bot.risk_manager:
                    balance = bot.risk_manager.current_balance
                    if balance <= 0.0:
                        try:
                            balance = bot.broker.get_balance()
                        except Exception:
                            balance = getattr(bot, "initial_balance", 10000.0)
                    metrics = bot.risk_manager.get_risk_metrics(balance)
                    if metrics:
                        log.info(f"📊 [Risk Metrics] WinRate: {metrics.get('win_rate', 0):.1%} | Profit Factor: {metrics.get('profit_factor', 0):.2f} | Drawdown: {metrics.get('current_drawdown_pct', 0):.2f}%")

            with bot._state_lock:
                bot.stats['cycles_completed'] = cycle_count
                bot.stats['last_cycle_time'] = datetime.now(timezone.utc)

            log.debug(f"Cycle #{cycle_count} démarré")

            try:
                bot._sync_positions_with_broker()
            except Exception as e:
                log.warning(f"Erreur de synchronisation des positions au cycle #{cycle_count} : {e}")

            try:
                bot._select_and_rotate_crypto()
            except Exception as e:
                log.warning(f"Erreur lors de la sélection/rotation crypto au cycle #{cycle_count} : {e}")

            scanned_instruments = list(bot.instruments)
            random.shuffle(scanned_instruments)

            def run_process_symbol(symbol):
                if not bot.running or bot.shutdown_event.is_set():
                    return
                try:
                    bot._process_symbol(symbol)
                except Exception as e:
                    log.error(f"Erreur lors du traitement de {symbol} : {e}")
                    log.debug(traceback.format_exc())
                    with bot._state_lock:
                        bot.stats['errors_count'] += 1
                        if getattr(bot, 'prometheus', None):
                            bot.prometheus.bot_api_errors_total.labels(
                                broker=bot.broker.get_asset_type(),
                                error_code="process_symbol_error"
                            ).inc()

            # 🔒 BUG FIX #RC — Traitement séquentiel pour éviter les race conditions
            # sur bot.positions, bot.session_pnl_by_symbol et les caches partagés.
            # _process_symbol modifie l'état global (positions, PnL, cooldowns) et le
            # _lock (RLock) ne couvre pas toutes les sections critiques.
            # Le ThreadPoolExecutor parallélisait les symboles et pouvait causer :
            # - double-exécution de trades (deux threads lisent bot.positions vides simultanément)
            # - corruption de session_pnl_by_symbol (écriture concurrente)
            # - écrasement des caches _indicators_cache / _strategy_cache
            for symbol in scanned_instruments:
                run_process_symbol(symbol)

            if bot.dashboard:
                try:
                    bot._update_dashboard()
                except Exception as e:
                    log.debug(f"Erreur lors de la mise à jour du dashboard : {e}")

            bot._adaptation_counter += 1
            if bot._adaptation_counter >= bot._adaptation_every:
                bot._update_adaptive_parameters()
                bot._adaptation_counter = 0

            bot._detect_model_drift()
            bot._run_walk_forward_calibration()

            cycle_duration = time.time() - cycle_start_time
            
            # ── Phase 3.3 : Alimentation Prometheus ──────────────────────────────
            if getattr(bot, 'prometheus', None) and bot.prometheus.is_running:
                try:
                    bot.prometheus.bot_cycle_duration_seconds.observe(cycle_duration)
                    bot.prometheus.bot_open_positions.set(len(bot.positions))
                    
                    if bot.risk_manager:
                        balance = bot.risk_manager.current_balance
                        if balance <= 0.0:
                            balance = bot._cached_balance if bot._cached_balance > 0 else getattr(bot, "initial_balance", 10000.0)
                        metrics = bot.risk_manager.get_risk_metrics(balance)
                        if metrics:
                            bot.prometheus.bot_drawdown_pct.set(metrics.get("current_drawdown_pct", 0.0))
                            
                    if bot._cached_balance > 0:
                        bot.prometheus.bot_balance.set(bot._cached_balance)
                        
                    session_pnl = sum(bot.session_pnl_by_symbol.values())
                    bot.prometheus.bot_pnl_session.set(session_pnl)
                except Exception as e:
                    log.debug(f"Erreur mise à jour Prometheus : {e}")

            target_cycle_time = 60

            if cycle_duration < target_cycle_time:
                sleep_time = target_cycle_time - cycle_duration
                slept = 0
                while slept < sleep_time and bot.running and not bot.shutdown_event.is_set():
                    time.sleep(min(1, sleep_time - slept))
                    slept += 1
            else:
                log.warning(f"⚠️ Cycle trop long : {cycle_duration:.2f}s (cible : {target_cycle_time}s)")

                # ── Détection post-freeze (fix 24/07/2026) ────────────────────
                # Si le cycle a duré bien plus que la cible, activer un
                # mode d'audit qui bloque les nouveaux trades N cycles.
                if cycle_duration > POST_FREEZE_THRESHOLD_SECONDS:
                    bot._post_freeze_cooldown_cycles = _PF_CYCLES
                    log.critical(
                        f"🔴 [Post-Freeze] Cycle de {cycle_duration:.0f}s détecté "
                        f"(seuil: {POST_FREEZE_THRESHOLD_SECONDS}s). "
                        f"Mode audit activé : aucun nouveau trade pendant {_PF_CYCLES} cycle(s). "
                        f"Les positions existantes sont vérifiées avant toute action."
                    )
                # ─────────────────────────────────────────────────────────────

        except Exception as e:
            log.error(f"Erreur dans la boucle principale : {e}")
            log.error(traceback.format_exc())
            bot.stats['errors_count'] += 1
            time.sleep(5)

    log.info("Boucle principale de trading terminée")
