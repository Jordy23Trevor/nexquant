"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╩
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
import logging
from datetime import datetime, timedelta
import json
import os

log = logging.getLogger("risk_manager")


class RiskManager:
    """
    Gestionnaire de risque professionnel basé sur les principes d'Elder et Kabbaj.
    Implémente les règles des 2% par trade et 6% mensuel, la taille de position Kelly,
    l'ajustement basé sur la volatilité et la corrélation, ainsi que le trailing stop.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le gestionnaire de risque.

        Args:
            config: Dictionnaire contenant la configuration de risque
                   (RISK_PCT, MAX_DAILY_LOSS_PCT, MAX_MONTHLY_LOSS_PCT,
                    MAX_OPEN_POSITIONS, KELLY_FRACTION, etc.)
        """
        self.config = config
        self.RISK_PCT = config.get('RISK_PCT', 1.0)  # % du compte à risquer par trade
        self.MAX_DAILY_LOSS_PCT = config.get('MAX_DAILY_LOSS_PCT', 3.0)  # % max perte journalier
        self.MAX_MONTHLY_LOSS_PCT = config.get('MAX_MONTHLY_LOSS_PCT', 6.0)  # % max perte mensuel
        self.MAX_OPEN_POSITIONS = config.get('MAX_OPEN_POSITIONS', 2)  # Max positions simultanées
        self.KELLY_FRACTION = config.get('KELLY_FRACTION', 0.25)  # Fraction de Kelly à utiliser
        self.MIN_TRADES_FOR_KELLY = config.get('MIN_TRADES_FOR_KELLY', 20)  # Trades min pour Kelly
        self.SL_ATR_MULT = config.get('SL_ATR_MULT', 1.5)  # Multiplicateur ATR pour SL
        self.TP_ATR_MULT = config.get('TP_ATR_MULT', 3.0)  # Multiplicateur ATR pour TP
        self.TRAIL_ATR_MULT = config.get('TRAIL_ATR_MULT', 1.0)  # Multiplicateur ATR pour trailing
        self.BE_ATR_MULT = config.get('BE_ATR_MULT', 1.0)  # Multiplicateur ATR pour break-even
        self.BE_DYN_RR = config.get('BE_DYN_RR', True)  # Activer le break-even dynamique (1:1 R:R)
        self.BE_DYN_RR_RATIO = config.get('BE_DYN_RR_RATIO', 1.0)  # Ratio R:R pour le break-even dynamique
        self.MIN_POSITION_SIZE = config.get('MIN_POSITION_SIZE', 0.001)  # Taille min position
        self.MAX_POSITION_SIZE = config.get('MAX_POSITION_SIZE', 1000.0)  # Taille max position


        # Multiplicateurs ATR dynamiques par type d'actif
        self.ATR_MULTIPLIERS = {
            'forex': {'sl': 1.5, 'tp': 3.0},
            # ✅ BUG FIX #4 — Multiplicateurs spécifiques pour paires JPY (volatility intrinsèque plus élevée)
            # GBPJPY, USDJPY, EURJPY bougent 150-250 pips/jour vs 60-100 pour EURUSD.
            # Un SL à 1.5×ATR déclenchait des fermetures prématurées (ex: GBPJPY fermé en 4 min le 2026-07-01).
            # R:R maintenu à 1:2 en augmentant proportionnellement SL et TP.
            'forex_jpy': {'sl': 2.0, 'tp': 4.0},
            'stock': {'sl': 2.0, 'tp': 4.0},
            'crypto': {'sl': 2.5, 'tp': 5.0}
        }

        # Historique des trades pour le calcul de Kelly
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_pnl = 0.0
        self.monthly_pnl = 0.0
        self.starting_balance = 0.0
        self.current_balance = 0.0
        self.day_start_balance = 0.0
        self.month_start_balance = 0.0
        self.last_daily_reset = datetime.now().date()
        self.last_monthly_reset = datetime.now().replace(day=1).date()

        # ── Phase 3 §3 — Protection par drawdown ────────────────────────────
        # Suivi du pic d'équité pour calculer le drawdown en temps réel.
        # Le risque par trade est réduit progressivement lorsque le compte
        # est en drawdown : -20% de risque à 5% DD, -50% à 10% DD.
        self.peak_balance: float = 0.0  # Plus haut historique du compte
        self.drawdown_pct: float = 0.0  # Drawdown courant en %
        self.DRAWDOWN_REDUCE_5PCT = config.get('DRAWDOWN_REDUCE_5PCT', 0.20)   # -20% risque à 5% DD
        self.DRAWDOWN_REDUCE_10PCT = config.get('DRAWDOWN_REDUCE_10PCT', 0.50)  # -50% risque à 10% DD
        self.DRAWDOWN_THRESH_1 = config.get('DRAWDOWN_THRESH_1', 5.0)   # % déclencheur niveau 1
        self.DRAWDOWN_THRESH_2 = config.get('DRAWDOWN_THRESH_2', 10.0)  # % déclencheur niveau 2

        # ✅ BUG FIX #5 — Cooldown entre deux trades consécutifs sur le même symbole.
        # Empêche le rechargement immédiat après une perte (ex: USDCAD réouvert 21min après une perte).
        # 1 heure = au moins 1 bougie H1 complète, permettant un changement de contexte marché.
        self.COOLDOWN_SECONDS = config.get('COOLDOWN_SECONDS', 3600)  # 1h par défaut
        self.last_trade_close_time: Dict[str, datetime] = {}  # symbol -> heure de dernière clôture

        # Positions actuelles et historique
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.position_history: List[Dict[str, Any]] = []
        self.consecutive_losses: Dict[str, int] = {}

        log.info(f"RiskManager initialisé avec config: {self.config}")

    def update_account_balance(self, balance: float):
        """
        Met à jour le solde du compte et réinitialise les périodes si nécessaire.

        Args:
            balance: Nouveau solde du compte
        """
        # Réinitialisation quotidienne
        today = datetime.now().date()
        if today > self.last_daily_reset:
            self.daily_pnl = 0.0
            self.last_daily_reset = today
            self.consecutive_losses = {}  # Reset daily consecutive losses
            self.day_start_balance = balance  # IMPORTANT: Update daily start balance
            log.debug("Réinitialisation du P&L journalier et des pertes consécutives")

        # Réinitialisation mensuelle
        if today.month > self.last_monthly_reset.month or today.year > self.last_monthly_reset.year:
            self.monthly_pnl = 0.0
            self.last_monthly_reset = today.replace(day=1)
            log.debug("Réinitialisation du P&L mensuel")

        # Mettre à jour le solde
        if self.starting_balance == 0.0:
            self.starting_balance = balance
            if self.day_start_balance == 0.0:
                self.day_start_balance = balance
            if self.month_start_balance == 0.0:
                self.month_start_balance = balance
        self.current_balance = balance

        # ── Phase 3 §3 — Mise à jour du pic d'équité et du drawdown ────────
        if balance > self.peak_balance:
            self.peak_balance = balance
        if self.peak_balance > 0:
            self.drawdown_pct = (self.peak_balance - balance) / self.peak_balance * 100
        else:
            self.drawdown_pct = 0.0

        # Calculer le P&L
        self.daily_pnl = balance - self.day_start_balance
        self.monthly_pnl = balance - self.month_start_balance

        log.debug(f"Solde mis à jour: {balance:.2f} | Daily P&L: {self.daily_pnl:.2f} | Monthly P&L: {self.monthly_pnl:.2f} | Drawdown: {self.drawdown_pct:.1f}%")

    def check_kill_switch(self, account_balance: float) -> bool:
        """
        Vérifie le Kill-Switch de Drawdown journalier.
        Retourne True si le bot doit se mettre en auto-pause pour la journée.
        """
        if self.day_start_balance > 0:
            daily_loss_pct = abs(min(0, self.daily_pnl)) / self.day_start_balance * 100
            if daily_loss_pct >= self.MAX_DAILY_LOSS_PCT:
                log.critical(f"⚠️ KILL-SWITCH ACTIVÉ : Perte journalière ({daily_loss_pct:.2f}%) >= {self.MAX_DAILY_LOSS_PCT}%.")
                return True
        return False

    def _can_take_new_trade(self, asset_type: str, account_balance: float = 0.0) -> Tuple[bool, str]:
        from superbot.risk.modules.risk_monitor import _can_take_new_trade
        return _can_take_new_trade(self, asset_type, account_balance)

    def calculate_position_size(self, account_balance: float, entry_price: float,
                                stop_loss: float, symbol: str = "",
                                sentiment_factor: float = 1.0,
                                volatility_data: Optional[Dict[str, Any]] = None,
                                correlation_data: Optional[Dict[str, Any]] = None,
                                broker: Optional[Any] = None,
                                hmm_regime: str = "") -> Tuple[float, Dict[str, Any]]:
        from superbot.risk.modules.position_sizer import calculate_position_size
        return calculate_position_size(
            self, account_balance=account_balance, entry_price=entry_price,
            stop_loss=stop_loss, symbol=symbol,
            sentiment_factor=sentiment_factor, volatility_data=volatility_data,
            correlation_data=correlation_data, broker=broker, hmm_regime=hmm_regime
        )

    def _calculate_kelly_fraction(self) -> Optional[float]:
        from superbot.risk.modules.position_sizer import _calculate_kelly_fraction
        return _calculate_kelly_fraction(self)

    def calculate_sl_tp_levels(self, current_price: float = 0.0, atr: float = 0.0, direction: str = "LONG",
                               asset_type: str = "forex", symbol: str = "", hmm_regime: str = "TRENDING",
                               entry_price: Optional[float] = None, atr_value: Optional[float] = None,
                               position_side: Optional[str] = None, **kwargs) -> Tuple[float, float]:
        price = entry_price if entry_price is not None else current_price
        atr_val = atr_value if atr_value is not None else atr
        side = position_side if position_side is not None else direction
        from superbot.risk.modules.stop_manager import calculate_sl_tp_levels
        return calculate_sl_tp_levels(self, price, atr_val, side, asset_type, symbol, hmm_regime)

    def record_trade(self, trade_record: Dict[str, Any]):
        from superbot.risk.modules.trade_recorder import record_trade
        return record_trade(self, trade_record)

    def load_trade_history_from_disk(self):
        from superbot.risk.modules.trade_recorder import load_trade_history_from_disk
        return load_trade_history_from_disk(self)

    def merge_broker_history(self, broker_trades: list):
        from superbot.risk.modules.trade_recorder import merge_broker_history
        return merge_broker_history(self, broker_trades)

    def update_open_position(self, symbol: str, current_price: float):
        """
        Met à jour une position ouverte avec le prix actuel pour le trailing stop et le break-even.

        Args:
            symbol: Symbole de la position
            current_price: Prix actuel du marché
        """
        if symbol not in self.open_positions:
            return

        position = self.open_positions[symbol]

        if 'initial_sl' not in position or position['initial_sl'] == 0:
            position['initial_sl'] = position.get('stop_loss', 0.0)

        try:
            if position['side'] == 'LONG':
                raw_pnl = (current_price - position['entry_price']) * position['size']
                pnl_pct = (current_price / position['entry_price'] - 1) * 100
            else:  # SHORT
                raw_pnl = (position['entry_price'] - current_price) * position['size']
                pnl_pct = (position['entry_price'] / current_price - 1) * 100

            sym = position.get('symbol', symbol)
            normalized_sym = sym.strip().upper().replace("/", "")
            if normalized_sym.endswith("JPY") and current_price > 0:
                pnl = raw_pnl / current_price
                log.debug(f"Conversion PnL unrealized JPY→USD pour {sym}: {raw_pnl:.2f} JPY / {current_price:.3f} = {pnl:.2f} USD")
            else:
                pnl = raw_pnl

            position['current_price'] = current_price
            position['unrealized_pnl'] = pnl
            position['unrealized_pnl_pct'] = pnl_pct
            position['last_update'] = datetime.now().isoformat()

            self._check_trailing_stop(symbol, position, current_price)
            self._check_break_even(symbol, position, current_price)

        except Exception as e:
            log.error(f"Erreur lors de la mise à jour de la position {symbol}: {e}")

    def _check_trailing_stop(self, *args, **kwargs):
        # Signature robuste pour accepter n'importe quelle variante d'arguments
        symbol = kwargs.get('symbol')
        pos = kwargs.get('pos') or kwargs.get('position')
        current_price = kwargs.get('current_price')

        positional = list(args)
        if positional and hasattr(positional[0], 'open_positions'):
            positional = positional[1:]

        if len(positional) >= 3:
            symbol, pos, current_price = positional[0], positional[1], positional[2]
        elif len(positional) == 2:
            symbol, current_price = positional[0], positional[1]
            pos = self.open_positions.get(symbol)

        if pos is None and symbol in self.open_positions:
            pos = self.open_positions[symbol]

        if symbol and pos and current_price is not None:
            from superbot.risk.modules.stop_manager import _check_trailing_stop
            return _check_trailing_stop(self, symbol, pos, current_price)

    def _check_break_even(self, symbol: str, pos: dict, current_price: float):
        from superbot.risk.modules.stop_manager import _check_break_even
        return _check_break_even(self, symbol, pos, current_price)

    def get_risk_metrics(self, account_balance: float = 0.0) -> Dict[str, Any]:
        from superbot.risk.modules.risk_monitor import get_risk_metrics
        return get_risk_metrics(self, account_balance)

    def reset_daily_stats(self):
        """Réinitialise les statistiques journalières."""
        self.daily_pnl = 0.0
        self.last_daily_reset = datetime.now().date()
        self.consecutive_losses = {}
        log.info("Statistiques journalières réinitialisées")

    def reset_monthly_stats(self):
        """Réinitialise les statistiques mensuelles."""
        self.monthly_pnl = 0.0
        self.last_monthly_reset = datetime.now().replace(day=1).date()
        log.info("Statistiques mensuelles réinitialisées")


# Fonctions utilitaires pour une utilisation facile
def calculate_position_size_from_risk(account_balance: float, risk_pct: float,
                                    entry_price: float, stop_loss: float) -> float:
    """
    Fonction utilitaire pour calculer rapidement la taille de position basée sur le risque.

    Args:
        account_balance: Solde du compte
        risk_pct: Pourcentage du compte à risquer (ex: 2.0 pour 2%)
        entry_price: Prix d'entrée
        stop_loss: Niveau de stop loss

    Returns:
        Taille de position
    """
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit <= 0:
        return 0.0
    risk_amount = account_balance * (risk_pct / 100.0)
    return risk_amount / risk_per_unit


# Export des classes et fonctions publiques
__all__ = [
    'RiskManager',
    'calculate_position_size_from_risk'
]