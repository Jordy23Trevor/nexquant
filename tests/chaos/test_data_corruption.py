import pytest
import pandas as pd
import numpy as np
from superbot.indicators.technical_indicators import TechnicalIndicators

def test_indicators_resilience_to_nans():
    """
    Test 3.6.2 : Vérifie que le moteur d'indicateurs ne crashe pas 
    si l'API courtier renvoie des bougies NaN ou totalement vides (chaos de données).
    """
    config = {
        'EMA_FAST': 9,
        'EMA_SLOW': 21,
        'RSI_LEN': 14,
        'ATR_LEN': 14,
    }
    ti = TechnicalIndicators(config)
    
    # 💥 INJECTION DE CHAOS : Données boursières totalement corrompues
    df_corrupted = pd.DataFrame({
        'open': [np.nan, 100.0, 101.0, np.nan, 102.0],
        'high': [105.0, 106.0, np.nan, 105.0, 107.0],
        'low': [95.0, np.nan, 98.0, 96.0, np.nan],
        'close': [np.nan, 102.0, np.nan, 100.0, 103.0],
        'volume': [0, 0, np.nan, 100, 200]
    })
    
    try:
        # L'exécution ne doit lever aucune exception
        df_result = ti.calculate_all_indicators(df_corrupted)
        
        # Le DataFrame final doit exister et contenir les colonnes attendues
        assert df_result is not None
        assert 'rsi' in df_result.columns
        assert 'atr' in df_result.columns
        
    except Exception as e:
        pytest.fail(f"Le calcul des indicateurs a crashé face à des données corrompues : {e}")
