"""Compare plusieurs jeux de poids du score TRENDING (BE 1.5R, sans trail).

Hypothèse : le seul vote à edge positif stable est Elder Impulse. On compare :
  - BASELINE : tous les votes à poids 1.0 (comportement d'origine)
  - ELDER+   : Elder ×2, les autres à 1.0 (on garde macd/volume)
  - CURRENT  : macd/volume retirés (0.0), Elder ×2 (reweighting actuel)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import superbot.strategy.components.scorer as scorer_module  # noqa: E402
from artifacts.measure_exit_policy import DATASETS, run_one, result_breakdown  # noqa: E402

VARIANTS = {
    "BASELINE (tous 1.0)": {
        'ema_cross': 1.0, 'price_vs_ema200': 1.0, 'htf_alignment': 1.0,
        'macd_cross': 1.0, 'supertrend': 1.0, 'adx_strength': 1.0,
        'trend_momentum': 1.0, 'volume_confirmation': 1.0, 'elder_impulse_confirm': 1.0,
    },
    "ELDER+ (elder×2)": {
        'ema_cross': 1.0, 'price_vs_ema200': 1.0, 'htf_alignment': 1.0,
        'macd_cross': 1.0, 'supertrend': 1.0, 'adx_strength': 1.0,
        'trend_momentum': 1.0, 'volume_confirmation': 1.0, 'elder_impulse_confirm': 2.0,
    },
    "CURRENT (macd/vol 0, elder×2)": {
        'ema_cross': 1.0, 'price_vs_ema200': 1.0, 'htf_alignment': 1.0,
        'macd_cross': 0.0, 'supertrend': 1.0, 'adx_strength': 1.0,
        'trend_momentum': 1.0, 'volume_confirmation': 0.0, 'elder_impulse_confirm': 2.0,
    },
}

for label, weights in VARIANTS.items():
    scorer_module.TRENDING_VOTE_WEIGHTS = dict(weights)
    print(f"\n=== {label} ===")
    print(f"{'Symbole':<10} {'Trades':>7} {'WinRate':>8} {'PF':>6} {'Return':>9} {'Sorties'}")
    for symbol, timeframe, fname, broker in DATASETS:
        r = run_one(symbol, timeframe, fname, broker, be_rr=1.5, trail_mult=0.0, trail_activate=2.0)
        print(
            f"{symbol:<10} {r.total_trades:>7} {r.win_rate*100:>7.1f}% "
            f"{r.profit_factor:>6.2f} {r.total_return_pct:>+8.2f}% {result_breakdown(r)}"
        )
