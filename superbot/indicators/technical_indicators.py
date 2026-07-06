"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╩
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
import logging

# Importer les fonctions de base

log = logging.getLogger("indicators.technical_indicators")


class TechnicalIndicators:
    """
    Classe pour calculer tous les indicateurs techniques nécessaires à la stratégie.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le calculateur d'indicateurs avec la configuration.

        Args:
            config: Dictionnaire contenant les paramètres des indicateurs
                   (EMA_FAST, EMA_SLOW, RSI_LEN, etc.)
        """
        self.config = config
        # Détecteur de régime HMM (chargé lazily au premier appel)
        self._regime_detector = None
        self._hmm_loaded = False  # Flag pour éviter les tentatives répétées
        log.debug(f"TechnicalIndicators initialisé avec config: {list(config.keys())}")

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule tous les indicateurs techniques sur un DataFrame OHLCV.

        Args:
            df: DataFrame avec colonnes ['open', 'high', 'low', 'close', 'volume']
                et index datetime

        Returns:
            DataFrame avec tous les indicateurs ajoutés en colonnes
        """
        # Importer les fonctions de base localement pour éviter les imports circulaires
        from superbot.strategy.knowledge_base import (
            calculate_atr, calculate_ema, calculate_sma, calculate_rsi,
            calculate_macd, calculate_adx, calculate_supertrend,
            calculate_bollinger_bands, calculate_ichimoku, calculate_vwap,
            detect_divergence
        )
        # S'assurer que nous avons les colonnes nécessaires
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            log.error(f"Colonnes manquantes dans le DataFrame: {missing}")
            return df

        # Travailler sur une copie pour éviter les SettingWithCopyWarning
        result = df.copy()

        # Extraire les séries pour faciliter les calculs
        open_price = result['open']
        high_price = result['high']
        low_price = result['low']
        close_price = result['close']
        volume = result['volume']

        # === MOYENNES MOBILES ===
        # EMA
        result['ema_fast'] = calculate_ema(close_price, self.config.get('EMA_FAST', 9))
        result['ema_slow'] = calculate_ema(close_price, self.config.get('EMA_SLOW', 21))
        result['ema_trend'] = calculate_ema(close_price, self.config.get('EMA_TREND', 200))
        result['ema_htf'] = calculate_ema(close_price, self.config.get('HTF_EMA', 50))
        result['ema_d1'] = calculate_ema(close_price, self.config.get('D1_EMA', 50))
        result['ema_w1'] = calculate_ema(close_price, self.config.get('W1_EMA', 20))

        # SMA (pour certaines utilisations spécifiques)
        result['sma_20'] = calculate_sma(close_price, 20)
        result['sma_50'] = calculate_sma(close_price, 50)

        # === OSCILLATEURS ===
        # RSI
        result['rsi'] = calculate_rsi(close_price, self.config.get('RSI_LEN', 14))

        # MACD
        macd_line, signal_line, histogram = calculate_macd(
            close_price,
            self.config.get('MACD_FAST', 12),
            self.config.get('MACD_SLOW', 26),
            self.config.get('MACD_SIGNAL', 9)
        )
        result['macd'] = macd_line
        result['macd_signal'] = signal_line
        result['macd_histogram'] = histogram

        # === INDICATEURS DE TENDANCE ===
        # ADX
        result['adx'] = calculate_adx(high_price, low_price, close_price, self.config.get('ADX_LEN', 14))

        # Supertrend
        supertrend, trend = calculate_supertrend(
            high_price, low_price, close_price,
            self.config.get('ST_ATR_LEN', 10),
            self.config.get('ST_MULTIPLIER', 3.0)
        )
        result['supertrend'] = supertrend
        result['supertrend_trend'] = trend  # 1 pour haussier, -1 pour baissier

        # Bandes de Bollinger
        upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(
            close_price,
            self.config.get('BB_LEN', 20),
            self.config.get('BB_STD', 2.0)
        )
        result['bb_upper'] = upper_bb
        result['bb_middle'] = middle_bb
        result['bb_lower'] = lower_bb
        result['bb_width'] = (upper_bb - lower_bb) / middle_bb  # Largeur des bandes
        result['bb_percent'] = (close_price - lower_bb) / (upper_bb - lower_bb)  # Position dans les bandes (%B)

        # === ICHIMOKU CLOUD ===
        ichimoku = calculate_ichimoku(
            high_price, low_price, close_price,
            self.config.get('ICHIMOKU_TENKAN', 9),
            self.config.get('ICHIMOKU_KIJUN', 26),
            self.config.get('ICHIMOKU_SENKOU_SPAN_B', 52),
            self.config.get('ICHIMOKU_DISPLACEMENT', 26)
        )
        result['ichimoku_tenkan'] = ichimoku['tenkan_sen']
        result['ichimoku_kijun'] = ichimoku['kijun_sen']
        result['ichimoku_senkou_a'] = ichimoku['senkou_span_a']
        result['ichimoku_senkou_b'] = ichimoku['senkou_span_b']
        result['ichimoku_chikou'] = ichimoku['chikou_span']

        # Le nuage (cloud) est entre senkou_span_a et senkou_span_b
        result['ichimoku_cloud_top'] = ichimoku['senkou_span_a'].combine_first(ichimoku['senkou_span_b'])
        result['ichimoku_cloud_bottom'] = ichimoku['senkou_span_b'].combine_first(ichimoku['senkou_span_a'])

        # === VWAP ===
        result['vwap'] = calculate_vwap(high_price, low_price, close_price, volume, self.config.get('VWAP_WINDOW', 14))

        # === ATR (pour le risk management) ===
        result['atr'] = calculate_atr(high_price, low_price, close_price, self.config.get('ATR_LEN', 14))

        # === PIVOT POINTS (supports et résistances dynamiques quotidiens) ===
        try:
            # Resampler en journalier pour obtenir les niveaux High, Low, Close du jour précédent
            df_temp = result.copy()
            if not isinstance(df_temp.index, pd.DatetimeIndex):
                df_temp.index = pd.to_datetime(df_temp.index)
            
            daily = df_temp.resample('D').agg({
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }).dropna()
            
            # Shift d'un jour pour utiliser les données de la veille
            daily_prev = daily.shift(1)
            
            daily_prev['pivot'] = (daily_prev['high'] + daily_prev['low'] + daily_prev['close']) / 3
            daily_prev['r1'] = (2 * daily_prev['pivot']) - daily_prev['low']
            daily_prev['s1'] = (2 * daily_prev['pivot']) - daily_prev['high']
            daily_prev['r2'] = daily_prev['pivot'] + (daily_prev['high'] - daily_prev['low'])
            daily_prev['s2'] = daily_prev['pivot'] - (daily_prev['high'] - daily_prev['low'])
            
            # Aligner les valeurs quotidiennes avec les lignes horaires de manière robuste sans reset_index
            date_only = df_temp.index.normalize()
            result['pivot'] = pd.Series(date_only.map(daily_prev['pivot']), index=result.index).ffill().bfill()
            result['r1'] = pd.Series(date_only.map(daily_prev['r1']), index=result.index).ffill().bfill()
            result['s1'] = pd.Series(date_only.map(daily_prev['s1']), index=result.index).ffill().bfill()
            result['r2'] = pd.Series(date_only.map(daily_prev['r2']), index=result.index).ffill().bfill()
            result['s2'] = pd.Series(date_only.map(daily_prev['s2']), index=result.index).ffill().bfill()
        except Exception as e:
            log.warning(f"Impossible de calculer les pivots quotidiens resamplés ({e}), repli sur pivots par bougie.")
            # Repli sur le calcul simple basé sur la bougie précédente
            prev_high = result['high'].shift(1)
            prev_low = result['low'].shift(1)
            prev_close = result['close'].shift(1)
            result['pivot'] = (prev_high + prev_low + prev_close) / 3
            result['r1'] = (2 * result['pivot']) - prev_low
            result['s1'] = (2 * result['pivot']) - prev_high
            result['r2'] = result['pivot'] + (prev_high - prev_low)
            result['s2'] = result['pivot'] - (prev_high - prev_low)


        # === INDICATEURS SUPPLÉMENTAIRES ===
        # Stochastic Oscillator (pour les marchés en range)
        result['stoch_k'], result['stoch_d'] = self._calculate_stochastic(
            high_price, low_price, close_price,
            k_period=self.config.get('STOCH_K_PERIOD', 14),
            d_period=self.config.get('STOCH_D_PERIOD', 3)
        )

        # Williams %R
        result['williams_r'] = self._calculate_williams_r(
            high_price, low_price, close_price,
            period=self.config.get('WILLIAMS_R_PERIOD', 14)
        )

        # Commodity Channel Index (CCI)
        result['cci'] = self._calculate_cci(
            high_price, low_price, close_price,
            period=self.config.get('CCI_PERIOD', 20)
        )

        # Money Flow Index (MFI)
        result['mfi'] = self._calculate_mfi(
            high_price, low_price, close_price, volume,
            period=self.config.get('MFI_PERIOD', 14)
        )

        # On-Balance Volume (OBV)
        result['obv'] = self._calculate_obv(close_price, volume)

        # === DÉTECTION DE DIVERGENCES ===
        # Divergences RSI
        result['rsi_divergence_bullish'], result['rsi_divergence_bearish'] = detect_divergence(
            close_price, result['rsi'], lookback=self.config.get('DIVERGENCE_LOOKBACK', 10)
        )

        # Divergences MACD
        result['macd_divergence_bullish'], result['macd_divergence_bearish'] = detect_divergence(
            close_price, result['macd'], lookback=self.config.get('DIVERGENCE_LOOKBACK', 10)
        )

        # Divergences OBV
        result['obv_divergence_bullish'], result['obv_divergence_bearish'] = detect_divergence(
            close_price, result['obv'], lookback=self.config.get('DIVERGENCE_LOOKBACK', 10)
        )

        # === Indicateurs des stratégies Alexander Elder & Thami Kabbaj ===
        # 1. Alexander Elder Impulse System
        ema_13 = calculate_ema(close_price, 13)
        result['elder_ema'] = ema_13
        
        ema_13_up = ema_13 > ema_13.shift(1)
        ema_13_down = ema_13 < ema_13.shift(1)
        macd_hist_up = result['macd_histogram'] > result['macd_histogram'].shift(1)
        macd_hist_down = result['macd_histogram'] < result['macd_histogram'].shift(1)
        
        # Par défaut : Bleu (Neutre, 0)
        result['elder_impulse'] = 0
        # Vert (Fortement haussier, 1)
        result.loc[ema_13_up & macd_hist_up, 'elder_impulse'] = 1
        # Rouge (Fortement baissier, -1)
        result.loc[ema_13_down & macd_hist_down, 'elder_impulse'] = -1

        # 2. Alexander Elder Triple Screen (Screen 1 : Tendance de fond HTF)
        result['elder_screen1_up'] = result['ema_htf'] > result['ema_htf'].shift(1)
        result['elder_screen1_down'] = result['ema_htf'] < result['ema_htf'].shift(1)

        # 3. Thami Kabbaj - Volatility Compression Squeeze
        bb_width_min = result['bb_width'].rolling(100).min()
        bb_width_max = result['bb_width'].rolling(100).max()
        result['kabbaj_squeeze'] = result['bb_width'] <= (bb_width_min + 0.25 * (bb_width_max - bb_width_min))

        log.debug(f"Indicateurs calculés pour {len(result)} périodes")
        return result

    def _calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series,
                             k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Calcule l'oscillateur Stochastique.

        Returns:
            Tuple de (%K, %D)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent

    def _calculate_williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series,
                             period: int = 14) -> pd.Series:
        """
        Calcule le Williams %R.

        Returns:
        Série contenant les valeurs de Williams %R (-100 à 0)
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))
        return williams_r

    def _calculate_cci(self, high: pd.Series, low: pd.Series, close: pd.Series,
                      period: int = 20) -> pd.Series:
        """
        Calcule le Commodity Channel Index (CCI).

        Returns:
        Série contenant les valeurs du CCI
        """
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
        )
        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        return cci

    def _calculate_mfi(self, high: pd.Series, low: pd.Series, close: pd.Series,
                      volume: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcule le Money Flow Index (MFI).

        Returns:
        Série contenant les valeurs du MFI (0-100)
        """
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume

        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()

        money_ratio = positive_mf / negative_mf
        mfi = 100 - (100 / (1 + money_ratio))
        return mfi

    def _calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Calcule l'On-Balance Volume (OBV).

        Returns:
        Série contenant les valeurs de l'OBV
        """
        direction = np.sign(close.diff()).fillna(0)
        obv = (direction * volume).fillna(0).cumsum()
        return obv

    # === MÉTHODES D'ANALYSE DE MARCHÉ ===

    def get_market_regime(self, df: pd.DataFrame) -> str:
        """
        Détermine le régime de marché actuel (TRENDING ou RANGING).
        Utilise le modèle HMM si disponible, sinon la règle ADX (fallback).

        Args:
            df: DataFrame avec les indicateurs calculés

        Returns:
            'TRENDING' ou 'RANGING'
        """
        regime, _, _ = self.get_market_regime_with_confidence(df)
        return regime

    def get_market_regime_with_confidence(self, df: pd.DataFrame) -> tuple:
        """
        Détermine le régime de marché avec un score de confiance ML.

        Utilise le modèle HMM (Phase 2) si le fichier .pkl est disponible,
        sinon replie sur la règle ADX classique (ADX > seuil -> TRENDING).

        Args:
            df: DataFrame avec les indicateurs calculés

        Returns:
            Tuple (regime: str, confidence: float, hmm_state: int)
            - regime     : 'TRENDING' ou 'RANGING'
            - confidence : probabilité de l'état prédit (0.5 si fallback ADX)
            - hmm_state  : index de l'état HMM (-1 si fallback ADX)
        """
        if len(df) == 0:
            return 'RANGING', 0.5, -1

        # Chargement lazy du modèle HMM (une seule fois)
        if not self._hmm_loaded:
            self._hmm_loaded = True
            try:
                from superbot.ml.regime_detector import MarketRegimeDetector
                self._regime_detector = MarketRegimeDetector.load()
                if self._regime_detector._is_trained:
                    log.info("[TechnicalIndicators] Modele HMM charge avec succes.")
                else:
                    log.info("[TechnicalIndicators] HMM non entraine — fallback ADX actif.")
            except Exception as e:
                log.debug(f"[TechnicalIndicators] HMM indisponible ({e}) — fallback ADX.")
                self._regime_detector = None

        # Prédiction HMM si disponible
        if self._regime_detector is not None and self._regime_detector._is_trained:
            try:
                regime, confidence, hmm_state = self._regime_detector.predict(df)
                return regime, confidence, hmm_state
            except Exception as e:
                log.debug(f"[TechnicalIndicators] Erreur HMM ({e}) — fallback ADX")

        # Fallback ADX
        latest = df.iloc[-1]
        adx_value = latest.get('adx', 0)
        adx_threshold = self.config.get('ADX_TREND', 22.0)

        if adx_value > adx_threshold:
            return 'TRENDING', 0.50, -1
        else:
            return 'RANGING', 0.50, -1

    def is_uptrend(self, df: pd.DataFrame) -> bool:
        """
        Détermine si le marché est en tendance haussière.

        Args:
            df: DataFrame avec les indicateurs calculés

        Returns:
            True si en tendance haussière, False sinon
        """
        if len(df) == 0:
            return False

        latest = df.iloc[-1]
        # Plusieurs conditions pour confirmer une tendance haussière
        price_above_ema200 = latest['close'] > latest.get('ema_trend', 0)
        ema_fast_above_slow = latest.get('ema_fast', 0) > latest.get('ema_slow', 0)
        macd_positive = latest.get('macd_histogram', 0) > 0
        supertrend_uptrend = latest.get('supertrend_trend', 0) > 0

        # Au moins 3 conditions sur 4 doivent être vraies
        conditions = [price_above_ema200, ema_fast_above_slow, macd_positive, supertrend_uptrend]
        return sum(conditions) >= 3

    def is_downtrend(self, df: pd.DataFrame) -> bool:
        """
        Détermine si le marché est en tendance baissière.

        Args:
            df: DataFrame avec les indicateurs calculés

        Returns:
            True si en tendance baissière, False sinon
        """
        if len(df) == 0:
            return False

        latest = df.iloc[-1]
        # Plusieurs conditions pour confirmer une tendance baissière
        price_below_ema200 = latest['close'] < latest.get('ema_trend', 0)
        ema_fast_below_slow = latest.get('ema_fast', 0) < latest.get('ema_slow', 0)
        macd_negative = latest.get('macd_histogram', 0) < 0
        supertrend_downtrend = latest.get('supertrend_trend', 0) < 0

        # Au moins 3 conditions sur 4 doivent être vraies
        conditions = [price_below_ema200, ema_fast_below_slow, macd_negative, supertrend_downtrend]
        return sum(conditions) >= 3

    def get_support_resistance_levels(self, df: pd.DataFrame, lookback: int = 50) -> Tuple[float, float]:
        """
        Calcule les niveaux de support et de résistance basés sur les hauts et bas récents.

        Args:
            df: DataFrame avec les données OHLCV
            lookback: Nombre de périodes à regarder en arrière

        Returns:
            Tuple de (support_level, resistance_level)
        """
        if len(df) < lookback:
            lookback = len(df)

        recent_data = df.iloc[-lookback:]
        resistance = recent_data['high'].max()
        support = recent_data['low'].min()

        return support, resistance

    def calculate_pivot_points(self, high: float, low: float, close: float) -> Dict[str, float]:
        """
        Calcule les points pivots classiques (floor trader's method).

        Args:
            high: Haut de la période précédente
            low: Bas de la période précédente
            close: Clôture de la période précédente

        Returns:
            Dictionnaire avec les niveaux de pivot
        """
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)

        return {
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            'r3': r3,
            's1': s1,
            's2': s2,
            's3': s3
        }

    def is_price_near_level(self, price: float, level: float, threshold_pct: float = 0.001) -> bool:
        """
        Vérifie si le prix est près d'un niveau donné (support/résistance/pivot).

        Args:
            price: Prix actuel
            level: Niveau à tester
            threshold_pct: Seuil en pourcentage du prix (défaut: 0.1%)

        Returns:
            True si le prix est près du niveau, False sinon
        """
        if price == 0:
            return False
        distance_pct = abs(price - level) / price
        return distance_pct <= threshold_pct


# Export des classes publiques
__all__ = ['TechnicalIndicators']