import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from superbot.risk.risk_manager import RiskManager

logging.basicConfig(level=logging.INFO)

class MockBroker:
    def __init__(self, contract_size, tick_size, tick_value, min_size=1.0, step_size=0.01, asset_type="forex"):
        self.contract_size = contract_size
        self.tick_size = tick_size
        self.tick_value = tick_value
        self.min_size = min_size
        self.step_size = step_size
        self.asset_type = asset_type
        
    def get_symbol_info(self, symbol):
        return {
            "contract_size": self.contract_size,
            "tick_size": self.tick_size,
            "tick_value": self.tick_value
        }
        
    def get_min_order_size(self, symbol):
        return self.min_size
        
    def get_step_size(self, symbol):
        return self.step_size

    def get_asset_type(self):
        return self.asset_type
        
    def get_account_summary(self):
        return {
            "free_margin": 10000.0,
            "leverage": 30 if self.asset_type == "forex" else (5 if self.asset_type == "crypto" else 1),
            "balance": 10000.0
        }

def test_risk_manager():
    # Initialize RiskManager with config dictionary
    config = {
        'RISK_PCT': 1.0,
        'MAX_DAILY_LOSS_PCT': 5.0,
        'MAX_MONTHLY_LOSS_PCT': 15.0,
        'MAX_OPEN_POSITIONS': 5,
        'KELLY_FRACTION': 0.05,
        'MIN_TRADES_FOR_KELLY': 20,
        'SL_ATR_MULT': 1.5,
        'TP_ATR_MULT': 3.0,
        'TRAIL_ATR_MULT': 2.0,
        'BE_ATR_MULT': 1.0,
        'MIN_POSITION_SIZE': 0.0001,
        'MAX_POSITION_SIZE': 10000000.0
    }
    rm = RiskManager(config)
    
    # Mock account balance
    balance = 10000.0  # $10,000
    
    # Case 1: EURUSD on MT5 (Account in USD)
    # Price difference: 1.08500 to 1.08000 = 50 pips / 0.00500 risk
    mock_eurusd = MockBroker(contract_size=100000.0, tick_size=0.00001, tick_value=0.87, min_size=1000.0, step_size=1000.0, asset_type="forex")
    size, details = rm.calculate_position_size(
        account_balance=balance,
        entry_price=1.08500,
        stop_loss=1.08000,
        symbol="EURUSD",
        broker=mock_eurusd
    )
    print(f"\n--- EURUSD (MT5 Mock) ---")
    print(f"Calculated position size: {size} units")
    print(f"Actual risk percentage: {details['actual_risk_pct']:.4f}%")
    print(f"Risk per unit in account currency: {details['risk_per_unit']:.6f}")
    
    # Case 2: USDJPY on MT5 (Account in USD)
    # Price difference: 150.00 to 149.00 = 1.00 risk
    mock_usdjpy = MockBroker(contract_size=100000.0, tick_size=0.001, tick_value=0.58, min_size=1000.0, step_size=1000.0, asset_type="forex")
    size, details = rm.calculate_position_size(
        account_balance=balance,
        entry_price=150.00,
        stop_loss=149.00,
        symbol="USDJPY",
        broker=mock_usdjpy
    )
    print(f"\n--- USDJPY (MT5 Mock) ---")
    print(f"Calculated position size: {size} units")
    print(f"Actual risk percentage: {details['actual_risk_pct']:.4f}%")
    print(f"Risk per unit in account currency: {details['risk_per_unit']:.6f}")
    
    # Case 3: XAUUSD on MT5 (Account in USD)
    # Price difference: 2350.00 to 2340.00 = 10.00 risk
    mock_xauusd = MockBroker(contract_size=100.0, tick_size=0.01, tick_value=0.87, min_size=1.0, step_size=1.0, asset_type="forex")
    size, details = rm.calculate_position_size(
        account_balance=balance,
        entry_price=2350.00,
        stop_loss=2340.00,
        symbol="XAUUSD",
        broker=mock_xauusd
    )
    print(f"\n--- XAUUSD (MT5 Mock) ---")
    print(f"Calculated position size: {size} units (ounces)")
    print(f"Actual risk percentage: {details['actual_risk_pct']:.4f}%")
    print(f"Risk per unit in account currency: {details['risk_per_unit']:.6f}")

    # Case 4: BTCUSDT on Binance (Account in USDT)
    # Price difference: 60000.0 to 59000.0 = 1000.00 risk
    mock_btcusdt = MockBroker(contract_size=1.0, tick_size=0.1, tick_value=0.1, min_size=0.001, step_size=0.001, asset_type="crypto")
    size, details = rm.calculate_position_size(
        account_balance=balance,
        entry_price=60000.0,
        stop_loss=59000.0,
        symbol="BTCUSDT",
        broker=mock_btcusdt
    )
    print(f"\n--- BTCUSDT (Binance Mock) ---")
    print(f"Calculated position size: {size} units (BTC)")
    print(f"Actual risk percentage: {details['actual_risk_pct']:.4f}%")
    print(f"Risk per unit in account currency: {details['risk_per_unit']:.6f}")

    # Case 5: SPY on Alpaca (Account in USD)
    # Price difference: 500.00 to 495.00 = 5.00 risk
    mock_spy = MockBroker(contract_size=1.0, tick_size=0.01, tick_value=0.01, min_size=0.000001, step_size=0.000001, asset_type="stock")
    size, details = rm.calculate_position_size(
        account_balance=balance,
        entry_price=500.00,
        stop_loss=495.00,
        symbol="SPY",
        broker=mock_spy
    )
    print(f"\n--- SPY (Alpaca Mock) ---")
    print(f"Calculated position size: {size} units (shares)")
    print(f"Actual risk percentage: {details['actual_risk_pct']:.4f}%")
    print(f"Risk per unit in account currency: {details['risk_per_unit']:.6f}")

if __name__ == "__main__":
    test_risk_manager()
