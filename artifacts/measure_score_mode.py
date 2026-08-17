"""Compare le score par votes (ancien) vs le score par signaux (nouveau).

BE 1.5R, trailing désactivé. Probabilité d'entrée permissive (monkeypatch).
Usage : python artifacts/measure_score_mode.py
"""

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("BACKTEST_MODE", "true")

import pandas as pd  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

for _n in ("strategy", "backtest.engine", "backtest.data_fetcher", "backtest.report",
           "root", "urllib3", "scorer", "ml.win_rate_calibrator"):
    logging.getLogger(_n).setLevel(logging.WARNING)

import superbot.config as cfg  # noqa: E402
import superbot.strategy.components.scorer as scorer_module  # noqa: E402
from superbot.backtest.engine import BacktestEngine  # noqa: E402
from superbot.backtest.data_fetcher import CACHE_DIR  # noqa: E402
from superbot.strategy.strategy import TradingStrategy  # noqa: E402


def _permissive_win_rate(score, market_regime="TRENDING", adx_value=20.0, rr_ratio=2.0):
    return {"win_prob": 0.9, "expected_value": 0.9 * rr_ratio - 0.1, "has_edge": True}


scorer_module.calculate_probabilistic_win_rate = _permissive_win_rate

DATASETS = [
    ("BTC/USDT", "1h", "BTC_USDT_1h_20240815_20260815_eb0f6eca.csv", "binance"),
    ("ETH/USDT", "1h", "ETH_USDT_1h_20240815_20260815_2193d9ae.csv", "binance"),
]

MAX_BARS = int(os.getenv("MEASURE_MAX_BARS", "3000"))


def build_config(broker_type: str, score_mode: str) -> dict:
    d = {k: getattr(cfg, k) for k in dir(cfg) if k.isupper()}
    d["BROKER_TYPE"] = broker_type
    d["BE_DYN_RR_RATIO"] = 1.5
    d["TRAIL_ATR_MULT"] = 0.0
    d["SCORE_MODE"] = score_mode
    return d


def load_cached(fname: str) -> pd.DataFrame:
    df = pd.read_csv(CACHE_DIR / fname, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    if MAX_BARS and len(df) > MAX_BARS:
        df = df.iloc[-MAX_BARS:]
    return df


def run_one(symbol, timeframe, fname, broker, score_mode):
    df = load_cached(fname)
    config = build_config(broker, score_mode)
    strategy = TradingStrategy(config)
    engine = BacktestEngine(df, config, symbol=symbol, timeframe=timeframe, broker_type=broker)
    return engine.run(strategy, warmup_bars=100)


def main() -> int:
    modes = sys.argv[1:] or ["votes", "signals"]
    print(f"{'Mode':<12} {'Symbole':<10} {'Trades':>7} {'WinRate':>8} {'PF':>6} {'Return':>9}")
    print("-" * 60)
    for mode in modes:
        for symbol, timeframe, fname, broker in DATASETS:
            r = run_one(symbol, timeframe, fname, broker, mode)
            print(f"{mode:<12} {symbol:<10} {r.total_trades:>7} {r.win_rate*100:>7.1f}% "
                  f"{r.profit_factor:>6.2f} {r.total_return_pct:>+8.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
