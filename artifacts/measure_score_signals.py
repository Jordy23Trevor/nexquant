"""Mesure le pouvoir prédictif des signaux candidats indépendants du score.

Exécute une fois BTC/ETH 1h (BE 1.5R, sans trail) et analyse, pour chaque signal
`sig_*` présent dans entry_details, le winrate par tercile + la corrélation de
Spearman avec l'issue du trade. Dump aussi les trades dans
artifacts/trade_signals.csv pour itérer sans re-run.

Usage :
    python artifacts/measure_score_signals.py
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


def run_one(symbol, timeframe, fname, broker):
    df = load_cached(fname)
    config = build_config(broker)
    strategy = TradingStrategy(config)
    engine = BacktestEngine(df, config, symbol=symbol, timeframe=timeframe, broker_type=broker)
    return engine.run(strategy, warmup_bars=100)


def analyze(trades, label: str):
    print(f"\n>>> {label} ({len(trades)} trades, WR {sum(1 for t in trades if t.is_winner())/max(len(trades),1)*100:.1f}%)")
    print(f"  {'Signal':<20} {'n':>5} {'WR bas':>7} {'WR haut':>8} {'edge':>7} {'ρ(spear)':>9}")
    print("  " + "-" * 62)
    rows = []
    for sig in SIGNALS:
        vals = [t.entry_details.get(sig) for t in trades]
        outs = [1 if t.is_winner() else 0 for t in trades]
        df = pd.DataFrame({"v": vals, "out": outs})
        df = df[df["v"].notna()]
        if len(df) < 10:
            continue
        q1, q2 = df["v"].quantile([1 / 3, 2 / 3])
        low = df[df["v"] <= q1]
        high = df[df["v"] >= q2]
        wr_low = low["out"].mean() * 100
        wr_high = high["out"].mean() * 100
        corr = df["v"].corr(df["out"], method="spearman")
        rows.append((sig, len(df), wr_low, wr_high, wr_high - wr_low, corr))
    rows.sort(key=lambda r: -abs(r[5]))
    for sig, n, wr_low, wr_high, edge, corr in rows:
        print(f"  {sig:<20} {n:>5} {wr_low:>6.1f}% {wr_high:>7.1f}% {edge:>+6.1f} {corr:>+8.3f}")
    return rows


def main() -> int:
    all_trades = []
    for symbol, timeframe, fname, broker in DATASETS:
        r = run_one(symbol, timeframe, fname, broker)
        for t in r.trades:
            t.symbol = symbol  # stamp pour l'analyse par actif
        analyze(r.trades, f"{symbol} {timeframe}")
        all_trades.extend(r.trades)

    analyze(all_trades, "POOLÉ BTC+ETH")

    # Dump pour itération hors-ligne
    dump = []
    for t in all_trades:
        row = {"symbol": getattr(t, "symbol", ""),
               "direction": t.direction, "pnl": t.pnl, "winner": int(t.is_winner()),
               "score": t.score, "result": t.result}
        row.update({k: v for k, v in t.entry_details.items() if k.startswith("sig_")})
        dump.append(row)
    pd.DataFrame(dump).to_csv(ROOT / "artifacts" / "trade_signals.csv", index=False)
    print(f"\nDump -> artifacts/trade_signals.csv ({len(dump)} trades)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
