import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import math
from typing import Dict, Any, Tuple, Optional
log = logging.getLogger(__name__)

def _can_take_new_trade(rm, account_balance: float, symbol: str = "") -> bool:
    """
    Vérifie si on peut prendre un nouveau trade basé sur les limites de risque.

    Args:
        account_balance: Solde actuel du compte
        symbol: Symbole de l'instrument

    Returns:
        True si on peut prendre un nouveau trade, False sinon
    """
    # Vérifier si on a déjà une position sur ce symbole
    if symbol and symbol in rm.open_positions:
        log.info(f"Position déjà ouverte pour {symbol}, rejet du nouveau trade.")
        return False

    # Vérifier les pertes consécutives sur ce symbole
    if symbol and rm.consecutive_losses.get(symbol, 0) >= 3:
        log.info(f"Symbole {symbol} bloqué (3 pertes consécutives atteintes).")
        return False

    # ✅ BUG FIX #5 — Cooldown : vérifier le délai depuis la dernière clôture sur ce symbole
    if symbol and symbol in rm.last_trade_close_time:
        elapsed = (datetime.now() - rm.last_trade_close_time[symbol]).total_seconds()
        if elapsed < rm.COOLDOWN_SECONDS:
            remaining_min = (rm.COOLDOWN_SECONDS - elapsed) / 60
            log.info(f"Cooldown actif pour {symbol} : {remaining_min:.0f}min restantes avant prochain trade autorisé")
            return False

    # Vérifier le nombre maximum de positions ouvertes
    if len(rm.open_positions) >= rm.MAX_OPEN_POSITIONS:
        log.info(f"Nombre maximum de positions atteint: {len(rm.open_positions)}/{rm.MAX_OPEN_POSITIONS}")
        return False

    # Vérifier la limite de perte quotidienne
    daily_loss_pct = abs(min(0, rm.daily_pnl)) / account_balance * 100 if account_balance > 0 else 0
    if daily_loss_pct >= rm.MAX_DAILY_LOSS_PCT:
        log.info(f"Limite de perte quotidienne atteinte: {daily_loss_pct:.2f}% >= {rm.MAX_DAILY_LOSS_PCT}%")
        return False

    # Vérifier la limite de perte mensuelle
    monthly_loss_pct = abs(min(0, rm.monthly_pnl)) / account_balance * 100 if account_balance > 0 else 0
    if monthly_loss_pct >= rm.MAX_MONTHLY_LOSS_PCT:
        log.info(f"Limite de perte mensuelle atteinte: {monthly_loss_pct:.2f}% >= {rm.MAX_MONTHLY_LOSS_PCT}%")
        return False

    return True

def get_risk_metrics(rm, account_balance: float = 0.0) -> Dict[str, Any]:
    """
    Retourne les métriques de risque actuelles.

    Args:
        account_balance: Solde actuel du compte

    Returns:
        Dictionnaire contenant les métriques de risque
    """
    try:
        if account_balance <= 0:
            account_balance = getattr(rm, 'starting_balance', 10000.0)
        # Calculer le drawdown
        peak_balance = max([rm.starting_balance] +
                         [t.get('balance_after', rm.starting_balance) for t in rm.trade_history if 'balance_after' in t] +
                         [account_balance])
        drawdown = peak_balance - account_balance
        drawdown_pct = (drawdown / peak_balance) * 100 if peak_balance > 0 else 0

        # Calculer le taux de victoire
        winning_trades = [t for t in rm.trade_history if t.get('pnl', 0) > 0]
        win_rate = len(winning_trades) / len(rm.trade_history) if rm.trade_history else 0

        # Calculer le profit factor
        gross_profit = sum([t['pnl'] for t in rm.trade_history if t.get('pnl', 0) > 0])
        gross_loss = abs(sum([t['pnl'] for t in rm.trade_history if t.get('pnl', 0) < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Calculer le gain moyen/perte moyenne
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        losing_trades = [t for t in rm.trade_history if t.get('pnl', 0) < 0]
        avg_loss = np.mean([abs(t['pnl']) for t in losing_trades]) if losing_trades else 0

        # Risque actuel basé sur les positions ouvertes
        current_risk = 0.0
        for position in rm.open_positions.values():
            if 'size' in position and 'entry_price' in position and 'stop_loss' in position:
                risk_per_unit = abs(position['entry_price'] - position['stop_loss'])
                position_risk = position['size'] * risk_per_unit
                current_risk += position_risk

        current_risk_pct = (current_risk / account_balance) * 100 if account_balance > 0 else 0

        metrics = {
            'account_balance': account_balance,
            'starting_balance': rm.starting_balance,
            'total_pnl': account_balance - rm.starting_balance,
            'total_pnl_pct': ((account_balance / rm.starting_balance) - 1) * 100 if rm.starting_balance > 0 else 0,
            'daily_pnl': rm.daily_pnl,
            'daily_pnl_pct': (rm.daily_pnl / account_balance) * 100 if account_balance > 0 else 0,
            'monthly_pnl': rm.monthly_pnl,
            'monthly_pnl_pct': (rm.monthly_pnl / account_balance) * 100 if account_balance > 0 else 0,
            'drawdown': drawdown,
            'drawdown_pct': drawdown_pct,
            'open_positions_count': len(rm.open_positions),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'trades_count': len(rm.trade_history),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'current_risk_pct': current_risk_pct,
            'kelly_fraction': rm._calculate_kelly_fraction(),
            'timestamp': datetime.now().isoformat()
        }

        return metrics

    except Exception as e:
        log.error(f"Erreur lors du calcul des métriques de risque: {e}")
        return {'error': str(e), 'timestamp': datetime.now().isoformat()}