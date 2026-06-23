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
BROKER_TYPE = os.getenv("BROKER_TYPE", "binance").lower()  # binance, alpaca, paper_forex, mt5, xtb

# =============================================================================
# METATRADER 5 (MT5) CONFIGURATION (associated with Fusion Markets)
# =============================================================================
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "FusionMarkets-Demo")
MT5_PATH = os.getenv("MT5_PATH", "")  # Path to terminal64.exe (optional)

# =============================================================================
# XTB CONFIGURATION (connects via numeric account ID and password)
# =============================================================================
XTB_USER_ID = os.getenv("XTB_USER_ID", os.getenv("XTB_EMAIL", ""))
XTB_EMAIL = XTB_USER_ID  # Alias de compatibilité
XTB_PASSWORD = os.getenv("XTB_PASSWORD", "")
XTB_SERVER = os.getenv("XTB_SERVER", "demo").lower()  # demo, real

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
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")  # Use paper trading by default
ALPACA_API_VERSION = os.getenv("ALPACA_API_VERSION", "v2")

# =============================================================================
# PAPER FOREX ENGINE CONFIGURATION
# =============================================================================
# Paper trading parameters for forex simulation
FOREX_DEFAULT_LEVERAGE = int(os.getenv("FOREX_DEFAULT_LEVERAGE", "30"))  # Typical forex leverage
FOREX_MARGIN_CALL_LEVEL = float(os.getenv("FOREX_MARGIN_CALL_LEVEL", "0.5"))  # 50% margin used triggers call
FOREX_STOP_OUT_LEVEL = float(os.getenv("FOREX_STOP_OUT_LEVEL", "0.2"))  # 20% margin used triggers stop out

# =============================================================================
# TRADING INSTRUMENTS & TIMEFRAMES
# =============================================================================
# Instruments to trade - format depends on broker
# For Binance: "BTC/USDT", "ETH/USDT"
# For Alpaca: "SPY", "QQQ", "AAPL"
# For Paper Forex: "EUR/USD", "GBP/USD", "USD/JPY"
INSTRUMENTS_STR = os.getenv("INSTRUMENTS", "BTC/USDT")
INSTRUMENTS = [s.strip() for s in INSTRUMENTS_STR.split(",")]

# Timeframes for analysis
GRANULARITY = os.getenv("GRANULARITY", "1h")  # Main trading timeframe
HTF_GRANULARITY = os.getenv("HTF_GRANULARITY", "4h")  # Higher timeframe for trend confirmation
D1_GRANULARITY = os.getenv("D1_GRANULARITY", "1d")  # Daily timeframe
W1_GRANULARITY = os.getenv("W1_GRANULARITY", "1w")  # Weekly timeframe (Elder's triple screen)
N_CANDLES = int(os.getenv("N_CANDLES", "500"))  # Number of candles to fetch

# =============================================================================
# TECHNICAL INDICATOR PARAMETERS
# =============================================================================
# Moving Averages
EMA_FAST = int(os.getenv("EMA_FAST", "9"))
EMA_SLOW = int(os.getenv("EMA_SLOW", "21"))
EMA_TREND = int(os.getenv("EMA_TREND", "200"))  # Long-term trend
HTF_EMA = int(os.getenv("HTF_EMA", "50"))  # Higher timeframe EMA
D1_EMA = int(os.getenv("D1_EMA", "50"))  # Daily EMA
W1_EMA = int(os.getenv("W1_EMA", "20"))  # Weekly EMA (Elder)

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
RISK_PCT = float(os.getenv("RISK_PCT", "1.0"))

# Stop Loss and Take Profit multiples of ATR
SL_ATR_MULT = float(os.getenv("SL_ATR_MULT", "1.5"))  # Stop Loss = 1.5 × ATR
TP_ATR_MULT = float(os.getenv("TP_ATR_MULT", "3.0"))  # Take Profit = 3.0 × ATR (1:2 RR)
TRAIL_ATR_MULT = float(os.getenv("TRAIL_ATR_MULT", "1.0"))  # Trailing stop distance
BE_ATR_MULT = float(os.getenv("BE_ATR_MULT", "1.0"))  # Breakeven activation threshold

# Score thresholds
SCORE_MIN = int(os.getenv("SCORE_MIN", "6"))  # Minimum score to enter (out of 10 max base score)

# Drawdown limits (Elder's rules)
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "3.0"))  # Max daily drawdown %
MAX_MONTHLY_LOSS_PCT = float(os.getenv("MAX_MONTHLY_LOSS_PCT", "6.0"))  # Max monthly drawdown %
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "3"))  # Max concurrent positions

# Position sizing limits (will be adjusted by broker-specific min/max)
MIN_POSITION_SIZE = float(os.getenv("MIN_POSITION_SIZE", "0.001"))
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "1000.0"))

# Kelly fraction parameters
KELLY_FRACTION = float(os.getenv("KELLY_FRACTION", "0.25"))  # Use 25% of Kelly optimum (conservative)
MIN_TRADES_FOR_KELLY = int(os.getenv("MIN_TRADES_FOR_KELLY", "20"))  # Min trades before using Kelly

# =============================================================================
# NEWS & SENTIMENT CONFIGURATION
# =============================================================================
# News avoidance windows (minutes)
NEWS_AVOIDANCE_BEFORE = int(os.getenv("NEWS_AVOIDANCE_BEFORE", "30"))  # Block entry X min before news
NEWS_AVOIDANCE_AFTER = int(os.getenv("NEWS_AVOIDANCE_AFTER", "15"))   # Block entry X min after news

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
LOG_FILE = LOG_DIR / "superbot.log"
TRADE_LOG_FILE = LOG_DIR / "trades.jsonl"  # Structured trade logs for analysis
ERROR_LOG_FILE = LOG_DIR / "errors.log"

# =============================================================================
# DEVELOPMENT & TESTING
# =============================================================================
ENABLE_PAPER_TRADING = os.getenv("ENABLE_PAPER_TRADING", "true").lower() == "true"
BACKTEST_MODE = os.getenv("BACKTEST_MODE", "false").lower() == "true"
LOG_TRADES = os.getenv("LOG_TRADES", "true").lower() == "true"
ENABLE_DASHBOARD = os.getenv("ENABLE_DASHBOARD", "true").lower() == "true"

# Export all config values
__all__ = [
    # Broker
    "BROKER_TYPE",

    # Binance
    "BINANCE_API_KEY", "BINANCE_API_SECRET", "BINANCE_TESTNET", "LEVERAGE",

    # Alpaca
    "ALPACA_API_KEY", "ALPACA_API_SECRET", "ALPACA_BASE_URL", "ALPACA_API_VERSION",

    # Paper Forex
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

    # Risk Management
    "RISK_PCT", "SL_ATR_MULT", "TP_ATR_MULT", "TRAIL_ATR_MULT", "BE_ATR_MULT",
    "SCORE_MIN", "MAX_DAILY_LOSS_PCT", "MAX_MONTHLY_LOSS_PCT", "MAX_OPEN_POSITIONS",
    "MIN_POSITION_SIZE", "MAX_POSITION_SIZE", "KELLY_FRACTION", "MIN_TRADES_FOR_KELLY",

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
    "LOG_LEVEL", "LOG_DIR", "LOG_FILE", "TRADE_LOG_FILE", "ERROR_LOG_FILE",

    # Development
    "ENABLE_PAPER_TRADING", "BACKTEST_MODE", "LOG_TRADES", "ENABLE_DASHBOARD"
]