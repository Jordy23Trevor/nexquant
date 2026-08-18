"""Tests du calibrateur de win rate (score -> win rate empirique)."""

import pytest

from superbot.ml.win_rate_calibrator import (
    WinRateCalibrator,
    DEFAULT_PRIOR,
)
import superbot.ml.win_rate_calibrator as cal_mod
from superbot.strategy.components.scorer import calculate_probabilistic_win_rate


def test_unfitted_uses_prior():
    cal = WinRateCalibrator()
    assert not cal.is_fitted
    assert cal.predict(7) == DEFAULT_PRIOR


def test_fit_and_predict_flat_win_rate():
    # 25% de win rate sur 80 trades : tous les buckets convergent vers ~25%.
    scores = [7] * 80
    outcomes = [1] * 20 + [0] * 60
    cal = WinRateCalibrator().fit(scores, outcomes)
    assert cal.is_fitted
    # Shrinkage bayésien : (20 + 10*0.3) / (80 + 10) = 0.2555...
    assert cal.predict(7) == pytest.approx(23 / 90, abs=1e-3)


def test_predict_bucket_separation():
    # Score bas perdant, score haut gagnant -> la calibration reflète la séparation.
    scores = [3] * 40 + [9] * 40
    outcomes = [0] * 40 + [1] * 40
    cal = WinRateCalibrator().fit(scores, outcomes)
    assert cal.predict(3) < cal.predict(9)


def test_save_load_roundtrip(tmp_path):
    cal = WinRateCalibrator().fit([6] * 50, [1] * 15 + [0] * 35)
    path = cal.save(tmp_path / "cal.json")
    loaded = WinRateCalibrator.load(path)
    assert loaded.is_fitted
    assert loaded.predict(6) == pytest.approx(cal.predict(6))


def test_calculate_probabilistic_win_rate_uses_calibration(monkeypatch):
    cal = WinRateCalibrator().fit([7] * 80, [1] * 20 + [0] * 60)
    monkeypatch.setattr(cal_mod, "_cached_calibrator", cal)
    meta = calculate_probabilistic_win_rate(7, rr_ratio=1.5)
    # win_prob calibré (~0.255) et non pas l'ancienne formule (0.63).
    assert meta["win_prob"] == pytest.approx(23 / 90, abs=1e-3)
    # EV < 0 -> pas d'edge avec un RR de 1.5.
    assert meta["expected_value"] < 0
    assert meta["has_edge"] is False


def test_calculate_probabilistic_win_rate_edge_positive(monkeypatch):
    # Win rate calibré élevé -> edge positif.
    cal = WinRateCalibrator().fit([8] * 80, [1] * 60 + [0] * 20)
    monkeypatch.setattr(cal_mod, "_cached_calibrator", cal)
    meta = calculate_probabilistic_win_rate(8, rr_ratio=1.5)
    assert meta["expected_value"] > 0
    assert meta["has_edge"] is True
