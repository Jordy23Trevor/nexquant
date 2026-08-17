import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
log = logging.getLogger('scorer')


# ── Poids des votes du score TRENDING ──────────────────────────────────────
# Le backtest (BTC/ETH 1h, ~137 trades, BE 1.5R) a montré que les votes sont
# largement redondants : ils mesurent tous la même chose (« c'est une tendance »),
# et le score ne sépare pas les bons trades des mauvais. Pouvoir prédictif mesuré :
#
#   elder_impulse_confirm : +6.1 pts   (seul vote à edge positif)
#   price_vs_ema200       : -0.8 pts   (~neutre)
#   ema_cross             : -5.9 pts
#   volume_confirmation   : -13.9 pts
#   macd_cross            : -16.9 pts
#
# Mais la re-pondération issue de ces edges ne s'est PAS montrée robuste :
#   - doubler elder_impulse ne change rien (votes corrélés : le score atteint déjà
#     le seuil quand elder est présent) ;
#   - retirer macd/volume améliore ETH mais dégrade BTC sous PF 1 (overfit d'un
#     échantillon de ~137 trades poolés sur deux actifs aux comportements opposés).
# Les poids restent donc NEUTRES (comportement d'origine). Le tableau ci-dessus
# sert de documentation pour une future calibration PAR CLASSE D'ACTIF sur un
# backtest walk-forward plus large.
TRENDING_VOTE_WEIGHTS = {
    'ema_cross': 1.0,
    'price_vs_ema200': 1.0,
    'htf_alignment': 1.0,
    'macd_cross': 1.0,
    'supertrend': 1.0,
    'adx_strength': 1.0,
    'trend_momentum': 1.0,
    'volume_confirmation': 1.0,
    'elder_impulse_confirm': 1.0,
}


