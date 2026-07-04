"""
USDT-Margined Binance Futures Client.
"""
import logging
import math
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import pandas as pd

try:
    from binance.client import Client as BnClient
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False

from superbot.broker.base import Broker
from superbot.config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET,
    LEVERAGE, MIN_POSITION_SIZE, MAX_POSITION_SIZE, RISK_PCT,
    FOREX_DEFAULT_LEVERAGE, FOREX_MARGIN_CALL_LEVEL, FOREX_STOP_OUT_LEVEL
)

log = logging.getLogger("binance")

# Correspondance intervalles → Binance kline
INTERVAL_MAP = {
    "1m":  "1m",  "3m":  "3m",  "5m":  "5m",
    "15m": "15m", "30m": "30m",
    "1h":  "1h",  "2h":  "2h",  "4h":  "4h",
    "6h":  "6h",  "8h":  "8h",  "12h": "12h",
    "1d":  "1d",  "3d":  "3d",  "1w":  "1w",
    # Alias
    "M1":  "1m",  "M5":  "5m",  "M15": "15m", "M30": "30m",
    "H1":  "1h",  "H4":  "4h",  "D":   "1d",  "W":   "1w",
}


class BinanceClient(Broker):
    """
    Client Binance Futures USDT-Margined.
    Supporte Long + Short nativement, levier configurable.
    Compatible avec TradingView (même API key).
    """

    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = None, **kwargs):
        if not BINANCE_AVAILABLE:
            raise ImportError(
                "python-binance non installé.\n"
                "   → pip install python-binance"
            )
        self._init_client(api_key, api_secret, testnet)
        self._symbol_info: Dict[str, Any] = {}
        
        # Caching configuration and states
        self._cache_duration = 10.0  # seconds
        self._account_cache = None
        self._account_cache_time = 0.0
        self._positions_cache = None
        self._positions_cache_time = 0.0
        self._price_cache: Dict[str, float] = {}
        self._price_cache_time = 0.0

    def _clear_cache(self):
        """Invalide le cache local pour forcer une récupération immédiate."""
        self._account_cache = None
        self._account_cache_time = 0.0
        self._positions_cache = None
        self._positions_cache_time = 0.0
        self._price_cache = {}
        self._price_cache_time = 0.0

    def _refresh_account_cache(self):
        now = time.time()
        if self._account_cache is not None and (now - self._account_cache_time) < self._cache_duration:
            return

        def run():
            account = self._client.futures_account()
            positions = self._client.futures_position_information()
            open_pos  = [p for p in positions if float(p["positionAmt"]) != 0]
            balances = self._get_usd_balances(account)
            
            self._account_cache = {
                "balance":        balances["wallet_balance"],
                "equity":         balances["margin_balance"],
                "unrealized_pnl": balances["unrealized_pnl"],
                "margin_used":    float(account["totalInitialMargin"]),
                "free_margin":    float(account.get("availableBalance", 0.0)),
                "open_positions": len(open_pos),
                "leverage":       LEVERAGE,
                "testnet":        BINANCE_TESTNET,
                "account_type":   "TESTNET" if BINANCE_TESTNET else "REAL",
            }
            self._account_cache_time = now

        self._call_api(run, None)

    def _refresh_positions_cache(self):
        now = time.time()
        if self._positions_cache is not None and (now - self._positions_cache_time) < self._cache_duration:
            return

        def run():
            all_positions = self._client.futures_position_information()
            all_open_orders = self._client.futures_get_open_orders()
            
            orders_by_symbol = {}
            for order in all_open_orders:
                sym = order.get("symbol")
                if sym not in orders_by_symbol:
                    orders_by_symbol[sym] = []
                orders_by_symbol[sym].append(order)
            
            new_positions_cache = {}
            for pos in all_positions:
                qty = float(pos["positionAmt"])
                raw_symbol = pos["symbol"]
                
                if qty != 0:
                    stop_loss = 0.0
                    take_profit = 0.0
                    open_orders = orders_by_symbol.get(raw_symbol, [])
                    for order in open_orders:
                        o_type = order.get("type")
                        o_side = order.get("side")
                        pos_side = "LONG" if qty > 0 else "SHORT"
                        is_close_side = (pos_side == "LONG" and o_side == "SELL") or (pos_side == "SHORT" and o_side == "BUY")
                        if is_close_side:
                            if o_type in ["STOP_MARKET", "STOP"]:
                                stop_loss = float(order.get("stopPrice", 0))
                            elif o_type in ["TAKE_PROFIT_MARKET", "TAKE_PROFIT"]:
                                take_profit = float(order.get("stopPrice", 0))
                            elif o_type == "LIMIT":
                                take_profit = float(order.get("price", 0))
                    
                    new_positions_cache[raw_symbol] = {
                        "side":           "LONG" if qty > 0 else "SHORT",
                        "size":            abs(qty),
                        "entry_price":    float(pos["entryPrice"]),
                        "mark_price":     float(pos["markPrice"]),
                        "unrealized_pnl": float(pos["unRealizedProfit"]),
                        "liquidation_price": float(pos.get("liquidationPrice", 0)) if pos.get("liquidationPrice") else None,
                        "margin_used":    float(pos.get("initialMargin", 0)),
                        "stop_loss":      stop_loss,
                        "take_profit":    take_profit,
                        "timestamp":      datetime.now(timezone.utc)
                    }
            
            self._positions_cache = new_positions_cache
            self._positions_cache_time = now
            
        self._call_api(run, None)

    def get_default_instruments(self) -> List[str]:
        return ["BTC/USDT", "ETH/USDT"]

    def get_default_news_assets(self) -> List[str]:
        return ["BTC", "ETH"]

    def get_asset_type(self) -> str:
        return "crypto"

    def _sync_time(self):
        """Synchronise l'offset de temps avec le serveur Binance."""
        try:
            server_time = self._client.futures_time()['serverTime']
            local_time = int(time.time() * 1000)
            self._client.timestamp_offset = server_time - local_time
            log.info(f"⏰ Temps synchronisé. Offset: {self._client.timestamp_offset}ms")
        except Exception as e:
            log.warning(f"️  Impossible de synchroniser le temps : {e}")

    def _call_api(self, api_func, default_val, *args, **kwargs):
        max_retries = 3
        backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                return api_func(*args, **kwargs)
            except BinanceAPIException as e:
                if e.code in (-1021, -1022) or "ahead" in str(e.message).lower() or "recvwindow" in str(e.message).lower():
                    log.warning(f"⏰ Erreur de synchronisation temporelle détectée ({e.message}). Réalignement...")
                    self._sync_time()
                    try:
                        return api_func(*args, **kwargs)
                    except Exception as ex:
                        log.error(f"Échec persistant après re-synchronisation : {ex}")
                        return default_val
                elif e.code == -1003:
                    log.warning(f"⚠️ Limite de taux Binance API atteinte (IP bloquée). Tentative {attempt}/{max_retries} après {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    log.error(f"Erreur Binance API : {e.message} (code {e.code})")
                    return default_val
            except Exception as e:
                log.warning(f"⚠️ Erreur réseau/inattendue lors de l'appel API ({e}). Tentative {attempt}/{max_retries} après {backoff}s...")
                if attempt == max_retries:
                    log.error(f"Échec critique après {max_retries} tentatives : {e}")
                    return default_val
                time.sleep(backoff)
                backoff *= 2.0

    def _init_client(self, api_key=None, api_secret=None, testnet=None):
        """Initialise le client Binance avec gestion du testnet."""
        key = api_key or BINANCE_API_KEY
        secret = api_secret or BINANCE_API_SECRET
        is_testnet = BINANCE_TESTNET if testnet is None else testnet

        if is_testnet:
            self._client = BnClient(
                key, secret,
                testnet=True,
                requests_params={"timeout": 10}
            )
            log.info("Connecté au TESTNET Binance Futures")
        else:
            self._client = BnClient(key, secret, requests_params={"timeout": 10})
            log.info("Connecté à Binance Futures (RÉEL)")

        # Synchroniser l'heure d'abord (évite les erreurs de timestamp)
        self._sync_time()

    def _get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Cache les infos de précision du symbole (step size, tick size)."""
        binance_symbol = symbol.replace("/", "").upper()

        if binance_symbol not in self._symbol_info:
            try:
                # Configurer le levier sur l'échange
                try:
                    self._client.futures_change_leverage(symbol=binance_symbol, leverage=LEVERAGE)
                    log.info(f"Effet de levier configuré avec succès à {LEVERAGE}x pour {symbol}")
                except Exception as e:
                    log.warning(f"⚠️ Impossible de configurer le levier à {LEVERAGE}x pour {symbol} : {e}")

                info = self._client.futures_exchange_info()
                for s in info["symbols"]:
                    if s["symbol"] == binance_symbol:
                        filters = {f["filterType"]: f for f in s["filters"]}
                        self._symbol_info[binance_symbol] = {
                            "price_precision": s["pricePrecision"],
                            "qty_precision":   s["quantityPrecision"],
                            "tick_size":       float(filters.get("PRICE_FILTER", {}).get("tickSize", "0.1")),
                            "step_size":       float(filters.get("LOT_SIZE", {}).get("stepSize", "0.001")),
                            "min_qty":         float(filters.get("LOT_SIZE", {}).get("minQty", "0.001")),
                        }
                        break
            except Exception as e:
                log.warning(f"️  Impossible de récupérer les infos du symbole {binance_symbol}: {e}")
                self._symbol_info[binance_symbol] = {
                    "price_precision": 8, "qty_precision": 8,
                    "tick_size": 0.01, "step_size": 0.00000001, "min_qty": 0.00000001,
                }
        return self._symbol_info.get(binance_symbol, {
            "price_precision": 8, "qty_precision": 8,
            "tick_size": 0.01, "step_size": 0.00000001, "min_qty": 0.00000001,
        })

    def _round_qty(self, symbol: str, qty: float) -> float:
        """Arrondit la quantité au step_size Binance."""
        binance_symbol = symbol.replace("/", "").upper()
        info = self._get_symbol_info(binance_symbol)
        step = info["step_size"]
        precision = info["qty_precision"]
        floored = math.floor(qty / step) * step
        return round(floored, precision)

    def _round_price(self, symbol: str, price: float) -> float:
        """Arrondit le prix au tick_size Binance."""
        binance_symbol = symbol.replace("/", "").upper()
        info = self._get_symbol_info(binance_symbol)
        tick = info["tick_size"]
        precision = info["price_precision"]
        rounded = round(round(price / tick) * tick, precision)
        return rounded

    # ─── Compte ───────────────────────────────────────────────

    def _get_usd_balances(self, account_data: Dict) -> Dict[str, float]:
        """Calcule le solde du portefeuille et le P&L latent convertis en USD/USDT pour le mode Multi-Actifs."""
        total_wallet_balance = 0.0
        total_unrealized_pnl = 0.0
        
        for asset_info in account_data.get("assets", []):
            wb = float(asset_info.get("walletBalance", 0.0))
            upnl = float(asset_info.get("unrealizedProfit", 0.0))
            if wb == 0.0 and upnl == 0.0:
                continue
                
            asset_name = asset_info.get("asset", "")
            if asset_name in ["USDT", "USDC", "USD"]:
                total_wallet_balance += wb
                total_unrealized_pnl += upnl
            else:
                # Récupérer le prix de l'actif
                try:
                    price = float(self.get_current_price(f"{asset_name}/USDT"))
                    if price <= 0:
                        price = float(self.get_current_price(asset_name))
                except Exception:
                    # Fallbacks approximatifs en dernier recours
                    fallbacks = {"BTC": 67000.0, "ETH": 3500.0, "BNB": 580.0, "SOL": 140.0, "ADA": 0.45}
                    price = fallbacks.get(asset_name, 1.0)
                
                total_wallet_balance += wb * price
                total_unrealized_pnl += upnl * price
                
        return {
            "wallet_balance": total_wallet_balance,
            "unrealized_pnl": total_unrealized_pnl,
            "margin_balance": total_wallet_balance + total_unrealized_pnl
        }

    def get_balance(self) -> float:
        """Solde total du portefeuille de futures (wallet balance) en USD/USDT."""
        self._refresh_account_cache()
        if self._account_cache is not None:
            return self._account_cache["balance"]
        return 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        """Résumé complet : balance, PnL, levier, positions."""
        self._refresh_account_cache()
        if self._account_cache is not None:
            return self._account_cache
        return {}

    # ─── Données marché ───────────────────────────────────────

    def fetch_candles(self, symbol: str, interval: str,
                      limit: int = 500) -> pd.DataFrame:
        """Télécharge les klines Binance Futures → DataFrame OHLCV."""
        binance_symbol = symbol.replace("/", "").upper()
        binance_interval = INTERVAL_MAP.get(interval, interval)

        try:
            klines = self._client.futures_klines(
                symbol=binance_symbol,
                interval=binance_interval,
                limit=limit + 1,  # +1 pour exclure la bougie en cours
            )
        except BinanceAPIException as e:
            log.error(f"fetch_candles {symbol}/{interval} : {e.message}")
            return pd.DataFrame()

        if not klines:
            return pd.DataFrame()

        df = pd.DataFrame(klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore",
        ])

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df = df.set_index("open_time")

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        df = df[["open", "high", "low", "close", "volume"]]

        # Exclure la bougie en cours (non clôturée)
        df = df.iloc[:-1]

        log.debug(f"{len(df)} bougies {symbol}/{interval}")
        return df

    def get_current_price(self, symbol: str) -> float:
        """Prix mark courant (Futures mark price), optimisé avec cache global."""
        binance_symbol = symbol.replace("/", "").upper()
        now = time.time()
        if not self._price_cache or (now - self._price_cache_time) > self._cache_duration:
            try:
                def run():
                    prices = self._client.futures_mark_price()
                    new_prices = {}
                    if isinstance(prices, list):
                        for p in prices:
                            s = p.get("symbol")
                            mp = p.get("markPrice")
                            if s and mp:
                                new_prices[s] = float(mp)
                    elif isinstance(prices, dict):
                        s = prices.get("symbol")
                        mp = prices.get("markPrice")
                        if s and mp:
                            new_prices[s] = float(mp)
                    self._price_cache = new_prices
                    self._price_cache_time = now
                self._call_api(run, None)
            except Exception as e:
                log.warning(f"⚠️ Impossible de rafraîchir le cache des prix mark : {e}")

        return self._price_cache.get(binance_symbol, 0.0)

    def get_funding_rate(self, symbol: str) -> float:
        """Taux de financement actuel (signal sentiment)."""
        binance_symbol = symbol.replace("/", "").upper()
        try:
            data = self._client.futures_mark_price(symbol=binance_symbol)
            return float(data.get("lastFundingRate", 0))
        except Exception:
            return 0.0

    def get_open_interest(self, symbol: str) -> float:
        """Open Interest total (signal conviction du marché)."""
        binance_symbol = symbol.replace("/", "").upper()
        try:
            data = self._client.futures_open_interest(symbol=binance_symbol)
            return float(data.get("openInterest", 0))
        except Exception:
            return 0.0

    # ─── Positions ────────────────────────────────────────────

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """Retourne la position ouverte sur le symbole."""
        binance_symbol = symbol.replace("/", "").upper()
        self._refresh_positions_cache()
        if self._positions_cache is not None and binance_symbol in self._positions_cache:
            return self._positions_cache[binance_symbol]
        return {}

    def close_position(self, symbol: str, reason: str = "") -> bool:
        """Ferme la position ouverte au prix du marché."""
        binance_symbol = symbol.replace("/", "").upper()
        pos = self.get_position(symbol)
        if not pos:
            log.info(f"ℹ️  Aucune position à fermer sur {symbol}")
            return False

        side   = pos["side"]
        size    = pos["size"]
        close_side = "SELL" if side == "LONG" else "BUY"

        def run():
            self._client.futures_create_order(
                symbol=binance_symbol,
                side=close_side,
                type="MARKET",
                quantity=self._round_qty(symbol, size),
                reduceOnly=True,
            )
            # Annuler aussi tous les ordres conditionnels
            self.cancel_all_orders(symbol)
            self._clear_cache()
            log.info(f"Position {side} fermée sur {symbol} | {reason}")
            return True
        return self._call_api(run, False)

    # ─── Ordres ───────────────────────────────────────────────

    def calculate_position_size(self, entry_price: float, sl_price: float,
                               risk_amount: float, leverage: int = 1,
                               symbol: str = "") -> float:
        """
        Calcule la taille de position basée sur le risque en monnaie de compte.

        Args:
            entry_price: Prix d'entrée prévu
            sl_price: Prix du stop loss
            risk_amount: Montant à risque en monnaie de compte (ex: $100)
            leverage: Effet de levier utilisé (défaut: 1 pour aucun levier)
            symbol: Symbole de l'instrument (ex: 'BTC/USDT')

        Returns:
            Taille de position en unités de base de l'actif
        """
        if entry_price == sl_price:
            return 0.0

        risk_per_unit = abs(entry_price - sl_price)
        if risk_per_unit == 0:
            return 0.0

        # Taille de base sans levier
        base_size = risk_amount / risk_per_unit

        # Ajuster pour le levier si applicable
        leveraged_size = base_size * leverage

        # Appliquer les limites du symbole
        symbol_binance = symbol if symbol else "BTC/USDT"
        min_size = self.get_min_order_size(symbol_binance)
        max_size = self.get_step_size(symbol_binance) * 1000  # Limite arbitraire supérieure

        final_size = max(min(leveraged_size, max_size), min_size)
        return self._round_qty(symbol_binance, final_size)

    def place_order(self, symbol: str, side: str, amount: float,
                   sl: float, tp: float, reduce_only: bool = False,
                   comment: str = "") -> bool:
        """
        Place un ordre de marché avec stop loss et take profit.
        """
        binance_symbol = symbol.replace("/", "").upper()
        side_binance = "BUY" if side.lower() == "buy" else "SELL"
        amount = self._round_qty(symbol, amount)
        sl = self._round_price(symbol, sl) if sl > 0 else 0
        tp = self._round_price(symbol, tp) if tp > 0 else 0

        # Diagnostic de marge pré-exécution
        try:
            self._refresh_account_cache()
            free_m = self._account_cache.get("free_margin", 0.0) if self._account_cache else 0.0
            est_price = self.get_current_price(symbol)
            req_m = (amount * est_price) / LEVERAGE if est_price > 0 else 0.0
            log.info(
                f"⚙️ Diagnostic marge pré-exécution pour {symbol} : "
                f"Quantité={amount} | Prix estimé={est_price:.2f} | "
                f"Marge requise={req_m:.2f} USDT | Marge disponible={free_m:.2f} USDT | Levier={LEVERAGE}x"
            )
        except Exception as e:
            log.debug(f"Erreur diagnostic marge pré-exécution: {e}")

        def run():
            # 1. Ordre principal (MARKET)
            order_params = {
                "symbol": binance_symbol,
                "side": side_binance,
                "type": "MARKET",
                "quantity": amount,
            }

            if not reduce_only:
                pass
            else:
                order_params["reduceOnly"] = True

            result = self._client.futures_create_order(**order_params)

            if not result or "orderId" not in result:
                log.error(f"Ordre principal échoué : {result}")
                return False

            entry_price = float(result.get("avgPrice", 0)) or self.get_current_price(symbol)
            close_side  = "SELL" if side_binance == "BUY" else "BUY"

            # 2. Stop Loss (STOP_MARKET) avec reduceOnly (si spécifié)
            if sl > 0 and not reduce_only:
                try:
                    self._client.futures_create_order(
                        symbol=binance_symbol,
                        side=close_side,
                        type="STOP_MARKET",
                        stopPrice=sl,
                        quantity=amount,
                        reduceOnly=True,
                    )
                except BinanceAPIException as e:
                    log.warning(f"️  SL non placé : {e.message}")

            # 3. Take Profit (TAKE_PROFIT_MARKET) avec reduceOnly (si spécifié)
            if tp > 0 and not reduce_only:
                try:
                    self._client.futures_create_order(
                        symbol=binance_symbol,
                        side=close_side,
                        type="TAKE_PROFIT_MARKET",
                        stopPrice=tp,
                        quantity=amount,
                        reduceOnly=True,
                    )
                except BinanceAPIException as e:
                    log.warning(f"️  TP non placé : {e.message}")

            self._clear_cache()
            arrow = "▲" if side == "buy" else "▼"
            log.info(
                f"{arrow} {side} {amount} {symbol} @ {entry_price:,.2f} | "
                f"SL: {sl:,.2f} | TP: {tp:,.2f} | {comment}"
            )
            return True

        return self._call_api(run, False)

    def modify_sl_tp(self, symbol: str, sl: float, tp: float) -> bool:
        """
        Modifie le stop loss et take profit d'une position existante.
        """
        binance_symbol = symbol.replace("/", "").upper()
        pos = self.get_position(symbol)
        if not pos:
            log.warning(f"️ modify_sl_tp : Aucune position ouverte sur {symbol}")
            return False

        close_side = "SELL" if pos["side"] == "LONG" else "BUY"
        size = pos["size"]
        sl = self._round_price(symbol, sl) if sl > 0 else 0
        tp = self._round_price(symbol, tp) if tp > 0 else 0

        def run():
            orders = self._client.futures_get_open_orders(symbol=binance_symbol)
            sl_orders = []
            tp_orders = []
            for o in orders:
                if o.get("type") in ["STOP_MARKET", "STOP"]:
                    sl_orders.append(o)
                elif o.get("type") in ["TAKE_PROFIT_MARKET", "TAKE_PROFIT"]:
                    tp_orders.append(o)

            # Mettre à jour le SL
            if sl > 0:
                for old_sl in sl_orders:
                    try:
                        self._client.futures_cancel_order(symbol=binance_symbol, orderId=old_sl["orderId"])
                        time.sleep(0.1)
                    except BinanceAPIException as e:
                        log.warning(f"⚠️ Impossible d'annuler l'ancien SL : {e.message}")

                try:
                    self._client.futures_create_order(
                        symbol=binance_symbol, side=close_side,
                        type="STOP_MARKET", stopPrice=sl,
                        quantity=size, reduceOnly=True,
                    )
                except BinanceAPIException as e:
                    log.error(f"Impossible de placer le nouveau SL : {e.message}")
                    return False

            # Mettre à jour le TP
            if tp > 0:
                for old_tp in tp_orders:
                    try:
                        self._client.futures_cancel_order(symbol=binance_symbol, orderId=old_tp["orderId"])
                        time.sleep(0.1)
                    except BinanceAPIException as e:
                        log.warning(f"⚠️ Impossible d'annuler l'ancien TP : {e.message}")

                try:
                    self._client.futures_create_order(
                        symbol=binance_symbol, side=close_side,
                        type="TAKE_PROFIT_MARKET", stopPrice=tp,
                        quantity=size, reduceOnly=True,
                    )
                except BinanceAPIException as e:
                    log.error(f"Impossible de placer le nouveau TP : {e.message}")
                    return False

            self._clear_cache()
            log.info(f"️  SL/TP mis à jour {symbol} | SL: {sl if sl > 0 else 'inchangé'} | TP: {tp if tp > 0 else 'inchangé'}")
            return True

        return self._call_api(run, False)

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Retourne les informations du symbole (contract_size, tick_size, tick_value) pour Binance.
        """
        symbol = self.normalize_symbol(symbol)
        info = self._get_symbol_info(symbol)
        tick_size = info.get("tick_size", 0.01)
        return {
            "contract_size": 1.0,
            "tick_size": tick_size,
            "tick_value": tick_size,
        }

    def get_min_order_size(self, symbol: str) -> float:
        """Retourne la taille minimale d'ordre autorisée pour un instrument."""
        binance_symbol = symbol.replace("/", "").upper()
        info = self._get_symbol_info(binance_symbol)
        return info["min_qty"]

    def get_step_size(self, symbol: str) -> float:
        """Retourne le pas de taille d'ordre (precision) pour un instrument."""
        binance_symbol = symbol.replace("/", "").upper()
        info = self._get_symbol_info(binance_symbol)
        return info["step_size"]

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalise un symbole selon le format attendu par le courtier.
        """
        return symbol.replace("/", "").upper()

    def cancel_all_orders(self, symbol: str) -> bool:
        """Annule tous les ordres ouverts (standards et algo SL/TP) sur le symbole."""
        binance_symbol = symbol.replace("/", "").upper()
        def run():
            try:
                self._client.futures_cancel_all_open_orders(symbol=binance_symbol)
            except BinanceAPIException as e:
                log.warning(f"️  cancel_all_orders (standards) : {e.message}")

            try:
                algo_orders = self._client.futures_get_open_algo_orders(symbol=binance_symbol)
                for o in algo_orders:
                    algo_id = o.get("algoId")
                    if algo_id:
                        self._client.futures_cancel_algo_order(symbol=binance_symbol, algoId=algo_id)
                self._clear_cache()
                log.info(f"Tous les ordres (standard & algo) annulés sur {symbol}")
                return True
            except BinanceAPIException as e:
                log.warning(f"️  cancel_all_orders (algo) : {e.message}")
                return False

        return self._call_api(run, False)


# Export des classes publiques
__all__ = ['BinanceClient']