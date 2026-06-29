"""
NexQuant — Knowledge Module: Contrarian Trading + Behavioral Contra-signals
============================================================================
Livres :
  - "Contrarian Trading for Forex/Stock/Crypto" — T.D.C. Jamie (2023)
  - "The Hacking of the American Mind" — Robert Lustig (2017)
Niveau : 2 — Systèmes (contre-tendance disciplinée, psychologie des marchés)

Jamie détaille les conditions précises pour trader contre le consensus avec un
avantage statistique. Lustig apporte la psychologie de la dopamine et de comment
les marchés exploitent les biais cognitifs des participants.

Stratégies débloquées :
- Contrarian entry en zone d'euphorie/panique extrême (nécessite multiple confirmations)
- Détection des conditions de capitulation (high volume + doji/hammer)
- Sentiment extrême comme signal de retournement
- Protection contre les décisions dopaminergiques (FOMO trading)

Source : T.D.C. Jamie — Contrarian Trading (2023)
         Robert Lustig — The Hacking of the American Mind (Harper Collins, 2017)
"""
from typing import List, Dict, Any

CONTRARIAN_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # TRADING CONTRARIAN — Conditions d'entrée précises
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "contrarian_extreme_rsi",
        "level": 2,
        "category": "signal",
        "book": "Contrarian Trading",
        "author": "T.D.C. Jamie",
        "source_chapter": "Chapter 3 - Identifying Extremes",
        "rule": (
            "A contrarian long entry requires ALL of: "
            "(1) RSI below 20 (extreme oversold), "
            "(2) Bullish divergence (price lower low, RSI higher low), "
            "(3) Volume spike on the last down bar (capitulation), "
            "(4) Bullish reversal candlestick (hammer, engulfing). "
            "One signal alone is NOT contrarian — it's gamble. All four confirm capitulation."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 2.0,
            "description": "CONTRARIAN_SIGNAL: RSI<20 + divergence + volume spike + candle = capitulation long"
        },
        "keywords": ["contrarian", "RSI 20", "oversold", "divergence", "capitulation", "volume spike"],
    },
    {
        "id": "contrarian_extreme_rsi_short",
        "level": 2,
        "category": "signal",
        "book": "Contrarian Trading",
        "author": "T.D.C. Jamie",
        "source_chapter": "Chapter 3 - Identifying Extremes",
        "rule": (
            "A contrarian short entry requires ALL of: "
            "(1) RSI above 80 (extreme overbought), "
            "(2) Bearish divergence (price higher high, RSI lower high), "
            "(3) Volume spike on the last up bar (exhaustion), "
            "(4) Bearish reversal candlestick (shooting star, bearish engulfing). "
            "These four conditions together confirm euphoria and exhaustion."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 2.0,
            "description": "CONTRARIAN_SIGNAL: RSI>80 + divergence + volume spike + candle = euphoria short"
        },
        "keywords": ["contrarian", "RSI 80", "overbought", "divergence", "exhaustion", "euphoria"],
    },
    {
        "id": "contrarian_never_in_trend",
        "level": 2,
        "category": "filter",
        "book": "Contrarian Trading",
        "author": "T.D.C. Jamie",
        "source_chapter": "Chapter 2 - When NOT to be Contrarian",
        "rule": (
            "Never use contrarian signals in strongly trending markets (ADX > 35). "
            "Strong trends can sustain 'overbought' conditions for weeks or months. "
            "Contrarian strategies only work in RANGING (low ADX < 22) markets. "
            "A contrarian trade in a strong trend is the fastest way to blow an account."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": True,
            "score_weight": -2.0,
            "description": "PENALTY_COUNTER_TREND: contrarian signals in trending market = severe penalty"
        },
        "keywords": ["contrarian", "trending market", "ADX 35", "ranging", "overbought trend"],
    },
    {
        "id": "contrarian_multiple_timeframe_confirm",
        "level": 2,
        "category": "filter",
        "book": "Contrarian Trading",
        "author": "T.D.C. Jamie",
        "source_chapter": "Chapter 4 - Multi-Timeframe Contrarian",
        "rule": (
            "A contrarian setup needs confirmation on at least TWO timeframes: "
            "extreme conditions must be present on both the entry timeframe AND the next higher timeframe. "
            "A single-timeframe extreme is often noise; "
            "a two-timeframe extreme is a genuine sentiment extreme."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "ENFORCE_MULTI_TIMEFRAME: contrarian signals require 2-timeframe extreme"
        },
        "keywords": ["contrarian", "two timeframes", "extreme", "sentiment", "confirmation"],
    },
    {
        "id": "contrarian_position_sizing",
        "level": 2,
        "category": "sizing",
        "book": "Contrarian Trading",
        "author": "T.D.C. Jamie",
        "source_chapter": "Chapter 5 - Risk Management",
        "rule": (
            "Contrarian trades have lower win rates but higher R:R when they work. "
            "Size contrarian positions at 50% of normal size to account for lower win rate. "
            "Target minimum 4:1 R:R for contrarian setups (vs 2:1 for trend setups). "
            "The math: 30% win rate * 4R reward > breakeven."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Contrarian sizing: 50% of normal size, target 4:1 R:R minimum"
        },
        "keywords": ["contrarian", "sizing", "50%", "4:1", "R:R", "lower win rate"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # PSYCHOLOGIE DOPAMINERGIQUE — Lustig sur les décisions impulsives
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "lustig_dopamine_fomo",
        "level": 2,
        "category": "psychology",
        "book": "The Hacking of the American Mind",
        "author": "Robert Lustig",
        "source_chapter": "Chapter 4 - Reward and Pleasure",
        "rule": (
            "FOMO (Fear Of Missing Out) is a dopaminergic response — the same brain circuit "
            "as addiction. Like an addict chasing a high, traders in FOMO mode increase risk "
            "at exactly the wrong time. "
            "When you feel compelled to enter a trade immediately because of 'missing out', "
            "the correct action is to WAIT — dopamine is making the decision, not analysis."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: FOMO = dopamine trap, mandatory waiting period"
        },
        "keywords": ["FOMO", "dopamine", "addiction", "compelling", "compelled", "missing out"],
    },
    {
        "id": "lustig_serotonin_patience",
        "level": 2,
        "category": "psychology",
        "book": "The Hacking of the American Mind",
        "author": "Robert Lustig",
        "source_chapter": "Chapter 5 - Contentment vs Happiness",
        "rule": (
            "Serotonin (contentment/wellbeing) opposes dopamine (reward-seeking). "
            "The patient, disciplined trader who follows a plan operates from a serotonin state. "
            "The addicted, impulsive trader operates from a dopamine state. "
            "Develop routine, meditation, and systematic process to strengthen serotonin pathways "
            "and reduce impulsive trading decisions."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: serotonin discipline vs dopamine impulsivity in execution"
        },
        "keywords": ["serotonin", "dopamine", "patience", "discipline", "routine", "impulsive"],
    },
    {
        "id": "lustig_notification_detox",
        "level": 2,
        "category": "psychology",
        "book": "The Hacking of the American Mind",
        "author": "Robert Lustig",
        "source_chapter": "Chapter 9 - Digital Dopamine",
        "rule": (
            "Constant market notifications and price alerts create a dopamine feedback loop. "
            "Checking prices every 5 minutes reinforces anxiety and impulsive trading. "
            "Set specific trading review times and disable all non-critical alerts. "
            "A bot that makes decisions based on data, not notifications, is inherently superior."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: systematic review schedule, not notification-driven decisions"
        },
        "keywords": ["notifications", "alerts", "dopamine", "feedback loop", "anxiety", "schedule"],
    },
]
