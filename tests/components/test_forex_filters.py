import datetime as _dt

import pandas as pd
import pytest

import superbot.components.forex_filters as ff


class FrozenClock:
    """Remplace le `datetime` du module pour des tests déterministes."""

    def __init__(self, now):
        self._now = now

    def utcnow(self):
        return self._now

    def fromisoformat(self, value):
        return _dt.datetime.fromisoformat(value)


TUESDAY = _dt.datetime(2026, 8, 11, 10, 0, 0)  # mardi 10h UTC


class FakeBroker:
    def __init__(self, spread):
        self._spread = spread

    def get_spread(self, symbol):
        return self._spread


# ---------------------------------------------------------------------------
# session / marché ouvert
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("now,expected", [
    (_dt.datetime(2026, 8, 11, 10, 0, 0), True),   # mardi 10h
    (_dt.datetime(2026, 8, 14, 23, 0, 0), False),  # vendredi ≥ 22h
    (_dt.datetime(2026, 8, 15, 12, 0, 0), False),  # samedi
    (_dt.datetime(2026, 8, 16, 20, 0, 0), False),  # dimanche < 21h
    (_dt.datetime(2026, 8, 16, 21, 0, 0), True),   # dimanche 21h (réouverture)
])
def test_is_market_open(monkeypatch, now, expected):
    monkeypatch.setattr(ff, 'datetime', FrozenClock(now))
    assert ff.is_market_open() is expected


def test_is_london_session_delegates(monkeypatch):
    monkeypatch.setattr(ff, 'datetime', FrozenClock(TUESDAY))
    assert ff.is_london_session() is True


# ---------------------------------------------------------------------------
# spread
# ---------------------------------------------------------------------------

def test_check_spread_acceptable():
    assert ff.check_spread(FakeBroker(1.5), 'EUR/USD', max_spread=2.0) is True


def test_check_spread_too_wide():
    assert ff.check_spread(FakeBroker(2.5), 'EUR/USD', max_spread=2.0) is False


# ---------------------------------------------------------------------------
# corrélation de devises
# ---------------------------------------------------------------------------

def test_correlation_empty_positions():
    assert ff.check_currency_correlation('EUR/USD', {}, max_exposure=2, cand_side='LONG') is True


def test_correlation_rejects_overexposure():
    positions = {'EUR/USD': {'size': 1.0, 'side': 'LONG'}}
    # LONG EUR/GBP ajoute +1 sur EUR → net +2 > limite 1
    assert ff.check_currency_correlation('EUR/GBP', positions, max_exposure=1, cand_side='LONG') is False


def test_correlation_short_side():
    positions = {'EUR/USD': {'size': 1.0, 'side': 'SHORT'}}  # EUR -1, USD +1
    # SHORT EUR/GBP → EUR -1 de plus → net -2, hors limite 1
    assert ff.check_currency_correlation('EUR/GBP', positions, max_exposure=1, cand_side='SHORT') is False


def test_correlation_non_standard_symbol_always_allowed():
    assert ff.check_currency_correlation('BTC', {}, max_exposure=0, cand_side='LONG') is True


# ---------------------------------------------------------------------------
# obstacle pivot
# ---------------------------------------------------------------------------

def _df(r1, s1, r2, s2):
    return pd.DataFrame([{'r1': r1, 's1': s1, 'r2': r2, 's2': s2}])


def test_pivot_obstacle_blocks_bad_rr_long():
    df = _df(r1=100.5, s1=99.0, r2=101.0, s2=98.0)
    # gain 0.5 / risque 1.0 = 0.5 < 1 → rejet
    assert ff.check_pivot_obstacle(100.0, 99.0, df, True, 'EUR/USD') is False


def test_pivot_obstacle_allows_good_rr_long():
    df = _df(r1=104.0, s1=96.0, r2=105.0, s2=95.0)
    assert ff.check_pivot_obstacle(100.0, 99.0, df, True, 'EUR/USD') is True


def test_pivot_obstacle_no_obstacle_long():
    df = _df(r1=99.0, s1=98.0, r2=98.5, s2=97.0)  # aucun pivot au-dessus du prix
    assert ff.check_pivot_obstacle(100.0, 99.0, df, True, 'EUR/USD') is True


def test_pivot_obstacle_short():
    df = _df(r1=101.0, s1=99.5, r2=102.0, s2=99.0)
    # gain 0.5 / risque 1.0 → rejet
    assert ff.check_pivot_obstacle(100.0, 101.0, df, False, 'EUR/USD') is False


# ---------------------------------------------------------------------------
# fenêtre news majeures
# ---------------------------------------------------------------------------

def test_news_window_blocks_within_avoid_minutes(monkeypatch):
    monkeypatch.setattr(ff, 'datetime', FrozenClock(TUESDAY))
    event = {'impact': 'HIGH', 'currency': 'EUR', 'time': TUESDAY.isoformat(), 'name': 'PMI'}
    assert ff.check_major_news_window('EURUSD', avoid_minutes=30, news_events=[event]) is False


def test_news_window_allows_far_event(monkeypatch):
    monkeypatch.setattr(ff, 'datetime', FrozenClock(TUESDAY))
    far = TUESDAY + _dt.timedelta(hours=2)
    event = {'impact': 'HIGH', 'currency': 'EUR', 'time': far.isoformat(), 'name': 'PMI'}
    assert ff.check_major_news_window('EURUSD', avoid_minutes=30, news_events=[event]) is True


def test_news_window_ignores_unrelated_currency(monkeypatch):
    monkeypatch.setattr(ff, 'datetime', FrozenClock(TUESDAY))
    event = {'impact': 'HIGH', 'currency': 'USD', 'time': TUESDAY.isoformat(), 'name': 'CPI'}
    assert ff.check_major_news_window('EURGBP', avoid_minutes=30, news_events=[event]) is True


def test_news_window_ignores_low_impact(monkeypatch):
    monkeypatch.setattr(ff, 'datetime', FrozenClock(TUESDAY))
    event = {'impact': 'LOW', 'currency': 'EUR', 'time': TUESDAY.isoformat(), 'name': 'Mineur'}
    assert ff.check_major_news_window('EURUSD', avoid_minutes=30, news_events=[event]) is True


def test_news_window_no_events(monkeypatch):
    monkeypatch.setattr(ff, 'datetime', FrozenClock(TUESDAY))
    assert ff.check_major_news_window('EURUSD', avoid_minutes=30, news_events=[]) is True
