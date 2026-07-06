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
            log.debug("Réinitialisation du P&L journalier et des pertes consécutives")

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

    def _can_take_new_trade(self, account_balance: float, symbol: str = "") -> bool:
        """
        Vérifie si on peut prendre un nouveau trade basé sur les limites de risque.

        Args:
            account_balance: Solde actuel du compte
            symbol: Symbole de l'instrument

        Returns:
            True si on peut prendre un nouveau trade, False sinon
        """
        # Vérifier si on a déjà une position sur ce symbole
        if symbol and symbol in self.open_positions:
            log.info(f"Position déjà ouverte pour {symbol}, rejet du nouveau trade.")
            return False
            
        # Vérifier les pertes consécutives sur ce symbole
        if symbol and self.consecutive_losses.get(symbol, 0) >= 3:
            log.info(f"Symbole {symbol} bloqué (3 pertes consécutives atteintes).")
            return False

        # ✅ BUG FIX #5 — Cooldown : vérifier le délai depuis la dernière clôture sur ce symbole
        if symbol and symbol in self.last_trade_close_time:
            elapsed = (datetime.now() - self.last_trade_close_time[symbol]).total_seconds()
            if elapsed < self.COOLDOWN_SECONDS:
                remaining_min = (self.COOLDOWN_SECONDS - elapsed) / 60
                log.info(f"Cooldown actif pour {symbol} : {remaining_min:.0f}min restantes avant prochain trade autorisé")
                return False

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
                               correlation_data: Optional[Dict[str, Any]] = None,
                               broker: Optional[Any] = None) -> Tuple[float, Dict[str, Any]]:
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
            broker: Instance du courtier actif

        Returns:
            Tuple de (taille_de_position, détails_du_calcul)
        """
        try:
            # 1. Récupérer les spécifications du symbole (taille du contrat, tick size, tick value)
            contract_size = 1.0
            tick_size = 0.01
            tick_value = 0.01
            
            if broker is not None and hasattr(broker, 'get_symbol_info'):
                try:
                    sym_info = broker.get_symbol_info(symbol)
                    contract_size = sym_info.get('contract_size', 1.0)
                    tick_size = sym_info.get('tick_size', 0.01)
                    tick_value = sym_info.get('tick_value', 0.01)
                except Exception as e:
                    log.warning(f"Impossible de récupérer les spécifications de symbole pour {symbol}: {e}")

            # 2. Calculer le risque par unité en devise de compte
            price_risk = abs(entry_price - stop_loss)
            if price_risk <= 0:
                log.warning(f"Risque par unité invalide pour {symbol}: {price_risk}")
                return 0.0, {'error': 'Invalid risk per unit'}

            # Formule universelle de risque par unité dans la monnaie de compte
            risk_per_unit = (price_risk / tick_size) * (tick_value / contract_size)

            # 3. Calculer le risque en pourcentage du compte
            risk_pct = self.RISK_PCT / 100.0  # Convertir en décimal

            # 4. Ajuster le risque basé sur le sentiment des nouvelles
            # sentiment_factor: < 1 = réduire le risque, > 1 = augmenter légèrement
            adjusted_risk_pct = risk_pct * sentiment_factor

            # S'assurer que le risque ajusté reste dans des limites raisonnables
            adjusted_risk_pct = max(0.005, min(0.05, adjusted_risk_pct))  # Entre 0.5% et 5%

            # 5. Ajuster basé sur la corrélation du portefeuille (si disponible)
            correlation_adjustment = 1.0
            if correlation_data and 'average_correlation' in correlation_data:
                avg_corr = correlation_data['average_correlation']
                # Plus forte corrélation moyenne = réduire la taille pour éviter la surconcentration
                if avg_corr > 0.7:  # Forte corrélation
                    correlation_adjustment = 0.7
                elif avg_corr > 0.5:  # Corrélation modérée
                    correlation_adjustment = 0.85

            # 6. Calculer la taille de position de base basée sur le risque
            risk_amount = account_balance * adjusted_risk_pct * correlation_adjustment
            base_position_size = risk_amount / risk_per_unit

            # 7. Appliquer la fraction de Kelly si on a suffisamment de données historiques
            kelly_fraction = self._calculate_kelly_fraction()
            if kelly_fraction is not None and len(self.trade_history) >= self.MIN_TRADES_FOR_KELLY:
                # Kelly suggère la fraction optimale du bankroll à miser
                kelly_position_size = account_balance * kelly_fraction / risk_per_unit
                # Combiner approche risque fixe et Kelly
                position_size = (base_position_size * (1 - self.KELLY_FRACTION) +
                               kelly_position_size * self.KELLY_FRACTION)
                log.debug(f"Kelly appliqué: base={base_position_size:.4f}, kelly={kelly_position_size:.4f}, final={position_size:.4f}")
            else:
                position_size = base_position_size
                if kelly_fraction is not None:
                    log.debug(f"Pas assez de données pour Kelly ({len(self.trade_history)}/{self.MIN_TRADES_FOR_KELLY}), utilisation du risque fixe")
                else:
                    log.debug("Kelly non disponible, utilisation du risque fixe")

            # 8. Récupérer les limites de taille spécifiques au broker
            min_size = self.MIN_POSITION_SIZE
            step_size = None
            if broker is not None:
                try:
                    min_size = broker.get_min_order_size(symbol)
                    step_size = broker.get_step_size(symbol)
                except Exception as e:
                    log.warning(f"Impossible de récupérer les limites broker pour {symbol}: {e}")

            # 8.5. Restreindre la taille par rapport à la marge disponible chez le broker
            free_margin = account_balance
            leverage = 1
            if broker is not None:
                try:
                    summary = broker.get_account_summary()
                    if summary:
                        # Chercher la marge disponible
                        free_margin = summary.get("free_margin")
                        if free_margin is None:
                            free_margin = summary.get("buying_power")
                        if free_margin is None:
                            free_margin = summary.get("available_balance")
                        if free_margin is None:
                            free_margin = summary.get("balance", account_balance)
                            
                        # Chercher l'effet de levier
                        leverage = summary.get("leverage", 1)
                except Exception as e:
                    log.warning(f"Impossible de récupérer la marge disponible du broker pour {symbol}: {e}")

            # Calculer la taille maximale autorisée par la marge disponible (avec 5% de buffer)
            is_buying_power_direct = (broker is not None and broker.get_asset_type() == "stock")
            if is_buying_power_direct:
                max_nominal = free_margin * 0.95
                max_size_by_margin = max_nominal / entry_price if entry_price > 0 else 0.0
            else:
                max_nominal = free_margin * leverage * 0.95
                max_size_by_margin = max_nominal / entry_price if entry_price > 0 else 0.0

            # Si la taille maximale par rapport à la marge est inférieure au minimum du symbole
            if max_size_by_margin < min_size:
                log.warning(
                    f"❌ Marge disponible insuffisante pour la taille minimale sur {symbol}. "
                    f"Taille min requise: {min_size:.6f}, Max autorisé par marge: {max_size_by_margin:.6f} "
                    f"(Marge dispo: {free_margin:.2f}, Levier: {leverage}x)"
                )
                return 0.0, {
                    'error': 'Insufficient margin for minimum position size',
                    'free_margin': free_margin,
                    'leverage': leverage,
                    'min_size': min_size,
                    'max_size_by_margin': max_size_by_margin
                }

            if position_size > max_size_by_margin:
                log.info(
                    f"⚠️ Taille de position restreinte par la marge disponible pour {symbol} : "
                    f"{position_size:.6f} -> {max_size_by_margin:.6f} "
                    f"(Marge disponible: {free_margin:.2f}, Levier: {leverage}x, Max nominal: {max_nominal:.2f})"
                )
                position_size = max_size_by_margin

            # Appliquer les limites de taille de position
            position_size = max(min_size, min(position_size, self.MAX_POSITION_SIZE))

            if step_size is not None and step_size > 0:
                import math
                position_size = math.floor(position_size / step_size) * step_size
                position_size = round(position_size, 8)

            # 9. Calculer le risque réel en pourcentage
            actual_risk_amount = position_size * risk_per_unit
            actual_risk_pct = (actual_risk_amount / account_balance) * 100 if account_balance > 0 else 0

            # Si le risque réel dépasse la limite de sécurité
            max_allowed_risk_pct = min(self.MAX_DAILY_LOSS_PCT, max(3.0, self.RISK_PCT * 2.0))
            if actual_risk_pct > max_allowed_risk_pct:
                if position_size <= min_size:
                    log.warning(
                        f"Risque réel de {actual_risk_pct:.2f}% dépasse la limite autorisée de {max_allowed_risk_pct:.2f}% "
                        f"pour {symbol} (taille minimale de contrat trop grande pour la taille du compte). Trade rejeté."
                    )
                    return 0.0, {'error': 'Risk too high for account size due to contract minimums'}
                else:
                    # Capper la taille pour respecter la limite
                    log.info(f"Capping de la taille de position de {position_size:.6f} à la limite de risque de {max_allowed_risk_pct:.2f}%")
                    position_size = (max_allowed_risk_pct / 100.0) * account_balance / risk_per_unit
                    if step_size is not None and step_size > 0:
                        position_size = math.floor(position_size / step_size) * step_size
                        position_size = round(position_size, 8)
                    actual_risk_amount = position_size * risk_per_unit
                    actual_risk_pct = (actual_risk_amount / account_balance) * 100 if account_balance > 0 else 0

            # Détails du calcul pour le logging et le débogage
            details = {
                'account_balance': account_balance,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'risk_per_unit': risk_per_unit,
                'price_risk': price_risk,
                'base_risk_pct': risk_pct * 100,
                'sentiment_factor': sentiment_factor,
                'correlation_adjustment': correlation_adjustment,
                'kelly_fraction': kelly_fraction,
                'adjusted_risk_pct': adjusted_risk_pct * 100,
                'position_size': position_size,
                'actual_risk_amount': actual_risk_amount,
                'actual_risk_pct': actual_risk_pct,
                'free_margin': free_margin,
                'leverage': leverage,
                'max_size_by_margin': max_size_by_margin,
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
            # Filtrer uniquement les trades CLÔTURÉS avec un P&L valide
            trades_with_pnl = [t for t in self.trade_history if t.get('pnl') is not None and t.get('status') == 'closed']

            # Pas assez de trades clôturés pour Kelly
            if len(trades_with_pnl) < self.MIN_TRADES_FOR_KELLY:
                log.debug(f"Pas assez de trades clôturés pour Kelly: {len(trades_with_pnl)}/{self.MIN_TRADES_FOR_KELLY}")
                return None

            # Séparer gagnants et perdants uniquement sur les trades avec P&L valide
            winning_trades = [t for t in trades_with_pnl if t.get('pnl', 0) > 0]
            losing_trades = [t for t in trades_with_pnl if t.get('pnl', 0) <= 0]

            if len(winning_trades) == 0 or len(losing_trades) == 0:
                log.debug(f"Kelly: winning={len(winning_trades)}, losing={len(losing_trades)} - impossible de calculer")
                return None

            # Calculer le win rate sur les trades clôturés uniquement
            win_rate = len(winning_trades) / len(trades_with_pnl)

            # Extraire les P&L avec validation
            avg_win = np.mean([t['pnl'] for t in winning_trades if 'pnl' in t]) if winning_trades else 0
            avg_loss = abs(np.mean([t['pnl'] for t in losing_trades if 'pnl' in t])) if losing_trades else 0

            if avg_loss == 0:
                log.debug("Kelly: avg_loss = 0, impossible de calculer")
                return None

            # Ratio gain/perte
            win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

            # Formule de Kelly: f* = (bp - q) / b
            # où b = ratio gain/perte, p = probabilité de gain, q = probabilité de perte (1-p)
            if win_loss_ratio > 0:
                kelly_fraction = (win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio
                # Kelly peut être négatif (pas d'avantage) ou trop élevé, on le borne
                kelly_fraction = max(0.0, min(kelly_fraction, 0.9))  # Maximum 90% (très agressif)
                log.debug(f"Kelly calculé: win_rate={win_rate:.2%}, win_loss_ratio={win_loss_ratio:.2f}, kelly={kelly_fraction:.2%}")
                return kelly_fraction
            else:
                log.debug(f"Kelly: win_loss_ratio={win_loss_ratio} <= 0")
                return None

        except KeyError as e:
            log.error(f"Erreur KeyError lors du calcul de la fraction de Kelly: clé manquante {e} - Vérifiez que tous les trades ont un champ 'pnl'")
            return None
        except Exception as e:
            log.error(f"Erreur lors du calcul de la fraction de Kelly: {e}")
            return None

    def calculate_sl_tp_levels(self, entry_price: float, atr_value: float,
                                  position_side: str, asset_type: str = "forex",
                                  symbol: str = "") -> Tuple[float, float]:
        """
        Calcule les niveaux de stop loss et take profit basés sur l'ATR, avec multiplicateurs selon l'actif.

        ✅ BUG FIX #4 — Le paramètre `symbol` permet de détecter automatiquement les paires JPY
        et d'appliquer des multiplicateurs ATR plus larges (2.0×SL / 4.0×TP) pour compenser
        leur plus grande amplitude intra-journalière.
        """
        # Détecter si la paire est une paire JPY — appliquer des multiplicateurs adaptés
        effective_asset_type = asset_type
        if symbol:
            normalized = symbol.strip().upper().replace("/", "")
            if normalized.endswith("JPY") and asset_type == "forex":
                effective_asset_type = "forex_jpy"
                log.debug(f"Multiplicateurs ATR élargis appliqués pour paire JPY {symbol}: SL=2.0×ATR, TP=4.0×ATR")

        if atr_value <= 0:
            risk_pct = 0.02
            if position_side == "LONG":
                sl_price = entry_price * (1 - risk_pct)
                tp_price = entry_price * (1 + risk_pct * 2)
            else:
                sl_price = entry_price * (1 + risk_pct)
                tp_price = entry_price * (1 - risk_pct * 2)
            return sl_price, tp_price

        mults = self.ATR_MULTIPLIERS.get(effective_asset_type, self.ATR_MULTIPLIERS['forex'])
        sl_mult, tp_mult = mults['sl'], mults['tp']

        if position_side == "LONG":
            sl_price = entry_price - (sl_mult * atr_value)
            tp_price = entry_price + (tp_mult * atr_value)
        else:
            sl_price = entry_price + (sl_mult * atr_value)
            tp_price = entry_price - (tp_mult * atr_value)

        return max(0.0001, sl_price), max(0.0001, tp_price)


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

            # Ajouter à l'historique uniquement si le trade est clôturé
            is_closed = trade_record.get('status') == 'closed' or trade_record.get('pnl') is not None
            if is_closed:
                self.trade_history.append(trade_record)

                # Garder seulement les 100 derniers trades pour éviter l'accumulation illimitée
                if len(self.trade_history) > 100:
                    self.trade_history = self.trade_history[-100:]

            # Mise à jour des pertes consécutives
            symbol = trade_record.get('symbol')
            if symbol and trade_record.get('status') == 'closed' and trade_record.get('pnl') is not None:
                if trade_record.get('pnl', 0) < 0:
                    self.consecutive_losses[symbol] = self.consecutive_losses.get(symbol, 0) + 1
                    log.info(f"📉 Perte enregistrée pour {symbol}. Série de pertes: {self.consecutive_losses[symbol]}")
                else:
                    self.consecutive_losses[symbol] = 0
                    log.debug(f"📈 Gain enregistré pour {symbol}. Réinitialisation de la série de pertes.")
                # ✅ BUG FIX #5 — Enregistrer l'heure de clôture pour le cooldown
                self.last_trade_close_time[symbol] = datetime.now()

            # Écrire dans le fichier JSON Lines
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            trades_file = os.path.join(log_dir, 'trades.jsonl')
            with open(trades_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(trade_record, ensure_ascii=False, default=str) + '\n')

            log.debug(f"Trade enregistré: {trade_record.get('symbol', 'Unknown')} | P&L: {trade_record.get('pnl', 0):.2f}")

        except Exception as e:
            log.error(f"Erreur lors de l'enregistrement du trade: {e}")

    def load_trade_history_from_disk(self):
        """
        Charge l'historique des trades enregistrés depuis le fichier JSON Lines.
        Ne charge que les trades CLÔTURÉS avec un P&L valide pour éviter les erreurs Kelly.
        """
        try:
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
            trades_file = os.path.join(log_dir, 'trades.jsonl')
            if not os.path.exists(trades_file):
                log.info("Aucun fichier d'historique de trades trouvé sur le disque.")
                return

            loaded_trades = []
            with open(trades_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            trade = json.loads(line.strip())
                            # Ne conserver que les trades clôturés AVEC un P&L valide
                            # Un trade ouvert n'a pas de champ 'pnl' ou a 'status' != 'closed'
                            if trade.get('status') == 'closed' and trade.get('pnl') is not None:
                                loaded_trades.append(trade)
                        except Exception:
                            continue

            # Garder les 100 plus récents
            self.trade_history = loaded_trades[-100:]
            log.info(f"Historique de trading chargé depuis le disque : {len(self.trade_history)} trades clôturés trouvés.")
        except Exception as e:
            log.error(f"Erreur lors du chargement de l'historique de trades : {e}")

    def merge_broker_history(self, broker_trades: List[Dict[str, Any]]):
        """
        Fusionne l'historique du broker avec l'historique local en évitant les doublons.
        """
        if not broker_trades:
            return

        # Créer un ensemble d'identifiants uniques pour les trades locaux existants
        existing_keys = set()
        for t in self.trade_history:
            ts = t.get('timestamp', '')
            if isinstance(ts, str) and 'T' in ts:
                ts = ts.split('.')[0]  # ignorer les microsecondes
            key = (t.get('symbol'), t.get('side'), ts)
            existing_keys.add(key)

        new_trades = []
        for t in broker_trades:
            ts = t.get('timestamp')
            if isinstance(ts, datetime):
                ts_str = ts.isoformat().split('.')[0]
                t_copy = t.copy()
                t_copy['timestamp'] = ts.isoformat()
            elif isinstance(ts, str):
                ts_str = ts.split('.')[0]
                t_copy = t.copy()
            else:
                ts_str = str(ts)
                t_copy = t.copy()

            key = (t_copy.get('symbol'), t_copy.get('side'), ts_str)
            if key not in existing_keys:
                new_trades.append(t_copy)
                existing_keys.add(key)

        # Ajouter les nouveaux trades et retrier par timestamp
        self.trade_history.extend(new_trades)
        
        # S'assurer que le timestamp est analysable pour le tri
        def get_ts(x):
            return x.get('timestamp', '')

        self.trade_history.sort(key=get_ts)
        
        # Garder seulement les 100 derniers
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]

        log.info(f"Fusion de l'historique broker terminée. Total trades en mémoire : {len(self.trade_history)}")

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

        # Enregistrer le stop loss initial si non présent pour les calculs de R:R
        if 'initial_sl' not in position or position['initial_sl'] == 0:
            position['initial_sl'] = position.get('stop_loss', 0.0)


        try:
            # Calculer le P&L actuel et le pourcentage
            if position['side'] == 'LONG':
                raw_pnl = (current_price - position['entry_price']) * position['size']
                pnl_pct = (current_price / position['entry_price'] - 1) * 100
            else:  # SHORT
                raw_pnl = (position['entry_price'] - current_price) * position['size']
                pnl_pct = (position['entry_price'] / current_price - 1) * 100

            # ✅ BUG FIX #2 — Conversion du PnL latent (unrealized) en devise du compte
            # Même problème que pour les clôtures : les paires JPY retournent un PnL en Yen.
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
        if not position.get('trailing_stop_enabled', True):
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

            # Déterminer si le break-even doit se déclencher
            should_trigger = False
            if self.BE_DYN_RR:
                initial_sl = position.get('initial_sl', 0.0)
                if position['side'] == 'LONG':
                    initial_risk = position['entry_price'] - initial_sl
                    current_profit = current_price - position['entry_price']
                    should_trigger = (initial_risk > 0 and current_profit >= initial_risk * self.BE_DYN_RR_RATIO)
                else: # SHORT
                    initial_risk = initial_sl - position['entry_price']
                    current_profit = position['entry_price'] - current_price
                    should_trigger = (initial_risk > 0 and current_profit >= initial_risk * self.BE_DYN_RR_RATIO)
            else:
                if position['side'] == 'LONG':
                    profit_in_atr = (current_price - position['entry_price']) / atr_value
                    should_trigger = (profit_in_atr >= self.BE_ATR_MULT)
                else: # SHORT
                    profit_in_atr = (position['entry_price'] - current_price) / atr_value
                    should_trigger = (profit_in_atr >= self.BE_ATR_MULT)

            if should_trigger:
                position['break_even_activated'] = True
                if position['side'] == 'LONG':
                    old_sl = position.get('stop_loss', 0)
                    new_sl = position['entry_price'] * 1.0005  # Légèrement au-dessus pour couvrir les frais
                    if new_sl > old_sl:
                        position['stop_loss'] = new_sl
                        log.info(f"Break-even activé pour {symbol} (LONG): SL moved to {new_sl:.4f}")
                    else:
                        log.info(f"Break-even activé pour {symbol} (LONG) mais le trailing stop actuel ({old_sl:.4f}) est meilleur que BE ({new_sl:.4f})")
                else:  # SHORT
                    old_sl = position.get('stop_loss', float('inf'))
                    new_sl = position['entry_price'] * 0.9995  # Légèrement en-dessous pour couvrir les frais
                    if new_sl < old_sl or old_sl == 0:
                        position['stop_loss'] = new_sl
                        log.info(f"Break-even activé pour {symbol} (SHORT): SL moved to {new_sl:.4f}")
                    else:
                        log.info(f"Break-even activé pour {symbol} (SHORT) mais le trailing stop actuel ({old_sl:.4f}) est meilleur que BE ({new_sl:.4f})")



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