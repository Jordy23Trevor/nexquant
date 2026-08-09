import logging
import time
import traceback
import threading
import random
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from datetime import datetime, timezone

log = logging.getLogger("cycle_runner")

# ⚡ V3 : Lire CYCLE_TIME depuis config (fix bug heartbeat 50-60s)
try:
    from superbot.config import (
        CYCLE_WATCHDOG_TIMEOUT, POST_FREEZE_THRESHOLD_SECONDS,
        POST_FREEZE_COOLDOWN_CYCLES as _PF_CYCLES,
        CYCLE_TIME as _DEFAULT_CYCLE_TIME,
        SYMBOL_TIMEOUT_SECONDS as _DEFAULT_SYMBOL_TIMEOUT,
        MAX_PARALLEL_SYMBOLS as _DEFAULT_MAX_PARALLEL,
    )
except ImportError:
    CYCLE_WATCHDOG_TIMEOUT = 300
    POST_FREEZE_THRESHOLD_SECONDS = 120
    _PF_CYCLES = 2
    _DEFAULT_CYCLE_TIME = 15  # V3 : 15s au lieu de 60s
    _DEFAULT_SYMBOL_TIMEOUT = 8
    _DEFAULT_MAX_PARALLEL = 4


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

    # ⚡ V3 : Lire CYCLE_TIME et les paramètres parallèles depuis la config du bot
    target_cycle_time = getattr(bot, 'CYCLE_TIME', _DEFAULT_CYCLE_TIME)
    symbol_timeout = getattr(bot, 'SYMBOL_TIMEOUT_SECONDS', _DEFAULT_SYMBOL_TIMEOUT)
    max_parallel = getattr(bot, 'MAX_PARALLEL_SYMBOLS', _DEFAULT_MAX_PARALLEL)
    log.info(
        f"⚡ Cycle runner V3 | CYCLE_TIME={target_cycle_time}s | "
        f"SYMBOL_TIMEOUT={symbol_timeout}s | MAX_PARALLEL={max_parallel}"
    )

    # ── 🧠 V3 : Démarrage des modules Brain ──────────────────────────────────
    # 1. KnowledgeFeeder en background thread
    if getattr(bot, 'knowledge_feeder', None):
        try:
            bot.knowledge_feeder.start()
            log.info("🌐 KnowledgeFeeder démarré en background")
        except Exception as _e:
            log.debug(f"KnowledgeFeeder start error: {_e}")

    # 2. Analyse pré-session initiale
    if getattr(bot, 'performance_learner', None) and getattr(bot, 'AUTO_LEARN_ENABLED', True):
        try:
            adj = bot.performance_learner.pre_session_analysis(bot)
            log.info(f"🔍 Pré-session initiale | {adj}")
        except Exception as _e:
            log.debug(f"Pre-session init error: {_e}")

    # 3. Timer interne pour les checks périodiques brain
    _last_pre_session_check = 0.0
    _last_mid_check = 0.0
    _last_perf_log = 0.0
    _PRE_SESSION_INTERVAL = 3600   # Analyse pré-session toutes les heures
    _MID_CHECK_INTERVAL = 1800     # Check mi-session toutes les 30 min
    _PERF_LOG_INTERVAL = 600       # Log de performance toutes les 10 min
    # ─────────────────────────────────────────────────────────────────────────

    while bot.running and not bot.shutdown_event.is_set():
        cycle_start = time.time()
        now_time = time.time()

        try:
            # ── Heartbeat watchdog ────────────────────────────────────────────
            # Mis à jour au tout début du cycle pour que le watchdog sache
            # que le bot est vivant même pendant les longs cycles.
            bot._last_cycle_heartbeat = time.time()
            # ─────────────────────────────────────────────────────────────────

            # BUG-A11 FIX: Réinitialiser tous les caches de données à chaque cycle
            # Sans ce reset, _fetch_market_data retourne les données stales du cycle précédent
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
            # BUG-11 FIX: Utiliser getattr pour éviter AttributeError si l'attribut n'est pas encore initialisé
            _last_cloud_sync = getattr(bot, '_last_cloud_sync', 0.0)
            if bot.telemetry.enabled and (now_time - _last_cloud_sync >= bot.CLOUD_SYNC_INTERVAL):
                # BUG-I5 FIX: Mettre à jour _last_cloud_sync ICI (dans le thread principal) AVANT de lancer
                # le thread de sync, pas à l'intérieur du thread. Sinon, si la réponse API prend plusieurs
                # cycles (>15s), un nouveau thread de sync est lancé à chaque cycle → N threads parallèles.
                bot._last_cloud_sync = now_time

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
            # BUG-11 FIX: Utiliser getattr pour éviter AttributeError si l'attribut n'est pas encore initialisé
            _last_telemetry_push = getattr(bot, '_last_telemetry_push', 0.0)
            if bot.telemetry.enabled and (now_time - _last_telemetry_push >= bot.TELEMETRY_INTERVAL):
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
                cycle_duration = time.time() - cycle_start
                if cycle_duration < target_cycle_time:
                    sleep_time = target_cycle_time - cycle_duration
                    slept = 0
                    while slept < sleep_time and bot.running and not bot.shutdown_event.is_set():
                        time.sleep(min(1, sleep_time - slept))
                        slept += 1
                continue

            # 📅 RESET QUOTIDIEN DES BLOCAGES D'ACTIFS + BRAIN V3
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

                # 🧠 V3 : Reset journalier du SessionManager et PerformanceLearner
                if getattr(bot, 'session_manager', None):
                    try:
                        balance = getattr(bot, '_cached_balance', 0.0) or getattr(bot, 'initial_balance', 10000.0)
                        bot.session_manager.reset_daily(balance)
                        log.info(f"🧠 SessionManager reset journalier | balance={balance:.2f}€")
                    except Exception as _e:
                        log.debug(f"SessionManager reset error: {_e}")
                
                if getattr(bot, 'risk_manager', None):
                    try:
                        bot.risk_manager.reset_daily_stats()
                    except Exception as _e:
                        log.debug(f"RiskManager reset error: {_e}")

            # 🧠 V3 : Analyse PRÉ-SESSION périodique (toutes les heures)
            if (getattr(bot, 'performance_learner', None) and
                    getattr(bot, 'AUTO_LEARN_ENABLED', True) and
                    now_time - _last_pre_session_check >= _PRE_SESSION_INTERVAL):
                try:
                    threading.Thread(
                        target=lambda: bot.performance_learner.pre_session_analysis(bot),
                        daemon=True, name="pre_session_analysis"
                    ).start()
                    _last_pre_session_check = now_time
                except Exception as _e:
                    log.debug(f"Pre-session analysis error: {_e}")

            # 🧠 V3 : Check MID-SESSION (toutes les 30 min)
            if (getattr(bot, 'performance_learner', None) and
                    getattr(bot, 'session_manager', None) and
                    now_time - _last_mid_check >= _MID_CHECK_INTERVAL):
                try:
                    sm = bot.session_manager
                    progress = sm.get_daily_progress()
                    pnl = progress.get('achieved_eur', 0)
                    target = progress.get('target_eur', 200)
                    balance = getattr(bot, '_cached_balance', 0.0) or getattr(bot, 'initial_balance', 10000.0)
                    actions = bot.performance_learner.mid_session_check(pnl, target, balance)
                    if actions.get('action'):
                        log.info(f"🔄 Mid-session : {actions['action']} | {progress['achieved_eur']:.1f}€/{target:.1f}€ ({progress['achievement_pct']:.0f}%)")
                    _last_mid_check = now_time
                except Exception as _e:
                    log.debug(f"Mid-session check error: {_e}")

            # 🧠 V3 : Log de performance périodique (toutes les 10 min)
            if now_time - _last_perf_log >= _PERF_LOG_INTERVAL:
                try:
                    if getattr(bot, 'session_manager', None):
                        log.info(f"📊 {bot.session_manager.get_session_summary()}")
                    if getattr(bot, 'db', None):
                        bal = getattr(bot, '_cached_balance', 0.0) or getattr(bot, 'initial_balance', 0.0)
                        sess = getattr(bot, 'session_manager', None)
                        bot.db.log_performance({
                            'balance': bal,
                            'equity': bal,
                            'daily_pnl': sess.get_daily_progress().get('achieved_eur', 0) if sess else 0,
                            'daily_target': getattr(bot, 'DAILY_TARGET_EUR', 200),
                            'open_positions': len(getattr(bot, 'positions', {})),
                            'session_name': sess.get_current_session().get('name', '') if sess else '',
                        })
                    _last_perf_log = now_time
                except Exception as _e:
                    log.debug(f"Perf log error: {_e}")

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

            def _process_symbol_safe(bot, sym, timeout):
                try:
                    bot._process_symbol(sym)
                except Exception as e:
                    log.error(f"Erreur lors du traitement de {sym} : {e}")
                    log.debug(traceback.format_exc())
                    with bot._state_lock:
                        bot.stats['errors_count'] += 1

            if max_parallel > 1 and len(scanned_instruments) > 1:
                with ThreadPoolExecutor(
                    max_workers=min(max_parallel, len(scanned_instruments)),
                    thread_name_prefix="sym_worker"
                ) as executor:
                    future_to_sym = {
                        executor.submit(
                            _process_symbol_safe, bot, sym, symbol_timeout
                        ): sym
                        for sym in scanned_instruments
                        if bot.running and not bot.shutdown_event.is_set()
                    }
                    for future in as_completed(
                        future_to_sym,
                        timeout=symbol_timeout * len(scanned_instruments) + 10
                    ):
                        sym = future_to_sym[future]
                        try:
                            future.result(timeout=symbol_timeout)
                        except FuturesTimeoutError:
                            log.warning(f"⏱️ Timeout ({symbol_timeout}s) pour {sym}")
                        except Exception as e:
                            log.error(f"Erreur traitement {sym}: {e}")
                            with bot._state_lock:
                                bot.stats['errors_count'] += 1
            else:
                for sym in scanned_instruments:
                    if not bot.running or bot.shutdown_event.is_set():
                        break
                    _process_symbol_safe(bot, sym, symbol_timeout)

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

            cycle_duration = time.time() - cycle_start
            
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

            # ⚡ V3 : Sleep jusqu'au prochain cycle (target_cycle_time lu depuis config)
            # BUG FIX : 'target_cycle_time = 60' était ici avant → écrasait la valeur de la config !
            # La valeur correcte est définie une seule fois au début de run_main_loop().
            if cycle_duration < target_cycle_time:
                sleep_time = target_cycle_time - cycle_duration
                slept = 0
                while slept < sleep_time and bot.running and not bot.shutdown_event.is_set():
                    time.sleep(min(1, sleep_time - slept))
                    slept += 1
                log.debug(
                    f"✅ Cycle #{cycle_count} : {cycle_duration:.1f}s "
                    f"(cible={target_cycle_time}s | sleep={sleep_time:.1f}s)"
                )
            else:
                log.warning(f"⚠️ Cycle #{cycle_count} trop long : {cycle_duration:.2f}s (cible : {target_cycle_time}s)")

                # ── Détection post-freeze (fix 24/07/2026) ─────────────────
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
