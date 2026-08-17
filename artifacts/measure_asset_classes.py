"""Winrate & Profit Factor par classe d'actif — AVANT vs APRÈS.

Compare la politique de sortie sur les trois classes d'actif :
  AVANT : break-even à 1.0R, trailing désactivé
  APRÈS : break-even à 1.5R, trailing désactivé (config recommandée)

Probabilité d'entrée permissive (monkeypatch) pour générer des trades :
sans cela, la porte probabiliste bloque tout et on ne peut rien mesurer.

Usage :
    python artifacts/measure_asset_classes.py
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

# (symbole, timeframe, fichier cache, broker, classe d'actif)
DATASETS = [
    ("BTC/USDT", "1h", "BTC_USDT_1h_20240815_20260815_eb0f6eca.csv", "binance", "CRYPTO"),
    ("ETH/USDT", "1h", "ETH_USDT_1h_20240815_20260815_2193d9ae.csv", "binance", "CRYPTO"),
    ("SPY",      "1d", "SPY_1d_20200101_20260705_59f4c8e2.csv",        "alpaca",  "ETF"),
    ("EURUSD",   "1d", "EURUSD=X_1d_20200101_20260705_c4f7fcf4.csv",   "mt5",     "FOREX"),
    ("XAUUSD",   "1d", "GC=F_1d_20200101_20260705_d23a191f.csv",       "mt5",     "FOREX"),
]

MAX_BARS = int(os.getenv("MEASURE_MAX_BARS", "3000"))


def build_config(broker_type: str, be_rr: float) -> dict:
    d = {k: getattr(cfg, k) for k in dir(cfg) if k.isupper()}
    d["BROKER_TYPE"] = broker_type
    d["BE_DYN_RR_RATIO"] = be_rr
    d["TRAIL_ATR_MULT"] = 0.0  # trailing désactivé (mesure isolée du BE)
    return d


def load_cached(fname: str) -> pd.DataFrame:
    df = pd.read_csv(CACHE_DIR / fname, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    if MAX_BARS and len(df) > MAX_BARS:
        df = df.iloc[-MAX_BARS:]
    return df


def run_one(symbol, timeframe, fname, broker, be_rr):
    df = load_cached(fname)
    config = build_config(broker, be_rr)
    strategy = TradingStrategy(config)
    engine = BacktestEngine(df, config, symbol=symbol, timeframe=timeframe, broker_type=broker)
    return engine.run(strategy, warmup_bars=100)


def main() -> int:
    print("\n" + "#" * 78)
    print("#  WINRATE & PROFIT FACTOR PAR CLASSE D'ACTIF — AVANT (BE 1.0R) vs APRÈS (BE 1.5R)")
    print("#" * 78)

    rows = []
    for symbol, timeframe, fname, broker, asset_class in DATASETS:
        print(f"\n>>> {asset_class:<6} {symbol} {timeframe}")
        before = run_one(symbol, timeframe, fname, broker, 1.0)
        after = run_one(symbol, timeframe, fname, broker, 1.5)
        print(f"    AVANT : WR={before.win_rate*100:5.1f}%  PF={before.profit_factor:5.2f}  "
              f"Return={before.total_return_pct:+7.2f}%  Trades={before.total_trades}")
        print(f"    APRÈS : WR={after.win_rate*100:5.1f}%  PF={after.profit_factor:5.2f}  "
              f"Return={after.total_return_pct:+7.2f}%  Trades={after.total_trades}")
        rows.append((asset_class, symbol, before, after))

    print("\n" + "=" * 78)
    print("  SYNTHÈSE")
    print("=" * 78)
    header = (f"  {'Classe':<7} {'Symbole':<10} "
              f"{'WR AVANT':>9} {'WR APRÈS':>9} {'PF AVANT':>9} {'PF APRÈS':>9}")
    print(header)
    print("-" * 78)
    for asset_class, symbol, before, after in rows:
        print(
            f"  {asset_class:<7} {symbol:<10} "
            f"{before.win_rate*100:>8.1f}% {after.win_rate*100:>8.1f}% "
            f"{before.profit_factor:>8.2f} {after.profit_factor:>8.2f}"
        )
    print("-" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
