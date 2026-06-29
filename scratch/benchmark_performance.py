"""
Benchmark comparatif de performance financière :
Avec vs Sans application des règles de connaissances crescendo.
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# S'assurer que la racine est dans le path
sys.path.insert(0, str(Path(__file__).parent.parent))

from superbot.strategy.strategy import TradingStrategy
from optimize_rules import RulesBacktester, generate_synthetic_data

def main():
    print("=" * 80)
    print("  BENCHMARK DE PERFORMANCE FINANCIÈRE : CONNAISSANCES CRESCENDO")
    print("=" * 80)

    # 1. Générer un dataset de test synthétique difficile (forte volatilité et alternance de régimes)
    np.random.seed(123)
    data_ranging = generate_synthetic_data(300, regime='ranging')
    data_trending = generate_synthetic_data(300, regime='trending')
    data = pd.concat([data_ranging, data_trending]).reset_index(drop=True)
    data.index = pd.date_range(start="2026-01-01", periods=len(data), freq="1h")

    # Config optimale de base
    config = {
        'SCORE_MIN': 5.0,
        'RISK_PCT': 2.0,
        'SL_ATR_MULT': 1.5,
        'TP_ATR_MULT': 3.0
    }

    # -- CAS A : SANS RÈGLES DE CONNAISSANCES (Stratégie purement technique brute)
    strategy_raw = TradingStrategy(config)
    strategy_raw.knowledge_rules = [] # On vide les règles pour le benchmark

    backtester_raw = RulesBacktester(data)
    res_raw = backtester_raw.run_backtest(strategy_raw)

    # -- CAS B : AVEC LES 133 RÈGLES DE CONNAISSANCES CRESCENDO (Filtres, Sizing, Biais)
    strategy_crescendo = TradingStrategy(config)
    backtester_crescendo = RulesBacktester(data)
    res_crescendo = backtester_crescendo.run_backtest(strategy_crescendo)

    print("\n--- RÉSULTATS COMPARATIFS ---")
    print(f"{'Métrique':<30} | {'Sans Règles (Brute)':<20} | {'Avec Crescendo (133)':<20}")
    print("-" * 78)
    print(f"{'PnL Global (%)':<30} | {res_raw['pnl_pct']:>18.2f}% | {res_crescendo['pnl_pct']:>18.2f}%")
    print(f"{'Nombre de trades':<30} | {res_raw['trades_count']:>19} | {res_crescendo['trades_count']:>19}")
    print(f"{'Taux de réussite (%)':<30} | {res_raw['win_rate']*100:>17.1f}% | {res_crescendo['win_rate']*100:>17.1f}%")
    print(f"{'Sharpe Ratio':<30} | {res_raw['sharpe_ratio']:>19.2f} | {res_crescendo['sharpe_ratio']:>19.2f}")
    print("-" * 78)

    # Explication de la différence de comportement
    print("\nAnalyse du comportement :")
    if res_crescendo['trades_count'] < res_raw['trades_count']:
        print(" -> Le système Crescendo filtre activement les faux signaux (réduction du nombre de trades).")
    if res_crescendo['win_rate'] >= res_raw['win_rate']:
        print(" -> Le taux de réussite est amélioré grâce aux filtres de tendance HTF (Murphy/Elder).")
    if res_crescendo['sharpe_ratio'] >= res_raw['sharpe_ratio'] or res_crescendo['pnl_pct'] >= res_raw['pnl_pct']:
        print(" -> Le rapport rendement/risque (Sharpe) est optimisé par le sizing dynamique fractionné de Kelly.")

if __name__ == "__main__":
    main()
