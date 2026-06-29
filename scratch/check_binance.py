import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

client = Client(api_key, api_secret, testnet=testnet)

print(f"Connecting to Binance Futures {'Testnet' if testnet else 'Production'}...")
try:
    acc = client.futures_account()
    print("\n--- Account Summary ---")
    print(f"Total Wallet Balance: {acc.get('totalWalletBalance')} USDT")
    print(f"Total Margin Balance: {acc.get('totalMarginBalance')} USDT")
    print(f"Available Balance: {acc.get('availableBalance')} USDT")
    print(f"Total Initial Margin: {acc.get('totalInitialMargin')} USDT")
    
    # Check assets
    print("\n--- Assets with Balance ---")
    for asset in acc.get('assets', []):
        wb = float(asset.get('walletBalance', 0))
        if wb != 0:
            print(f"Asset: {asset.get('asset')} | Wallet Balance: {wb} | Margin Balance: {asset.get('marginBalance')}")

    # Check positions
    print("\n--- Open Positions ---")
    positions = client.futures_position_information()
    for pos in positions:
        amt = float(pos.get('positionAmt', 0))
        if amt != 0:
            print(f"Symbol: {pos.get('symbol')} | Size: {amt} | Entry Price: {pos.get('entryPrice')} | Leverage: {pos.get('leverage')}x | Initial Margin: {pos.get('initialMargin')}")
            
    # Check BTCUSDT leverage
    for pos in positions:
        if pos.get('symbol') == 'BTCUSDT':
            print(f"\nBTCUSDT current leverage: {pos.get('leverage')}x")
            break

except Exception as e:
    print(f"Error querying Binance API: {e}")
