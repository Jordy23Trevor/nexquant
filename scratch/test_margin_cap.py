import sys
import os
import logging

# Configurer les chemins d'importation
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from superbot.risk.risk_manager import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("test_margin_cap")

class MockBroker:
    def __init__(self, free_margin=1000.0, leverage=5, asset_type="crypto", min_qty=0.001, step_size=0.001):
        self._free_margin = free_margin
        self._leverage = leverage
        self._asset_type = asset_type
        self._min_qty = min_qty
        self._step_size = step_size

    def get_account_summary(self):
        return {
            "balance": 10000.0,
            "equity": 10000.0,
            "free_margin": self._free_margin,
            "leverage": self._leverage,
        }

    def get_asset_type(self):
        return self._asset_type

    def get_min_order_size(self, symbol):
        return self._min_qty

    def get_step_size(self, symbol):
        return self._step_size

    def get_symbol_info(self, symbol):
        return {
            "contract_size": 1.0,
            "tick_size": 0.01,
            "tick_value": 0.01,
        }

def run_test():
    config = {
        'RISK_PCT': 1.0,
        'MAX_DAILY_LOSS_PCT': 3.0,
        'MAX_MONTHLY_LOSS_PCT': 6.0,
        'MAX_OPEN_POSITIONS': 2,
        'KELLY_FRACTION': 0.25,
        'MIN_TRADES_FOR_KELLY': 20,
    }
    rm = RiskManager(config)

    # 1. Test avec beaucoup de marge disponible
    log.info("--- TEST 1 : Beaucoup de marge disponible ---")
    broker = MockBroker(free_margin=5000.0, leverage=5)
    size, details = rm.calculate_position_size(
        account_balance=10000.0,
        entry_price=60000.0,
        stop_loss=59000.0,
        symbol="BTC/USDT",
        broker=broker
    )
    log.info(f"Taille calculée : {size} (Attendu: ~0.1 BTC)")
    log.info(f"Détails : {details}\n")
    assert size > 0, "Le calcul simple a échoué"

    # 2. Test avec marge contrainte (doit capper)
    log.info("--- TEST 2 : Marge contrainte (Doit capper) ---")
    # Marge dispo = 500 USDT, Levier = 5x -> Max nominal = 500 * 5 * 0.95 = 2375 USDT.
    # A 60000 USDT/BTC, la taille max par marge est 2375 / 60000 = 0.03958 BTC.
    # Arrondi par le bas au step_size (0.001) -> 0.039 BTC.
    broker = MockBroker(free_margin=500.0, leverage=5)
    size, details = rm.calculate_position_size(
        account_balance=10000.0,
        entry_price=60000.0,
        stop_loss=59000.0,
        symbol="BTC/USDT",
        broker=broker
    )
    log.info(f"Taille calculée : {size} (Attendu: ~0.039 BTC)")
    log.info(f"Détails : {details}\n")
    assert size == 0.039, f"Le capping a échoué : obtenu {size} au lieu de 0.039"

    # 3. Test avec marge extrêmement basse (doit rejeter)
    log.info("--- TEST 3 : Marge insuffisante (Doit rejeter, size = 0.0) ---")
    # Marge dispo = 10 USDT, Levier = 5x -> Max nominal = 10 * 5 * 0.95 = 47.5 USDT.
    # Max size = 47.5 / 60000 = 0.00079 BTC.
    # C'est inférieur à min_qty (0.001) -> Doit être rejeté (size = 0.0).
    broker = MockBroker(free_margin=10.0, leverage=5)
    size, details = rm.calculate_position_size(
        account_balance=10000.0,
        entry_price=60000.0,
        stop_loss=59000.0,
        symbol="BTC/USDT",
        broker=broker
    )
    log.info(f"Taille calculée : {size} (Attendu: 0.0)")
    log.info(f"Détails : {details}\n")
    assert size == 0.0, f"Le rejet a échoué : obtenu {size} au lieu de 0.0"
    assert "error" in details, "Aucune erreur signalée dans les détails"

    # 4. Test avec action (Stock) - buying power direct
    log.info("--- TEST 4 : Asset Type Stock (buying power direct) ---")
    # Marge dispo = 1000 USD (buying_power), Levier = 1 (stock).
    # Max nominal = 1000 * 0.95 = 950 USD.
    # Prix entrée = 100 USD -> Max size = 9.5 shares.
    # Arrondi au step_size (1.0) -> 9.0 shares.
    broker = MockBroker(free_margin=1000.0, leverage=1, asset_type="stock", min_qty=1.0, step_size=1.0)
    size, details = rm.calculate_position_size(
        account_balance=10000.0,
        entry_price=100.0,
        stop_loss=90.0,
        symbol="AAPL",
        broker=broker
    )
    log.info(f"Taille calculée : {size} (Attendu: 9.0)")
    log.info(f"Détails : {details}\n")
    assert size == 9.0, f"Le capping pour actions a échoué : obtenu {size} au lieu de 9.0"

    log.info("🎉 TOUS LES TESTS DE MARGE ONT RÉUSSI AVEC SUCCÈS !")

if __name__ == "__main__":
    run_test()
