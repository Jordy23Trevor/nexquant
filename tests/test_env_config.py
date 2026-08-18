import superbot.config as config


def test_backtest_mode_enforced():
    # Le conftest racine force BACKTEST_MODE pour que la suite ne dépende pas
    # des identifiants broker du `.env`. Garde-fou contre une régression silencieuse.
    assert config.BACKTEST_MODE is True


def test_broker_type_is_valid():
    # « paper » n'est pas un broker supporté ; le type doit rester dans la liste légale.
    assert config.BROKER_TYPE in ("binance", "alpaca", "mt5")
