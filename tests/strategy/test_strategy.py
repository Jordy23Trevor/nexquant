import pytest
import pandas as pd
from superbot.strategy.strategy import TradingStrategy

@pytest.fixture
def strategy():
    config = {
        'SCORE_MIN': 6.0,
        'COMMISSION_PCT': 0.1,
        'SLIPPAGE_PCT': 0.05,
        'SL_ATR_MULT': 1.5,
        'TP_ATR_MULT': 3.0
    }
    return TradingStrategy(config)

def test_calculate_potential_rr_brut(strategy):
    # Simuler une bougie récente
    latest = pd.Series({'atr': 100})
    current_price = 50000.0

    # ATR = 100, SL = 50000 - 150 = 49850, TP = 50000 + 300 = 50300
    # Risk brut = 150, Reward brut = 300
    # R:R brut attendu = 300 / 150 = 2.0

    rr_ratio, sl_price, tp_price = strategy._calculate_potential_rr(latest, current_price)

    assert sl_price == 49850.0
    assert tp_price == 50300.0
    assert round(rr_ratio, 4) == 2.0

def test_deterministic_scoring(strategy):
    # Données simulées menant à un signal clair (trend haussier très fort)
    data = {
        'open': [100.0] * 55,
        'high': [101.0] * 55,
        'low': [99.0] * 55,
        'close': [100.0] * 55,
        'volume': [1000.0] * 55,
        'ema_fast': [98.0] * 55,
        'ema_slow': [95.0] * 55,
        'ema_trend': [90.0] * 55,
        'rsi': [55.0] * 55, # Pas suracheté
        'adx': [30.0] * 55, # Tendance forte
        'macd': [2.0] * 55,
        'macd_signal': [1.0] * 55,
        'supertrend': [90.0] * 55,
        'supertrend_trend': [1.0] * 55, # Haussier
        'atr': [5.0] * 55,
        'bb_lower': [90.0] * 55,
        'bb_upper': [110.0] * 55,
        'close_htf': [100.0] * 55,
        'ema_htf': [80.0] * 55
    }
    df = pd.DataFrame(data)

    signal = strategy.analyze_market(df=df, symbol="TEST")
    
    # Le score doit être calculé de manière prévisible
    # Le régime ADX > 25 avec trend positif devrait être STRONG_TREND ou TRENDING
    assert signal['market_regime'] in ["STRONG_TREND", "TRENDING"]
    assert signal['total_score'] > 0.0
