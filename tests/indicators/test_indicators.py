import pytest
import pandas as pd
import numpy as np
from superbot.indicators.technical_indicators import TechnicalIndicators

@pytest.fixture
def dummy_config():
    return {
        'EMA_FAST': 10,
        'EMA_SLOW': 20,
        'EMA_TREND': 50,
        'HTF_EMA': 200,
        'D1_EMA': 50,
        'W1_EMA': 20,
        'RSI_LEN': 14,
        'RSI_OB': 70,
        'RSI_OS': 30,
        'MACD_FAST': 12,
        'MACD_SLOW': 26,
        'MACD_SIGNAL': 9,
        'ADX_LEN': 14,
        'ADX_TREND': 25,
        'ST_MULTIPLIER': 3.0,
        'ST_ATR_LEN': 10,
        'ATR_LEN': 14,
        'BB_LEN': 20,
        'BB_STD': 2.0,
        'ICHIMOKU_TENKAN': 9,
        'ICHIMOKU_KIJUN': 26,
        'ICHIMOKU_SENKOU_SPAN_B': 52,
        'ICHIMOKU_DISPLACEMENT': 26,
        'VWAP_WINDOW': 14
    }

@pytest.fixture
def dummy_data():
    dates = pd.date_range("2026-01-01", periods=100, freq="h")
    df = pd.DataFrame({
        "open": np.random.uniform(40000, 45000, 100),
        "high": np.random.uniform(45000, 46000, 100),
        "low": np.random.uniform(39000, 40000, 100),
        "close": np.random.uniform(40000, 45000, 100),
        "volume": np.random.uniform(10, 100, 100)
    }, index=dates)
    return df

def test_indicators_empty_df(dummy_config):
    """Test avec un DataFrame vide."""
    indicators = TechnicalIndicators(dummy_config)
    empty_df = pd.DataFrame()
    result = indicators.calculate_all_indicators(empty_df)
    assert len(result) == 0

def test_indicators_missing_columns(dummy_config):
    """Test avec un DataFrame manquant des colonnes requises."""
    indicators = TechnicalIndicators(dummy_config)
    df = pd.DataFrame({"close": [10, 20, 30]})
    result = indicators.calculate_all_indicators(df)
    # Ne doit pas crasher, mais retourne le DF d'origine si colonnes manquantes
    assert "open" not in result.columns

def test_indicators_caching(dummy_config, dummy_data):
    """Test que le système de cache fonctionne correctement."""
    indicators = TechnicalIndicators(dummy_config)
    
    # Premier appel
    result1 = indicators.calculate_all_indicators(dummy_data)
    # Deuxième appel avec les mêmes données
    result2 = indicators.calculate_all_indicators(dummy_data)
    
    assert "ema_fast" in result1.columns
    assert "ema_fast" in result2.columns
    # Les résultats doivent être identiques (même s'il vient du cache)
    pd.testing.assert_frame_equal(result1, result2)

def test_indicators_with_nan(dummy_config, dummy_data):
    """Test avec des valeurs NaN dans les données."""
    indicators = TechnicalIndicators(dummy_config)
    
    # Introduire des NaNs
    df_with_nan = dummy_data.copy()
    df_with_nan.iloc[50, df_with_nan.columns.get_loc('close')] = np.nan
    
    # Ne doit pas crasher
    result = indicators.calculate_all_indicators(df_with_nan)
    
    # Devrait quand même retourner un DataFrame valide avec les colonnes calculées
    assert "ema_fast" in result.columns
    assert "rsi" in result.columns
