"""
XTB broker client.
Connects via email (userId) and password.
Supports xStation API (xAPI) JSON protocol over WebSocket.
"""
import logging
import json
import time
import ssl
import socket
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd

try:
    import websocket
except ImportError:
    websocket = None

from superbot.broker.base import Broker
from superbot.config import (
    XTB_EMAIL, XTB_PASSWORD, XTB_SERVER
)

log = logging.getLogger("xtb_client")


class XTBClient(Broker):
    """
    Client Broker XTB (xStation5 xAPI v2.5.0) via WebSocket.
    """

    def __init__(self):
        self.email = XTB_EMAIL
        self.password = XTB_PASSWORD
        self.server = XTB_SERVER or "demo"
        self.ssid = None
        self.ws = None
        self._price_cache = {}
        self._last_update = {}

        if not self.email or not self.password:
            log.warning("Identifiants XTB non définis. Passage en mode simulation XTB.")
            self.simulation_mode = True
            return

        self.simulation_mode = False
        log.info(f"Connexion à XTB ({self.server.upper()}) avec l'email {self.email}...")

        # Résoudre l'URL WebSocket
        if self.server.lower() == "real":
            self.ws_url = "wss://ws.xtb.com/real"
        else:
            self.ws_url = "wss://ws.xtb.com/demo"

        try:
            self._connect()
        except Exception as e:
            log.error(f"Impossible de se connecter à XTB : {e}. Passage en mode simulation.")
            self.simulation_mode = True

    def _connect(self):
        if websocket is None:
            raise ImportError("Le package python-websocket-client est requis pour XTB. Lancez 'pip install websocket-client'.")

        self.ws = websocket.create_connection(self.ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})
        
        # Authentification
        login_req = {
            "command": "login",
            "arguments": {
                "userId": self.email,
                "password": self.password
            }
        }
        self.ws.send(json.dumps(login_req))
        response = json.loads(self.ws.recv())
        
        if response.get("status") is True:
            self.ssid = response.get("streamSessionId")
            log.info(f"Connecté avec succès à XTB (Session: {self.ssid})")
        else:
            reason = response.get("errorDescr", "Raison inconnue")
            raise RuntimeError(f"Échec de la connexion XTB : {reason}")

    def _send_command(self, command: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Envoie une commande synchrone à l'API XTB."""
        if self.simulation_mode:
            return {"status": False, "error": "Simulation Mode"}

        req = {"command": command}
        if arguments:
            req["arguments"] = arguments

        try:
            self.ws.send(json.dumps(req))
            res = json.loads(self.ws.recv())
            return res
        except Exception as e:
            log.error(f"Erreur de communication API XTB command '{command}' : {e}")
            # Reconnexion automatique si la socket a expiré
            try:
                log.info("Tentative de reconnexion à XTB...")
                self._connect()
                self.ws.send(json.dumps(req))
                res = json.loads(self.ws.recv())
                return res
            except Exception as e2:
                log.error(f"Échec de la reconnexion XTB : {e2}")
                self.simulation_mode = True
                return {"status": False, "error": str(e2)}

    def get_default_instruments(self) -> List[str]:
        return ["EURUSD", "GBPUSD", "USDJPY"]

    def get_default_news_assets(self) -> List[str]:
        return ["EUR", "USD", "GBP", "JPY"]

    def get_asset_type(self) -> str:
        return "forex"

    def get_balance(self) -> float:
        """Retourne le solde disponible (equity)."""
        if self.simulation_mode:
            return 10000.0

        res = self._send_command("getMarginLevel")
        if res.get("status") is True:
            return float(res["returnData"].get("equity", 0.0))
        return 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        """Résumé complet du compte."""
        if self.simulation_mode:
            return {
                "balance": 10000.0,
                "equity": 10000.0,
                "unrealized_pnl": 0.0,
                "margin_used": 0.0,
                "free_margin": 10000.0,
                "margin_level": 0.0,
                "open_positions": 0,
                "account_type": "XTB_SIMULATED",
            }

        res = self._send_command("getMarginLevel")
        balance = 0.0
        equity = 0.0
        margin = 0.0
        free_margin = 0.0
        margin_level = 0.0

        if res.get("status") is True:
            data = res["returnData"]
            balance = float(data.get("balance", 0.0))
            equity = float(data.get("equity", 0.0))
            margin = float(data.get("margin", 0.0))
            free_margin = float(data.get("freeMargin", 0.0))
            margin_level = float(data.get("marginLevel", 0.0))

        trades = self._send_command("getTrades", {"openedOnly": True})
        open_positions = len(trades.get("returnData", [])) if trades.get("status") is True else 0

        return {
            "balance": balance,
            "equity": equity,
            "unrealized_pnl": equity - balance,
            "margin_used": margin,
            "free_margin": free_margin,
            "margin_level": margin_level,
            "open_positions": open_positions,
            "account_type": f"XTB_{self.server.upper()}",
        }

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Récupère les bougies historiques depuis XTB."""
        symbol = self.normalize_symbol(symbol)
        
        # Traduction du timeframe
        tf_map = {
            "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "2h": 120, "4h": 240, "1d": 1440, "1w": 10080
        }
        period = tf_map.get(timeframe.lower(), 60)

        if self.simulation_mode:
            # Générer des données simulées
            return self._generate_simulated_candles(symbol, timeframe, limit)

        # Calculer le timestamp de début
        minutes_total = period * limit
        start_time = datetime.now() - timedelta(minutes=minutes_total)
        start_ms = int(start_time.timestamp() * 1000)

        args = {
            "info": {
                "period": period,
                "start": start_ms,
                "symbol": symbol
            }
        }
        
        res = self._send_command("getChartLastRequest", args)
        if res.get("status") is True:
            rate_infos = res["returnData"].get("rateInfos", [])
            if not rate_infos:
                return pd.DataFrame()

            # XTB renvoie des valeurs codées par rapport à un point de référence (ctm)
            df_data = []
            for r in rate_infos:
                t = pd.to_datetime(r["ctm"], unit='ms')
                o = float(r["open"])
                # XTB utilise des offsets de pips entiers pour high/low/close par rapport à open
                h = float(o + r["high"])
                l = float(o + r["low"])
                c = float(o + r["close"])
                v = float(r["vol"])
                df_data.append({"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v})

            df = pd.DataFrame(df_data)
            df = df.set_index("time")
            return df.tail(limit)

        return pd.DataFrame()

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """Retourne les détails d'une position ouverte."""
        symbol = self.normalize_symbol(symbol)
        if self.simulation_mode:
            return {}

        res = self._send_command("getTrades", {"openedOnly": True})
        if res.get("status") is True:
            for trade in res.get("returnData", []):
                if trade.get("symbol") == symbol:
                    # cmd: 0 pour BUY, 1 pour SELL
                    side = "LONG" if trade.get("cmd") == 0 else "SHORT"
                    return {
                        "ticket": trade.get("position"),
                        "side": side,
                        "size": trade.get("volume"),
                        "entry_price": trade.get("open_price"),
                        "mark_price": trade.get("close_price"),
                        "unrealized_pnl": trade.get("profit"),
                        "stop_loss": trade.get("sl"),
                        "take_profit": trade.get("tp"),
                        "liquidation_price": None,
                        "margin_used": 0.0,
                    }
        return {}

    def close_position(self, symbol: str, reason: str = "") -> bool:
        """Ferme la position ouverte sur un symbole."""
        symbol = self.normalize_symbol(symbol)
        pos = self.get_position(symbol)
        if not pos or "ticket" not in pos:
            log.info(f"Aucune position ouverte à fermer pour {symbol} sur XTB.")
            return False

        if self.simulation_mode:
            log.info(f"[Simulation] Fermeture de position sur {symbol}")
            return True

        ticket = pos["ticket"]
        volume = pos["size"]
        # cmd: 0 pour BUY, 1 pour SELL (on ferme avec l'opposé)
        cmd = 1 if pos["side"] == "LONG" else 0

        args = {
            "tradeTransInfo": {
                "cmd": cmd,
                "customComment": f"Close {reason}",
                "expiration": 0,
                "offset": 0,
                "order": ticket,
                "price": pos["mark_price"],
                "sl": 0.0,
                "tp": 0.0,
                "symbol": symbol,
                "type": 4,  # TYPE_CLOSE
                "volume": volume
            }
        }

        res = self._send_command("tradeTransaction", args)
        if res.get("status") is True:
            order_id = res["returnData"].get("order")
            log.info(f"Requête de fermeture XTB envoyée (Order ID: {order_id})")
            return True
        else:
            log.error(f"Échec de la fermeture de position XTB: {res.get('errorDescr')}")
            return False

    def place_order(self, symbol: str, side: str, amount: float,
                   sl: float, tp: float, reduce_only: bool = False,
                   comment: str = "") -> bool:
        """Place un ordre au marché avec stop loss et take profit."""
        symbol = self.normalize_symbol(symbol)
        side_upper = side.upper()

        if self.simulation_mode:
            log.info(f"[Simulation] Exécution ordre XTB : {side_upper} {amount} {symbol}")
            return True

        # Déterminer cmd (0 = BUY, 1 = SELL)
        cmd = 0 if side_upper in ["BUY", "LONG"] else 1
        price = self.get_current_price(symbol)

        args = {
            "tradeTransInfo": {
                "cmd": cmd,
                "customComment": comment or "SuperBot Trade",
                "expiration": 0,
                "offset": 0,
                "order": 0,
                "price": price,
                "sl": float(sl) if sl > 0 else 0.0,
                "tp": float(tp) if tp > 0 else 0.0,
                "symbol": symbol,
                "type": 0,  # TYPE_BUY/TYPE_SELL
                "volume": amount
            }
        }

        res = self._send_command("tradeTransaction", args)
        if res.get("status") is True:
            order_id = res["returnData"].get("order")
            log.info(f"Ordre XTB placé avec succès. Ticket: {order_id}")
            return True
        else:
            log.error(f"Échec de placement d'ordre XTB: {res.get('errorDescr')}")
            return False

    def modify_sl_tp(self, symbol: str, sl: float, tp: float) -> bool:
        """Modifie le SL/TP d'une position existante."""
        symbol = self.normalize_symbol(symbol)
        pos = self.get_position(symbol)
        if not pos or "ticket" not in pos:
            return False

        if self.simulation_mode:
            log.info(f"[Simulation] Modification SL/TP XTB sur {symbol} -> SL: {sl}, TP: {tp}")
            return True

        ticket = pos["ticket"]
        cmd = 0 if pos["side"] == "LONG" else 1

        args = {
            "tradeTransInfo": {
                "cmd": cmd,
                "customComment": "Modify SL/TP",
                "expiration": 0,
                "offset": 0,
                "order": ticket,
                "price": pos["entry_price"],
                "sl": float(sl) if sl > 0 else 0.0,
                "tp": float(tp) if tp > 0 else 0.0,
                "symbol": symbol,
                "type": 3,  # TYPE_MODIFY
                "volume": pos["size"]
            }
        }

        res = self._send_command("tradeTransaction", args)
        if res.get("status") is True:
            log.info(f"Modification SL/TP XTB enregistrée pour le ticket {ticket}.")
            return True
        return False

    def get_current_price(self, symbol: str) -> float:
        """Retourne le dernier prix."""
        symbol = self.normalize_symbol(symbol)
        if self.simulation_mode:
            # Générer un prix simulé
            return self._generate_simulated_price(symbol)

        res = self._send_command("getSymbol", {"symbol": symbol})
        if res.get("status") is True:
            data = res["returnData"]
            ask = float(data.get("ask", 0.0))
            bid = float(data.get("bid", 0.0))
            return (ask + bid) / 2
        return 0.0

    def get_min_order_size(self, symbol: str) -> float:
        return 0.01

    def get_step_size(self, symbol: str) -> float:
        return 0.01

    def normalize_symbol(self, symbol: str) -> str:
        """XTB utilise des symboles sans slash."""
        clean = symbol.strip().upper()
        return clean.replace("/", "")

    def _generate_simulated_price(self, symbol: str) -> float:
        now = datetime.now(timezone.utc)
        if symbol in self._last_update:
            time_diff = (now - self._last_update[symbol]).total_seconds()
            if time_diff < 5:
                return self._price_cache[symbol]

        base_prices = {"EURUSD": 1.0800, "GBPUSD": 1.2600, "USDJPY": 149.50}
        base = base_prices.get(symbol, 1.0000)
        
        import random
        price = base * random.uniform(0.995, 1.005)
        self._price_cache[symbol] = price
        self._last_update[symbol] = now
        return price

    def _generate_simulated_candles(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        import numpy as np
        
        timeframe_deltas = {
            "1m": timedelta(minutes=1), "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15), "30m": timedelta(minutes=30),
            "1h": timedelta(hours=1), "2h": timedelta(hours=2),
            "4h": timedelta(hours=4), "1d": timedelta(days=1),
            "1w": timedelta(weeks=1)
        }
        delta = timeframe_deltas.get(timeframe, timedelta(hours=1))
        
        end_time = datetime.now()
        timestamps = [end_time - i * delta for i in range(limit)]
        timestamps.reverse()
        
        base_price = 1.0800
        if "JPY" in symbol:
            base_price = 149.50
        elif "GBP" in symbol:
            base_price = 1.2600

        prices = [base_price]
        volatility = 0.001 if "JPY" not in symbol else 0.1
        for _ in range(limit - 1):
            change = np.random.normal(0, volatility)
            prices.append(max(prices[-1] + change, 0.0001))
            
        opens, highs, lows, closes, volumes = [], [], [], [], []
        for p in prices:
            noise = np.random.uniform(0.0001, 0.0005) if "JPY" not in symbol else np.random.uniform(0.01, 0.05)
            o = p * np.random.uniform(0.9998, 1.0002)
            c = p * np.random.uniform(0.9998, 1.0002)
            h = max(o, c) + noise
            l = min(o, c) - noise
            v = np.random.randint(100, 1000)
            
            opens.append(o)
            closes.append(c)
            highs.append(h)
            lows.append(l)
            volumes.append(float(v))
            
        df = pd.DataFrame({
            "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes
        }, index=timestamps)
        
        df.index.name = "time"
        return df

    def __del__(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
