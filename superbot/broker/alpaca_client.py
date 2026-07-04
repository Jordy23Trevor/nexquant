"""
Alpaca Markets Client.
"""
import logging
import math
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import pandas as pd

try:
    import alpaca_trade_api as tradeapi
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

from superbot.broker.base import Broker
from superbot.config import (
    ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_BASE_URL, ALPACA_API_VERSION,
    MIN_POSITION_SIZE, MAX_POSITION_SIZE, RISK_PCT
)

log = logging.getLogger("alpaca")


class AlpacaClient(Broker):
    """
    Client Alpaca Markets pour ETFs et actions US.
    Fournit un accès gratuit au paper trading et au trading réel avec zéro commission.
    Supporte les ordres market, limit, stop, trailing stop, etc.
    """

    def __init__(self, api_key: str = None, api_secret: str = None, base_url: str = None, **kwargs):
        if not ALPACA_AVAILABLE:
            raise ImportError(
                "alpaca-trade-api non installé.\n"
                "   → pip install alpaca-trade-api"
            )
        self._init_client(api_key, api_secret, base_url)

    def get_default_instruments(self) -> List[str]:
        return ["SPY", "QQQ", "AAPL"]

    def get_default_news_assets(self) -> List[str]:
        return ["SPY", "QQQ", "AAPL"]

    def get_asset_type(self) -> str:
        return "stock"

    def _init_client(self, api_key=None, api_secret=None, base_url=None):
        """Initialise le client Alpaca."""
        key = api_key or ALPACA_API_KEY
        secret = api_secret or ALPACA_API_SECRET
        url = base_url or ALPACA_BASE_URL
        self._api = tradeapi.REST(
            key,
            secret,
            base_url=url,
            api_version=ALPACA_API_VERSION
        )

        try:
            account = self._api.get_account()
            log.info(f"Connecté à Alpaca ({'paper' if 'paper' in url else 'live'})")
            log.info(f"   Compte: {account.account_number} | Status: {account.status}")
        except Exception as e:
            log.error(f"Échec de connexion à Alpaca : {e}")
            raise

    def _call_api(self, api_func, default_val, *args, **kwargs):
        max_retries = 3
        backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                return api_func(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "rate limit" in err_str or "too many requests" in err_str
                
                if attempt == max_retries:
                    log.error(f"Critical Alpaca API failure after {max_retries} attempts: {e}")
                    return default_val
                    
                sleep_duration = backoff * 2.0 if is_rate_limit else backoff
                log.warning(
                    f"⚠️ Alpaca API call failed ({e}). "
                    f"Attempt {attempt}/{max_retries}. Retrying in {sleep_duration:.2f}s..."
                )
                time.sleep(sleep_duration)
                backoff *= 2.0

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalise un symbole pour Alpaca.
        """
        return symbol.upper().replace("/", "")

    def _get_min_size(self, symbol: str) -> float:
        """Retourne la taille minimale d'ordre pour Alpaca."""
        # Pour les actions/ETFs, la taille minimale est de 1 share pour les bracket/stop/limit orders
        return 1.0

    def _get_step_size(self, symbol: str) -> float:
        """Retourne le pas de taille d'ordre pour Alpaca (précision)."""
        # Précision d'une action entière pour éviter le rejet des bracket orders
        return 1.0

    def _round_qty(self, symbol: str, qty: float) -> float:
        """Arrondit la quantité selon la précision Alpaca (actions entières)."""
        return float(math.floor(qty))

    def _round_price(self, symbol: str, price: float) -> float:
        """Arrondit le prix selon la précision Alpaca."""
        return round(price, 2)

    # ─── Compte ───────────────────────────────────────────────

    def get_balance(self) -> float:
        """Solde disponible en devise du compte."""
        def run():
            account = self._api.get_account()
            return float(account.cash) if hasattr(account, 'cash') else float(account.equity)
        return self._call_api(run, 0.0)

    def get_account_summary(self) -> Dict[str, Any]:
        """Résumé complet du compte Alpaca."""
        def run():
            account = self._api.get_account()
            positions = self._api.list_positions()

            equity = float(account.equity)
            last_equity = float(account.last_equity)
            unrealized_pl = sum(float(getattr(pos, 'unrealized_pl', 0.0)) for pos in positions)

            return {
                "balance":        float(account.cash) if hasattr(account, 'cash') else equity,
                "equity":         equity,
                "last_equity":    last_equity,
                "unrealized_pl":  unrealized_pl,
                "realized_pl":    equity - last_equity - unrealized_pl,
                "buying_power":   float(account.buying_power),
                "initial_margin": float(account.initial_margin) if hasattr(account, 'initial_margin') else 0.0,
                "maintenance_margin": float(account.maintenance_margin) if hasattr(account, 'maintenance_margin') else 0.0,
                "margin_used":    float(account.initial_margin) if hasattr(account, 'initial_margin') else 0.0,
                "open_positions": len(positions),
                "account_number": account.account_number,
                "status":         account.status,
                "trading_blocked": account.trading_blocked,
                "transfers_blocked": account.transfers_blocked,
                "account_type":   "PAPER" if 'paper' in ALPACA_BASE_URL else "LIVE",
            }
        return self._call_api(run, {})

    # ─── Données marché ───────────────────────────────────────

    def fetch_candles(self, symbol: str, timeframe: str,
                      limit: int = 500) -> pd.DataFrame:
        """
        Télécharge les barres historiques Alpaca → DataFrame OHLCV.
        """
        timeframe_map = {
            "1m": "1Min", "5m": "5Min", "15m": "15Min", "30m": "30Min",
            "1h": "1Hour", "2h": "2Hour", "4h": "4Hour", "6h": "6Hour",
            "1d": "1Day", "1w": "1Week", "1M": "1Day"
        }
        alpaca_timeframe = timeframe_map.get(timeframe, timeframe)
        alpaca_symbol = self._normalize_symbol(symbol)

        from datetime import datetime, timedelta
        # Calculer un start date de sécurité basé sur la granularité et la limite (marché US fermé le week-end et ouvert 6.5h/jour)
        tf_lower = timeframe.lower()
        if tf_lower.endswith("m"):
            mins_per_bar = int(tf_lower[:-1])
            days_needed = max(7, int((limit * mins_per_bar) / 390 * 2.0))
        elif tf_lower.endswith("h"):
            hours_per_bar = int(tf_lower[:-1])
            days_needed = max(10, int((limit * hours_per_bar) / 6.5 * 2.0))
        elif tf_lower.endswith("d"):
            days_needed = max(30, int(limit * 1.5))
        elif tf_lower.endswith("w"):
            days_needed = max(90, int(limit * 7 * 1.5))
        else:
            days_needed = limit * 2
            
        start_date = (datetime.now() - timedelta(days=days_needed)).strftime('%Y-%m-%d')

        try:
            bars = self._api.get_bars(
                alpaca_symbol,
                alpaca_timeframe,
                start=start_date,
                limit=limit,
                adjustment='raw'
            ).df

            if bars.empty:
                return pd.DataFrame()

            bars = bars.tz_convert('UTC') if bars.index.tz else bars.tz_localize('UTC')

            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in bars.columns for col in required_cols):
                log.warning(f"️  Colonnes manquantes dans les données Alpaca pour {symbol}")
                return pd.DataFrame()

            df = bars[required_cols].copy()
            log.debug(f"{len(df)} barres {symbol}/{timeframe}")
            return df

        except Exception as e:
            log.error(f"fetch_candles {symbol}/{timeframe} : {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> float:
        """Prix mark/courant pour un symbole Alpaca."""
        alpaca_symbol = self._normalize_symbol(symbol)
        try:
            trade = self._api.get_latest_trade(alpaca_symbol)
            return float(trade.price)
        except Exception as e:
            log.warning(f"️  Impossible d'obtenir le prix actuel pour {symbol} : {e}")
            try:
                from datetime import datetime, timedelta
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                bars = self._api.get_bars(alpaca_symbol, "1Min", start=start_date, limit=1).df
                if not bars.empty:
                    return float(bars['close'].iloc[-1])
            except:
                pass
            return 0.0

    # ─── Positions ────────────────────────────────────────────

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """Retourne la position ouverte sur un symbole Alpaca."""
        alpaca_symbol = self._normalize_symbol(symbol)
        def run():
            try:
                position = self._api.get_position(alpaca_symbol)
                qty = float(position.qty)
                return {
                    "side":           "LONG" if qty > 0 else "SHORT",
                    "size":            abs(qty),
                    "entry_price":    float(position.avg_entry_price),
                    "mark_price":     float(position.market_value) / abs(qty) if qty != 0 else 0.0,
                    "unrealized_pnl": float(position.unrealized_pl),
                    "liquidation_price": None,
                    "margin_used":    float(position.market_value) if hasattr(position, 'market_value') else 0.0,
                }
            except Exception:
                return {}
        return self._call_api(run, {})

    def close_position(self, symbol: str, reason: str = "") -> bool:
        """Ferme la position ouverte au prix du marché."""
        alpaca_symbol = self._normalize_symbol(symbol)
        pos = self.get_position(symbol)
        if not pos:
            log.info(f"ℹ️  Aucune position à fermer sur {symbol}")
            return False

        side   = pos["side"]
        size    = pos["size"]
        close_side = "sell" if side == "LONG" else "buy"

        def run():
            try:
                # Annuler d'abord tous les ordres en cours sur ce symbole pour éviter les ordres fantômes
                self.cancel_all_orders(symbol)
                
                self._api.submit_order(
                    symbol=alpaca_symbol,
                    qty=size,
                    side=close_side,
                    type="market",
                    time_in_force="day",
                )
                log.info(f"Position {side} fermée sur {symbol} | {reason}")
                return True
            except Exception as e:
                log.error(f"Échec de fermeture de position sur {symbol} : {e}")
                return False
        return self._call_api(run, False)

    # ─── Ordres ───────────────────────────────────────────────

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

        # Taille de base sans levier
        base_size = risk_amount / risk_per_unit
        leveraged_size = base_size

        # Appliquer les limites
        target_symbol = symbol if symbol else "SPY"
        min_size = self.get_min_order_size(symbol=target_symbol)
        max_size = self.get_step_size(symbol=target_symbol) * 1000000

        final_size = max(min(leveraged_size, max_size), min_size)
        return self._round_qty(target_symbol, final_size)

    def place_order(self, symbol: str, side: str, amount: float,
                   sl: float, tp: float, reduce_only: bool = False,
                   comment: str = "") -> bool:
        """
        Place un ordre de marché avec stop loss et take profit.
        """
        alpaca_symbol = self._normalize_symbol(symbol)
        side_alpaca = "buy" if side.lower() == "buy" else "sell"
        amount_rounded = self._round_qty(symbol, amount)
        if amount_rounded <= 0:
            log.warning(
                f"⚠️ Quantité d'ordre nulle ou insuffisante pour {symbol} "
                f"(demandé: {amount}, arrondi: {amount_rounded}). L'ordre est ignoré."
            )
            return False
        amount = amount_rounded
        sl = self._round_price(symbol, sl) if sl > 0 else None
        tp = self._round_price(symbol, tp) if tp > 0 else None

        def run():
            try:
                order_params = {
                    "symbol": alpaca_symbol,
                    "qty": amount,
                    "side": side_alpaca,
                    "type": "market",
                    "time_in_force": "day",
                }

                if sl is not None or tp is not None:
                    order_params["order_class"] = "bracket"
                    if sl is not None:
                        order_params["stop_loss"] = {"stop_price": sl}
                    if tp is not None:
                        order_params["take_profit"] = {"limit_price": tp}

                if reduce_only and self.get_asset_type() == "crypto":
                    order_params["reduce_only"] = True

                order = self._api.submit_order(**order_params)

                arrow = "▲" if side == "buy" else "▼"
                sl_str = f"SL: {sl:,.2f}" if sl is not None else "SL: None"
                tp_str = f"TP: {tp:,.2f}" if tp is not None else "TP: None"
                log.info(
                    f"{arrow} {side} {amount} {symbol} @ market | {sl_str} | {tp_str} | {comment}"
                )
                return True

            except Exception as e:
                log.error(f"Échec de placement d'ordre sur {symbol} : {e}")
                return False
        return self._call_api(run, False)

    def modify_sl_tp(self, symbol: str, sl: float, tp: float) -> bool:
        """
        Modifie le stop loss et take profit d'une position existante.
        Au lieu d'annuler tous les ordres et d'en renvoyer un au marché, on remplace les ordres existants.
        """
        alpaca_symbol = self._normalize_symbol(symbol)
        pos = self.get_position(symbol)
        if not pos:
            log.warning(f"️ modify_sl_tp : Aucune position ouverte sur {symbol}")
            return False

        close_side = "sell" if pos["side"] == "LONG" else "buy"
        size = pos["size"]
        sl = self._round_price(symbol, sl) if sl > 0 else None
        tp = self._round_price(symbol, tp) if tp > 0 else None

        def run():
            try:
                orders = self._api.list_orders(status="open")
                success = False
                
                for order in orders:
                    if order.symbol != alpaca_symbol:
                        continue
                    
                    # Ordre Stop Loss (stop ou stop_limit)
                    if order.type in ["stop", "stop_limit"] and sl is not None:
                        try:
                            self._api.replace_order(order.id, stop_price=sl)
                            log.info(f"Stop Loss mis à jour pour {symbol} sur Alpaca : {sl}")
                            success = True
                        except Exception as e:
                            log.error(f"Échec de mise à jour du SL pour {symbol} sur Alpaca : {e}")
                    
                    # Ordre Take Profit (limit)
                    elif order.type == "limit" and tp is not None:
                        try:
                            self._api.replace_order(order.id, limit_price=tp)
                            log.info(f"Take Profit mis à jour pour {symbol} sur Alpaca : {tp}")
                            success = True
                        except Exception as e:
                            log.error(f"Échec de mise à jour du TP pour {symbol} sur Alpaca : {e}")

                # Si aucun ordre n'existait, on en crée de nouveaux
                if not success:
                    if sl is not None:
                        try:
                            self._api.submit_order(
                                symbol=alpaca_symbol,
                                qty=size,
                                side=close_side,
                                type="stop",
                                stop_price=sl,
                                time_in_force="gtc"
                            )
                            log.info(f"Nouveau Stop Loss créé pour {symbol} sur Alpaca : {sl}")
                            success = True
                        except Exception as e:
                            log.error(f"Échec de création du nouveau SL pour {symbol} sur Alpaca : {e}")
                    
                    if tp is not None:
                        try:
                            self._api.submit_order(
                                symbol=alpaca_symbol,
                                qty=size,
                                side=close_side,
                                type="limit",
                                limit_price=tp,
                                time_in_force="gtc"
                            )
                            log.info(f"Nouveau Take Profit créé pour {symbol} sur Alpaca : {tp}")
                            success = True
                        except Exception as e:
                            log.error(f"Échec de création du nouveau TP pour {symbol} sur Alpaca : {e}")

                return success

            except Exception as e:
                log.error(f"Échec de modification SL/TP sur {symbol} : {e}")
                return False
        return self._call_api(run, False)

    # ─── Méthodes utilitaires ────────────────────────────────────────

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Retourne les informations du symbole (contract_size, tick_size, tick_value) pour Alpaca.
        """
        return {
            "contract_size": 1.0,
            "tick_size": 0.01,
            "tick_value": 0.01,
        }

    def get_min_order_size(self, symbol: str) -> float:
        """Retourne la taille minimale d'ordre autorisée pour un instrument."""
        return self._get_min_size(symbol)

    def get_step_size(self, symbol: str) -> float:
        """Retourne le pas de taille d'ordre (precision) pour un instrument."""
        return self._get_step_size(symbol)

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalise un symbole selon le format attendu par Alpaca.
        """
        normalized = symbol.strip().upper()

        if "/" not in normalized and "=X" not in normalized:
            if len(normalized) == 6 and normalized.isalpha():
                return f"{normalized}=X"
            return normalized

        return normalized.replace("/", "")

    def cancel_all_orders(self, symbol: str) -> bool:
        """Annule tous les ordres ouverts (standards et OCO) sur le symbole."""
        alpaca_symbol = self._normalize_symbol(symbol)
        def run():
            try:
                orders = self._api.get_orders(status="open", symbols=[alpaca_symbol])
                for order in orders:
                    self._api.cancel_order(order.id)
                log.info(f"Tous les ordres annulés sur {symbol}")
                return True
            except Exception as e:
                log.warning(f"️  Échec d'annulation des ordres sur {symbol} : {e}")
                return False
        return self._call_api(run, False)


# Export des classes publiques
__all__ = ['AlpacaClient']