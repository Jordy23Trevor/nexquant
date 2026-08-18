"""Ajuste la calibration du win rate à partir des trades de backtest.

La stratégie ne prend plus de trade quand la probabilité calibrée est sous le
seuil de rentabilité. Pour récolter des issues réalisées (et ainsi calibrer),
on génère d'abord des trades avec une probabilité permissive, puis on ajuste
WinRateCalibrator sur les paires (score, issue) et on le sauvegarde dans
resources/win_rate_calibration.json.

Usage :
    python artifacts/fit_win_rate_calibration.py
"""

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("BACKTEST_MODE", "true")

import pandas as pd  # noqa: E402

# Sortie redirigée → fichier : forcer UTF-8 (sinon cp1252 plante sur « → »).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

for _n in ("strategy", "backtest.engine", "backtest.data_fetcher", "backtest.report", "root", "urllib3"):
    logging.getLogger(_n).setLevel(logging.WARNING)

import superbot.config as cfg  # noqa: E402
import superbot.strategy.components.scorer as scorer_module  # noqa: E402
from superbot.backtest.engine import BacktestEngine  # noqa: E402
from superbot.backtest.data_fetcher import DataFetcher  # noqa: E402
from superbot.strategy.strategy import TradingStrategy  # noqa: E402
from superbot.ml.win_rate_calibrator import WinRateCalibrator  # noqa: E402


def _permissive_win_rate(score, market_regime="TRENDING", adx_value=20.0, rr_ratio=2.0):
    """Probabilité permissive : génère des trades pour récolter leurs issues."""
    return {"win_prob": 0.9, "expected_value": 0.9 * rr_ratio - 0.1, "has_edge": True}


# Patcher AVANT de lancer la stratégie (l'import dans analyze_market est paresseux).
scorer_module.calculate_probabilistic_win_rate = _permissive_win_rate


def build_config():
    d = {k: getattr(cfg, k) for k in dir(cfg) if k.isupper()}
    d["BROKER_TYPE"] = "binance"
    return d


DATASETS = [
    ("BTC/USDT", "15m", "2025-08-15", "2026-08-15"),
    ("ETH/USDT", "15m", "2025-08-15", "2026-08-15"),
    ("BTC/USDT", "1h", "2024-08-15", "2026-08-15"),
    ("ETH/USDT", "1h", "2024-08-15", "2026-08-15"),
]


def main() -> int:
    print("\n" + "#" * 70)
    print("#  CALIBRATION DU WIN RATE (score -> win rate réalisé)")
    print("#" * 70)

    fetcher = DataFetcher("binance")
    scores: list = []
    outcomes: list = []

    for symbol, tf, start, end in DATASETS:
        print(f"\n>>> {symbol} {tf} ({start} → {end}) — génération des trades...")
        df = fetcher.fetch(symbol, tf, start=start, end=end)
        config = build_config()
        strategy = TradingStrategy(config)
        engine = BacktestEngine(df, config, symbol=symbol, timeframe=tf, broker_type="binance")
        results = engine.run(strategy, warmup_bars=100)
        for t in results.trades:
            scores.append(t.score)
            outcomes.append(1 if t.is_winner() else 0)
        print(f"    {results.total_trades} trades | WR={results.win_rate:.1%}")

    if len(scores) < 20:
        print("[ERREUR] Pas assez de trades générés pour calibrer.")
        return 1

    overall = sum(outcomes) / len(outcomes)
    print(f"\nTotal : {len(scores)} trades, win rate global {overall:.1%}")

    cal = WinRateCalibrator().fit(scores, outcomes)
    cal.save()
    print("\nCalibration terminée -> resources/win_rate_calibration.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
