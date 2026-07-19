import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
log = logging.getLogger('scorer')


def _calculate_trending_score(
    self, df: pd.DataFrame,
    ema_fast_col: str = 'ema_fast',
    ema_slow_col: str = 'ema_slow',
    adx_threshold: float = 22.0
) -> Tuple[float, Dict[str, Any]]:
    """
    Calcule le score pour un marché en tendance.
    Utilise les colonnes EMA spécifiques à l'asset_type (crypto=EMA21/55, forex=EMA21/55, stock=EMA20/50).

    Returns:
        Tuple de (score, détails)
    """
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    score = 0
    details = {}

    # 1. EMA croisée (colonnes spécifiques à l'asset_type) - 1 point
    ema_fast = latest.get(ema_fast_col, latest.get('ema_fast', 0))
    ema_slow = latest.get(ema_slow_col, latest.get('ema_slow', 0))
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