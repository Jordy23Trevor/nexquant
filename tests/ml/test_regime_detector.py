"""Tests de l'heuristique de régime et du mapping d'états."""

import pandas as pd

from superbot.ml.regime_detector import heuristic_regime, REGIME_MAP, MarketRegimeDetector


def _df(adx, bb_width):
    return pd.DataFrame({
        "adx": [adx, adx],
        "bb_width": [bb_width] * 2,
    })


def test_heuristic_low_adx_is_ranging():
    assert heuristic_regime(_df(adx=15.0, bb_width=0.02), adx_threshold=25.0) == "RANGING"


def test_heuristic_high_adx_expansion_is_trending():
    # BB en expansion (width > médiane) + ADX fort -> TRENDING
    assert heuristic_regime(_df(adx=30.0, bb_width=0.03), adx_threshold=25.0) == "TRENDING"


def test_heuristic_squeeze_is_ranging_even_with_high_adx():
    # BB en compression (width < médiane) -> RANGING malgré l'ADX fort
    df = pd.DataFrame({
        "adx": [30.0] * 50,
        "bb_width": [0.01] * 49 + [0.001],  # dernière largeur en squeeze vs médiane 0.01
    })
    assert heuristic_regime(df, adx_threshold=25.0) == "RANGING"


def test_state_to_regime_handles_legacy_labels():
    assert MarketRegimeDetector._state_to_regime("BULLISH_STABLE") == "TRENDING"
    assert MarketRegimeDetector._state_to_regime("BEARISH_VOLATILE") == "TRENDING"
    assert MarketRegimeDetector._state_to_regime("RANGING_QUIET") == "RANGING"
    assert MarketRegimeDetector._state_to_regime("INCONNU_RANGE") == "RANGING"
