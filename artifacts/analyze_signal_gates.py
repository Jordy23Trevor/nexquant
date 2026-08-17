"""Évalue, hors-ligne, quels signaux candidats améliorent WR/PF par actif.

Lit artifacts/trade_signals.csv (généré par measure_score_signals.py) et, pour
chaque signal et chaque actif, teste la « gate » dans les deux directions
(> médiane ou < médiane) : WR et PF du sous-ensemble survivant vs ensemble total.
C'est une approximation (filtrage, pas ré-exécution du backtest) mais elle
oriente la reconstruction du score.

Usage :
    python artifacts/analyze_signal_gates.py
"""

import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "artifacts" / "trade_signals.csv"

SIGNALS = [
    "sig_adx", "sig_dist_ema_atr", "sig_rsi", "sig_bb_percent",
    "sig_macd_hist_slope", "sig_vol_ratio", "sig_atr_rank", "sig_donchian_pos",
]


def pf(sub: pd.DataFrame) -> float:
    wins = sub[sub["pnl"] > 0]["pnl"].sum()
    losses = abs(sub[sub["pnl"] < 0]["pnl"].sum())
    return wins / losses if losses > 0 else float("inf")


def main() -> int:
    df = pd.read_csv(CSV)
    print(f"Trades chargés : {len(df)}")

    for symbol, sub_all in df.groupby("symbol"):
        if not symbol:
            continue
        wr_all = sub_all["winner"].mean() * 100
        pf_all = pf(sub_all)
        print(f"\n=== {symbol} (n={len(sub_all)}, WR={wr_all:.1f}%, PF={pf_all:.2f}) ===")
        print(f"  {'Signal':<20} {'dir':>6} {'n':>4} {'WR':>7} {'PF':>7} {'ΔWR':>7} {'ΔPF':>7}")
        print("  " + "-" * 66)
        for sig in SIGNALS:
            s = sub_all[sub_all[sig].notna()]
            if len(s) < 8:
                continue
            med = s[sig].median()
            hi = s[s[sig] > med]
            lo = s[s[sig] <= med]
            for label, sub in (("haut", hi), ("bas", lo)):
                if len(sub) < 5:
                    continue
                wr = sub["winner"].mean() * 100
                p = pf(sub)
                print(f"  {sig:<20} {label:>6} {len(sub):>4} {wr:>6.1f}% {p:>6.2f} "
                      f"{wr - wr_all:>+6.1f} {p - pf_all:>+6.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
