import pytest

from superbot.risk.risk_manager import RiskManager
from superbot.risk.modules.position_sizer import _calculate_kelly_fraction


def make_rm(**overrides):
    config = {
        'RISK_PCT': 2.0,
        'MAX_OPEN_POSITIONS': 5,
        'MAX_DAILY_LOSS_PCT': 5.0,
        'KELLY_FRACTION': 0.5,
        'MIN_TRADES_FOR_KELLY': 50,
    }
    config.update(overrides)
    return RiskManager(config)


class FakeBroker:
    def __init__(self, free_margin=10000.0, leverage=1, asset_type='forex',
                 min_order=0.001, step=0.0):
        self._free_margin = free_margin
        self._leverage = leverage
        self._asset_type = asset_type
        self._min_order = min_order
        self._step = step

    def get_symbol_info(self, symbol):
        return {'contract_size': 1.0, 'tick_size': 0.01, 'tick_value': 0.01}

    def get_account_summary(self):
        return {'free_margin': self._free_margin, 'leverage': self._leverage}

    def get_min_order_size(self, symbol):
        return self._min_order

    def get_step_size(self, symbol):
        return self._step

    def get_asset_type(self):
        return self._asset_type


# Entrée 100 / SL 95 → risque prix brut = 5, frais = 100 * 0.25% = 0.25 → risque unitaire 5.25.
def test_base_position_size_no_broker():
    rm = make_rm()
    size, details = rm.calculate_position_size(
        account_balance=10000.0, entry_price=100.0, stop_loss=95.0, symbol='EUR/USD')
    # Risque 2% de 10 000 = 200 → 200 / 5.25
    assert size == pytest.approx(200 / 5.25)
    assert details['adjusted_risk_pct'] == pytest.approx(2.0)


def test_zero_balance():
    rm = make_rm()
    size, _ = rm.calculate_position_size(
        account_balance=0.0, entry_price=100.0, stop_loss=95.0, symbol='EUR/USD')
    assert size == 0.0


def test_drawdown_tier_2_halves_risk():
    rm = make_rm()
    rm.drawdown_pct = 12.0  # >= DRAWDOWN_THRESH_2 (10%) → risque ×0.5
    size, _ = rm.calculate_position_size(10000.0, 100.0, 95.0, 'EUR/USD')
    assert size == pytest.approx((200 * 0.5) / 5.25)


def test_drawdown_tier_1_reduces_risk():
    rm = make_rm()
    rm.drawdown_pct = 6.0  # >= DRAWDOWN_THRESH_1 (5%), < 10% → risque ×0.8
    size, _ = rm.calculate_position_size(10000.0, 100.0, 95.0, 'EUR/USD')
    assert size == pytest.approx((200 * 0.8) / 5.25)


def test_regime_risk_multipliers():
    rm = make_rm()
    size_hi, _ = rm.calculate_position_size(
        10000.0, 100.0, 95.0, 'EUR/USD', hmm_regime='HIGH_VOL_RANGE')
    assert size_hi == pytest.approx((200 * 0.5) / 5.25)

    size_trend, _ = rm.calculate_position_size(
        10000.0, 100.0, 95.0, 'EUR/USD', hmm_regime='TRENDING')
    assert size_trend == pytest.approx((200 * 1.2) / 5.25)


def test_correlation_reduces_size():
    rm = make_rm()
    size, _ = rm.calculate_position_size(
        10000.0, 100.0, 95.0, 'EUR/USD',
        correlation_data={'average_correlation': 0.8})
    # Corrélation forte (> 0.7) → ajustement 0.7
    assert size == pytest.approx((200 * 0.7) / 5.25)


def test_sentiment_factor_reduces_size():
    rm = make_rm()
    size, _ = rm.calculate_position_size(
        10000.0, 100.0, 95.0, 'EUR/USD', sentiment_factor=0.5)
    assert size == pytest.approx((200 * 0.5) / 5.25)


def test_margin_caps_position_size():
    rm = make_rm()
    broker = FakeBroker(free_margin=500.0, leverage=1)
    size, _ = rm.calculate_position_size(
        10000.0, 100.0, 95.0, 'EUR/USD', broker=broker)
    # max_nominal = 500 * 1 * 0.95 = 475 → taille max = 475 / 100 = 4.75
    assert size == pytest.approx(4.75)


def test_insufficient_margin_rejects():
    rm = make_rm()
    broker = FakeBroker(free_margin=0.001, leverage=1)
    size, details = rm.calculate_position_size(
        10000.0, 100.0, 95.0, 'EUR/USD', broker=broker)
    assert size == 0.0
    assert 'error' in details


def test_kelly_insufficient_history():
    rm = make_rm()
    rm.trade_history = [{'pnl': 10.0, 'status': 'closed'} for _ in range(10)]
    assert _calculate_kelly_fraction(rm) is None


def test_kelly_all_winners_returns_none():
    rm = make_rm()
    rm.trade_history = [
        {'pnl': 10.0, 'status': 'closed', 'initial_risk_amount': 10.0}
        for _ in range(60)
    ]
    assert _calculate_kelly_fraction(rm) is None


def test_kelly_mixed_trades():
    rm = make_rm()
    winners = [
        {'pnl': 100.0, 'status': 'closed', 'initial_risk_amount': 100.0}
        for _ in range(30)
    ]
    losers = [
        {'pnl': -50.0, 'status': 'closed', 'initial_risk_amount': 50.0}
        for _ in range(20)
    ]
    rm.trade_history = winners + losers
    # win_rate=0.6, avg_win=1.0R, avg_loss=1.0R → Kelly brut 0.2 → demi-Kelly 0.1
    assert _calculate_kelly_fraction(rm) == pytest.approx(0.1)


def test_kelly_applied_in_position_sizing():
    rm = make_rm()
    base_size, _ = rm.calculate_position_size(
        100000.0, 100.0, 95.0, 'EUR/USD')

    winners = [
        {'pnl': 100.0, 'status': 'closed', 'initial_risk_amount': 100.0}
        for _ in range(30)
    ]
    losers = [
        {'pnl': -50.0, 'status': 'closed', 'initial_risk_amount': 50.0}
        for _ in range(20)
    ]
    rm.trade_history = winners + losers
    kelly_size, _ = rm.calculate_position_size(
        100000.0, 100.0, 95.0, 'EUR/USD')
    # L'avantage positif (Kelly 0.1) doit gonfler la taille vs risque fixe seul
    assert kelly_size > base_size
