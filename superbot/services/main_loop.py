"""
Main loop module for SuperBot V3.
====================================
Fix critique Phase 0 — Bug cycle lent (heartbeat 50-60s → <15s)

Causes du bug identifiées dans bug_log.md :
  - CYCLE_TIME hardcodé à 60s dans getattr() → jamais lu depuis config
  - Traitement SÉQUENTIEL des symboles (chaque MT5 fetch_candles = 2-3s × N symboles)
  - Pas de timeout par symbole → un symbole bloqué = tout le cycle bloqué

Corrections V3 :
  1. CYCLE_TIME lu depuis config (défaut 15s)
  2. Traitement PARALLÈLE des symboles via ThreadPoolExecutor (max 4 workers)
  3. Timeout hard de SYMBOL_TIMEOUT_SECONDS (défaut 8s) par symbole
  4. Cache de données invalidé correctement entre cycles
  5. Heartbeat mesuré et loggé à chaque fin de cycle
  6. Slippage/commission simulés en mode live_conditions pour préparer le live
"""

import time
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from datetime import datetime, timezone
from typing import Optional, Any, Dict
import hashlib
import logging


class MainLoopManager:
    """
    Gestionnaire de la boucle principale de trading V3.
    
    Améliorations vs V2 :
    - Traitement parallèle des symboles (ThreadPoolExecutor)
    - Timeout par symbole pour éviter les blocages
    - Cycle time réduit à 15s (vs 60s avant)
    - Heartbeat mesuré et loggé
    - Support du mode live_conditions (slippage + commission simulés)
    """

    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.log = bot_instance.log

        # Lire les paramètres V3 depuis le bot ou la config
        self.cycle_time = getattr(bot_instance, 'CYCLE_TIME', 15)
        self.symbol_timeout = getattr(bot_instance, 'SYMBOL_TIMEOUT_SECONDS', 8)
        self.max_parallel = getattr(bot_instance, 'MAX_PARALLEL_SYMBOLS', 4)
        self.trading_mode = getattr(bot_instance, 'TRADING_MODE', 'live_conditions')
        self.simulated_slippage = getattr(bot_instance, 'SIMULATED_SLIPPAGE_POINTS', 2.0)
        self.simulated_commission_pct = getattr(bot_instance, 'SIMULATED_COMMISSION_PCT', 0.003)

        # Statistiques heartbeat
        self._last_heartbeat: float = time.time()
        self._cycle_times: list = []  # Historique des 10 derniers temps de cycle
        self._data_hash_cache: Dict[str, str] = {}  # Cache hash par symbole

        self.log.info(
            f"MainLoopManager V3 initialisé | "
            f"CYCLE_TIME={self.cycle_time}s | "
            f"SYMBOL_TIMEOUT={self.symbol_timeout}s | "
            f"MAX_PARALLEL={self.max_parallel} | "
            f"TRADING_MODE={self.trading_mode}"
        )

    def run_main_loop(self):
        """
        Boucle principale de trading V3 — traitement parallèle avec heartbeat.
        
        Architecture du cycle :
          1. Rotation crypto (si applicable)
          2. Traitement PARALLÈLE de tous les symboles (ThreadPoolExecutor)
          3. Mise à jour dashboard
          4. Adaptation des paramètres (toutes les N cycles)
          5. Détection drift ML (toutes les M cycles)
          6. Sauvegarde d'état (toutes les 5 min)
          7. Sleep jusqu'à prochain cycle (target = CYCLE_TIME)
        """
        self.log.info(
            f"🚀 Boucle principale V3 démarrée | "
            f"Cycle cible : {self.cycle_time}s | "
            f"Symboles : {self.bot.instruments}"
        )

        while self.bot.running and not self.bot.shutdown_event.is_set():
            cycle_start_time = time.time()

            try:
                # === 1. ROTATION CRYPTO (si applicable) ===
                if hasattr(self.bot, '_select_and_rotate_crypto'):
                    try:
                        self.bot._select_and_rotate_crypto()
                    except Exception as e:
                        self.log.warning(f"Erreur rotation crypto : {e}")

                # === 2. TRAITEMENT PARALLÈLE DES SYMBOLES ===
                # Invalider les caches de stratégie et indicateurs avant le cycle
                with self.bot._lock:
                    self.bot._indicators_cache = {}
                    self.bot._strategy_cache = {}
                    # Conserver _market_data_cache pour le cycle (rempli au fur et à mesure)
                    self.bot._market_data_cache = {}

                symbols_to_process = list(self.bot.instruments)

                if symbols_to_process:
                    self._process_symbols_parallel(symbols_to_process)

                # === 3. MISE À JOUR DASHBOARD ===
                if hasattr(self.bot, '_update_dashboard'):
                    try:
                        self.bot._update_dashboard()
                    except Exception as e:
                        self.log.debug(f"Dashboard update error: {e}")

                # === 4. ADAPTATION DES PARAMÈTRES (toutes les N cycles) ===
                if hasattr(self.bot, '_update_adaptive_parameters'):
                    self.bot._adaptation_counter = getattr(self.bot, '_adaptation_counter', 0) + 1
                    adapt_every = getattr(self.bot, '_adaptation_every', 20)
                    if self.bot._adaptation_counter >= adapt_every:
                        try:
                            self.bot._update_adaptive_parameters()
                        except Exception as e:
                            self.log.warning(f"Adaptive params update error: {e}")
                        self.bot._adaptation_counter = 0

                # === 5. DÉTECTION DRIFT ML (toutes les 30 cycles ≈ 7.5 min) ===
                if hasattr(self.bot, '_detect_model_drift'):
                    _drift_counter = getattr(self.bot, '_drift_counter', 0) + 1
                    self.bot._drift_counter = _drift_counter
                    if _drift_counter >= 30:
                        try:
                            self.bot._detect_model_drift()
                        except Exception as e:
                            self.log.debug(f"Model drift detection error: {e}")
                        self.bot._drift_counter = 0

                # === 6. WALK-FORWARD CALIBRATION (toutes les 100 cycles ≈ 25 min) ===
                if hasattr(self.bot, '_run_walk_forward_calibration'):
                    _wf_counter = getattr(self.bot, '_wf_counter', 0) + 1
                    self.bot._wf_counter = _wf_counter
                    if _wf_counter >= 100:
                        try:
                            self.bot._run_walk_forward_calibration()
                        except Exception as e:
                            self.log.debug(f"Walk-forward calibration error: {e}")
                        self.bot._wf_counter = 0

                # === 7. SAUVEGARDE D'ÉTAT (toutes les 5 minutes) ===
                if hasattr(self.bot, '_save_cooldowns'):
                    last_save = getattr(self.bot, '_last_state_save', 0)
                    if time.time() - last_save > 300:
                        try:
                            self.bot._save_cooldowns()
                        except Exception as e:
                            self.log.debug(f"State save error: {e}")
                        self.bot._last_state_save = time.time()

                # === 8. MESURE DU HEARTBEAT ===
                cycle_elapsed = time.time() - cycle_start_time
                self._cycle_times.append(cycle_elapsed)
                if len(self._cycle_times) > 10:
                    self._cycle_times.pop(0)
                avg_cycle = sum(self._cycle_times) / len(self._cycle_times)

                # Mettre à jour le heartbeat
                self._last_heartbeat = time.time()
                self.bot.stats['cycles_completed'] += 1
                self.bot.stats['last_cycle_time'] = self._last_heartbeat

                # Log du cycle avec heartbeat (INFO si lent, DEBUG si normal)
                if cycle_elapsed > self.cycle_time * 1.5:
                    self.log.warning(
                        f"⚠️ Cycle lent : {cycle_elapsed:.1f}s (cible {self.cycle_time}s) | "
                        f"Moy. 10 derniers : {avg_cycle:.1f}s"
                    )
                else:
                    self.log.debug(
                        f"✅ Cycle OK : {cycle_elapsed:.1f}s (cible {self.cycle_time}s) | "
                        f"Moy. : {avg_cycle:.1f}s"
                    )

                # === 9. SLEEP JUSQU'AU PROCHAIN CYCLE ===
                remaining = self.cycle_time - cycle_elapsed
                if remaining > 0:
                    # Sleep fractionné pour réactivité au shutdown
                    sleep_chunk = min(1.0, remaining)
                    slept = 0.0
                    while slept < remaining and self.bot.running and not self.bot.shutdown_event.is_set():
                        time.sleep(sleep_chunk)
                        slept += sleep_chunk

            except Exception as e:
                self.bot.stats['errors_count'] += 1
                self.log.error(f"Erreur critique dans la boucle principale : {e}")
                self.log.debug(traceback.format_exc())
                # Sleep court pour éviter les boucles d'erreurs serrées
                time.sleep(5)

        self.log.info("Boucle principale V3 arrêtée proprement.")

    def _process_symbols_parallel(self, symbols: list):
        """
        Traite tous les symboles EN PARALLÈLE avec un pool de threads.
        
        Chaque symbole a un timeout de SYMBOL_TIMEOUT_SECONDS pour éviter
        qu'un symbole bloqué ne retarde tout le cycle.
        
        Args:
            symbols: Liste des symboles à traiter
        """
        if not symbols:
            return

        with ThreadPoolExecutor(max_workers=self.max_parallel, thread_name_prefix="symbol_worker") as executor:
            # Soumettre tous les symboles
            future_to_symbol = {
                executor.submit(self._process_symbol_safe, symbol): symbol
                for symbol in symbols
                if self.bot.running and not self.bot.shutdown_event.is_set()
            }

            # Récupérer les résultats avec timeout
            for future in as_completed(future_to_symbol, timeout=self.symbol_timeout * len(symbols) + 5):
                symbol = future_to_symbol[future]
                try:
                    future.result(timeout=self.symbol_timeout)
                except FuturesTimeoutError:
                    self.log.warning(f"⏱️ Timeout ({self.symbol_timeout}s) pour {symbol} — cycle suivant")
                except Exception as e:
                    self.log.error(f"Erreur lors du traitement de {symbol} : {e}")

    def _process_symbol_safe(self, symbol: str):
        """
        Wrapper sécurisé autour de _process_symbol pour le threading.
        Gère les exceptions et assure la non-réentrance par symbole.
        """
        try:
            if not self.bot.running or self.bot.shutdown_event.is_set():
                return
            self._process_symbol(symbol)
        except Exception as e:
            self.log.error(f"Exception non capturée pour {symbol}: {e}")
            self.log.debug(traceback.format_exc())

    def _process_symbol(self, symbol: str):
        """
        Traite un symbole : fetch data → indicateurs → signal → exécution.
        
        V3 additions :
        - Hash check pour détecter les nouvelles données réelles
        - Mode live_conditions : slippage + commission simulés
        - Log de profiling détaillé en DEBUG
        """
        try:
            symbol_start_time = time.time()

            # === 1. FETCH DES DONNÉES MARCHÉ ===
            fetch_start = time.time()
            df = self._fetch_market_data(symbol)
            fetch_time = time.time() - fetch_start

            if df is None or len(df) < 50:
                self.log.debug(f"Données insuffisantes pour {symbol}: {len(df) if df is not None else 0} bougies")
                return

            # Check hash pour détecter les vraies nouvelles données
            df_hash = hashlib.md5(df.iloc[-1].to_string().encode()).hexdigest() if len(df) > 0 else None
            last_hash = self._data_hash_cache.get(symbol)
            data_changed = (df_hash != last_hash)
            self._data_hash_cache[symbol] = df_hash

            # === 2. CALCUL DES INDICATEURS TECHNIQUES ===
            indicators_start = time.time()
            with self.bot._lock:
                if symbol not in self.bot._indicators_cache or data_changed:
                    df_with_indicators = self.bot.technical_indicators.calculate_all_indicators(df.copy())
                    self.bot._indicators_cache[symbol] = df_with_indicators
                else:
                    df_with_indicators = self.bot._indicators_cache[symbol]
                self.bot.market_data[symbol] = df_with_indicators
            indicators_time = time.time() - indicators_start

            # === 3. GESTION DU RISQUE DES POSITIONS OUVERTES ===
            risk_start = time.time()
            self._update_active_position_risk(symbol, df_with_indicators)
            risk_time = time.time() - risk_start

            # === 4. VÉRIFICATIONS DE FILTRES ===
            # Symbole bloqué ?
            if symbol in self.bot.blocked_symbols:
                self.log.info(f"⛔ {symbol} bloqué pour cette session")
                return

            # Crypto active ?
            if self.bot.broker.get_asset_type() == "crypto":
                active_cryptos = getattr(self.bot, '_active_crypto_symbols', [])
                if active_cryptos and symbol not in active_cryptos:
                    return

            # Marché US ouvert ? (Alpaca uniquement)
            if self.bot.broker.get_asset_type() == "stock":
                if not self._is_us_market_open():
                    self.log.debug(f"Marché US fermé : skip {symbol}")
                    return

            # === 5. ANALYSE STRATÉGIE ET SIGNAL ===
            strategy_start = time.time()
            signal_data = self._compute_signal(symbol, df_with_indicators)
            strategy_time = time.time() - strategy_start

            if signal_data is None:
                return

            # === 6. FILTRES NEWS ===
            should_avoid, news_event = False, None
            if getattr(self.bot, 'news_manager', None):
                try:
                    should_avoid, news_event = self.bot.news_manager.should_avoid_trading_due_to_news(symbol)
                except Exception as e:
                    self.log.debug(f"NewsManager error pour {symbol}: {e}")

            score_raw = signal_data['total_score']
            score_min = signal_data.get('score_min', self.bot.strategy.score_min)
            rr = signal_data['rr_ratio']

            self.log.info(
                f"📊 Signal {symbol}: régime={signal_data['market_regime']} "
                f"score={score_raw:.1f}/{score_min} "
                f"L={signal_data['should_long']} S={signal_data['should_short']} "
                f"RR={rr:.2f} news_ok={not should_avoid}"
            )

            if should_avoid:
                self.log.info(f"📰 Trading évité pour {symbol} (news: {news_event.title if news_event else '?'})")
                return

            # === 7. EXÉCUTION DU SIGNAL ===
            if signal_data['should_long'] or signal_data['should_short']:
                trade_start = time.time()
                # En mode live_conditions : appliquer slippage simulé
                if self.trading_mode == 'live_conditions':
                    signal_data['_simulated_slippage'] = self.simulated_slippage
                    signal_data['_simulated_commission_pct'] = self.simulated_commission_pct
                self._execute_signal_trade(symbol, signal_data, df_with_indicators)
                trade_time = time.time() - trade_start
            else:
                self.log.info(
                    f"👁️  Scan {symbol} : {signal_data['market_regime']} | "
                    f"Score: {score_raw:.1f}/{score_min} | "
                    f"Pas de signal (Trigger L={signal_data['trigger_long']}, S={signal_data['trigger_short']}, RR={rr:.2f})"
                )
                trade_time = 0.0

            # === 8. LOG DE PROFILING ===
            total_time = time.time() - symbol_start_time
            self.log.debug(
                f"⏱️ Profiling {symbol}: "
                f"fetch={fetch_time:.2f}s indicators={indicators_time:.2f}s "
                f"risk={risk_time:.2f}s strategy={strategy_time:.2f}s "
                f"trade={trade_time:.2f}s TOTAL={total_time:.2f}s"
            )

        except Exception as e:
            self.bot.stats['errors_count'] += 1
            self.log.error(f"Erreur inattendue dans _process_symbol({symbol}): {e}")
            self.log.debug(traceback.format_exc())

    def _compute_signal(self, symbol: str, df_with_indicators) -> Optional[dict]:
        """
        Calcule le signal de trading en utilisant le cache du cycle.
        Thread-safe grâce au lock.
        """
        with self.bot._lock:
            if symbol in self.bot._strategy_cache:
                return self.bot._strategy_cache[symbol]

        # Données balance et Kelly
        real_balance = getattr(self.bot, '_cached_balance', 0.0)
        real_win_rate = None
        if (self.bot.risk_manager and
                len(self.bot.risk_manager.trade_history) >= self.bot.risk_manager.MIN_TRADES_FOR_KELLY):
            try:
                real_win_rate = self.bot.risk_manager._calculate_kelly_fraction()
            except Exception:
                pass

        # Changement BTC 24h (pour crypto uniquement)
        btc_change_24h = self._get_btc_24h_change()

        # Facteur de sentiment
        sentiment_factor = 1.0
        news_filter_passed = True
        if self.bot.news_manager:
            try:
                sentiment_factor = self.bot.news_manager.get_risk_factor()
                should_avoid, _ = self.bot.news_manager.should_avoid_trading_due_to_news(symbol)
                news_filter_passed = not should_avoid
            except Exception as e:
                self.log.debug(f"NewsManager error: {e}")

        try:
            signal_data = self.bot.strategy.analyze_market(
                df_with_indicators,
                account_balance=real_balance,
                real_win_rate=real_win_rate,
                symbol=symbol,
                btc_change_24h=btc_change_24h,
                sentiment_factor=sentiment_factor,
                news_filter_passed=news_filter_passed
            )
            signal_data['symbol'] = symbol

            with self.bot._lock:
                self.bot._strategy_cache[symbol] = signal_data

            return signal_data
        except Exception as e:
            self.log.error(f"Erreur analyse stratégie pour {symbol}: {e}")
            return None

    def _get_btc_24h_change(self) -> Optional[float]:
        """Calcule le changement BTC sur 24h depuis les données en cache (crypto only)."""
        if self.bot.broker.get_asset_type() != "crypto":
            return None

        # Essayer BTC/USDT ou BTCUSD (MT5 crypto)
        for btc_sym in ['BTC/USDT', 'BTCUSD']:
            btc_df = self.bot.market_data.get(btc_sym)
            if btc_df is not None and len(btc_df) >= 24:
                try:
                    price_now = float(btc_df.iloc[-1]['close'])
                    price_24h = float(btc_df.iloc[-24]['close'])
                    if price_24h > 0:
                        return (price_now - price_24h) / price_24h * 100.0
                except Exception:
                    pass
        return None

    def _is_us_market_open(self) -> bool:
        """Vérifie si le marché US est ouvert (Alpaca uniquement)."""
        if hasattr(self.bot.broker, '_api') and hasattr(self.bot.broker._api, 'get_clock'):
            try:
                clock = self.bot.broker._api.get_clock()
                return clock.is_open
            except Exception:
                return False
        return True  # Fallback permissif

    def _update_active_position_risk(self, symbol: str, df_with_indicators):
        """
        Met à jour trailing stops et break-evens pour les positions ouvertes.
        Thread-safe via lock.
        """
        with self.bot._lock:
            has_local_pos = symbol in self.bot.positions
            has_risk_pos = (self.bot.risk_manager is not None and
                           symbol in self.bot.risk_manager.open_positions)

        if not has_local_pos or not has_risk_pos:
            return

        try:
            current_price = df_with_indicators.iloc[-1]['close']
            atr_value = df_with_indicators.iloc[-1].get('atr', 0)

            pos_risk = self.bot.risk_manager.open_positions[symbol]
            pos_risk['atr_value'] = atr_value
            old_sl = pos_risk.get('stop_loss', 0.0)

            broker_pos = self.bot.broker.get_position(symbol)
            broker_tp = broker_pos.get('take_profit', 0.0) if broker_pos else 0.0
            broker_sl = broker_pos.get('stop_loss', 0.0) if broker_pos else 0.0

            self.bot.risk_manager.update_open_position(symbol, current_price)

            new_sl = pos_risk.get('stop_loss', 0.0)
            theoretical_tp = pos_risk.get('take_profit', 0.0)

            # Recalculer TP si manquant
            if theoretical_tp == 0.0:
                entry_price = pos_risk.get('entry_price', current_price)
                side = pos_risk.get('side', 'LONG')
                _, theoretical_tp = self.bot.risk_manager.calculate_sl_tp_levels(
                    entry_price=entry_price,
                    atr_value=atr_value,
                    position_side=side,
                    asset_type=self.bot.broker.get_asset_type(),
                    symbol=symbol
                )
                pos_risk['take_profit'] = theoretical_tp
                with self.bot._lock:
                    if symbol in self.bot.positions:
                        self.bot.positions[symbol]['take_profit'] = theoretical_tp

            # Mise à jour broker si SL a bougé significativement (deadband > 0.2 ATR)
            significant_move = abs(new_sl - old_sl) > (atr_value * 0.2)
            should_update = (significant_move and new_sl > 0) or \
                           (broker_sl == 0.0 and new_sl > 0) or \
                           (broker_tp == 0.0 and theoretical_tp > 0)

            if should_update:
                self.log.info(
                    f"📈 Mise à jour SL/TP {symbol}: "
                    f"SL {old_sl:.5f}→{new_sl:.5f} TP={theoretical_tp:.5f}"
                )
                success = self.bot.broker.modify_sl_tp(symbol, new_sl, theoretical_tp)
                if success:
                    with self.bot._lock:
                        if symbol in self.bot.positions:
                            self.bot.positions[symbol]['stop_loss'] = new_sl
                            self.bot.positions[symbol]['take_profit'] = theoretical_tp

        except Exception as e:
            self.log.warning(f"Erreur update position risk pour {symbol}: {e}")

    def _execute_signal_trade(self, symbol: str, signal_data: dict, df_with_indicators):
        """Délègue l'exécution à signal_executor."""
        from superbot.components.signal_executor import execute_signal_trade
        execute_signal_trade(self.bot, symbol, signal_data, df_with_indicators)

    def _fetch_market_data(self, symbol: str, limit: int = 500) -> Optional[Any]:
        """
        Récupère les données marché avec cache par cycle.
        
        V3: thread-safe, utilise _market_data_cache partagé.
        """
        with self.bot._lock:
            cache = getattr(self.bot, '_market_data_cache', {})
            if symbol in cache:
                return cache[symbol]

        try:
            timeframe = self.bot.GRANULARITY
            df = self.bot.broker.fetch_candles(symbol, timeframe, limit)

            if df is None or df.empty:
                self.log.warning(f"Pas de données pour {symbol}")
                return None

            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                self.log.warning(f"Colonnes manquantes pour {symbol}: {df.columns.tolist()}")
                return None

            with self.bot._lock:
                if not hasattr(self.bot, '_market_data_cache'):
                    self.bot._market_data_cache = {}
                self.bot._market_data_cache[symbol] = df

            return df

        except Exception as e:
            self.log.error(f"Erreur fetch données pour {symbol}: {e}")
            return None

    def get_heartbeat_status(self) -> dict:
        """
        Retourne le statut du heartbeat pour monitoring.
        Utilisé par le BugWatchdog et le dashboard.
        """
        now = time.time()
        time_since_last = now - self._last_heartbeat
        avg_cycle = sum(self._cycle_times) / len(self._cycle_times) if self._cycle_times else 0
        last_cycle = self._cycle_times[-1] if self._cycle_times else 0

        return {
            'last_heartbeat_ago_s': round(time_since_last, 1),
            'target_cycle_s': self.cycle_time,
            'last_cycle_s': round(last_cycle, 2),
            'avg_cycle_s': round(avg_cycle, 2),
            'is_healthy': time_since_last < self.cycle_time * 3,
            'cycles_completed': self.bot.stats.get('cycles_completed', 0),
        }


def run_main_loop(bot_instance):
    """Convenience function pour lancer la boucle principale V3."""
    manager = MainLoopManager(bot_instance)
    manager.run_main_loop()