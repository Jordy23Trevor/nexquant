import sys
sys.path.insert(0, '.')
from superbot.risk.risk_manager import RiskManager

# Mock config
config = {
    'RISK_PCT': 1.0,
    'MAX_DAILY_LOSS_PCT': 2.0,
    'MAX_MONTHLY_LOSS_PCT': 5.0,
    'MAX_OPEN_POSITIONS': 2,
    'KELLY_FRACTION': 0.05,
    'MIN_TRADES_FOR_KELLY': 5,  # lower for test
    'SL_ATR_MULT': 1.5,
    'TP_ATR_MULT': 3.0,
    'TRAIL_ATR_MULT': 1.0,
    'BE_ATR_MULT': 1.0,
    'BE_DYN_RR': True,
    'BE_DYN_RR_RATIO': 1.0,
    'MIN_POSITION_SIZE': 0.001,
    'MAX_POSITION_SIZE': 1000000.0,
    'COOLDOWN_SECONDS': 3600,
}

rm = RiskManager(config)

# Add some fake trade history
import pandas as pd
from datetime import datetime, timedelta

def add_trade(pnl):
    rm.trade_history.append({
        'symbol': 'TEST',
        'side': 'buy',
        'pnl': pnl,
        'timestamp': (datetime.now() - timedelta(minutes=10)).isoformat(),
        'status': 'closed'
    })

print("Testing Kelly fraction calculation...")
print("="*50)

# Case 1: balanced wins/losses
rm.trade_history.clear()
for p in [10, -5, 12, -3, 8]:
    add_trade(p)

kelly = rm._calculate_kelly_fraction()
print(f'Case 1 - Balanced wins/losses: {kelly}')

# Case 2: all wins (should return None because win_loss_ratio infinite -> but we return None in our code)
rm.trade_history.clear()
for p in [10, 12, 8, 15, 7]:
    add_trade(p)
kelly = rm._calculate_kelly_fraction()
print(f'Case 2 - All wins: {kelly}')  # expect None

# Case 3: all losses
rm.trade_history.clear()
for p in [-10, -5, -8, -12, -7]:
    add_trade(p)
kelly = rm._calculate_kelly_fraction()
print(f'Case 3 - All losses: {kelly}')  # expect None

# Case 4: with outlier large win
rm.trade_history.clear()
# small wins and losses but one huge win
for p in [2, -1, 2, -1, 100]:  # last is outlier
    add_trade(p)
kelly = rm._calculate_kelly_fraction()
print(f'Case 4 - With outlier win: {kelly}')

# Also compute mean based to see difference
wins = [t['pnl'] for t in rm.trade_history if t['pnl'] > 0]
losses = [abs(t['pnl']) for t in rm.trade_history if t['pnl'] < 0]
print(f'\nWins: {wins}')
print(f'Losses: {losses}')
if wins and losses:
    import numpy as np
    mean_win = np.mean(wins)
    median_win = np.median(wins)
    mean_loss = np.mean(losses)
    median_loss = np.median(losses)
    print(f'Mean win: {mean_win}, Median win: {median_win}')
    print(f'Mean loss: {mean_loss}, Median loss: {median_loss}')
    win_loss_ratio_mean = mean_win / mean_loss if mean_loss != 0 else 0
    win_loss_ratio_median = median_win / median_loss if median_loss != 0 else 0
    print(f'Win/Loss ratio mean: {win_loss_ratio_mean}, median: {win_loss_ratio_median}')
    win_rate = len(wins) / len(rm.trade_history)
    kelly_mean = (win_loss_ratio_mean * win_rate - (1 - win_rate)) / win_loss_ratio_mean if win_loss_ratio_mean != 0 else 0
    kelly_median = (win_loss_ratio_median * win_rate - (1 - win_rate)) / win_loss_ratio_median if win_loss_ratio_median != 0 else 0
    print(f'Kelly (mean) raw: {kelly_mean}')
    print(f'Kelly (median) raw: {kelly_median}')
    # apply conservative half Kelly and cap 0.5
    kelly_mean = max(0.0, min(kelly_mean * 0.5, 0.5))
    kelly_median = max(0.0, min(kelly_median * 0.5, 0.5))
    print(f'Kelly (mean) final: {kelly_mean}')
    print(f'Kelly (median) final: {kelly_median}')

print("\n" + "="*50)
print("Test completed.")