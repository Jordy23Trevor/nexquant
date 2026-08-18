"""Tests de non-régression du rapport de backtest."""

from superbot.backtest.engine import BacktestResults
from superbot.backtest.report import BacktestReport
import superbot.backtest.report as report_mod


def _make_results(symbol):
    return BacktestResults(
        symbol=symbol,
        timeframe="15m",
        start_date="2026-01-01",
        end_date="2026-01-02",
        initial_balance=10000.0,
        final_balance=10000.0,
    )


def test_save_json_sanitizes_slash_symbol(tmp_path, monkeypatch):
    # Le symbole 'BTC/USDT' ne doit plus casser le chemin du fichier généré.
    monkeypatch.setattr(report_mod, "RESULTS_DIR", tmp_path)
    report = BacktestReport(_make_results("BTC/USDT"))
    path = report.save_json()
    assert path.exists()
    assert "/" not in path.name
    assert "BTC-USDT" in path.name
