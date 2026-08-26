"""
Tests unitaires et de stress pour RiskManager (Forex & Commodities).
"""
import pytest
from superbot.risk.risk_manager import RiskManager
from types import SimpleNamespace


@pytest.fixture
def risk_manager():
    config = {
        'RISK_PCT': 1.0,
        'MAX_OPEN_POSITIONS': 3,
        'MAX_DAILY_LOSS_PCT': 3.0,
        'MAX_DAILY_LOSS_AMOUNT': 300.0,
        'KELLY_FRACTION': 0.25,
        'MIN_TRADES_FOR_KELLY': 20,
        'COMMISSION_PCT': 0.0,
        'SLIPPAGE_PCT': 0.0,
        'DRAWDOWN_THRESH_1': 5.0,
        'DRAWDOWN_THRESH_2': 10.0,
        'DRAWDOWN_REDUCE_5PCT': 0.20,
        'DRAWDOWN_REDUCE_10PCT': 0.50,
    }
    return RiskManager(config)


class TestRiskManager:

    def test_kill_switch_daily_loss(self, risk_manager):
        risk_manager.update_account_balance(10000.0)
        assert risk_manager.check_kill_switch(10000.0) is False

        # Perte journalière de 400€ (-4.0% > 3.0%)
        risk_manager.daily_pnl = -400.0
        assert risk_manager.check_kill_switch(9600.0) is True

    def test_drawdown_protection_risk_reduction(self, risk_manager):
        # Initialiser avec un pic à 10000€
        risk_manager.update_account_balance(10000.0)
        assert risk_manager.drawdown_pct == 0.0

        # Solde descend à 9400€ (6% Drawdown > 5%)
        risk_manager.update_account_balance(9400.0)
        assert risk_manager.drawdown_pct == 6.0

        # Solde descend à 8900€ (11% Drawdown > 10%)
        risk_manager.update_account_balance(8900.0)
        assert risk_manager.drawdown_pct == 11.0

    def test_position_sizing_forex(self, risk_manager):
        mock_broker = SimpleNamespace(
            get_symbol_info=lambda sym: {
                'contract_size': 100000.0,
                'tick_size': 0.00001,
                'tick_value': 1.0,
                'volume_min': 0.01,
                'volume_step': 0.01,
                'volume_max': 100.0
            },
            get_account_summary=lambda: {
                'balance': 10000.0,
                'free_margin': 10000.0,
                'leverage': 100
            }
        )

        size, details = risk_manager.calculate_position_size(
            account_balance=10000.0,
            entry_price=1.1000,
            stop_loss=1.0980,  # 20 pips risk = 200 ticks * 1 = $200 per lot
            symbol="EURUSD",
            broker=mock_broker
        )
        assert size > 0
        assert details['actual_risk_pct'] <= 2.0

    def test_position_sizing_gold(self, risk_manager):
        mock_broker = SimpleNamespace(
            get_symbol_info=lambda sym: {
                'contract_size': 100.0,
                'tick_size': 0.01,
                'tick_value': 1.0,
                'volume_min': 0.01,
                'volume_step': 0.01,
                'volume_max': 100.0
            },
            get_account_summary=lambda: {
                'balance': 10000.0,
                'free_margin': 10000.0,
                'leverage': 100
            }
        )

        size, details = risk_manager.calculate_position_size(
            account_balance=10000.0,
            entry_price=2500.0,
            stop_loss=2490.0,  # $10 stop on 100 oz = $1000 risk per lot
            symbol="XAUUSD",
            broker=mock_broker
        )
        assert size > 0
        assert details['actual_risk_pct'] <= 2.0

    def test_get_risk_metrics(self, risk_manager):
        risk_manager.update_account_balance(10000.0)
        metrics = risk_manager.get_risk_metrics(10000.0)
        assert isinstance(metrics, dict)
        assert 'drawdown_pct' in metrics
        assert 'win_rate' in metrics
