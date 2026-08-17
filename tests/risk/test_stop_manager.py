import pytest

from superbot.risk.risk_manager import RiskManager
from superbot.risk.modules.stop_manager import (
    _check_trailing_stop,
    _check_break_even,
)


def make_rm(**overrides):
    config = {
        'RISK_PCT': 2.0,
        'TRAIL_ATR_MULT': 1.0,
        'TRAIL_ACTIVATE_ATR_MULT': 2.0,
        'BE_ATR_MULT': 1.0,
        'BE_DYN_RR': True,
        'BE_DYN_RR_RATIO': 1.0,
    }
    config.update(overrides)
    return RiskManager(config)


# ---------------------------------------------------------------------------
# calculate_sl_tp_levels
# ---------------------------------------------------------------------------

def test_sl_tp_standard_forex_long():
    rm = make_rm()
    sl, tp = rm.calculate_sl_tp_levels(
        entry_price=100.0, atr_value=1.0, position_side='LONG',
        asset_type='forex', symbol='EUR/USD', hmm_regime='TRENDING')
    # TRENDING + forex → SL 1.5×ATR, TP 3.0×ATR
    assert sl == 98.5
    assert tp == 103.0


def test_sl_tp_standard_forex_short():
    rm = make_rm()
    sl, tp = rm.calculate_sl_tp_levels(
        entry_price=100.0, atr_value=1.0, position_side='SHORT',
        asset_type='forex', symbol='EUR/USD', hmm_regime='TRENDING')
    assert sl == 101.5
    assert tp == 97.0


def test_sl_tp_jpy_pair_widened():
    rm = make_rm()
    sl, tp = rm.calculate_sl_tp_levels(
        entry_price=100.0, atr_value=1.0, position_side='LONG',
        asset_type='forex', symbol='USD/JPY', hmm_regime='TRENDING')
    # forex_jpy → multiplicateurs ×1.25 → SL 1.875 (arrondi 1.88), TP 3.75
    assert sl == pytest.approx(98.12)
    assert tp == pytest.approx(103.75)


def test_sl_tp_zero_atr_fallback_long():
    rm = make_rm()
    sl, tp = rm.calculate_sl_tp_levels(
        entry_price=100.0, atr_value=0.0, position_side='LONG',
        asset_type='forex', symbol='EUR/USD')
    assert sl == pytest.approx(98.0)   # -2%
    assert tp == pytest.approx(104.0)  # +4%


def test_sl_tp_zero_atr_fallback_short():
    rm = make_rm()
    sl, tp = rm.calculate_sl_tp_levels(
        entry_price=100.0, atr_value=0.0, position_side='SHORT',
        asset_type='forex', symbol='EUR/USD')
    assert sl == pytest.approx(102.0)
    assert tp == pytest.approx(96.0)


# ---------------------------------------------------------------------------
# trailing stop
# ---------------------------------------------------------------------------

def test_trailing_stop_long_moves_up():
    rm = make_rm()
    pos = {'side': 'LONG', 'trailing_stop_enabled': True,
           'atr_value': 1.0, 'stop_loss': 98.0}
    _check_trailing_stop(rm, 'EUR/USD', pos, 101.0)
    assert pos['stop_loss'] == pytest.approx(100.0)


def test_trailing_stop_long_never_descends():
    rm = make_rm()
    pos = {'side': 'LONG', 'trailing_stop_enabled': True,
           'atr_value': 1.0, 'stop_loss': 98.0}
    _check_trailing_stop(rm, 'EUR/USD', pos, 99.0)
    assert pos['stop_loss'] == pytest.approx(98.0)


def test_trailing_stop_short_moves_down():
    rm = make_rm()
    pos = {'side': 'SHORT', 'trailing_stop_enabled': True,
           'atr_value': 1.0, 'stop_loss': 103.0}
    _check_trailing_stop(rm, 'EUR/USD', pos, 99.0)
    assert pos['stop_loss'] == pytest.approx(100.0)


def test_trailing_stop_short_never_rises():
    rm = make_rm()
    pos = {'side': 'SHORT', 'trailing_stop_enabled': True,
           'atr_value': 1.0, 'stop_loss': 103.0}
    _check_trailing_stop(rm, 'EUR/USD', pos, 105.0)
    assert pos['stop_loss'] == pytest.approx(103.0)


def test_trailing_stop_disabled_does_nothing():
    rm = make_rm()
    pos = {'side': 'LONG', 'trailing_stop_enabled': False,
           'atr_value': 1.0, 'stop_loss': 98.0}
    _check_trailing_stop(rm, 'EUR/USD', pos, 101.0)
    assert pos['stop_loss'] == pytest.approx(98.0)


