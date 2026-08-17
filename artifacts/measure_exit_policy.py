"""Mesure l'impact de la politique de sortie sur le winrate (A/B).

Compare, sur les mêmes données et exactement les mêmes entrées :
  AVANT : break-even à 1.0R, trailing désactivé (ancien backtest)
  APRÈS : break-even à 1.5R, trailing 1.5×ATR activé à +2.0×ATR

La probabilité d'entrée est rendue permissive (monkeypatch) car sinon la porte
probabiliste de analyze_market bloque toutes les entrées (0 trade) et aucune
mesure n'est possible.

Usage :
    python artifacts/measure_exit_policy.py
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
    """Probabilité permissive : génère des trades pour mesurer les sorties."""
    return {"win_prob": 0.9, "expected_value": 0.9 * rr_ratio - 0.1, "has_edge": True}


# Patcher AVANT de lancer la stratégie (l'import dans analyze_market est paresseux).
scorer_module.calculate_probabilistic_win_rate = _permissive_win_rate


# (symbole, timeframe, fichier cache, broker)
DATASETS = [
    ("BTC/USDT", "1h", "BTC_USDT_1h_20240815_20260815_eb0f6eca.csv", "binance"),
    ("ETH/USDT", "1h", "ETH_USDT_1h_20240815_20260815_2193d9ae.csv", "binance"),
]


# (nom, BE_DYN_RR_RATIO, TRAIL_ATR_MULT, TRAIL_ACTIVATE_ATR_MULT)
EXIT_CONFIGS = {
    "AVANT (BE 1.0R, sans trail)":    (1.0, 0.0, 2.0),
    "BE 1.5R, sans trail":            (1.5, 0.0, 2.0),
    "BE 1.5R, trail 1.5@2.0":         (1.5, 1.5, 2.0),
    "BE 1.5R, trail 2.5@3.0":         (1.5, 2.5, 3.0),
}


def build_config(broker_type: str, be_rr: float, trail_mult: float, trail_activate: float) -> dict:
    """Configuration de production, avec la politique de sortie choisie."""
    d = {k: getattr(cfg, k) for k in dir(cfg) if k.isupper()}
    d["BROKER_TYPE"] = broker_type
    d["BE_DYN_RR_RATIO"] = be_rr
    d["TRAIL_ATR_MULT"] = trail_mult      # 0 = trailing désactivé
    d["TRAIL_ACTIVATE_ATR_MULT"] = trail_activate
    return d


# Nombre de bougies à rejouer (les dernières) — réduit le temps de calcul.
# 3000 barres 1h ≈ 4 mois de données, largement assez pour estimer un winrate.
MAX_BARS = int(os.getenv("MEASURE_MAX_BARS", "3000"))


def load_cached(fname: str) -> pd.DataFrame:
    df = pd.read_csv(CACHE_DIR / fname, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    if MAX_BARS and len(df) > MAX_BARS:
        df = df.iloc[-MAX_BARS:]
    return df


def result_breakdown(results) -> dict:
    counts = {}
    for t in results.trades:
        counts[t.result] = counts.get(t.result, 0) + 1
    return counts


# Votes du score (clés des détails) dont on mesure le pouvoir prédictif.
VOTE_KEYS = [
    'ema_cross', 'price_vs_ema200', 'htf_alignment', 'macd_cross',
    'supertrend', 'adx_strength', 'trend_momentum', 'volume_confirmation',
    'elder_impulse_confirm', 'divergence_bonus', 'rsi_extreme', 'stoch_rsi_cross',
    'bb_position', 'price_action', 'sr_proximity', 'macd_hist_cross',
    'mfi_exhaustion', 'pivot_proximity',
]


def vote_analysis(trades) -> str:
    """Mesure le winrate quand chaque vote est présent (>=1) vs absent (0)."""
    rows = []
    winners = [t for t in trades if t.is_winner()]
    for key in VOTE_KEYS:
        on = [t for t in trades if t.entry_details.get(key, 0)]
        off = [t for t in trades if not t.entry_details.get(key, 0)]
        if not on:
            continue
        wr_on = sum(1 for t in on if t.is_winner()) / len(on) * 100
        wr_off = sum(1 for t in off if t.is_winner()) / len(off) * 100 if off else float('nan')
        rows.append((key, len(on), len(off), wr_on, wr_off, wr_on - wr_off))
    rows.sort(key=lambda r: -r[5])
    lines = [f"  {'Vote':<22} {'n=1':>5} {'n=0':>5} {'WR=1':>7} {'WR=0':>7} {'edge':>7}"]
    lines.append("  " + "-" * 58)
    for key, n_on, n_off, wr_on, wr_off, edge in rows:
        lines.append(f"  {key:<22} {n_on:>5} {n_off:>5} {wr_on:>6.1f}% {wr_off:>6.1f}% {edge:>+6.1f}")
    lines.append(f"  (base : {len(winners)}/{len(trades)} = {len(winners)/len(trades)*100:.1f}%)")
    return "\n".join(lines)


def run_one(symbol: str, timeframe: str, fname: str, broker: str, be_rr: float,
             trail_mult: float, trail_activate: float):
    df = load_cached(fname)
    config = build_config(broker, be_rr, trail_mult, trail_activate)
    strategy = TradingStrategy(config)
    engine = BacktestEngine(df, config, symbol=symbol, timeframe=timeframe, broker_type=broker)
    results = engine.run(strategy, warmup_bars=100)
    return results


def main() -> int:
    print("\n" + "#" * 74)
    print("#  A/B POLITIQUE DE SORTIE — winrate AVANT vs APRÈS")
    print("#" * 74)

    summary = {}
    for symbol, timeframe, fname, broker in DATASETS:
        print(f"\n{'=' * 74}\n>>> {symbol} {timeframe}  ({fname})\n{'=' * 74}")
        for label, (be_rr, trail_mult, trail_activate) in EXIT_CONFIGS.items():
            r = run_one(symbol, timeframe, fname, broker, be_rr, trail_mult, trail_activate)
            breakdown = result_breakdown(r)
            print(f"\n  {label}")
            print(f"    Trades        : {r.total_trades}")
            print(f"    Win rate      : {r.win_rate*100:.1f}%")
            print(f"    Profit Factor : {r.profit_factor:.2f}")
            print(f"    Return        : {r.total_return_pct:+.2f}%")
            print(f"    Max DD        : {r.max_drawdown_pct:.2f}%")
            print(f"    Sorties       : {breakdown}")
            summary[(symbol, label)] = r

    print("\n" + "=" * 74)
    print("  SYNTHÈSE")
    print("=" * 74)
    header = f"  {'Run':<30} {'Trades':>7} {'WinRate':>8} {'PF':>6} {'Return':>9} {'MaxDD':>8}"
    print(header)
    print("-" * 74)
    for symbol, _, _, _ in DATASETS:
        for label in EXIT_CONFIGS:
            r = summary[(symbol, label)]
            print(
                f"  {symbol:<10} {label:<18} {r.total_trades:>7} {r.win_rate*100:>7.1f}% "
                f"{r.profit_factor:>6.2f} {r.total_return_pct:>+8.2f}% {r.max_drawdown_pct:>7.2f}%"
            )
    print("-" * 74)

    # Pouvoir prédictif de chaque vote du score (config BE 1.5R sans trailing).
    print("\n" + "=" * 74)
    print("  POUVOIR PRÉDICTIF DES VOTES DU SCORE (BE 1.5R, sans trail)")
    print("=" * 74)
    all_trades = []
    for symbol, _, _, _ in DATASETS:
        all_trades.extend(summary[(symbol, "BE 1.5R, sans trail")].trades)
    print(vote_analysis(all_trades))
    return 0


if __name__ == "__main__":
    sys.exit(main())
