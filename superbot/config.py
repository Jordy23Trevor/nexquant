"""
╔═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════⌀
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# =============================================================================
# BROKER CONFIGURATION
# =============================================================================
BROKER_TYPE = os.getenv("BROKER_TYPE", "mt5").lower()  # mt5 (prioritaire V3), binance, alpaca
ALLOW_LIVE_TRADING = os.getenv("ALLOW_LIVE_TRADING", "false").lower() == "true"

# =============================================================================
# METATRADER 5 (MT5) CONFIGURATION (associated with Fusion Markets)
# =============================================================================
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "FusionMarkets-Demo")
MT5_PATH = os.getenv("MT5_PATH", "")  # Path to terminal64.exe (optional)

# =============================================================================
# BINANCE FUTURES CONFIGURATION
# =============================================================================
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
LEVERAGE = int(os.getenv("LEVERAGE", "5"))

# =============================================================================
# ALPACA MARKETS CONFIGURATION (for ETFs/US stocks)
# =============================================================================
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET", "")
_alpaca_use_paper = os.getenv("ALPACA_USE_PAPER", "true").lower() == "true"
_default_alpaca_url = "https://paper-api.alpaca.markets" if _alpaca_use_paper else "https://api.alpaca.markets"
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", _default_alpaca_url)
ALPACA_API_VERSION = os.getenv("ALPACA_API_VERSION", "v2")

# =============================================================================
# FOREX DATA PROVIDERS (utilisé par MT5)
# =============================================================================
FOREX_DEFAULT_LEVERAGE = int(os.getenv("FOREX_DEFAULT_LEVERAGE", "30"))  # Typical forex leverage
FOREX_MARGIN_CALL_LEVEL = float(os.getenv("FOREX_MARGIN_CALL_LEVEL", "0.5"))  # 50% margin used triggers call
FOREX_STOP_OUT_LEVEL = float(os.getenv("FOREX_STOP_OUT_LEVEL", "0.2"))  # 20% margin used triggers stop out
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
FOREX_DATA_PROVIDER = os.getenv("FOREX_DATA_PROVIDER", "twelvedata")

# =============================================================================
# TRADING INSTRUMENTS & TIMEFRAMES
# =============================================================================
# Instruments to trade - format depends on broker
# For Binance: "BTC/USDT", "ETH/USDT"
# For Alpaca: "SPY", "QQQ", "AAPL"
# For MT5: "EURUSD", "GBPUSD", "USDJPY"
INSTRUMENTS_STR = os.getenv("INSTRUMENTS", "BTC/USDT")
INSTRUMENTS = [s.strip() for s in INSTRUMENTS_STR.split(",")]

# ─────────────────────────────────────────────────────────────────────────────
# 📊 RAPPORT CRYPTO (2026-07-02) — Corrections appliquées
# ─────────────────────────────────────────────────────────────────────────────
# P0-2 : SOL/USDT retiré (0% WR, −484 USD sur 4 trades) jusqu'à correction
#         du filtre dominance BTC. Ajouter dans CRYPTO_BLACKLIST pour le bloquer
#         même s'il est présent dans INSTRUMENTS.
# P2-1 : ADA/USDT (20% WR, −51 USD) remplacé par XRP/USDT (corrélation BTC < ADA)
CRYPTO_BLACKLIST_STR = os.getenv("CRYPTO_BLACKLIST", "SOL/USDT")
CRYPTO_BLACKLIST: list = [s.strip() for s in CRYPTO_BLACKLIST_STR.split(",") if s.strip()]

# P1-2 : Score minimum plus strict pour les paires crypto en période de faible ADX.
#         Default = 7 (vs 6 global). Le bot générait trop de signaux BNB en range (38% WR).
CRYPTO_SCORE_MIN = int(os.getenv("CRYPTO_SCORE_MIN", "7"))

# P1-1 : Si BTC a baissé de > X% sur 24h, bloquer TOUS les signaux BUY sur les altcoins.
#         Cible les crash copycat observés sur SOL/ADA/BNB les 29-30 juin 2026.
CRYPTO_BUY_BLOCK_BTC_DROP = float(os.getenv("CRYPTO_BUY_BLOCK_BTC_DROP", "2.0"))

# P2-1 : Volume minimum BNB/USDT — 150% de la moyenne mobile 20 périodes.
#         Réduit l'overtrading en période de range directionnel faible.
CRYPTO_BNB_VOLUME_FACTOR = float(os.getenv("CRYPTO_BNB_VOLUME_FACTOR", "1.5"))

# =============================================================================
# TRANSACTION COSTS (Phase 2 - Realism Modeling)
# =============================================================================
COMMISSION_PCT = float(os.getenv("COMMISSION_PCT", "0.1"))
SLIPPAGE_PCT = float(os.getenv("SLIPPAGE_PCT", "0.05"))

# Timeframes for analysis
GRANULARITY = os.getenv("GRANULARITY", "1h")  # Main trading timeframe
HTF_GRANULARITY = os.getenv("HTF_GRANULARITY", "4h")  # Higher timeframe for trend confirmation
D1_GRANULARITY = os.getenv("D1_GRANULARITY", "1d")  # Daily timeframe
W1_GRANULARITY = os.getenv("W1_GRANULARITY", "1w")  # Weekly timeframe (Elder's triple screen)
N_CANDLES = int(os.getenv("N_CANDLES", "500"))  # Number of candles to fetch

# =============================================================================
# TECHNICAL INDICATOR PARAMETERS
# =============================================================================
# Moving Averages (paramètres globaux — utilisés si aucun paramètre spécifique n'est défini)
EMA_FAST = int(os.getenv("EMA_FAST", "9"))
EMA_SLOW = int(os.getenv("EMA_SLOW", "21"))
EMA_TREND = int(os.getenv("EMA_TREND", "200"))  # Long-term trend
HTF_EMA = int(os.getenv("HTF_EMA", "50"))  # Higher timeframe EMA
D1_EMA = int(os.getenv("D1_EMA", "50"))  # Daily EMA
W1_EMA = int(os.getenv("W1_EMA", "20"))  # Weekly EMA (Elder)

# =============================================================================
# PARAMÈTRES PAR CLASSE D'ACTIFS (override des paramètres globaux)
# =============================================================================
# --- CRYPTO (Binance Futures) ---
# EMA(21,55) : moins de bruit sur H1 crypto vs EMA(9,21) trop rapides
# ADX 25     : seuil plus élevé car la crypto est volatile même en range
# SCORE_MIN 7 : confirmation supplémentaire nécessaire sur marchés manipulables
EMA_FAST_CRYPTO = int(os.getenv("EMA_FAST_CRYPTO", "21"))
EMA_SLOW_CRYPTO = int(os.getenv("EMA_SLOW_CRYPTO", "55"))
ADX_TREND_CRYPTO = int(os.getenv("ADX_TREND_CRYPTO", "25"))
SCORE_MIN_CRYPTO = int(os.getenv("SCORE_MIN_CRYPTO", "7"))
SL_ATR_MULT_CRYPTO = float(os.getenv("SL_ATR_MULT_CRYPTO", "2.0"))  # SL plus large (crypto volatile)
TP_ATR_MULT_CRYPTO = float(os.getenv("TP_ATR_MULT_CRYPTO", "4.0"))  # TP plus ambitieux

# --- FOREX (MetaTrader 5 — marchés institutionnels) ---
# EMA(14,50) : Plus réactif pour capter les tendances de moyen terme
# ADX 18     : Abaissé pour permettre plus de signaux en tendance faible
# SCORE_MIN 5 : Permet plus d'opportunités de trades
EMA_FAST_FOREX = int(os.getenv("EMA_FAST_FOREX", "14"))
EMA_SLOW_FOREX = int(os.getenv("EMA_SLOW_FOREX", "50"))
ADX_TREND_FOREX = int(os.getenv("ADX_TREND_FOREX", "18"))
SCORE_MIN_FOREX = int(os.getenv("SCORE_MIN_FOREX", "5"))
SL_ATR_MULT_FOREX = float(os.getenv("SL_ATR_MULT_FOREX", "1.5"))   # SL standard
TP_ATR_MULT_FOREX = float(os.getenv("TP_ATR_MULT_FOREX", "3.0"))   # TP standard
# News économiques maçjeures à éviter (nombres en minutes avant/après)
FOREX_NEWS_AVOID_MINUTES = int(os.getenv("FOREX_NEWS_AVOID_MINUTES", "30"))

# --- ETF/STOCKS (Alpaca US Markets) ---
# EMA(20,50) : références institutionnelles US (EMA20 = SMA20 standard, EMA50 clé)
# ADX 20     : ETF trend est stable, seuil standard
# SCORE_MIN 5 : ETF moins volatils, moins de signal à filtrer
# ALLOW_SHORT_STOCK false : éviter les shorts sur ETF (PDT rule, margin costs)
EMA_FAST_STOCK = int(os.getenv("EMA_FAST_STOCK", "20"))
EMA_SLOW_STOCK = int(os.getenv("EMA_SLOW_STOCK", "50"))
ADX_TREND_STOCK = int(os.getenv("ADX_TREND_STOCK", "20"))
SCORE_MIN_STOCK = int(os.getenv("SCORE_MIN_STOCK", "5"))
SL_ATR_MULT_STOCK = float(os.getenv("SL_ATR_MULT_STOCK", "1.5"))   # SL standard
TP_ATR_MULT_STOCK = float(os.getenv("TP_ATR_MULT_STOCK", "3.0"))   # TP standard
ALLOW_SHORT_STOCK = os.getenv("ALLOW_SHORT_STOCK", "false").lower() == "true"  # Désactivé par défaut

# RSI
RSI_LEN = int(os.getenv("RSI_LEN", "14"))
RSI_OB = int(os.getenv("RSI_OB", "70"))  # Overbought
RSI_OS = int(os.getenv("RSI_OS", "30"))  # Oversold

# MACD
MACD_FAST = int(os.getenv("MACD_FAST", "12"))
MACD_SLOW = int(os.getenv("MACD_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

# ADX (Trend strength)
ADX_LEN = int(os.getenv("ADX_LEN", "14"))
ADX_TREND = int(os.getenv("ADX_TREND", "22"))  # Threshold for trending vs ranging

# Supertrend
ST_MULTIPLIER = float(os.getenv("ST_MULTIPLIER", "3.0"))
ST_ATR_LEN = int(os.getenv("ST_ATR_LEN", "10"))

# ATR (Volatility)
ATR_LEN = int(os.getenv("ATR_LEN", "14"))

# Bollinger Bands
BB_LEN = int(os.getenv("BB_LEN", "20"))
BB_STD = float(os.getenv("BB_STD", "2.0"))

# Ichimoku Cloud parameters
ICHIMOKU_TENKAN = int(os.getenv("ICHIMOKU_TENKAN", "9"))
ICHIMOKU_KIJUN = int(os.getenv("ICHIMOKU_KIJUN", "26"))
ICHIMOKU_SENKOU_SPAN_B = int(os.getenv("ICHIMOKU_SENKOU_SPAN_B", "52"))
ICHIMOKU_DISPLACEMENT = int(os.getenv("ICHIMOKU_DISPLACEMENT", "26"))

# VWAP
VWAP_WINDOW = int(os.getenv("VWAP_WINDOW", "14"))

# =============================================================================
# ️ RISK MANAGEMENT PARAMETERS
# =============================================================================
# Risk per trade (account currency %)
RISK_PCT = float(os.getenv("RISK_PCT", "1.5"))

# Stop Loss and Take Profit multiples of ATR
SL_ATR_MULT = float(os.getenv("SL_ATR_MULT", "1.5"))  # Stop Loss = 1.5 × ATR
TP_ATR_MULT = float(os.getenv("TP_ATR_MULT", "3.5"))  # Take Profit = 3.5 × ATR (Asymmetric R:R > 2.3:1)
TRAIL_ATR_MULT = float(os.getenv("TRAIL_ATR_MULT", "1.0"))  # Trailing stop distance
BE_ATR_MULT = float(os.getenv("BE_ATR_MULT", "1.0"))  # Breakeven activation threshold

# Forex filters
MAX_FOREX_CURRENCY_EXPOSURE = int(os.getenv("MAX_FOREX_CURRENCY_EXPOSURE", "2"))
MAX_SPREAD_PIPS = float(os.getenv("MAX_SPREAD_PIPS", "2.5"))
BE_DYN_RR = os.getenv("BE_DYN_RR", "true").lower() == "true"
BE_DYN_RR_RATIO = float(os.getenv("BE_DYN_RR_RATIO", "1.0"))


# Score thresholds
SCORE_MIN = int(os.getenv("SCORE_MIN", "6"))  # Minimum score to enter (out of 10 max base score)

# Drawdown limits (Elder's rules & Hard Daily Cap)
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "3.0"))  # Max daily drawdown %
MAX_DAILY_LOSS_AMOUNT = float(os.getenv("MAX_DAILY_LOSS_AMOUNT", "100.0"))  # Hard cap absolu 100€ max de perte jour
MAX_MONTHLY_LOSS_PCT = float(os.getenv("MAX_MONTHLY_LOSS_PCT", "6.0"))  # Max monthly drawdown %
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "6"))  # Max concurrent positions across fleet

# =============================================================================
# 🗡️ PROTECTION PAR DRAWDOWN (Phase 3 §3)
# =============================================================================
# Seuils de drawdown (en %) déclenchant la réduction progressive du risque par trade.
# BUG-15 FIX: Ces variables étaient dans __all__ mais pas définies dans config.py.
DRAWDOWN_THRESH_1       = float(os.getenv("DRAWDOWN_THRESH_1",       "5.0"))   # % DD niveau 1
DRAWDOWN_THRESH_2       = float(os.getenv("DRAWDOWN_THRESH_2",       "10.0"))  # % DD niveau 2
DRAWDOWN_REDUCE_5PCT    = float(os.getenv("DRAWDOWN_REDUCE_5PCT",    "0.20"))  # -20% risque à 5% DD
DRAWDOWN_REDUCE_10PCT   = float(os.getenv("DRAWDOWN_REDUCE_10PCT",   "0.50"))  # -50% risque à 10% DD

# =============================================================================
# 🌙 PROTECTION NOCTURNE (Recommandation #3 — post-analyse Mer-Ven 22-24/07)
# =============================================================================
# Limite de positions ouvertes en session nocturne (heure UTC)
# Evite l'over-exposition sur des positions corrélées pendant les heures creuses
MAX_OPEN_POSITIONS_NIGHT = int(os.getenv("MAX_OPEN_POSITIONS_NIGHT", "3"))
# Score minimum relevé la nuit pour filtrer les signaux de qualité marginale
SCORE_MIN_NIGHT = int(os.getenv("SCORE_MIN_NIGHT", "8"))
# Fenêtre nocturne en UTC : 20h00 → 06h00 (= 22h → 08h CET en hiver)
NIGHT_SESSION_START_UTC = int(os.getenv("NIGHT_SESSION_START_UTC", "20"))
NIGHT_SESSION_END_UTC = int(os.getenv("NIGHT_SESSION_END_UTC", "6"))

# =============================================================================
# ⏱️ WATCHDOG & PROTECTION POST-FREEZE (Recommandations #2 & #4)
# =============================================================================
# Délai max entre deux heartbeats de cycle avant déclenchement de l'alerte critique (secondes)
CYCLE_WATCHDOG_TIMEOUT = int(os.getenv("CYCLE_WATCHDOG_TIMEOUT", "300"))
# Si un cycle a duré plus longtemps que ce seuil, activer le mode audit post-freeze
# Le bot attendra N cycles d'observation avant d'ouvrir de nouveaux trades
POST_FREEZE_THRESHOLD_SECONDS = int(os.getenv("POST_FREEZE_THRESHOLD_SECONDS", "120"))
# Nombre de cycles d'observation après un freeze avant de reprendre les trades
POST_FREEZE_COOLDOWN_CYCLES = int(os.getenv("POST_FREEZE_COOLDOWN_CYCLES", "2"))

# =============================================================================
# ⚡ CYCLE TIME — V3 Fix bug heartbeat lent (50-60s → 15s)
# =============================================================================
# Durée cible d'un cycle complet en secondes.
# AVANT : 60s par défaut → heartbeat lent (50-60s mesuré = bug critique)
# APRES : 15s → réactivité accrue, pas de signal manqué
CYCLE_TIME = int(os.getenv("CYCLE_TIME", "15"))
# Timeout maximum par symbole pour éviter les blocages (secondes)
SYMBOL_TIMEOUT_SECONDS = int(os.getenv("SYMBOL_TIMEOUT_SECONDS", "8"))
# Nombre max de symboles traités en parallèle (threads)
MAX_PARALLEL_SYMBOLS = int(os.getenv("MAX_PARALLEL_SYMBOLS", "4"))

# =============================================================================
# 🎯 OBJECTIFS JOURNALIERS & GESTION DE SESSIONS — V3
# =============================================================================
# Objectif de gain journalier en EUR (pour comptes ≥ 1000€)
# Le PerformanceLearner adapte automatiquement pour les autres soldes
DAILY_TARGET_EUR = float(os.getenv("DAILY_TARGET_EUR", "200.0"))
# Activer la conscience temporelle (sessions Asia/London/NY)
SESSION_AWARE = os.getenv("SESSION_AWARE", "true").lower() == "true"
# Mode de condition : 'paper' = paper trading, 'live_conditions' = mêmes règles que live mais en paper
# 'live_conditions' impose les mêmes garde-fous (spread, latence, slippage simulé) que le live
TRADING_MODE = os.getenv("TRADING_MODE", "live_conditions")  # 'paper' | 'live_conditions' | 'live'
# Slippage simulé en paper (points/pips) pour conditions réalistes
SIMULATED_SLIPPAGE_POINTS = float(os.getenv("SIMULATED_SLIPPAGE_POINTS", "2.0"))
# Commission simulée en paper (% par trade) pour conditions réalistes
SIMULATED_COMMISSION_PCT = float(os.getenv("SIMULATED_COMMISSION_PCT", "0.003"))

# =============================================================================
# 🪙 CRYPTO SUR MT5 — V3 (paires CFD crypto via Fusion Markets)
# =============================================================================
# Fusion Markets propose des CFD crypto : BTCUSD, ETHUSD, BNBUSD, XRPUSD, SOLUSD
# Ces symboles sont disponibles 24h/24 7j/7 sur MT5
MT5_CRYPTO_ENABLED = os.getenv("MT5_CRYPTO_ENABLED", "true").lower() == "true"
# Symboles crypto disponibles sur Fusion Markets MT5 (format sans /)
MT5_CRYPTO_SYMBOLS_STR = os.getenv("MT5_CRYPTO_SYMBOLS", "BTCUSD,ETHUSD,BNBUSD,XRPUSD")
MT5_CRYPTO_SYMBOLS: list = [s.strip() for s in MT5_CRYPTO_SYMBOLS_STR.split(",") if s.strip()]
# Paramètres crypto MT5 (CFD avec spread, pas de funding)
MT5_CRYPTO_SCORE_MIN = int(os.getenv("MT5_CRYPTO_SCORE_MIN", "7"))
MT5_CRYPTO_SL_ATR = float(os.getenv("MT5_CRYPTO_SL_ATR", "2.0"))
MT5_CRYPTO_TP_ATR = float(os.getenv("MT5_CRYPTO_TP_ATR", "4.0"))
MT5_CRYPTO_MAX_SPREAD = float(os.getenv("MT5_CRYPTO_MAX_SPREAD", "50.0"))  # En points

# =============================================================================
# 🧠 PARAMÈTRES AUTO-APPRENTISSAGE — V3 (PerformanceLearner)
# =============================================================================
# Activer l'auto-apprentissage post-session
AUTO_LEARN_ENABLED = os.getenv("AUTO_LEARN_ENABLED", "true").lower() == "true"
# Heure UTC du debrief post-session (analyse de fin de journée)
POST_SESSION_DEBRIEF_HOUR_UTC = int(os.getenv("POST_SESSION_DEBRIEF_HOUR_UTC", "22"))
# Heure UTC de la pré-analyse (avant ouverture London)
PRE_SESSION_ANALYSIS_HOUR_UTC = int(os.getenv("PRE_SESSION_ANALYSIS_HOUR_UTC", "6"))
# Activer le Knowledge Feeder automatique (ingestion quotidienne RSS/blogs/forums)
KNOWLEDGE_FEEDER_ENABLED = os.getenv("KNOWLEDGE_FEEDER_ENABLED", "true").lower() == "true"
# Heure UTC d'ingestion quotidienne des nouvelles ressources
KNOWLEDGE_FEEDER_HOUR_UTC = int(os.getenv("KNOWLEDGE_FEEDER_HOUR_UTC", "0"))
# Reddit API (optionnel) - pour scraping r/Forex r/algotrading
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
# Alpha Vantage (gratuit, 500 req/jour)
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
# FRED (Federal Reserve Economic Data) — gratuit, sans clé requise
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
# NewsAPI (optionnel, 100 req/jour gratuit)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# =============================================================================
# 📊 PARAMÈTRES ADAPTATIFS PAR SOLDE — V3
# =============================================================================
# Seuils de solde pour l'adaptation automatique des barrières
BALANCE_TIER_HIGH = float(os.getenv("BALANCE_TIER_HIGH", "5000.0"))   # ≥5000€ : agressif
BALANCE_TIER_MID = float(os.getenv("BALANCE_TIER_MID", "1000.0"))    # ≥1000€ : standard (200€/j)
BALANCE_TIER_LOW = float(os.getenv("BALANCE_TIER_LOW", "500.0"))     # ≥500€ : prudent
BALANCE_TIER_MICRO = float(os.getenv("BALANCE_TIER_MICRO", "200.0")) # ≥200€ : micro

# Position sizing limits
MIN_POSITION_SIZE = float(os.getenv("MIN_POSITION_SIZE", "0.001"))
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "1000.0"))

# Cooldown minimum entre deux trades consécutifs sur le même symbole (en secondes)
# 300s (5 minutes) pour réactivité optimale en tendance forte
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "300"))

# Kelly fraction parameters (Industrial standard)
KELLY_FRACTION = float(os.getenv("KELLY_FRACTION", "0.45"))  # 45% Kelly optimum pour compounding rapide
MIN_TRADES_FOR_KELLY = int(os.getenv("MIN_TRADES_FOR_KELLY", "15"))  # Min trades before using Kelly

# =============================================================================
# NEWS & SENTIMENT CONFIGURATION
# =============================================================================
# News avoidance windows (minutes)
NEWS_AVOIDANCE_BEFORE = int(os.getenv("NEWS_AVOIDANCE_BEFORE", "30"))  # Block entry X min before news
NEWS_AVOIDANCE_AFTER = int(os.getenv("NEWS_AVOIDANCE_AFTER", "30"))   # Block entry X min after news

# News impact on position sizing
NEWS_RISK_REDUCTION_FACTOR = float(os.getenv("NEWS_RISK_REDUCTION_FACTOR", "0.5"))  # Reduce risk by this factor if news today
NEWS_HIGH_IMPACT_ONLY = os.getenv("NEWS_HIGH_IMPACT_ONLY", "true").lower() == "true"  # Only consider HIGH impact news

# Currencies/assets to monitor for news (comma-separated)
NEWS_ASSETS_STR = os.getenv("NEWS_ASSETS", "BTC,ETH,EUR,USD,SPY")
NEWS_ASSETS = [s.strip().upper() for s in NEWS_ASSETS_STR.split(",")]

# News update interval (seconds)
NEWS_UPDATE_INTERVAL = int(os.getenv("NEWS_UPDATE_INTERVAL", "300"))  # 5 minutes

# News API endpoints (free tiers)
FEAR_GREED_API = "https://api.alternative.me/fng/"
COINGECKO_API = "https://api.coingecko.com/api/v3"
CRYPTOCOMPARE_API = "https://min-api.cryptocompare.com/data"
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "")
FOREXFACTORY_API = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
# For ETFs/news, we could use Finnhub, IEX Cloud, etc. but keeping free sources for now

# Fear & Greed thresholds (for contrarian signals)
FEAR_GREED_EXTREME_FEAR = int(os.getenv("FEAR_GREED_EXTREME_FEAR", "20"))  # < 20 = buying opportunity
FEAR_GREED_EXTREME_GREED = int(os.getenv("FEAR_GREED_EXTREME_GREED", "80"))  # > 80 = selling opportunity

# =============================================================================
# WEBHOOK CONFIGURATION (for TradingView alerts)
# =============================================================================
WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change_this_to_a_strong_secret")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))

# =============================================================================
# ⏰ TRADING SESSIONS & LIQUIDITY FILTERS
# =============================================================================
# Trading sessions in UTC (for forex-like assets that have session preferences)
# Format: list of (start_hour, end_hour) tuples
FOREX_SESSIONS_UTC = [
    (7, 16),   # London session
    (12, 20),  # New York session
    (23, 6),   # Tokyo session (overnight)
]

# Crypto and ETFs can use liquidity filters based on high-volume hours
USE_LIQUIDITY_FILTER = os.getenv("USE_LIQUIDITY_FILTER", "false").lower() == "true"
HIGH_LIQUIDITY_HOURS_UTC = [
    (8, 16),   # London/New York overlap
    (0, 6),    # Asian session
]

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"superbot_{BROKER_TYPE}.log"
TRADE_LOG_FILE = LOG_DIR / f"trades_{BROKER_TYPE}.jsonl"  # Structured trade logs for analysis
ERROR_LOG_FILE = LOG_DIR / f"errors_{BROKER_TYPE}.log"
BUG_LOG_FILE   = LOG_DIR / "bug_log.md"                   # Bug Watchdog journal (Formulation 2)

# =============================================================================
# 🐛 BUG WATCHDOG CONFIGURATION (Formulation 2 — agent de supervision technique)
# =============================================================================
# Intervalle de vérification du watchdog (secondes)
BUG_WATCHDOG_INTERVAL = int(os.getenv("BUG_WATCHDOG_INTERVAL", "60"))
# Activer/désactiver le Bug Watchdog
BUG_WATCHDOG_ENABLED  = os.getenv("BUG_WATCHDOG_ENABLED", "true").lower() == "true"
# Latence d'exécution maximale acceptée (secondes) avant d'émettre une alerte Medium
BUG_WATCHDOG_MAX_LATENCY = float(os.getenv("BUG_WATCHDOG_MAX_LATENCY", "5.0"))

# =============================================================================
# 📈 TRAILING PROFIT CIRCUIT BREAKER (Formulation 2 — protection des gains en série)
# =============================================================================
# Profit minimal (€) à partir duquel le circuit breaker est actif
PROFIT_CB_TRIGGER_EUR      = float(os.getenv("PROFIT_CB_TRIGGER_EUR",      "200.0"))
# Retracement (fraction) du pic qui déclenche la pause (ex: 0.25 = -25%)
PROFIT_CB_RETRACEMENT      = float(os.getenv("PROFIT_CB_RETRACEMENT",      "0.25"))
# Durée de la pause de trading en heures (Règle 1)
PROFIT_CB_PAUSE_HOURS      = float(os.getenv("PROFIT_CB_PAUSE_HOURS",      "3.0"))
# Retracement après reprise qui déclenche l'arrêt définitif (Règle 2)
PROFIT_CB_STOP_RETRACEMENT = float(os.getenv("PROFIT_CB_STOP_RETRACEMENT", "0.25"))


# =============================================================================
# DEVELOPMENT & TESTING
# =============================================================================
# ENABLE_PAPER_TRADING supprimé — utiliser le broker alpaca avec paper-api.alpaca.markets pour simuler
BACKTEST_MODE = os.getenv("BACKTEST_MODE", "false").lower() == "true"
LOG_TRADES = os.getenv("LOG_TRADES", "true").lower() == "true"
ENABLE_DASHBOARD = os.getenv("ENABLE_DASHBOARD", "true").lower() == "true"
# V3: Chemin base de données SQLite persistante
import tempfile as _tmpfile
_default_db_path = str(Path(__file__).parent / "db" / "nexquant.db")
DB_PATH = os.getenv("DB_PATH", _default_db_path)

# =============================================================================
# CONFIGURATION VALIDATION ENGINE
# =============================================================================
def validate_config():
    """
    Validates key configuration settings to ensure safe trading conditions.
    Only checks broker credentials if NOT in backtesting mode.
    """
    errors = []

    # 1. Broker type check
    valid_brokers = ["binance", "alpaca", "mt5"]
    if BROKER_TYPE.lower() not in valid_brokers:
        errors.append(f"BROKER_TYPE '{BROKER_TYPE}' est invalide. Doit être l'un de : {valid_brokers}")

    # 2. Broker credentials check (only if not backtesting and not using SaaS mode)
    using_saas = bool(os.getenv("NEXQUANT_USER_ID") and os.getenv("NEXQUANT_INGEST_TOKEN"))
    if not BACKTEST_MODE and not using_saas:
        if BROKER_TYPE.lower() == "mt5":
            if MT5_LOGIN <= 0:
                errors.append("MT5_LOGIN doit être un entier positif (votre identifiant de compte).")
            if not MT5_PASSWORD:
                errors.append("MT5_PASSWORD ne doit pas être vide.")
            if not MT5_SERVER:
                errors.append("MT5_SERVER ne doit pas être vide.")
        elif BROKER_TYPE.lower() == "binance":
            if not BINANCE_API_KEY or not BINANCE_API_SECRET:
                errors.append("BINANCE_API_KEY et BINANCE_API_SECRET doivent être configurés.")
        elif BROKER_TYPE.lower() == "alpaca":
            if not ALPACA_API_KEY or not ALPACA_API_SECRET:
                errors.append("ALPACA_API_KEY et ALPACA_API_SECRET doivent être configurés.")

    # 3. Risk parameter bounds checks
    if not (0.1 <= RISK_PCT <= 10.0):  # V3: élargi à 10% max pour stratégies agressives
        errors.append(f"RISK_PCT ({RISK_PCT}%) est hors limites. Il doit être compris entre 0.1% et 10.0% par transaction.")

    if not (0.5 <= MAX_DAILY_LOSS_PCT <= 15.0):  # V3: élargi à 15% pour stratégies x10
        errors.append(f"MAX_DAILY_LOSS_PCT ({MAX_DAILY_LOSS_PCT}%) est hors limites. Il doit être compris entre 0.5% et 15.0% pour protéger le capital.")

    if not (1.0 <= MAX_MONTHLY_LOSS_PCT <= 20.0):
        errors.append(f"MAX_MONTHLY_LOSS_PCT ({MAX_MONTHLY_LOSS_PCT}%) doit être compris entre 1.0% et 20.0%.")

    if not (1 <= MAX_OPEN_POSITIONS <= 10):
        errors.append(f"MAX_OPEN_POSITIONS ({MAX_OPEN_POSITIONS}) doit être compris entre 1 et 10.")

    if not (0.5 <= SL_ATR_MULT <= 5.0):
        errors.append(f"SL_ATR_MULT ({SL_ATR_MULT}) est anormal et doit être compris entre 0.5 et 5.0.")

    if not (1.0 <= TP_ATR_MULT <= 10.0):
        errors.append(f"TP_ATR_MULT ({TP_ATR_MULT}) doit être compris entre 1.0 et 10.0.")

    if not (1 <= SCORE_MIN <= 10):
        errors.append(f"SCORE_MIN ({SCORE_MIN}) doit être compris entre 1 et 10.")

    if errors:
        error_msg = (
            "\n" + "="*80 + "\n"
            "❌ ERREURS DE CONFIGURATION DU SUPERBOT DÉTECTÉES :\n"
            + "\n".join(f"  • {err}" for err in errors) + "\n"
            "Veuillez ajuster les valeurs correspondantes dans votre fichier '.env'.\n"
            + "="*80 + "\n"
        )
        raise ValueError(error_msg)

# Exécuter la validation automatiquement lors du chargement du module
validate_config()

# Export all config values
__all__ = [
    "validate_config",
    # Crypto-specific filters (rapport 2026-07-02)
    "CRYPTO_BLACKLIST", "CRYPTO_SCORE_MIN", "CRYPTO_BUY_BLOCK_BTC_DROP", "CRYPTO_BNB_VOLUME_FACTOR",
    # Broker
    "BROKER_TYPE", "ALLOW_LIVE_TRADING",

    # MT5 (prioritaire V3)
    "MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER", "MT5_PATH",

    # MT5 Crypto (CFD)
    "MT5_CRYPTO_ENABLED", "MT5_CRYPTO_SYMBOLS", "MT5_CRYPTO_SCORE_MIN",
    "MT5_CRYPTO_SL_ATR", "MT5_CRYPTO_TP_ATR", "MT5_CRYPTO_MAX_SPREAD",

    # Binance
    "BINANCE_API_KEY", "BINANCE_API_SECRET", "BINANCE_TESTNET", "LEVERAGE",

    # Alpaca
    "ALPACA_API_KEY", "ALPACA_API_SECRET", "ALPACA_BASE_URL", "ALPACA_API_VERSION",

    # Forex data providers (utilisés par MT5)
    "TWELVEDATA_API_KEY", "ALPHAVANTAGE_API_KEY", "FOREX_DATA_PROVIDER",
    "FOREX_DEFAULT_LEVERAGE", "FOREX_MARGIN_CALL_LEVEL", "FOREX_STOP_OUT_LEVEL",

    # Trading
    "INSTRUMENTS", "GRANULARITY", "HTF_GRANULARITY", "D1_GRANULARITY",
    "W1_GRANULARITY", "N_CANDLES",

    # Indicators
    "EMA_FAST", "EMA_SLOW", "EMA_TREND", "HTF_EMA", "D1_EMA", "W1_EMA",
    "RSI_LEN", "RSI_OB", "RSI_OS", "MACD_FAST", "MACD_SLOW", "MACD_SIGNAL",
    "ADX_LEN", "ADX_TREND", "ST_MULTIPLIER", "ST_ATR_LEN", "ATR_LEN",
    "BB_LEN", "BB_STD", "ICHIMOKU_TENKAN", "ICHIMOKU_KIJUN",
    "ICHIMOKU_SENKOU_SPAN_B", "ICHIMOKU_DISPLACEMENT", "VWAP_WINDOW",

    # Paramètres par classe d'actifs
    "EMA_FAST_CRYPTO", "EMA_SLOW_CRYPTO", "ADX_TREND_CRYPTO", "SCORE_MIN_CRYPTO",
    "SL_ATR_MULT_CRYPTO", "TP_ATR_MULT_CRYPTO",
    "EMA_FAST_FOREX", "EMA_SLOW_FOREX", "ADX_TREND_FOREX", "SCORE_MIN_FOREX",
    "SL_ATR_MULT_FOREX", "TP_ATR_MULT_FOREX", "FOREX_NEWS_AVOID_MINUTES",
    "EMA_FAST_STOCK", "EMA_SLOW_STOCK", "ADX_TREND_STOCK", "SCORE_MIN_STOCK",
    "SL_ATR_MULT_STOCK", "TP_ATR_MULT_STOCK", "ALLOW_SHORT_STOCK",

    # Risk Management
    "RISK_PCT", "SL_ATR_MULT", "TP_ATR_MULT", "TRAIL_ATR_MULT", "BE_ATR_MULT",
    "SCORE_MIN", "MAX_DAILY_LOSS_PCT", "MAX_MONTHLY_LOSS_PCT", "MAX_OPEN_POSITIONS",
    "MAX_DAILY_LOSS_AMOUNT",
    "MIN_POSITION_SIZE", "MAX_POSITION_SIZE", "KELLY_FRACTION", "MIN_TRADES_FOR_KELLY",
    "COOLDOWN_SECONDS",
    "MAX_FOREX_CURRENCY_EXPOSURE", "MAX_SPREAD_PIPS", "BE_DYN_RR", "BE_DYN_RR_RATIO",
    "DRAWDOWN_REDUCE_5PCT", "DRAWDOWN_REDUCE_10PCT", "DRAWDOWN_THRESH_1", "DRAWDOWN_THRESH_2",

    # Protection nocturne
    "MAX_OPEN_POSITIONS_NIGHT", "SCORE_MIN_NIGHT",
    "NIGHT_SESSION_START_UTC", "NIGHT_SESSION_END_UTC",

    # Watchdog
    "CYCLE_WATCHDOG_TIMEOUT", "POST_FREEZE_THRESHOLD_SECONDS", "POST_FREEZE_COOLDOWN_CYCLES",
    "BUG_WATCHDOG_INTERVAL", "BUG_WATCHDOG_ENABLED", "BUG_WATCHDOG_MAX_LATENCY",

    # ⚡ V3 — Cycle et performance
    "CYCLE_TIME", "SYMBOL_TIMEOUT_SECONDS", "MAX_PARALLEL_SYMBOLS",

    # 🎯 V3 — Objectifs journaliers & sessions
    "DAILY_TARGET_EUR", "SESSION_AWARE", "TRADING_MODE",
    "SIMULATED_SLIPPAGE_POINTS", "SIMULATED_COMMISSION_PCT",

    # 🧠 V3 — Auto-apprentissage
    "AUTO_LEARN_ENABLED", "POST_SESSION_DEBRIEF_HOUR_UTC", "PRE_SESSION_ANALYSIS_HOUR_UTC",
    "KNOWLEDGE_FEEDER_ENABLED", "KNOWLEDGE_FEEDER_HOUR_UTC",
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
    "FRED_API_KEY", "NEWS_API_KEY",

    # 📊 V3 — Tiers de solde adaptatifs
    "BALANCE_TIER_HIGH", "BALANCE_TIER_MID", "BALANCE_TIER_LOW", "BALANCE_TIER_MICRO",

    # Circuit breaker profit
    "PROFIT_CB_TRIGGER_EUR", "PROFIT_CB_RETRACEMENT",
    "PROFIT_CB_PAUSE_HOURS", "PROFIT_CB_STOP_RETRACEMENT",

    # News & Sentiment
    "NEWS_AVOIDANCE_BEFORE", "NEWS_AVOIDANCE_AFTER", "NEWS_RISK_REDUCTION_FACTOR",
    "NEWS_HIGH_IMPACT_ONLY", "NEWS_ASSETS", "NEWS_UPDATE_INTERVAL",
    "FEAR_GREED_API", "COINGECKO_API", "CRYPTOCOMPARE_API", "CRYPTOCOMPARE_API_KEY", "FOREXFACTORY_API",
    "FEAR_GREED_EXTREME_FEAR", "FEAR_GREED_EXTREME_GREED",

    # Webhook
    "WEBHOOK_ENABLED", "WEBHOOK_SECRET", "WEBHOOK_HOST", "WEBHOOK_PORT",

    # Sessions
    "FOREX_SESSIONS_UTC", "USE_LIQUIDITY_FILTER", "HIGH_LIQUIDITY_HOURS_UTC",

    # Logging
    "LOG_LEVEL", "LOG_DIR", "LOG_FILE", "TRADE_LOG_FILE", "ERROR_LOG_FILE", "BUG_LOG_FILE",

    # Development
    "BACKTEST_MODE", "LOG_TRADES", "ENABLE_DASHBOARD",

    # DB
    "DB_PATH",
]