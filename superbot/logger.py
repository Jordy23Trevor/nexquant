"""
╔═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╩
"""
import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import traceback

class SuperBotLogger:
    """
    Logger structuré pour le SuperBot Trading Unifié.
    Fournit un logging JSON structuré pour faciliter l'analyse post-trade.
    """

    def __init__(self, name: str = "SuperBot", log_level: str = "INFO",
                 log_dir: str = "logs", max_bytes: int = 10*1024*1024,
                 backup_count: int = 5):
        """
        Initialise le logger structuré.

        Args:
            name: Nom du logger
            log_level: Niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Répertoire où stocker les fichiers de log
            max_bytes: Taille maximale d'un fichier de log avant rotation
            backup_count: Nombre de fichiers de sauvegarde à garder
        """
        self.name = name
        self.log_level = getattr(logging, log_level.upper())
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # Créer le répertoire de logs s'il n'existe pas
        os.makedirs(self.log_dir, exist_ok=True)

        # Configurer le logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)
        self.logger.handlers.clear()  # Éviter les doublons

        # Formatter JSON structuré
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "module": "%(module)s", '
            '"function": "%(funcName)s", "line": %(lineno)d, '
            '"message": %(message)s}'
        )

        # Handler pour fichier avec rotation
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, f"{name.lower()}.log"),
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)

        # Handler pour console (lisible par les humains)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
        )
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        self.logger.info(f"Logger '{name}' initialisé - Niveau: {log_level}")

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log un message de niveau DEBUG."""
        self._log(logging.DEBUG, message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log un message de niveau INFO."""
        self._log(logging.INFO, message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log un message de niveau WARNING."""
        self._log(logging.WARNING, message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None,
              exc_info: bool = False):
        """Log un message de niveau ERROR."""
        self._log(logging.ERROR, message, extra, exc_info)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None,
                 exc_info: bool = False):
        """Log un message de niveau CRITICAL."""
        self._log(logging.CRITICAL, message, extra, exc_info)

    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None,
             exc_info: bool = False):
        """
        Méthode interne de logging qui supporte les données extra structurées.

        Args:
            level: Niveau de logging
            message: Message à logger
            extra: Données supplémentaires à inclure dans le log JSON
            exc_info: Inclure les informations d'exception
        """
        if extra:
            # Créer un message JSON avec les données extra
            extra_json = json.dumps(extra, default=str)
            formatted_message = f'{message} | extra: {extra_json}'
        else:
            formatted_message = message

        # Pour les niveaux ERROR et CRITICAL, ajouter la trace si demandé
        if exc_info and level >= logging.ERROR:
            self.logger.log(level, formatted_message, exc_info=True)
        else:
            self.logger.log(level, formatted_message)

    def log_trade(self, symbol: str, side: str, size: float, entry_price: float,
                  stop_loss: float, take_profit: float, strategy_score: float,
                  market_regime: str, order_id: Optional[str] = None):
        """
        Log un trade exécuté de manière structurée.

        Args:
            symbol: Symbole de l'instrument
            side: Côté du trade ('buy' ou 'sell')
            size: Taille de la position
            entry_price: Prix d'entrée
            stop_loss: Niveau de stop loss
            take_profit: Niveau de take profit
            strategy_score: Score de la stratégie qui a généré le signal
            market_regime: Régime de marché détecté
            order_id: ID de l'ordre broker (optionnel)
        """
        trade_data = {
            'event_type': 'TRADE_EXECUTED',
            'symbol': symbol,
            'side': side,
            'size': size,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'strategy_score': strategy_score,
            'market_regime': market_regime,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'order_id': order_id
        }

        self.info(f"Trade exécuté: {symbol} {side.upper()} {size}", extra=trade_data)

    def log_signal(self, symbol: str, should_long: bool, should_short: bool,
                   total_score: float, market_regime: str, rr_ratio: float,
                   entry_price: float, sl_price: float, tp_price: float):
        """
        Log un signal de trading généré.

        Args:
            symbol: Symbole de l'instrument
            should_long: True si signal d'achat
            should_short: True si signal de vente
            total_score: Score total de la stratégie
            market_regime: Régime de marché détecté
            rr_ratio: Ratio risque/récompense
            entry_price: Prix d'entrée proposé
            sl_price: Prix de stop loss proposé
            tp_price: Prix de take profit proposé
        """
        signal_data = {
            'event_type': 'TRADING_SIGNAL',
            'symbol': symbol,
            'should_long': should_long,
            'should_short': should_short,
            'total_score': total_score,
            'market_regime': market_regime,
            'risk_reward_ratio': rr_ratio,
            'entry_price': entry_price,
            'stop_loss': sl_price,
            'take_profit': tp_price,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        self.info(f"Signal généré: {symbol} - Score: {total_score:.1f} - {market_regime}",
                  extra=signal_data)

    def log_risk_metrics(self, account_balance: float, daily_pnl: float,
                         monthly_pnl: float, drawdown_pct: float,
                         open_positions: int, win_rate: float):
        """
        Log les métriques de risque.

        Args:
            account_balance: Solde du compte
            daily_pnl: P&L journalier
            monthly_pnl: P&L mensuel
            drawdown_pct: Drawdown en pourcentage
            open_positions: Nombre de positions ouvertes
            win_rate: Taux de réussite
        """
        risk_data = {
            'event_type': 'RISK_METRICS',
            'account_balance': account_balance,
            'daily_pnl': daily_pnl,
            'monthly_pnl': monthly_pnl,
            'drawdown_percentage': drawdown_pct,
            'open_positions': open_positions,
            'win_rate': win_rate,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        self.info(f"Métriques de risque - Balance: {account_balance:.2f} - DD: {drawdown_pct:.2f}%",
                  extra=risk_data)

    def log_news_event(self, title: str, source: str, impact: str,
                       sentiment_score: float, symbols_affected: list):
        """
        Log un événement de nouvelle.

        Args:
            title: Titre de la nouvelle
            source: Source de la nouvelle
            impact: Niveau d'impact (LOW, MEDIUM, HIGH)
            sentiment_score: Score de sentiment (-1 à +1)
            symbols_affected: Liste des symboles affectés
        """
        news_data = {
            'event_type': 'NEWS_EVENT',
            'title': title,
            'source': source,
            'impact': impact,
            'sentiment_score': sentiment_score,
            'symbols_affected': symbols_affected,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        self.info(f"Événement de nouvelles: {title} - Impact: {impact}", extra=news_data)

    def log_error_with_context(self, message: str, context: Dict[str, Any],
                               exc: Optional[Exception] = None):
        """
        Log une erreur avec contexte supplémentaire.

        Args:
            message: Message d'erreur
            context: Contexte additionnel (symbol, fonction, etc.)
            exc: Exception originale (optionnel)
        """
        error_data = {
            'event_type': 'ERROR',
            'message': message,
            'context': context,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        if exc:
            error_data['exception_type'] = type(exc).__name__
            error_data['exception_message'] = str(exc)

        self.error(f"Erreur: {message}", extra=error_data, exc_info=True if exc else False)


# Instance globale du logger pour un accès facile
def setup_logging(name: str = "SuperBot", log_level: str = "INFO",
                  log_dir: str = "logs") -> SuperBotLogger:
    """
    Configure et retourne une instance du logger structuré.

    Args:
        name: Nom du logger
        log_level: Niveau de logging
        log_dir: Répertoire des logs

    Returns:
        Instance configurée de SuperBotLogger
    """
    return SuperBotLogger(name=name, log_level=log_level, log_dir=log_dir)


# Pour une utilisation directe et simple
def get_logger(name: str = "SuperBot") -> logging.Logger:
    """
    Retourne un logger standard (pour compatibilité avec les modules existants).

    Args:
        name: Nom du logger

    Returns:
        Logger standard de Python
    """
    return logging.getLogger(name)


# Export des classes publiques
__all__ = ['SuperBotLogger', 'setup_logging', 'get_logger']