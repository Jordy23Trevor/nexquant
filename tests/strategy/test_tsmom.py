"""Tests du module time-series momentum (superbot.strategy.tsmom)."""

import numpy as np
import pandas as pd
import pytest

from superbot.strategy import tsmom


def _daily(n=500, seed=0, drift=0.0005, vol=0.01) -> pd.Series:
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    prices = 100 * np.exp(np.cumsum(rets))
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    return pd.Series(prices, index=idx)


def test_monthly_signals_uptrend_and_downtrend():
    idx = pd.date_range("2020-01-01", periods=400, freq="D", tz="UTC")
    up = pd.Series(np.linspace(100, 200, 400), index=idx)
    down = pd.Series(np.linspace(200, 100, 400), index=idx)

    sig_up = tsmom.monthly_signals(up, lookback=3, skip=1)
    sig_down = tsmom.monthly_signals(down, lookback=3, skip=1)

    # Une fois la fenêtre passée, signe constant : +1 en tendance haussière, -1 en baisse.
    assert (sig_up.iloc[4:] == 1.0).all()
    assert (sig_down.iloc[4:] == -1.0).all()


def test_monthly_signals_no_lookahead():
    idx = pd.date_range("2020-01-01", periods=400, freq="D", tz="UTC")
    base = pd.Series(np.linspace(100, 200, 400), index=idx)

    sig_before = tsmom.monthly_signals(base, lookback=3, skip=1)

    # Pic injecté uniquement dans les 5 DERNIERS jours (le mois courant) :
    # le signal du mois courant ne doit pas changer (il n'utilise que des clôtures <= mois-1).
    spike = base.copy()
    spike.iloc[-5:] *= 3.0
    sig_after = tsmom.monthly_signals(spike, lookback=3, skip=1)

    assert sig_before.iloc[-1] == sig_after.iloc[-1]


def test_target_weights_clipping_and_scaling():
    idx = pd.date_range("2020-01-01", periods=300, freq="D", tz="UTC")
    # Vol très faible => le poids visé dépasse le plafond de levier.
    flat = pd.Series(np.linspace(100, 101, 300), index=idx)
    sig = tsmom.monthly_signals(flat, lookback=3, skip=1).replace(0.0, 1.0)

    weights, _ = tsmom.target_weights(flat, sig, target_vol=0.15, max_leverage=1.5)
    assert (weights.dropna().abs() <= 1.5 + 1e-9).all()
    assert weights.dropna().max() <= 1.5 + 1e-9


def test_target_weights_long_only_never_short():
    closes = _daily()
    sig = pd.Series(-1.0, index=closes.resample("ME").last().index)
    weights, _ = tsmom.target_weights(closes, sig, long_only=True)
    assert (weights.dropna() >= -1e-9).all()


def test_backtest_monthly_shape_and_columns():
    closes = _daily(n=400)
    d = tsmom.backtest_monthly(closes, lookback=3, skip=1)
    assert {"close", "ret", "signal", "weight", "turnover", "strat"}.issubset(d.columns)
    assert len(d) >= 12
    # Pas de NaN dans les rendements de stratégie une fois la fenêtre passée.
    assert not d["strat"].iloc[6:].isna().any()


def test_metrics_on_known_series():
    # 6 mois gagnants (+2%) et 2 mois perdants (-1%) => PF = 12/2 = 6, WR = 75%.
    s = pd.Series([0.02, 0.02, 0.02, 0.02, 0.02, 0.02, -0.01, -0.01])
    m = tsmom.metrics(s)
    assert m["pf"] == pytest.approx(6.0)
    assert m["wr"] == pytest.approx(0.75)


def test_portfolio_returns_equal_weight_mean():
    a = pd.Series([0.01, 0.02], index=pd.date_range("2020-01-31", periods=2, freq="ME"))
    b = pd.Series([0.03, 0.00], index=a.index)
    port = tsmom.portfolio_returns({"a": a, "b": b})
    assert port.iloc[0] == pytest.approx(0.02)
