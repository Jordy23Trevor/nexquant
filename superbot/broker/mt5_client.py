"""
MetaTrader 5 (MT5) Forex Broker client for SuperBot.
Only compatible with Windows operating systems.
"""
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from superbot.broker.base import Broker
from superbot.config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, FOREX_DEFAULT_LEVERAGE

log = logging.getLogger("mt5_client")

# Import MT5 dynamically to prevent import crashes on non-Windows/non-installed environments
mt5 = None
try:
    import MetaTrader5 as mt5
except ImportError:
    pass


class MT5Client(Broker):
    """
    Client de trading universel connecté à un terminal MetaTrader 5 local.
    Permet de trader avec n'importe quel courtier supporté par MT5 (ex: IC Markets, Admiral, Pepperstone, etc.).
    """

    def __init__(self, **kwargs):
        self.login = MT5_LOGIN
        self.password = MT5_PASSWORD
        self.server = MT5_SERVER
        self.connected = False

        if mt5 is None:
            log.warning(
                "⚠️ La bibliothèque python 'MetaTrader5' n'est pas installée.\n"
                "Pour l'utiliser, lancez : pip install MetaTrader5 (uniquement sur Windows)."
            )
            return

        # Tenter d'initialiser MT5
        if not mt5.initialize():
            log.warning(f"⚠️ Échec de l'initialisation de MetaTrader5 : {mt5.last_error()}")
            return

        # Connexion au compte si spécifié
        if self.login > 0:
            authorized = mt5.login(login=self.login, password=self.password, server=self.server)
            if not authorized:
                log.error(
                    f"⚠️ Échec de la connexion au compte MT5 {self.login} sur le serveur {self.server} : "
                    f"{mt5.last_error()}"
                )
                return
        
        self.connected = True
        log.info(f"Connecté avec succès à MetaTrader5 (Compte: {self.login if self.login > 0 else 'Défaut'})")

    def get_default_instruments(self) -> List[str]:
        return ["EURUSD", "GBPUSD", "USDJPY"]

    def get_default_news_assets(self) -> List[str]:
        return ["EUR", "USD", "GBP", "JPY"]

    def get_asset_type(self) -> str:
        return "forex"

    def get_balance(self) -> float:
        if not self.connected or mt5 is None:
            return 0.0
        account_info = mt5.account_info()
        if account_info is not None:
            return float(account_info.balance)
        return 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        if not self.connected or mt5 is None:
            return {
                "balance": 0.0,
                "equity": 0.0,
                "unrealized_pnl": 0.0,
                "margin_used": 0.0,
                "free_margin": 0.0,
                "margin_level": 0.0,
                "open_positions": 0,
                "account_type": "MT5_DISCONNECTED",
                "leverage": FOREX_DEFAULT_LEVERAGE,
            }

        info = mt5.account_info()
        if info is not None:
            positions_count = mt5.positions_total()
            return {
                "balance": float(info.balance),
                "equity": float(info.equity),
                "unrealized_pnl": float(info.profit),
                "margin_used": float(info.margin),
                "free_margin": float(info.margin_free),
                "margin_level": float(info.margin_level) if info.margin > 0 else 0.0,
                "open_positions": int(positions_count),
                "account_type": f"MT5_{info.company}",
                "leverage": int(info.leverage),
            }

        return {
            "balance": 0.0,
            "equity": 0.0,
            "unrealized_pnl": 0.0,
            "margin_used": 0.0,
            "free_margin": 0.0,
            "margin_level": 0.0,
            "open_positions": 0,
            "account_type": "MT5_ERROR",
            "leverage": FOREX_DEFAULT_LEVERAGE,
        }

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Télécharge les bougies historiques depuis MT5."""
        if not self.connected or mt5 is None:
            return pd.DataFrame()

        normalized = self.normalize_symbol(symbol)
        mt5.symbol_select(normalized, True)

        tf_map = {
            "1m": mt5.TIMEFRAME_M1, "5m": mt5.TIMEFRAME_M5, "15m": mt5.TIMEFRAME_M15, "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1, "2h": mt5.TIMEFRAME_H2, "4h": mt5.TIMEFRAME_H4, "1d": mt5.TIMEFRAME_D1, "1w": mt5.TIMEFRAME_W1
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)

        rates = mt5.copy_rates_from_pos(normalized, mt5_tf, 0, limit)
        if rates is None or len(rates) == 0:
            log.error(f"MT5: Échec du téléchargement des bougies pour {normalized} : {mt5.last_error()}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('timestamp')
        df = df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'tick_volume': 'volume'
        })
        return df[['open', 'high', 'low', 'close', 'volume']]

    def get_current_price(self, symbol: str) -> float:
        if not self.connected or mt5 is None:
            return 0.0
        normalized = self.normalize_symbol(symbol)
        tick = mt5.symbol_info_tick(normalized)
        if tick is not None:
            return float((tick.bid + tick.ask) / 2)
        return 0.0

    def get_position(self, symbol: str) -> Dict[str, Any]:
        if not self.connected or mt5 is None:
            return self._empty_position()

        normalized = self.normalize_symbol(symbol)
        positions = mt5.positions_get(symbol=normalized)
        if positions is not None and len(positions) > 0:
            pos = positions[0]
            side = "LONG" if pos.type == 0 else "SHORT"
            size = float(pos.volume)
            entry_price = float(pos.price_open)
            current_price = float(pos.price_current)
            unrealized_pnl = float(pos.profit)

            return {
                "side": side,
                "size": size,
                "entry_price": entry_price,
                "mark_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "liquidation_price": None,
                "margin_used": 0.0,
            }

        return self._empty_position()

    def _empty_position(self) -> Dict[str, Any]:
        return {
            "side": None,
            "size": 0.0,
            "entry_price": 0.0,
            "mark_price": 0.0,
            "unrealized_pnl": 0.0,
            "liquidation_price": None,
            "margin_used": 0.0,
        }

    def close_position(self, symbol: str, reason: str = "") -> bool:
        if not self.connected or mt5 is None:
            return False

        normalized = self.normalize_symbol(symbol)
        positions = mt5.positions_get(symbol=normalized)
        if positions is None or len(positions) == 0:
            return False

        pos = positions[0]
        action = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            return False
        price = tick.bid if action == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": normalized,
            "volume": pos.volume,
            "type": action,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": 234567,
            "comment": f"Close: {reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            log.info(f"MT5: Position fermée avec succès pour {symbol}. Ticket: {pos.ticket}")
            return True
        else:
            log.error(f"MT5: Échec de fermeture de position pour {symbol} : {result.comment if result else mt5.last_error()}")
            return False

    def place_order(self, symbol: str, side: str, amount: float,
                   sl: float, tp: float, reduce_only: bool = False,
                   comment: str = "") -> bool:
        if not self.connected or mt5 is None:
            return False

        normalized = self.normalize_symbol(symbol)
        side_upper = side.upper()
        order_type = mt5.ORDER_TYPE_BUY if side_upper in ["BUY", "LONG"] else mt5.ORDER_TYPE_SELL

        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            log.error(f"MT5: Impossible de récupérer le tick actuel pour {normalized}")
            return False

        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": normalized,
            "volume": float(amount),
            "type": order_type,
            "price": price,
            "sl": float(sl) if sl and sl > 0 else 0.0,
            "tp": float(tp) if tp and tp > 0 else 0.0,
            "deviation": 20,
            "magic": 234567,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            log.info(f"MT5: Ordre placé avec succès sur {symbol} | Type: {side} | Volume: {amount}")
            return True
        else:
            log.error(f"MT5: Échec du placement d'ordre sur {symbol} : {result.comment if result else mt5.last_error()}")
            return False

    def modify_sl_tp(self, symbol: str, sl: float, tp: float) -> bool:
        if not self.connected or mt5 is None:
            return False

        normalized = self.normalize_symbol(symbol)
        positions = mt5.positions_get(symbol=normalized)
        if positions is None or len(positions) == 0:
            return False

        pos = positions[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": normalized,
            "position": pos.ticket,
            "sl": float(sl) if sl and sl > 0 else 0.0,
            "tp": float(tp) if tp and tp > 0 else 0.0,
        }

        result = mt5.order_send(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            log.info(f"MT5: SL/TP modifié avec succès pour {symbol} | SL: {sl} | TP: {tp}")
            return True
        else:
            log.error(f"MT5: Échec de la modification SL/TP pour {symbol} : {result.comment if result else mt5.last_error()}")
            return False

    def get_min_order_size(self, symbol: str) -> float:
        if not self.connected or mt5 is None:
            return 0.01
        normalized = self.normalize_symbol(symbol)
        info = mt5.symbol_info(normalized)
        if info is not None:
            return float(info.volume_min)
        return 0.01

    def get_step_size(self, symbol: str) -> float:
        if not self.connected or mt5 is None:
            return 0.01
        normalized = self.normalize_symbol(symbol)
        info = mt5.symbol_info(normalized)
        if info is not None:
            return float(info.volume_step)
        return 0.01

    def normalize_symbol(self, symbol: str) -> str:
        clean = symbol.strip().upper()
        if "/" in clean:
            return clean.replace("/", "")
        return clean
