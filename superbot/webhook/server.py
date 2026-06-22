"""
Webhook server for SuperBot Trading Unifié.
Reçoit des alertes externes (ex: TradingView) et les traite pour déclencher des actions de trading.
"""

import json
import logging
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse

log = logging.getLogger("webhook")


class WebhookHandler(BaseHTTPRequestHandler):
    """Gestionnaire HTTP pour les webhooks entrants."""

    def __init__(self, *args, webhook_secret: str = None, callback_func = None, **kwargs):
        self.webhook_secret = webhook_secret
        self.callback_func = callback_func
        super().__init__(*args, **kwargs)

    def do_POST(self):
        """Traite les requêtes POST entrantes."""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_error(400, "No content")
            return

        # Lire le corps de la requête
        post_data = self.rfile.read(content_length)
        content_type = self.headers.get('Content-Type', '')

        try:
            # Parser les données selon le content-type
            if 'application/json' in content_type:
                data = json.loads(post_data.decode('utf-8'))
            elif 'application/x-www-form-urlencoded' in content_type:
                # Pour les données formulaire (comme TradingView parfois)
                parsed = urllib.parse.parse_qs(post_data.decode('utf-8'))
                data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            else:
                # Essayer de parser comme JSON par défaut
                data = json.loads(post_data.decode('utf-8'))

            log.info(f"Webhook reçu: {json.dumps(data, indent=2)[:500]}...")

            # Vérifier la signature ou le secret dans le body si un secret est configuré
            if self.webhook_secret:
                has_valid_sig = self._verify_signature(post_data, self.headers.get('X-Signature', ''))
                has_valid_body_sec = isinstance(data, dict) and data.get('secret') == self.webhook_secret
                
                if not (has_valid_sig or has_valid_body_sec):
                    log.warning("Signature ou secret de webhook invalide")
                    self.send_error(401, "Invalid signature or secret")
                    return

            # Traiter les données du webhook
            if self.callback_func:
                try:
                    result = self.callback_func(data)
                    log.info(f"Callback webhook exécuté avec résultat: {result}")
                except Exception as e:
                    log.error(f"Erreur lors de l'exécution du callback webhook: {e}")
                    self.send_error(500, "Callback execution failed")
                    return

            # Répondre avec succès
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "success", "timestamp": datetime.now().isoformat()}
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except json.JSONDecodeError:
            log.error("Impossible de parser les données JSON du webhook")
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            log.error(f"Erreur lors du traitement du webhook: {e}")
            self.send_error(500, "Internal server error")

    def do_GET(self):
        """Traite les requêtes GET (pour les health checks)."""
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "SuperBot Webhook Server",
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, "Not found")

    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Vérifie la signature HMAC du webhook.

        Args:
            payload: Corps de la requête
            signature: Signature fournie dans l'en-tête

        Returns:
            True si la signature est valide, False sinon
        """
        if not self.webhook_secret or not signature:
            return False

        try:
            # Supporter différents formats de signature
            if signature.startswith('sha256='):
                signature = signature[7:]  # Enlever le préfixe 'sha256='

            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            log.error(f"Erreur lors de la vérification de la signature: {e}")
            return False

    def log_message(self, format, *args):
        """Override pour désactiver les logs HTTP par défaut (utiliser notre propre logger)."""
        log.debug("%s - - [%s] %s" %
                  (self.address_string(),
                   self.log_date_time_string(),
                   format % args))


class WebhookServer:
    """Serveur webhook pour SuperBot."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080,
                 webhook_secret: str = None, callback_func = None):
        """
        Initialise le serveur webhook.

        Args:
            host: Adresse d'écoute
            port: Port d'écoute
            webhook_secret: Secret pour vérifier les signatures HMAC (optionnel)
            callback_func: Fonction à appeler lorsque un webhook est reçu
        """
        self.host = host
        self.port = port
        self.webhook_secret = webhook_secret
        self.callback_func = callback_func
        self.server = None
        self.server_thread = None
        self.running = False

        log.info(f"WebhookServer configuré sur {host}:{port}")

    def start(self):
        """Démarre le serveur webhook en arrière-plan."""
        if self.running:
            log.warning("️  Le serveur webhook est déjà en cours d'exécution")
            return

        def handler_factory(*args, **kwargs):
            return WebhookHandler(*args,
                                webhook_secret=self.webhook_secret,
                                callback_func=self.callback_func,
                                **kwargs)

        self.server = HTTPServer((self.host, self.port), handler_factory)
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        log.info(f"Serveur webhook démarré sur {self.host}:{self.port}")

    def stop(self):
        """Arrête le serveur webhook."""
        if not self.running:
            log.warning("️  Le serveur webhook n'est pas en cours d'exécution")
            return

        log.info("Arrêt du serveur webhook...")
        self.running = False
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5.0)
        log.info("Serveur webhook arrêté")

    def _run_server(self):
        """Boucle principale du serveur."""
        log.info(f"Serveur webhook en écoute sur {self.host}:{self.port}")
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Ne pas logger l'erreur si on est en train d'arrêter
                log.error(f"Erreur dans le serveur webhook: {e}")
        finally:
            log.info("Boucle du serveur webhook terminée")


# Fonction utilitaire pour créer un callback de trading simple
def create_trading_callback(broker, strategy, risk_manager, news_manager):
    """
    Crée une fonction callback pour traiter les webhooks de trading.

    Args:
        broker: Instance du broker
        strategy: Instance de la stratégie
        risk_manager: Instance du gestionnaire de risque
        news_manager: Instance du gestionnaire de nouvelles

    Returns:
        Fonction callback à passer au webhook server
    """
    def callback(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite les données du webhook et génère potentiellement un signal de trading.

        Args:
            data: Données reçues du webhook

        Returns:
            Résultat du traitement
        """
        try:
            log.info(f"Traitement du callback webhook: {data}")

            # Exemple de structure de données attendue (à adapter selon votre source)
            # {
            #   "symbol": "BTC/USDT",
            #   "action": "buy" or "sell",
            #   "price": 50000.0,
            #   "strength": 0.8,  # Force du signal (0-1)
            #   "source": "TradingView",
            #   "timestamp": "2023-01-01T12:00:00Z"
            # }

            symbol = data.get('symbol')
            action = data.get('action')
            price = data.get('price')
            strength = data.get('strength', 1.0)
            source = data.get('source', 'unknown')

            if not all([symbol, action, price]):
                return {"error": "Missing required fields: symbol, action, price"}

            # Vérifier les filtres de nouvelles
            should_avoid, news_event = news_manager.should_avoid_trading_due_to_news(symbol)
            if should_avoid:
                log.info(f"Trading évité pour {symbol} à cause des nouvelles: {news_event.title if news_event else 'Unknown'}")
                return {"action": "skipped", "reason": "news_avoidance", "news_event": str(news_event) if news_event else None}

            # Ici, on pourrait intégrer le webhook dans la stratégie existante
            # Pour l'instant, on log simplement l'alerte
            log.info(f"Alerte de trading reçue: {action.upper()} {symbol} @ {price} (force: {strength}) depuis {source}")

            # Dans une implémentation complète, on retournerait un signal à traiter par la boucle principale
            return {
                "status": "processed",
                "symbol": symbol,
                "action": action,
                "price": price,
                "strength": strength,
                "source": source,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            log.error(f"Erreur lors du traitement du callback webhook: {e}")
            return {"error": str(e)}

    return callback


# Export des classes et fonctions publiques
__all__ = [
    'WebhookServer',
    'WebhookHandler',
    'create_trading_callback'
]