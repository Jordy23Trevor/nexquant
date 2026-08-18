"""Collecte les trades (avec timestamp + signaux candidats) pour le walk-forward.

Exécute un backtest permissif (porte probabiliste bypassée) sur chaque jeu de
données en cache, et dump les trades dans artifacts/trade_signals_wf.csv avec
entry_time, asset_class, symbol et les features `sig_*`.

Usage :
    python artifacts/collect_trades_wf.py [symbole ...]   # filtre optionnel
    python artifacts/collect_trades_wf.py                 # tout collecter
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
OUT = ROOT / "artifacts" / "trade_signals_wf.csv"

SIGNALS = [
    "sig_adx", "sig_dist_ema_atr", "sig_rsi", "sig_bb_percent",
    "sig_macd_hist_slope", "sig_vol_ratio", "sig_atr_rank", "sig_donchian_pos",
]


def build_config(broker_type: str) -> dict:
    d = {k: getattr(cfg, k) for k in dir(cfg) if k.isupper()}
    d["BROKER_TYPE"] = broker_type
    d["BE_DYN_RR_RATIO"] = 1.5
    d["TRAIL_ATR_MULT"] = 0.0
    return d


def load_cached(fname: str) -> pd.DataFrame:
    df = pd.read_csv(CACHE_DIR / fname, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    if MAX_BARS and len(df) > MAX_BARS:
        df = df.iloc[-MAX_BARS:]
    return df


def run_one(symbol, timeframe, fname, broker, asset_class):
    df = load_cached(fname)
    config = build_config(broker)
    strategy = TradingStrategy(config)
    engine = BacktestEngine(df, config, symbol=symbol, timeframe=timeframe, broker_type=broker)
    r = engine.run(strategy, warmup_bars=100)
    rows = []
    for t in r.trades:
        row = {
            "symbol": symbol,
            "asset_class": asset_class,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "direction": t.direction,
            "pnl": t.pnl,
            "winner": int(t.is_winner()),
            "score": t.score,
            "result": t.result,
        }
        row.update({k: v for k, v in t.entry_details.items() if k.startswith("sig_")})
        rows.append(row)
    print(f"  {asset_class:<6} {symbol:<10} {timeframe:<4} -> {len(rows)} trades")
    return rows


def main() -> int:
    only = [a.upper().replace("/", "") for a in sys.argv[1:]]
    # Écriture incrémentale par symbole : un timeout ne perd pas les runs déjà faits.
    existing = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame()
    if existing.empty:
        existing.to_csv(OUT, index=False)  # en-têtes

    for symbol, timeframe, fname, broker, asset_class in DATASETS:
        if only and not any(o in symbol.upper().replace("/", "") for o in only):
            continue
        if not existing.empty and symbol in set(existing.get("symbol", [])):
            print(f"  skip {symbol} (déjà collecté)")
            continue
        rows = run_one(symbol, timeframe, fname, broker, asset_class)
        if rows:
            df = pd.DataFrame(rows)
            for sig in SIGNALS:
                if sig not in df.columns:
                    df[sig] = pd.NA
            df = df[["symbol", "asset_class", "entry_time", "direction", "pnl",
                     "winner", "score", "result"] + SIGNALS]
            existing = pd.concat([existing, df], ignore_index=True)
            existing.to_csv(OUT, index=False)

    print(f"\nDump -> {OUT} ({len(existing)} trades)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
