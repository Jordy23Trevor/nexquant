"""
NexQuant — Knowledge Module: Dr. Alexander Elder
=================================================
Livre : "Vivre du Trading" / "Come Into My Trading Room" (2002)
Niveau : 2 — Intermédiaire (systèmes de trading, gestion du risque, psychologie)

Elder apporte la STRUCTURE au-dessus des fondations de Murphy.
Les règles d'Elder sont des MODIFICATEURS DE SCORE et des règles de
money management strictes appliquées à chaque trade.

Hiérarchie de l'intégration :
1. Murphy (niveau 1) → lit le marché
2. Elder (niveau 2) → structure le système de trading
3. Chan (niveau 3)  → optimise mathématiquement

Principes clés d'Elder :
- Triple Screen System : 3 timeframes, 3 filtres successifs
- Impulse System : couleur de la bougie = alignement tendance + momentum
- Iron Triangle : Money Management > Entries > Psychology
- Règle des 2% et 6% : limites de perte absolues

Source : Dr. Alexander Elder — Vivre du Trading / Come Into My Trading Room
Publisher : Valor Editions (FR), Wiley (EN), 2002
"""
from typing import List, Dict, Any

ELDER_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # TRIPLE SCREEN SYSTEM — Le cœur de la méthode Elder
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_triple_screen_system",
        "level": 2,
        "category": "strategy",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - The Triple Screen Trading System",
        "rule": (
            "The Triple Screen System uses three timeframes: "
            "(1) Weekly chart for trend direction (using MACD or EMA slope), "
            "(2) Daily chart for oscillator timing (Stochastic, Force Index), "
            "(3) Intraday chart for entry execution. "
            "Only trade in the direction of the weekly trend, confirmed by daily oscillator."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 2.0,
            "description": "ENFORCE_MULTI_TIMEFRAME: weekly trend mandatory filter before any entry"
        },
        "keywords": ["triple screen", "weekly", "daily", "timeframe", "oscillator", "trend"],
    },
    {
        "id": "elder_screen1_weekly_trend",
        "level": 2,
        "category": "filter",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - The Triple Screen Trading System",
        "rule": (
            "Screen 1 (Weekly): A rising weekly MACD histogram indicates a bullish tide. "
            "A falling weekly histogram indicates a bearish tide. "
            "Only take longs when the weekly tide is bullish, only take shorts when bearish."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Weekly trend filter: refuse signals against the weekly MACD tide"
        },
        "keywords": ["screen 1", "weekly", "MACD histogram", "tide", "bullish", "bearish"],
    },
    {
        "id": "elder_screen2_daily_oscillator",
        "level": 2,
        "category": "signal",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - The Triple Screen Trading System",
        "rule": (
            "Screen 2 (Daily): When weekly trend is up, buy when daily oscillator (Stochastic/Force Index) "
            "declines into oversold territory and turns up. "
            "When weekly trend is down, sell when daily oscillator rises into overbought and turns down. "
            "This gives counter-cyclical entry in the direction of the primary trend."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.5,
            "description": "Daily oscillator pullback in trend direction adds significantly to entry score"
        },
        "keywords": ["screen 2", "daily", "oscillator", "pullback", "oversold", "entry timing"],
    },
    {
        "id": "elder_screen3_intraday_entry",
        "level": 2,
        "category": "signal",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - The Triple Screen Trading System",
        "rule": (
            "Screen 3 (Intraday): After Screens 1 and 2 are aligned, use a trailing buy stop "
            "one tick above the previous bar's high (for longs) or a trailing sell stop "
            "one tick below the previous bar's low (for shorts). "
            "This ensures entry only when price moves in the anticipated direction."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Intraday entry timing — prefer entries on pullback high break"
        },
        "keywords": ["screen 3", "intraday", "trailing stop", "entry", "pullback"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPULSE SYSTEM — Couleur des bougies comme signal de permission
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_impulse_green_only_long",
        "level": 2,
        "category": "filter",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - The Impulse System",
        "rule": (
            "The Impulse System combines a 13-period EMA (trend) and MACD histogram (momentum). "
            "A GREEN bar = EMA rising AND histogram rising → permission to BUY (long only). "
            "A RED bar = EMA falling AND histogram falling → permission to SELL (short only). "
            "A BLUE bar = mixed → no new positions allowed."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Impulse System: refuse longs on RED bar, refuse shorts on GREEN bar"
        },
        "keywords": ["impulse", "green", "red", "blue", "EMA 13", "histogram", "permission"],
    },
    {
        "id": "elder_impulse_no_entry_mixed",
        "level": 2,
        "category": "filter",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - The Impulse System",
        "rule": (
            "When EMA and MACD histogram give conflicting signals (one up, one down), "
            "the Impulse bar is BLUE — no new positions should be initiated. "
            "Wait for alignment before entering. This prevents entering in choppy markets."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": -1.0,
            "description": "Penalty for entering when Impulse is BLUE (mixed signal)"
        },
        "keywords": ["impulse", "blue", "mixed", "no entry", "choppy"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # FORCE INDEX — Indicateur de volume-prix d'Elder
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_force_index_two_period",
        "level": 2,
        "category": "signal",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Force Index",
        "rule": (
            "The 2-period Force Index = (Close - Previous Close) × Volume. "
            "When in an uptrend, a negative 2-period Force Index (pullback on reduced force) "
            "is a low-risk buy signal. When in a downtrend, a positive 2-period FI is a short signal. "
            "Confirm with trend direction from 13-period EMA."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "Force Index pullback in trend = low-risk entry, adds to score"
        },
        "keywords": ["force index", "2-period", "volume", "pullback", "low-risk", "buy"],
    },
    {
        "id": "elder_force_index_long_term",
        "level": 2,
        "category": "signal",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Force Index",
        "rule": (
            "The 13-period Force Index measures the power of bulls and bears over time. "
            "A rising 13-period FI confirms uptrend momentum. A falling FI confirms downtrend. "
            "Divergence between 13-period FI and price signals an impending reversal."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Long-term Force Index divergence signals reversal"
        },
        "keywords": ["force index", "13-period", "bulls", "bears", "divergence", "reversal"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MONEY MANAGEMENT — Iron Triangle (la règle d'or d'Elder)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_2_percent_rule",
        "level": 2,
        "category": "risk",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Money Management: The Iron Triangle",
        "rule": (
            "Never risk more than 2% of your trading account on any single trade. "
            "The stop-loss distance in dollars must not exceed 2% of total account equity. "
            "This is the absolute maximum — professional traders often use 0.5% to 1%."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "CAP_RISK_PCT: hard cap at 2% risk per trade — Elder's Iron Triangle rule #1"
        },
        "keywords": ["2%", "2 percent", "single trade", "account equity", "risk", "stop loss"],
    },
    {
        "id": "elder_6_percent_monthly_rule",
        "level": 2,
        "category": "risk",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Money Management: The Iron Triangle",
        "rule": (
            "Stop trading for the remainder of the month if account drawdown reaches 6%. "
            "This 6% monthly limit prevents catastrophic loss cascades. "
            "When the 6% is hit, close all positions and observe only — do not trade."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Monthly drawdown circuit breaker: halt all trading at 6% monthly loss"
        },
        "keywords": ["6%", "monthly", "drawdown", "stop trading", "circuit breaker"],
    },
    {
        "id": "elder_iron_triangle_priority",
        "level": 2,
        "category": "strategy",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Money Management: The Iron Triangle",
        "rule": (
            "The Iron Triangle of trading success: "
            "(1) Money Management is most important — without it you cannot survive. "
            "(2) Entry and Exit methods come second. "
            "(3) Psychology comes third — but is the hardest to master. "
            "A trader with mediocre entries but strict money management will outlast a brilliant "
            "analyst with no money management."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Conceptual priority rule — money management always takes precedence over signal quality"
        },
        "keywords": ["iron triangle", "money management", "entry", "psychology", "priority"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MACD ET HISTOGRAMME — La lecture d'Elder du momentum
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_macd_histogram_divergence",
        "level": 2,
        "category": "signal",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - MACD and MACD-Histogram",
        "rule": (
            "When price makes a new high but the MACD histogram makes a lower peak, "
            "this bearish divergence is the strongest sell signal in technical analysis. "
            "When price makes a new low but histogram makes a higher trough, "
            "this bullish divergence is the strongest buy signal."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["TRENDING", "RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 2.0,
            "description": "MACD histogram divergence = Elder's highest confidence signal, major score boost"
        },
        "keywords": ["MACD", "histogram", "divergence", "bearish", "bullish", "strongest signal"],
    },
    {
        "id": "elder_macd_histogram_slope",
        "level": 2,
        "category": "signal",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - MACD and MACD-Histogram",
        "rule": (
            "When the MACD histogram rises for two consecutive bars, it is a buy signal. "
            "When it falls for two consecutive bars, it is a sell signal. "
            "The slope of the histogram is more important than its position relative to zero."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "MACD histogram slope change (2 bars) is an early momentum signal"
        },
        "keywords": ["MACD", "histogram", "slope", "two bars", "rising", "falling"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # EMA ET ENVELOPPE — Zones de surachat/survendu d'Elder
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_ema_channel_overbought",
        "level": 2,
        "category": "signal",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Moving Averages",
        "rule": (
            "Price above the upper EMA envelope (EMA + X%) signals overbought conditions. "
            "Price below the lower EMA envelope (EMA - X%) signals oversold. "
            "Markets tend to revert to the EMA after touching the envelope — use for exits."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "EMA envelope extreme position = exit or reversal signal"
        },
        "keywords": ["EMA", "envelope", "overbought", "oversold", "revert", "channel"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # PSYCHOLOGIE DU TRADING — Elder et la discipline mentale
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_trading_journal_mandatory",
        "level": 2,
        "category": "psychology",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Trader's Diary",
        "rule": (
            "Every trade must be logged: entry reason, exit reason, emotional state at entry, "
            "what the market did versus what was expected. "
            "Without a trading journal, you cannot learn from your mistakes or identify your edge."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: mandate trade logging for performance improvement"
        },
        "keywords": ["journal", "log", "entry reason", "discipline", "learn", "mistakes"],
    },
    {
        "id": "elder_emotions_enemy",
        "level": 2,
        "category": "psychology",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Psychology of Trading",
        "rule": (
            "Fear and greed are the two great destroyers of trading accounts. "
            "Fear causes premature exits and missed opportunities. "
            "Greed causes overtrading, over-leveraging, and holding losers too long. "
            "A mechanical system removes emotion from execution."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: mechanical execution eliminates fear and greed"
        },
        "keywords": ["fear", "greed", "emotion", "mechanical", "system", "discipline"],
    },
    {
        "id": "elder_revenge_trading_forbidden",
        "level": 2,
        "category": "psychology",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Psychology of Trading",
        "rule": (
            "After a loss, do not immediately try to 'win it back'. "
            "Revenge trading leads to larger losses and destroys risk management. "
            "Take a break, review what went wrong, and only re-enter with a clean analysis."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: no revenge trading; post-loss cooldown"
        },
        "keywords": ["revenge trading", "loss", "win back", "break", "psychological"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # STOP LOSS ET SORTIE — Elder sur la gestion des sorties
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_stop_below_last_minor_low",
        "level": 2,
        "category": "risk",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Setting Stops",
        "rule": (
            "For long positions, place the stop just below the last minor low (swing low). "
            "For short positions, place the stop just above the last minor high. "
            "This provides a logical technical level — if the stop is hit, the premise is wrong."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Stop placement logic: swing low/high relative to entry"
        },
        "keywords": ["stop", "minor low", "minor high", "swing", "technical level", "long", "short"],
    },
    {
        "id": "elder_trailing_stop_lock_profit",
        "level": 2,
        "category": "exit",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Exits and Trailing Stops",
        "rule": (
            "Once a position is profitable, use a trailing stop to lock in gains. "
            "Move the stop up (for longs) or down (for shorts) to just below the most recent "
            "minor low (longs) or above the most recent minor high (shorts). "
            "Never move a stop in the wrong direction — only trail it."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Trailing stop management for profitable positions"
        },
        "keywords": ["trailing stop", "lock in", "profit", "move stop", "winning position"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # TRADE PLANNING — Avant d'entrer
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "elder_3m_plan_before_trade",
        "level": 2,
        "category": "strategy",
        "book": "Vivre du Trading",
        "author": "Dr. Alexander Elder",
        "source_chapter": "Chapter - Come Into My Trading Room",
        "rule": (
            "Before placing any trade, define three key parameters: "
            "(1) Entry price — where and why, "
            "(2) Stop loss — maximum acceptable loss, "
            "(3) Target — where to take profit. "
            "If you cannot define all three, do not trade."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Mandatory: entry, stop, target must all be defined before position opening"
        },
        "keywords": ["plan", "entry", "stop", "target", "three parameters", "before trade"],
    },
]
