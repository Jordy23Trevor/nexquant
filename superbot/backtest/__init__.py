"""
NexQuant Backtest Module
========================
Module de backtesting sur données historiques réelles.

Usage :
    from superbot.backtest.data_fetcher import DataFetcher
    from superbot.backtest.engine import BacktestEngine
    from superbot.backtest.report import BacktestReport

    fetcher = DataFetcher(broker_type='binance')
    df = fetcher.fetch('BTCUSDT', '1h', start='2024-01-01', end='2024-12-31')

    engine = BacktestEngine(df, config)
    results = engine.run(strategy)

    report = BacktestReport(results)
    report.print_summary()
    report.save_json('results/btcusdt_2024.json')
"""
from superbot.backtest.data_fetcher import DataFetcher
from superbot.backtest.engine import BacktestEngine, BacktestResults
from superbot.backtest.report import BacktestReport

__all__ = ['DataFetcher', 'BacktestEngine', 'BacktestResults', 'BacktestReport']
