"""
NexQuant — Knowledge Module: Python Algorithmic Trading (Implémentation Avancée)
==================================================================================
Livres :
  - "Python for Algorithmic Trading Cookbook" — Jason Strimpel (2024)
  - "Algorithmic Trading Strategies: Most Profitable" — Scotty Ratford (2022)
  - "Algorithmic Trading Pro: Options Trading with Python" — L.J. Van Der Post (2023)
  - "Power Trader: Options Trading with Python" — L.J. Van Der Post (2024)
Niveau : 3 — Avancé (implémentation, stratégies multi-asset, options)

Ces livres apportent des stratégies concrètes prêtes à implémenter :
- Options Greeks comme hedges de portefeuille
- Scalping algorithmique avec des critères stricts de liquidité
- Détection de patterns via Python (autocorrelation, seasonality)
- Multi-asset momentum (cross-sectional)

Stratégies débloquées :
- Options Greeks hedging (Delta, Gamma exposure management)
- Seasonality patterns (day-of-week, month-of-year)
- Autocorrelation-based entry timing
- Liquidity-based position sizing (bid-ask spread filter)

Source : Jason Strimpel — Python for Algorithmic Trading Cookbook (O'Reilly, 2024)
         Scotty Ratford — Algorithmic Trading Strategies (2022)
         L.J. Van Der Post — Algorithmic Trading Pro + Power Trader (2023, 2024)
"""
from typing import List, Dict, Any

