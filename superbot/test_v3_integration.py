"""Test d'intégration complet NexQuant V3"""
import sys; sys.path.insert(0, 'c:/Users/Pavillon/Desktop/nexquant_v2/nexquant')
import os, tempfile, numpy as np, pandas as pd
os.environ['BACKTEST_MODE'] = 'true'
os.environ['BROKER_TYPE'] = 'mt5'
os.environ['MT5_LOGIN'] = '1'
os.environ['MT5_PASSWORD'] = 'x'
os.environ['MT5_SERVER'] = 'x'
DB_TMP = tempfile.mktemp(suffix='_nexquant_v3.db')
os.environ['DB_PATH'] = DB_TMP

errors = []

# Test 1 : Config V3
try:
    from superbot.config import CYCLE_TIME, DAILY_TARGET_EUR, MT5_CRYPTO_ENABLED, DB_PATH
    assert CYCLE_TIME == 15, f'CYCLE_TIME={CYCLE_TIME}'
    assert DAILY_TARGET_EUR == 200.0
    assert MT5_CRYPTO_ENABLED == True
    print(f'[1/9] Config V3            ✅ | CYCLE_TIME={CYCLE_TIME}s | DAILY_TARGET={DAILY_TARGET_EUR}€')
except Exception as e:
    errors.append(f'Config: {e}'); print(f'[1/9] Config V3            ❌ {e}')

# Test 2 : DB SQLite
try:
    from superbot.db.database import NexQuantDB
    db = NexQuantDB(DB_TMP)
    db.insert_trade({'symbol': 'EURUSD', 'side': 'LONG', 'pnl': 50.0, 'opened_at': '2026-07-30T10:00:00Z'})
    db.insert_trade({'symbol': 'BTCUSD', 'side': 'LONG', 'pnl': -20.0, 'opened_at': '2026-07-30T11:00:00Z'})
    stats = db.get_performance_stats(1)
    assert stats['total_trades'] == 2
    sid = db.start_session('LONDON', 10000.0, 200.0)
    db.close_session(sid, {'balance_end': 10150.0, 'pnl_total': 150})
    print(f'[2/9] DB SQLite            ✅ | trades={stats["total_trades"]} | pnl={stats["total_pnl"]}')
except Exception as e:
    errors.append(f'DB: {e}'); print(f'[2/9] DB SQLite            ❌ {e}')

# Test 3 : SessionManager
try:
    from superbot.brain.session_manager import SessionManager
    sm = SessionManager(daily_target_eur=200.0)
    sm.register_trade(50.0)
    sm.register_trade(-20.0)
    progress = sm.get_daily_progress()
    assert progress['achieved_eur'] == 30.0
    t200 = sm._compute_daily_target(200.0)
    t1000 = sm._compute_daily_target(1000.0)
    t5000 = sm._compute_daily_target(5000.0)
    assert t200 == 50.0 and t1000 == 200.0 and t5000 == 250.0
    print(f'[3/9] SessionManager       ✅ | session={sm.get_current_session()["name"]} | PnL={progress["achieved_eur"]}€')
except Exception as e:
    errors.append(f'SessionManager: {e}'); print(f'[3/9] SessionManager       ❌ {e}')

# Test 4 : KnowledgeFeeder
try:
    from superbot.brain.knowledge_feeder import KnowledgeFeeder
    kf = KnowledgeFeeder(db=db)
    sentiment = kf.get_current_sentiment()
    assert 'fear_greed_index' in sentiment
    # Test sentiment basique
    score = kf._compute_quick_sentiment("Bitcoin rally surge bullish breakout record high")
    assert score > 0
    score2 = kf._compute_quick_sentiment("crash bear dump fear uncertainty sell off")
    assert score2 < 0
    print(f'[4/9] KnowledgeFeeder      ✅ | sentiment={sentiment["overall_sentiment"]} | bull_score={score:.2f} | bear_score={score2:.2f}')
except Exception as e:
    errors.append(f'KnowledgeFeeder: {e}'); print(f'[4/9] KnowledgeFeeder      ❌ {e}')

# Test 5 : StrategyEngine
try:
    from superbot.brain.strategy_engine import StrategyEngine
    se = StrategyEngine(db=db, session_manager=sm)
    strat_bull, conf_bull = se.select_best_strategy('trending_bull', 'LONDON', 'forex', 'EURUSD', adx_value=30)
    strat_range, conf_range = se.select_best_strategy('ranging', 'ASIA', 'forex', 'USDJPY', adx_value=14)
    strat_crypto, conf_crypto = se.select_best_strategy('breakout', 'OVERLAP', 'crypto', 'BTCUSD', adx_value=22)
    se.record_trade_result('TREND_FOLLOW_EMA', 'EURUSD', 50.0, 2.5)
    se.record_trade_result('REVERSAL_RSI', 'USDJPY', -15.0, 1.0)
    lb = se.get_strategy_leaderboard()
    print(f'[5/9] StrategyEngine       ✅ | bull={strat_bull} | range={strat_range} | crypto={strat_crypto}')
except Exception as e:
    errors.append(f'StrategyEngine: {e}'); print(f'[5/9] StrategyEngine       ❌ {e}')

