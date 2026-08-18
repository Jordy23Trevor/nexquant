"""Allocations TSMOM courantes depuis la config + le cache quotidien.

Montre le poids à tenir AUJOURD'HUI pour chaque actif de TSMOM_UNIVERSE,
calculé avec les clôtures passées uniquement (signal « L-1 » + vol roulante).

Usage :
    python artifacts/tsmom_allocations.py
"""

import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import superbot.config as cfg  # noqa: E402
from superbot.backtest.data_fetcher import CACHE_DIR  # noqa: E402
from superbot.strategy import tsmom  # noqa: E402

# Fichier cache correspondant à chaque symbole de TSMOM_UNIVERSE.
CACHE_FILES = {
    "SPY":    "SPY_1d_20200101_20260705_59f4c8e2.csv",
    "XAUUSD": "GC=F_1d_20200101_20260705_d23a191f.csv",
    "BTCUSD": "BTC_USD_1d_20200101_20260705_2f72f20f.csv",
}


def main() -> int:
    if not cfg.TSMOM_ENABLED:
        print("TSMOM_ENABLED=false — la stratégie est désactivée. "
              "Passez TSMOM_ENABLED=true dans .env pour l'activer.")
    prices = {}
    for symbol, fname in CACHE_FILES.items():
        if symbol not in cfg.TSMOM_UNIVERSE:
            continue
        df = pd.read_csv(CACHE_DIR / fname, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        prices[symbol] = df["close"]

    alloc = tsmom.compute_allocations(vars(cfg), prices)
    if alloc.empty:
        print("Aucune allocation calculable (données insuffisantes).")
        return 1

    print(f"TSMOM lookback={cfg.TSMOM_LOOKBACK} skip={cfg.TSMOM_SKIP} "
          f"target_vol={cfg.TSMOM_TARGET_VOL:.0%} max_lev={cfg.TSMOM_MAX_LEVERAGE}\n")
    print(f"  {'Symbole':<8} {'Signal':>7} {'Poids':>8}  {'Mode':<10}")
    print("  " + "-" * 40)
    for _, row in alloc.iterrows():
        mode = "long-only" if row["long_only"] else "long/short"
        print(f"  {row['symbol']:<8} {row['signal']:>+7.0f} {row['weight']:>+7.2f}  {mode:<10}")

    total_long = alloc[alloc["weight"] > 0]["weight"].sum()
    total_short = abs(alloc[alloc["weight"] < 0]["weight"].sum())
    print("  " + "-" * 40)
    print(f"  Exposition LONG {total_long:.2f} | SHORT {total_short:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
