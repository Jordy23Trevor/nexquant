"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╩
"""
import asyncio
import signal
import sys
import os

# --- INJECTION CLI POUR MULTI-SESSION ---
# On parse les arguments AVANT les imports globaux pour surcharger .env
if "--broker" in sys.argv:
    try:
        idx = sys.argv.index("--broker")
        os.environ["BROKER_TYPE"] = sys.argv[idx + 1]
    except IndexError:
        pass

if "--dashboard-port" in sys.argv:
    try:
        idx = sys.argv.index("--dashboard-port")
        os.environ["DASHBOARD_PORT"] = sys.argv[idx + 1]
    except IndexError:
        pass

if "--webhook-port" in sys.argv:
    try:
        idx = sys.argv.index("--webhook-port")
        os.environ["WEBHOOK_PORT"] = sys.argv[idx + 1]
    except IndexError:
        pass
# ----------------------------------------

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
from typing import Dict, List, Optional, Any, Set
import threading
import traceback

# Importer les modules du SuperBot
from superbot.config import (
    BROKER_TYPE, INSTRUMENTS, GRANULARITY,
    LOG_LEVEL, LOG_FILE, ENABLE_DASHBOARD, WEBHOOK_ENABLED,
    WEBHOOK_SECRET, WEBHOOK_HOST, WEBHOOK_PORT,
    
    # Risk Management
    RISK_PCT, MAX_DAILY_LOSS_PCT, MAX_MONTHLY_LOSS_PCT, MAX_OPEN_POSITIONS,
    KELLY_FRACTION, MIN_TRADES_FOR_KELLY, SL_ATR_MULT, TP_ATR_MULT,
    TRAIL_ATR_MULT, BE_ATR_MULT, MIN_POSITION_SIZE, MAX_POSITION_SIZE,
    COOLDOWN_SECONDS,  # ✅ BUG FIX #5
    MAX_FOREX_CURRENCY_EXPOSURE, MAX_SPREAD_PIPS, BE_DYN_RR, BE_DYN_RR_RATIO,

    
    # Strategy / Indicators
    SCORE_MIN, EMA_FAST, EMA_SLOW, EMA_TREND, HTF_EMA, D1_EMA, W1_EMA,
    RSI_LEN, RSI_OB, RSI_OS, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    ADX_LEN, ADX_TREND, ST_MULTIPLIER, ST_ATR_LEN, ATR_LEN,
    BB_LEN, BB_STD, ICHIMOKU_TENKAN, ICHIMOKU_KIJUN,
    ICHIMOKU_SENKOU_SPAN_B, ICHIMOKU_DISPLACEMENT, VWAP_WINDOW,
    
    # News & Sentiment
    NEWS_ASSETS, NEWS_UPDATE_INTERVAL, NEWS_AVOIDANCE_BEFORE, NEWS_AVOIDANCE_AFTER,
    NEWS_RISK_REDUCTION_FACTOR, NEWS_HIGH_IMPACT_ONLY, FEAR_GREED_EXTREME_FEAR,
    FEAR_GREED_EXTREME_GREED, CRYPTOCOMPARE_API_KEY,

    # Filtres crypto — rapport post-mortem 2026-07-02
    CRYPTO_BLACKLIST, CRYPTO_SCORE_MIN, CRYPTO_BUY_BLOCK_BTC_DROP, CRYPTO_BNB_VOLUME_FACTOR,
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
from superbot.telemetry import TelemetryClient, TelemetryLoggingHandler

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("main")

# Initialisation globale de la télémétrie pour les logs
telemetry_client = TelemetryClient()
if telemetry_client.enabled:
    telemetry_handler = TelemetryLoggingHandler(telemetry_client)
    telemetry_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(telemetry_handler)

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
        self.is_paused = False
        self.telemetry = telemetry_client
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

        # Blocage dynamique des actifs perdants
        self.blocked_symbols: Set[str] = set()
        self.session_pnl_by_symbol: Dict[str, float] = {}
        self.session_date = datetime.now().date()
        self.ASSET_BLOCK_LOSS_THRESHOLD = float(os.getenv('ASSET_BLOCK_LOSS_THRESHOLD', 50.0))  # USD
        self.CLOUD_SYNC_INTERVAL = 300.0       # 5 minutes (300s)
        self.TELEMETRY_INTERVAL = 120.0        # 2 minutes (120s)
        self._last_cloud_sync = 0.0
        self._last_telemetry_push = 0.0

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

            # 1. Synchronisation de la configuration Cloud & Télémétrie
            self.remote_config = None
            active_broker_type = BROKER_TYPE
            broker_kwargs = {}

            if self.telemetry.enabled:
                log.info("Tentative de synchronisation de la configuration cloud...")
                res = self.telemetry.sync_config(current_version="v1.0.0")
                if res:
                    if res.get("is_expired"):
                        log.error("❌ Licence expirée ou inactive. Le bot ne peut pas démarrer.")
                        sys.exit(1)
                    if res.get("ok"):
                        self.remote_config = res
                        log.info("Configuration cloud synchronisée avec succès.")
                        
                        # Mettre à jour les paramètres de trading
                        cloud_cfg = res.get("config", {})
                        self.adaptive_risk_pct = cloud_cfg.get("risk_pct", self.adaptive_risk_pct)
                        self.adaptive_score_min = cloud_cfg.get("score_min", self.adaptive_score_min)
                        
                        if not cloud_cfg.get("is_running", True):
                            self.is_paused = True
                            log.info("⏸️ Le bot démarre en état de PAUSE (configuré ainsi sur le Cloud).")

                        # Récupérer les informations du Broker depuis le Cloud
                        broker_info = res.get("broker")
                        if broker_info:
                            active_broker_type = broker_info.get("broker_type", BROKER_TYPE)
                            # Si c'est MT5, rajouter les clés de connexion spécifiques
                            if active_broker_type == "mt5":
                                broker_kwargs["login"] = broker_info.get("login")
                                broker_kwargs["password"] = broker_info.get("password")
                                broker_kwargs["server"] = broker_info.get("server")
                                broker_kwargs["path"] = broker_info.get("path")
                            else:
                                broker_kwargs["api_key"] = broker_info.get("api_key")
                                broker_kwargs["api_secret"] = broker_info.get("api_secret")
                            log.info(f"Utilisation du broker configuré sur le Cloud : {active_broker_type}")
                        
                        # Vérification des mises à jour
                        update_info = res.get("update", {})
                        if update_info.get("available"):
                            log.warning(f"🔔 Une nouvelle version du bot est disponible : {update_info.get('latest_version')}")
                            if update_info.get("mandatory"):
                                log.error("❌ Cette mise à jour est obligatoire. Veuillez mettre à jour le bot pour continuer.")
                                sys.exit(1)

            log.info(f"Création du broker : {active_broker_type}")
            self.broker = create_broker(active_broker_type, **broker_kwargs)
            log.info("Broker initialisé")
            
            try:
                acc_summary = self.broker.get_account_summary()
                self.initial_balance = float(acc_summary.get("equity") or acc_summary.get("balance") or self.broker.get_balance())
                log.info(f"Solde/Équité initial détecté : {self.initial_balance}")
            except Exception as e:
                log.warning(f"⚠️  Impossible de récupérer le solde initial via le résumé du compte : {e}")
                try:
                    self.initial_balance = self.broker.get_balance()
                    log.info(f"Solde initial détecté (fallback get_balance) : {self.initial_balance}")
                except Exception as e2:
                    log.warning(f"⚠️  Impossible de récupérer le solde initial : {e2}")
                    self.initial_balance = 10000.0

            # Déterminer les instruments selon le broker (clés spécifiques au broker en priorité)
            broker_type = active_broker_type  # "binance", "alpaca", "paper_forex", "mt5"
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
                log.info(f"Aucun instrument configuré — défauts courtier ({active_broker_type}) : {self.instruments}")

            news_broker_key = f"NEWS_ASSETS_{active_broker_type.upper()}"
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
                log.info(f"Actifs de nouvelles — défauts broker ({active_broker_type}) : {self.news_assets}")

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
                'BE_DYN_RR': BE_DYN_RR,
                'BE_DYN_RR_RATIO': BE_DYN_RR_RATIO,
                'MIN_POSITION_SIZE': actual_min_pos,
                'MAX_POSITION_SIZE': actual_max_pos,
                'COOLDOWN_SECONDS': COOLDOWN_SECONDS,  # ✅ BUG FIX #5
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
                'VWAP_WINDOW': VWAP_WINDOW,
                # Filtres crypto — rapport post-mortem 2026-07-02
                'CRYPTO_BLACKLIST': CRYPTO_BLACKLIST,
                'CRYPTO_SCORE_MIN': CRYPTO_SCORE_MIN,
                'CRYPTO_BUY_BLOCK_BTC_DROP': CRYPTO_BUY_BLOCK_BTC_DROP,
                'CRYPTO_BNB_VOLUME_FACTOR': CRYPTO_BNB_VOLUME_FACTOR,
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
                    dash_port = int(os.environ.get("DASHBOARD_PORT", 5000))
                    self.dashboard = Dashboard(port=dash_port, host="0.0.0.0")
                    log.info(f"Dashboard initialisé sur le port {dash_port}")
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
            failed_symbols = set()
            for symbol in self.instruments:
                try:
                    pos = self.broker.get_position(symbol)
                    if pos and pos.get('size', 0) > 0:
                        active_positions[symbol] = {
                            'side': pos['side'],
                            'size': pos['size'],
                            'entry_price': pos['entry_price'],
                            'stop_loss': pos.get('stop_loss', 0.0) or self.positions.get(symbol, {}).get('stop_loss', 0.0),
                            'take_profit': pos.get('take_profit', 0.0) or self.positions.get(symbol, {}).get('take_profit', 0.0),
                            'liquidation_price': pos.get('liquidation_price', 0.0),
                            'timestamp': self.positions.get(symbol, {}).get('timestamp') or pos.get('timestamp') or datetime.now(timezone.utc),
                            'status': 'open'
                        }
                except Exception as e:
                    log.warning(f"Erreur API lors de la vérification de la position de {symbol} : {e}")
                    failed_symbols.add(symbol)

            # Détecter les positions fermées
            for symbol, old_pos in self.positions.items():
                if symbol in failed_symbols:
                    # En cas d'échec de l'API, on conserve la position en mémoire pour éviter d'ouvrir des doublons
                    log.warning(f"⚠️ Impossible de vérifier le statut de la position {symbol}. Maintien en mémoire par sécurité.")
                    active_positions[symbol] = old_pos
                    continue
                    
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
                                trade_time = t.get('timestamp')
                                pos_time = old_pos.get('timestamp')
                                if trade_time and pos_time:
                                    if isinstance(trade_time, str):
                                        trade_time = datetime.fromisoformat(trade_time.replace('Z', '+00:00'))
                                    if isinstance(pos_time, str):
                                        pos_time = datetime.fromisoformat(pos_time.replace('Z', '+00:00'))
                                    
                                    # Handle tzinfo difference
                                    if trade_time.tzinfo is None and pos_time.tzinfo is not None:
                                        trade_time = trade_time.replace(tzinfo=timezone.utc)
                                    elif trade_time.tzinfo is not None and pos_time.tzinfo is None:
                                        pos_time = pos_time.replace(tzinfo=timezone.utc)
                                        
                                    if trade_time >= pos_time:
                                        matching_trade = t
                                        break
                                else:
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
                                raw_pnl = (exit_price - entry_price) * size
                            else:
                                raw_pnl = (entry_price - exit_price) * size
                            # ✅ BUG FIX #1 — Conversion devise de cotation → devise du compte
                            # Sur les paires XXX/JPY, le PnL brut est en JPY, pas en USD.
                            # On divise par exit_price (taux XXXJPY) pour obtenir le PnL en USD.
                            pnl = self._convert_pnl_to_account_currency(symbol, raw_pnl, exit_price)
                            log.info(f"Calcul théorique de la fermeture pour {symbol} : Exit={exit_price}, P&L={pnl:.2f} (brut={raw_pnl:.2f})")
                        except Exception as e:
                            log.error(f"Erreur lors du calcul théorique de fermeture pour {symbol} : {e}")
                            
                    # Enregistrer le trade clôturé
                    if self.risk_manager:
                        # ✅ BUG FIX #3 — Propager market_regime depuis la position ouverte vers la clôture
                        market_regime_at_open = old_pos.get('market_regime', 'UNKNOWN')
                        trade_record = {
                            'symbol': symbol,
                            'side': 'buy' if side == 'LONG' else 'sell',
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'position_size': size,
                            'pnl': pnl,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'status': 'closed',
                            'market_regime': market_regime_at_open,
                            'broker': BROKER_TYPE
                        }
                        self.risk_manager.record_trade(trade_record)

                        # Envoi de la clôture à la télémétrie Cloud
                        if self.telemetry.enabled:
                            try:
                                pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
                                if side == 'SHORT':
                                    pnl_pct = -pnl_pct
                                
                                self.telemetry.push_position(
                                    symbol=symbol,
                                    side=side,
                                    qty=size,
                                    entry_price=entry_price,
                                    current_price=exit_price,
                                    pnl=pnl,
                                    pnl_pct=pnl_pct,
                                    status="closed",
                                    broker=self.broker.get_asset_type()
                                )
                            except Exception as e:
                                log.debug(f"Erreur envoi position (fermeture) télémétrie : {e}")

                        # 🎯 TRACKING P&L PAR ACTIF POUR BLOCAGE DYNAMIQUE
                        # Ajouter le P&L au cumul de session
                        current_pnl = self.session_pnl_by_symbol.get(symbol, 0.0)
                        self.session_pnl_by_symbol[symbol] = current_pnl + pnl

                        # Calculer le seuil de perte de session de manière hybride/safe
                        val = self.ASSET_BLOCK_LOSS_THRESHOLD
                        if val >= 1.0:
                            threshold_usd = val
                        elif 0.0 < val < 1.0:
                            threshold_usd = self.initial_balance * val
                        else:
                            threshold_usd = float('inf')  # Désactivé si <= 0

                        if self.session_pnl_by_symbol[symbol] < -threshold_usd:
                            self.blocked_symbols.add(symbol)
                            log.warning(f"🚫 {symbol} BLOQUÉ - Perte session: {self.session_pnl_by_symbol[symbol]:.2f} USD (seuil: -{threshold_usd:.2f} USD)")
                        elif pnl < 0:
                            log.info(f"📉 {symbol} : {self.session_pnl_by_symbol[symbol]:.2f} USD de perte cumulée en session")
            # Mettre à jour self.positions
            self.positions = active_positions

            # Mettre à jour self.risk_manager.open_positions
            if self.risk_manager:
                self.risk_manager.open_positions = {
                    symbol: {
                        'symbol': symbol,  # ✅ BUG FIX #2 — Nécessaire pour la conversion JPY→USD du PnL latent
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
                # Réinitialiser le cache des données de marché pour ce cycle
                self._market_data_cache = {}
                self._indicators_cache = {}
                self._strategy_cache = {}
                self._cached_balance = 0.0  # sera mis à jour au premier appel get_balance()

                now_time = time.time()
                # 📡 TÉLÉMÉTRIE CLOUD : Synchronisation et heartbeat (fréquence réduite)
                if self.telemetry.enabled and (now_time - self._last_cloud_sync >= self.CLOUD_SYNC_INTERVAL):
                    res = self.telemetry.sync_config(current_version="v1.0.0")
                    self._last_cloud_sync = now_time
                    if res:
                        if res.get("is_expired"):
                            log.error("❌ Licence expirée ou inactive détectée. Arrêt automatique du bot.")
                            self.stop()
                            break
                        
                        cloud_cfg = res.get("config", {})
                        self.adaptive_risk_pct = cloud_cfg.get("risk_pct", self.adaptive_risk_pct)
                        self.adaptive_score_min = cloud_cfg.get("score_min", self.adaptive_score_min)
                        
                        # Commande de pause/reprise depuis l'interface web
                        cloud_running = cloud_cfg.get("is_running", True)
                        if not cloud_running and not self.is_paused:
                            log.info("⏸️ Commande de PAUSE reçue depuis le Cloud.")
                            self.is_paused = True
                        elif cloud_running and self.is_paused:
                            log.info("▶️ Commande de REPRISE reçue depuis le Cloud.")
                            self.is_paused = False
                            
                    # Envoyer le signal de vie (heartbeat)
                    self.telemetry.push_heartbeat(
                        is_running=self.running and not self.is_paused,
                        broker_type=self.broker.get_asset_type(),
                        testnet=getattr(self.broker, 'testnet', True) or getattr(self.broker, 'account_type', 'PAPER') == 'PAPER' or 'demo' in str(getattr(self.broker, 'server', '')).lower() or 'demo' in str(getattr(self.broker, 'company', '')).lower()
                    )
                
                # 📡 TÉLÉMÉTRIE CLOUD : Envoi périodique des métriques du compte et des positions actives
                if self.telemetry.enabled and (now_time - self._last_telemetry_push >= self.TELEMETRY_INTERVAL):
                    self._last_telemetry_push = now_time
                    # Envoyer l'état de l'équité
                    try:
                        acc_summary = self.broker.get_account_summary()
                        equity = 0.0
                        if acc_summary:
                            equity = float(acc_summary.get("equity") or acc_summary.get("balance") or 0.0)
                        
                        # Fallback en cas de valeur non disponible ou nulle
                        if equity <= 0.0:
                            bal = self.broker.get_balance()
                            if bal > 0.0:
                                equity = bal
                                
                        if equity > 0.0:
                            pnl_total = equity - self.initial_balance
                            self.telemetry.push_equity(equity=equity, pnl_total=pnl_total, drawdown=0.0)
                        else:
                            log.warning("⚠️ Impossible de pousser l'équité à la télémétrie : valeur invalide ou nulle.")
                    except Exception as e:
                        log.debug(f"Erreur envoi équité télémétrie : {e}")

                    # Envoyer les positions ouvertes
                    try:
                        for symbol, pos in self.positions.items():
                            pnl = pos.get("unrealized_pnl", 0.0)
                            entry = pos.get("entry_price", 0.0)
                            current = pos.get("mark_price", entry)
                            pnl_pct = ((current - entry) / entry * 100) if entry > 0 else 0.0
                            if pos.get("side") == "SHORT":
                                pnl_pct = -pnl_pct
                            
                            self.telemetry.push_position(
                                symbol=symbol,
                                side=pos.get("side", "LONG"),
                                qty=pos.get("size", 0.0),
                                entry_price=entry,
                                current_price=current,
                                pnl=pnl,
                                pnl_pct=pnl_pct,
                                status="open",
                                broker=self.broker.get_asset_type()
                            )
                    except Exception as e:
                        log.debug(f"Erreur envoi positions télémétrie : {e}")

                # Gestion du mode pause
                if self.is_paused:
                    log.info("😴 Bot en pause. En attente du signal de démarrage depuis la plateforme web...")
                    cycle_duration = time.time() - cycle_start_time
                    target_cycle_time = 60
                    if cycle_duration < target_cycle_time:
                        sleep_time = target_cycle_time - cycle_duration
                        slept = 0
                        while slept < sleep_time and self.running and not self.shutdown_event.is_set():
                            time.sleep(min(1, sleep_time - slept))
                            slept += 1
                    continue

                # 📅 RESET QUOTIDIEN DES BLOCAGES D'ACTIFS
                today = datetime.now().date()
                if today != self.session_date:
                    blocked_count = len(self.blocked_symbols)
                    self.blocked_symbols.clear()
                    self.session_pnl_by_symbol.clear()
                    self.session_date = today
                    if blocked_count > 0:
                        log.info(f"📅 Reset quotidien : {blocked_count} actifs débloqués pour nouvelle session")
                    else:
                        log.debug("📅 Reset quotidien des blocages d'actifs")

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

                # Traiter chaque instrument en parallèle pour accélérer l'exécution (mélangé aléatoirement)
                import random
                from concurrent.futures import ThreadPoolExecutor
                scanned_instruments = list(self.instruments)
                random.shuffle(scanned_instruments)

                def run_process_symbol(symbol):
                    if not self.running or self.shutdown_event.is_set():
                        return
                    try:
                        self._process_symbol(symbol)
                    except Exception as e:
                        log.error(f"Erreur lors du traitement de {symbol} : {e}")
                        log.debug(traceback.format_exc())
                        self.stats['errors_count'] += 1

                max_workers = min(16, len(scanned_instruments)) if scanned_instruments else 1
                if max_workers > 1:
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Convertir le map en list pour forcer l'évaluation dans le bloc 'with'
                        list(executor.map(run_process_symbol, scanned_instruments))
                else:
                    for symbol in scanned_instruments:
                        run_process_symbol(symbol)

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

            # 2. Calculer les indicateurs techniques (avec cache de cycle)
            if not hasattr(self, '_indicators_cache'):
                self._indicators_cache = {}
            if symbol in self._indicators_cache:
                df_with_indicators = self._indicators_cache[symbol]
            else:
                df_with_indicators = self.technical_indicators.calculate_all_indicators(df.copy())
                self._indicators_cache[symbol] = df_with_indicators
            self.market_data[symbol] = df_with_indicators

            # === GESTION DE RISQUE CONTINUE DES POSITIONS OUVERTES ===
            self._update_active_position_risk(symbol, df_with_indicators)

            # 🚫 BLOCAGE DYNAMIQUE : Skip si actif bloqué pour cette session
            if symbol in self.blocked_symbols:
                log.info(f"⛔ {symbol} bloqué pour cette session (perte cumulée > seuil)")
                return

            # Si le courtier est crypto et que le symbole n'est pas parmi les actifs sélectionnés
            if self.broker.get_asset_type() == "crypto":
                active_cryptos = getattr(self, '_active_crypto_symbols', [])
                if active_cryptos and symbol not in active_cryptos:
                    # Ne pas chercher à ouvrir de nouvelles positions sur cet actif
                    return

            # 🕒 FILTRE SESSION US (Alpaca/Stocks)
            if self.broker.get_asset_type() == "stock":
                now_utc = datetime.now(timezone.utc).time()
                start_session = datetime.strptime("14:30", "%H:%M").time()
                end_session = datetime.strptime("21:00", "%H:%M").time()
                if not (start_session <= now_utc <= end_session):
                    log.debug(f"Hors session US ({now_utc}) : skip {symbol}")
                    return

            # 3. Analyser le marché et générer un signal de trading (avec cache de cycle)
            if not hasattr(self, '_strategy_cache'):
                self._strategy_cache = {}
            if symbol in self._strategy_cache:
                signal_data = self._strategy_cache[symbol]
            else:
                # Passer le vrai solde et le Kelly réel calculé depuis l'historique au modèle
                _real_balance = getattr(self, '_cached_balance', 0.0)
                _real_win_rate = None
                if self.risk_manager and len(self.risk_manager.trade_history) >= self.risk_manager.MIN_TRADES_FOR_KELLY:
                    _real_win_rate = self.risk_manager._calculate_kelly_fraction()

                # P1-1 : Calculer la variation BTC 24h depuis les données de marché en cache
                _btc_change_24h = None
                if self.broker.get_asset_type() == "crypto":
                    btc_sym = 'BTC/USDT'
                    btc_df_24h = self.market_data.get(btc_sym)
                    if btc_df_24h is not None and len(btc_df_24h) >= 24:
                        try:
                            price_now = float(btc_df_24h.iloc[-1]['close'])
                            price_24h = float(btc_df_24h.iloc[-24]['close'])  # 24 bougies H1 = 24h
                            if price_24h > 0:
                                _btc_change_24h = (price_now - price_24h) / price_24h * 100.0
                                log.debug(f"[P1-1] Variation BTC 24h: {_btc_change_24h:+.2f}%")
                        except Exception as _e:
                            log.debug(f"[P1-1] Impossible de calculer la variation BTC 24h: {_e}")

                # Récupérer les facteurs NLP et filtres depuis le NewsManager
                _sentiment_factor = 1.0
                _news_filter_passed = True
                if self.news_manager:
                    try:
                        _sentiment_factor = self.news_manager.get_risk_factor()
                        _should_avoid, _ = self.news_manager.should_avoid_trading_due_to_news(symbol)
                        _news_filter_passed = not _should_avoid
                    except Exception as e:
                        log.debug(f"Erreur NewsManager: {e}")

                signal_data = self.strategy.analyze_market(
                    df_with_indicators,
                    account_balance=_real_balance,
                    real_win_rate=_real_win_rate,
                    symbol=symbol,
                    btc_change_24h=_btc_change_24h,
                    sentiment_factor=_sentiment_factor,
                    news_filter_passed=_news_filter_passed
                )
                self._strategy_cache[symbol] = signal_data
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
                
                # Récupérer la position brute du courtier pour vérifier la présence des ordres SL/TP réels
                broker_pos = self.broker.get_position(symbol)
                broker_tp = broker_pos.get('take_profit', 0.0) if broker_pos else 0.0
                broker_sl = broker_pos.get('stop_loss', 0.0) if broker_pos else 0.0
                
                # Lancer la mise à jour (calcul du trailing stop / break-even)
                self.risk_manager.update_open_position(symbol, current_price)
                
                new_sl = pos_risk.get('stop_loss', 0.0)
                theoretical_tp = pos_risk.get('take_profit', 0.0)
                
                # Recalculer le TP théorique si manquant
                if theoretical_tp == 0.0:
                    entry_price = pos_risk.get('entry_price', current_price)
                    side = pos_risk.get('side', 'LONG')
                    _, theoretical_tp = self.risk_manager.calculate_sl_tp_levels(
                        entry_price=entry_price,
                        atr_value=atr_value,
                        position_side=side,
                        asset_type=self.broker.get_asset_type(),
                        symbol=symbol
                    )
                    pos_risk['take_profit'] = theoretical_tp
                    self.positions[symbol]['take_profit'] = theoretical_tp
                    log.info(f"Recalcul du Take Profit théorique pour {symbol} : {theoretical_tp:.5f}")
                
                # Mettre à jour si le SL a changé, ou s'il manque le SL ou le TP chez le courtier
                should_update_broker = (new_sl != old_sl and new_sl > 0) or (broker_sl == 0.0 and new_sl > 0) or (broker_tp == 0.0 and theoretical_tp > 0)
                
                if should_update_broker:
                    log.info(f"Mise à jour SL/TP pour {symbol} chez le courtier (SL: {old_sl:.5f} -> {new_sl:.5f}, TP: {theoretical_tp:.5f})")
                    success = self.broker.modify_sl_tp(symbol, new_sl, theoretical_tp)
                    if success:
                        # Mettre à jour notre dictionnaire local de suivi de position
                        self.positions[symbol]['stop_loss'] = new_sl
                        self.positions[symbol]['take_profit'] = theoretical_tp

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
        # Mettre le solde en cache pour les prochains appels analyze_market du cycle
        self._cached_balance = account_balance
        entry_price = signal_data['entry_price']

        # 2d. Filtres avancés Forex (Session, Spread, Corrélation, Pivots Obstacles)
        if self.broker.get_asset_type() == 'forex':
            # A. Session horaire (Londres 08h00 - 18h00, bloquer nuits & vendredi soir/week-end)
            from datetime import timedelta
            now_utc = datetime.utcnow()
            
            # Déterminer si DST (British Summer Time - UTC+1) est active à Londres
            is_dst = False
            if 3 < now_utc.month < 10:
                is_dst = True
            elif now_utc.month == 3:
                last_sunday = 31 - (datetime(now_utc.year, 3, 31).weekday() + 1) % 7
                if now_utc.day >= last_sunday:
                    is_dst = True
            elif now_utc.month == 10:
                last_sunday = 31 - (datetime(now_utc.year, 10, 31).weekday() + 1) % 7
                if now_utc.day < last_sunday:
                    is_dst = True

            london_offset = 1 if is_dst else 0
            london_time = now_utc + timedelta(hours=london_offset)
            london_hour = london_time.hour
            weekday = london_time.weekday() # 0 = Lundi, ..., 4 = Vendredi, 5 = Samedi, 6 = Dimanche

            # Règle : entre 08h00 et 18h00 heure de Londres
            in_hours = (8 <= london_hour < 18)
            
            # Bloquer la nuit, le week-end et le vendredi soir (après 17h00 heure de Londres)
            is_weekend = (weekday >= 5) or (weekday == 4 and london_hour >= 17) or (weekday == 6 and london_hour < 17)
            
            if not in_hours or is_weekend:
                log.info(
                    f"🚫 Trade {symbol} rejeté : En dehors de la session Forex (Londres 08h-18h) ou week-end. "
                    f"Heure Londres : {london_time.strftime('%H:%M:%S')} (Jour de la semaine: {weekday})"
                )
                return


            # B. Garde-fou Spread
            spread = self.broker.get_spread(symbol)
            if spread > MAX_SPREAD_PIPS:
                log.info(f"🚫 Trade {symbol} rejeté : Spread trop large ({spread:.1f} pips > {MAX_SPREAD_PIPS} pips max)")
                return

            # C. Corrélation de devises
            clean = symbol.upper().replace("/", "")
            if len(clean) >= 6:
                base_cand = clean[:3]
                quote_cand = clean[3:6]
                
                currency_exposure = {}
                for open_sym, pos in self.positions.items():
                    if pos.get('size', 0) > 0:
                        open_clean = open_sym.upper().replace("/", "")
                        if len(open_clean) >= 6:
                            op_base = open_clean[:3]
                            op_quote = open_clean[3:6]
                            op_side = pos.get('side', '').upper()
                            
                            if op_side in ['LONG', 'BUY']:
                                currency_exposure[op_base] = currency_exposure.get(op_base, 0) + 1
                                currency_exposure[op_quote] = currency_exposure.get(op_quote, 0) - 1
                            elif op_side in ['SHORT', 'SELL']:
                                currency_exposure[op_base] = currency_exposure.get(op_base, 0) - 1
                                currency_exposure[op_quote] = currency_exposure.get(op_quote, 0) + 1

                cand_side = 'LONG' if signal_data.get('should_long') else 'SHORT'
                if cand_side == 'LONG':
                    new_base_exp = currency_exposure.get(base_cand, 0) + 1
                    new_quote_exp = currency_exposure.get(quote_cand, 0) - 1
                else:
                    new_base_exp = currency_exposure.get(base_cand, 0) - 1
                    new_quote_exp = currency_exposure.get(quote_cand, 0) + 1

                if abs(new_base_exp) > MAX_FOREX_CURRENCY_EXPOSURE or abs(new_quote_exp) > MAX_FOREX_CURRENCY_EXPOSURE:
                    log.info(
                        f"🚫 Trade {symbol} rejeté : Risque de corrélation de devises trop élevé. "
                        f"Exposition nette après trade : {base_cand}={new_base_exp}, {quote_cand}={new_quote_exp} "
                        f"(limite autorisée: +/- {MAX_FOREX_CURRENCY_EXPOSURE})"
                    )
                    return

            # D. Obstacle pivot
            last_row = df_with_indicators.iloc[-1]
            pivot = last_row.get('pivot', 0)
            r1 = last_row.get('r1', 0)
            s1 = last_row.get('s1', 0)
            r2 = last_row.get('r2', 0)
            s2 = last_row.get('s2', 0)

            target_obstacle = 0.0
            if signal_data.get('should_long'):
                obstacles = [val for val in [r1, r2] if val > entry_price]
                target_obstacle = min(obstacles) if obstacles else 0.0
            elif signal_data.get('should_short'):
                obstacles = [val for val in [s1, s2] if val < entry_price]
                target_obstacle = max(obstacles) if obstacles else 0.0

            atr_value = df_with_indicators.iloc[-1].get('atr', 0)
            sl_price, _ = self.risk_manager.calculate_sl_tp_levels(
                entry_price, atr_value, 
                "LONG" if signal_data.get('should_long') else "SHORT", 
                asset_type="forex", symbol=symbol
            )
            
            if target_obstacle > 0:
                potential_gain = abs(target_obstacle - entry_price)
                potential_risk = abs(entry_price - sl_price)
                if potential_risk > 0:
                    real_rr = potential_gain / potential_risk
                    if real_rr < 1.0:
                        log.info(f"🚫 Trade {symbol} rejeté : Obstacle pivot trop proche. R:R réel potentiel = {real_rr:.2f} < 1.0 (Obstacle à {target_obstacle:.5f})")
                        return


        # 2b. Filtre volume minimum (protection contre le slippage sur actifs illiquides)
        if self.broker.get_asset_type() == "crypto":
            last_bar = df_with_indicators.iloc[-1]
            volume = float(last_bar.get('volume', 0))
            volume_ma = float(last_bar.get('volume_ma', 0))
            # Rejeter si le volume de la bougie est inférieur à 20% de la moyenne mobile de volume
            if volume_ma > 0 and volume < volume_ma * 0.20:
                log.info(f"🚨 Volume insuffisant pour {symbol} ({volume:.0f} < 20% de {volume_ma:.0f}) — risque de slippage, trade rejeté")
                return

        # 2c. Filtre de dominance BTC pour les altcoins
        # Ne pas ouvrir un SHORT sur un altcoin si BTC est en tendance haussière forte
        if self.broker.get_asset_type() == "crypto" and 'BTC' not in symbol.upper():
            btc_symbol = 'BTC/USDT'
            if btc_symbol in self.market_data and not self.market_data[btc_symbol].empty:
                btc_df = self.market_data[btc_symbol]
                btc_last = btc_df.iloc[-1]
                btc_ema_fast = btc_last.get('ema_fast', 0)
                btc_ema_slow = btc_last.get('ema_slow', 0)
                btc_adx = btc_last.get('adx', 0)
                btc_bullish_trend = btc_ema_fast > btc_ema_slow and btc_adx > 25
                btc_bearish_trend = btc_ema_fast < btc_ema_slow and btc_adx > 25

                if signal_data['should_short'] and btc_bullish_trend:
                    log.info(f"🚨 Filtre dominance BTC : SHORT {symbol} rejeté — BTC est en tendance haussière forte (ADX={btc_adx:.1f})")
                    return
                if signal_data['should_long'] and btc_bearish_trend:
                    log.info(f"🚨 Filtre dominance BTC : LONG {symbol} rejeté — BTC est en tendance baissière forte (ADX={btc_adx:.1f})")
                    return

        # 3. Déterminer le stop loss et take profit via le Risk Manager (pour appliquer les multiplicateurs spécifiques à l'actif)
        atr_value = df_with_indicators.iloc[-1].get('atr', 0)
        if atr_value > 0 and self.risk_manager:
            position_side = "LONG" if signal_data['should_long'] else "SHORT"
            sl_price, tp_price = self.risk_manager.calculate_sl_tp_levels(
                entry_price, atr_value, position_side,
                asset_type=self.broker.get_asset_type(),
                symbol=symbol
            )
        else:
            # Fallback : utiliser les valeurs calculées par la stratégie
            sl_price = signal_data.get('sl_price') or (entry_price * 0.98 if signal_data['should_long'] else entry_price * 1.02)
            tp_price = signal_data.get('tp_price') or (entry_price * 1.04 if signal_data['should_long'] else entry_price * 0.96)

        # 3. Calculer la taille de position avec le Risk Manager
        position_size, size_details = self.risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss=sl_price,
            symbol=symbol,
            sentiment_factor=self.news_manager.get_risk_factor() if self.news_manager else 1.0,
            broker=self.broker
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
        if not self.risk_manager._can_take_new_trade(account_balance, symbol):
            log.info(f"Limites de risque ou limite par symbole atteintes, pas de nouvel ordre pour {symbol}")
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
                'market_regime': signal_data['market_regime'],
                'broker': BROKER_TYPE
            }
            self.risk_manager.record_trade(trade_record)

            # Mettre à jour la position suivie (avec market_regime pour propagation à la clôture)
            self._update_position_tracking(symbol, side, position_size, entry_price, sl_price, tp_price,
                                            market_regime=signal_data.get('market_regime', 'UNKNOWN'))

        else:
            log.error(f"Échec de l'exécution du trade pour {symbol}")

    def _select_and_rotate_crypto(self):
        """
        Pour la crypto, sélectionne automatiquement les meilleurs actifs (jusqu'à K positions max)
        parmi tous les instruments configurés et gère la rotation si un nouvel actif devient nettement
        plus performant que l'un des actifs sélectionnés.
        """
        try:
            if not self.broker or self.broker.get_asset_type() != "crypto":
                return

            # 1. Calculer les scores pour TOUS les instruments crypto configurés
            scores = {}
            for symbol in self.instruments:
                try:
                    df = self._fetch_market_data(symbol)
                    if df is None or len(df) < 50:
                        continue

                    # Utiliser le cache du cycle pour les indicateurs
                    if not hasattr(self, '_indicators_cache'):
                        self._indicators_cache = {}
                    if symbol in self._indicators_cache:
                        indicators = self._indicators_cache[symbol]
                    else:
                        indicators = self.technical_indicators.calculate_all_indicators(df.copy())
                        self._indicators_cache[symbol] = indicators

                    # Utiliser le cache du cycle pour les signaux
                    if not hasattr(self, '_strategy_cache'):
                        self._strategy_cache = {}
                    if symbol in self._strategy_cache:
                        signal = self._strategy_cache[symbol]
                    else:
                        signal = self.strategy.analyze_market(indicators)
                        self._strategy_cache[symbol] = signal

                    # Calcul du score de force de tendance/momentum
                    last = df.iloc[-1]
                    score = float(signal.get('total_score', 0))

                    # Bonus de tendance à long terme
                    ema_200 = last.get('ema_trend', last['close'])
                    score += 5.0 if last['close'] > ema_200 else -5.0

                    # Force de tendance ADX
                    adx = last.get('adx', 0)
                    score += (adx / 10.0) if last['close'] > ema_200 else -(adx / 10.0)

                    # RSI (momentum)
                    rsi = last.get('rsi', 50)
                    score += (rsi - 50) / 10.0

                    scores[symbol] = score
                except Exception as e:
                    log.debug(f"Erreur lors du calcul du score pour {symbol} : {e}")

            if not scores:
                log.debug("Aucun instrument crypto valide pour la rotation.")
                return

            # Déterminer la limite de positions pour ce broker
            limit_pos = self.risk_manager.MAX_OPEN_POSITIONS if self.risk_manager else 2
            limit_pos = max(1, min(limit_pos, len(scores)))

            # Trier les instruments par score décroissant
            sorted_symbols = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

            # Récupérer les actifs actuellement actifs
            current_active = list(getattr(self, '_active_crypto_symbols', []))
            if not current_active:
                current_active = sorted_symbols[:limit_pos]
                log.info(f"Initialisation des actifs crypto actifs : {current_active}")

            # Si le nombre d'actifs actifs est inférieur à limit_pos, on en ajoute
            while len(current_active) < limit_pos:
                added = False
                for sym in sorted_symbols:
                    if sym not in current_active:
                        current_active.append(sym)
                        added = True
                        break
                if not added:
                    break

            # Gérer la rotation
            for i in range(len(current_active)):
                active_sym = current_active[i]
                active_score = scores.get(active_sym, -999)

                inactive_symbols = [s for s in sorted_symbols if s not in current_active]
                if not inactive_symbols:
                    break

                best_inactive = inactive_symbols[0]
                best_inactive_score = scores[best_inactive]

                if best_inactive_score > active_score + 2.0:
                    log.info(f"🔄 ROTATION CRYPTO : Bascule de {active_sym} ({active_score:.2f}) vers {best_inactive} ({best_inactive_score:.2f})")
                    current_active[i] = best_inactive

                    if active_sym in self.positions:
                        log.info(f"Fermeture de la position sur {active_sym} pour rotation vers {best_inactive}")
                        self.broker.close_position(active_sym, reason="Rotation de portefeuille crypto")
                        # Bug#5 fix : pas de _sync_positions_with_broker ici
                        # La synchronisation est déjà faite au début du cycle dans la boucle principale

            self._active_crypto_symbols = current_active
            log.info(f"Évaluation Crypto : {len(scores)} actifs scannés | Actifs actifs : {self._active_crypto_symbols}")

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
        # Vérifier d'abord le cache du cycle de trading pour éviter des appels API doubles
        cache = getattr(self, '_market_data_cache', {})
        if symbol in cache:
            return cache[symbol]

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

            # Mettre en cache pour ce cycle
            if not hasattr(self, '_market_data_cache'):
                self._market_data_cache = {}
            self._market_data_cache[symbol] = df

            return df

        except Exception as e:
            log.error(f"Erreur lors de la récupération des données pour {symbol} : {e}")
            return None

    def _convert_pnl_to_account_currency(self, symbol: str, pnl: float, reference_price: float) -> float:
        """
        ✅ BUG FIX #1 — Convertit un PnL brut dans la devise de cotation vers la devise du compte (USD).

        Pour les paires forex classiques (ex: EURUSD), le PnL est déjà en USD → pas de conversion.
        Pour les paires dont la devise de cotation est le JPY (ex: USDJPY, GBPJPY, EURJPY),
        le PnL brut calculé par (price_diff * size) est en JPY. On divise par le taux de change
        (reference_price = taux au moment de la clôture) pour obtenir le montant en USD.

        Cette méthode peut être étendue pour d'autres devises de cotation (CHF, CAD, etc.)
        si le compte de trading n'est pas libellé dans la même devise.

        Args:
            symbol: Symbole de l'instrument (ex: 'GBPJPY', 'EURUSD')
            pnl: PnL brut calculé en devise de cotation
            reference_price: Prix de sortie (taux de change au moment de la clôture)

        Returns:
            PnL converti en USD (devise du compte)
        """
        normalized = symbol.strip().upper().replace("/", "")
        # Paires dont la quote currency est le JPY : le PnL brut est en JPY
        if normalized.endswith("JPY"):
            if reference_price > 0:
                converted = pnl / reference_price
                log.debug(f"Conversion PnL JPY→USD pour {symbol} : {pnl:.2f} JPY / {reference_price:.3f} = {converted:.2f} USD")
                return converted
            else:
                log.warning(f"Prix de référence nul pour {symbol}, conversion JPY→USD impossible")
                return pnl
        # Pour toutes les autres paires (EURUSD, GBPUSD, etc.), le PnL est déjà en USD
        return pnl

    def _update_position_tracking(self, symbol: str, side: str, size: float, entry_price: float,
                                   stop_loss: float = 0.0, take_profit: float = 0.0,
                                   market_regime: str = 'UNKNOWN'):
        """
        Met à jour le suivi des positions ouvertes.

        Args:
            symbol: Symbole de l'instrument
            side: Côté de la position ('buy' ou 'sell')
            size: Taille de la position
            entry_price: Prix d'entrée
            stop_loss: Niveau de Stop Loss
            take_profit: Niveau de Take Profit
            market_regime: Régime de marché au moment de l'ouverture
        """
        position_side = "LONG" if side == "buy" else "SHORT"

        self.positions[symbol] = {
            'side': position_side,
            'size': size,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now(timezone.utc),
            'status': 'open',
            # ✅ BUG FIX #3 — Stocker le régime de marché pour propagation à la clôture
            'market_regime': market_regime
        }

        log.debug(f"Position suivie mise à jour pour {symbol} : {position_side} {size} | Régime: {market_regime}")

        if self.telemetry.enabled:
            try:
                self.telemetry.push_position(
                    symbol=symbol,
                    side=position_side,
                    qty=size,
                    entry_price=entry_price,
                    current_price=entry_price,
                    pnl=0.0,
                    pnl_pct=0.0,
                    status="open",
                    broker=self.broker.get_asset_type()
                )
            except Exception as e:
                log.debug(f"Erreur envoi position (update tracking) télémétrie : {e}")

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
                sentiment_factor=self.news_manager.get_risk_factor() if self.news_manager else 1.0,
                broker=self.broker
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
                    'market_regime': 'Webhook Alert',
                    'broker': BROKER_TYPE
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
        Calcule le taux de victoire sur les 20 derniers trades CLÔTURÉS.

        Returns:
            Taux de victoire entre 0.0 et 1.0, ou 0.0 si pas assez de trades.
        """
        # Filtrer uniquement les trades clôturés avec P&L valide
        closed_trades = [t for t in self.risk_manager.trade_history if t.get('status') == 'closed' and t.get('pnl') is not None]

        if not closed_trades:
            return 0.0

        recent = closed_trades[-20:]
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
        # Filtrer uniquement les trades CLÔTURÉS avec P&L valide
        closed_trades = [t for t in self.risk_manager.trade_history if t.get('status') == 'closed' and t.get('pnl') is not None]

        if len(closed_trades) < 10:
            return  # Pas assez de données pour détecter une dérive

        # Calculer le taux de victoire sur les 10 derniers trades clôturés
        recent = closed_trades[-10:]
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