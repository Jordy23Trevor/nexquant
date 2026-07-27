#!/usr/bin/env python
"""
NexQuant Optimizer & Backtester CLI — Phase 1
===============================================
Interface en ligne de commande pour lancer des backtests sur données réelles
et optimiser les paramètres de la stratégie (Optuna ou recherche aléatoire).

Exemples d'utilisation :

  # Backtest simple sur BTC/USDT H1 (2024)
  python optimize_rules.py --broker binance --symbol BTCUSDT --timeframe 1h --start 2024-01-01 --end 2024-12-31

  # Backtest avec fallback yfinance (sans clé API)
  python optimize_rules.py --broker yfinance --symbol BTC-USD --timeframe 1h --start 2024-01-01

  # Mode Walk-Forward 70/30
  python optimize_rules.py --broker binance --symbol BTCUSDT --timeframe 1h --start 2024-01-01 --walk-forward

  # Optimisation Optuna (25 essais)
  python optimize_rules.py --broker binance --symbol BTCUSDT --timeframe 1h --start 2024-01-01 --optimize --trials 25

  # Forcer le re-téléchargement (ignorer le cache)
  python optimize_rules.py --broker binance --symbol BTCUSDT --timeframe 1h --start 2024-01-01 --no-cache

  # Sauvegarder le rapport JSON + graphique
  python optimize_rules.py --broker binance --symbol BTCUSDT --timeframe 1h --start 2024-01-01 --save-report --plot
"""
import os
import sys
import math
import argparse
import logging
import random
from typing import Dict, Any

import pandas as pd

# S'assurer que le répertoire racine est dans le path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(name)s — %(levelname)s — %(message)s'
)
log = logging.getLogger("optimizer")

# ─── Chargement de la configuration NexQuant ────────────────────────────────
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "superbot.config",
        os.path.join(os.path.dirname(__file__), "superbot", "config.py")
    )
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    BASE_CONFIG = {k: v for k, v in vars(config_module).items() if k.isupper()}
    log.info(f"Configuration NexQuant chargée ({len(BASE_CONFIG)} paramètres)")
except Exception as e:
    log.warning(f"Impossible de charger superbot/config.py ({e}) — utilisation d'une config minimale.")
    BASE_CONFIG = {
        'SCORE_MIN': 6, 'RISK_PCT': 1.0, 'SL_ATR_MULT': 1.5,
        'TP_ATR_MULT': 3.0, 'EMA_FAST': 9, 'EMA_SLOW': 21,
        'EMA_TREND': 200, 'ADX_TREND': 22, 'RSI_LEN': 14,
        'ATR_LEN': 14, 'ADX_LEN': 14, 'BE_DYN_RR': True,
        'MACD_FAST': 12, 'MACD_SLOW': 26, 'MACD_SIGNAL': 9,
        'BB_LEN': 20, 'BB_STD': 2.0, 'RSI_OS': 30, 'RSI_OB': 70,
        'BROKER_TYPE': 'binance',
    }


