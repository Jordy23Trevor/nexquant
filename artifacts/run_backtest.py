"""Backtest de bout en bout de la stratégie sur données historiques propres.

Charge les données OHLCV réelles du cache local (superbot/backtest/cache/),
applique la configuration de production (superbot.config) avec le bon type de
broker par classe d'actif, puis produit un rapport de performance par instrument
(+ comparaison in-sample / out-of-sample pour BTC).

Usage :
    python artifacts/run_backtest.py
"""

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Backtest sans dépendance aux identifiants broker réels.
os.environ.setdefault("BACKTEST_MODE", "true")

import pandas as pd

for _name in ("strategy", "backtest.engine", "backtest.data_fetcher", "backtest.report", "root"):
    logging.getLogger(_name).setLevel(logging.WARNING)

import superbot.config as cfg
from superbot.backtest.engine import BacktestEngine
from superbot.backtest.report import BacktestReport, compare_walk_forward
from superbot.backtest.data_fetcher import CACHE_DIR
from superbot.strategy.strategy import TradingStrategy


def build_config(broker_type: str) -> dict:
    """Configuration de production, avec le broker de la classe d'actif visée."""
    d = {k: getattr(cfg, k) for k in dir(cfg) if k.isupper()}
    d["BROKER_TYPE"] = broker_type
    return d


# (symbole de rapport, broker pour la détection de classe d'actif, fichier cache)
DATASETS = [
    ("BTC-USD", "binance", "BTC_USD_1d_20200101_20260705_2f72f20f.csv"),
    ("EURUSD",  "mt5",     "EURUSD=X_1d_20200101_20260705_c4f7fcf4.csv"),
    ("SPY",     "alpaca",  "SPY_1d_20200101_20260705_59f4c8e2.csv"),
    ("XAUUSD",  "mt5",     "GC=F_1d_20200101_20260705_d23a191f.csv"),
]


def load_cached(fname: str) -> pd.DataFrame:
    df = pd.read_csv(CACHE_DIR / fname, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def run_one(symbol: str, broker_type: str, fname: str):
    df = load_cached(fname)
    config = build_config(broker_type)
    strategy = TradingStrategy(config)
    engine = BacktestEngine(df, config, symbol=symbol, timeframe="1d", broker_type=broker_type)
    results = engine.run(strategy, warmup_bars=50)

    report = BacktestReport(results)
    report.print_summary()
    report.print_monthly_breakdown()
    report.save_json()
    return results


def main() -> int:
    print("\n" + "#" * 70)
    print("#  NEXQUANT — BACKTEST END-TO-END (données historiques propres)")
    print("#" * 70)

    all_results = {}
    for symbol, broker_type, fname in DATASETS:
        print(f"\n{'=' * 70}\n>>> {symbol} ({broker_type}) — {fname}\n{'=' * 70}")
        try:
            all_results[symbol] = run_one(symbol, broker_type, fname)
        except Exception as e:
            import traceback
            print(f"[ERREUR] {symbol}: {e}")
            traceback.print_exc()
            all_results[symbol] = None

    # Walk-forward BTC (sur-apprentissage ?)
    print("\n" + "=" * 70)
    print(">>> WALK-FORWARD BTC-USD (70% in-sample / 30% out-of-sample)")
    print("=" * 70)
    try:
        df_btc = load_cached("BTC_USD_1d_20200101_20260705_2f72f20f.csv")
        strategy = TradingStrategy(build_config("binance"))
        engine = BacktestEngine(df_btc, build_config("binance"), symbol="BTC-USD",
                                timeframe="1d", broker_type="binance")
        in_sample, out_sample = engine.run_walk_forward(strategy, train_ratio=0.7, warmup_bars=50)
        compare_walk_forward(in_sample, out_sample)
    except Exception as e:
        import traceback
        print(f"[ERREUR] walk-forward BTC: {e}")
        traceback.print_exc()

    # Synthèse consolidée
    print("\n" + "=" * 70)
    print("  SYNTHÈSE")
    print("=" * 70)
    header = f"  {'Symbole':<10} {'Return':>9} {'MaxDD':>8} {'Sharpe':>8} {'WinRate':>8} {'PF':>6} {'Trades':>7}"
    print(header)
    print("-" * 70)
    for symbol, r in all_results.items():
        if r is None:
            print(f"  {symbol:<10} {'FAILED':>9}")
            continue
        print(
            f"  {symbol:<10} {r.total_return_pct:>+8.2f}% {r.max_drawdown_pct:>7.2f}% "
            f"{r.sharpe_ratio:>8.2f} {r.win_rate*100:>7.1f}% {r.profit_factor:>6.2f} {r.total_trades:>7}"
        )
    print("-" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
