"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╩
"""
import asyncio
import signal
import sys
import os

# S'assurer que le dossier racine du projet est dans le path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

class SafeStreamWrapper:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        try:
            self.stream.write(data)
            self.stream.flush()
        except UnicodeEncodeError:
            try:
                encoding = getattr(self.stream, 'encoding', 'ascii') or 'ascii'
                safe_data = data.encode(encoding, errors='backslashreplace').decode(encoding)
                self.stream.write(safe_data)
                self.stream.flush()
            except Exception:
                pass
    def flush(self):
        try:
            self.stream.flush()
        except Exception:
            pass
    def __getattr__(self, name):
        return getattr(self.stream, name)

sys.stdout = SafeStreamWrapper(sys.stdout)
sys.stderr = SafeStreamWrapper(sys.stderr)
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import threading
import traceback

# Importer les modules du SuperBot
from superbot.config import (
    BROKER_TYPE, INSTRUMENTS, GRANULARITY, ENABLE_PAPER_TRADING,
    LOG_LEVEL, ENABLE_DASHBOARD, WEBHOOK_ENABLED,
    WEBHOOK_SECRET, WEBHOOK_HOST, WEBHOOK_PORT,
    
    # Risk Management
    RISK_PCT, MAX_DAILY_LOSS_PCT, MAX_MONTHLY_LOSS_PCT, MAX_OPEN_POSITIONS,
    KELLY_FRACTION, MIN_TRADES_FOR_KELLY, SL_ATR_MULT, TP_ATR_MULT,
    TRAIL_ATR_MULT, BE_ATR_MULT, MIN_POSITION_SIZE, MAX_POSITION_SIZE,
    
    # Strategy / Indicators
    SCORE_MIN, EMA_FAST, EMA_SLOW, EMA_TREND, HTF_EMA, D1_EMA, W1_EMA,
    RSI_LEN, RSI_OB, RSI_OS, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    ADX_LEN, ADX_TREND, ST_MULTIPLIER, ST_ATR_LEN, ATR_LEN,
    BB_LEN, BB_STD, ICHIMOKU_TENKAN, ICHIMOKU_KIJUN,
    ICHIMOKU_SENKOU_SPAN_B, ICHIMOKU_DISPLACEMENT, VWAP_WINDOW,
    
    # News & Sentiment
    NEWS_ASSETS, NEWS_UPDATE_INTERVAL, NEWS_AVOIDANCE_BEFORE, NEWS_AVOIDANCE_AFTER,
    NEWS_RISK_REDUCTION_FACTOR, NEWS_HIGH_IMPACT_ONLY, FEAR_GREED_EXTREME_FEAR,
    FEAR_GREED_EXTREME_GREED, CRYPTOCOMPARE_API_KEY
)
from superbot.broker import create_broker
from superbot.strategy import TradingStrategy
from superbot.risk import RiskManager
from superbot.news import NewsManager
from superbot.indicators.technical_indicators import TechnicalIndicators

# Importer les modules optionnels
try:
    from superbot.dashboard import Dashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    log = None  # Sera initialisé plus bas

try:
    from superbot.logger import setup_logging
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False

# Configurer le logging
import logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("superbot/logs/superbot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("main")

class SuperBot:
    """
    Orchestrateur principal du SuperBot Trading Unifié.
    Gère la coordination entre tous les composants : broker, stratégie, risque, nouvelles, etc.
    """

    def __init__(self):
        """Initialise le SuperBot avec tous ses composants."""
        log.info("Initialisation du SuperBot Trading Unifié")

        # État du bot
        self.running = False
        self.shutdown_event = threading.Event()

        # Composants principaux
        self.broker = None
        self.strategy = None
        self.risk_manager = None
        self.news_manager = None
        self.technical_indicators = None
        self.dashboard = None

        # Données de marché et états
        self.market_data: Dict[str, any] = {}  # Symbol -> DataFrame avec indicateurs
        self.positions: Dict[str, Dict] = {}   # Symbol -> position info
        self.active_orders: Dict[str, Dict] = {} # Symbol -> ordre info
        self.instruments: List[str] = []
        self.news_assets: List[str] = []
        self.initial_balance: float = 10000.0

        # Paramètres adaptatifs
        self.adaptive_risk_pct = RISK_PCT
        self.adaptive_score_min = SCORE_MIN
        self._adaptation_counter = 0
        self._adaptation_every = 10  # cycles

        # Statistiques et monitoring
        self.stats = {
            'start_time': None,
            'cycles_completed': 0,
            'signals_generated': 0,
            'trades_executed': 0,
            'errors_count': 0,
            'last_cycle_time': None
        }

        # Initialiser les composants
        self._initialize_components()

    def _initialize_components(self):
        """Initialise tous les composants du bot."""
        try:
            log.info("Initialisation des composants...")

            # 1. Créer le broker
            log.info(f"Création du broker : {BROKER_TYPE}")
            self.broker = create_broker(BROKER_TYPE)
            log.info("Broker initialisé")
            
            try:
                self.initial_balance = self.broker.get_balance()
                log.info(f"Solde initial détecté : {self.initial_balance}")
            except Exception as e:
                log.warning(f"️  Impossible de récupérer le solde initial : {e}")
                self.initial_balance = 10000.0

            # Déterminer les instruments selon le broker (clés spécifiques au broker en priorité)
            broker_type = BROKER_TYPE  # "binance", "alpaca", "paper_forex", "mt5"
            broker_key = f"INSTRUMENTS_{broker_type.upper()}"  # ex: INSTRUMENTS_MT5
            env_instruments_broker = os.getenv(broker_key)
            env_instruments_generic = os.getenv("INSTRUMENTS")

            if env_instruments_broker:
                self.instruments = [s.strip() for s in env_instruments_broker.split(",") if s.strip()]
                log.info(f"Instruments spécifiques au broker ({broker_key}) : {self.instruments}")
            elif env_instruments_generic:
                self.instruments = [s.strip() for s in env_instruments_generic.split(",") if s.strip()]
                log.info(f"Instruments configurés via la variable générique INSTRUMENTS : {self.instruments}")
            else:
                self.instruments = self.broker.get_default_instruments()
                log.info(f"Aucun instrument configuré — défauts courtier ({BROKER_TYPE}) : {self.instruments}")

            news_broker_key = f"NEWS_ASSETS_{BROKER_TYPE.upper()}"
            env_news_assets_broker = os.getenv(news_broker_key)
            env_news_assets_generic = os.getenv("NEWS_ASSETS")
            if env_news_assets_broker:
                self.news_assets = [s.strip().upper() for s in env_news_assets_broker.split(",")]
                log.info(f"Actifs de nouvelles spécifiques au broker ({news_broker_key}) : {self.news_assets}")
            elif env_news_assets_generic:
                self.news_assets = [s.strip().upper() for s in env_news_assets_generic.split(",")]
                log.info(f"Actifs de nouvelles configurés via .env : {self.news_assets}")
            else:
                self.news_assets = self.broker.get_default_news_assets()
                log.info(f"Actifs de nouvelles — défauts broker ({BROKER_TYPE}) : {self.news_assets}")

            # 2. Créer le gestionnaire de risques
            asset_type = self.broker.get_asset_type()
            default_min_pos = MIN_POSITION_SIZE
            default_max_pos = MAX_POSITION_SIZE
            
            if asset_type == "forex":
                # Pour le forex, les tailles sont en unités de devise (ex: 1000 EUR)
                default_min_pos = 1.0
                default_max_pos = 10000000.0
            elif asset_type == "stock":
                # Pour les actions, les tailles sont en actions (ex: 1 action SPY = ~500 USD)
                default_min_pos = 0.001
                default_max_pos = 100000.0
            elif asset_type == "crypto":
                # Pour la crypto, les tailles sont en jetons (ex: 0.001 BTC, 0.1 SOL)
                default_min_pos = 0.001
                default_max_pos = 1000000.0

            # Permettre à l'utilisateur de surcharger via .env s'ils ont explicitement configuré ces variables
            env_min_pos = os.getenv("MIN_POSITION_SIZE")
            env_max_pos = os.getenv("MAX_POSITION_SIZE")
            actual_min_pos = float(env_min_pos) if env_min_pos else default_min_pos
            actual_max_pos = float(env_max_pos) if env_max_pos else default_max_pos

            # Déterminer le nombre maximum de positions selon le broker
            broker_type = BROKER_TYPE
            max_pos_key = f"MAX_OPEN_POSITIONS_{broker_type.upper()}"
            env_max_pos_broker = os.getenv(max_pos_key)
            if env_max_pos_broker:
                try:
                    actual_max_open_positions = int(env_max_pos_broker)
                    log.info(f"Nombre maximum de positions spécifique au broker ({max_pos_key}) : {actual_max_open_positions}")
                except ValueError:
                    actual_max_open_positions = MAX_OPEN_POSITIONS
            else:
                actual_max_open_positions = MAX_OPEN_POSITIONS

            self.risk_manager = RiskManager({
                'RISK_PCT': RISK_PCT,
                'MAX_DAILY_LOSS_PCT': MAX_DAILY_LOSS_PCT,
                'MAX_MONTHLY_LOSS_PCT': MAX_MONTHLY_LOSS_PCT,
                'MAX_OPEN_POSITIONS': actual_max_open_positions,
                'KELLY_FRACTION': KELLY_FRACTION,
                'MIN_TRADES_FOR_KELLY': MIN_TRADES_FOR_KELLY,
                'SL_ATR_MULT': SL_ATR_MULT,
                'TP_ATR_MULT': TP_ATR_MULT,
                'TRAIL_ATR_MULT': TRAIL_ATR_MULT,
                'BE_ATR_MULT': BE_ATR_MULT,
                'MIN_POSITION_SIZE': actual_min_pos,
                'MAX_POSITION_SIZE': actual_max_pos
            })
            log.info("Gestionnaire de risques initialisé")

            # Charger l'historique de trading réel (disque + broker)
            try:
                self.risk_manager.load_trade_history_from_disk()
                broker_history = self.broker.get_trade_history(days=30)
                if broker_history:
                    self.risk_manager.merge_broker_history(broker_history)
                log.info(f"Historique de trading final chargé : {len(self.risk_manager.trade_history)} trades en mémoire.")
            except Exception as e:
                log.warning(f"Impossible de pré-charger l'historique de trading : {e}")

            # 3. Créer la stratégie de trading
            self.strategy = TradingStrategy({
                'SCORE_MIN': SCORE_MIN,
                'RISK_PCT': RISK_PCT,
                'KELLY_FRACTION': KELLY_FRACTION,
                'EMA_FAST': EMA_FAST,
                'EMA_SLOW': EMA_SLOW,
                'EMA_TREND': EMA_TREND,
                'HTF_EMA': HTF_EMA,
                'D1_EMA': D1_EMA,
                'W1_EMA': W1_EMA,
                'RSI_LEN': RSI_LEN,
                'RSI_OB': RSI_OB,
                'RSI_OS': RSI_OS,
                'MACD_FAST': MACD_FAST,
                'MACD_SLOW': MACD_SLOW,
                'MACD_SIGNAL': MACD_SIGNAL,
                'ADX_LEN': ADX_LEN,
                'ADX_TREND': ADX_TREND,
                'ST_MULTIPLIER': ST_MULTIPLIER,
                'ST_ATR_LEN': ST_ATR_LEN,
                'ATR_LEN': ATR_LEN,
                'BB_LEN': BB_LEN,
                'BB_STD': BB_STD,
                'ICHIMOKU_TENKAN': ICHIMOKU_TENKAN,
                'ICHIMOKU_KIJUN': ICHIMOKU_KIJUN,
                'ICHIMOKU_SENKOU_SPAN_B': ICHIMOKU_SENKOU_SPAN_B,
                'ICHIMOKU_DISPLACEMENT': ICHIMOKU_DISPLACEMENT,
                'VWAP_WINDOW': VWAP_WINDOW
            })
            log.info("Stratégie de trading initialisée")

            # 4. Créer le gestionnaire de nouvelles
            self.news_manager = NewsManager({
                'NEWS_ASSETS': self.news_assets,
                'NEWS_UPDATE_INTERVAL': NEWS_UPDATE_INTERVAL,
                'NEWS_AVOIDANCE_BEFORE': NEWS_AVOIDANCE_BEFORE,
                'NEWS_AVOIDANCE_AFTER': NEWS_AVOIDANCE_AFTER,
                'NEWS_RISK_REDUCTION_FACTOR': NEWS_RISK_REDUCTION_FACTOR,
                'NEWS_HIGH_IMPACT_ONLY': NEWS_HIGH_IMPACT_ONLY,
                'FEAR_GREED_EXTREME_FEAR': FEAR_GREED_EXTREME_FEAR,
                'FEAR_GREED_EXTREME_GREED': FEAR_GREED_EXTREME_GREED,
                'CRYPTOCOMPARE_API_KEY': CRYPTOCOMPARE_API_KEY
            })
            log.info("Gestionnaire de nouvelles initialisé")

            # 5. Créer le calculateur d'indicateurs techniques
            self.technical_indicators = TechnicalIndicators({
                'EMA_FAST': EMA_FAST,
                'EMA_SLOW': EMA_SLOW,
                'EMA_TREND': EMA_TREND,
                'HTF_EMA': HTF_EMA,
                'D1_EMA': D1_EMA,
                'W1_EMA': W1_EMA,
                'RSI_LEN': RSI_LEN,
                'RSI_OB': RSI_OB,
                'RSI_OS': RSI_OS,
                'MACD_FAST': MACD_FAST,
                'MACD_SLOW': MACD_SLOW,
                'MACD_SIGNAL': MACD_SIGNAL,
                'ADX_LEN': ADX_LEN,
                'ADX_TREND': ADX_TREND,
                'ST_MULTIPLIER': ST_MULTIPLIER,
                'ST_ATR_LEN': ST_ATR_LEN,
                'ATR_LEN': ATR_LEN,
                'BB_LEN': BB_LEN,
                'BB_STD': BB_STD,
                'ICHIMOKU_TENKAN': ICHIMOKU_TENKAN,
                'ICHIMOKU_KIJUN': ICHIMOKU_KIJUN,
                'ICHIMOKU_SENKOU_SPAN_B': ICHIMOKU_SENKOU_SPAN_B,
                'ICHIMOKU_DISPLACEMENT': ICHIMOKU_DISPLACEMENT,
                'VWAP_WINDOW': VWAP_WINDOW
            })
            log.info("Calculateur d'indicateurs techniques initialisé")

            # 6. Initialiser le dashboard si activé et disponible
            if ENABLE_DASHBOARD and DASHBOARD_AVAILABLE:
                try:
                    self.dashboard = Dashboard(port=5000, host="0.0.0.0")
                    log.info("Dashboard initialisé")
                except Exception as e:
                    log.warning(f"️  Impossible d'initialiser le dashboard : {e}")
                    self.dashboard = None
            else:
                log.info("Dashboard désactivé ou non disponible")

            # Synchroniser les positions initiales avec le broker
            try:
                self._sync_positions_with_broker()
            except Exception as e:
                log.warning(f"Impossible de synchroniser les positions initiales : {e}")

            log.info("Tous les composants ont été initialisés avec succès")

        except Exception as e:
            log.error(f"Erreur lors de l'initialisation des composants : {e}")
            log.error(traceback.format_exc())
            raise

    def _sync_positions_with_broker(self):
        """
        Synchronise l'état interne des positions du bot et du RiskManager avec le broker.
        """
        try:
            active_positions = {}
            for symbol in self.instruments:
                try:
                    pos = self.broker.get_position(symbol)
                    if pos and pos.get('size', 0) > 0:
                        active_positions[symbol] = {
                            'side': pos['side'],
                            'size': pos['size'],
                            'entry_price': pos['entry_price'],
                            'stop_loss': pos.get('stop_loss', 0.0),
                            'take_profit': pos.get('take_profit', 0.0),
                            'timestamp': self.positions.get(symbol, {}).get('timestamp') or pos.get('timestamp') or datetime.now(timezone.utc),
                            'status': 'open'
                        }
                except Exception as e:
                    log.debug(f"Erreur lors de la récupération de la position de {symbol} : {e}")

            # Détecter les positions fermées
            for symbol, old_pos in self.positions.items():
                if symbol not in active_positions:
                    log.info(f"Position fermée détectée pour {symbol}")
                    entry_price = old_pos.get('entry_price', 0.0)
                    side = old_pos.get('side', 'LONG')
                    size = old_pos.get('size', 0.0)
                    
                    exit_price = 0.0
                    pnl = 0.0
                    
                    # 1. Tenter de récupérer l'info exacte via l'historique du broker
                    try:
                        history = self.broker.get_trade_history(days=1)
                        matching_trade = None
                        for t in history:
                            if t['symbol'] == symbol:
                                matching_trade = t
                                break
                        if matching_trade:
                            exit_price = matching_trade['exit_price']
                            pnl = matching_trade['pnl']
                            entry_price = matching_trade.get('entry_price') or entry_price
                            log.info(f"Détails du trade récupérés depuis l'historique broker pour {symbol} : Exit={exit_price}, P&L={pnl}")
                    except Exception as e:
                        log.debug(f"Impossible de récupérer l'historique broker pour la fermeture de {symbol} : {e}")
                        
                    # 2. Si non trouvé, calculer de manière théorique
                    if exit_price == 0.0:
                        try:
                            exit_price = self.broker.get_current_price(symbol)
                            if side == 'LONG':
                                pnl = (exit_price - entry_price) * size
                            else:
                                pnl = (entry_price - exit_price) * size
                            log.info(f"Calcul théorique de la fermeture pour {symbol} : Exit={exit_price}, P&L={pnl:.2f}")
                        except Exception as e:
                            log.error(f"Erreur lors du calcul théorique de fermeture pour {symbol} : {e}")
                            
                    # Enregistrer le trade clôturé
                    if self.risk_manager:
                        trade_record = {
                            'symbol': symbol,
                            'side': 'buy' if side == 'LONG' else 'sell',
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'position_size': size,
                            'pnl': pnl,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'status': 'closed'
                        }
                        self.risk_manager.record_trade(trade_record)

            # Mettre à jour self.positions
            self.positions = active_positions

            # Mettre à jour self.risk_manager.open_positions
            if self.risk_manager:
                self.risk_manager.open_positions = {
                    symbol: {
                        'symbol': symbol,
                        'side': pos['side'],
                        'entry_price': pos['entry_price'],
                        'size': pos['size'],
                        'stop_loss': pos['stop_loss'],
                        'take_profit': pos['take_profit'],
                        'timestamp': pos['timestamp'].isoformat() if hasattr(pos['timestamp'], 'isoformat') else str(pos['timestamp'])
                    }
                    for symbol, pos in active_positions.items()
                }
            log.info(f"Synchronisation des positions réussie : {list(active_positions.keys())}")
        except Exception as e:
            log.error(f"Erreur lors de la synchronisation des positions avec le broker : {e}")

    def start(self):
        """Démarre le bot de trading."""
        if self.running:
            log.warning("️  Le bot est déjà en cours d'exécution")
            return

        log.info("Démarrage du SuperBot Trading Unifié")
        self.running = True
        self.stats['start_time'] = datetime.now(timezone.utc)

        # Démarrer le gestionnaire de nouvelles
        try:
            self.news_manager.start()
            log.info("Gestionnaire de nouvelles démarré")
        except Exception as e:
            log.error(f"Erreur lors du démarrage du gestionnaire de nouvelles : {e}")

        # Démarrer le dashboard si disponible
        if self.dashboard:
            try:
                self.dashboard.start()
                log.info("Dashboard démarré")
            except Exception as e:
                log.error(f"Erreur lors du démarrage du dashboard : {e}")

        # Démarrer le webhook server si activé
        if WEBHOOK_ENABLED:
            try:
                from superbot.webhook.server import WebhookServer
                self.webhook_server = WebhookServer(
                    host=WEBHOOK_HOST,
                    port=WEBHOOK_PORT,
                    webhook_secret=WEBHOOK_SECRET,
                    callback_func=self._process_webhook_signal
                )
                self.webhook_server.start()
                log.info(f"Serveur Webhook démarré sur {WEBHOOK_HOST}:{WEBHOOK_PORT}")
            except Exception as e:
                log.error(f"Erreur lors du démarrage du serveur Webhook : {e}")

        # Démarrer la boucle principale dans un thread séparé
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.start()
        log.info("Boucle principale de trading démarrée")

        # Configurer la gestion des signaux pour un arrêt propre
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        log.info("SuperBot démarré avec succès")

    def stop(self):
        """Arrête le bot de trading de manière propre."""
        if not self.running:
            log.warning("️  Le bot n'est pas en cours d'exécution")
            return

        log.info("Arrêt du SuperBot...")
        self.running = False
        self.shutdown_event.set()

        # Arrêter le gestionnaire de nouvelles
        try:
            self.news_manager.stop()
            log.info("Gestionnaire de nouvelles arrêté")
        except Exception as e:
            log.error(f"Erreur lors de l'arrêt du gestionnaire de nouvelles : {e}")

        # Arrêter le dashboard
        if self.dashboard:
            try:
                self.dashboard.stop()
                log.info("Dashboard arrêté")
            except Exception as e:
                log.error(f"Erreur lors de l'arrêt du dashboard : {e}")

        # Arrêter le serveur webhook
        if hasattr(self, 'webhook_server') and self.webhook_server:
            try:
                self.webhook_server.stop()
                log.info("Serveur Webhook arrêté")
            except Exception as e:
                log.error(f"Erreur lors de l'arrêt du serveur Webhook : {e}")

        # Attendre la fin du thread principal
        if hasattr(self, 'main_thread') and self.main_thread.is_alive():
            self.main_thread.join(timeout=10.0)
            if self.main_thread.is_alive():
                log.warning("️  Le thread principal ne s'est pas arrêté dans les temps")
            else:
                log.info("Thread principal arrêté")

        # Fermer les connexions du broker
        try:
            # La plupart des brokers n'ont pas besoin de fermeture explicite
            # mais on peut ajouter ici du nettoyage si nécessaire
            log.info("Connexions broker fermées")
        except Exception as e:
            log.error(f"Erreur lors de la fermeture des connexions broker : {e}")

        log.info("SuperBot arrêté avec succès")

    def _signal_handler(self, signum, frame):
        """Gestionnaire de signaux pour un arrêt propre."""
        log.info(f"Signal reçu : {signum}")
        self.stop()
        sys.exit(0)

    def _main_loop(self):
        """
        Boucle principale de trading.
        Cette boucle exécute le cycle de trading pour chaque instrument.
        """
        log.info("Démarrage de la boucle principale de trading")

        cycle_count = 0
        last_news_update = 0
        news_update_interval = 300  # 5 minutes

        while self.running and not self.shutdown_event.is_set():
            cycle_start_time = time.time()

            try:
                # Mettre à jour les statistiques
                cycle_count += 1
                self.stats['cycles_completed'] = cycle_count
                self.stats['last_cycle_time'] = datetime.now(timezone.utc)

                log.debug(f"Cycle #{cycle_count} démarré")

                # Synchroniser les positions avec le broker
                try:
                    self._sync_positions_with_broker()
                except Exception as e:
                    log.warning(f"Erreur de synchronisation des positions au cycle #{cycle_count} : {e}")

                # Sélectionner l'actif crypto actif et effectuer les rotations si nécessaire
                try:
                    self._select_and_rotate_crypto()
                except Exception as e:
                    log.warning(f"Erreur lors de la sélection/rotation crypto au cycle #{cycle_count} : {e}")

                # Traiter chaque instrument (mélangé aléatoirement pour éviter tout biais d'ordre)
                import random
                scanned_instruments = list(self.instruments)
                random.shuffle(scanned_instruments)
                for symbol in scanned_instruments:
                    if not self.running:
                        break

                    try:
                        self._process_symbol(symbol)
                    except Exception as e:
                        log.error(f"Erreur lors du traitement de {symbol} : {e}")
                        log.debug(traceback.format_exc())
                        self.stats['errors_count'] += 1

                # Mettre à jour le dashboard si disponible
                if self.dashboard:
                    try:
                        self._update_dashboard()
                    except Exception as e:
                        log.debug(f"Erreur lors de la mise à jour du dashboard : {e}")

                # Mise à jour des paramètres adaptatifs périodiquement
                self._adaptation_counter += 1
                if self._adaptation_counter >= self._adaptation_every:
                    self._update_adaptive_parameters()
                    self._adaptation_counter = 0

                # Détection de dérive du modèle
                self._detect_model_drift()

                # Calculer le temps de cycle et dormir si nécessaire
                cycle_duration = time.time() - cycle_start_time
                target_cycle_time = 60  # 60 secondes par cycle (ajustable)

                if cycle_duration < target_cycle_time:
                    sleep_time = target_cycle_time - cycle_duration
                    # Dormir par petites pauses pour pouvoir répondre rapidement au signal d'arrêt
                    slept = 0
                    while slept < sleep_time and self.running and not self.shutdown_event.is_set():
                        time.sleep(min(1, sleep_time - slept))
                        slept += 1
                else:
                    log.warning(f"️  Cycle trop long : {cycle_duration:.2f}s (cible : {target_cycle_time}s)")

            except Exception as e:
                log.error(f"Erreur dans la boucle principale : {e}")
                log.error(traceback.format_exc())
                self.stats['errors_count'] += 1
                time.sleep(5)  # Attendre un peu avant de reprendre en cas d'erreur

        log.info("Boucle principale de trading terminée")

    def _process_symbol(self, symbol: str):
        """
        Traite un symbole spécifique : récupère les données, analyse, génère des signaux, exécute des trades.

        Args:
            symbol: Symbole à traiter (ex: BTC/USDT)
        """
        try:
            # 1. Récupérer les données de marché récentes
            df = self._fetch_market_data(symbol)
            if df is None or len(df) < 50:  # Minimum de données nécessaires
                log.debug(f"Données insuffisantes pour {symbol} : {len(df) if df is not None else 0} barres")
                return

            # 2. Calculer les indicateurs techniques
            df_with_indicators = self.technical_indicators.calculate_all_indicators(df.copy())
            self.market_data[symbol] = df_with_indicators

            # === GESTION DE RISQUE CONTINUE DES POSITIONS OUVERTES ===
            self._update_active_position_risk(symbol, df_with_indicators)

            # Si le courtier est crypto et que le symbole n'est pas l'actif sélectionné
            if self.broker.get_asset_type() == "crypto":
                active_crypto = getattr(self, '_active_crypto_symbol', None)
                if active_crypto and symbol != active_crypto:
                    # Ne pas chercher à ouvrir de nouvelles positions sur cet actif
                    return

            # 3. Analyser le marché et générer un signal de trading
            signal_data = self.strategy.analyze_market(df_with_indicators)
            signal_data['symbol'] = symbol  # Ajouter le symbole au signal

            # DEBUG: log signal details and pre-check news avoidance
            score_raw = signal_data['total_score']
            score_min = self.strategy.score_min
            rr = signal_data['rr_ratio']
            should_avoid, news_event = self.news_manager.should_avoid_trading_due_to_news(symbol)
            news_ok = not should_avoid
            log.info(
                f"Signal DEBUG {symbol}: regime={signal_data['market_regime']} "
                f"score_raw={score_raw:.1f} score_min={score_min} "
                f"should_long={signal_data['should_long']} should_short={signal_data['should_short']} "
                f"RR={rr:.2f} news_ok={news_ok}"
            )

            if should_avoid:
                log.info(f"Trading évité pour {symbol} à cause des nouvelles : {news_event.title if news_event else 'Unknown'}")
                return
            elif signal_data['should_long'] or signal_data['should_short']:
                self._execute_signal_trade(symbol, signal_data, df_with_indicators)
            else:
                log.info(
                    f"Scan {symbol} : {signal_data['market_regime']} | "
                    f"Score: {score_raw:.1f}/{score_min} | "
                    f"Pas de signal (Trigger L: {signal_data['trigger_long']}, S: {signal_data['trigger_short']}, R:R: {rr:.2f})"
                )

        except Exception as e:
            log.error(f"Erreur inattendue dans _process_symbol pour {symbol} : {e}")
            log.debug(traceback.format_exc())

    def _update_active_position_risk(self, symbol: str, df_with_indicators):
        """
        Met à jour les trailing stops et break-evens pour les positions ouvertes.
        """
        if symbol in self.positions:
            current_price = df_with_indicators.iloc[-1]['close']
            atr_value = df_with_indicators.iloc[-1].get('atr', 0)
            
            # Mettre à jour l'ATR dans la position pour le risk manager
            if self.risk_manager and symbol in self.risk_manager.open_positions:
                pos_risk = self.risk_manager.open_positions[symbol]
                pos_risk['atr_value'] = atr_value
                
                old_sl = pos_risk.get('stop_loss', 0.0)
                
                # Lancer la mise à jour (calcul du trailing stop / break-even)
                self.risk_manager.update_open_position(symbol, current_price)
                
                new_sl = pos_risk.get('stop_loss', 0.0)
                
                # Si le stop loss a été modifié localement, mettre à jour chez le broker
                if new_sl != old_sl and new_sl > 0:
                    log.info(f"Mise à jour du Stop Loss pour {symbol} chez le courtier : {old_sl:.5f} -> {new_sl:.5f}")
                    success = self.broker.modify_sl_tp(symbol, new_sl, pos_risk.get('take_profit', 0.0))
                    if success:
                        # Mettre à jour notre dictionnaire local de suivi de position
                        self.positions[symbol]['stop_loss'] = new_sl

    def _execute_signal_trade(self, symbol: str, signal_data: dict, df_with_indicators):
        """
        Valide les filtres macro, calcule la taille de position de manière sécurisée et exécute l'ordre.
        """
        self.stats['signals_generated'] += 1
        log.info(
            f"Signal pour {symbol} : {signal_data['market_regime']} | "
            f"Score: {signal_data['total_score']:.1f} | "
            f"Long: {signal_data['should_long']} | Short: {signal_data['should_short']} | "
            f"RR: {signal_data['rr_ratio']:.2f}"
        )

        # 1. Vérifier les filtres de nouvelles et de sentiment
        should_avoid, news_event = self.news_manager.should_avoid_trading_due_to_news(symbol)
        if should_avoid:
            log.info(f"Trading évité pour {symbol} à cause des nouvelles : {news_event.title if news_event else 'Unknown'}")
            return

        # 2. Récupérer le solde et le prix d'entrée
        account_balance = self.broker.get_balance()
        entry_price = signal_data['entry_price']

        # Déterminer le stop loss et take profit
        sl_price = signal_data['sl_price']
        tp_price = signal_data['tp_price']

        # Si les prix SL/TP ne sont pas fournis, les calculer basé sur l'ATR
        if sl_price == 0 or tp_price == 0:
            atr_value = df_with_indicators.iloc[-1].get('atr', 0)
            if atr_value > 0:
                position_side = "LONG" if signal_data['should_long'] else "SHORT"
                sl_price, tp_price = self.risk_manager.calculate_sl_tp_levels(
                    entry_price, atr_value, position_side
                )
            else:
                # Fallback : utiliser un pourcentage fixe provenant de la configuration
                risk_pct = RISK_PCT / 100.0  # Convertir de pourcentage en décimal
                if signal_data['should_long']:
                    sl_price = entry_price * (1 - risk_pct)
                    tp_price = entry_price * (1 + risk_pct * 2)  # RR 1:2
                else:
                    sl_price = entry_price * (1 + risk_pct)
                    tp_price = entry_price * (1 - risk_pct * 2)

        # 3. Calculer la taille de position avec le Risk Manager
        position_size, size_details = self.risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss=sl_price,
            symbol=symbol,
            sentiment_factor=self.news_manager.get_risk_factor() if self.news_manager else 1.0
        )

        # DEBUG: Log detailed risk sizing information
        log.info(
            f"Risk sizing {symbol}: size={position_size:.6f} | "
            f"details={size_details}"
        )

        if position_size <= 0:
            log.debug(f"Taille de position nulle ou rejetée pour {symbol}, pas d'action")
            return

        log.info(
            f"Taille de position calculée pour {symbol} : {position_size:.6f} | "
            f"Risque : {size_details.get('actual_risk_pct', 0.0):.2f}% du compte"
        )

        # 4. Vérifier les limites de risque globales avant d'envoyer l'ordre
        if not self.risk_manager._can_take_new_trade(account_balance):
            log.info(f"Limites de risque atteintes, pas de nouvel ordre pour {symbol}")
            return

        # 5. Exécuter le trade chez le courtier
        side = "buy" if signal_data['should_long'] else "sell"
        log.info(
            f"Exécution du trade : {side.upper()} {position_size:.6f} {symbol} @ {entry_price:.4f} | "
            f"SL: {sl_price:.4f} | TP: {tp_price:.4f}"
        )

        # Placer l'ordre
        order_result = self.broker.place_order(
            symbol=symbol,
            side=side,
            amount=position_size,
            sl=sl_price,
            tp=tp_price,
            comment=f"SuperBot signal - {signal_data['market_regime']} - Score:{signal_data['total_score']:.1f}"
        )

        if order_result:
            self.stats['trades_executed'] += 1
            log.info(f"Trade exécuté avec succès pour {symbol}")

            # Enregistrer le trade pour le suivi du risque
            trade_record = {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'position_size': position_size,
                'stop_loss': sl_price,
                'take_profit': tp_price,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'signal_score': signal_data['total_score'],
                'market_regime': signal_data['market_regime']
            }
            self.risk_manager.record_trade(trade_record)

            # Mettre à jour la position suivie
            self._update_position_tracking(symbol, side, position_size, entry_price, sl_price, tp_price)

        else:
            log.error(f"Échec de l'exécution du trade pour {symbol}")

    def _select_and_rotate_crypto(self):
        """
        Pour la crypto, sélectionne automatiquement le meilleur actif (BTC ou ETH)
        et gère l'abandon/rotation de l'autre vers le nouvel actif sélectionné.
        """
        try:
            if not self.broker or self.broker.get_asset_type() != "crypto":
                return

            btc_symbol = None
            eth_symbol = None

            # Détecter les symboles BTC et ETH parmi les instruments ou les valeurs par défaut du broker
            symbols_to_check = list(self.instruments)
            try:
                for default_sym in self.broker.get_default_instruments():
                    if default_sym not in symbols_to_check:
                        symbols_to_check.append(default_sym)
            except Exception:
                pass

            for s in symbols_to_check:
                s_upper = s.upper()
                if "BTC" in s_upper and ("USDT" in s_upper or "USD" in s_upper) and not btc_symbol:
                    btc_symbol = s
                elif "ETH" in s_upper and ("USDT" in s_upper or "USD" in s_upper) and not eth_symbol:
                    eth_symbol = s

            # Fallbacks si non trouvés dans la liste
            if not btc_symbol:
                btc_symbol = "BTC/USDT" if "/" in self.instruments[0] else "BTCUSDT"
            if not eth_symbol:
                eth_symbol = "ETH/USDT" if "/" in self.instruments[0] else "ETHUSDT"

            log.debug(f"Analyse rotation crypto : BTC={btc_symbol}, ETH={eth_symbol}")

            # Récupérer les données pour les deux actifs
            btc_df = self._fetch_market_data(btc_symbol)
            eth_df = self._fetch_market_data(eth_symbol)

            if btc_df is None or eth_df is None or len(btc_df) < 50 or len(eth_df) < 50:
                # Si l'un des deux échoue, on ne change rien
                log.debug("Données insuffisantes pour effectuer la sélection de rotation crypto.")
                return

            # Calculer les indicateurs et analyser avec la stratégie
            btc_indicators = self.technical_indicators.calculate_all_indicators(btc_df.copy())
            eth_indicators = self.technical_indicators.calculate_all_indicators(eth_df.copy())

            btc_signal = self.strategy.analyze_market(btc_indicators)
            eth_signal = self.strategy.analyze_market(eth_indicators)

            # Calculer un score de force de tendance/momentum pour la rotation
            def compute_trend_score(df, sig) -> float:
                last = df.iloc[-1]
                score = float(sig.get('total_score', 0))
                
                # Bonus de tendance à long terme
                ema_200 = last.get('ema_trend', last['close'])
                if last['close'] > ema_200:
                    score += 5.0
                else:
                    score -= 5.0

                # Force de tendance ADX
                adx = last.get('adx', 0)
                if last['close'] > ema_200:
                    score += adx / 10.0
                else:
                    score -= adx / 10.0

                # RSI (momentum)
                rsi = last.get('rsi', 50)
                score += (rsi - 50) / 10.0

                return score

            btc_score = compute_trend_score(btc_indicators, btc_signal)
            eth_score = compute_trend_score(eth_indicators, eth_signal)

            log.info(f"Évaluation Crypto : BTC Score = {btc_score:.2f} | ETH Score = {eth_score:.2f}")

            # Choix de l'actif
            current_active = getattr(self, '_active_crypto_symbol', None)
            
            # Appliquer un buffer de rotation (différence > 2.0) pour éviter les allers-retours
            if current_active is None:
                selected = btc_symbol if btc_score >= eth_score else eth_symbol
            elif current_active == btc_symbol:
                selected = eth_symbol if eth_score > btc_score + 2.0 else btc_symbol
            else:
                selected = btc_symbol if btc_score > eth_score + 2.0 else eth_symbol

            self._active_crypto_symbol = selected
            log.info(f"Actif crypto sélectionné : {selected}")

            # Abandon/rotation de position :
            # Si nous détenons une position sur l'autre symbole, et que nous choisissons de basculer,
            # on vérifie s'il faut abandonner l'actif actuel.
            other_symbol = eth_symbol if selected == btc_symbol else btc_symbol
            other_pos = self.positions.get(other_symbol)

            if other_pos and other_pos.get('size', 0) > 0:
                current_pos_score = btc_score if other_symbol == btc_symbol else eth_score
                selected_score = eth_score if selected == eth_symbol else btc_score

                # Si le nouvel actif est nettement meilleur (score supérieur de 3.0 points ou plus)
                if selected_score > current_pos_score + 3.0:
                    log.info(f"🔄 ROTATION CRYPTO : Fermeture de la position sur {other_symbol} (score {current_pos_score:.2f}) pour basculer sur {selected} (score {selected_score:.2f})")
                    self.broker.close_position(other_symbol, reason="Rotation de portefeuille crypto")
                    self._sync_positions_with_broker()

        except Exception as e:
            log.error(f"Erreur dans _select_and_rotate_crypto: {e}")
            log.debug(traceback.format_exc())

    def _fetch_market_data(self, symbol: str, limit: int = 500) -> Optional[any]:
        """
        Récupère les données de marché récentes pour un symbole.

        Args:
            symbol: Symbole à récupérer
            limit: Nombre de bougies à récupérer

        Returns:
            DataFrame avec les données OHLCV ou None en cas d'erreur
        """
        try:
            # Utiliser le timeframe configuré
            timeframe = GRANULARITY

            # Récupérer les données depuis le broker
            df = self.broker.fetch_candles(symbol, timeframe, limit)

            if df is None or df.empty:
                log.warning(f"Aucune donnée retournée pour {symbol}")
                return None

            # S'assurer que le DataFrame a les colonnes requises
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                log.warning(f"Colonnes manquantes dans les données pour {symbol} : {df.columns.tolist()}")
                return None

            return df

        except Exception as e:
            log.error(f"Erreur lors de la récupération des données pour {symbol} : {e}")
            return None

    def _update_position_tracking(self, symbol: str, side: str, size: float, entry_price: float, stop_loss: float = 0.0, take_profit: float = 0.0):
        """
        Met à jour le suivi des positions ouvertes.

        Args:
            symbol: Symbole de l'instrument
            side: Côté de la position ('buy' ou 'sell')
            size: Taille de la position
            entry_price: Prix d'entrée
            stop_loss: Niveau de Stop Loss
            take_profit: Niveau de Take Profit
        """
        position_side = "LONG" if side == "buy" else "SHORT"

        self.positions[symbol] = {
            'side': position_side,
            'size': size,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now(timezone.utc),
            'status': 'open'
        }

        log.debug(f"Position suivie mise à jour pour {symbol} : {position_side} {size}")

    def _process_webhook_signal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un signal de trading reçu via Webhook (ex: TradingView).
        """
        try:
            log.info(f"Traitement du signal Webhook : {data}")

            # Vérifier le secret si configuré
            secret = data.get('secret')
            if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
                log.warning("Secret de webhook invalide dans le payload")
                return {"status": "error", "reason": "invalid_secret"}

            # Adapter le payload pour TradingView (ticker -> symbol, position/strategy_position -> action, close -> price)
            symbol = data.get('symbol') or data.get('ticker')
            action = data.get('action') or data.get('strategy_position') or data.get('position')
            if action:
                action = str(action).lower()
            else:
                action = ''
                
            price = data.get('price') or data.get('close')
            if price is not None:
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    price = None
            
            if not symbol or not action:
                log.warning(f"Champs manquants ou invalides dans le webhook : symbol={symbol}, action={action}")
                return {"status": "error", "reason": "missing_fields"}

            # Normaliser le symbole pour le broker
            symbol = self.broker.normalize_symbol(symbol)

            # 1. Action de fermeture / sortie
            if action in ['exit', 'close', 'sell_all', 'buy_all']:
                log.info(f"Demande de fermeture de position reçue via webhook pour {symbol}")
                success = self.broker.close_position(symbol, reason="Webhook exit request")
                if success:
                    # Mettre à jour l'état local
                    if symbol in self.positions:
                        del self.positions[symbol]
                    if self.risk_manager and symbol in self.risk_manager.open_positions:
                        del self.risk_manager.open_positions[symbol]
                    return {"status": "success", "action": "closed", "symbol": symbol}
                else:
                    return {"status": "error", "reason": "failed_to_close", "symbol": symbol}

            # 2. Action d'entrée (buy/sell)
            if action not in ['buy', 'sell']:
                return {"status": "error", "reason": f"unknown_action: {action}"}

            # Vérifier les nouvelles si activé
            should_avoid, news_event = self.news_manager.should_avoid_trading_due_to_news(symbol)
            if should_avoid:
                log.info(f"Signal webhook évité pour {symbol} à cause des nouvelles : {news_event.title if news_event else 'Unknown'}")
                return {"status": "skipped", "reason": "news_avoidance", "news_event": str(news_event) if news_event else None}

            # Récupérer les prix SL/TP optionnels ou les calculer
            sl_price = float(data.get('sl', 0))
            tp_price = float(data.get('tp', 0))

            # Si non fournis dans le webhook, essayer de les calculer avec l'ATR si on a des données de marché
            if sl_price == 0 or tp_price == 0:
                df = self._fetch_market_data(symbol)
                if df is not None and not df.empty:
                    df_with_indicators = self.technical_indicators.calculate_all_indicators(df.copy())
                    atr_value = df_with_indicators.iloc[-1].get('atr', 0)
                    if atr_value > 0:
                        position_side = "LONG" if action == 'buy' else "SHORT"
                        sl_price, tp_price = self.risk_manager.calculate_sl_tp_levels(
                            price or self.broker.get_current_price(symbol), atr_value, position_side
                        )
                
                # Fallback fixe si toujours pas calculable
                if sl_price == 0 or tp_price == 0:
                    entry = price or self.broker.get_current_price(symbol)
                    risk_pct = RISK_PCT / 100.0
                    if action == 'buy':
                        sl_price = entry * (1 - risk_pct)
                        tp_price = entry * (1 + risk_pct * 2)
                    else:
                        sl_price = entry * (1 + risk_pct)
                        tp_price = entry * (1 - risk_pct * 2)

            # Calculer la taille de position
            account_balance = self.broker.get_balance()
            entry_price = price or self.broker.get_current_price(symbol)
            
            position_size, size_details = self.risk_manager.calculate_position_size(
                account_balance=account_balance,
                entry_price=entry_price,
                stop_loss=sl_price,
                symbol=symbol,
                sentiment_factor=self.news_manager.get_risk_factor() if self.news_manager else 1.0
            )

            if position_size <= 0:
                log.warning(f"Taille de position calculée nulle pour {symbol}")
                return {"status": "error", "reason": "zero_position_size"}

            # Vérifier les limites de risque globales
            if not self.risk_manager._can_take_new_trade(account_balance):
                log.info(f"Limites de risque atteintes, pas d'exécution de webhook pour {symbol}")
                return {"status": "skipped", "reason": "risk_limit_reached"}

            # Exécuter l'ordre
            log.info(f"Exécution du trade webhook : {action.upper()} {position_size:.6f} {symbol} @ {entry_price:.4f} | SL: {sl_price:.4f} | TP: {tp_price:.4f}")
            order_result = self.broker.place_order(
                symbol=symbol,
                side=action,
                amount=position_size,
                sl=sl_price,
                tp=tp_price,
                comment=f"TradingView webhook signal - {action.upper()}"
            )

            if order_result:
                self.stats['trades_executed'] += 1
                
                # Enregistrer le trade pour le suivi du risque
                trade_record = {
                    'symbol': symbol,
                    'side': action,
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'stop_loss': sl_price,
                    'take_profit': tp_price,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'signal_score': data.get('strength', 1.0) * 10,
                    'market_regime': 'Webhook Alert'
                }
                self.risk_manager.record_trade(trade_record)

                # Mettre à jour la position suivie
                self._update_position_tracking(symbol, action, position_size, entry_price, sl_price, tp_price)
                return {"status": "success", "action": action, "symbol": symbol, "size": position_size, "entry": entry_price}
            else:
                log.error(f"Échec de l'exécution du trade webhook pour {symbol}")
                return {"status": "error", "reason": "order_placement_failed"}

        except Exception as e:
            log.error(f"Erreur inattendue dans _process_webhook_signal : {e}")
            log.debug(traceback.format_exc())
            return {"status": "error", "reason": str(e)}

    def _update_dashboard(self):
        """
        Met à jour le dashboard avec les données actuelles.
        """
        if not self.dashboard:
            return

        try:
            # Préparer les données pour le dashboard
            serialized_history = []
            if self.risk_manager:
                for t in self.risk_manager.trade_history:
                    t_copy = t.copy()
                    if isinstance(t_copy.get('timestamp'), datetime):
                        t_copy['timestamp'] = t_copy['timestamp'].isoformat()
                    serialized_history.append(t_copy)

            dashboard_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'broker_type': BROKER_TYPE,
                'asset_type': self.broker.get_asset_type(),
                'stats': {
                    **self.stats.copy(),
                    'running': self.running,
                    'uptime_seconds': (datetime.now(timezone.utc) - self.stats['start_time']).total_seconds() if self.stats.get('start_time') else 0,
                    'total_trades': len(self.risk_manager.trade_history) if self.risk_manager else 0,
                    'win_trades': len([t for t in self.risk_manager.trade_history if t.get('pnl', 0) > 0]) if self.risk_manager else 0,
                },
                'positions': {},
                'history': serialized_history,
                'market_data': {},
                'account': {},
                'risk_metrics': {},
                'news_sentiment': {}
            }

            # Ajouter les informations du compte (normalisées pour tous les brokers)
            try:
                acc_raw = self.broker.get_account_summary()
                if not acc_raw or not isinstance(acc_raw, dict):
                    acc_raw = {}
                # Normaliser les clés — chaque broker utilise des noms différents
                bal  = float(acc_raw.get('balance') or acc_raw.get('equity') or acc_raw.get('cash') or self.initial_balance)
                upnl = float(acc_raw.get('unrealized_pnl') or acc_raw.get('unrealized_pl') or acc_raw.get('unrealized_profit') or 0.0)
                dashboard_data['account'] = {
                    'balance':         bal,
                    'initial_balance': self.initial_balance,
                    'equity':          float(acc_raw.get('equity') or bal),
                    'unrealized_pnl':  upnl,
                    'pnl':             bal - self.initial_balance,
                    'open_positions':  int(acc_raw.get('open_positions', len(self.positions))),
                    'account_type':    acc_raw.get('account_type', 'PAPER'),
                    'broker':          BROKER_TYPE,
                }
            except Exception as e:
                log.debug(f"Erreur solde: {e}")
                dashboard_data['account'] = {
                    'balance': self.initial_balance, 'initial_balance': self.initial_balance,
                    'pnl': 0.0, 'unrealized_pnl': 0.0,
                    'open_positions': len(self.positions), 'broker': BROKER_TYPE,
                }

            # Ajouter les métriques de risque
            try:
                account_balance = self.broker.get_balance()
                dashboard_data['risk_metrics'] = self.risk_manager.get_risk_metrics(account_balance)
            except Exception as e:
                log.debug(f"Erreur lors de la récupération des métriques de risque : {e}")
                dashboard_data['risk_metrics'] = {'error': str(e)}

            # Ajouter les données de sentiment des nouvelles
            try:
                if self.news_manager:
                    dashboard_data['news_sentiment'] = self.news_manager.get_sentiment_summary()
            except Exception as e:
                log.debug(f"Erreur lors de la récupération du sentiment des nouvelles : {e}")
                dashboard_data['news_sentiment'] = {'error': str(e)}

            # Ajouter les positions actuelles
            for symbol, position in self.positions.items():
                try:
                    # Obtenir le prix actuel pour calculer le P&L
                    current_price = self.broker.get_current_price(symbol)
                    position['current_price'] = current_price

                    # Calculer le P&L non réalisé
                    if position['side'] == 'LONG':
                        position['unrealized_pnl'] = (current_price - position['entry_price']) * position['size']
                    else:  # SHORT
                        position['unrealized_pnl'] = (position['entry_price'] - current_price) * position['size']

                    dashboard_data['positions'][symbol] = position
                except Exception as e:
                    log.debug(f"Erreur lors de la mise à jour de la position pour {symbol} : {e}")
                    dashboard_data['positions'][symbol] = {**position, 'error': str(e)}

            # Ajouter quelques données de marché récentes pour le graphique
            for symbol, df in self.market_data.items():
                if df is not None and not df.empty:
                    recent = df.tail(100).copy()
                    # Normaliser les noms de colonnes (certains brokers les mettent en majuscule)
                    recent.columns = [c.lower() for c in recent.columns]
                    candles = []
                    for ts, row in recent.iterrows():
                        try:
                            # Convertir en millisecondes Unix pour ApexCharts (compatible tous navigateurs)
                            if hasattr(ts, 'timestamp'):
                                ts_ms = int(ts.timestamp() * 1000)
                            else:
                                import pandas as pd
                                ts_ms = int(pd.Timestamp(ts).timestamp() * 1000)
                            candles.append({
                                't': ts_ms,
                                'o': float(row.get('open',   row.get('o', 0))),
                                'h': float(row.get('high',   row.get('h', 0))),
                                'l': float(row.get('low',    row.get('l', 0))),
                                'c': float(row.get('close',  row.get('c', 0))),
                                'v': float(row.get('volume', row.get('v', 0))),
                            })
                        except Exception:
                            continue
                    if candles:
                        dashboard_data['market_data'][symbol] = candles

            # Mettre à jour le dashboard
            self.dashboard.update_data(dashboard_data)

        except Exception as e:
            log.debug(f"Erreur lors de la mise à jour du dashboard : {e}")

    def _get_recent_win_rate(self) -> float:
        """
        Calcule le taux de victoire sur les 20 derniers trades enregistrés.
        Returns:
            Taux de victoire entre 0.0 et 1.0, ou 0.0 si pas assez de trades.
        """
        if not self.risk_manager.trade_history:
            return 0.0
        recent = self.risk_manager.trade_history[-20:]
        if not recent:
            return 0.0
        winning = sum(1 for t in recent if t.get('pnl', 0) > 0)
        return winning / len(recent)

    def _update_adaptive_parameters(self):
        """
        Ajuste les paramètres de risque et de score en fonction de la performance récente.
        """
        if len(self.risk_manager.trade_history) < 5:
            return  # Pas assez de données pour ajuster

        recent_win_rate = self._get_recent_win_rate()
        log.debug(f"Taux de victoire récent (20 derniers trades) : {recent_win_rate:.2f}")

        # Seuils d'ajustement
        if recent_win_rate > 0.6:
            # Performance bonne : augmenter légèrement le risque et abaisser le seuil de score
            old_risk = self.adaptive_risk_pct
            old_score = self.adaptive_score_min
            self.adaptive_risk_pct = min(self.adaptive_risk_pct * 1.05, 2.5)  # max 2.5%
            self.adaptive_score_min = max(self.adaptive_score_min - 0.5, 2.0)  # min 2.0
            if old_risk != self.adaptive_risk_pct or old_score != self.adaptive_score_min:
                log.info(f"Adaptation paramètres : risque {old_risk:.2f}% -> {self.adaptive_risk_pct:.2f}%, score min {old_score:.1f} -> {self.adaptive_score_min:.1f}")
        elif recent_win_rate < 0.4:
            # Performance mauvaise : réduire le risque et augmenter le seuil de score
            old_risk = self.adaptive_risk_pct
            old_score = self.adaptive_score_min
            self.adaptive_risk_pct = max(self.adaptive_risk_pct * 0.95, 0.5)  # min 0.5%
            self.adaptive_score_min = min(self.adaptive_score_min + 0.5, 8.0)  # max 8.0
            if old_risk != self.adaptive_risk_pct or old_score != self.adaptive_score_min:
                log.info(f"Adaptation paramètres : risque {old_risk:.2f}% -> {self.adaptive_risk_pct:.2f}%, score min {old_score:.1f} -> {self.adaptive_score_min:.1f}")
        # else: garder les paramètres actuels

    def _detect_model_drift(self):
        """
        Détecte une éventuelle dérive du modèle en surveillant le taux de victoire récent.
        Si le taux de victoire chute de manière significative, un avertissement est enregistré.
        """
        if len(self.risk_manager.trade_history) < 10:
            return  # Pas assez de données pour détecter une dérive

        # Calculer le taux de victoire sur les 10 derniers trades
        recent = self.risk_manager.trade_history[-10:]
        winning = sum(1 for t in recent if t.get('pnl', 0) > 0)
        win_rate = winning / len(recent) if recent else 0.0

        # Seuil d'alerte : taux de victoire inférieur à 30% sur les 10 derniers trades
        if win_rate < 0.3:
            log.warning(f"⚠️ Dérive du modèle détectée : taux de victoire récent ({win_rate:.2f}) inférieur au seuil critique de 0.30")

    def get_status(self) -> Dict:
        """
        Retourne le statut actuel du bot.

        Returns:
            Dictionnaire avec le statut du bot
        """
        return {
            'running': self.running,
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'uptime_seconds': (datetime.now(timezone.utc) - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0,
            'stats': self.stats.copy(),
            'components': {
                'broker': self.broker is not None,
                'strategy': self.strategy is not None,
                'risk_manager': self.risk_manager is not None,
                'news_manager': self.news_manager is not None,
                'technical_indicators': self.technical_indicators is not None,
                'dashboard': self.dashboard is not None and getattr(self.dashboard, 'running', False)
            }
        }

def main():
    """Point d'entrée principal du SuperBot."""
    print("SuperBot Trading Unifié")
    print("=" * 50)

    # Créer et démarrer le bot
    bot = SuperBot()

    try:
        bot.start()

        # Boucle principale d'attente (le bot travaille dans des threads séparés)
        print("SuperBot démarré avec succès")
        print("Appuyez sur Ctrl+C pour arrêter le bot")
        print("=" * 50)

        # Attendre jusqu'à interruption
        while bot.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"\nErreur fatale : {e}")
        traceback.print_exc()
    finally:
        print("\nArrêt du SuperBot en cours...")
        bot.stop()
        print("SuperBot arrêté")
        print("Au revoir !")

if __name__ == "__main__":
    main()