def _append_candidate_signals(details: Dict[str, Any], df: pd.DataFrame,
                              latest: pd.Series, price: float,
                              ema_slow: float, adx: float) -> None:
    """Ajoute les signaux candidats indépendants (mesurés, non notés) à details.

    Ces features sont enregistrées dans entry_details du backtest pour mesurer
    leur pouvoir prédictif (artifacts/measure_score_signals.py) sans modifier
    le score lui-même.
    """
    _atr = latest.get('atr', 0.0) or 0.0
    details['sig_adx'] = float(adx or 0.0)
    details['sig_dist_ema_atr'] = float((price - ema_slow) / _atr) if _atr > 0 else 0.0
    details['sig_rsi'] = float(latest.get('rsi', 50.0) or 50.0)
    _bbp = latest.get('bb_percent', 0.5)
    details['sig_bb_percent'] = float(_bbp) if not pd.isna(_bbp) else 0.5
    _hist = latest.get('macd_histogram', 0.0) or 0.0
    _hist_prev = (df.iloc[-4].get('macd_histogram', 0.0) if len(df) >= 4 else 0.0) or 0.0
    details['sig_macd_hist_slope'] = float((_hist - _hist_prev) / _atr) if _atr > 0 else 0.0
    _vol_ma = latest.get('volume_ma', 0.0) or 0.0
    details['sig_vol_ratio'] = float(latest.get('volume', 0.0) / _vol_ma) if _vol_ma > 0 else 0.0
    if 'atr' in df.columns and len(df) >= 100 and _atr > 0:
        details['sig_atr_rank'] = float((df['atr'].iloc[-100:] < _atr).mean())
    else:
        details['sig_atr_rank'] = 0.5
    if len(df) >= 20:
        _hi20 = df['high'].iloc[-20:].max()
        _lo20 = df['low'].iloc[-20:].min()
        details['sig_donchian_pos'] = float((price - _lo20) / (_hi20 - _lo20)) if _hi20 != _lo20 else 0.5
    else:
        details['sig_donchian_pos'] = 0.5


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
            score += TRENDING_VOTE_WEIGHTS['ema_cross']
            details['ema_cross'] = 1
        else:
            details['ema_cross'] = 0
    elif self.indicators.is_downtrend(df):
        if price_below_ema and ema_cross_bearish:
            score += TRENDING_VOTE_WEIGHTS['ema_cross']
            details['ema_cross'] = 1
        else:
            details['ema_cross'] = 0
    else:
        details['ema_cross'] = 0

    # 2. Prix vs EMA200 (tendance de long terme) - 1 point
    ema_trend = latest.get('ema_trend', 0)
    if self.indicators.is_uptrend(df):
        if price > ema_trend:
            score += TRENDING_VOTE_WEIGHTS['price_vs_ema200']
            details['price_vs_ema200'] = 1
        else:
            details['price_vs_ema200'] = 0
    elif self.indicators.is_downtrend(df):
        if price < ema_trend:
            score += TRENDING_VOTE_WEIGHTS['price_vs_ema200']
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
            score += TRENDING_VOTE_WEIGHTS['htf_alignment']
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
            score += TRENDING_VOTE_WEIGHTS['macd_cross']
            details['macd_cross'] = 1
        else:
            details['macd_cross'] = 0
    elif self.indicators.is_downtrend(df):
        if macd_cross_bearish or (macd < 0 and macd_signal < 0):
            score += TRENDING_VOTE_WEIGHTS['macd_cross']
            details['macd_cross'] = 1
        else:
            details['macd_cross'] = 0
    else:
        details['macd_cross'] = 0

    # 5. Supertrend direction - 1 point
    supertrend_trend = latest.get('supertrend_trend', 0)
    if self.indicators.is_uptrend(df):
        if supertrend_trend > 0:
            score += TRENDING_VOTE_WEIGHTS['supertrend']
            details['supertrend'] = 1
        else:
            details['supertrend'] = 0
    elif self.indicators.is_downtrend(df):
        if supertrend_trend < 0:
            score += TRENDING_VOTE_WEIGHTS['supertrend']
            details['supertrend'] = 1
        else:
            details['supertrend'] = 0
    else:
        details['supertrend'] = 0

    # 6. ADX strength (confirmation de tendance) - 1 point
    adx = latest.get('adx', 0)
    if adx > adx_threshold:
        score += TRENDING_VOTE_WEIGHTS['adx_strength']
        details['adx_strength'] = 1
    else:
        details['adx_strength'] = 0

    # 7. DI+ > DI- (pour tendance haussière) ou DI- > DI+ (pour tendance baissière) - 1 point
    plus_di = latest.get('plus_di', 0)
    minus_di = latest.get('minus_di', 0)
    if self.indicators.is_uptrend(df):
        if plus_di > minus_di:
            score += TRENDING_VOTE_WEIGHTS['trend_momentum']
            details['trend_momentum'] = 1
        else:
            details['trend_momentum'] = 0
    elif self.indicators.is_downtrend(df):
        if minus_di > plus_di:
            score += TRENDING_VOTE_WEIGHTS['trend_momentum']
            details['trend_momentum'] = 1
        else:
            details['trend_momentum'] = 0
    else:
        details['trend_momentum'] = 0

    # 8. Chaikin Money Flow ou MFI confirmation (volume) - 1 point bonus
    mfi = latest.get('mfi', 50)
    if self.indicators.is_uptrend(df):
        if mfi > 50:  # Pression d'achat
            score += TRENDING_VOTE_WEIGHTS['volume_confirmation']
            details['volume_confirmation'] = 1
        else:
            details['volume_confirmation'] = 0
    elif self.indicators.is_downtrend(df):
        if mfi < 50:  # Pression de vente
            score += TRENDING_VOTE_WEIGHTS['volume_confirmation']
            details['volume_confirmation'] = 1
        else:
            details['volume_confirmation'] = 0
    else:
        details['volume_confirmation'] = 0

    # 9. Alexander Elder Impulse System confirmation - 1 point bonus
    elder_impulse = latest.get('elder_impulse', 0)
    if self.indicators.is_uptrend(df):
        if elder_impulse == 1:  # Vert (EMA13 en hausse et MACD histogramme en hausse)
            score += TRENDING_VOTE_WEIGHTS['elder_impulse_confirm']
            details['elder_impulse_confirm'] = 1
        else:
            details['elder_impulse_confirm'] = 0
    elif self.indicators.is_downtrend(df):
        if elder_impulse == -1:  # Rouge (EMA13 en baisse et MACD histogramme en baisse)
            score += TRENDING_VOTE_WEIGHTS['elder_impulse_confirm']
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

    # Signaux candidats indépendants (mesurés, non notés).
    _append_candidate_signals(details, df, latest, price, ema_slow, adx)

    # S'assurer que le score ne dépasse pas 10
    score = min(score, 10)

    return score, details


