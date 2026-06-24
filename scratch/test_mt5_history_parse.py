import MetaTrader5 as mt5
import datetime
import sys

if not mt5.initialize():
    print("MT5 initialization failed")
    sys.exit(1)

from_date = datetime.datetime.now() - datetime.timedelta(days=30)
to_date = datetime.datetime.now()

deals = mt5.history_deals_get(from_date, to_date)
if deals is None:
    print("No deals found")
else:
    reconstructed_trades = []
    for deal in deals:
        if deal.entry == 1 and deal.symbol:
            side = "buy" if deal.type == 1 else "sell"
            pnl = deal.profit + deal.commission + deal.swap + deal.fee
            
            trade = {
                'symbol': deal.symbol,
                'side': side,
                'exit_price': deal.price,
                'pnl': pnl,
                'size': deal.volume,
                'timestamp': datetime.datetime.fromtimestamp(deal.time, datetime.timezone.utc).isoformat(),
                'ticket': deal.ticket,
                'position_id': deal.position_id
            }
            reconstructed_trades.append(trade)
            
    print(f"Reconstructed {len(reconstructed_trades)} closed trades:")
    for t in reconstructed_trades[:10]:
        print(t)

mt5.shutdown()
