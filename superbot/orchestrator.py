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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set
import threading
import traceback

# Importer les modules du SuperBot
from superbot.config import (
    BROKER_TYPE, ALLOW_LIVE_TRADING, INSTRUMENTS, GRANULARITY,
    LOG_LEVEL, LOG_FILE, ENABLE_DASHBOARD, WEBHOOK_ENABLED,
    WEBHOOK_SECRET, WEBHOOK_HOST, WEBHOOK_PORT,
    
    # Risk Management
    RISK_PCT, MAX_DAILY_LOSS_PCT, MAX_MONTHLY_LOSS_PCT, MAX_OPEN_POSITIONS,
    KELLY_FRACTION, MIN_TRADES_FOR_KELLY, SL_ATR_MULT, TP_ATR_MULT,
    TRAIL_ATR_MULT, TRAIL_ACTIVATE_ATR_MULT, BE_ATR_MULT, MIN_POSITION_SIZE, MAX_POSITION_SIZE,
    COOLDOWN_SECONDS,
    MAX_FOREX_CURRENCY_EXPOSURE, MAX_SPREAD_PIPS, BE_DYN_RR, BE_DYN_RR_RATIO,
    # Seuils de drawdown et perte maximale journalière
    MAX_DAILY_LOSS_AMOUNT,
    DRAWDOWN_THRESH_1, DRAWDOWN_THRESH_2, DRAWDOWN_REDUCE_5PCT, DRAWDOWN_REDUCE_10PCT,

    
    # Strategy / Indicators
    SCORE_MIN, EMA_FAST, EMA_SLOW, EMA_TREND, HTF_EMA, D1_EMA, W1_EMA,
    RSI_LEN, RSI_OB, RSI_OS, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    ADX_LEN, ADX_TREND, ST_MULTIPLIER, ST_ATR_LEN, ATR_LEN,
    BB_LEN, BB_STD, ICHIMOKU_TENKAN, ICHIMOKU_KIJUN,
    ICHIMOKU_SENKOU_SPAN_B, ICHIMOKU_DISPLACEMENT, VWAP_WINDOW,

    # Paramètres par classe d'actifs (P0 — refactoring stratégie)
    EMA_FAST_CRYPTO, EMA_SLOW_CRYPTO, ADX_TREND_CRYPTO, SCORE_MIN_CRYPTO,
    SL_ATR_MULT_CRYPTO, TP_ATR_MULT_CRYPTO,
    EMA_FAST_FOREX, EMA_SLOW_FOREX, ADX_TREND_FOREX, SCORE_MIN_FOREX,
    SL_ATR_MULT_FOREX, TP_ATR_MULT_FOREX, FOREX_NEWS_AVOID_MINUTES,
    EMA_FAST_STOCK, EMA_SLOW_STOCK, ADX_TREND_STOCK, SCORE_MIN_STOCK,
    SL_ATR_MULT_STOCK, TP_ATR_MULT_STOCK, ALLOW_SHORT_STOCK,
    # News & Sentiment
    NEWS_ASSETS, NEWS_UPDATE_INTERVAL, NEWS_AVOIDANCE_BEFORE, NEWS_AVOIDANCE_AFTER,
    NEWS_RISK_REDUCTION_FACTOR, NEWS_HIGH_IMPACT_ONLY, FEAR_GREED_EXTREME_FEAR,
    FEAR_GREED_EXTREME_GREED, CRYPTOCOMPARE_API_KEY,

    # Filtres crypto
    CRYPTO_BLACKLIST, CRYPTO_SCORE_MIN, CRYPTO_BUY_BLOCK_BTC_DROP, CRYPTO_BNB_VOLUME_FACTOR,
    COMMISSION_PCT, SLIPPAGE_PCT,

    # ⚡ V3 — Cycle, performances et sessions
    CYCLE_TIME, SYMBOL_TIMEOUT_SECONDS, MAX_PARALLEL_SYMBOLS,
    DAILY_TARGET_EUR, SESSION_AWARE, TRADING_MODE,
    SIMULATED_SLIPPAGE_POINTS, SIMULATED_COMMISSION_PCT,

    # 🪙 V3 — Crypto MT5
    MT5_CRYPTO_ENABLED, MT5_CRYPTO_SYMBOLS,

    # 📊 V3 — Tiers de solde adaptatifs
    BALANCE_TIER_HIGH, BALANCE_TIER_MID, BALANCE_TIER_LOW, BALANCE_TIER_MICRO,

    # 🧠 V3 — Auto-apprentissage
    AUTO_LEARN_ENABLED, POST_SESSION_DEBRIEF_HOUR_UTC, PRE_SESSION_ANALYSIS_HOUR_UTC,
    KNOWLEDGE_FEEDER_ENABLED,

    # DB
    DB_PATH,

    # 📈 TSMOM — time-series momentum (stratégie mensuelle)
    TSMOM_ENABLED, TSMOM_PLACE_ORDERS, TSMOM_UNIVERSE, TSMOM_BROKER_SYMBOLS,
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
from logging.handlers import RotatingFileHandler
from superbot.telemetry import TelemetryClient, TelemetryLoggingHandler

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        # Forcer UTF-8 sur la console Windows (sinon CP1252 corrompt les emoji).
        logging.StreamHandler(open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False))
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
        self.active_broker_type = BROKER_TYPE

        # 📈 TSMOM — time-series momentum (stratégie mensuelle)
        self.TSMOM_ENABLED = TSMOM_ENABLED
        self.TSMOM_PLACE_ORDERS = TSMOM_PLACE_ORDERS
        self.TSMOM_UNIVERSE = TSMOM_UNIVERSE
        self.TSMOM_BROKER_SYMBOLS = TSMOM_BROKER_SYMBOLS
        self._tsmom_last_month = None
        self._tsmom_last_log_day = None

        # Composants principaux
        self.broker = None
        self.strategy = None
        self.risk_manager = None
        self.news_manager = None
        self.technical_indicators = None
        self.dashboard = None
        self.bug_watchdog = None
        self.profit_circuit_breaker = None

        # Données de marché et états
        self.market_data: Dict[str, any] = {}  # Symbol -> DataFrame avec indicateurs
        self.positions: Dict[str, Dict] = {}   # Symbol -> position info
        self.active_orders: Dict[str, Dict] = {} # Symbol -> ordre info
        self.instruments: List[str] = []
        self.news_assets: List[str] = []
        self.initial_balance: float = 10000.0

        # Paramètres adaptatifs — source unique de vérité (RuntimeConfig).
        # adaptive_risk_pct / adaptive_score_min délèguent ici via des propriétés
        # et propagent automatiquement vers RiskManager / TradingStrategy.
        from superbot.components.runtime_config import RuntimeConfig
        self.runtime_config = RuntimeConfig(risk_pct=RISK_PCT, score_min=SCORE_MIN)
        self._adaptation_counter = 0
        self._adaptation_every = 10  # cycles

        # Blocage dynamique des actifs perdants (géré par StateManager)
        
        # Persistance complète des états
        from superbot.state import StateManager
        import os
        state_file = os.path.join(root_dir, 'superbot', 'logs', f'state_{self.active_broker_type}.json')
        self.state_manager = StateManager(filepath=state_file, ttl_hours=24)
        self.state_manager.load_state()

        # Initialiser l'optimiseur Walk-Forward
        from superbot.ml.walk_forward import WalkForwardOptimizer
        self.walk_forward_optimizer = WalkForwardOptimizer()

        self.failed_execution_cooldowns = self.state_manager.failed_execution_cooldowns
        self.blocked_symbols = self.state_manager.blocked_symbols
        self.session_pnl_by_symbol = self.state_manager.session_pnl_by_symbol
        self.consecutive_losses = self.state_manager.consecutive_losses
        self._adaptation_counter = self.state_manager.adaptation_counter
        
        # 1.2: Verrous pour protéger les accès concurrents.
        #
        # Modèle de threads :
        #   - Boucle principale (cycle_runner) : sync positions, dispatch workers, stats/télémétrie.
        #   - Workers ThreadPoolExecutor (cycle_runner) : _process_symbol → exécution + risk.
        #   - Thread webhook (webhook/server) : ouverture/fermeture manuelle de positions.
        #   - Thread télémétrie (TelemetryClient) : envois HTTP via une file dédiée (pas d'état bot).
        #
        # Convention de verrouillage :
        #   - `_lock`       (RLock) : état de marché — positions, market_data,
        #                            caches de cycle et risk_manager.open_positions.
        #   - `_state_lock` (Lock)  : compteurs/drapeaux — stats, cooldowns,
        #                            blocked_symbols, failed_execution_cooldowns.
        # Ne jamais tenir un verrou pendant un appel broker réseau (I/O).
        self._state_lock = threading.Lock()
        self._lock = threading.RLock()
        
        # Restaurer l'état de pause et de solde journalier initial si même jour calendaire
        self.is_paused = False
        self.session_date = datetime.now().date()
        
        # Vérifier si on est toujours dans la même journée que la sauvegarde
        saved_date_str = self.state_manager.last_daily_reset_str
        same_day = False
        if saved_date_str:
            try:
                same_day = (datetime.fromisoformat(saved_date_str).date() == self.session_date)
            except Exception:
                pass
                
        if same_day:
            self.is_paused = self.state_manager.is_paused
            log.info(f"Restauration de l'état de pause : {self.is_paused}")
        else:
            log.info("Nouvelle journée détectée au démarrage, reset des paramètres de pause.")
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

        # =================================================================
        # ⚡ V3 : Attributs de cycle et performance (lus par cycle_runner)
        # =================================================================
        # Fix bug heartbeat 50-60s : CYCLE_TIME est maintenant 15s par défaut
        self.CYCLE_TIME = CYCLE_TIME
        self.SYMBOL_TIMEOUT_SECONDS = SYMBOL_TIMEOUT_SECONDS
        self.MAX_PARALLEL_SYMBOLS = MAX_PARALLEL_SYMBOLS
        # Objectifs journaliers et mode de trading
        self.DAILY_TARGET_EUR = DAILY_TARGET_EUR
        self.SESSION_AWARE = SESSION_AWARE
        self.TRADING_MODE = TRADING_MODE
        self.SIMULATED_SLIPPAGE_POINTS = SIMULATED_SLIPPAGE_POINTS
        self.SIMULATED_COMMISSION_PCT = SIMULATED_COMMISSION_PCT
        # Crypto MT5
        self.MT5_CRYPTO_ENABLED = MT5_CRYPTO_ENABLED
        self.MT5_CRYPTO_SYMBOLS = MT5_CRYPTO_SYMBOLS
        # Tiers de solde
        self.BALANCE_TIER_HIGH = BALANCE_TIER_HIGH
        self.BALANCE_TIER_MID = BALANCE_TIER_MID
        self.BALANCE_TIER_LOW = BALANCE_TIER_LOW
        self.BALANCE_TIER_MICRO = BALANCE_TIER_MICRO
        # Auto-apprentissage
        self.AUTO_LEARN_ENABLED = AUTO_LEARN_ENABLED
        self.POST_SESSION_DEBRIEF_HOUR_UTC = POST_SESSION_DEBRIEF_HOUR_UTC
        self.PRE_SESSION_ANALYSIS_HOUR_UTC = PRE_SESSION_ANALYSIS_HOUR_UTC
        self.KNOWLEDGE_FEEDER_ENABLED = KNOWLEDGE_FEEDER_ENABLED
        # DB
        self.DB_PATH = DB_PATH

        log.info(
            f"🚀 SuperBot V3 | CYCLE_TIME={self.CYCLE_TIME}s | "
            f"MAX_PARALLEL={self.MAX_PARALLEL_SYMBOLS} | "
            f"DAILY_TARGET={self.DAILY_TARGET_EUR}€ | "
            f"TRADING_MODE={self.TRADING_MODE} | "
            f"MT5_CRYPTO={'activé' if self.MT5_CRYPTO_ENABLED else 'désactivé'}"
        )

        # =================================================================
        # 🧠 V3 : BRAIN — Modules d'intelligence autonome
        # =================================================================
        self.db = None
        self.session_manager = None
        self.knowledge_feeder = None
        self.performance_learner = None
        self.strategy_engine = None
        self.regime_detector = None
        self.report_generator = None
        self.online_learner = None
        self._brain_initialized = False
        self._last_pre_session_hour = -1
        self._last_mid_check_time = 0.0
        self._last_perf_log_time = 0.0
        self._init_brain()

        # Initialiser les composants broker/stratégie
        self._initialize_components()

    # ─── Paramètres adaptatifs : source unique de vérité ─────────────────────

    @property
    def adaptive_risk_pct(self) -> float:
        return self.runtime_config.risk_pct

    @adaptive_risk_pct.setter
    def adaptive_risk_pct(self, value: float):
        self.runtime_config.set(risk_pct=value)

    @property
    def adaptive_score_min(self) -> float:
        return self.runtime_config.score_min

    @adaptive_score_min.setter
    def adaptive_score_min(self, value: float):
        self.runtime_config.set(score_min=value)

    def _init_brain(self):
        """Initialise tous les modules d'intelligence autonome V3."""
        log.info("🧠 Initialisation du Brain V3...")
        try:
            from superbot.db.database import init_db
            self.db = init_db(self.DB_PATH)
            log.info(f"🗄️ DB SQLite initialisée : {self.DB_PATH}")
        except Exception as e:
            log.warning(f"⚠️ DB non disponible : {e}")

        try:
            from superbot.brain.session_manager import SessionManager
            self.session_manager = SessionManager(
                bot_instance=self,
                daily_target_eur=self.DAILY_TARGET_EUR
            )
            log.info("🕐 SessionManager initialisé")
        except Exception as e:
            log.warning(f"⚠️ SessionManager non disponible : {e}")

        try:
            from superbot.brain.strategy_engine import StrategyEngine
            self.strategy_engine = StrategyEngine(db=self.db, session_manager=self.session_manager)
            log.info("♟️ StrategyEngine initialisé")
        except Exception as e:
            log.warning(f"⚠️ StrategyEngine non disponible : {e}")

        try:
            from superbot.brain.performance_learner import PerformanceLearner
            self.performance_learner = PerformanceLearner(
                db=self.db,
                session_manager=self.session_manager,
                strategy_engine=self.strategy_engine
            )
            log.info("📊 PerformanceLearner initialisé")
        except Exception as e:
            log.warning(f"⚠️ PerformanceLearner non disponible : {e}")

        try:
            from superbot.brain.regime_detector import MarketRegimeDetector
            self.regime_detector = MarketRegimeDetector(db=self.db)
            log.info("🔍 RegimeDetector initialisé")
        except Exception as e:
            log.warning(f"⚠️ RegimeDetector non disponible : {e}")

        if self.KNOWLEDGE_FEEDER_ENABLED:
            try:
                from superbot.brain.knowledge_feeder import KnowledgeFeeder
                self.knowledge_feeder = KnowledgeFeeder(db=self.db)
                log.info("🌐 KnowledgeFeeder initialisé")
            except Exception as e:
                log.warning(f"⚠️ KnowledgeFeeder non disponible : {e}")

        # Online Learner (EnsembleScorer partial_fit)
        try:
            from superbot.ml.online_learner import OnlineLearner
            self.online_learner = OnlineLearner(db=self.db)
            log.info("🤖 OnlineLearner initialisé")
        except Exception as e:
            log.warning(f"⚠️ OnlineLearner non disponible : {e}")

        # Report Generator (rapport journalier à 22h30 UTC)
        try:
            from superbot.brain.report_generator import ReportGenerator
            self.report_generator = ReportGenerator(
                db=self.db,
                session_manager=self.session_manager,
                strategy_engine=self.strategy_engine,
                performance_learner=self.performance_learner,
                knowledge_feeder=self.knowledge_feeder,
            )
            self.report_generator.start_daily_scheduler()
            log.info("📝 ReportGenerator initialisé + scheduler 22h30 UTC")
        except Exception as e:
            log.warning(f"⚠️ ReportGenerator non disponible : {e}")

        # Initialiser la DB journalière
        if self.db and self.session_manager:
            try:
                balance = getattr(self, 'initial_balance', 0) or 0
                target = self.session_manager._compute_daily_target(balance or self.BALANCE_TIER_MID)
                self.db.set_daily_target(balance or self.BALANCE_TIER_MID, target)
            except Exception:
                pass

        self._brain_initialized = True
        log.info("✅ Brain V3 initialisé avec succès")


    # ─── Builders des composants (extraits de _initialize_components) ─────────

    def _build_risk_manager(self):
        """Construit le RiskManager avec les tailles de position par classe d'actif."""
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

        # Surcharge possible via .env.
        env_min_pos = os.getenv("MIN_POSITION_SIZE")
        env_max_pos = os.getenv("MAX_POSITION_SIZE")
        actual_min_pos = float(env_min_pos) if env_min_pos else default_min_pos
        actual_max_pos = float(env_max_pos) if env_max_pos else default_max_pos

        max_pos_key = f"MAX_OPEN_POSITIONS_{self.active_broker_type.upper()}"
        env_max_pos_broker = os.getenv(max_pos_key)
        if env_max_pos_broker:
            try:
                actual_max_open_positions = int(env_max_pos_broker)
                log.info(f"Nombre maximum de positions spécifique au broker ({max_pos_key}) : {actual_max_open_positions}")
            except ValueError:
                actual_max_open_positions = MAX_OPEN_POSITIONS
        else:
            actual_max_open_positions = MAX_OPEN_POSITIONS

        return RiskManager({
            'RISK_PCT': self.adaptive_risk_pct,
            'MAX_DAILY_LOSS_PCT': MAX_DAILY_LOSS_PCT,
            'MAX_MONTHLY_LOSS_PCT': MAX_MONTHLY_LOSS_PCT,
            'MAX_OPEN_POSITIONS': actual_max_open_positions,
            'KELLY_FRACTION': KELLY_FRACTION,
            'MIN_TRADES_FOR_KELLY': MIN_TRADES_FOR_KELLY,
            'SL_ATR_MULT': SL_ATR_MULT,
            'TP_ATR_MULT': TP_ATR_MULT,
            'TRAIL_ATR_MULT': TRAIL_ATR_MULT,
            'TRAIL_ACTIVATE_ATR_MULT': TRAIL_ACTIVATE_ATR_MULT,
            'BE_ATR_MULT': BE_ATR_MULT,
            'BE_DYN_RR': BE_DYN_RR,
            'BE_DYN_RR_RATIO': BE_DYN_RR_RATIO,
            'MIN_POSITION_SIZE': actual_min_pos,
            'MAX_POSITION_SIZE': actual_max_pos,
            'COOLDOWN_SECONDS': COOLDOWN_SECONDS,
            'MAX_DAILY_LOSS_AMOUNT': MAX_DAILY_LOSS_AMOUNT,
            'DRAWDOWN_THRESH_1': DRAWDOWN_THRESH_1,
            'DRAWDOWN_THRESH_2': DRAWDOWN_THRESH_2,
            'DRAWDOWN_REDUCE_5PCT': DRAWDOWN_REDUCE_5PCT,
            'DRAWDOWN_REDUCE_10PCT': DRAWDOWN_REDUCE_10PCT,
        })

    def _build_technical_indicators(self):
        """Construit le calculateur d'indicateurs techniques."""
        return TechnicalIndicators({
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

    def _build_strategy(self, active_broker_type: str):
        """Construit la TradingStrategy avec les paramètres par classe d'actif."""
        # Ajuster les commissions et slippage selon le broker actif pour éviter de brider le R:R
        actual_commission = COMMISSION_PCT
        actual_slippage = SLIPPAGE_PCT
        if active_broker_type == "alpaca":
            actual_commission = 0.0  # Commission zéro sur Alpaca US Stocks/ETFs
        elif active_broker_type == "binance":
            actual_commission = 0.04  # Commission moyenne Binance Futures (0.02% maker, 0.04% taker)

        return TradingStrategy({
            'SCORE_MIN': self.adaptive_score_min,
            'RISK_PCT': self.adaptive_risk_pct,
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
            # Filtres crypto
            'CRYPTO_BLACKLIST': CRYPTO_BLACKLIST,
            'CRYPTO_SCORE_MIN': CRYPTO_SCORE_MIN,
            'CRYPTO_BUY_BLOCK_BTC_DROP': CRYPTO_BUY_BLOCK_BTC_DROP,
            'CRYPTO_BNB_VOLUME_FACTOR': CRYPTO_BNB_VOLUME_FACTOR,
            'COMMISSION_PCT': actual_commission,
            'SLIPPAGE_PCT': actual_slippage,
            # Paramètres par classe d'actifs
            'BROKER_TYPE': active_broker_type,
            # Crypto (Binance Futures)
            'EMA_FAST_CRYPTO': EMA_FAST_CRYPTO,
            'EMA_SLOW_CRYPTO': EMA_SLOW_CRYPTO,
            'ADX_TREND_CRYPTO': ADX_TREND_CRYPTO,
            'SCORE_MIN_CRYPTO': SCORE_MIN_CRYPTO,
            'SL_ATR_MULT_CRYPTO': SL_ATR_MULT_CRYPTO,
            'TP_ATR_MULT_CRYPTO': TP_ATR_MULT_CRYPTO,
            # Forex (MT5)
            'EMA_FAST_FOREX': EMA_FAST_FOREX,
            'EMA_SLOW_FOREX': EMA_SLOW_FOREX,
            'ADX_TREND_FOREX': ADX_TREND_FOREX,
            'SCORE_MIN_FOREX': SCORE_MIN_FOREX,
            'SL_ATR_MULT_FOREX': SL_ATR_MULT_FOREX,
            'TP_ATR_MULT_FOREX': TP_ATR_MULT_FOREX,
            'FOREX_NEWS_AVOID_MINUTES': FOREX_NEWS_AVOID_MINUTES,
            # ETF/Stocks (Alpaca)
            'EMA_FAST_STOCK': EMA_FAST_STOCK,
            'EMA_SLOW_STOCK': EMA_SLOW_STOCK,
            'ADX_TREND_STOCK': ADX_TREND_STOCK,
            'SCORE_MIN_STOCK': SCORE_MIN_STOCK,
            'SL_ATR_MULT_STOCK': SL_ATR_MULT_STOCK,
            'TP_ATR_MULT_STOCK': TP_ATR_MULT_STOCK,
            'ALLOW_SHORT_STOCK': ALLOW_SHORT_STOCK,
        }, indicators=self.technical_indicators)

    def _build_news_manager(self):
        """Construit le gestionnaire de nouvelles."""
        return NewsManager({
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

            if self.active_broker_type != active_broker_type:
                log.info(f"Le type de broker a changé de {self.active_broker_type} à {active_broker_type}. Réinitialisation du StateManager...")
                self.active_broker_type = active_broker_type
                from superbot.state import StateManager
                state_file = os.path.join(root_dir, 'superbot', 'logs', f'state_{self.active_broker_type}.json')
                self.state_manager = StateManager(filepath=state_file, ttl_hours=24)
                self.state_manager.load_state()
                self.failed_execution_cooldowns = self.state_manager.failed_execution_cooldowns
                self.blocked_symbols = self.state_manager.blocked_symbols
                self.session_pnl_by_symbol = self.state_manager.session_pnl_by_symbol
                self.consecutive_losses = self.state_manager.consecutive_losses
                self._adaptation_counter = self.state_manager.adaptation_counter

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
            broker_type = active_broker_type  # "binance", "alpaca", "mt5"
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

            # 🪙 V3 : Intégration crypto MT5 (Fusion Markets CFD)
            # Si broker=MT5 et MT5_CRYPTO_ENABLED=true, ajouter les paires crypto disponibles
            if (active_broker_type == "mt5" and
                    MT5_CRYPTO_ENABLED and
                    hasattr(self.broker, 'get_crypto_instruments')):
                try:
                    crypto_instruments = self.broker.get_crypto_instruments()
                    if crypto_instruments:
                        # Ajouter uniquement les crypto pas déjà dans la liste
                        existing = set(self.instruments)
                        new_crypto = [s for s in crypto_instruments if s not in existing]
                        self.instruments.extend(new_crypto)
                        log.info(
                            f"🪙 Crypto MT5 ajoutée à la liste des instruments : {new_crypto}\n"
                            f"   Total instruments : {self.instruments}"
                        )
                    else:
                        log.info("🪙 MT5_CRYPTO_ENABLED=true mais aucun symbole crypto disponible sur ce compte Fusion Markets")
                except Exception as e:
                    log.warning(f"Impossible de charger les instruments crypto MT5 : {e}")

            # Filtre multi-devises : ne rejeter les paires croisées que sur Binance
            # (MT5 convertit nativement le PnL des croisées).
            supported_instruments = []
            for symbol in self.instruments:
                normalized = symbol.upper().replace("/", "")
                # Pour Alpaca, pas de concept de paires de devises croisées (ce sont des actions/ETFs cotés en USD)
                if active_broker_type == "alpaca":
                    supported_instruments.append(symbol)
                # MT5 gère nativement les paires croisées — les accepter toutes
                elif active_broker_type == "mt5":
                    supported_instruments.append(symbol)
                # Si le symbole finit par USD (ou USDT, USDC, BUSD) ou commence par USD, on l'accepte
                elif normalized.endswith("USD") or normalized.endswith("USDT") or normalized.endswith("USDC") or normalized.endswith("BUSD") or normalized.startswith("USD"):
                    supported_instruments.append(symbol)
                else:
                    log.warning(f"🚨 PAIRE CROISÉE DÉTECTÉE ({symbol}) : La conversion PnL automatique sans USD comme devise de base ou de cotation n'est pas supportée. Actif désactivé.")
            self.instruments = supported_instruments

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
            self.risk_manager = self._build_risk_manager()
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

            # 3. Créer le calculateur d'indicateurs techniques
            self.technical_indicators = self._build_technical_indicators()
            log.info("Calculateur d'indicateurs techniques initialisé")

            # 4. Créer la stratégie de trading
            self.strategy = self._build_strategy(active_broker_type)
            log.info("Stratégie de trading initialisée")
            # Exposer le config au niveau bot pour les filtres de l'executor
            self.config = self.strategy.config

            # Lier la source unique de vérité aux composants actifs : toute
            # écriture ultérieure sur adaptive_risk_pct / adaptive_score_min
            # se propage automatiquement.
            self.runtime_config.bind(self.risk_manager, self.strategy)

            # 5. Créer le gestionnaire de nouvelles
            self.news_manager = self._build_news_manager()
            log.info("Gestionnaire de nouvelles initialisé")

            # Initialiser Prometheus Exporter
            try:
                from superbot.telemetry import PrometheusExporter
                # Calculer un port de métriques unique pour éviter les conflits en multi-instances
                dash_port = int(os.environ.get("DASHBOARD_PORT", 5000))
                prom_port = int(os.getenv("PROMETHEUS_PORT", str(dash_port + 3000)))
                self.prometheus = PrometheusExporter(port=prom_port)
                self.prometheus.start()
            except Exception as e:
                self.prometheus = None
                log.warning(f"Impossible d'initialiser Prometheus Exporter : {e}")

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

            # 7. Initialiser les agents de supervision
            try:
                from superbot.monitoring.bug_watchdog import BugWatchdog
                from superbot.config import BUG_WATCHDOG_INTERVAL, BUG_WATCHDOG_MAX_LATENCY, BUG_WATCHDOG_ENABLED
                if BUG_WATCHDOG_ENABLED:
                    self.bug_watchdog = BugWatchdog(self, interval=BUG_WATCHDOG_INTERVAL, max_latency=BUG_WATCHDOG_MAX_LATENCY)
                    log.info("Bug Watchdog initialisé")
            except Exception as e:
                log.warning(f"Impossible d'initialiser Bug Watchdog : {e}")

            try:
                from superbot.risk.modules.profit_circuit_breaker import ProfitCircuitBreaker
                self.profit_circuit_breaker = ProfitCircuitBreaker(self)
                log.info("Trailing Profit Circuit Breaker initialisé")
            except Exception as e:
                log.warning(f"Impossible d'initialiser Trailing Profit Circuit Breaker : {e}")

            log.info("Tous les composants ont été initialisés avec succès")

        except Exception as e:
            log.error(f"Erreur lors de l'initialisation des composants : {e}")
            log.error(traceback.format_exc())
            raise

    def _tsmom_cycle(self):
        """Mode TSMOM : allocation mensuelle à la place de la boucle intraday.

        Quand TSMOM_ENABLED=true, la boucle principale appelle cette méthode au
        lieu de scanner les symboles en intraday. Elle :
          1. récupère les clôtures QUOTIDIENNES des actifs TSMOM du broker actif ;
          2. calcule l'allocation cible (poids) via superbot.strategy.tsmom ;
          3. logue la cible une fois par jour ;
          4. au changement de mois, rapproche les positions de la cible :
             ordres market si TSMOM_PLACE_ORDERS=true, sinon dry-run (log seul).

        Un seul broker à la fois : alpaca→SPY, mt5→XAUUSD, binance→BTC/USDT.
        sl/tp = 0 signifie « pas de stop » (hold mensuel) — comportement à
        valider par broker avant tout placement réel.
        """
        import pandas as pd
        from datetime import datetime, timezone
        import superbot.config as cfg
        from superbot.strategy import tsmom

        broker_map = self.TSMOM_BROKER_SYMBOLS.get(self.active_broker_type.lower(), {})
        if not broker_map:
            log.info("[TSMOM] Aucun actif pour le broker %s — allocation sautée.", self.active_broker_type)
            return

        now = datetime.now(timezone.utc)
        day_key = now.date()
        # Throttle : le cycle tourne toutes les ~15s mais la stratégie est
        # mensuelle ; on ne refait le travail (fetch + allocation) qu'une fois/jour.
        if getattr(self, "_tsmom_last_log_day", None) == day_key:
            return
        self._tsmom_last_log_day = day_key
        month_key = (now.year, now.month)

        # 1. Clôtures quotidiennes des actifs de l'univers du broker
        prices = {}
        for uni_sym, broker_sym in broker_map.items():
            if uni_sym not in self.TSMOM_UNIVERSE:
                continue
            try:
                df = self.broker.fetch_candles(broker_sym, "1d", limit=400)
                if df is None or df.empty or "close" not in df.columns:
                    log.warning("[TSMOM] Clôtures quotidiennes indisponibles pour %s", broker_sym)
                    continue
                # Le dashboard utilise la dernière série OHLC disponible pour
                # alimenter le graphique. TSMOM ne doit pas laisser ce cache vide
                # simplement parce qu'il ne passe qu'une fois par jour.
                with self._lock:
                    self.market_data[broker_sym] = df.copy()
                closes = df["close"].astype(float)
                closes.index = pd.to_datetime(closes.index, utc=True)
                prices[uni_sym] = closes
            except Exception as e:
                log.warning("[TSMOM] Erreur récupération %s : %s", broker_sym, e)

        if not prices:
            return

        # 2. Allocation cible (signal « L-1 » + vol ciblée, sans look-ahead)
        cfg_dict = {k: v for k, v in vars(cfg).items() if k.startswith("TSMOM_")}
        alloc = tsmom.compute_allocations(cfg_dict, prices)
        if alloc.empty:
            log.info("[TSMOM] Allocation non calculable (données insuffisantes).")
            return

        # 3. Log quotidien de la cible (une fois/jour via le throttle ci-dessus)
        targets = ", ".join(f"{r.symbol}={r.weight:+.2f}" for _, r in alloc.iterrows())
        log.info("[TSMOM] Allocation cible du jour : %s", targets)

        # 4. Rebalancement uniquement au changement de mois
        if getattr(self, "_tsmom_last_month", None) == month_key:
            return
        self._tsmom_last_month = month_key

        # 5. Équité réelle (sinon dry-run forcé)
        equity = 0.0
        try:
            acc = self.broker.get_account_summary()
            if acc:
                equity = float(acc.get("equity") or acc.get("balance") or 0.0)
        except Exception:
            equity = 0.0
        if equity <= 0.0:
            try:
                equity = float(self.broker.get_balance())
            except Exception:
                equity = 0.0

        place_orders = bool(self.TSMOM_PLACE_ORDERS) and equity > 0.0
        if self.TSMOM_PLACE_ORDERS and equity <= 0.0:
            log.warning("[TSMOM] Équité indisponible — rebalancement en dry-run.")

        for _, row in alloc.iterrows():
            uni_sym = str(row["symbol"])
            broker_sym = broker_map.get(uni_sym)
            if not broker_sym:
                continue
            target_weight = float(row["weight"])
            try:
                price = float(self.broker.get_current_price(broker_sym))
            except Exception:
                price = float(prices[uni_sym].iloc[-1]) if uni_sym in prices else 0.0
            if price <= 0.0:
                log.warning("[TSMOM] Prix indisponible pour %s — ignoré.", broker_sym)
                continue

            target_notional = target_weight * equity if equity > 0.0 else 0.0
            target_signed_size = target_notional / price  # >0 long, <0 short

            # Garde-fou « compte insuffisant » : ne jamais produire un ordre
            # impossible à exécuter. Le broker impose une taille minimale
            # (ex. XAUUSD = 1 once = 0.01 lot). Si la cible entière est sous ce
            # minimum, le compte ne peut pas porter ce symbole → on le saute.
            min_order_size = None
            try:
                min_order_size = self.broker.get_min_order_size(broker_sym)
            except Exception:
                min_order_size = None
            if min_order_size and min_order_size > 0 and abs(target_signed_size) > 0:
                if abs(target_signed_size) < min_order_size:
                    required_equity = (
                        min_order_size * price / abs(target_weight)
                        if target_weight else float("inf")
                    )
                    log.info(
                        "[TSMOM] %s : cible %.6f < minimum broker %.4f → compte "
                        "insuffisant (requis ≈ %.0f %s). Symbole ignoré.",
                        broker_sym, target_signed_size, min_order_size,
                        required_equity, "USD",
                    )
                    continue

            pos = self.positions.get(broker_sym) or {}
            cur_size = float(pos.get("size", 0.0) or 0.0)
            cur_signed = -cur_size if str(pos.get("side", "LONG")).upper() == "SHORT" else cur_size
            delta = target_signed_size - cur_signed

            min_notional = equity * 0.01 if equity > 0.0 else 0.0
            if min_notional > 0.0 and abs(delta) * price < min_notional:
                log.info("[TSMOM] %s : delta %.6f < seuil 1%% — position conservée.", broker_sym, delta)
                continue

            side = "buy" if delta > 0 else "sell"
            amount = abs(delta)
            if place_orders:
                try:
                    ok = self.broker.place_order(
                        broker_sym, side, amount, sl=0.0, tp=0.0, comment="TSMOM rebalance"
                    )
                    log.info("[TSMOM] Ordre %s %s %.6f → %s", side, broker_sym, amount,
                             "OK" if ok else "ÉCHEC")
                except Exception as e:
                    log.error("[TSMOM] Échec ordre %s %s : %s", side, broker_sym, e)
            else:
                log.info("[TSMOM] DRY-RUN : %s %s %.6f (poids cible %+.2f) — TSMOM_PLACE_ORDERS=false",
                         side.upper(), broker_sym, amount, target_weight)

    def _sync_positions_with_broker(self):
        """
        Synchronise l'état interne des positions du bot et du RiskManager avec le broker.
        """
        from superbot.components.position_syncer import sync_positions_with_broker
        sync_positions_with_broker(self)

    def start(self):
        """Démarre le bot de trading."""
        if self.running:
            log.warning("️  Le bot est déjà en cours d'exécution")
            return

        # 1.1 Garde-fou Live Trading
        is_testnet = getattr(self.broker, 'testnet', True) or getattr(self.broker, 'account_type', 'PAPER') == 'PAPER'
        if not is_testnet and not ALLOW_LIVE_TRADING:
            log.error("🚨 TRADING LIVE DÉTECTÉ MAIS NON AUTORISÉ DANS .ENV (ALLOW_LIVE_TRADING=true manquant). CRASH PRÉVENTIF.")
            sys.exit(1)

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

        # Démarrer le Bug Watchdog
        if getattr(self, 'bug_watchdog', None):
            try:
                self.bug_watchdog.start()
            except Exception as e:
                log.error(f"Erreur lors du démarrage du Bug Watchdog : {e}")

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

        # Sauvegarder l'état avant l'arrêt
        self._save_cooldowns()
        log.info("États de session sauvegardés avec succès.")

        # Arrêter le gestionnaire de nouvelles
        try:
            self.news_manager.stop()
            log.info("Gestionnaire de nouvelles arrêté")
        except Exception as e:
            log.error(f"Erreur lors de l'arrêt du gestionnaire de nouvelles : {e}")

        # Arrêter le Bug Watchdog
        if getattr(self, 'bug_watchdog', None):
            try:
                self.bug_watchdog.stop()
            except Exception as e:
                log.error(f"Erreur lors de l'arrêt du Bug Watchdog : {e}")

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

        # Fermer les connexions du broker (MT5 garde une connexion COM ouverte sinon).
        try:
            if hasattr(self.broker, 'disconnect'):
                self.broker.disconnect()
                log.info("Connexions broker fermées")
            elif hasattr(self.broker, 'close'):
                self.broker.close()
                log.info("Connexions broker fermées")
            else:
                log.info("Connexions broker fermées (pas de méthode explicite)")
        except Exception as e:
            log.error(f"Erreur lors de la fermeture des connexions broker : {e}")

        # 🧠 V3 : Arrêter les modules Brain
        if getattr(self, 'report_generator', None):
            try:
                self.report_generator.stop()
                log.info("📝 ReportGenerator arrêté")
            except Exception as e:
                log.debug(f"Erreur arrêt ReportGenerator: {e}")

        if getattr(self, 'knowledge_feeder', None):
            try:
                self.knowledge_feeder.stop()
                log.info("KnowledgeFeeder arrêté")
            except Exception as e:
                log.debug(f"Erreur arrêt KnowledgeFeeder: {e}")

        # Flusher le modèle ML avant la fermeture DB (sinon les derniers apprentissages sont perdus).
        if getattr(self, 'online_learner', None):
            try:
                self.online_learner.flush()
                log.info("🧠 OnlineLearner sauvegardé à l'arrêt")
            except Exception as e:
                log.debug(f"Erreur flush OnlineLearner: {e}")

        if getattr(self, 'db', None):
            try:
                self.db.close()
                log.info("🗄️ DB SQLite fermée")
            except Exception as e:
                log.debug(f"Erreur fermeture DB: {e}")

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
        from superbot.components.cycle_runner import run_main_loop
        run_main_loop(self)

    def _process_symbol(self, symbol: str):
        """
        Traite un symbole spécifique : récupère les données, analyse, génère des signaux, exécute des trades.

        Args:
            symbol: Symbole à traiter (ex: BTC/USDT)
        """
        try:
            # Mesurer le temps de traitement total pour profiling
            symbol_start_time = time.time()

            # 1. Récupérer les données de marché récentes
            fetch_start = time.time()
            df = self._fetch_market_data(symbol)
            fetch_time = time.time() - fetch_start
            if df is None or len(df) < 50:  # Minimum de données nécessaires
                log.debug(f"Données insuffisantes pour {symbol} : {len(df) if df is not None else 0} barres")
                return

            # Vérifier si nous avons réellement de nouvelles données depuis le dernier traitement
            # Pour éviter de retraiter les mêmes données inutilement
            df_hash = hash(df.iloc[-1].to_string()) if len(df) > 0 else None
            last_hash = getattr(self, '_last_data_hash', {}).get(symbol)
            if df_hash == last_hash and len(df) > 0:
                # Même dernière barre, on peut skip le traitement sauf si on a besoin de mettre à jour les positions
                # Mais on continue quand même pour la gestion des risques des positions ouvertes
                pass  # Continuer pour la gestion de risque
            else:
                # Nouveaux données, mettre à jour le hash
                if not hasattr(self, '_last_data_hash'):
                    self._last_data_hash = {}
                self._last_data_hash[symbol] = df_hash

            # 2. Calculer les indicateurs techniques (avec cache de cycle)
            indicators_start = time.time()
            with self._lock:
                if not hasattr(self, '_indicators_cache'):
                    self._indicators_cache = {}
                if symbol in self._indicators_cache:
                    df_with_indicators = self._indicators_cache[symbol]
                else:
                    df_with_indicators = self.technical_indicators.calculate_all_indicators(df.copy())
                    self._indicators_cache[symbol] = df_with_indicators
                self.market_data[symbol] = df_with_indicators
            indicators_time = time.time() - indicators_start

            # === GESTION DE RISQUE CONTINUE DES POSITIONS OUVERTES ===
            risk_start = time.time()
            self._update_active_position_risk(symbol, df_with_indicators)
            risk_time = time.time() - risk_start

            # 🧠 V3 : Vérification de session (SessionManager)
            if self.session_manager:
                try:
                    self.session_manager.tick()
                    can_trade, reason = self.session_manager.can_trade_symbol(symbol)
                    if not can_trade:
                        log.debug(f"Session filter: {symbol} skipé — {reason}")
                        return
                except Exception as _se:
                    log.debug(f"SessionManager tick error: {_se}")

            # ⚫ V3 : Vérification PerformanceLearner (blocage pertes consécutives)
            if self.performance_learner:
                try:
                    if self.performance_learner.is_symbol_blocked(symbol):
                        log.info(f"🚫 {symbol} bloqué par PerformanceLearner (3+ pertes consécutives)")
                        return
                except Exception as _pe:
                    log.debug(f"PerformanceLearner check error: {_pe}")

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
                market_is_open = True
                
                # Vérification API officielle Alpaca
                if hasattr(self.broker, '_api') and hasattr(self.broker._api, 'get_clock'):
                    try:
                        clock = self.broker._api.get_clock()
                        market_is_open = clock.is_open
                    except Exception as e:
                        log.warning(f"Erreur vérification horloge Alpaca : {e}")
                        market_is_open = False # Par précaution
                        
                if not market_is_open:
                    log.debug(f"Marché US fermé (Alpaca API) : skip {symbol}")
                    return

            # 3. Analyser le marché et générer un signal de trading (avec cache de cycle)
            strategy_start = time.time()
            with self._lock:
                if not hasattr(self, '_strategy_cache'):
                    self._strategy_cache = {}
                if symbol in self._strategy_cache:
                    signal_data = self._strategy_cache[symbol]
                else:
                    signal_data = None
            if signal_data is None:
                # Passer le vrai solde et le win rate réel au modèle.
                _real_balance = getattr(self, '_cached_balance', 0.0)
                _real_win_rate = None
                if self.risk_manager and len(self.risk_manager.trade_history) >= self.risk_manager.MIN_TRADES_FOR_KELLY:
                    closed = [t for t in self.risk_manager.trade_history if t.get('target') is not None]
                    if closed:
                        _real_win_rate = sum(1 for t in closed if t.get('target') == 1) / len(closed)

                # Calculer la variation BTC 24h depuis les données de marché en cache
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
                signal_data['symbol'] = symbol

                # 🧠 V3 : Enrichir le signal avec le régime Brain + StrategyEngine
                try:
                    if self.regime_detector:
                        asset_class = 'crypto' if 'BTC' in symbol or 'ETH' in symbol or 'BNB' in symbol else 'forex'
                        regime_result = self.regime_detector.detect(
                            df_with_indicators, symbol=symbol, asset_class=asset_class, store_in_db=False
                        )
                        # Le brain V3 retourne un format ('high_volatility'/'ranging') différent du
                        # label HMM brut attendu par stop_manager/position_sizer. On le stocke donc
                        # séparément, sans écraser le hmm_label injecté par la stratégie.
                        signal_data['brain_regime'] = regime_result.regime
                        signal_data['market_regime'] = regime_result.regime
                        # hmm_label : ne mettre à jour que si non encore défini par la strategy
                        if 'hmm_label' not in signal_data or signal_data.get('hmm_label') in ('UNKNOWN', '', None):
                            signal_data['hmm_label'] = regime_result.regime
                        signal_data['regime_confidence'] = regime_result.confidence
                        signal_data['regime_risk_mult'] = self.regime_detector.get_risk_multiplier(regime_result.regime)

                    if self.strategy_engine and self.session_manager:
                        sess = self.session_manager.get_current_session()
                        regime = signal_data.get('market_regime', 'ranging')
                        asset_class = 'crypto' if 'BTC' in symbol or 'ETH' in symbol else 'forex'
                        best_strat, strat_conf = self.strategy_engine.select_best_strategy(
                            regime=regime,
                            session_name=sess.get('name', 'LONDON'),
                            asset_class=asset_class,
                            symbol=symbol,
                            adx_value=float(df_with_indicators.iloc[-1].get('adx', 0) or 0),
                        )
                        signal_data['strategy_used'] = best_strat
                        signal_data['strategy_confidence'] = strat_conf

                        # Ajuster le score_min selon le régime
                        if self.regime_detector:
                            score_adj = self.regime_detector.get_score_min_adjustment(regime)
                            base_score_min = signal_data.get('score_min', self.strategy.score_min)
                            signal_data['score_min'] = max(1, base_score_min + score_adj)

                        # Ajuster le score_min selon la session
                        if self.session_manager:
                            base_score_min = signal_data.get('score_min', self.strategy.score_min)
                            signal_data['score_min'] = self.session_manager.get_adapted_score_min(base_score_min)

                except Exception as _brain_e:
                    log.debug(f"Brain enrichment error ({symbol}): {_brain_e}")

                with self._lock:
                    self._strategy_cache[symbol] = signal_data
            strategy_time = time.time() - strategy_start

            # DEBUG: log signal details and pre-check news avoidance
            score_raw = signal_data['total_score']
            # Afficher le score_min effectif (par asset_type) plutôt que le global
            score_min = signal_data.get('score_min', self.strategy.score_min)
            rr = signal_data['rr_ratio']
            if getattr(self, 'news_manager', None):
                should_avoid, news_event = self.news_manager.should_avoid_trading_due_to_news(symbol)
            else:
                should_avoid, news_event = False, None
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
                # Exécuter le trade
                trade_start = time.time()
                self._execute_signal_trade(symbol, signal_data, df_with_indicators)
                trade_time = time.time() - trade_start
            else:
                log.info(
                    f"Scan {symbol} : {signal_data['market_regime']} | "
                    f"Score: {score_raw:.1f}/{score_min} | "
                    f"Pas de signal (Trigger L: {signal_data['trigger_long']}, S: {signal_data['trigger_short']}, R:R: {rr:.2f})"
                )

            # Log des temps de traitement pour profiling (en mode debug seulement)
            total_time = time.time() - symbol_start_time
            if log.isEnabledFor(logging.DEBUG):
                log.debug(
                    f"Profiling {symbol}: "
                    f"fetch={fetch_time:.3f}s, indicators={indicators_time:.3f}s, "
                    f"risk={risk_time:.3f}s, strategy={strategy_time:.3f}s, "
                    f"trade={trade_time if 'trade_time' in locals() else 0:.3f}s, "
                    f"total={total_time:.3f}s"
                )

        except Exception as e:
            log.error(f"Erreur inattendue dans _process_symbol pour {symbol} : {e}")
            log.debug(traceback.format_exc())

    def _update_active_position_risk(self, symbol: str, df_with_indicators):
        """
        Met à jour les trailing stops et break-evens pour les positions ouvertes.
        """
        # Snapshot thread-safe de l'existence de la position
        with self._lock:
            has_local_pos = symbol in self.positions
            has_risk_pos = self.risk_manager is not None and symbol in self.risk_manager.open_positions
        if not has_local_pos or not has_risk_pos:
            return

        current_price = df_with_indicators.iloc[-1]['close']
        atr_value = df_with_indicators.iloc[-1].get('atr', 0)

        # Mettre à jour l'ATR dans la position pour le risk manager (sous verrou interne).
        with self.risk_manager._history_lock:
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
            with self.risk_manager._history_lock:
                if symbol in self.risk_manager.open_positions:
                    self.risk_manager.open_positions[symbol]['take_profit'] = theoretical_tp
            with self._lock:
                if symbol in self.positions:
                    self.positions[symbol]['take_profit'] = theoretical_tp
            log.info(f"Recalcul du Take Profit théorique pour {symbol} : {theoretical_tp:.5f}")

        # Mettre à jour si le SL a changé de manière significative (Deadband > 0.2 ATR)
        significant_move = abs(new_sl - old_sl) > (atr_value * 0.2)
        should_update_broker = (significant_move and new_sl > 0) or (broker_sl == 0.0 and new_sl > 0) or (broker_tp == 0.0 and theoretical_tp > 0)

        if should_update_broker:
            log.info(f"Mise à jour SL/TP pour {symbol} chez le courtier (SL: {old_sl:.5f} -> {new_sl:.5f}, TP: {theoretical_tp:.5f})")
            success = self.broker.modify_sl_tp(symbol, new_sl, theoretical_tp)
            if success:
                # Mettre à jour notre dictionnaire local de suivi de position
                with self._lock:
                    if symbol in self.positions:
                        self.positions[symbol]['stop_loss'] = new_sl
                        self.positions[symbol]['take_profit'] = theoretical_tp

    def _execute_signal_trade(self, symbol: str, signal_data: dict, df_with_indicators):
        """
        Valide les filtres macro, calcule la taille de position de manière sécurisée et exécute l'ordre.
        """
        from superbot.components.signal_executor import execute_signal_trade
        execute_signal_trade(self, symbol, signal_data, df_with_indicators)

    def _save_cooldowns(self):
        """Sauvegarde les cooldowns d'exécution et l'état général (QW-4)"""
        if hasattr(self, 'state_manager'):
            day_start_bal = 0.0
            last_daily_reset_str = ""
            if self.risk_manager:
                day_start_bal = getattr(self.risk_manager, 'day_start_balance', 0.0)
                if getattr(self.risk_manager, 'last_daily_reset', None):
                    last_daily_reset_str = datetime.combine(self.risk_manager.last_daily_reset, datetime.min.time()).isoformat()
            
            with self._state_lock:
                self.state_manager.save_state(
                    self.failed_execution_cooldowns,
                    self.blocked_symbols,
                    self.session_pnl_by_symbol,
                    getattr(self, 'consecutive_losses', 0),
                    self._adaptation_counter,
                    is_paused=self.is_paused,
                    day_start_balance=day_start_bal,
                    last_daily_reset_str=last_daily_reset_str
                )

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
            # Exclure d'emblée les symboles en blacklist pour qu'ils ne polluent jamais la rotation
            crypto_blacklist = set(self.config.get('CRYPTO_BLACKLIST', []))
            scores = {}
            for symbol in self.instruments:
                # Exclure les symboles en blacklist AVANT de calculer leur score
                sym_clean = symbol.replace('/', '').upper()
                if any(b.replace('/', '').upper() == sym_clean for b in crypto_blacklist):
                    log.debug(f"[Rotation] {symbol} exclu de la rotation (blacklist)")
                    continue
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
                        signal = self.strategy.analyze_market(indicators, symbol=symbol)  # — fix: symbol manquant
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

            # Récupérer les actifs actuellement actifs — toujours purger les blacklistés
            current_active = [
                s for s in getattr(self, '_active_crypto_symbols', [])
                if s in scores  # scores ne contient déjà plus les blacklistés
            ]
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
        # Vérifier d'abord le cache du cycle de trading pour éviter des appels API doubles.
        # Accès sous verrou : _market_data_cache est partagé entre les workers du cycle.
        with self._lock:
            cache = getattr(self, '_market_data_cache', None)
            if cache is None:
                self._market_data_cache = {}
                cache = self._market_data_cache
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
            with self._lock:
                if not hasattr(self, '_market_data_cache'):
                    self._market_data_cache = {}
                self._market_data_cache[symbol] = df

            return df

        except Exception as e:
            log.error(f"Erreur lors de la récupération des données pour {symbol} : {e}")
            return None

    def _convert_pnl_to_account_currency(self, symbol: str, pnl: float, reference_price: float) -> float:
        """
        Convertit un PnL brut dans la devise de cotation vers la devise du compte (USD).
        """
        normalized = symbol.strip().upper().replace("/", "")
        
        # Paires dont la quote currency est le JPY, CAD, CHF, AUD, NZD et la base est USD
        # Le PnL brut calculé par le broker est dans la devise de cotation.
        # En divisant par reference_price (taux USD/XXX), on revient en USD.
        quote_currencies_to_divide = ["JPY", "CAD", "CHF", "AUD", "NZD"]
        
        if any(normalized.endswith(q) for q in quote_currencies_to_divide) and normalized.startswith("USD"):
            if reference_price > 0:
                converted = pnl / reference_price
                log.debug(f"Conversion PnL vers USD pour {symbol} : {pnl:.2f} / {reference_price:.3f} = {converted:.2f} USD")
                return converted
            else:
                log.warning(f"Prix de référence nul pour {symbol}, conversion vers USD impossible")
                return pnl
                
        # Pour toutes les autres paires (EURUSD, BTCUSDT, etc.), le PnL est déjà en USD
        return pnl

    def _update_position_tracking(self, symbol: str, side: str, size: float, entry_price: float,
                                   stop_loss: float = 0.0, take_profit: float = 0.0,
                                   market_regime: str = 'UNKNOWN', features: dict = None):
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
            features: Dictionnaire optionnel de caractéristiques (ML features)
        """
        position_side = "LONG" if side == "buy" else "SHORT"

        # Normaliser le symbole pour que bot.positions utilise le même nom que MT5
        # (évite les doublons du GhostCleaner et le pyramidage).
        if hasattr(self.broker, 'normalize_symbol'):
            symbol = self.broker.normalize_symbol(symbol)

        with self._lock:
            self.positions[symbol] = {
                'side': position_side,
                'size': size,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timestamp': datetime.now(timezone.utc),
                'status': 'open',
                # Régime de marché conservé pour être propagé à la clôture.
                'market_regime': market_regime,
                'features': features or {}
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
                    # Mettre à jour l'état local sous verrou : ce thread peut tourner
                    # en parallèle des workers du cycle et du sync.
                    with self._lock:
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

            # 🔒 Filtres de sécurité webhook (même pipeline que le trading automatique)

            # A. Vérifier si le bot est en pause
            if self.is_paused:
                return {"status": "skipped", "reason": "bot_paused"}

            # B. Vérifier les actifs bloqués
            if symbol in self.blocked_symbols:
                return {"status": "skipped", "reason": "symbol_blocked", "symbol": symbol}

            # C. Vérifier si une position est déjà ouverte (anti-pyramidage)
            if symbol in self.positions:
                return {"status": "skipped", "reason": "position_already_open", "symbol": symbol}

            # D. Vérifier le cooldown
            with self._state_lock:
                if symbol in self.failed_execution_cooldowns:
                    time_since = time.time() - self.failed_execution_cooldowns[symbol]
                    if time_since < 900:
                        return {"status": "skipped", "reason": "cooldown_active", "symbol": symbol}

            # E. Filtre session US (stocks/ETFs)
            if self.broker.get_asset_type() == "stock":
                market_is_open = True
                # 1) Horloge officielle Alpaca (autoritaire, gère DST + jours fériés)
                if hasattr(self.broker, '_api') and hasattr(self.broker._api, 'get_clock'):
                    try:
                        market_is_open = bool(self.broker._api.get_clock().is_open)
                    except Exception as e:
                        log.warning(f"Erreur horloge Alpaca (webhook) : {e}")
                        market_is_open = False
                else:
                    # 2) Fallback DST-aware + week-end (pas d'API dispo)
                    try:
                        import zoneinfo
                        et_tz = zoneinfo.ZoneInfo("America/New_York")
                        now_et = datetime.now(et_tz)
                        open_t = datetime.strptime("09:30", "%H:%M").time()
                        close_t = datetime.strptime("16:00", "%H:%M").time()
                        market_is_open = (now_et.weekday() < 5 and open_t <= now_et.time() <= close_t)
                    except Exception:
                        market_is_open = False
                if not market_is_open:
                    return {"status": "skipped", "reason": "outside_us_session", "symbol": symbol}

            # F. Bloquer les SHORTs sur ETF/Stocks si non autorisé
            if self.broker.get_asset_type() in ('stock', 'alpaca', 'equity'):
                if action == 'sell' and not ALLOW_SHORT_STOCK:
                    return {"status": "skipped", "reason": "short_blocked_stocks", "symbol": symbol}

            if getattr(self, 'news_manager', None):
                should_avoid, news_event = self.news_manager.should_avoid_trading_due_to_news(symbol)
            else:
                should_avoid, news_event = False, None
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

            # Vérifier les limites de risque globales (avec symbol pour check position existante)
            if not self.risk_manager._can_take_new_trade(account_balance, symbol=symbol):
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
                with self._state_lock:
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
                    'broker': self.active_broker_type
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

            # 🧠 V3: Collecte des données Brain
            brain_data = {}
            try:
                sm = getattr(self, 'session_manager', None)
                if sm:
                    progress = sm.get_daily_progress()
                    curr_session = sm.get_current_session()
                    brain_data['daily_progress'] = {
                        'achieved_eur': progress.get('achieved_eur', 0),
                        'target_eur': progress.get('target_eur', 200),
                        'achievement_pct': progress.get('achievement_pct', 0),
                    }
                    brain_data['session'] = {
                        'name': curr_session.get('name', ''),
                        'description': curr_session.get('description', ''),
                        'risk_mult': curr_session.get('risk_multiplier', 1.0),
                    }

                rd = getattr(self, 'regime_detector', None)
                if rd:
                    last_reg = None
                    if hasattr(rd, '_cache') and rd._cache:
                        last_reg = list(rd._cache.values())[-1]
                    elif hasattr(rd, '_last_regime'):
                        last_reg = rd._last_regime

                    if last_reg:
                        brain_data['regime'] = {
                            'regime': getattr(last_reg, 'regime', '—'),
                            'confidence': getattr(last_reg, 'confidence', 0),
                            'risk_mult': rd.get_risk_multiplier(getattr(last_reg, 'regime', '')) if hasattr(rd, 'get_risk_multiplier') else 1.0,
                        }

                se = getattr(self, 'strategy_engine', None)
                if se:
                    lb = se.get_strategy_leaderboard()[:1]
                    if lb:
                        top = lb[0]
                        brain_data['strategy'] = {
                            'name': top.get('strategy', ''),
                            'confidence': top.get('wr', 0),
                            'trades': top.get('trades', 0),
                        }

                pl = getattr(self, 'performance_learner', None)
                if pl:
                    brain_data['learner_params'] = pl.get_current_params()
                    brain_data['blocked_symbols'] = [
                        {'symbol': sym, 'reason': '3 pertes consécutives'}
                        for sym in getattr(pl, '_blocked_symbols', set())
                    ]
                    brain_data['recent_decisions'] = getattr(pl, '_decisions_log', [])

                kf_inst = getattr(self, 'knowledge_feeder', None)
                if kf_inst:
                    kf_sentiment = kf_inst.get_current_sentiment()
                    brain_data['knowledge_feeder'] = {
                        'items_today': getattr(kf_inst, '_items_today', 0),
                        'last_refresh': getattr(kf_inst, '_last_refresh_time', None),
                        'is_running': getattr(kf_inst, '_running', False),
                        'fear_greed_index': kf_sentiment.get('fear_greed_index'),
                        'overall_sentiment': kf_sentiment.get('overall_sentiment', 'neutral'),
                    }
            except Exception as e:
                log.debug(f"Erreur collecte brain data dans _update_dashboard: {e}")

            dashboard_data['brain'] = brain_data

            # Mettre à jour le dashboard
            self.dashboard.update_data(dashboard_data)

        except Exception as e:
            log.debug(f"Erreur lors de la mise à jour du dashboard : {e}")

    def _get_recent_win_rate(self) -> float:
        from superbot.components.adaptive_params import get_recent_win_rate
        return get_recent_win_rate(self)

    def _run_walk_forward_calibration(self):
        """
        Déclenche l'optimisation Walk-Forward périodique (Phase 3.2).
        Recalibre score_min, RSI_OB et ADX_TREND sur l'historique des 90 derniers jours.
        """
        if not hasattr(self, 'walk_forward_optimizer') or self.walk_forward_optimizer is None:
            return

        # 30 jours en secondes = 30 * 24 * 3600 = 2 592 000
        interval = float(os.getenv("WALK_FORWARD_INTERVAL_SECONDS", 2592000))
        
        now = time.time()
        if now - self.walk_forward_optimizer.last_calibration_time < interval:
            return

        log.info("Recalibration Walk-Forward périodique déclenchée.")
        # Filtrer les trades fermés sur les 90 derniers jours
        import pandas as pd
        cutoff_date = datetime.now() - timedelta(days=90)
        recent_trades = []
        for t in self.risk_manager.trade_history:
            if t.get('status') == 'closed' and t.get('timestamp'):
                try:
                    import dateutil.parser
                    t_time = dateutil.parser.parse(str(t['timestamp']))
                    if t_time.tzinfo is not None:
                        t_time = t_time.replace(tzinfo=None)
                    if t_time >= cutoff_date:
                        recent_trades.append(t)
                except Exception:
                    continue

        if not recent_trades:
            log.warning("Aucun trade récent dans les 90 derniers jours pour calibrer le Walk-Forward.")
            # Mettre à jour le time pour ne pas spammer
            self.walk_forward_optimizer.last_calibration_time = now
            return

        df = pd.DataFrame(recent_trades)
        
        def run_async():
            try:
                best_params = self.walk_forward_optimizer.optimize(df)
                self.strategy.config['SCORE_MIN'] = best_params['SCORE_MIN']
                self.strategy.config['RSI_OB'] = best_params['RSI_OB']
                self.strategy.config['ADX_TREND'] = best_params['ADX_TREND']
                self.strategy.score_min = best_params['SCORE_MIN']
                self.adaptive_score_min = best_params['SCORE_MIN']
                log.info(f"Paramètres de stratégie mis à jour par Walk-Forward : {best_params}")
            except Exception as e:
                log.error(f"Erreur lors de l'optimisation Walk-Forward : {e}")

        t = threading.Thread(target=run_async, daemon=True)
        t.start()

    def _update_adaptive_parameters(self):
        from superbot.components.adaptive_params import update_adaptive_parameters
        update_adaptive_parameters(self)

    def _apply_adaptive_params(self):
        """Pousse les paramètres adaptatifs (cloud, walk-forward, adaptation) vers les composants actifs."""
        rc = getattr(self, 'runtime_config', None)
        if rc is not None:
            rc.apply()
            return
        # Fallback pour les mocks légers de test (sans runtime_config).
        if self.risk_manager:
            self.risk_manager.RISK_PCT = self.adaptive_risk_pct
        if self.strategy:
            self.strategy.score_min = self.adaptive_score_min
            self.strategy.risk_per_trade = self.adaptive_risk_pct

    def _detect_model_drift(self):
        from superbot.components.drift_detector import detect_model_drift
        detect_model_drift(self)

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