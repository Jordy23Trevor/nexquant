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
        self.MIN_POSITION_SIZE = config.get('MIN_POSITION_SIZE', 0.001)  # Taille min position
        self.MAX_POSITION_SIZE = config.get('MAX_POSITION_SIZE', 1000.0)  # Taille max position

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

        # Positions actuelles et historique
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.position_history: List[Dict[str, Any]] = []

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
            log.debug("Réinitialisation du P&L journalier")

        # Réinitialisation mensuelle
        if today.month > self.last_monthly_reset.month or today.year > self.last_monthly_reset.year:
            self.monthly_pnl = 0.0
            self.last_monthly_reset = today.replace(day=1)
            log.debug("Réinitialisation du P&L mensuel")

        # Mettre à jour le solde
        if self.starting_balance == 0.0:
            self.starting_balance = balance
        self.current_balance = balance

        # Calculer le P&L
        self.daily_pnl = balance - self.day_start_balance
        self.monthly_pnl = balance - self.month_start_balance

        log.debug(f"Solde mis à jour: {balance:.2f} | Daily P&L: {self.daily_pnl:.2f} | Monthly P&L: {self.monthly_pnl:.2f}")

    def _can_take_new_trade(self, account_balance: float) -> bool:
        """
        Vérifie si on peut prendre un nouveau trade basé sur les limites de risque.

        Args:
            account_balance: Solde actuel du compte

        Returns:
            True si on peut prendre un nouveau trade, False sinon
        """
        # Vérifier le nombre maximum de positions ouvertes
        if len(self.open_positions) >= self.MAX_OPEN_POSITIONS:
            log.info(f"Nombre maximum de positions atteint: {len(self.open_positions)}/{self.MAX_OPEN_POSITIONS}")
            return False

        # Vérifier la limite de perte quotidienne
        daily_loss_pct = abs(min(0, self.daily_pnl)) / account_balance * 100 if account_balance > 0 else 0
        if daily_loss_pct >= self.MAX_DAILY_LOSS_PCT:
            log.info(f"Limite de perte quotidienne atteinte: {daily_loss_pct:.2f}% >= {self.MAX_DAILY_LOSS_PCT}%")
            return False

        # Vérifier la limite de perte mensuelle
        monthly_loss_pct = abs(min(0, self.monthly_pnl)) / account_balance * 100 if account_balance > 0 else 0
        if monthly_loss_pct >= self.MAX_MONTHLY_LOSS_PCT:
            log.info(f"Limite de perte mensuelle atteinte: {monthly_loss_pct:.2f}% >= {self.MAX_MONTHLY_LOSS_PCT}%")
            return False

        return True

    def calculate_position_size(self, account_balance: float, entry_price: float,
                               stop_loss: float, symbol: str = "",
                               sentiment_factor: float = 1.0,
                               volatility_data: Optional[Dict[str, Any]] = None,
                               correlation_data: Optional[Dict[str, Any]] = None) -> Tuple[float, Dict[str, Any]]:
        """
        Calcule la taille de position optimale basée sur le risque, Kelly, et divers facteurs.

        Args:
            account_balance: Solde du compte
            entry_price: Prix d'entrée proposé
            stop_loss: Niveau de stop loss proposé
            symbol: Symbole de l'instrument
            sentiment_factor: Facteur de sentiment des nouvelles (0-2, où 1 = neutre)
            volatility_data: Données de volatilité pour ajustement
            correlation_data: Données de corrélation pour ajustement de portefeuille

        Returns:
            Tuple de (taille_de_position, détails_du_calcul)
        """
        try:
            # 1. Calculer le risque par unité (en prix)
            risk_per_unit = abs(entry_price - stop_loss)
            if risk_per_unit <= 0:
                log.warning(f"Risque par unité invalide pour {symbol}: {risk_per_unit}")
                return 0.0, {'error': 'Invalid risk per unit'}

            # 2. Calculer le risque en pourcentage du compte
            risk_pct = self.RISK_PCT / 100.0  # Convertir en décimal

            # 3. Ajuster le risque basé sur le sentiment des nouvelles
            # sentiment_factor: < 1 = réduire le risque, > 1 = augmenter légèrement
            adjusted_risk_pct = risk_pct * sentiment_factor

            # S'assurer que le risque ajusté reste dans des limites raisonnables
            adjusted_risk_pct = max(0.005, min(0.05, adjusted_risk_pct))  # Entre 0.5% et 5%

            # 4. Ajuster basé sur la volatilité (si disponible)
            if volatility_data and 'atr' in volatility_data:
                # Plus grande volatilité = taille de position plus petite pour le même risque en $
                # Ceci est déjà pris en compte par le risque en unités de prix, donc pas d'ajustement supplémentaire nécessaire ici
                pass

            # 5. Ajuster basé sur la corrélation du portefeuille (si disponible)
            correlation_adjustment = 1.0
            if correlation_data and 'average_correlation' in correlation_data:
                avg_corr = correlation_data['average_correlation']
                # Plus forte corrélation moyenne = réduire la taille pour éviter la surconcentration
                if avg_corr > 0.7:  # Forte corrélation
                    correlation_adjustment = 0.7
                elif avg_corr > 0.5:  # Corrélation modérée
                    correlation_adjustment = 0.85
                # Faible corrélation (< 0.5) = pas d'ajustement ou augmentation légère

            # 6. Calculer la taille de position de base basée sur le risque
            risk_amount = account_balance * adjusted_risk_pct * correlation_adjustment
            base_position_size = risk_amount / risk_per_unit

            # 7. Appliquer la fraction de Kelly si on a suffisamment de données historiques
            kelly_fraction = self._calculate_kelly_fraction()
            if kelly_fraction is not None and len(self.trade_history) >= self.MIN_TRADES_FOR_KELLY:
                # Kelly suggère la fraction optimale du bankroll à miser
                kelly_position_size = account_balance * kelly_fraction / risk_per_unit
                # Combiner approche risque fixe et Kelly (souvent on utilise une fraction de Kelly)
                position_size = (base_position_size * (1 - self.KELLY_FRACTION) +
                               kelly_position_size * self.KELLY_FRACTION)
                log.debug(f"Kelly appliqué: base={base_position_size:.4f}, kelly={kelly_position_size:.4f}, final={position_size:.4f}")
            else:
                position_size = base_position_size
                if kelly_fraction is not None:
                    log.debug(f"Pas assez de données pour Kelly ({len(self.trade_history)}/{self.MIN_TRADES_FOR_KELLY}), utilisation du risque fixe")
                else:
                    log.debug("Kelly non disponible, utilisation du risque fixe")

            # 8. Appliquer les limites de taille de position
            position_size = max(self.MIN_POSITION_SIZE, min(position_size, self.MAX_POSITION_SIZE))

            # 9. Calculer le risque réel en pourcentage
            actual_risk_amount = position_size * risk_per_unit
            actual_risk_pct = (actual_risk_amount / account_balance) * 100 if account_balance > 0 else 0

            # Détails du calcul pour le logging et le débogage
            details = {
                'account_balance': account_balance,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'risk_per_unit': risk_per_unit,
                'base_risk_pct': risk_pct * 100,
                'sentiment_factor': sentiment_factor,
                'correlation_adjustment': correlation_adjustment,
                'kelly_fraction': kelly_fraction,
                'adjusted_risk_pct': adjusted_risk_pct * 100,
                'position_size': position_size,
                'actual_risk_amount': actual_risk_amount,
                'actual_risk_pct': actual_risk_pct,
                'timestamp': datetime.now().isoformat()
            }

            log.info(f"Taille de position calculée pour {symbol}: {position_size:.6f} | Risque: {actual_risk_pct:.2f}% du compte")
            return position_size, details

        except Exception as e:
            log.error(f"Erreur lors du calcul de la taille de position pour {symbol}: {e}")
            return 0.0, {'error': str(e)}

    def _calculate_kelly_fraction(self) -> Optional[float]:
        """
        Calcule la fraction de Kelly basée sur l'historique des trades.

        Returns:
            Fraction de Kelly (0 à 1) ou None si pas assez de données
        """
        if len(self.trade_history) < self.MIN_TRADES_FOR_KELLY:
            return None

        try:
            # Calculer le taux de victoire et le gain moyen/perte moyenne
            winning_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
            losing_trades = [t for t in self.trade_history if t.get('pnl', 0) <= 0]

            if len(winning_trades) == 0 or len(losing_trades) == 0:
                return None

            win_rate = len(winning_trades) / len(self.trade_history)
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = abs(np.mean([t['pnl'] for t in losing_trades])) if losing_trades else 0

            if avg_loss == 0:
                return None

            # Ratio gain/perte
            win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

            # Formule de Kelly: f* = (bp - q) / b
            # où b = ratio gain/perte, p = probabilité de gain, q = probabilité de perte (1-p)
            if win_loss_ratio > 0:
                kelly_fraction = (win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio
                # Kelly peut être négatif (pas d'avantage) ou trop élevé, on le borne
                kelly_fraction = max(0.0, min(kelly_fraction, 0.9))  # Maximum 90% (très agressif)
                return kelly_fraction
            else:
                return None

        except Exception as e:
            log.error(f"Erreur lors du calcul de la fraction de Kelly: {e}")
            return None

    def calculate_sl_tp_levels(self, entry_price: float, atr_value: float,
                              position_side: str) -> Tuple[float, float]:
        """
        Calcule les niveaux de stop loss et take profit basés sur l'ATR.

        Args:
            entry_price: Prix d'entrée
            atr_value: Valeur de l'ATR (Average True Range)
            position_side: 'LONG' ou 'SHORT'

        Returns:
            Tuple de (stop_loss, take_profit)
        """
        if atr_value <= 0:
            # Fallback : utiliser un pourcentage fixe si l'ATR n'est pas disponible
            risk_pct = 0.02  # 2% de risque par défaut
            if position_side == "LONG":
                sl_price = entry_price * (1 - risk_pct)
                tp_price = entry_price * (1 + risk_pct * 2)  # RR 1:2
            else:  # SHORT
                sl_price = entry_price * (1 + risk_pct)
                tp_price = entry_price * (1 - risk_pct * 2)
            return sl_price, tp_price

        if position_side == "LONG":
            sl_price = entry_price - (self.SL_ATR_MULT * atr_value)
            tp_price = entry_price + (self.TP_ATR_MULT * atr_value)
        else:  # SHORT
            sl_price = entry_price + (self.SL_ATR_MULT * atr_value)
            tp_price = entry_price - (self.TP_ATR_MULT * atr_value)

        # S'assurer que les prix sont positifs et raisonnables
        sl_price = max(0.0001, sl_price)
        tp_price = max(0.0001, tp_price)

        return sl_price, tp_price

    def record_trade(self, trade_record: Dict[str, Any]):
        """
        Enregistre un trade clôturé dans l'historique pour le calcul de Kelly et l'analyse.
        Écrit également le trade dans un fichier JSON Lines pour persistance.

        Args:
            trade_record: Dictionnaire contenant les détails du trade
        """
        try:
            # Ajouter un timestamp de clôture si pas présent
            if 'timestamp' not in trade_record:
                trade_record['timestamp'] = datetime.now().isoformat()
            # S'assurer que le timestamp est une string pour la sérialisation JSON
            elif isinstance(trade_record['timestamp'], datetime):
                trade_record['timestamp'] = trade_record['timestamp'].isoformat()

            # Ajouter à l'historique
            self.trade_history.append(trade_record)

            # Garder seulement les 100 derniers trades pour éviter l'accumulation illimitée
            if len(self.trade_history) > 100:
                self.trade_history = self.trade_history[-100:]

            # Écrire dans le fichier JSON Lines
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            trades_file = os.path.join(log_dir, 'trades.jsonl')
            with open(trades_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(trade_record, ensure_ascii=False, default=str) + '\n')

            log.debug(f"Trade enregistré: {trade_record.get('symbol', 'Unknown')} | P&L: {trade_record.get('pnl', 0):.2f}")

        except Exception as e:
            log.error(f"Erreur lors de l'enregistrement du trade: {e}")

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

        try:
            # Calculer le P&L actuel et le pourcentage
            if position['side'] == 'LONG':
                pnl = (current_price - position['entry_price']) * position['size']
                pnl_pct = (current_price / position['entry_price'] - 1) * 100
            else:  # SHORT
                pnl = (position['entry_price'] - current_price) * position['size']
                pnl_pct = (position['entry_price'] / current_price - 1) * 100

            position['current_price'] = current_price
            position['unrealized_pnl'] = pnl
            position['unrealized_pnl_pct'] = pnl_pct
            position['last_update'] = datetime.now().isoformat()

            # Vérifier les conditions de trailing stop et break-even
            self._check_trailing_stop(symbol, position, current_price)
            self._check_break_even(symbol, position, current_price)

        except Exception as e:
            log.error(f"Erreur lors de la mise à jour de la position {symbol}: {e}")

    def _check_trailing_stop(self, symbol: str, position: Dict[str, Any], current_price: float):
        """
        Vérifie et met à jour le stop loss suiveur si les conditions sont remplies.

        Args:
            symbol: Symbole de la position
            position: Dictionnaire de la position
            current_price: Prix actuel du marché
        """
        # Vérifier si le trailing stop est activé pour cette position
        if not position.get('trailing_stop_enabled', False):
            return

        try:
            atr_value = position.get('atr_value', 0)
            if atr_value <= 0:
                return

            if position['side'] == 'LONG':
                # Pour une position longue, le trailing stop monte quand le prix monte
                new_sl = current_price - (self.TRAIL_ATR_MULT * atr_value)
                # Ne jamais descendre le stop loss pour une position longue
                if new_sl > position.get('stop_loss', 0):
                    old_sl = position.get('stop_loss', 0)
                    position['stop_loss'] = new_sl
                    log.info(f"Trailing stop mis à jour pour {symbol} (LONG): {old_sl:.4f} -> {new_sl:.4f}")
            else:  # SHORT
                # Pour une position courte, le trailing stop descend quand le prix descend
                new_sl = current_price + (self.TRAIL_ATR_MULT * atr_value)
                # Ne jamais monter le stop loss pour une position courte
                if new_sl < position.get('stop_loss', float('inf')) or position.get('stop_loss', 0) == 0:
                    old_sl = position.get('stop_loss', 0)
                    position['stop_loss'] = new_sl
                    log.info(f"Trailing stop mis à jour pour {symbol} (SHORT): {old_sl:.4f} -> {new_sl:.4f}")

        except Exception as e:
            log.error(f"Erreur lors de la vérification du trailing stop pour {symbol}: {e}")

    def _check_break_even(self, symbol: str, position: Dict[str, Any], current_price: float):
        """
        Vérifie et déplace le stop loss au point d'entrée si les conditions sont remplies.

        Args:
            symbol: Symbole de la position
            position: Dictionnaire de la position
            current_price: Prix actuel du marché
        """
        # Vérifier si le break-even est activé et pas déjà activé
        if position.get('break_even_activated', False):
            return

        try:
            atr_value = position.get('atr_value', 0)
            if atr_value <= 0:
                return

            # Calculer le profit actuel en unités d'ATR
            if position['side'] == 'LONG':
                profit_in_atr = (current_price - position['entry_price']) / atr_value
                # Activer le break-even quand le profit atteint BE_ATR_MULT * ATR
                if profit_in_atr >= self.BE_ATR_MULT:
                    old_sl = position.get('stop_loss', 0)
                    # Déplacer le stop loss légèrement au-dessus du prix d'entrée pour couvrir les frais
                    new_sl = position['entry_price'] * 1.001  # Légèrement au-dessus pour les frais
                    if new_sl > old_sl:  # Seulement si ça améliore le stop loss
                        position['stop_loss'] = new_sl
                        position['break_even_activated'] = True
                        log.info(f"Break-even activé pour {symbol} (LONG): SL moved to {new_sl:.4f}")
            else:  # SHORT
                profit_in_atr = (position['entry_price'] - current_price) / atr_value
                if profit_in_atr >= self.BE_ATR_MULT:
                    old_sl = position.get('stop_loss', float('inf'))
                    # Déplacer le stop loss légèrement en-dessous du prix d'entrée pour couvrir les frais
                    new_sl = position['entry_price'] * 0.999  # Légèrement en-dessous pour les frais
                    if new_sl < old_sl or old_sl == 0:  # Seulement si ça améliore le stop loss
                        position['stop_loss'] = new_sl
                        position['break_even_activated'] = True
                        log.info(f"Break-even activé pour {symbol} (SHORT): SL moved to {new_sl:.4f}")

        except Exception as e:
            log.error(f"Erreur lors de la vérification du break-even pour {symbol}: {e}")

    def get_risk_metrics(self, account_balance: float) -> Dict[str, Any]:
        """
        Retourne les métriques de risque actuelles.

        Args:
            account_balance: Solde actuel du compte

        Returns:
            Dictionnaire contenant les métriques de risque
        """
        try:
            # Calculer le drawdown
            peak_balance = max([self.starting_balance] +
                             [t.get('balance_after', self.starting_balance) for t in self.trade_history if 'balance_after' in t] +
                             [account_balance])
            drawdown = peak_balance - account_balance
            drawdown_pct = (drawdown / peak_balance) * 100 if peak_balance > 0 else 0

            # Calculer le taux de victoire
            winning_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
            win_rate = len(winning_trades) / len(self.trade_history) if self.trade_history else 0

            # Calculer le profit factor
            gross_profit = sum([t['pnl'] for t in self.trade_history if t.get('pnl', 0) > 0])
            gross_loss = abs(sum([t['pnl'] for t in self.trade_history if t.get('pnl', 0) < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

            # Calculer le gain moyen/perte moyenne
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            losing_trades = [t for t in self.trade_history if t.get('pnl', 0) < 0]
            avg_loss = np.mean([abs(t['pnl']) for t in losing_trades]) if losing_trades else 0

            # Risque actuel basé sur les positions ouvertes
            current_risk = 0.0
            for position in self.open_positions.values():
                if 'size' in position and 'entry_price' in position and 'stop_loss' in position:
                    risk_per_unit = abs(position['entry_price'] - position['stop_loss'])
                    position_risk = position['size'] * risk_per_unit
                    current_risk += position_risk

            current_risk_pct = (current_risk / account_balance) * 100 if account_balance > 0 else 0

            metrics = {
                'account_balance': account_balance,
                'starting_balance': self.starting_balance,
                'total_pnl': account_balance - self.starting_balance,
                'total_pnl_pct': ((account_balance / self.starting_balance) - 1) * 100 if self.starting_balance > 0 else 0,
                'daily_pnl': self.daily_pnl,
                'daily_pnl_pct': (self.daily_pnl / account_balance) * 100 if account_balance > 0 else 0,
                'monthly_pnl': self.monthly_pnl,
                'monthly_pnl_pct': (self.monthly_pnl / account_balance) * 100 if account_balance > 0 else 0,
                'drawdown': drawdown,
                'drawdown_pct': drawdown_pct,
                'open_positions_count': len(self.open_positions),
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'trades_count': len(self.trade_history),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'current_risk_pct': current_risk_pct,
                'kelly_fraction': self._calculate_kelly_fraction(),
                'timestamp': datetime.now().isoformat()
            }

            return metrics

        except Exception as e:
            log.error(f"Erreur lors du calcul des métriques de risque: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    def reset_daily_stats(self):
        """Réinitialise les statistiques journalières."""
        self.daily_pnl = 0.0
        self.last_daily_reset = datetime.now().date()
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