PYTHON_ALGO_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # LIQUIDITÉ — Filtre critique avant toute entrée
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "python_bid_ask_spread_filter",
        "level": 3,
        "category": "filter",
        "book": "Python for Algorithmic Trading Cookbook",
        "author": "Jason Strimpel",
        "source_chapter": "Chapter 3 - Execution and Order Management",
        "rule": (
            "The bid-ask spread is an immediate cost that must be factored into expected profit. "
            "Reject any trade where the spread exceeds 0.1% of the asset price for liquid assets, "
            "or 0.3% for less liquid assets. "
            "A wide spread signals low liquidity — your exits will be costly. "
            "Spread cost = spread / mid_price * 100 in basis points."
        ),
        "confidence": 0.95,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": -1.0,
            "description": "Liquidity filter: reject if bid-ask spread > 0.1% (liquid) or 0.3% (illiquid)"
        },
        "keywords": ["bid-ask", "spread", "liquidity", "0.1%", "cost", "reject", "filter"],
    },
    {
        "id": "python_order_book_depth",
        "level": 3,
        "category": "filter",
        "book": "Python for Algorithmic Trading Cookbook",
        "author": "Jason Strimpel",
        "source_chapter": "Chapter 3 - Execution and Order Management",
        "rule": (
            "Check order book depth before entry: ensure sufficient liquidity at your intended price. "
            "If your order size exceeds 10% of the best bid/ask quantity, "
            "expect significant slippage. Reduce size or use limit orders. "
            "For market orders, never exceed 1% of average daily volume in a single order."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Order book depth check: max 10% of best bid/ask, or use limit orders"
        },
        "keywords": ["order book", "depth", "slippage", "limit order", "daily volume"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # SAISONNALITÉ — Patterns temporels exploitables
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "ratford_dow_seasonality",
        "level": 3,
        "category": "signal",
        "book": "Algorithmic Trading Strategies",
        "author": "Scotty Ratford",
        "source_chapter": "Chapter - Seasonal Patterns",
        "rule": (
            "Day-of-week effects are statistically persistent: "
            "Monday: typically weakest day (weekend news digestion), slight negative bias. "
            "Tuesday-Wednesday: strongest days for continuation of prior week's trend. "
            "Friday: profit-taking before weekend, often reversal of Thursday's direction. "
            "Use this as a minor modifier: +0.3 on Tuesday/Wednesday, -0.3 on Monday/Friday."
        ),
        "confidence": 0.7,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.3,
            "description": "Day-of-week seasonality: minor score modifier based on statistical tendency"
        },
        "keywords": ["seasonality", "Monday", "Friday", "day of week", "calendar effect"],
    },
    {
        "id": "ratford_end_of_month_effect",
        "level": 3,
        "category": "signal",
        "book": "Algorithmic Trading Strategies",
        "author": "Scotty Ratford",
        "source_chapter": "Chapter - Seasonal Patterns",
        "rule": (
            "The turn-of-month effect: the last 2 trading days and first 3 trading days "
            "of each month have statistically higher average returns due to institutional "
            "fund flows and pension rebalancing. "
            "Slightly increase long bias during this window for equity assets."
        ),
        "confidence": 0.7,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.3,
            "description": "Turn-of-month: minor long bias boost during last 2 / first 3 trading days"
        },
        "keywords": ["end of month", "turn of month", "pension", "fund flows", "rebalancing"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # OPTIONS GREEKS — Hedging et sizing options-augmenté
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "vanderpost_delta_hedge",
        "level": 3,
        "category": "risk",
        "book": "Algorithmic Trading Pro: Options Trading with Python",
        "author": "L.J. Van Der Post",
        "source_chapter": "Chapter - Delta Hedging",
        "rule": (
            "Delta measures the directional exposure of an options portfolio. "
            "Net portfolio Delta > 1.5 = excessive directional bet, reduce by closing positions or hedging. "
            "For a delta-neutral approach: periodically rebalance to keep net delta near 0. "
            "Delta hedging eliminates directional risk but retains volatility exposure (Vega)."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Delta monitoring: excessive directional delta > 1.5 triggers size reduction"
        },
        "keywords": ["delta", "hedge", "options", "directional", "delta-neutral", "rebalance"],
    },
    {
        "id": "vanderpost_vega_vix_relationship",
        "level": 3,
        "category": "signal",
        "book": "Power Trader: Options Trading with Python",
        "author": "L.J. Van Der Post",
        "source_chapter": "Chapter - Volatility Trading",
        "rule": (
            "Vega-positive strategies (long options) profit from volatility expansion. "
            "When VIX is historically low (< 15), buying options (long Vega) is cheap. "
            "When VIX spikes above 30, selling options (short Vega) captures elevated premium. "
            "Map current VIX level to strategy preference: "
            "VIX < 15: buy vol. VIX 15-25: neutral. VIX > 25: sell vol."
        ),
        "confidence": 0.8,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "VIX-based volatility regime: low VIX favors long-vol, high VIX favors short-vol"
        },
        "keywords": ["vega", "VIX", "volatility", "long options", "short options", "premium"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTOCORRÉLATION — Timing basé sur les patterns statistiques
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "strimpel_autocorrelation_timing",
        "level": 3,
        "category": "signal",
        "book": "Python for Algorithmic Trading Cookbook",
        "author": "Jason Strimpel",
        "source_chapter": "Chapter 7 - Time Series Analysis",
        "rule": (
            "Positive autocorrelation (AR coefficient > 0) in returns indicates momentum: "
            "recent positive returns predict near-future positive returns. "
            "Negative autocorrelation (AR < 0) indicates mean reversion: "
            "recent positive returns predict near-future negative returns. "
            "Test autocorrelation at lag 1 and lag 5 for intraday patterns."
        ),
        "confidence": 0.8,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Autocorrelation test: positive AR = momentum strategy, negative AR = mean reversion"
        },
        "keywords": ["autocorrelation", "AR", "momentum", "mean reversion", "lag 1", "returns"],
    },
    {
        "id": "strimpel_portfolio_rebalancing",
        "level": 3,
        "category": "strategy",
        "book": "Python for Algorithmic Trading Cookbook",
        "author": "Jason Strimpel",
        "source_chapter": "Chapter 10 - Portfolio Construction",
        "rule": (
            "Systematic portfolio rebalancing captures mean-reversion between assets. "
            "Set rebalancing thresholds (5% drift from target) rather than calendar-based rebalancing. "
            "Threshold rebalancing reduces transaction costs while maintaining target allocation. "
            "Rebalance immediately when any position drifts more than 5% from target weight."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Portfolio rebalancing: 5% drift threshold triggers allocation adjustment"
        },
        "keywords": ["rebalancing", "5% drift", "threshold", "allocation", "target", "portfolio"],
    },
    {
        "id": "ratford_multiple_entry_scale_in",
        "level": 3,
        "category": "strategy",
        "book": "Algorithmic Trading Strategies",
        "author": "Scotty Ratford",
        "source_chapter": "Chapter - Entry Strategies",
        "rule": (
            "Scale-in entries reduce average entry price risk: "
            "Enter 50% at the initial signal, "
            "add 25% if price confirms with a new signal in the same direction, "
            "add final 25% only after the position is profitable. "
            "Never add to a losing position — averaging down is a destroyer of accounts."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Scale-in strategy: 50/25/25 split on confirmation, never average losers"
        },
        "keywords": ["scale in", "average", "confirm", "add to winner", "never average down"],
    },
]
