"""
Paper Forex simulation broker client.
"""
import logging
import math
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from superbot.broker.base import Broker
from superbot.config import (
    FOREX_DEFAULT_LEVERAGE, FOREX_MARGIN_CALL_LEVEL, FOREX_STOP_OUT_LEVEL,
    MIN_POSITION_SIZE, MAX_POSITION_SIZE, RISK_PCT
)

log = logging.getLogger("paper_forex")


class PaperForexClient(Broker):
    """
    Moteur de simulation de trading forex utilisant des données simulées.
    Permet le paper trading réaliste sans compte broker forex traditionnel.
    Simule l'exécution d'ordres, SL/TP, marge, effet de levier.
    """

    def __init__(self):
        self._init_data_provider()
        self._positions: Dict[str, Dict] = {}
        self._orders: Dict[str, Dict] = {}
        self._symbol_info: Dict[str, Dict] = {}
        self._price_cache: Dict[str, Dict] = {}
        self._last_update: Dict[str, datetime] = {}
        self._initialize_symbols()

    def get_default_instruments(self) -> List[str]:
        return ["EUR/USD", "GBP/USD", "USD/JPY"]

    def get_default_news_assets(self) -> List[str]:
        return ["EUR", "USD", "GBP", "JPY"]

    def get_asset_type(self) -> str:
        return "forex"

    def _init_data_provider(self):
        """Initialise le fournisseur de données (simulation uniquement)."""
        self.data_provider = "simulation"
        log.info("Fournisseur de données forex : simulation")

    def _initialize_symbols(self):
        """Initialise la liste des symboles forex soutenus avec leurs caractéristiques."""
        self._symbol_info = {
            "EUR/USD": {"pip_value": 0.0001, "typical_spread": 1.0, "leverage": FOREX_DEFAULT_LEVERAGE},
            "GBP/USD": {"pip_value": 0.0001, "typical_spread": 1.5, "leverage": FOREX_DEFAULT_LEVERAGE},
            "USD/JPY": {"pip_value": 0.01, "typical_spread": 1.0, "leverage": FOREX_DEFAULT_LEVERAGE},
            "USD/CHF": {"pip_value": 0.0001, "typical_spread": 1.2, "leverage": FOREX_DEFAULT_LEVERAGE},
            "AUD/USD": {"pip_value": 0.0001, "typical_spread": 1.5, "leverage": FOREX_DEFAULT_LEVERAGE},
            "USD/CAD": {"pip_value": 0.0001, "typical_spread": 1.2, "leverage": FOREX_DEFAULT_LEVERAGE},
            "NZD/USD": {"pip_value": 0.0001, "typical_spread": 1.8, "leverage": FOREX_DEFAULT_LEVERAGE},
            "EUR/GBP": {"pip_value": 0.0001, "typical_spread": 1.5, "leverage": FOREX_DEFAULT_LEVERAGE},
            "EUR/JPY": {"pip_value": 0.01, "typical_spread": 2.0, "leverage": FOREX_DEFAULT_LEVERAGE},
            "GBP/JPY": {"pip_value": 0.01, "typical_spread": 2.5, "leverage": FOREX_DEFAULT_LEVERAGE},
        }

    def _get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Récupère les informations d'un symbole (pip value, spread, etc.)."""
        symbol_upper = symbol.upper()
        return self._symbol_info.get(symbol_upper, {
            "pip_value": 0.0001,
            "typical_spread": 1.0,
            "leverage": FOREX_DEFAULT_LEVERAGE,
        })

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalise un symbole forex pour un usage interne.
        """
        clean = symbol.strip().upper()
        if clean.endswith("=X") and len(clean) == 8:
            base = clean[:3]
            quote = clean[3:6]
            return f"{base}/{quote}"
        elif len(clean) == 6 and clean.isalpha():
            base = clean[:3]
            quote = clean[3:]
            return f"{base}/{quote}"
        elif "/" in clean and len(clean.split("/")) == 2:
            parts = clean.split("/")
            return f"{parts[0]}/{parts[1]}"
        else:
            return clean

    def _fetch_price_simulation(self, symbol: str) -> Dict[str, Any]:
        """Génère un prix simulé basé sur le dernier prix connu ou une valeur de base."""
        normalized = self._normalize_symbol(symbol)
        symbol_info = self._get_symbol_info(normalized)

        base_prices = {
            "EUR/USD": 1.0800,
            "GBP/USD": 1.2600,
            "USD/JPY": 149.50,
            "USD/CHF": 0.8800,
            "AUD/USD": 0.6500,
            "USD/CAD": 1.3600,
            "NZD/USD": 0.5900,
            "EUR/GBP": 0.8550,
            "EUR/JPY": 161.50,
            "GBP/JPY": 188.00,
        }

        base_price = base_prices.get(normalized, 1.0000)

        if normalized in self._price_cache:
            last_price = self._price_cache[normalized]["price"]
            volatility = 0.005
            change = random.uniform(-volatility, volatility) * last_price
            price = max(last_price + change, 0.0001)
        else:
            price = base_price * random.uniform(0.995, 1.005)

        price = round(price, 5) if normalized != "USD/JPY" else round(price, 3)

        return {
            "price": price,
            "timestamp": datetime.now(timezone.utc),
            "bid": price - (symbol_info["typical_spread"] * symbol_info["pip_value"] / 2),
            "ask": price + (symbol_info["typical_spread"] * symbol_info["pip_value"] / 2),
        }

    def get_current_price(self, symbol: str) -> float:
        """Prix mark/courant pour un symbole forex (mid price)."""
        normalized = self._normalize_symbol(symbol)

        now = datetime.now(timezone.utc)
        if normalized in self._last_update:
            time_diff = (now - self._last_update[normalized]).total_seconds()
            if time_diff < 5:
                return self._price_cache[normalized]["price"]

        price_data = self._fetch_price_simulation(symbol)

        self._price_cache[normalized] = price_data
        self._last_update[normalized] = now

        return price_data["price"]

    def get_spread(self, symbol: str) -> float:
        """Retourne le spread typique pour un symbole forex."""
        normalized = self._normalize_symbol(symbol)
        info = self._get_symbol_info(normalized)
        return float(info.get("typical_spread", 1.0))


    def get_balance(self) -> float:
        """Solde disponible en devise de base du compte de simulation."""
        return 10000.0

    def get_account_summary(self) -> Dict[str, Any]:
        """Résumé complet du compte de simulation."""
        balance = self.get_balance()
        unrealized_pnl = 0.0
        margin_used = 0.0

        for symbol, position in self._positions.items():
            if position["size"] != 0:
                current_price = self.get_current_price(symbol)
                entry_price = position["entry_price"]
                size = position["size"]

                if position["side"] == "LONG":
                    pl = (current_price - entry_price) * size
                else:
                    pl = (entry_price - current_price) * size

                unrealized_pnl += pl

                symbol_info = self._get_symbol_info(symbol)
                leverage = symbol_info["leverage"]
                notional = abs(size * entry_price)
                margin_used += notional / leverage

        equity = balance + unrealized_pnl
        free_margin = equity - margin_used
        margin_level = (equity / margin_used * 100) if margin_used > 0 else 0

        return {
            "balance": balance,
            "equity": equity,
            "unrealized_pnl": unrealized_pnl,
            "margin_used": margin_used,
            "free_margin": free_margin,
            "margin_level": margin_level,
            "open_positions": len([p for p in self._positions.values() if p["size"] != 0]),
            "account_type": "PAPER_FOREX_SIMULATION",
            "leverage": FOREX_DEFAULT_LEVERAGE,
        }

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """Retourne la position ouverte sur un symbole."""
        normalized = self._normalize_symbol(symbol)
        position = self._positions.get(normalized, {
            "side": None,
            "size": 0.0,
            "entry_price": 0.0,
            "mark_price": 0.0,
            "unrealized_pnl": 0.0,
            "liquidation_price": None,
            "margin_used": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
        })

        if position["size"] != 0:
            current_price = self.get_current_price(symbol)
            position["mark_price"] = current_price

            if position["side"] == "LONG":
                position["unrealized_pnl"] = (current_price - position["entry_price"]) * abs(position["size"])
            elif position["side"] == "SHORT":
                position["unrealized_pnl"] = (position["entry_price"] - current_price) * abs(position["size"])

            symbol_info = self._get_symbol_info(symbol)
            leverage = symbol_info["leverage"]
            notional = abs(position["size"] * position["entry_price"])
            position["margin_used"] = notional / leverage

            if position["side"] == "LONG":
                price_drop = position["margin_used"] * leverage / abs(position["size"])
                position["liquidation_price"] = position["entry_price"] - price_drop
            elif position["side"] == "SHORT":
                price_rise = position["margin_used"] * leverage / abs(position["size"])
                position["liquidation_price"] = position["entry_price"] + price_rise

        return position

    def close_position(self, symbol: str, reason: str = "") -> bool:
        """Ferme la position ouverte au prix du marché."""
        normalized = self._normalize_symbol(symbol)
        pos = self.get_position(symbol)
        if not pos or pos["size"] == 0:
            log.info(f"ℹ️  Aucune position à fermer sur {symbol}")
            return False

        side = pos["side"]
        size = pos["size"]

        close_price = self.get_current_price(symbol)
        slippage = 0.0001
        if side == "LONG":
            close_price -= slippage
        else:
            close_price += slippage

        if side == "LONG":
            pnl = (close_price - pos["entry_price"]) * size
        else:
            pnl = (pos["entry_price"] - close_price) * size

        log.info(
            f"Position {side} fermée sur {symbol} | "
            f"Taille: {size:.4f} | Entry: {pos['entry_price']:.4f} | "
            f"Close: {close_price:.4f} | P&L: {pnl:.2f} | {reason}"
        )

        self._positions[normalized] = {
            "side": None,
            "size": 0.0,
            "entry_price": 0.0,
            "mark_price": 0.0,
            "unrealized_pnl": 0.0,
            "liquidation_price": None,
            "margin_used": 0.0,
        }

        self._cancel_related_orders(normalized)
        return True

    def calculate_position_size(self, entry_price: float, sl_price: float,
                               risk_amount: float, leverage: int = 1,
                               symbol: str = "") -> float:
        """
        Calcule la taille de position basée sur le risque en monnaie de compte.
        """
        if entry_price == sl_price:
            return 0.0

        risk_per_unit = abs(entry_price - sl_price)
        if risk_per_unit == 0:
            return 0.0

        base_size = risk_amount / risk_per_unit
        leveraged_size = base_size * leverage

        target_symbol = symbol if symbol else "EUR/USD"
        min_size = self.get_min_order_size(symbol=target_symbol)
        max_size = self.get_step_size(symbol=target_symbol) * 100000

        final_size = max(min(leveraged_size, max_size), min_size)
        return final_size

    def place_order(self, symbol: str, side: str, amount: float,
                   sl: float, tp: float, reduce_only: bool = False,
                   comment: str = "") -> bool:
        """
        Place un ordre de marché avec stop loss et take profit.
        """
        normalized = self._normalize_symbol(symbol)
        side_lower = side.lower()
        amount = round(amount, 6)
        sl = round(sl, 5) if sl > 0 else None
        tp = round(tp, 5) if tp > 0 else None

        def run():
            try:
                entry_price = self.get_current_price(symbol)
                slippage = 0.0001

                if side_lower == "buy":
                    entry_price += slippage
                else:
                    entry_price -= slippage

                min_size = self.get_min_order_size(symbol)
                max_size = self.get_max_order_size(symbol) if hasattr(self, 'get_max_order_size') else float('inf')
                if amount < min_size:
                    log.warning(f"️  Taille d'ordre {amount} inférieure au minimum {min_size} pour {symbol}")
                    amount = min_size
                if amount > max_size:
                    log.warning(f"️  Taille d'ordre {amount} supérieure au maximum {max_size} pour {symbol}")
                    amount = max_size

                if not reduce_only:
                    self._positions[normalized] = {
                        "side": "LONG" if side_lower == "buy" else "SHORT",
                        "size": amount,
                        "entry_price": entry_price,
                        "mark_price": entry_price,
                        "unrealized_pnl": 0.0,
                        "liquidation_price": None,
                        "margin_used": 0.0,
                        "stop_loss": sl if sl else 0.0,
                        "take_profit": tp if tp else 0.0,
                    }
                    log.info(
                        f"{'▲' if side == 'buy' else '▼'} {side} {amount} {symbol} @ {entry_price:.4f} | "
                        f"SL: {sl if sl is not None else 'None'} | TP: {tp if tp is not None else 'None'} | {comment}"
                    )
                else:
                    pos = self.get_position(symbol)
                    if not pos or pos["size"] == 0:
                        log.warning(f"️  Aucune position à réduire sur {symbol}")
                        return False

                    if amount > pos["size"]:
                        log.warning(f"️  Tentative de réduire {amount} alors que la position est seulement {pos['size']}")
                        amount = pos["size"]

                    current_size = pos["size"]
                    current_side = pos["side"]
                    remaining_size = current_size - amount

                    if remaining_size <= 0:
                        close_side = "sell" if current_side == "LONG" else "buy"
                        close_price = self.get_current_price(symbol)
                        slippage_close = 0.0001
                        if close_side == "sell":
                            close_price -= slippage_close
                        else:
                            close_price += slippage_close

                        if current_side == "LONG":
                            pnl = (close_price - pos["entry_price"]) * amount
                        else:
                            pnl = (pos["entry_price"] - close_price) * amount

                        log.info(
                            f"Position {current_side} réduite à zéro sur {symbol} | "
                            f"Taille fermée: {amount:.4f} | Entry: {pos['entry_price']:.4f} | "
                            f"Close: {close_price:.4f} | P&L: {pnl:.2f} | {comment}"
                        )

                        self._positions[normalized] = {
                            "side": None,
                            "size": 0.0,
                            "entry_price": 0.0,
                            "mark_price": 0.0,
                            "unrealized_pnl": 0.0,
                            "liquidation_price": None,
                            "margin_used": 0.0,
                        }
                    else:
                        if current_side == "LONG":
                            pnl = (entry_price - pos["entry_price"]) * amount
                        else:
                            pnl = (pos["entry_price"] - entry_price) * amount

                        self._positions[normalized]["size"] = remaining_size
                        log.info(
                            f"Position {current_side} réduite sur {symbol} | "
                            f"Taille fermée: {amount:.4f} | Reste: {remaining_size:.4f} | "
                            f"Entry: {pos['entry_price']:.4f} | P&L partiel: {pnl:.2f} | {comment}"
                        )

                if not reduce_only and (sl is not None or tp is not None):
                    if sl is not None:
                        log.debug(f"SL placé pour {symbol} à {sl:.4f}")
                    if tp is not None:
                        log.debug(f"TP placé pour {symbol} à {tp:.4f}")

                return True

            except Exception as e:
                log.error(f"Échec de placement d'ordre sur {symbol} : {e}")
                return False
        return self._call_api(run, False)

    def _call_api(self, func, default_val):
        try:
            return func()
        except Exception as e:
            log.error(f"Erreur inattendue : {e}")
            return default_val

    def modify_sl_tp(self, symbol: str, sl: float, tp: float) -> bool:
        """
        Modifie le stop loss et take profit d'une position existante.
        """
        normalized = self._normalize_symbol(symbol)
        pos = self.get_position(symbol)
        if not pos or pos["size"] == 0:
            log.warning(f"️ modify_sl_tp : Aucune position ouverte sur {symbol}")
            return False

        sl = round(sl, 5) if sl > 0 else None
        tp = round(tp, 5) if tp > 0 else None

        def run():
            try:
                if sl is not None:
                    self._positions[normalized]["stop_loss"] = sl
                    log.info(f"️  SL mis à jour pour {symbol} à {sl:.4f}")
                if tp is not None:
                    self._positions[normalized]["take_profit"] = tp
                    log.info(f"️  TP mis à jour pour {symbol} à {tp:.4f}")
                return True
            except Exception as e:
                log.error(f"Échec de modification SL/TP sur {symbol} : {e}")
                return False
        return self._call_api(run, False)

    def get_min_order_size(self, symbol: str) -> float:
        """Retourne la taille minimale d'ordre autorisée pour un instrument forex."""
        return 0.001

    def get_step_size(self, symbol: str) -> float:
        """Retourne le pas de taille d'ordre (precision) pour un instrument forex."""
        return 0.000001

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalise un symbole selon le format attendu par le simulateur forex.
        """
        return self._normalize_symbol(symbol)

    def cancel_all_orders(self, symbol: str) -> bool:
        """Annule tous les ordres ouverts sur le symbole."""
        normalized = self._normalize_symbol(symbol)
        def run():
            log.info(f"Tous les ordres conditionnels annulés sur {symbol} (simulation)")
            return True
        return self._call_api(run, False)

    def _cancel_related_orders(self, symbol: str):
        pass

    def get_max_order_size(self, symbol: str) -> float:
        """Retourne la taille maximale d'ordre autorisée pour un instrument."""
        return 100.0

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """
        Génère des bougies historiques en simulation pour le forex.
        """
        normalized = self._normalize_symbol(symbol)
        return self._generate_simulated_candles(normalized, timeframe, limit)

    def _generate_simulated_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Génère un DataFrame OHLCV simulé pour le backtesting/paper trading."""
        import numpy as np
        
        # Résoudre le point de départ en temps basé sur le timeframe
        timeframe_deltas = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "30m": timedelta(minutes=30),
            "1h": timedelta(hours=1),
            "2h": timedelta(hours=2),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1),
            "1w": timedelta(weeks=1),
        }
        delta = timeframe_deltas.get(timeframe, timedelta(hours=1))
        
        # Générer des timestamps
        end_time = datetime.now()
        timestamps = [end_time - i * delta for i in range(limit)]
        timestamps.reverse()
        
        # Prix de départ
        base_price = 1.0800
        if "JPY" in symbol:
            base_price = 149.50
        elif "GBP" in symbol:
            base_price = 1.2600
        elif "CHF" in symbol:
            base_price = 0.8800
        elif "AUD" in symbol:
            base_price = 0.6500
        elif "CAD" in symbol:
            base_price = 1.3600
            
        # Simuler un mouvement (random walk avec drift)
        prices = [base_price]
        volatility = 0.001 if "JPY" not in symbol else 0.1
        for _ in range(limit - 1):
            change = np.random.normal(0, volatility)
            prices.append(max(prices[-1] + change, 0.0001))
            
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        for p in prices:
            # Créer la bougie
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
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes
        }, index=timestamps)
        
        df.index.name = "timestamp"
        return df


# Export des classes publiques
__all__ = ['PaperForexClient']