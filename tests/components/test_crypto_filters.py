import pandas as pd

from superbot.components.crypto_filters import check_crypto_volume


def test_volume_above_threshold():
    df = pd.DataFrame([{'volume': 1000.0, 'volume_ma': 2000.0}])  # 50% de la moyenne
    assert check_crypto_volume('BTC/USDT', df) is True


def test_volume_below_threshold_rejected():
    df = pd.DataFrame([{'volume': 300.0, 'volume_ma': 2000.0}])  # 15% < 20%
    assert check_crypto_volume('BTC/USDT', df) is False


def test_volume_ma_zero_allows_trade():
    # Moyenne mobile absente → ne doit pas bloquer le trade
    df = pd.DataFrame([{'volume': 100.0, 'volume_ma': 0.0}])
    assert check_crypto_volume('BTC/USDT', df) is True