# Test 6 : PerformanceLearner
try:
    from superbot.brain.performance_learner import PerformanceLearner
    pl = PerformanceLearner(db=db, session_manager=sm, strategy_engine=se)
    adj = pl.pre_session_analysis()
    mid = pl.mid_session_check(150.0, 200.0, 10000.0)
    # Test trade fermé
    result = pl.on_trade_closed({'symbol': 'EURUSD', 'pnl': -10.0, 'strategy_name': 'TREND_FOLLOW_EMA', 'rr_ratio': 1.0})
    result2 = pl.on_trade_closed({'symbol': 'EURUSD', 'pnl': -15.0, 'strategy_name': 'TREND_FOLLOW_EMA', 'rr_ratio': 0.8})
    result3 = pl.on_trade_closed({'symbol': 'EURUSD', 'pnl': -12.0, 'strategy_name': 'TREND_FOLLOW_EMA', 'rr_ratio': 0.9})
    assert pl.is_symbol_blocked('EURUSD'), "EURUSD devrait être bloqué après 3 pertes"
    params = pl.get_current_params()
    print(f'[6/9] PerformanceLearner   ✅ | EURUSD bloqué={pl.is_symbol_blocked("EURUSD")} | params={params}')
except Exception as e:
    errors.append(f'PerformanceLearner: {e}'); print(f'[6/9] PerformanceLearner   ❌ {e}')

# Test 7 : MarketRegimeDetector
try:
    from superbot.brain.regime_detector import MarketRegimeDetector
    rd = MarketRegimeDetector(db=db)
    n = 100
    # Scénario trending_bull : ADX élevé + EMA alignées haussier
    df_bull = pd.DataFrame({
        'close': np.linspace(1.07, 1.10, n),
        'high': np.linspace(1.08, 1.11, n),
        'low': np.linspace(1.06, 1.09, n),
        'volume': np.random.uniform(1000, 3000, n),
        'adx': np.full(n, 32.0),
        'rsi': np.full(n, 62.0),
        'ema_fast': np.linspace(1.07, 1.10, n),
        'ema_slow': np.linspace(1.065, 1.095, n),
        'ema_trend': np.linspace(1.06, 1.09, n),
        'atr': np.full(n, 0.0010),
        'bb_upper': np.full(n, 1.105),
        'bb_lower': np.full(n, 1.075),
        'supertrend_direction': np.full(n, 1.0),
        'macd_histogram': np.full(n, 0.0008),
        'vwap': np.linspace(1.07, 1.10, n),
    })
    regime_bull = rd.detect(df_bull, 'EURUSD', 'forex', store_in_db=False)
    # Scénario ranging : ADX faible
    df_range = df_bull.copy()
    df_range['adx'] = 14.0
    df_range['ema_fast'] = 1.085
    df_range['ema_slow'] = 1.083
    df_range['ema_trend'] = 1.082
    regime_range = rd.detect(df_range, 'USDJPY', 'forex', store_in_db=False)
    assert regime_bull.regime in ('trending_bull', 'breakout'), f"Expected trending, got {regime_bull.regime}"
    mult = rd.get_risk_multiplier(regime_bull.regime)
    strats = rd.get_strategy_recommendation(regime_bull.regime, 'forex')
    print(f'[7/9] RegimeDetector       ✅ | bull={regime_bull.regime}({regime_bull.confidence:.2f}) | range={regime_range.regime}({regime_range.confidence:.2f}) | risk_mult={mult}')
except Exception as e:
    errors.append(f'RegimeDetector: {e}'); print(f'[7/9] RegimeDetector       ❌ {e}')

# Test 8 : cycle_runner V3
try:
    from superbot.components.cycle_runner import _DEFAULT_CYCLE_TIME, _DEFAULT_SYMBOL_TIMEOUT, _DEFAULT_MAX_PARALLEL
    assert _DEFAULT_CYCLE_TIME == 15
    assert _DEFAULT_SYMBOL_TIMEOUT >= 5
    assert _DEFAULT_MAX_PARALLEL >= 1
    print(f'[8/9] CycleRunner V3       ✅ | CYCLE={_DEFAULT_CYCLE_TIME}s | TIMEOUT={_DEFAULT_SYMBOL_TIMEOUT}s | PARALLEL={_DEFAULT_MAX_PARALLEL}')
except Exception as e:
    errors.append(f'CycleRunner: {e}'); print(f'[8/9] CycleRunner V3       ❌ {e}')

# Test 9 : MT5 asset detection
try:
    from superbot.broker.mt5_client import _detect_asset_class_mt5
    assert _detect_asset_class_mt5('BTCUSD') == 'crypto'
    assert _detect_asset_class_mt5('EURUSD') == 'forex'
    assert _detect_asset_class_mt5('XAUUSD') == 'commodity'
    assert _detect_asset_class_mt5('USDJPY') == 'forex_jpy'
    print(f'[9/9] MT5 Crypto/Forex     ✅ | BTC=crypto, EUR=forex, XAU=commodity, JPY=forex_jpy')
except Exception as e:
    errors.append(f'MT5: {e}'); print(f'[9/9] MT5 Crypto/Forex     ❌ {e}')

# Cleanup
try:
    db.close()
    os.unlink(DB_TMP)
except Exception:
    pass

print()
print('=' * 60)
if not errors:
    print('✅ VALIDATION COMPLETE V3 : 9/9 PHASES PASS')
else:
    print(f'⚠️  VALIDATION PARTIELLE : {9 - len(errors)}/9 pass | Erreurs: {errors}')
print('=' * 60)
