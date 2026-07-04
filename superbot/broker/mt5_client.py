"""
MetaTrader 5 (MT5) broker client.
Associated with Fusion Markets.
"""
import logging
import time
from datetime import datetime, timezone, timedelta
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

    def __init__(self, login: int = None, password: str = None, server: str = None, path: str = None, api_key: str = None, api_secret: str = None, **kwargs):
        if mt5 is None:
            raise ImportError(
                "Le module python MetaTrader5 n'est pas installé.\n"
                "Veuillez l'installer via 'pip install MetaTrader5' (système Windows uniquement)."
            )

        # Résoudre les paramètres (SaaS transmet les clés via api_key et api_secret)
        self._login = int(login or api_key or MT5_LOGIN)
        self._password = password or api_secret or MT5_PASSWORD
        self._server = server or MT5_SERVER
        self._path = path or MT5_PATH

        # Paramètres d'initialisation
        self._init_kwargs = {}
        if self._path:
            import os
            resolved_path = self._path
            if os.path.isdir(resolved_path):
                resolved_path = os.path.join(resolved_path, "terminal64.exe")
            self._init_kwargs["path"] = resolved_path
        if self._login > 0:
            self._init_kwargs["login"] = self._login
        if self._password:
            self._init_kwargs["password"] = self._password
        if self._server:
            self._init_kwargs["server"] = self._server

        if not self._connect_terminal():
            raise RuntimeError(
                "Impossible d'initialiser ou de se connecter au terminal MT5. "
                "Veuillez vérifier les logs et vous assurer que le terminal Fusion Markets est ouvert."
            )

    def _connect_terminal(self) -> bool:
        """Initialise la connexion au terminal MT5 et s'authentifie."""
        log.info(f"Initialisation de MetaTrader 5 (Serveur: {self._server})...")
        if not mt5.initialize(**self._init_kwargs):
            error_code = mt5.last_error()
            log.error(f"Échec de l'initialisation de MT5 : {error_code}")
            return False

        # Connexion au compte de trading
        if self._login > 0:
            authorized = mt5.login(login=self._login, password=self._password, server=self._server)
            if not authorized:
                error_code = mt5.last_error()
                log.error(f"Échec de l'authentification MT5 pour le compte {self._login} : {error_code}")
                return False

        acc_info = mt5.account_info()
        if acc_info:
            log.info(f"Connecté avec succès à MT5. Compte: {acc_info.login} | Solde: {acc_info.balance} {acc_info.currency}")
            return True
        else:
            log.warning("Connecté à MT5, mais impossible de récupérer les informations du compte.")
            return True

    def _call_api(self, api_func, default_val, *args, **kwargs):
        """
        Wrapper unifié pour les appels de fonctions MT5 avec gestion des retries et reconnexion.
        """
        max_retries = 3
        backoff = 0.5
        for attempt in range(1, max_retries + 1):
            try:
                res = api_func(*args, **kwargs)
                if res is None or res is False:
                    error_code = mt5.last_error()
                    log.warning(f"⚠️ Appel MT5 retourné {res} (code d'erreur: {error_code}). Tentative {attempt}/{max_retries}...")
                    if attempt < max_retries:
                        log.info("Tentative de reconnexion au terminal MT5...")
                        self._connect_terminal()
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                return res
            except Exception as e:
                if attempt == max_retries:
                    log.error(f"Échec critique de l'appel MT5 après {max_retries} tentatives : {e}")
                    return default_val
                log.warning(f"⚠️ Exception lors de l'appel MT5 : {e}. Tentative {attempt}/{max_retries} après {backoff}s...")
                log.info("Tentative de reconnexion au terminal MT5...")
                self._connect_terminal()
                time.sleep(backoff)
                backoff *= 2.0
        return default_val

    def get_default_instruments(self) -> List[str]:
        return ["EURUSD", "GBPUSD", "USDJPY"]

    def get_default_news_assets(self) -> List[str]:
        return ["EUR", "USD", "GBP", "JPY"]

    def get_asset_type(self) -> str:
        return "forex"

    def get_balance(self) -> float:
        """Retourne le solde disponible."""
        acc_info = self._call_api(mt5.account_info, None)
        return acc_info.balance if acc_info else 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        """Résumé complet du compte."""
        acc_info = self._call_api(mt5.account_info, None)
        if not acc_info:
            return {
                "balance": 0.0,
                "equity": 0.0,
                "unrealized_pnl": 0.0,
                "margin_used": 0.0,
                "free_margin": 0.0,
                "margin_level": 0.0,
                "open_positions": 0,
                "leverage": 1,
                "account_type": "MT5_FUSION_MARKETS",
            }

        positions = self._call_api(mt5.positions_get, [])
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
            "leverage": acc_info.leverage,
            "account_type": "MT5_REAL" if acc_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_REAL else "MT5_DEMO",
            "company": acc_info.company
        }

    def get_trade_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des trades fermés sur les N derniers jours depuis MT5.
        """
        if not mt5:
            log.error("Module MetaTrader5 non disponible")
            return []

        try:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()

            deals = self._call_api(lambda: mt5.history_deals_get(from_date, to_date), None)
            if deals is None:
                log.warning("Aucun deal d'historique trouvé ou erreur.")
                return []

            trades = []
            # Première passe : Identifier les deals de fermeture (EXIT)
            for deal in deals:
                if deal.entry == 1 and deal.symbol:  # entry == 1 est l'EXIT d'une position
                    side = "buy" if deal.type == 1 else "sell"
                    pnl = deal.profit + deal.commission + deal.swap + deal.fee
                    
                    trades.append({
                        'symbol': deal.symbol,
                        'side': side,
                        'entry_price': 0.0,  # sera résolu après
                        'exit_price': deal.price,
                        'pnl': pnl,
                        'size': deal.volume,
                        'timestamp': datetime.fromtimestamp(deal.time, timezone.utc),
                        'ticket': deal.ticket,
                        'position_id': deal.position_id
                    })

            # Deuxième passe : Trouver le prix d'entrée à partir du position_id
            pos_entries = {}
            for deal in deals:
                if deal.entry == 0 and deal.symbol:  # entry == 0 est l'ENTRY d'une position
                    pos_entries[deal.position_id] = deal.price

            for t in trades:
                pos_id = t['position_id']
                if pos_id in pos_entries:
                    t['entry_price'] = pos_entries[pos_id]

            # Trier les trades du plus récent au plus ancien
            trades.sort(key=lambda x: x['timestamp'], reverse=True)
            return trades
        except Exception as e:
            log.error(f"Erreur lors de la récupération de l'historique MT5 : {e}")
            return []

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
        self._call_api(lambda: mt5.symbol_select(symbol, True), False)

        rates = self._call_api(lambda: mt5.copy_rates_from_pos(symbol, mt5_tf, 0, limit), None)
        if rates is None or len(rates) == 0:
            log.warning(f"Impossible de récupérer les bougies de {symbol} depuis MT5")
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

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère les détails du symbole (contract_size, tick_size, tick_value) depuis MT5.
        """
        if not mt5:
            return {
                "contract_size": 100000.0,
                "tick_size": 0.00001,
                "tick_value": 1.0,
            }
        symbol = self.normalize_symbol(symbol)
        self._call_api(lambda: mt5.symbol_select(symbol, True), False)
        info = self._call_api(lambda: mt5.symbol_info(symbol), None)
        if not info:
            return {
                "contract_size": 100000.0,
                "tick_size": 0.00001,
                "tick_value": 1.0,
            }
        return {
            "contract_size": info.trade_contract_size if info.trade_contract_size > 0 else 100000.0,
            "tick_size": info.trade_tick_size if info.trade_tick_size > 0 else 0.00001,
            "tick_value": info.trade_tick_value if info.trade_tick_value > 0 else (info.trade_tick_size * info.trade_contract_size),
        }

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """
        Retourne la position ouverte sur un symbole.
        S'il y a plusieurs positions (Hedging), nous les combinons/aggrégons.
        """
        symbol = self.normalize_symbol(symbol)
        positions = self._call_api(lambda: mt5.positions_get(symbol=symbol), [])

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

        tick = self._call_api(lambda: mt5.symbol_info_tick(symbol), None)
        mark_price = (tick.bid + tick.ask) / 2 if tick else avg_entry

        # Convertir la taille de lots en unités de base currency pour être cohérent avec les autres brokers
        info = self._call_api(lambda: mt5.symbol_info(symbol), None)
        contract_size = info.trade_contract_size if info and info.trade_contract_size > 0 else 100000.0
        total_volume_units = total_volume * contract_size

        return {
            "ticket": first_pos.ticket,
            "side": dominant_side,
            "size": total_volume_units,
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
        positions = self._call_api(lambda: mt5.positions_get(symbol=symbol), [])
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
            tick = self._call_api(lambda: mt5.symbol_info_tick(symbol), None)
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
                "comment": f"Close #{ticket} - {reason}"[:29],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            log.info(f"Fermeture position MT5 #{ticket} sur {symbol} (Taille: {volume}, Type: {side})...")
            result = self._call_api(lambda: mt5.order_send(request), None)

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
        self._call_api(lambda: mt5.symbol_select(symbol, True), False)

        # Déterminer les prix d'entrée
        tick = self._call_api(lambda: mt5.symbol_info_tick(symbol), None)
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

        # S'assurer que la quantité respecte les contraintes du courtier (calculé en unités)
        min_units = self.get_min_order_size(symbol)
        step_units = self.get_step_size(symbol)
        amount = max(amount, min_units)
        amount = round(amount / step_units) * step_units

        # Convertir en lots pour MT5
        info = self._call_api(lambda: mt5.symbol_info(symbol), None)
        contract_size = info.trade_contract_size if info and info.trade_contract_size > 0 else 100000.0
        amount_lots = amount / contract_size

        # S'assurer du respect des limites minimales et du pas en lots
        volume_min = info.volume_min if info else 0.01
        volume_step = info.volume_step if info else 0.01
        amount_lots = max(amount_lots, volume_min)
        amount_lots = round(amount_lots / volume_step) * volume_step
        amount_lots = round(amount_lots, 4)

        # Nettoyer le commentaire pour nous assurer qu'il contient des caractères sûrs pour MT5
        base_comment = comment or f"SuperBot order - {side_upper}"
        cleaned_chars = []
        for c in str(base_comment):
            if ord(c) >= 128 or not c.isprintable():
                cleaned_chars.append('_')
            else:
                if c.isalnum() or c in (' ', '-', '_', '.'):
                    cleaned_chars.append(c)
                else:
                    cleaned_chars.append('_')
        cleaned = ''.join(cleaned_chars)
        if not cleaned:
            cleaned = f"SBOT-{side_upper}"
        final_comment = cleaned[:29]
        log.debug(f"Commentaire MT5 final : '{final_comment}' (original: '{base_comment}')")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(amount_lots),
            "type": order_type,
            "price": price,
            "sl": float(sl) if sl > 0 else 0.0,
            "tp": float(tp) if tp > 0 else 0.0,
            "deviation": 20,
            "magic": 10099,
            "comment": final_comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        log.info(f"Envoi de l'ordre MT5 : {side_upper} {amount_lots} {symbol} @ {price:.5f} (SL: {sl:.5f}, TP: {tp:.5f})")
        result = self._call_api(lambda: mt5.order_send(request), None)

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
        positions = self._call_api(lambda: mt5.positions_get(symbol=symbol), [])
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
            result = self._call_api(lambda: mt5.order_send(request), None)

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
        self._call_api(lambda: mt5.symbol_select(symbol, True), False)
        tick = self._call_api(lambda: mt5.symbol_info_tick(symbol), None)
        if tick is None:
            return 0.0
        return (tick.bid + tick.ask) / 2

    def get_spread(self, symbol: str) -> float:
        """Retourne le spread actuel en pips."""
        symbol = self.normalize_symbol(symbol)
        self._call_api(lambda: mt5.symbol_select(symbol, True), False)
        tick = self._call_api(lambda: mt5.symbol_info_tick(symbol), None)
        if tick is None or tick.bid == 0.0 or tick.ask == 0.0:
            return 0.0
        spread_raw = tick.ask - tick.bid
        normalized = symbol.upper().replace("/", "")
        pip_size = 0.01 if "JPY" in normalized else 0.0001
        return spread_raw / pip_size


    def get_min_order_size(self, symbol: str) -> float:
        symbol = self.normalize_symbol(symbol)
        info = self._call_api(lambda: mt5.symbol_info(symbol), None)
        if info:
            contract_size = info.trade_contract_size if info.trade_contract_size > 0 else 100000.0
            return info.volume_min * contract_size
        return 1000.0

    def get_step_size(self, symbol: str) -> float:
        symbol = self.normalize_symbol(symbol)
        info = self._call_api(lambda: mt5.symbol_info(symbol), None)
        if info:
            contract_size = info.trade_contract_size if info.trade_contract_size > 0 else 100000.0
            return info.volume_step * contract_size
        return 1000.0

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