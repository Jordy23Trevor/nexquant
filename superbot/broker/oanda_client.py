"""
OANDA v20 REST API Forex client for SuperBot.
"""
import logging
import pandas as pd
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from superbot.broker.base import Broker
from superbot.config import OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT, FOREX_DEFAULT_LEVERAGE

log = logging.getLogger("oanda_client")


class OandaClient(Broker):
    """
    Client de trading réel et démo pour OANDA utilisant l'API REST v20.
    """

    def __init__(self, **kwargs):
        self.api_key = OANDA_API_KEY
        self.account_id = OANDA_ACCOUNT_ID
        self.environment = OANDA_ENVIRONMENT.lower()

        if self.environment == "live":
            self.base_url = "https://api-fxtrade.oanda.com/v3"
        else:
            self.base_url = "https://api-fxpractice.oanda.com/v3"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if not self.api_key or not self.account_id:
            log.warning("⚠️ OANDA_API_KEY ou OANDA_ACCOUNT_ID non configurés dans le fichier .env !")

    def get_default_instruments(self) -> List[str]:
        return ["EUR_USD", "GBP_USD", "USD_JPY"]

    def get_default_news_assets(self) -> List[str]:
        return ["EUR", "USD", "GBP", "JPY"]

    def get_asset_type(self) -> str:
        return "forex"

    def get_account_summary(self) -> Dict[str, Any]:
        """Récupère le résumé du compte depuis OANDA."""
        if not self.api_key or not self.account_id:
            return self._empty_account_summary("OANDA_MISSING_CONFIG")

        url = f"{self.base_url}/accounts/{self.account_id}/summary"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                data = res.json().get("account", {})
                balance = float(data.get("balance", 0.0))
                unrealized_pnl = float(data.get("unrealizedPL", 0.0))
                margin_used = float(data.get("marginUsed", 0.0))
                equity = float(data.get("equity", balance))
                free_margin = float(data.get("marginAvailable", 0.0))
                margin_level = (equity / margin_used * 100) if margin_used > 0 else 0.0
                open_pos_count = int(data.get("openPositionCount", 0))

                return {
                    "balance": balance,
                    "equity": equity,
                    "unrealized_pnl": unrealized_pnl,
                    "margin_used": margin_used,
                    "free_margin": free_margin,
                    "margin_level": margin_level,
                    "open_positions": open_pos_count,
                    "account_type": f"OANDA_{self.environment.upper()}",
                    "leverage": FOREX_DEFAULT_LEVERAGE,
                }
            else:
                log.error(f"Oanda summary error {res.status_code}: {res.text}")
        except Exception as e:
            log.error(f"Oanda summary exception: {e}")

        return self._empty_account_summary(f"OANDA_ERROR_{self.environment.upper()}")

    def _empty_account_summary(self, status: str) -> Dict[str, Any]:
        return {
            "balance": 0.0,
            "equity": 0.0,
            "unrealized_pnl": 0.0,
            "margin_used": 0.0,
            "free_margin": 0.0,
            "margin_level": 0.0,
            "open_positions": 0,
            "account_type": status,
            "leverage": FOREX_DEFAULT_LEVERAGE,
        }

    def get_balance(self) -> float:
        return self.get_account_summary()["balance"]

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Récupère les bougies historiques de OANDA."""
        if not self.api_key or not self.account_id:
            return pd.DataFrame()

        normalized = self.normalize_symbol(symbol)
        tf_map = {
            "1m": "M1", "5m": "M5", "15m": "M15", "30m": "M30",
            "1h": "H1", "2h": "H2", "4h": "H4", "1d": "D", "1w": "W"
        }
        granularity = tf_map.get(timeframe, "H1")
        url = f"{self.base_url}/instruments/{normalized}/candles"
        params = {
            "granularity": granularity,
            "count": limit,
            "price": "M"
        }
        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json().get("candles", [])
                df_list = []
                for c in data:
                    if not c.get("complete", True) and len(data) > 1:
                        continue
                    time_str = c.get("time")
                    mid = c.get("mid", {})
                    df_list.append({
                        "timestamp": pd.to_datetime(time_str),
                        "open": float(mid.get("o", 0.0)),
                        "high": float(mid.get("h", 0.0)),
                        "low": float(mid.get("l", 0.0)),
                        "close": float(mid.get("c", 0.0)),
                        "volume": float(c.get("volume", 0.0))
                    })
                df = pd.DataFrame(df_list)
                if not df.empty:
                    df = df.set_index("timestamp")
                    df = df.sort_index()
                    return df
            else:
                log.error(f"Oanda candle error {res.status_code}: {res.text}")
        except Exception as e:
            log.error(f"Oanda candle exception: {e}")

        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    def get_current_price(self, symbol: str) -> float:
        """Récupère le prix actuel du marché (mid price)."""
        if not self.api_key or not self.account_id:
            return 0.0

        normalized = self.normalize_symbol(symbol)
        url = f"{self.base_url}/accounts/{self.account_id}/pricing"
        params = {"instruments": normalized}
        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=10)
            if res.status_code == 200:
                prices = res.json().get("prices", [])
                if prices:
                    p = prices[0]
                    bid = float(p.get("closeoutBid", 0.0))
                    ask = float(p.get("closeoutAsk", 0.0))
                    return round((bid + ask) / 2, 5)
            else:
                log.error(f"Oanda pricing error {res.status_code}: {res.text}")
        except Exception as e:
            log.error(f"Oanda pricing exception: {e}")

        # Fallback aux bougies
        df = self.fetch_candles(symbol, "1m", limit=1)
        if not df.empty:
            return float(df["close"].iloc[-1])
        return 0.0

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """Récupère la position ouverte pour un instrument donné."""
        if not self.api_key or not self.account_id:
            return self._empty_position()

        normalized = self.normalize_symbol(symbol)
        url = f"{self.base_url}/accounts/{self.account_id}/positions/{normalized}"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                data = res.json().get("position", {})
                long_units = float(data.get("long", {}).get("units", 0.0))
                short_units = float(data.get("short", {}).get("units", 0.0))

                side = None
                size = 0.0
                entry_price = 0.0
                unrealized_pnl = 0.0

                if long_units > 0:
                    side = "LONG"
                    size = long_units
                    entry_price = float(data.get("long", {}).get("averagePrice", 0.0))
                    unrealized_pnl = float(data.get("long", {}).get("unrealizedPL", 0.0))
                elif short_units < 0:
                    side = "SHORT"
                    size = abs(short_units)
                    entry_price = float(data.get("short", {}).get("averagePrice", 0.0))
                    unrealized_pnl = float(data.get("short", {}).get("unrealizedPL", 0.0))

                if size > 0:
                    current_price = self.get_current_price(symbol)
                    return {
                        "side": side,
                        "size": size,
                        "entry_price": entry_price,
                        "mark_price": current_price,
                        "unrealized_pnl": unrealized_pnl,
                        "liquidation_price": None,
                        "margin_used": 0.0,
                    }
            elif res.status_code == 404:
                # Pas de position ouverte
                pass
            else:
                log.error(f"Oanda position error {res.status_code}: {res.text}")
        except Exception as e:
            log.error(f"Oanda position exception: {e}")

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
        """Ferme la position sur OANDA."""
        if not self.api_key or not self.account_id:
            return False

        normalized = self.normalize_symbol(symbol)
        pos = self.get_position(symbol)
        if not pos or pos["size"] == 0:
            return False

        url = f"{self.base_url}/accounts/{self.account_id}/positions/{normalized}/close"
        body = {}
        if pos["side"] == "LONG":
            body["longUnits"] = "ALL"
        else:
            body["shortUnits"] = "ALL"

        try:
            res = requests.put(url, headers=self.headers, json=body, timeout=10)
            if res.status_code in [200, 201]:
                log.info(f"Oanda position closed successfully for {symbol}. Reason: {reason}")
                return True
            else:
                log.error(f"Oanda close position error {res.status_code}: {res.text}")
        except Exception as e:
            log.error(f"Oanda close position exception: {e}")
        return False

    def place_order(self, symbol: str, side: str, amount: float,
                   sl: float, tp: float, reduce_only: bool = False,
                   comment: str = "") -> bool:
        """Place un ordre au marché avec SL/TP optionnels."""
        if not self.api_key or not self.account_id:
            return False

        normalized = self.normalize_symbol(symbol)
        units = amount
        if side.lower() in ["sell", "short"]:
            units = -amount

        units_val = int(round(units))
        if units_val == 0:
            log.warning(f"Oanda order size is 0 units after rounding amount {amount}")
            return False

        order_dict: Dict[str, Any] = {
            "type": "MARKET",
            "instrument": normalized,
            "units": str(units_val),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT"
        }

        if sl and sl > 0:
            order_dict["stopLossOnFill"] = {"price": f"{sl:.5f}" if "JPY" not in normalized else f"{sl:.3f}"}
        if tp and tp > 0:
            order_dict["takeProfitOnFill"] = {"price": f"{tp:.5f}" if "JPY" not in normalized else f"{tp:.3f}"}

        url = f"{self.base_url}/accounts/{self.account_id}/orders"
        body = {"order": order_dict}

        try:
            res = requests.post(url, headers=self.headers, json=body, timeout=10)
            if res.status_code in [200, 201]:
                log.info(f"Oanda order placed successfully for {symbol} | Units: {units_val} | SL: {sl} | TP: {tp} | {comment}")
                return True
            else:
                log.error(f"Oanda place order error {res.status_code}: {res.text}")
        except Exception as e:
            log.error(f"Oanda place order exception: {e}")
        return False

    def modify_sl_tp(self, symbol: str, sl: float, tp: float) -> bool:
        """Modifie le SL/TP d'un trade ouvert."""
        if not self.api_key or not self.account_id:
            return False

        normalized = self.normalize_symbol(symbol)

        # 1. Trouver le trade ID ouvert
        url_trades = f"{self.base_url}/accounts/{self.account_id}/openTrades"
        trade_id = None
        try:
            res = requests.get(url_trades, headers=self.headers, timeout=10)
            if res.status_code == 200:
                trades = res.json().get("trades", [])
                for t in trades:
                    if t.get("instrument") == normalized:
                        trade_id = t.get("id")
                        break
            else:
                log.error(f"Oanda get open trades error {res.status_code}: {res.text}")
                return False
        except Exception as e:
            log.error(f"Oanda get open trades exception: {e}")
            return False

        if not trade_id:
            log.warning(f"Oanda modify_sl_tp: Aucun trade ouvert trouvé pour {symbol}")
            return False

        # 2. Modifier le trade avec le nouveau SL/TP
        url_modify = f"{self.base_url}/accounts/{self.account_id}/trades/{trade_id}/orders"
        body = {}
        if sl and sl > 0:
            body["stopLoss"] = {
                "price": f"{sl:.5f}" if "JPY" not in normalized else f"{sl:.3f}",
                "timeInForce": "GTC"
            }
        if tp and tp > 0:
            body["takeProfit"] = {
                "price": f"{tp:.5f}" if "JPY" not in normalized else f"{tp:.3f}",
                "timeInForce": "GTC"
            }

        try:
            res = requests.put(url_modify, headers=self.headers, json=body, timeout=10)
            if res.status_code in [200, 201]:
                log.info(f"Oanda SL/TP mis à jour pour {symbol} | SL: {sl} | TP: {tp}")
                return True
            else:
                log.error(f"Oanda modify trade error {res.status_code}: {res.text}")
        except Exception as e:
            log.error(f"Oanda modify trade exception: {e}")
        return False

    def get_min_order_size(self, symbol: str) -> float:
        return 1.0

    def get_step_size(self, symbol: str) -> float:
        return 1.0

    def normalize_symbol(self, symbol: str) -> str:
        clean = symbol.strip().upper()
        if "/" in clean:
            return clean.replace("/", "_")
        elif len(clean) == 6 and clean.isalpha():
            return f"{clean[:3]}_{clean[3:]}"
        return clean
