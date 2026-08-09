import logging
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import math
from typing import Dict, Any, Tuple, Optional, List
log = logging.getLogger(__name__)


def record_trade(rm, trade_record: Dict[str, Any]):
    """
    Enregistre un trade clôturé dans l'historique pour le calcul de Kelly et l'analyse.
    Écrit également le trade dans un fichier JSON Lines pour persistance.

    Args:
        trade_record: Dictionnaire contenant les détails du trade
    """
    try:
        # Ajouter un timestamp de clôture si pas présent
        # BUG-A13 FIX: Utiliser datetime.now(timezone.utc) pour cohérence timezone
        if 'timestamp' not in trade_record:
            trade_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        # S'assurer que le timestamp est une string pour la sérialisation JSON
        elif isinstance(trade_record['timestamp'], datetime):
            trade_record['timestamp'] = trade_record['timestamp'].isoformat()

        # Ajouter à l'historique uniquement si le trade est clôturé
        is_closed = trade_record.get('status') == 'closed' or trade_record.get('pnl') is not None
        if is_closed:
            rm.trade_history.append(trade_record)

            # Garder seulement les 100 derniers trades pour éviter l'accumulation illimitée
            if len(rm.trade_history) > 100:
                rm.trade_history = rm.trade_history[-100:]

        # Mise à jour des pertes consécutives
        symbol = trade_record.get('symbol')
        if symbol and trade_record.get('status') == 'closed' and trade_record.get('pnl') is not None:
            if trade_record.get('pnl', 0) < 0:
                rm.consecutive_losses[symbol] = rm.consecutive_losses.get(symbol, 0) + 1
                log.info(f"📉 Perte enregistrée pour {symbol}. Série de pertes: {rm.consecutive_losses[symbol]}")
            else:
                rm.consecutive_losses[symbol] = 0
                log.debug(f"📈 Gain enregistré pour {symbol}. Réinitialisation de la série de pertes.")
            # ✅ BUG FIX #5 — Enregistrer l'heure de clôture pour le cooldown
            # BUG-01 FIX: Utiliser datetime.now(timezone.utc) pour cohérence avec le cooldown check
            rm.last_trade_close_time[symbol] = datetime.now(timezone.utc)

        # BUG-09 FIX: Écrire dans le fichier JSON Lines UNIQUEMENT pour les trades clôturés
        # Les trades ouverts ne doivent pas polluer le fichier JSONL
        if is_closed:
            from superbot.config import TRADE_LOG_FILE
            trades_file = str(TRADE_LOG_FILE)
            log_dir = os.path.dirname(trades_file)
            os.makedirs(log_dir, exist_ok=True)
            with open(trades_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(trade_record, ensure_ascii=False, default=str) + '\n')

        log.debug(f"Trade enregistré: {trade_record.get('symbol', 'Unknown')} | P&L: {trade_record.get('pnl', 0):.2f}")

    except Exception as e:
        log.error(f"Erreur lors de l'enregistrement du trade: {e}")

def load_trade_history_from_disk(rm):
    """
    Charge l'historique des trades enregistrés depuis le fichier JSON Lines.
    Ne charge que les trades CLÔTURÉS avec un P&L valide pour éviter les erreurs Kelly.
    """
    try:
        from superbot.config import TRADE_LOG_FILE
        trades_file = str(TRADE_LOG_FILE)
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
        rm.trade_history = loaded_trades[-100:]
        log.info(f"Historique de trading chargé depuis le disque : {len(rm.trade_history)} trades clôturés trouvés.")
    except Exception as e:
        log.error(f"Erreur lors du chargement de l'historique de trades : {e}")

def merge_broker_history(rm, broker_trades: List[Dict[str, Any]]):
    """
    Fusionne l'historique du broker avec l'historique local en évitant les doublons.
    """
    if not broker_trades:
        return

    # Créer un ensemble d'identifiants uniques pour les trades locaux existants
    existing_keys = set()
    for t in rm.trade_history:
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
    rm.trade_history.extend(new_trades)

    # S'assurer que le timestamp est analysable pour le tri
    def get_ts(x):
        return x.get('timestamp', '')

    rm.trade_history.sort(key=get_ts)

    # Garder seulement les 100 derniers
    if len(rm.trade_history) > 100:
        rm.trade_history = rm.trade_history[-100:]

    log.info(f"Fusion de l'historique broker terminée. Total trades en mémoire : {len(rm.trade_history)}")