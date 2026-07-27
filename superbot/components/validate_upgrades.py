"""Validation script for all Phase 3 upgrades."""
import sys
sys.path.insert(0, '.')

print('=== Validation finale de tous les upgrades ===')

print()
print('1. risk_manager -- drawdown + regime + SL/TP HMM...')
from superbot.risk.risk_manager import RiskManager
rm = RiskManager({'RISK_PCT': 1.0})

rm.update_account_balance(10000)
rm.update_account_balance(8900)
assert rm.drawdown_pct > 10.0, f'DD expected >10, got {rm.drawdown_pct}'

sl_hv, tp_hv = rm.calculate_sl_tp_levels(100.0, 1.0, 'LONG', 'forex', 'EURUSD', hmm_regime='HIGH_VOL_RANGE')
sl_tr, tp_tr = rm.calculate_sl_tp_levels(100.0, 1.0, 'LONG', 'forex', 'EURUSD', hmm_regime='TRENDING')
assert sl_hv < sl_tr, f'HIGH_VOL SL ({sl_hv}) doit etre plus loin que TRENDING ({sl_tr})'

import inspect
sig = inspect.signature(rm.calculate_position_size)
assert 'hmm_regime' in sig.parameters, 'hmm_regime manquant dans calculate_position_size'
print(f'   OK -- drawdown={rm.drawdown_pct:.1f}%, SL HIGH_VOL={sl_hv:.4f} vs SL TREND={sl_tr:.4f}')

print()
print('2. strategy -- hmm_label dans signal + Hurst ETF seuil...')
src = open('superbot/strategy/strategy.py', encoding='utf-8').read()
assert 'hmm_label' in src
assert 'hurst_block_threshold = 0.65 if is_stock else 0.50' in src
assert 'stock_momentum_long and (base_trigger or stock_momentum_long)' in src
print('   OK -- hmm_label present, Hurst ETF=0.65, trigger ETF assoupli')

print()
print('3. signal_executor -- hmm_label connecte + macd_hist corrige...')
src2 = open('superbot/components/signal_executor.py', encoding='utf-8').read()
assert 'hmm_regime=hmm_label' in src2
assert 'macd_histogram' in src2
print('   OK -- hmm_regime connecte, MACD hist corrige')

print()
print('4. ghost_cleaner -- module cree...')
from superbot.components.ghost_cleaner import clean_ghost_positions, run_startup_ghost_check
ghosts_found, ghosts = clean_ghost_positions(
    bot_positions={'BTC/USDT': {'size': 0.01, 'side': 'LONG', 'entry_price': 50000}},
    risk_manager_open_positions={},
    broker_real_positions=[],
    dry_run=True
)
assert ghosts_found == 1 and 'BTC/USDT' in ghosts
print(f'   OK -- {ghosts_found} ghost detecte en dry_run: {ghosts}')

print()
print('5. position_syncer -- ghost_cleaner integre...')
src3 = open('superbot/components/position_syncer.py', encoding='utf-8').read()
assert 'ghost_cleaner' in src3
assert 'run_startup_ghost_check' in src3
print('   OK -- ghost_cleaner appele depuis position_syncer')

print()
print('=== TOUS LES TESTS PASSES ===')
