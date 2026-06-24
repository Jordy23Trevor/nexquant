import MetaTrader5 as mt5
import sys

if not mt5.initialize():
    print("MT5 initialization failed")
    sys.exit(1)

print("Connected to MT5 account:", mt5.account_info().login)

import datetime
from datetime import timezone

# Fetch history from 30 days ago to now
from_date = datetime.datetime.now() - datetime.timedelta(days=30)
to_date = datetime.datetime.now()

deals = mt5.history_deals_get(from_date, to_date)
if deals is None:
    print("Failed to get history deals, error code =", mt5.last_error())
else:
    print(f"Total deals found: {len(deals)}")
    # Print the first few deals
    for i, deal in enumerate(deals[:10]):
        print(f"Deal #{i}: Ticket={deal.ticket}, Symbol={deal.symbol}, Type={deal.type}, Entry/Exit={deal.entry}, Volume={deal.volume}, Price={deal.price}, Profit={deal.profit}")

mt5.shutdown()
