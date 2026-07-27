import pytest
import threading
import time
from unittest.mock import MagicMock, patch

from superbot.orchestrator import SuperBot
from superbot.components.cycle_runner import run_main_loop

@pytest.fixture
def mock_bot():
    with patch('superbot.orchestrator.create_broker') as mock_create_broker:
        # Configuration minimale
        mock_broker = MagicMock()
        mock_broker.get_asset_type.return_value = "crypto"
        mock_broker.get_balance.return_value = 10000.0
        mock_broker.get_account_summary.return_value = {"equity": 10000.0}
        mock_broker.get_default_instruments.return_value = ["BTC/USDT"]
        
        mock_create_broker.return_value = mock_broker
        
        # Désactiver les éléments réseau lourds (Dashboard, Webhook, Télémétrie)
        with patch('superbot.orchestrator.ENABLE_DASHBOARD', False), \
             patch('superbot.orchestrator.WEBHOOK_ENABLED', False):
            
            bot = SuperBot()
            bot.telemetry = MagicMock()
            bot.telemetry.enabled = False
            
            return bot

def test_cycle_runner_graceful_shutdown(mock_bot):
    """Teste que la boucle principale démarre et s'arrête proprement."""
    
    # Simuler le démarrage du bot
    mock_bot.running = True
    
    # Lancer la boucle dans un thread séparé (comme en prod)
    thread = threading.Thread(target=run_main_loop, args=(mock_bot,))
    thread.start()
    
    # Laisser tourner la boucle un court instant
    time.sleep(0.5)
    
    # Demander l'arrêt
    mock_bot.running = False
    mock_bot.shutdown_event.set()
    
    # Attendre que le thread se termine
    thread.join(timeout=2.0)
    
    # Si le thread est toujours vivant, le test échoue (la boucle n'a pas quitté)
    assert not thread.is_alive(), "La boucle principale ne s'est pas arrêtée !"

def test_cycle_runner_processes_symbols(mock_bot):
    """Teste que la boucle appelle bien le traitement des symboles."""
    
    # On mock _process_symbol pour vérifier s'il est appelé
    mock_bot._process_symbol = MagicMock()
    mock_bot.running = True
    
    # Lancer la boucle
    thread = threading.Thread(target=run_main_loop, args=(mock_bot,))
    thread.start()
    
    # Attendre que le premier cycle commence
    time.sleep(0.5)
    
    # Arrêter
    mock_bot.running = False
    mock_bot.shutdown_event.set()
    thread.join(timeout=2.0)
    
    # _process_symbol aurait dû être appelé au moins une fois
    assert mock_bot._process_symbol.called
