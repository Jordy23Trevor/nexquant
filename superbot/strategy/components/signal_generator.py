import logging
import pandas as pd
import numpy as np
from typing import Tuple
log = logging.getLogger("signal_generator")

def _check_entry_triggers(
    self, df: pd.DataFrame, is_trending: bool,
    ema_fast_col: str = 'ema_fast', ema_slow_col: str = 'ema_slow',
    adx_threshold: float = 22.0,
    is_crypto: bool = False, is_forex: bool = False, is_stock: bool = False
) -> Tuple[bool, bool]:
    """
    Vérifie les conditions de déclenchement pour entrer en position.
    Les triggers sont adaptés à la classe d'actif :
    - Crypto : EMA cross + Pullback élargi (3 bougies) + Elder
    - Forex  : EMA cross + Inside Bar / Pin Bar (Price Action) + Elder
    - Stock  : EMA cross + Momentum relatif (Elder Impulse obligatoire)
    """
    if len(df) < 2:
        return False, False

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    trigger_long = False
    trigger_short = False

    if is_trending:
        if self.indicators.is_uptrend(df):
            # Utiliser les colonnes EMA spécifiques à l'asset_type
            ema_f_now  = latest.get(ema_fast_col, latest.get('ema_fast', 0))
            ema_s_now  = latest.get(ema_slow_col, latest.get('ema_slow', 0))
            ema_f_prev = prev.get(ema_fast_col, prev.get('ema_fast', 0))
            ema_s_prev = prev.get(ema_slow_col, prev.get('ema_slow', 0))

            ema_cross = (ema_f_now > ema_s_now and ema_f_prev <= ema_s_prev)
            macd_cross = (latest.get('macd', 0) > latest.get('macd_signal', 0) and
                        prev.get('macd', 0) <= prev.get('macd_signal', 0))
            supertrend_up = latest.get('supertrend_trend', 0) > 0 and prev.get('supertrend_trend', 0) <= 0

            # Pullback sur EMA lente : le prix a touché l'EMA lente et rebouncé dessus
            # Crypto : fenêtre élargie (3 bougies) pour capturer les retours de pression de vente
            if is_crypto and len(df) >= 3:
                prev2 = df.iloc[-3]
                pullback_long = (
                    ema_f_now > ema_s_now and
                    (prev['low'] <= ema_s_now or prev2.get(ema_slow_col, prev2.get('ema_slow', 0)) >= prev2['low']) and
                    latest['close'] > ema_s_now and
                    latest.get('supertrend_trend', 0) > 0 and
                    latest.get('rsi', 50) < 65
                )
            else:
                pullback_long = (
                    ema_f_now > ema_s_now and
                    prev['low'] <= ema_s_now and
                    latest['close'] > ema_s_now and
                    latest.get('supertrend_trend', 0) > 0 and
                    latest.get('rsi', 50) < 65
                )

            # ── TRIGGER CONTINUATION (nouveau) ──────────────────────────────────
            # Permet d'entrer sur une tendance déjà établie sans attendre un croisement EMA/MACD/ST rare.
            # Conditions : EMA fast > slow, Supertrend haussier, prix > EMA lente, RSI entre 45-65 (momentum sain)
            # Évite le biais de non-entry quand le bot rate le croisement initial mais la tendance continue.
            continuation_long = (
                ema_f_now > ema_s_now and
                latest.get('supertrend_trend', 0) > 0 and
                latest['close'] > ema_s_now and
                45 <= latest.get('rsi', 50) <= 68 and
                latest.get('macd', 0) > 0  # MACD positif = momentum haussier confirmé
            )

            # --- FOREX spécifique : ajouter Inside Bar / Pin Bar comme trigger ---
            # L'Inside Bar signale une compression avant breakout haussier
            inside_bar_long = False
            pin_bar_long = False
            if is_forex:
                # Inside Bar : high et low de prev contenus dans prev-prev
                if len(df) >= 3:
                    prev2 = df.iloc[-3]
                    inside_bar_long = (
                        prev['high'] <= prev2['high'] and
                        prev['low'] >= prev2['low'] and
                        latest['close'] > prev2['high']  # Breakout de l'inside bar
                    )
                # Pin Bar (Hammer) : ombrage inf long, corps court, trend haussier
                body = abs(latest['close'] - latest['open'])
                total = latest['high'] - latest['low'] if latest['high'] != latest['low'] else 1
                lower_wick = min(latest['open'], latest['close']) - latest['low']
                pin_bar_long = (
                    (lower_wick / total) > 0.55 and
                    (body / total) < 0.30 and
                    latest['close'] > latest['open'] and  # Bougie haussiere
                    ema_f_now > ema_s_now  # Dans le sens de la tendance
                )

            # --- STOCK/ETF : Elder Impulse vert obligatoire ---
            stock_momentum_long = False
            if is_stock:
                stock_momentum_long = latest.get('elder_impulse', 0) == 1  # Elder vert = trend+momentum alignés

            # --- RÈGLES ALEXANDER ELDER ---
            elder_allow_long = latest.get('elder_impulse', 0) != -1
            _screen1_val = latest.get('elder_screen1_up', None)
            elder_screen1_ok = (_screen1_val is None) or bool(_screen1_val)

            base_trigger = (ema_cross or macd_cross or supertrend_up or pullback_long or continuation_long)
            forex_trigger = base_trigger or inside_bar_long or pin_bar_long
            # ETF : Elder Impulse vert peut déclencher seul OU en combo avec un signal de base
            # Cela évite de rater les trades quand l'EMA cross est déjà passé mais Elder reste vert
            stock_trigger = stock_momentum_long and (base_trigger or stock_momentum_long)

            if is_forex:
                trigger_long = forex_trigger and elder_allow_long and elder_screen1_ok
            elif is_stock:
                trigger_long = stock_trigger and elder_screen1_ok
            else:  # crypto
                trigger_long = base_trigger and elder_allow_long and elder_screen1_ok

        elif self.indicators.is_downtrend(df):
            ema_f_now  = latest.get(ema_fast_col, latest.get('ema_fast', 0))
            ema_s_now  = latest.get(ema_slow_col, latest.get('ema_slow', 0))
            ema_f_prev = prev.get(ema_fast_col, prev.get('ema_fast', 0))
            ema_s_prev = prev.get(ema_slow_col, prev.get('ema_slow', 0))

            ema_cross = (ema_f_now < ema_s_now and ema_f_prev >= ema_s_prev)
            macd_cross = (latest.get('macd', 0) < latest.get('macd_signal', 0) and
                        prev.get('macd', 0) >= prev.get('macd_signal', 0))
            supertrend_down = latest.get('supertrend_trend', 0) < 0 and prev.get('supertrend_trend', 0) >= 0

            # Pullback SHORT
            pullback_short = (
                ema_f_now < ema_s_now and
                prev['high'] >= ema_s_now and
                latest['close'] < ema_s_now and
                latest.get('supertrend_trend', 0) < 0 and
                latest.get('rsi', 50) > 35
            )

            # ── TRIGGER CONTINUATION SHORT (nouveau) ─────────────────────────────
            continuation_short = (
                ema_f_now < ema_s_now and
                latest.get('supertrend_trend', 0) < 0 and
                latest['close'] < ema_s_now and
                32 <= latest.get('rsi', 50) <= 55 and
                latest.get('macd', 0) < 0  # MACD négatif = momentum baissier confirmé
            )

            # Forex : Inside Bar baissier / Shooting Star
            inside_bar_short = False
            pin_bar_short = False
            if is_forex and len(df) >= 3:
                prev2 = df.iloc[-3]
                inside_bar_short = (
                    prev['high'] <= prev2['high'] and
                    prev['low'] >= prev2['low'] and
                    latest['close'] < prev2['low']  # Breakout baissier
                )
                body = abs(latest['close'] - latest['open'])
                total = latest['high'] - latest['low'] if latest['high'] != latest['low'] else 1
                upper_wick = latest['high'] - max(latest['open'], latest['close'])
                pin_bar_short = (
                    (upper_wick / total) > 0.55 and
                    (body / total) < 0.30 and
                    latest['close'] < latest['open'] and
                    ema_f_now < ema_s_now
                )

            # --- RÈGLES ALEXANDER ELDER ---
            elder_allow_short = latest.get('elder_impulse', 0) != 1
            _screen1_down_val = latest.get('elder_screen1_down', None)
            elder_screen1_ok = (_screen1_down_val is None) or bool(_screen1_down_val)

            base_trigger = (ema_cross or macd_cross or supertrend_down or pullback_short or continuation_short)

            if is_forex:
                trigger_short = (base_trigger or inside_bar_short or pin_bar_short) and elder_allow_short and elder_screen1_ok
            else:  # crypto (stock n'a pas de short)
                trigger_short = base_trigger and elder_allow_short and elder_screen1_ok
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