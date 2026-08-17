"""Tests du câblage TSMOM dans la boucle du bot.

Vérifie _tsmom_cycle() sans instancier le SuperBot complet (coûteux et avec
effets de bord disque) : on utilise SuperBot.__new__ + un broker factice.
"""

import threading

import numpy as np
import pandas as pd

from superbot.orchestrator import SuperBot


class FakeBroker:
    def __init__(self, closes):
        self._closes = np.asarray(closes, dtype=float)
        self.orders = []

    def fetch_candles(self, symbol, timeframe, limit=500):
        n = len(self._closes)
        idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
        return pd.DataFrame({
            "open": self._closes,
            "high": self._closes * 1.01,
            "low": self._closes * 0.99,
            "close": self._closes,
            "volume": np.full(n, 1e6),
        }, index=idx)

    def get_account_summary(self):
        return {"equity": 100_000.0, "balance": 100_000.0}

    def get_balance(self):
        return 100_000.0

    def get_current_price(self, symbol):
        return float(self._closes[-1])

    def place_order(self, symbol, side, amount, sl=0.0, tp=0.0,
                    reduce_only=False, comment=""):
        self.orders.append((side, amount))
        return True


def _make_bot(place_orders: bool) -> SuperBot:
    bot = SuperBot.__new__(SuperBot)
    bot.active_broker_type = "binance"
    bot.TSMOM_BROKER_SYMBOLS = {"binance": {"BTCUSD": "BTC/USDT"}}
    bot.TSMOM_UNIVERSE = {"BTCUSD": {"long_only": False, "cost": 0.001, "periods_per_year": 365}}
    bot.TSMOM_PLACE_ORDERS = place_orders
    bot.positions = {}
    bot.market_data = {}
    bot._lock = threading.RLock()
    bot._tsmom_last_month = None
    bot._tsmom_last_log_day = None
    bot.broker = FakeBroker(np.linspace(100.0, 200.0, 400))  # tendance haussière
    return bot


def test_tsmom_cycle_dry_run_places_no_order():
    bot = _make_bot(place_orders=False)
    bot._tsmom_cycle()
    assert bot.broker.orders == []
    assert bot._tsmom_last_month is not None  # le mois a bien été marqué
    assert "BTC/USDT" in bot.market_data  # le dashboard peut afficher le graphique


def test_tsmom_cycle_places_order_when_enabled():
    bot = _make_bot(place_orders=True)
    bot._tsmom_cycle()
    assert len(bot.broker.orders) == 1
    side, amount = bot.broker.orders[0]
    assert side == "buy"          # tendance haussière → LONG
    assert amount > 0


def test_tsmom_cycle_no_rebalance_same_month():
    bot = _make_bot(place_orders=True)
    bot._tsmom_cycle()
    first_orders = list(bot.broker.orders)
    bot._tsmom_cycle()  # même mois calendaire → pas de nouvel ordre
    assert bot.broker.orders == first_orders


def test_tsmom_skips_symbol_below_broker_min_order_size():
    """Un compte trop petit pour le minimum broker ne doit produire aucun ordre."""
    bot = _make_bot(place_orders=True)
    # La cible (fraction de 100k) sera toujours sous ce minimum énorme.
    bot.broker.get_min_order_size = lambda symbol: 1e9
    bot._tsmom_cycle()
    assert bot.broker.orders == []
    assert bot._tsmom_last_month is not None  # le cycle a bien été exécuté
