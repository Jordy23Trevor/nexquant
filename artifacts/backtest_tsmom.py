"""Time-series momentum (TSMOM) — backtest via le module superbot.strategy.tsmom.

Compare les lookbacks canoniques (12, 6, 3, 1 mois) sur l'univers liquide en
cache, avec ciblage de volatilité (15 % par actif) pour maîtriser les drawdowns
de BTC. Portefeuille égal-poids.

Usage :
    python artifacts/backtest_tsmom.py
"""

import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from superbot.backtest.data_fetcher import CACHE_DIR  # noqa: E402
from superbot.strategy import tsmom  # noqa: E402

# (symbole, fichier, long_only, coût aller-retour, périodes/an)
ASSETS = [
    ("SPY",    "SPY_1d_20200101_20260705_59f4c8e2.csv",        True,  0.0005, 252),
    ("XAUUSD", "GC=F_1d_20200101_20260705_d23a191f.csv",       False, 0.0005, 252),
    ("BTCUSD", "BTC_USD_1d_20200101_20260705_2f72f20f.csv",    False, 0.0010, 365),
]

LOOKBACKS = [12, 6, 3, 1]


def load_daily(fname: str) -> pd.Series:
    df = pd.read_csv(CACHE_DIR / fname, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df["close"]


def main() -> int:
    print("=" * 92)
    print("  TIME-SERIES MOMENTUM (mensuel, 2020 → 2026, vol ciblée 15 %/actif)")
    print("=" * 92)

    for lookback in LOOKBACKS:
        print(f"\n### Lookback {lookback} mois (skip 1 mois)")
        print(f"  {'Actif':<8} {'Mois':>5} {'CAGR':>8} {'Vol':>7} {'Sharpe':>7} "
              f"{'MaxDD':>8} {'PF':>6} {'WR':>6}")
        print("  " + "-" * 64)
        strat_rets = {}
        for name, fname, long_only, cost, ppy in ASSETS:
            closes = load_daily(fname)
            d = tsmom.backtest_monthly(closes, lookback=lookback, long_only=long_only,
                                       cost=cost, periods_per_year=ppy)
            strat_rets[name] = d["strat"]
            m = tsmom.metrics(d["strat"])
            if m:
                print(f"  {name:<8} {m['n_months']:>5} {m['cagr']*100:>7.1f}% "
                      f"{m['vol']*100:>6.1f}% {m['sharpe']:>7.2f} {m['maxdd']*100:>7.1f}% "
                      f"{m['pf']:>6.2f} {m['wr']*100:>5.0f}%")
        port = tsmom.portfolio_returns(strat_rets)
        m = tsmom.metrics(port)
        print("  " + "-" * 64)
        if m:
            print(f"  {'PORTF':<8} {m['n_months']:>5} {m['cagr']*100:>7.1f}% "
                  f"{m['vol']*100:>6.1f}% {m['sharpe']:>7.2f} {m['maxdd']*100:>7.1f}% "
                  f"{m['pf']:>6.2f} {m['wr']*100:>5.0f}%")

    print("\nNote : SPY long-only, XAUUSD/BTCUSD long/short. Vol ciblée 15 %/actif, "
          "levier plafonné à 1.5x. Coûts : SPY 5pb, XAUUSD 5pb, BTCUSD 10pb (aller-retour).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