def test_trailing_stop_long_not_activated_before_threshold():
    rm = make_rm()
    pos = {'side': 'LONG', 'trailing_stop_enabled': True,
           'atr_value': 1.0, 'entry_price': 100.0, 'stop_loss': 98.0}
    # Profit = 1.5 ATR < 2.0 ATR d'activation → pas de trailing.
    _check_trailing_stop(rm, 'EUR/USD', pos, 101.5)
    assert pos['stop_loss'] == pytest.approx(98.0)


def test_trailing_stop_long_activated_after_threshold():
    rm = make_rm()
    pos = {'side': 'LONG', 'trailing_stop_enabled': True,
           'atr_value': 1.0, 'entry_price': 100.0, 'stop_loss': 98.0}
    # Profit = 2.5 ATR >= 2.0 ATR → trailing : 102.5 - 1.0 = 101.5.
    _check_trailing_stop(rm, 'EUR/USD', pos, 102.5)
    assert pos['stop_loss'] == pytest.approx(101.5)


def test_trailing_stop_short_activation_threshold():
    rm = make_rm()
    pos = {'side': 'SHORT', 'trailing_stop_enabled': True,
           'atr_value': 1.0, 'entry_price': 100.0, 'stop_loss': 103.0}
    # Profit = 2.5 ATR >= 2.0 ATR → trailing : 97.5 + 1.0 = 98.5.
    _check_trailing_stop(rm, 'EUR/USD', pos, 97.5)
    assert pos['stop_loss'] == pytest.approx(98.5)


# ---------------------------------------------------------------------------
# break-even
# ---------------------------------------------------------------------------

def test_break_even_dynamic_triggers_long():
    rm = make_rm()
    pos = {'side': 'LONG', 'break_even_activated': False, 'atr_value': 1.0,
           'entry_price': 100.0, 'initial_sl': 98.0, 'stop_loss': 98.0}
    _check_break_even(rm, 'EUR/USD', pos, 102.0)  # gain 2 ≥ risque 2 × 1.0
    assert pos['break_even_activated'] is True
    assert pos['stop_loss'] == pytest.approx(100.05)


def test_break_even_dynamic_not_triggered():
    rm = make_rm()
    pos = {'side': 'LONG', 'break_even_activated': False, 'atr_value': 1.0,
           'entry_price': 100.0, 'initial_sl': 98.0, 'stop_loss': 98.0}
    _check_break_even(rm, 'EUR/USD', pos, 101.0)  # gain 1 < 2
    assert pos['break_even_activated'] is False
    assert pos['stop_loss'] == pytest.approx(98.0)


def test_break_even_dynamic_ratio_1_5():
    # Nouveau défaut : BE à 1.5R au lieu de 1.0R.
    rm = make_rm(BE_DYN_RR_RATIO=1.5)
    pos = {'side': 'LONG', 'break_even_activated': False, 'atr_value': 1.0,
           'entry_price': 100.0, 'initial_sl': 98.0, 'stop_loss': 98.0}
    _check_break_even(rm, 'EUR/USD', pos, 102.5)  # gain 2.5 < risque 2 × 1.5 = 3
    assert pos['break_even_activated'] is False
    _check_break_even(rm, 'EUR/USD', pos, 103.5)  # gain 3.5 >= 3
    assert pos['break_even_activated'] is True


def test_break_even_atr_based_triggers():
    rm = make_rm(BE_DYN_RR=False)
    pos = {'side': 'LONG', 'break_even_activated': False, 'atr_value': 1.0,
           'entry_price': 100.0, 'stop_loss': 98.0}
    _check_break_even(rm, 'EUR/USD', pos, 101.5)  # profit 1.5 ATR ≥ 1.0
    assert pos['break_even_activated'] is True


def test_break_even_already_activated_noop():
    rm = make_rm()
    pos = {'side': 'LONG', 'break_even_activated': True, 'atr_value': 1.0,
           'entry_price': 100.0, 'initial_sl': 98.0, 'stop_loss': 100.05}
    _check_break_even(rm, 'EUR/USD', pos, 102.0)
    assert pos['stop_loss'] == pytest.approx(100.05)


def test_break_even_no_atr_noop():
    rm = make_rm()
    pos = {'side': 'LONG', 'break_even_activated': False, 'atr_value': 0.0,
           'entry_price': 100.0, 'initial_sl': 98.0, 'stop_loss': 98.0}
    _check_break_even(rm, 'EUR/USD', pos, 102.0)
    assert pos['break_even_activated'] is False
