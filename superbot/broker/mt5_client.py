"""
MetaTrader 5 (MT5) broker client.
Associated with Fusion Markets.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from superbot.broker.base import Broker
from superbot.config import (
    MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH
)

log = logging.getLogger("mt5_client")


class MT5Client(Broker):
    """
    Client Broker MetaTrader 5 connecté aux serveurs de Fusion Markets.
    """

    def __init__(self):
        if mt5 is None:
            raise ImportError(
                "Le module python MetaTrader5 n'est pas installé.\n"
                "Veuillez l'installer via 'pip install MetaTrader5' (système Windows uniquement)."
            )

        log.info(f"Initialisation de MetaTrader 5 (Serveur: {MT5_SERVER})...")
        
        # Paramètres d'initialisation
        init_kwargs = {}
        if MT5_PATH:
            import os
            resolved_path = MT5_PATH
            if os.path.isdir(resolved_path):
                resolved_path = os.path.join(resolved_path, "terminal64.exe")
            init_kwargs["path"] = resolved_path
        if MT5_LOGIN > 0:
            init_kwargs["login"] = MT5_LOGIN
        if MT5_PASSWORD:
            init_kwargs["password"] = MT5_PASSWORD
        if MT5_SERVER:
            init_kwargs["server"] = MT5_SERVER

        # Initialiser la connexion au terminal MT5
        if not mt5.initialize(**init_kwargs):
            error_code = mt5.last_error()
            log.error(f"Échec de la connexion à MT5 : {error_code}")
            raise RuntimeError(
                f"Échec de l'initialisation de MT5 (code d'erreur: {error_code}).\n"
                "Veuillez vérifier que le terminal MT5 Fusion Markets est ouvert et "
                "que les informations de connexion (Login, Serveur) sont correctes."
            )

        # Connexion au compte de trading
        if MT5_LOGIN > 0:
            authorized = mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
            if not authorized:
                error_code = mt5.last_error()
                log.error(f"Échec de l'authentification MT5 pour le compte {MT5_LOGIN} : {error_code}")
                raise RuntimeError(f"Échec de l'authentification MT5 (compte: {MT5_LOGIN}, code d'erreur: {error_code})")

        acc_info = mt5.account_info()
        if acc_info:
            log.info(f"Connecté avec succès à MT5. Compte: {acc_info.login} | Solde: {acc_info.balance} {acc_info.currency}")
        else:
            log.warning("Connecté à MT5, mais impossible de récupérer les informations du compte.")

    def get_default_instruments(self) -> List[str]:
        return ["EURUSD", "GBPUSD", "USDJPY"]

    def get_default_news_assets(self) -> List[str]:
        return ["EUR", "USD", "GBP", "JPY"]

    def get_asset_type(self) -> str:
        return "forex"

    def get_balance(self) -> float:
        """Retourne le solde disponible."""
        acc_info = mt5.account_info()
        return acc_info.balance if acc_info else 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        """Résumé complet du compte."""
        acc_info = mt5.account_info()
        if not acc_info:
            return {
                "balance": 0.0,
                "equity": 0.0,
                "unrealized_pnl": 0.0,
                "margin_used": 0.0,
                "free_margin": 0.0,
                "margin_level": 0.0,
                "open_positions": 0,
                "account_type": "MT5_FUSION_MARKETS",
            }

        positions = mt5.positions_get()
        open_positions_count = len(positions) if positions else 0

        # Margin level calculation (equity / margin * 100)
        margin_level = acc_info.margin_level if acc_info.margin > 0 else 0.0

        return {
            "balance": acc_info.balance,
            "equity": acc_info.equity,
            "unrealized_pnl": acc_info.profit,
            "margin_used": acc_info.margin,
            "free_margin": acc_info.margin_free,
            "margin_level": margin_level,
            "open_positions": open_positions_count,
            "account_type": "MT5_REAL" if acc_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_REAL else "MT5_DEMO",
            "company": acc_info.company
        }

    def _get_mt5_timeframe(self, timeframe: str) -> int:
        """Associe un timeframe string à la constante correspondante MT5."""
        tf_map = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1,
            "2h": mt5.TIMEFRAME_H2,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1,
            "1w": mt5.TIMEFRAME_W1,
        }
        return tf_map.get(timeframe.lower(), mt5.TIMEFRAME_H1)

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Récupère les bougies historiques depuis MT5."""
        symbol = self.normalize_symbol(symbol)
        mt5_tf = self._get_mt5_timeframe(timeframe)
        
        # S'assurer que le symbole est visible/sélectionné dans le Market Watch de MT5
        mt5.symbol_select(symbol, True)

        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, limit)
        if rates is None or len(rates) == 0:
            log.warning(f"Impossible de récupérer les bougies de {symbol} depuis MT5 (erreur: {mt5.last_error()})")
            return pd.DataFrame()

        # Convertir en DataFrame pandas
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('time')
        df = df.rename(columns={
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "tick_volume": "volume"
        })
        return df[['open', 'high', 'low', 'close', 'volume']]

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """
        Retourne la position ouverte sur un symbole.
        S'il y a plusieurs positions (Hedging), nous les combinons/agrégons.
        """
        symbol = self.normalize_symbol(symbol)
        positions = mt5.positions_get(symbol=symbol)
        
        if not positions or len(positions) == 0:
            return {}

        total_volume = 0.0
        weighted_entry = 0.0
        total_profit = 0.0
        
        # Trouver la direction dominante ou utiliser la première position pour définir le type principal
        first_pos = positions[0]
        dominant_side = "LONG" if first_pos.type == mt5.POSITION_TYPE_BUY else "SHORT"
        
        sl = first_pos.sl
        tp = first_pos.tp

        for pos in positions:
            pos_side = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"
            if pos_side == dominant_side:
                total_volume += pos.volume
                weighted_entry += pos.price_open * pos.volume
            else:
                total_volume -= pos.volume
                weighted_entry -= pos.price_open * pos.volume
            total_profit += pos.profit

        if total_volume == 0:
            return {}

        if total_volume < 0:
            dominant_side = "SHORT" if dominant_side == "LONG" else "LONG"
            total_volume = abs(total_volume)

        avg_entry = abs(weighted_entry / total_volume) if total_volume > 0 else 0.0
        
        tick = mt5.symbol_info_tick(symbol)
        mark_price = (tick.bid + tick.ask) / 2 if tick else avg_entry

        return {
            "ticket": first_pos.ticket,
            "side": dominant_side,
            "size": total_volume,
            "entry_price": avg_entry,
            "mark_price": mark_price,
            "unrealized_pnl": total_profit,
            "stop_loss": sl,
            "take_profit": tp,
            "liquidation_price": None,
            "margin_used": 0.0,
        }

    def close_position(self, symbol: str, reason: str = "") -> bool:
        """Ferme toutes les positions ouvertes sur un symbole."""
        symbol = self.normalize_symbol(symbol)
        positions = mt5.positions_get(symbol=symbol)
        if not positions or len(positions) == 0:
            log.info(f"Aucune position ouverte à fermer pour {symbol} sur MT5.")
            return False

        success = True
        for pos in positions:
            ticket = pos.ticket
            volume = pos.volume
            side = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"

            # Déterminer le type d'ordre opposé pour fermer la position
            order_type = mt5.ORDER_TYPE_SELL if side == "LONG" else mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                log.error(f"Impossible d'obtenir les prix tick pour fermer la position #{ticket}")
                success = False
                continue
                
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 10099,
                "comment": f"Close #{ticket} - {reason}"[:31],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            log.info(f"Fermeture position MT5 #{ticket} sur {symbol} (Taille: {volume}, Type: {side})...")
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error_code = mt5.last_error()
                log.error(f"Échec de la fermeture de position #{ticket} sur {symbol}: {result.comment if result else ''} (code: {error_code})")
                success = False
            else:
                log.info(f"Position #{ticket} sur {symbol} fermée avec succès.")
                
        return success

    def place_order(self, symbol: str, side: str, amount: float,
                   sl: float, tp: float, reduce_only: bool = False,
                   comment: str = "") -> bool:
        """Place un ordre au marché avec stop loss et take profit."""
        symbol = self.normalize_symbol(symbol)
        side_upper = side.upper()

        # Ne pas ouvrir si reduce_only est requis mais pas de position
        if reduce_only:
            pos = self.get_position(symbol)
            if not pos or pos["size"] == 0:
                log.warning(f"Ordre reduce_only demandé sur {symbol} mais aucune position active.")
                return False

        # Vérifier si le symbole est sélectionné
        mt5.symbol_select(symbol, True)

        # Déterminer les prix d'entrée
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            log.error(f"Impossible d'obtenir le prix tick actuel pour {symbol}.")
            return False

        if side_upper in ["BUY", "LONG"]:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif side_upper in ["SELL", "SHORT"]:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            log.error(f"Type d'action d'ordre inconnu : {side}")
            return False

        # S'assurer que le volume respecte les contraintes du courtier
        amount = max(amount, self.get_min_order_size(symbol))
        step = self.get_step_size(symbol)
        amount = round(amount / step) * step

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(amount),
            "type": order_type,
            "price": price,
            "sl": float(sl) if sl > 0 else 0.0,
            "tp": float(tp) if tp > 0 else 0.0,
            "deviation": 20,
            "magic": 10099,
            "comment": str(comment or f"SuperBot order - {side_upper}")[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        log.info(f"Envoi de l'ordre MT5 : {side_upper} {amount} {symbol} @ {price:.5f} (SL: {sl:.5f}, TP: {tp:.5f})")
        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_code = mt5.last_error()
            comment_err = result.comment if result else "Pas de réponse du serveur MT5"
            log.error(f"Échec de l'ordre de marché sur {symbol}: {comment_err} (code ret: {result.retcode if result else 'N/A'}, err mt5: {error_code})")
            return False

        log.info(f"Ordre MT5 exécuté avec succès. Ticket: {result.order}")
        return True

    def modify_sl_tp(self, symbol: str, sl: float, tp: float) -> bool:
        """Modifie le SL/TP de toutes les positions existantes sur un symbole."""
        symbol = self.normalize_symbol(symbol)
        positions = mt5.positions_get(symbol=symbol)
        if not positions or len(positions) == 0:
            log.warning(f"Impossible de modifier le SL/TP: aucune position sur {symbol}")
            return False

        success = True
        for pos in positions:
            ticket = pos.ticket
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": float(sl) if sl > 0 else 0.0,
                "tp": float(tp) if tp > 0 else 0.0,
            }

            log.info(f"Modification SL/TP position MT5 #{ticket} ({symbol}) -> SL: {sl:.5f}, TP: {tp:.5f}")
            result = mt5.order_send(request)

            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error_code = mt5.last_error()
                log.error(f"Échec de la modification du SL/TP sur #{ticket} ({symbol}): {result.comment if result else ''} (code err: {error_code})")
                success = False
            else:
                log.info(f"Modification SL/TP sur position #{ticket} effectuée avec succès.")
                
        return success

    def get_current_price(self, symbol: str) -> float:
        """Retourne le dernier prix (mid price)."""
        symbol = self.normalize_symbol(symbol)
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return 0.0
        return (tick.bid + tick.ask) / 2

    def get_min_order_size(self, symbol: str) -> float:
        symbol = self.normalize_symbol(symbol)
        info = mt5.symbol_info(symbol)
        return info.volume_min if info else 0.01

    def get_step_size(self, symbol: str) -> float:
        symbol = self.normalize_symbol(symbol)
        info = mt5.symbol_info(symbol)
        return info.volume_step if info else 0.01

    def normalize_symbol(self, symbol: str) -> str:
        """
        Adapte le symbole (ex: EUR/USD -> EURUSD).
        Fusion Markets utilise des symboles sans barre oblique et des codes spécifiques.
        """
        clean = symbol.strip().upper().replace("/", "")
        # Correspondance des matières premières Fusion Markets
        if clean in ["WTIUSD", "WTI"]:
            return "XTIUSD"
        if clean in ["BRENTUSD", "BRENT", "BRNUSD"]:
            return "XBRUSD"
        return clean

    def __del__(self):
        """Libère le terminal à la suppression de l'objet client."""
        if mt5 is not None:
            try:
                mt5.shutdown()
            except Exception:
                pass
