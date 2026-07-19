"""
Main loop module for SuperBot.
Contains the main trading loop logic.
"""

import time
import threading
from datetime import datetime, timezone
from typing import Optional, Any
import hashlib
import logging

# Import statements will be resolved when used in the context of the bot

class MainLoopManager:
    """Manages the main trading loop of the SuperBot."""

    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.log = bot_instance.log

    def run_main_loop(self):
        """
        Main trading loop.
        This loop executes the trading cycle for each instrument.
        """
        self.log.info("Main trading loop started")

        while self.bot.running and not self.bot.shutdown_event.is_set():
            cycle_start_time = time.time()

            try:
                # Process Symbol Rotation for Crypto (if applicable)
                if hasattr(self.bot, '_select_and_rotate_crypto'):
                    self.bot._select_and_rotate_crypto()

                # Process each instrument
                for symbol in self.bot.instruments:
                    if not self.bot.running or self.bot.shutdown_event.is_set():
                        break
                    self._process_symbol(symbol)

                # Update dashboard
                if hasattr(self.bot, '_update_dashboard'):
                    self.bot._update_dashboard()

                # Update adaptive parameters periodically
                if hasattr(self.bot, '_update_adaptive_parameters'):
                    self.bot._adaptation_counter += 1
                    if self.bot._adaptation_counter >= self.bot._adaptation_every:
                        self.bot._update_adaptive_parameters()
                        self.bot._adaptation_counter = 0

                # Check for model drift periodically
                if hasattr(self.bot, '_detect_model_drift'):
                    self.bot._detect_model_drift()

                # Run walk-forward calibration periodically
                if hasattr(self.bot, '_run_walk_forward_calibration'):
                    self.bot._run_walk_forward_calibration()

                # Update cooldowns and save state periodically
                if hasattr(self.bot, '_save_cooldowns'):
                    # Save every 5 minutes or so
                    if time.time() - getattr(self.bot, '_last_state_save', 0) > 300:
                        self.bot._save_cooldowns()
                        self.bot._last_state_save = time.time()

                # Calculate cycle time and sleep if needed to maintain frequency
                cycle_time = time.time() - cycle_start_time
                target_cycle_time = getattr(self.bot, 'CYCLE_TIME', 60)  # Default 60 seconds
                if cycle_time < target_cycle_time:
                    time.sleep(target_cycle_time - cycle_time)

                # Update stats
                self.bot.stats['cycles_completed'] += 1
                self.bot.stats['last_cycle_time'] = time.time()

            except Exception as e:
                self.bot.stats['errors_count'] += 1
                self.log.error(f"Error in main loop: {e}")
                self.log.debug(traceback.format_exc())
                # Short sleep to prevent tight error loops
                time.sleep(5)

        self.log.info("Main trading loop stopped")

    def _process_symbol(self, symbol: str):
        """
        Process a specific symbol: fetch data, analyze, generate signals, execute trades.

        Args:
            symbol: Symbol to process (e.g., BTC/USDT)
        """
        try:
            # Measure total processing time for profiling
            symbol_start_time = time.time()

            # 1. Fetch recent market data
            fetch_start = time.time()
            df = self._fetch_market_data(symbol)
            fetch_time = time.time() - fetch_start
            if df is None or len(df) < 50:  # Minimum data required
                self.log.debug(f"Insufficient data for {symbol}: {len(df) if df is not None else 0} bars")
                return

            # Check if we have new data since last processing
            df_hash = hashlib.md5(df.iloc[-1].to_string().encode()).hexdigest() if len(df) > 0 else None
            last_hash = getattr(self, '_last_data_hash', {}).get(symbol)
            if df_hash == last_hash and len(df) > 0:
                # Same last bar, can skip processing except for position risk updates
                pass  # Continue for risk management
            else:
                # New data, update hash
                if not hasattr(self, '_last_data_hash'):
                    self._last_data_hash = {}
                self._last_data_hash[symbol] = df_hash

            # 2. Calculate technical indicators (with cycle caching)
            indicators_start = time.time()
            with self.bot._lock:
                if not hasattr(self.bot, '_indicators_cache'):
                    self.bot._indicators_cache = {}
                if symbol in self.bot._indicators_cache:
                    df_with_indicators = self.bot._indicators_cache[symbol]
                else:
                    df_with_indicators = self.bot.technical_indicators.calculate_all_indicators(df.copy())
                    self.bot._indicators_cache[symbol] = df_with_indicators
                self.bot.market_data[symbol] = df_with_indicators
            indicators_time = time.time() - indicators_start

            # === CONTINUOUS RISK MANAGEMENT FOR OPEN POSITIONS ===
            risk_start = time.time()
            self._update_active_position_risk(symbol, df_with_indicators)
            risk_time = time.time() - risk_start

            # 🚫 DYNAMIC BLOCKING: Skip if asset is blocked for this session
            if symbol in self.bot.blocked_symbols:
                self.log.info(f"⛔ {symbol} blocked for this session (cumulative loss > threshold)")
                return

            # If broker is crypto and symbol is not among selected assets
            if self.bot.broker.get_asset_type() == "crypto":
                active_cryptos = getattr(self.bot, '_active_crypto_symbols', [])
                if active_cryptos and symbol not in active_cryptos:
                    # Don't look to open new positions on this asset
                    return

            # 🕒 US SESSION FILTER (Alpaca/Stocks)
            if self.bot.broker.get_asset_type() == "stock":
                market_is_open = True

                # Check official Alpaca API
                if hasattr(self.bot.broker, '_api') and hasattr(self.bot.broker._api, 'get_clock'):
                    try:
                        clock = self.bot.broker._api.get_clock()
                        market_is_open = clock.is_open
                    except Exception as e:
                        self.log.warning(f"Error checking Alpaca clock: {e}")
                        market_is_open = False  # Err on the side of caution

                if not market_is_open:
                    self.log.debug(f"US market closed (Alpaca API): skip {symbol}")
                    return

            # 3. Analyze market and generate trading signal (with cycle caching)
            strategy_start = time.time()
            with self.bot._lock:
                if not hasattr(self.bot, '_strategy_cache'):
                    self.bot._strategy_cache = {}
                if symbol in self.bot._strategy_cache:
                    signal_data = self.bot._strategy_cache[symbol]
                else:
                    signal_data = None
            if signal_data is None:
                # Pass the real balance and actual Kelly calculated from history to the model
                _real_balance = getattr(self.bot, '_cached_balance', 0.0)
                _real_win_rate = None
                if (self.bot.risk_manager and
                    len(self.bot.risk_manager.trade_history) >= self.bot.risk_manager.MIN_TRADES_FOR_KELLY):
                    _real_win_rate = self.bot.risk_manager._calculate_kelly_fraction()

                # P1-1: Calculate 24h BTC change from cached market data
                _btc_change_24h = None
                if self.bot.broker.get_asset_type() == "crypto":
                    btc_sym = 'BTC/USDT'
                    btc_df_24h = self.bot.market_data.get(btc_sym)
                    if btc_df_24h is not None and len(btc_df_24h) >= 24:
                        try:
                            price_now = float(btc_df_24h.iloc[-1]['close'])
                            price_24h = float(btc_df_24h.iloc[-24]['close'])  # 24 H1 candles = 24h
                            if price_24h > 0:
                                _btc_change_24h = (price_now - price_24h) / price_24h * 100.0
                                self.log.debug(f"[P1-1] 24h BTC change: {_btc_change_24h:+.2f}%")
                        except Exception as _e:
                            self.log.debug(f"[P1-1] Could not calculate 24h BTC change: {_e}")

                # Get NLP factors and filters from NewsManager
                _sentiment_factor = 1.0
                _news_filter_passed = True
                if self.bot.news_manager:
                    try:
                        _sentiment_factor = self.bot.news_manager.get_risk_factor()
                        _should_avoid, _ = self.bot.news_manager.should_avoid_trading_due_to_news(symbol)
                        _news_filter_passed = not _should_avoid
                    except Exception as e:
                        self.log.debug(f"NewsManager error: {e}")

                signal_data = self.bot.strategy.analyze_market(
                    df_with_indicators,
                    account_balance=_real_balance,
                    real_win_rate=_real_win_rate,
                    symbol=symbol,
                    btc_change_24h=_btc_change_24h,
                    sentiment_factor=_sentiment_factor,
                    news_filter_passed=_news_filter_passed
                )
                signal_data['symbol'] = symbol
                with self.bot._lock:
                    self.bot._strategy_cache[symbol] = signal_data
            strategy_time = time.time() - strategy_start

            # DEBUG: Log signal details and pre-check news avoidance
            score_raw = signal_data['total_score']
            # Show effective score_min (per asset_type) rather than global
            score_min = signal_data.get('score_min', self.bot.strategy.score_min)
            rr = signal_data['rr_ratio']
            should_avoid, news_event = self.bot.news_manager.should_avoid_trading_due_to_news(symbol)
            news_ok = not should_avoid
            self.log.info(
                f"Signal DEBUG {symbol}: regime={signal_data['market_regime']} "
                f"score_raw={score_raw:.1f} score_min={score_min} "
                f"should_long={signal_data['should_long']} should_short={signal_data['should_short']} "
                f"RR={rr:.2f} news_ok={news_ok}"
            )

            if should_avoid:
                self.log.info(f"Trading avoided for {symbol} due to news: {news_event.title if news_event else 'Unknown'}")
                return
            elif signal_data['should_long'] or signal_data['should_short']:
                # Execute the trade
                trade_start = time.time()
                self._execute_signal_trade(symbol, signal_data, df_with_indicators)
                trade_time = time.time() - trade_start
            else:
                self.log.info(
                    f"Scan {symbol} : {signal_data['market_regime']} | "
                    f"Score: {score_raw:.1f}/{score_min} | "
                    f"No signal (Trigger L: {signal_data['trigger_long']}, S: {signal_data['trigger_short']}, R:R: {rr:.2f})"
                )

            # Log processing times for profiling (debug mode only)
            total_time = time.time() - symbol_start_time
            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug(
                    f"Profiling {symbol}: "
                    f"fetch={fetch_time:.3f}s, indicators={indicators_time:.3f}s, "
                    f"risk={risk_time:.3f}s, strategy={strategy_time:.3f}s, "
                    f"trade={trade_time if 'trade_time' in locals() else 0:.3f}s, "
                    f"total={total_time:.3f}s"
                )

        except Exception as e:
            self.bot.stats['errors_count'] += 1
            self.log.error(f"Unexpected error in _process_symbol for {symbol}: {e}")
            self.log.debug(traceback.format_exc())

    def _update_active_position_risk(self, symbol: str, df_with_indicators):
        """
        Update trailing stops and break-evens for open positions.

        Args:
            symbol: Symbol to update
            df_with_indicators: DataFrame with technical indicators
        """
        # Thread-safe snapshot of position existence
        with self.bot._lock:
            has_local_pos = symbol in self.bot.positions
            has_risk_pos = (self.bot.risk_manager is not None and
                          symbol in self.bot.risk_manager.open_positions)
        if not has_local_pos or not has_risk_pos:
            return

        current_price = df_with_indicators.iloc[-1]['close']
        atr_value = df_with_indicators.iloc[-1].get('atr', 0)

        # Update ATR in position for risk manager
        pos_risk = self.bot.risk_manager.open_positions[symbol]
        pos_risk['atr_value'] = atr_value

        old_sl = pos_risk.get('stop_loss', 0.0)

        # Get raw position from broker to check for real SL/TP orders
        broker_pos = self.bot.broker.get_position(symbol)
        broker_tp = broker_pos.get('take_profit', 0.0) if broker_pos else 0.0
        broker_sl = broker_pos.get('stop_loss', 0.0) if broker_pos else 0.0

        # Execute update (trailing stop / break-even calculation)
        self.bot.risk_manager.update_open_position(symbol, current_price)

        new_sl = pos_risk.get('stop_loss', 0.0)
        theoretical_tp = pos_risk.get('take_profit', 0.0)

        # Recalculate theoretical TP if missing
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
            self.log.info(f"Recalculated theoretical Take Profit for {symbol}: {theoretical_tp:.5f}")

        # Update if SL changed significantly (deadband > 0.2 ATR)
        significant_move = abs(new_sl - old_sl) > (atr_value * 0.2)
        should_update_broker = (significant_move and new_sl > 0) or \
                              (broker_sl == 0.0 and new_sl > 0) or \
                              (broker_tp == 0.0 and theoretical_tp > 0)

        if should_update_broker:
            self.log.info(f"Updating SL/TP for {symbol} with broker (SL: {old_sl:.5f} -> {new_sl:.5f}, TP: {theoretical_tp:.5f})")
            success = self.bot.broker.modify_sl_tp(symbol, new_sl, theoretical_tp)
            if success:
                # Update local position tracking dictionary
                with self.bot._lock:
                    if symbol in self.bot.positions:
                        self.bot.positions[symbol]['stop_loss'] = new_sl
                        self.bot.positions[symbol]['take_profit'] = theoretical_tp

    def _execute_signal_trade(self, symbol: str, signal_data: dict, df_with_indicators):
        """
        Validate macro filters, calculate position size safely, and execute order.

        Args:
            symbol: Symbol to trade
            signal_data: Signal data from strategy analysis
            df_with_indicators: DataFrame with technical indicators
        """
        from superbot.components.signal_executor import execute_signal_trade
        execute_signal_trade(self.bot, symbol, signal_data, df_with_indicators)

    def _fetch_market_data(self, symbol: str, limit: int = 500) -> Optional[Any]:
        """
        Fetch recent market data for a symbol.

        Args:
            symbol: Symbol to fetch
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data or None on error
        """
        # First check the trading cycle cache to avoid double API calls
        cache = getattr(self.bot, '_market_data_cache', {})
        if symbol in cache:
            return cache[symbol]

        try:
            # Use configured timeframe
            timeframe = self.bot.GRANULARITY

            # Fetch data from broker
            df = self.bot.broker.fetch_candles(symbol, timeframe, limit)

            if df is None or df.empty:
                self.log.warning(f"No data returned for {symbol}")
                return None

            # Ensure DataFrame has required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                self.log.warning(f"Missing columns in data for {symbol}: {df.columns.tolist()}")
                return None

            # Cache for this cycle
            if not hasattr(self.bot, '_market_data_cache'):
                self.bot._market_data_cache = {}
            self.bot._market_data_cache[symbol] = df

            return df

        except Exception as e:
            self.log.error(f"Error fetching data for {symbol}: {e}")
            return None


def run_main_loop(bot_instance):
    """Convenience function to run the main loop."""
    manager = MainLoopManager(bot_instance)
    manager.run_main_loop()