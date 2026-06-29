import requests
import hmac
import hashlib
import json
import logging
import os
from typing import Dict, Any, Optional

log = logging.getLogger("telemetry")

class TelemetryClient:
    """
    Client de télémétrie pour connecter le bot local à la plateforme Web NexQuant.
    Gère la signature HMAC-SHA256, l'envoi de données (ingest) et la récupération de configuration.
    """

    def __init__(self, api_url: Optional[str] = None, user_id: Optional[str] = None, ingest_token: Optional[str] = None):
        # Charger les configurations depuis .env si non passées en paramètres
        self.api_url = api_url or os.getenv("NEXQUANT_API_URL", "http://localhost:8080")
        self.user_id = user_id or os.getenv("NEXQUANT_USER_ID")
        self.ingest_token = ingest_token or os.getenv("NEXQUANT_INGEST_TOKEN")
        self.enabled = bool(self.user_id and self.ingest_token)

        if not self.enabled:
            log.warning("⚠️  Télémétrie désactivée : NEXQUANT_USER_ID ou NEXQUANT_INGEST_TOKEN non configuré dans .env")
        else:
            log.info(f"Télémétrie activée pour l'utilisateur {self.user_id} sur {self.api_url}")

    def _sign_payload(self, payload_str: str) -> str:
        """Calcule la signature HMAC-SHA256 du corps de la requête."""
        if not self.ingest_token:
            return ""
        return hmac.new(
            self.ingest_token.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _post(self, endpoint: str, data: dict) -> Optional[dict]:
        """Envoie une requête POST sécurisée et signée au serveur."""
        if not self.enabled:
            return None

        url = f"{self.api_url.rstrip('/')}/api/public/{endpoint}"
        
        # Stringify le body de manière déterministe pour la signature
        body_str = json.dumps(data, separators=(',', ':'))
        signature = self._sign_payload(body_str)

        headers = {
            "Content-Type": "application/json",
            "x-user-id": self.user_id,
            "x-signature": signature
        }

        try:
            response = requests.post(url, data=body_str, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                log.error("❌ Licence expirée ou invalide. Le bot va être arrêté.")
                return {"error": "licence_expired", "is_expired": True}
            else:
                log.debug(f"Erreur d'ingestion [{response.status_code}] : {response.text}")
                return None
        except Exception as e:
            log.debug(f"Impossible de contacter le serveur de télémétrie : {e}")
            return None

    def push_heartbeat(self, is_running: bool, broker_type: str, testnet: bool) -> bool:
        """Envoie un signal de présence (heartbeat) du bot."""
        payload = {
            "kind": "heartbeat",
            "user_id": self.user_id,
            "payload": {
                "is_running": is_running,
                "broker_type": broker_type,
                "testnet": testnet
            }
        }
        res = self._post("ingest", payload)
        return res is not None and not res.get("is_expired", False)

    def push_equity(self, equity: float, pnl_total: float = 0.0, drawdown: float = 0.0) -> bool:
        """Envoie une capture de la courbe d'équité."""
        payload = {
            "kind": "equity",
            "user_id": self.user_id,
            "payload": {
                "equity": float(equity),
                "pnl_total": float(pnl_total),
                "drawdown": float(drawdown)
            }
        }
        res = self._post("ingest", payload)
        return res is not None

    def push_position(self, symbol: str, side: str, qty: float, entry_price: float, current_price: float, pnl: float, pnl_pct: float, status: str = "open", broker: str = "binance") -> bool:
        """Envoie les détails d'une position ouverte ou fermée."""
        payload = {
            "kind": "position",
            "user_id": self.user_id,
            "payload": {
                "symbol": symbol,
                "side": side.lower(),  # "long" ou "short"
                "qty": float(qty),
                "entry_price": float(entry_price),
                "current_price": float(current_price),
                "pnl": float(pnl),
                "pnl_pct": float(pnl_pct),
                "status": status,  # "open" ou "closed"
                "broker": broker
            }
        }
        res = self._post("ingest", payload)
        return res is not None

    def push_log(self, level: str, message: str, source: str = "engine") -> bool:
        """Envoie un log d'exécution pour affichage distant."""
        # Adapter les niveaux log Python aux niveaux attendus par Supabase
        lvl_map = {
            "DEBUG": "debug",
            "INFO": "info",
            "WARNING": "warn",
            "ERROR": "error",
            "CRITICAL": "error",
            "SUCCESS": "success"
        }
        mapped_level = lvl_map.get(level.upper(), "info")

        payload = {
            "kind": "log",
            "user_id": self.user_id,
            "payload": {
                "level": mapped_level,
                "source": source,
                "message": message
            }
        }
        res = self._post("ingest", payload)
        return res is not None

    def push_regime(self, symbol: str, regime: str, confidence: float, trend_direction: str = "neutral", news_sentiment: float = 0.0) -> bool:
        """Envoie l'état du régime de marché."""
        payload = {
            "kind": "regime",
            "user_id": self.user_id,
            "payload": {
                "symbol": symbol,
                "regime": regime.lower(),  # "trending", "ranging", "volatile"
                "confidence": float(confidence),
                "trend_direction": trend_direction.lower(),  # "up", "down", "neutral"
                "news_sentiment": float(news_sentiment)
            }
        }
        res = self._post("ingest", payload)
        return res is not None

    def sync_config(self, current_version: str = "v1.0.0") -> Optional[dict]:
        """
        Récupère la configuration de trading, les clés API du broker et vérifie les mises à jour.
        Retourne la configuration si succès, None en cas d'erreur ou dict avec 'is_expired': True si la licence a expiré.
        """
        if not self.enabled:
            return None

        payload = {
            "user_id": self.user_id,
            "version": current_version
        }
        
        return self._post("config", payload)


class TelemetryLoggingHandler(logging.Handler):
    """
    Handler de logging Python redirigeant automatiquement les logs significatifs
    vers l'API de télémétrie NexQuant.
    """
    def __init__(self, telemetry_client: TelemetryClient):
        super().__init__()
        self.telemetry_client = telemetry_client
        # Filtrer pour ne pousser que les événements importants (INFO, WARNING, ERROR, CRITICAL)
        self.setLevel(logging.INFO)

    def emit(self, record):
        try:
            # Éviter la récursion infinie
            if record.name in ("telemetry", "urllib3", "requests"):
                return
            
            message = self.format(record)
            self.telemetry_client.push_log(
                level=record.levelname,
                message=message,
                source=record.name
            )
        except Exception:
            pass
