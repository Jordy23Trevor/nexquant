"""
Tests de concurrence pour le SuperBot (Phase 1.2 — Durcissement multi-threading).

Ces tests vérifient que les accès concurrents aux structures de données partagées
(`positions`, `market_data`, `active_orders`, `state`) ne provoquent ni corruption,
ni `RuntimeError: dictionary changed size during iteration`, ni incohérence d'état.
"""
import os
import sys
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

# Permet l'import de `superbot` depuis la racine projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class _FakeBot:
    """
    Stand-in minimal du SuperBot qui réutilise les mêmes primitives de verrouillage.
    Le but n'est pas de tester la logique de trading mais l'invariant de concurrence :
    'aucune exception + état cohérent après N accès parallèles'.
    """

    def __init__(self):
        self.positions = {}
        self.market_data = {}
        self.active_orders = {}
        # ⚠️ Mêmes verrous que dans superbot.orchestrator.SuperBot.__init__
        self._lock = threading.RLock()
        self._state_lock = threading.Lock()
        self.stats = {'errors_count': 0, 'cycles_completed': 0}
        self.blocked_symbols = set()
        self.session_pnl_by_symbol = {}
        self.shutdown_event = threading.Event()

    def safe_add_position(self, symbol, payload):
        with self._lock:
            self.positions[symbol] = payload

    def safe_update_position(self, symbol, key, value):
        with self._lock:
            if symbol in self.positions:
                self.positions[symbol][key] = value

    def safe_iter_positions(self):
        # Snapshot sous lock pour éviter "dict changed size during iteration"
        with self._lock:
            return list(self.positions.items())

    def safe_increment_stat(self, key, delta=1):
        with self._state_lock:
            self.stats[key] = self.stats.get(key, 0) + delta

    def safe_block_symbol(self, symbol):
        with self._state_lock:
            self.blocked_symbols.add(symbol)


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------

def test_lock_objects_exist():
    """Le bot doit exposer les deux verrous."""
    bot = _FakeBot()
    assert isinstance(bot._lock, type(threading.RLock()))
    assert isinstance(bot._state_lock, type(threading.Lock()))


def test_concurrent_position_writes_no_corruption():
    """
    50 workers écrivent simultanément des positions différentes.
    À la fin, le nombre de positions doit être exactement celui attendu.
    """
    bot = _FakeBot()
    n_symbols = 200
    symbols = [f"SYM{i}/USDT" for i in range(n_symbols)]

    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = [
            ex.submit(bot.safe_add_position, s, {'side': 'LONG', 'size': 0.1, 'entry': 100.0})
            for s in symbols
        ]
        for f in as_completed(futures):
            f.result()

    assert len(bot.positions) == n_symbols, (
        f"Perte de positions en écriture concurrente : {len(bot.positions)}/{n_symbols}"
    )


def test_concurrent_reads_during_writes_no_runtime_error():
    """
    10 readers itèrent en continu pendant que 10 writers mutent.
    Doit se terminer sans 'RuntimeError: dictionary changed size during iteration'.
    """
    bot = _FakeBot()
    n_symbols = 100
    for i in range(n_symbols):
        bot.safe_add_position(f"SYM{i}", {'side': 'LONG', 'size': 0.1})

    errors = []
    stop = threading.Event()

    def reader():
        try:
            while not stop.is_set():
                snap = bot.safe_iter_positions()
                _ = sum(p['size'] for _, p in snap)
        except Exception as e:
            errors.append(e)

    def writer():
        try:
            for i in range(500):
                s = f"SYM{random.randint(0, n_symbols-1)}"
                bot.safe_update_position(s, 'size', random.random())
        except Exception as e:
            errors.append(e)

    readers = [threading.Thread(target=reader) for _ in range(10)]
    writers = [threading.Thread(target=writer) for _ in range(10)]
    for t in readers + writers:
        t.start()
    time.sleep(2)
    stop.set()
    for t in readers + writers:
        t.join(timeout=5)

    assert not errors, f"Erreurs détectées sous concurrence : {errors}"


def test_stats_increment_is_atomic():
    """
    1000 incréments concurrents sur stats['trades'] doivent donner exactement 1000.
    Si _state_lock est retiré, on observe des pertes (race condition classique).
    """
    bot = _FakeBot()
    n = 1000
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda _: bot.safe_increment_stat('trades'), range(n)))
    assert bot.stats['trades'] == n, (
        f"Race sur stats : attendu {n}, obtenu {bot.stats['trades']}"
    )


def test_blocked_symbols_set_is_atomic():
    """
    Bloquer le même symbole N fois en parallèle ne doit pas lever d'exception
    et l'ensemble final doit contenir le symbole une seule fois.
    """
    bot = _FakeBot()
    n_workers = 50
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda _: bot.safe_block_symbol('BTC/USDT'), range(n_workers)))
    assert 'BTC/USDT' in bot.blocked_symbols
    assert len(bot.blocked_symbols) == 1


def test_rlock_supports_nested_acquisition():
    """
    Le _lock doit être un RLock pour permettre l'acquisition récursive
    (ex: _process_symbol appelle _update_active_position_risk qui relock les positions).
    """
    bot = _FakeBot()
    bot.positions['SYM1'] = {'side': 'LONG', 'size': 1.0}
    nested_ok = True

    def nested():
        nonlocal nested_ok
        try:
            with bot._lock:
                with bot._lock:  # 2e acquisition sur le même thread
                    bot.positions['SYM1']['size'] = 2.0
        except RuntimeError:
            nested_ok = False

    t = threading.Thread(target=nested)
    t.start()
    t.join()
    assert nested_ok, "RLock n'autorise pas l'acquisition récursive"
    assert bot.positions['SYM1']['size'] == 2.0


def test_sync_positions_with_broker_concurrent_with_writes():
    """
    Le vrai syncer doit tolérer des écritures concurrentes (thread webhook / workers)
    sans RuntimeError ni perte de cohérence : le snapshot et le swap sont sous _lock.
    """
    from types import SimpleNamespace
    from superbot.components.position_syncer import sync_positions_with_broker

    class _Broker:
        def get_position(self, symbol):
            return {"side": "LONG", "size": 0.5, "entry_price": 100.0,
                    "stop_loss": 90.0, "take_profit": 110.0}

        def get_open_positions(self):
            return [{"symbol": "BTC/USDT"}]

        def cancel_all_orders(self, symbol):
            pass

        def get_trade_history(self, days=1):
            return []

    bot = _FakeBot()
    bot.instruments = ["BTC/USDT"]
    bot.broker = _Broker()
    bot.risk_manager = SimpleNamespace(
        open_positions={"BTC/USDT": {"symbol": "BTC/USDT", "side": "LONG"}}
    )
    bot.telemetry = SimpleNamespace(enabled=False)
    bot.positions["BTC/USDT"] = {"side": "LONG", "size": 0.5, "entry_price": 100.0}

    errors = []
    stop = threading.Event()

    def syncer():
        try:
            while not stop.is_set():
                sync_positions_with_broker(bot)
        except Exception as e:
            errors.append(e)

    def writer():
        try:
            while not stop.is_set():
                with bot._lock:
                    bot.positions["BTC/USDT"] = {"side": "LONG", "size": 0.5, "entry_price": 100.0}
                bot.safe_increment_stat("writes")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=syncer) for _ in range(2)]
    threads += [threading.Thread(target=writer) for _ in range(4)]
    for t in threads:
        t.start()
    time.sleep(2)
    stop.set()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"Erreurs sous concurrence (syncer) : {errors}"


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