def _calculate_trending_score_signals(
    self, df: pd.DataFrame,
    ema_fast_col: str = 'ema_fast',
    ema_slow_col: str = 'ema_slow',
    adx_threshold: float = 22.0,
    asset_hint: str = ""
) -> Tuple[float, Dict[str, Any]]:
    """Score de tendance reconstruit sur des signaux INDÉPENDANTS (mesurés).

    Remplace les 9 votes redondants de l'ancien score (qui mesuraient tous
    « c'est une tendance ») par 4 dimensions orthogonales, calibrées sur le
    backtest (BTC/ETH 1h, 137 trades) :

      1. Elder Impulse (direction + momentum alignés)     — +2 pts
         (seul vote de l'ancien score à edge positif mesuré, +6.1 pts)
      2. Volatilité en expansion (percentile ATR > 50 %)  — +2 pts
         (edge positif mesuré sur BTC ET ETH : +0.29/+0.33 PF)
      3. Extension vs EMA lente, direction selon l'actif  — +2 pts
         (BTC = momentum : extension OK ; altcoin = mean-reversion : pullback OK)
      4. ADX modéré (<= 35, pas d'exhaustion de tendance) — +2 pts
         (l'ancien vote « ADX > 22 » était anti-prédictif)

    Plus le bonus divergence conservé (0-1 pt). Total max 9.
    """
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    uptrend = self.indicators.is_uptrend(df)
    downtrend = self.indicators.is_downtrend(df)

    score = 0.0
    details = {}

    price = latest['close']
    ema_slow = latest.get(ema_slow_col, latest.get('ema_slow', price))
    atr = latest.get('atr', 0.0) or 0.0

    # 1. Elder Impulse — ancre de direction/momentum (+2)
    elder_impulse = latest.get('elder_impulse', 0)
    if (uptrend and elder_impulse == 1) or (downtrend and elder_impulse == -1):
        score += 2.0
        details['elder_impulse_confirm'] = 1
    else:
        details['elder_impulse_confirm'] = 0

    # 2. Volatilité en expansion (+2)
    if 'atr' in df.columns and len(df) >= 100 and atr > 0:
        atr_rank = float((df['atr'].iloc[-100:] < atr).mean())
    else:
        atr_rank = 0.5
    if atr_rank > 0.5:
        score += 2.0
        details['vol_expansion'] = 1
    else:
        details['vol_expansion'] = 0

    # 3. Extension vs EMA lente — direction selon l'actif (+2)
    dist_ema_atr = (price - ema_slow) / atr if atr > 0 else 0.0
    if asset_hint == 'BTC':
        ext_ok = dist_ema_atr > 0.0       # momentum : la tendance s'étend
    elif asset_hint == 'ALTCOIN':
        ext_ok = dist_ema_atr <= 1.0      # mean-reversion : pas de sur-extension
    elif asset_hint == 'STOCK':
        ext_ok = dist_ema_atr > -1.0      # neutre conservateur
    else:  # FOREX / inconnu : pas de filtre d'extension
        ext_ok = True
    if ext_ok:
        score += 2.0
        details['extension_ok'] = 1
    else:
        details['extension_ok'] = 0

    # 4. ADX modéré (+2) — ADX élevé signe souvent l'exhaustion de tendance
    adx = latest.get('adx', 0.0) or 0.0
    if adx <= 35.0:
        score += 2.0
        details['adx_moderate'] = 1
    else:
        details['adx_moderate'] = 0

    # Bonus divergence (conservé, 0-1 pt)
    rsi_div_bull = latest.get('rsi_divergence_bullish', False)
    rsi_div_bear = latest.get('rsi_divergence_bearish', False)
    macd_div_bull = latest.get('macd_divergence_bullish', False)
    macd_div_bear = latest.get('macd_divergence_bearish', False)
    obv_div_bull = latest.get('obv_divergence_bullish', False)
    obv_div_bear = latest.get('obv_divergence_bearish', False)

    bonus_score = 0
    if uptrend and (rsi_div_bull or macd_div_bull or obv_div_bull):
        bonus_score += 1
    elif downtrend and (rsi_div_bear or macd_div_bear or obv_div_bear):
        bonus_score += 1

    score += bonus_score
    details['divergence_bonus'] = bonus_score

    # Signaux candidats indépendants (mesurés, non notés).
    _append_candidate_signals(details, df, latest, price, ema_slow, adx)

    score = min(score, 10.0)
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


def calculate_probabilistic_win_rate(score: float, market_regime: str = "TRENDING", adx_value: float = 20.0, rr_ratio: float = 2.0) -> Dict[str, Any]:
    """
    Estime la probabilité de réussite P(Win) et l'espérance mathématique E(R) du trade.

    E(R) = P(Win) * RR - (1 - P(Win)) * 1.0

    L'ancienne formule linéaire (0.35 + score/10*0.40) annonçait 59-75% de gain
    là où le win rate réalisé est ~25%. Elle est remplacée par une calibration
    empirique sur les trades réels (WinRateCalibrator), avec un prior prudent
    en l'absence d'historique. market_regime/adx_value restent dans la signature
    pour compatibilité mais ne gonflent plus artificiellement la probabilité.
    """
    from superbot.ml.win_rate_calibrator import get_calibrator

    win_prob = get_calibrator().predict(score)
    win_prob = max(win_prob, 0.05)

    expected_value = (win_prob * rr_ratio) - ((1.0 - win_prob) * 1.0)
    # Edge = espérance strictement positive (seuil de rentabilité 1/(1+RR)).
    has_statistical_edge = expected_value > 0

    return {
        'win_prob': round(win_prob, 3),
        'expected_value': round(expected_value, 3),
        'has_edge': has_statistical_edge
    }