def build_strategy_config(overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Fusionne la config de base avec des surcharges."""
    config = dict(BASE_CONFIG)
    config.update(overrides)
    return config


def run_single_backtest(args) -> None:
    """Lance un backtest simple et affiche les résultats."""
    from superbot.backtest.data_fetcher import DataFetcher
    from superbot.backtest.engine import BacktestEngine
    from superbot.backtest.report import BacktestReport, compare_walk_forward
    from superbot.strategy.strategy import TradingStrategy

    # 1. Téléchargement des données
    log.info(f"Téléchargement des données : {args.symbol} {args.timeframe} ({args.broker})")
    fetcher = DataFetcher(broker_type=args.broker)
    df = fetcher.fetch(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start=args.start,
        end=args.end,
        periods=args.periods,
        force_refresh=args.no_cache,
    )

    log.info(f"{len(df)} bougies chargées : {df.index[0].date()} → {df.index[-1].date()}")

    # 2. Construire la configuration
    config = build_strategy_config({
        'SCORE_MIN': args.score_min,
        'RISK_PCT': args.risk_pct,
        'SL_ATR_MULT': args.sl_mult,
        'TP_ATR_MULT': args.tp_mult,
        'BROKER_TYPE': args.broker,
    })

    strategy = TradingStrategy(config)

    # 3. Lancer le backtest
    engine = BacktestEngine(
        df=df,
        config=config,
        initial_balance=args.balance,
        commission_pct=args.commission,
        symbol=args.symbol,
        timeframe=args.timeframe,
        broker_type=args.broker,
    )

    if args.walk_forward:
        # Mode Walk-Forward
        in_sample, out_sample = engine.run_walk_forward(strategy, train_ratio=0.7)

        print("\n  ── IN-SAMPLE (70%) ──")
        report_is = BacktestReport(in_sample)
        report_is.print_summary()

        print("\n  ── OUT-OF-SAMPLE (30%) ──")
        report_oos = BacktestReport(out_sample)
        report_oos.print_summary()

        compare_walk_forward(in_sample, out_sample)

        if args.save_report or args.json_output:
            report_is.save_json()
            report_oos.save_json(filename=args.json_output if args.json_output else 'backtest_results.json')
        if args.plot:
            report_oos.plot_equity_curve()

    else:
        results = engine.run(strategy)
        report = BacktestReport(results)
        report.print_summary()
        report.print_regime_breakdown() if hasattr(report, 'print_regime_breakdown') else None
        report._print_regime_breakdown()
        report.print_monthly_breakdown()

        if args.trades:
            report.print_trades_breakdown(max_trades=args.trades)

        if args.save_report or args.json_output:
            out_file = args.json_output if args.json_output else 'backtest_results.json'
            report.save_json(filename=out_file)

        if args.plot:
            report.plot_equity_curve()


def run_optimization(args) -> None:
    """Lance l'optimisation Optuna ou une recherche aléatoire si Optuna absent."""
    from superbot.backtest.data_fetcher import DataFetcher
    from superbot.backtest.engine import BacktestEngine
    from superbot.strategy.strategy import TradingStrategy

    log.info(f"Téléchargement des données pour optimisation : {args.symbol} {args.timeframe}")
    fetcher = DataFetcher(broker_type=args.broker)
    df = fetcher.fetch(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start=args.start,
        end=args.end,
        periods=args.periods,
        force_refresh=args.no_cache,
    )

    # Définir la fonction objectif commune
    def objective_fn(score_min: int, risk_pct: float, sl_mult: float, tp_mult: float) -> float:
        config = build_strategy_config({
            'SCORE_MIN': score_min,
            'RISK_PCT': risk_pct,
            'SL_ATR_MULT': sl_mult,
            'TP_ATR_MULT': tp_mult,
            'BROKER_TYPE': args.broker,
        })
        strategy = TradingStrategy(config)
        engine = BacktestEngine(
            df=df, config=config, initial_balance=args.balance,
            commission_pct=args.commission, symbol=args.symbol, timeframe=args.timeframe,
        )
        # In-Sample uniquement pour l'optimisation
        split_idx = int(len(df) * 0.7)
        engine.df = df.iloc[:split_idx]
        results = engine.run(strategy)

        # Fonction objectif : maximiser le rendement ajusté au Sharpe
        if results.total_trades < 5:
            return -9999.0  # Pénaliser les stratégies qui tradent trop peu
        if results.max_drawdown_pct > 30:
            return -9999.0  # Pénaliser les drawdowns catastrophiques

        # Combiner rendement, Sharpe et Profit Factor
        score = results.total_return_pct * 0.4 + results.sharpe_ratio * 20 + results.profit_factor * 5
        return score

    best_params = {}
    best_score = -9999.0

    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        log.info(f"Optimisation Optuna — {args.trials} essais")

        def optuna_objective(trial):
            return objective_fn(
                score_min=trial.suggest_int('score_min', 4, 9),
                risk_pct=trial.suggest_float('risk_pct', 0.5, 2.5),
                sl_mult=trial.suggest_float('sl_mult', 1.0, 3.0),
                tp_mult=trial.suggest_float('tp_mult', 2.0, 5.0),
            )

        study = optuna.create_study(direction='maximize')
        study.optimize(optuna_objective, n_trials=args.trials, show_progress_bar=True)
        best_params = study.best_params
        best_score = study.best_value

    except ImportError:
        log.warning("Optuna non installé — recherche aléatoire (pip install optuna pour activer)")
        for i in range(args.trials):
            params = {
                'score_min': random.randint(4, 9),
                'risk_pct': random.uniform(0.5, 2.5),
                'sl_mult': random.uniform(1.0, 3.0),
                'tp_mult': random.uniform(2.0, 5.0),
            }
            trial_score = objective_fn(**params)
            if trial_score > best_score:
                best_score = trial_score
                best_params = dict(params)
            if (i + 1) % 5 == 0:
                log.info(f"  Essai {i+1}/{args.trials} — meilleur score : {best_score:.2f}")

    # Afficher les résultats de l'optimisation
    sep = "=" * 60
    print(f"\n{sep}")
    print("  RÉSULTATS DE L'OPTIMISATION")
    print(sep)
    print(f"  Meilleur score composite : {best_score:.2f}")
    print(f"  Paramètres optimaux :")
    for k, v in best_params.items():
        print(f"    {k:<20} = {v}")
    print(sep)

    # Valider sur l'Out-of-Sample
    print("\n  Validation Out-of-Sample avec les paramètres optimaux...")
    from superbot.backtest.engine import BacktestEngine
    from superbot.backtest.report import BacktestReport, compare_walk_forward

    config_best = build_strategy_config({
        'SCORE_MIN': best_params.get('score_min', 6),
        'RISK_PCT': best_params.get('risk_pct', 1.0),
        'SL_ATR_MULT': best_params.get('sl_mult', 1.5),
        'TP_ATR_MULT': best_params.get('tp_mult', 3.0),
        'BROKER_TYPE': args.broker,
    })
    strategy_best = TradingStrategy(config_best)
    engine_full = BacktestEngine(
        df=df, config=config_best, initial_balance=args.balance,
        commission_pct=args.commission, symbol=args.symbol, timeframe=args.timeframe,
    )
    in_sample, out_sample = engine_full.run_walk_forward(strategy_best, train_ratio=0.7)

    report_is = BacktestReport(in_sample)
    report_oos = BacktestReport(out_sample)

    print("\n  IN-SAMPLE (70%) — Paramètres optimaux :")
    report_is.print_summary()
    print("\n  OUT-OF-SAMPLE (30%) — Validation :")
    report_oos.print_summary()
    compare_walk_forward(in_sample, out_sample)

    if args.save_report:
        report_oos.save_json()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="NexQuant Backtest & Optimizer CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Source de données
    data_group = parser.add_argument_group("📥 Données")
    data_group.add_argument('--broker',    default='yfinance', help="Broker source (binance/alpaca/mt5/yfinance) [défaut: yfinance]")
    data_group.add_argument('--symbol',    default='BTC-USD',  help="Symbole (ex: BTCUSDT, SPY, EURUSD) [défaut: BTC-USD]")
    data_group.add_argument('--timeframe', default='1h',       help="Timeframe (1m/5m/15m/30m/1h/4h/1d/1w) [défaut: 1h]")
    data_group.add_argument('--start',     default=None,       help="Date de début ISO (ex: 2024-01-01)")
    data_group.add_argument('--end',       default=None,       help="Date de fin ISO (ex: 2024-12-31)")
    data_group.add_argument('--periods',   type=int, default=2000, help="Nombre de bougies si --start absent [défaut: 2000]")
    data_group.add_argument('--no-cache',  action='store_true', help="Forcer le re-téléchargement (ignore le cache)")

    # Paramètres de simulation
    sim_group = parser.add_argument_group("⚙️  Simulation")
    sim_group.add_argument('--balance',    type=float, default=10000.0, help="Capital initial en USD [défaut: 10000]")
    sim_group.add_argument('--commission', type=float, default=0.04,    help="Commission par trade en %% [défaut: 0.04]")
    sim_group.add_argument('--score-min',  type=int,   default=6,       help="Score minimum d'entrée [défaut: 6]")
    sim_group.add_argument('--risk-pct',   type=float, default=1.0,     help="Risque par trade en %% [défaut: 1.0]")
    sim_group.add_argument('--sl-mult',    type=float, default=1.5,     help="Multiplicateur SL × ATR [défaut: 1.5]")
    sim_group.add_argument('--tp-mult',    type=float, default=3.0,     help="Multiplicateur TP × ATR [défaut: 3.0]")

    # Modes d'exécution
    mode_group = parser.add_argument_group("🎯 Mode d'exécution")
    mode_group.add_argument('--walk-forward', action='store_true', help="Activer le mode Walk-Forward (70/30)")
    mode_group.add_argument('--optimize',     action='store_true', help="Activer l'optimisation des paramètres")
    mode_group.add_argument('--trials',       type=int, default=25, help="Nombre d'essais d'optimisation [défaut: 25]")

    # Sortie
    out_group = parser.add_argument_group("📊 Sortie")
    out_group.add_argument('--save-report', action='store_true', help="Sauvegarder le rapport JSON")
    out_group.add_argument('--plot',        action='store_true', help="Afficher la courbe d'équité (matplotlib)")
    out_group.add_argument('--trades',      type=int, default=0, help="Afficher les N derniers trades (0=désactivé)")
    out_group.add_argument('--run-backtest', action='store_true', help="Ignoré, alias API pour run")
    out_group.add_argument('--json-output',  type=str, default=None, help="Chemin spécifique où sauvegarder le rapport JSON (API)")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print("\n" + "=" * 60)
    print("  NexQuant Backtest & Optimizer — Phase 1")
    print(f"  {args.symbol} | {args.timeframe} | Broker: {args.broker}")
    print("=" * 60 + "\n")

    if args.optimize:
        run_optimization(args)
    else:
        run_single_backtest(args)
