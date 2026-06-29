"""
Benchmark comparatif de performance financière en marché favorable (Trending).
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from superbot.strategy.strategy import TradingStrategy
from optimize_rules import RulesBacktester, generate_synthetic_data

def main():
    print("=" * 80)
    print("  BENCHMARK FINANCIER EN MARCHÉ TENDANCE HAUSSIÈRE")
    print("=" * 80)

    # dataset haussier stable
    data = generate_synthetic_data(500, regime='trending')

    # Config
    config = {
        'SCORE_MIN': 5.0,
        'RISK_PCT': 2.0,
        'SL_ATR_MULT': 1.5,
        'TP_ATR_MULT': 3.0
    }

    # Sans règles
    strategy_raw = TradingStrategy(config)
    strategy_raw.knowledge_rules = []
    backtester_raw = RulesBacktester(data)
    res_raw = backtester_raw.run_backtest(strategy_raw)

    # Avec Crescendo
    strategy_crescendo = TradingStrategy(config)
    backtester_crescendo = RulesBacktester(data)
    res_crescendo = backtester_crescendo.run_backtest(strategy_crescendo)

    print("\n--- RÉSULTATS COMPARATIFS (TRENDING HAUSSIER) ---")
    print(f"{'Métrique':<30} | {'Sans Règles (Brute)':<20} | {'Avec Crescendo (133)':<20}")
    print("-" * 78)
    print(f"{'PnL Global (%)':<30} | {res_raw['pnl_pct']:>18.2f}% | {res_crescendo['pnl_pct']:>18.2f}%")
    print(f"{'Nombre de trades':<30} | {res_raw['trades_count']:>19} | {res_crescendo['trades_count']:>19}")
    print(f"{'Taux de réussite (%)':<30} | {res_raw['win_rate']*100:>17.1f}% | {res_crescendo['win_rate']*100:>17.1f}%")
    print(f"{'Sharpe Ratio':<30} | {res_raw['sharpe_ratio']:>19.2f} | {res_crescendo['sharpe_ratio']:>19.2f}")
    print("-" * 78)

if __name__ == "__main__":
    main()
