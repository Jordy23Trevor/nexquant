import os
import sys
import logging

# Ensure the nexquant folder is in PYTHONPATH
sys.path.insert(0, r"c:\Users\Pavillon\Desktop\nexquant_v2\nexquant")

# Configure basic logging to check output
logging.basicConfig(level=logging.WARNING)

# Load dotenv to get other settings (like API keys)
from dotenv import load_dotenv
load_dotenv()

# We expect BROKER_TYPE to be set in os.environ
broker_type = os.environ.get("BROKER_TYPE")
print(f"\n============================================")
print(f"TESTING BROKER: {broker_type}")
print(f"============================================")

try:
    # Now import bot components
    from superbot.broker import create_broker
    
    # 1. Initialize broker
    print("[1] Initializing broker client...")
    broker = create_broker(broker_type)
    print(f" -> Asset Type: {broker.get_asset_type()}")
    
    # 2. Get Balance
    print("[2] Getting account balance...")
    balance = broker.get_balance()
    print(f" -> Balance: {balance}")
    
    # 3. Get Account Summary
    print("[3] Getting account summary...")
    summary = broker.get_account_summary()
    print(f" -> Summary: {summary}")
    
    # 4. Fetch candles for default instrument (positionally to avoid argument name conflicts)
    default_instruments = broker.get_default_instruments()
    if default_instruments:
        symbol = default_instruments[0]
        print(f"[4] Fetching candles for {symbol}...")
        df = broker.fetch_candles(symbol, "1h", 5)
        print(f" -> Fetched DataFrame shape: {df.shape}")
        if not df.empty:
            print(f" -> Last Close Price: {df['close'].iloc[-1]}")
    else:
        print("[4] No default instruments found.")
        
    print(f"SUCCESS: Broker {broker_type} is working properly!")
    sys.exit(0)
    
except Exception as e:
    print(f"ERROR testing broker {broker_type}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
