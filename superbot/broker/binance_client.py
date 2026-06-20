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

    def __init__(self):
        if not BINANCE_AVAILABLE:
            raise ImportError(
                "python-binance non installé.\n"
                "   → pip install python-binance"
            )
        self._init_client()
        self._symbol_info: Dict[str, Any] = {}

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
        try:
            return api_func(*args, **kwargs)
        except BinanceAPIException as e:
            if e.code in (-1021, -1022) or "ahead" in str(e.message).lower() or "recvwindow" in str(e.message).lower():
                log.warning(f"⏰ Erreur de synchronisation temporelle détectée ({e.message}). Réalignement avec le serveur...")
                self._sync_time()
                try:
                    return api_func(*args, **kwargs)
                except BinanceAPIException as e2:
                    log.error(f"Échec persistant après re-synchronisation : {e2.message} (code {e2.code})")
                    return default_val
            else:
                log.error(f"Erreur Binance API : {e.message} (code {e.code})")
                return default_val
        except Exception as e:
            log.error(f"Erreur inattendue lors de l'appel API : {e}")
            return default_val

    def _init_client(self):
        """Initialise le client Binance avec gestion du testnet."""
        if BINANCE_TESTNET:
            self._client = BnClient(
                BINANCE_API_KEY, BINANCE_API_SECRET,
                testnet=True,
            )
            log.info("Connecté au TESTNET Binance Futures")
        else:
            self._client = BnClient(BINANCE_API_KEY, BINANCE_API_SECRET)
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

    def get_balance(self) -> float:
        """Solde total du portefeuille de futures (wallet balance)."""
        def run():
            account = self._client.futures_account()
            return float(account["totalWalletBalance"])
        return self._call_api(run, 0.0)

    def get_account_summary(self) -> Dict[str, Any]:
        """Résumé complet : balance, PnL, levier, positions."""
        def run():
            account = self._client.futures_account()
            positions = self._client.futures_position_information()
            open_pos  = [p for p in positions if float(p["positionAmt"]) != 0]
            return {
                "balance":        float(account["totalWalletBalance"]),
                "equity":         float(account["totalMarginBalance"]),
                "unrealized_pnl": float(account["totalUnrealizedProfit"]),
                "margin_used":    float(account["totalInitialMargin"]),
                "open_positions": len(open_pos),
                "leverage":       LEVERAGE,
                "testnet":        BINANCE_TESTNET,
                "account_type":   "TESTNET" if BINANCE_TESTNET else "REAL",
            }
        return self._call_api(run, {})

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
        """Prix mark courant (Futures mark price)."""
        binance_symbol = symbol.replace("/", "").upper()
        try:
            tick = self._client.futures_mark_price(symbol=binance_symbol)
            return float(tick["markPrice"])
        except BinanceAPIException as e:
            log.error(f"get_current_price : {e.message}")
            return 0.0

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
        def run():
            positions = self._client.futures_position_information(symbol=binance_symbol)
            for pos in positions:
                qty = float(pos["positionAmt"])
                if qty != 0:
                    # Récupérer les prix SL et TP parmi les ordres ouverts
                    stop_loss = 0.0
                    take_profit = 0.0
                    try:
                        open_orders = self._client.futures_get_open_orders(symbol=binance_symbol)
                        for order in open_orders:
                            o_type = order.get("type")
                            o_side = order.get("side")
                            pos_side = "LONG" if qty > 0 else "SHORT"
                            # L'ordre de fermeture doit être dans le sens opposé de la position
                            is_close_side = (pos_side == "LONG" and o_side == "SELL") or (pos_side == "SHORT" and o_side == "BUY")
                            if is_close_side:
                                if o_type in ["STOP_MARKET", "STOP"]:
                                    stop_loss = float(order.get("stopPrice", 0))
                                elif o_type in ["TAKE_PROFIT_MARKET", "TAKE_PROFIT"]:
                                    take_profit = float(order.get("stopPrice", 0))
                                elif o_type == "LIMIT":
                                    take_profit = float(order.get("price", 0))
                    except Exception as e:
                        log.debug(f"Impossible de récupérer les ordres ouverts pour SL/TP de {symbol}: {e}")

                    return {
                        "side":           "LONG" if qty > 0 else "SHORT",
                        "size":            abs(qty),  # Utiliser 'size' comme dans l'interface abstraite
                        "entry_price":    float(pos["entryPrice"]),
                        "mark_price":     float(pos["markPrice"]),
                        "unrealized_pnl": float(pos["unRealizedProfit"]),
                        "liquidation_price": float(pos.get("liquidationPrice", 0)) if pos.get("liquidationPrice") else None,
                        "margin_used":    float(pos.get("initialMargin", 0)),
                        "stop_loss":      stop_loss,
                        "take_profit":    take_profit,
                        "timestamp":      datetime.now(timezone.utc)
                    }
            return {}  # Aucune position
        return self._call_api(run, {})

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
            orders = self._client.futures_get_open_algo_orders(symbol=binance_symbol)
            sl_order = None
            tp_order = None
            for o in orders:
                if o.get("orderType") == "STOP_MARKET":
                    sl_order = o
                elif o.get("orderType") == "TAKE_PROFIT_MARKET":
                    tp_order = o

            # Mettre à jour le SL
            if sl > 0:
                if sl_order:
                    try:
                        self._client.futures_cancel_algo_order(symbol=binance_symbol, algoId=sl_order["algoId"])
                        time.sleep(0.2)
                    except BinanceAPIException as e:
                        log.warning(f"️ Impossible d'annuler l'ancien SL algo : {e.message}")

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
                if tp_order:
                    try:
                        self._client.futures_cancel_algo_order(symbol=binance_symbol, algoId=tp_order["algoId"])
                        time.sleep(0.2)
                    except BinanceAPIException as e:
                        log.warning(f"️ Impossible d'annuler l'ancien TP algo : {e.message}")

                try:
                    self._client.futures_create_order(
                        symbol=binance_symbol, side=close_side,
                        type="TAKE_PROFIT_MARKET", stopPrice=tp,
                        quantity=size, reduceOnly=True,
                    )
                except BinanceAPIException as e:
                    log.error(f"Impossible de placer le nouveau TP : {e.message}")
                    return False

            log.info(f"️  SL/TP mis à jour {symbol} | SL: {sl if sl > 0 else 'inchangé'} | TP: {tp if tp > 0 else 'inchangé'}")
            return True

        return self._call_api(run, False)

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
                log.info(f"Tous les ordres (standard & algo) annulés sur {symbol}")
                return True
            except BinanceAPIException as e:
                log.warning(f"️  cancel_all_orders (algo) : {e.message}")
                return False

        return self._call_api(run, False)


# Export des classes publiques
__all__ = ['BinanceClient']