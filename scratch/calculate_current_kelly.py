import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from superbot.risk.risk_manager import RiskManager

def run():
    # Load config mock
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
        'MIN_POSITION_SIZE': 1.0,
        'MAX_POSITION_SIZE': 10000000.0
    }
    rm = RiskManager(config)
    rm.load_trade_history_from_disk()
    
    print(f"Total trades loaded: {len(rm.trade_history)}")
    
    # Run _calculate_kelly_fraction
    kelly = rm._calculate_kelly_fraction()
    print(f"Calculated Kelly fraction: {kelly}")
    
    # Detailed analysis
    trades_with_pnl = [t for t in rm.trade_history if t.get('pnl') is not None and t.get('status') == 'closed']
    print(f"Closed trades with PnL: {len(trades_with_pnl)}")
    
    winning_trades = [t for t in trades_with_pnl if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades_with_pnl if t.get('pnl', 0) <= 0]
    
    print(f"Winning trades: {len(winning_trades)}")
    print(f"Losing trades: {len(losing_trades)}")
    
    if trades_with_pnl:
        win_rate = len(winning_trades) / len(trades_with_pnl)
        print(f"Win Rate: {win_rate:.2%}")
        
    if winning_trades:
        import numpy as np
        avg_win = np.mean([t['pnl'] for t in winning_trades])
        print(f"Average Win: {avg_win:.4f}")
    else:
        avg_win = 0
        
    if losing_trades:
        import numpy as np
        avg_loss = abs(np.mean([t['pnl'] for t in losing_trades]))
        print(f"Average Loss: {avg_loss:.4f}")
    else:
        avg_loss = 0
        
    if avg_loss > 0:
        win_loss_ratio = avg_win / avg_loss
        print(f"Win/Loss Ratio: {win_loss_ratio:.4f}")
        
if __name__ == "__main__":
    run()
