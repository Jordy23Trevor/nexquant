import pytest

from superbot.risk.risk_manager import RiskManager
from superbot.strategy.strategy import TradingStrategy
from superbot.orchestrator import SuperBot
from superbot.components.adaptive_params import (
    update_adaptive_parameters,
    get_recent_win_rate,
)
from superbot.components.runtime_config import RuntimeConfig


class FakeBot:
    # Réutilise la vraie implémentation testée, sans construire un SuperBot complet.
    _apply_adaptive_params = SuperBot._apply_adaptive_params

    def __init__(self, risk_pct=2.0, score_min=6.0):
        self.risk_manager = RiskManager({'RISK_PCT': risk_pct})
        self.strategy = TradingStrategy({'SCORE_MIN': score_min, 'RISK_PCT': risk_pct})
        self.adaptive_risk_pct = risk_pct
        self.adaptive_score_min = score_min


def _closed_trades(pnls):
    return [{'status': 'closed', 'pnl': p} for p in pnls]


def test_apply_adaptive_params_pushes_to_components():
    bot = FakeBot()
    bot.adaptive_risk_pct = 1.5
    bot.adaptive_score_min = 5.0
    bot._apply_adaptive_params()
    assert bot.risk_manager.RISK_PCT == 1.5
    assert bot.strategy.score_min == 5.0
    assert bot.strategy.risk_per_trade == 1.5


def test_update_adaptive_good_performance_increases_risk():
    bot = FakeBot(risk_pct=1.0, score_min=6.0)
    bot.risk_manager.trade_history = _closed_trades([10] * 15 + [-5] * 5)  # win rate 0.75
    update_adaptive_parameters(bot)
    assert bot.adaptive_risk_pct == pytest.approx(1.05)
    assert bot.adaptive_score_min == pytest.approx(5.5)
    # Les composants actifs reçoivent bien les nouvelles valeurs
    assert bot.risk_manager.RISK_PCT == pytest.approx(1.05)
    assert bot.strategy.score_min == pytest.approx(5.5)


def test_update_adaptive_bad_performance_decreases_risk():
    bot = FakeBot(risk_pct=1.0, score_min=4.0)
    bot.risk_manager.trade_history = _closed_trades([10] * 5 + [-5] * 15)  # win rate 0.25
    update_adaptive_parameters(bot)
    assert bot.adaptive_risk_pct == pytest.approx(0.95)
    assert bot.adaptive_score_min == pytest.approx(4.5)
    assert bot.risk_manager.RISK_PCT == pytest.approx(0.95)
    assert bot.strategy.score_min == pytest.approx(4.5)


def test_update_adaptive_respects_bounds():
    bot = FakeBot(risk_pct=2.45, score_min=2.2)
    bot.risk_manager.trade_history = _closed_trades([10] * 15 + [-5] * 5)
    update_adaptive_parameters(bot)
    assert bot.adaptive_risk_pct == pytest.approx(2.5)  # cap à 2.5%
    assert bot.adaptive_score_min == pytest.approx(2.0)  # plancher à 2.0


def test_update_adaptive_insufficient_trades_noop():
    bot = FakeBot(risk_pct=1.0, score_min=6.0)
    bot.risk_manager.trade_history = _closed_trades([10] * 3 + [-5] * 1)  # 4 trades < 5
    update_adaptive_parameters(bot)
    assert bot.adaptive_risk_pct == 1.0
    assert bot.adaptive_score_min == 6.0


def test_get_recent_win_rate():
    bot = FakeBot()
    bot.risk_manager.trade_history = _closed_trades([10] * 6 + [-5] * 4)
    assert get_recent_win_rate(bot) == pytest.approx(0.6)


def test_runtime_config_set_propagates():
    rm = RiskManager({'RISK_PCT': 2.0})
    strat = TradingStrategy({'SCORE_MIN': 6.0, 'RISK_PCT': 2.0})
    rc = RuntimeConfig(risk_pct=2.0, score_min=6.0)
    rc.bind(rm, strat)

    rc.set(risk_pct=1.25, score_min=5.0)
    assert rm.RISK_PCT == 1.25
    assert strat.score_min == 5.0
    assert strat.risk_per_trade == 1.25


def test_runtime_config_noop_when_unchanged():
    rm = RiskManager({'RISK_PCT': 2.0})
    strat = TradingStrategy({'SCORE_MIN': 6.0, 'RISK_PCT': 2.0})
    rc = RuntimeConfig(risk_pct=2.0, score_min=6.0)
    rc.bind(rm, strat)

    # Même valeur → pas de propagation (changed=False).
    assert rc.set(risk_pct=2.0, score_min=6.0) is False
    assert rc.set(risk_pct=2.5) is True
