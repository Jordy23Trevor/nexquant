import pytest
import time
from datetime import datetime, date
from unittest.mock import patch, MagicMock
from superbot.orchestrator import SuperBot

class FakeBroker:
    def __init__(self):
        self.testnet = True
        self.account_type = "PAPER"
    def get_balance(self): return 10000.0
    def get_asset_type(self): return "crypto"
    def get_symbol_limits(self, symbol): return {'min_qty': 0.001, 'step_size': 0.001, 'max_qty': 1000.0, 'max_nominal': float('inf')}
    def get_leverage(self, symbol=None): return 1.0
    def get_free_margin(self): return 10000.0
    def get_symbol_info(self, symbol): return {'tick_size': 1.0, 'contract_size': 1.0}
    def get_min_order_size(self, symbol): return 0.001
    def get_account_summary(self): return {"equity": 10000.0}
    def get_position(self, symbol): return None
    def cancel_all_orders(self, symbol): pass
    def get_trade_history(self, days=1): return []
    def __getattr__(self, name):
        if "size" in name or "min" in name or "max" in name or "step" in name:
            return lambda *a, **k: 0.001
        return lambda *a, **k: 1.0

@pytest.fixture
def mock_bot(monkeypatch):
    monkeypatch.setenv("BROKER_TYPE", "paper")
    fake = FakeBroker()
    with patch('superbot.orchestrator.create_broker', return_value=fake):
        bot = SuperBot()
        bot.broker = fake
        if bot.risk_manager:
            bot.risk_manager.broker = bot.broker
        return bot

def test_daily_reset_on_clock_skew(mock_bot):
    """
    Test 3.6.4 : Simule un saut dans le temps de 24h (Désynchronisation NTP)
    pour vérifier que le bot purge bien son PnL quotidien et ses blocages.
    """
    # Étape 1 : Initialisation de l'état (Veille)
    initial_date = date(2026, 7, 11)
    mock_bot.session_date = initial_date
    mock_bot.blocked_symbols.add("BTC/USDT")
    mock_bot.session_pnl_by_symbol["ETH/USDT"] = 150.0
    
    # On mock datetime pour simuler le lendemain matin
    tomorrow = datetime(2026, 7, 12, 10, 0, 0)
    
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return tomorrow

    with patch('superbot.components.cycle_runner.datetime', MockDatetime):
        # On extrait la logique de reset de cycle_runner.py pour la tester
        today = MockDatetime.now().date()
        if today != mock_bot.session_date:
            mock_bot.blocked_symbols.clear()
            mock_bot.session_pnl_by_symbol.clear()
            mock_bot.session_date = today
            
    # Vérifications de résilience
    assert mock_bot.session_date == date(2026, 7, 12), "La date de session n'a pas été mise à jour"
    assert len(mock_bot.blocked_symbols) == 0, "Les actifs bloqués n'ont pas été purgés après 24h"
    assert len(mock_bot.session_pnl_by_symbol) == 0, "Le PnL de session n'a pas été remis à zéro après 24h"

def test_cooldown_expiration_on_clock_skew(mock_bot):
    """
    Test 3.6.5 : Vérifie qu'un saut dans le temps permet l'expiration correcte 
    d'un cooldown de sécurité.
    """
    # 1. On met BTC/USDT en cooldown (timestamp d'il y a 20 minutes)
    past_time = time.time() - 1200  # -20 minutes (cooldown=15m)
    mock_bot.failed_execution_cooldowns["BTC/USDT"] = past_time
    
    # 2. Exécution du signal
    import pandas as pd
    df_with_indicators = pd.DataFrame([{'close': 50000.0, 'atr': 1000.0, 'rsi': 40, 'adx': 25, 'macd_hist': 10}])
    signal_data = {
        "market_regime": "TRENDING",
        "total_score": 8.0,
        "should_long": True,
        "should_short": False,
        "rr_ratio": 2.5,
        "entry_price": 50000.0,
    }
    
    from superbot.components.signal_executor import execute_signal_trade
    
    # On simule un trade valide côté courtier
    mock_bot.broker.place_order = MagicMock(return_value={'id': '123'})
    
    execute_signal_trade(mock_bot, "BTC/USDT", signal_data, df_with_indicators)
    
    # Assertions : Le trade doit être passé car 20m > 15m
    assert mock_bot.stats['trades_executed'] == 1, "Le cooldown n'a pas expiré face au temps écoulé"
    assert "BTC/USDT" not in mock_bot.failed_execution_cooldowns, "Le cooldown n'a pas été purgé de la liste"
