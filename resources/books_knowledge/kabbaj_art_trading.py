"""
NexQuant — Knowledge Module: Thami Kabbaj
==========================================
Livre : "L'Art du Trading" (2010, édition mise à jour)
Niveau : 1/2 — Fondations + Systèmes (approche hybride price action + quantitatif)

Kabbaj est la référence francophone du trading. Ses règles combinent :
- La lecture du price action (niveau 1, complète Murphy)
- Le sizing Kelly fractionnel (niveau 2, complémente Elder)
- La rotation sectorielle comme filtre macro (niveau 2)

Stratégies débloquées :
- Squeeze Breakout : compression Bollinger → explosion directionnelle
- Kelly 25% : sizing conservateur validé empiriquement
- Ichimoku comme filtre de tendance HTF
- Rotation sectorielle pour détecter les flux institutionnels

Source : Thami Kabbaj — L'Art du Trading
Publisher : Eyrolles, 2010 (FR)
"""
from typing import List, Dict, Any

KABBAJ_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # KELLY FRACTIONNEL — La signature de Kabbaj
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "kabbaj_kelly_25pct",
        "level": 2,
        "category": "sizing",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Gestion du Capital",
        "rule": (
            "Use only 25% of the full Kelly fraction (quarter-Kelly). "
            "While half-Kelly (Chan) is theoretically optimal, the quarter-Kelly "
            "provides even more protection against parameter estimation errors and "
            "behavioral biases in live trading. "
            "f_applied = 0.25 * f_full_kelly."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "CAP_KELLY: Kabbaj recommends quarter-Kelly (0.25) as applied fraction"
        },
        "keywords": ["kelly", "25%", "quarter kelly", "capital management", "fraction"],
    },
    {
        "id": "kabbaj_rr_minimum_2to1",
        "level": 1,
        "category": "risk",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Gestion des Risques",
        "rule": (
            "Minimum reward-to-risk ratio of 2:1 on every trade entry. "
            "If the nearest logical stop is so far that the target cannot be at least "
            "2x the stop distance, skip the trade. "
            "Kabbaj's minimum is 2:1 vs Murphy's 3:1 — use 2:1 as floor, target 3:1."
        ),
        "confidence": 0.95,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Minimum R:R filter: 2:1 absolute floor before entry"
        },
        "keywords": ["reward", "risk", "2:1", "ratio", "minimum", "target"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # SQUEEZE BREAKOUT — La stratégie signature de Kabbaj
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "kabbaj_squeeze_breakout",
        "level": 1,
        "category": "signal",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Stratégies de Breakout",
        "rule": (
            "The Squeeze Breakout: Bollinger Bands narrow to their minimum width (squeeze), "
            "price compresses. The directional breakout occurs when price closes clearly "
            "outside the Bollinger Bands after the squeeze. "
            "Confirm with increasing volume on the breakout bar. "
            "Enter on the close of the first bar breaking the band."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 2.0,
            "description": "Squeeze breakout from BB narrow = Kabbaj signature setup; VOLATILITY_BREAKOUT"
        },
        "keywords": ["squeeze", "bollinger", "breakout", "narrow", "width", "close outside"],
    },
    {
        "id": "kabbaj_partial_tp1",
        "level": 2,
        "category": "exit",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Gestion des Positions",
        "rule": (
            "At the first target (TP1): exit 50% of the position. "
            "Move the stop-loss to the entry price (breakeven) on the remaining 50%. "
            "Let the rest run toward TP2 with a trailing stop. "
            "This two-stage exit eliminates risk while maximizing upside on winners."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "50% exit at TP1, breakeven stop on remainder, trailing for TP2"
        },
        "keywords": ["partial", "TP1", "50%", "breakeven", "trailing", "two-stage"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # PRICE ACTION — Kabbaj sur les patterns de chandeliers
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "kabbaj_pin_bar_reversal",
        "level": 1,
        "category": "signal",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Price Action",
        "rule": (
            "A Pin Bar (long shadow, small body) at a key level is a powerful reversal signal. "
            "Bullish Pin Bar: long lower shadow at support — price rejected lower prices. "
            "Bearish Pin Bar: long upper shadow at resistance — price rejected higher prices. "
            "The longer the shadow relative to the body, the stronger the rejection."
        ),
        "confidence": 0.95,
        "applicable_regimes": ["TRENDING", "RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.5,
            "description": "Pin Bar at key level = strong rejection signal, high probability"
        },
        "keywords": ["pin bar", "shadow", "body", "rejection", "reversal", "support", "resistance"],
    },
    {
        "id": "kabbaj_engulfing_confirmation",
        "level": 1,
        "category": "signal",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Price Action",
        "rule": (
            "An engulfing pattern carries more weight when it occurs at a key structure level "
            "AND is accompanied by above-average volume. "
            "A bullish engulfing at support on high volume confirms institutional buying. "
            "Always require volume confirmation for candlestick patterns."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["TRENDING", "RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "Volume-confirmed engulfing at structure = institutional confirmation"
        },
        "keywords": ["engulfing", "volume", "institutional", "confirmation", "structure"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ICHIMOKU — Filtre de tendance HTF
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "kabbaj_ichimoku_cloud_filter",
        "level": 2,
        "category": "filter",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Ichimoku",
        "rule": (
            "Use the Ichimoku cloud as a trend filter on higher timeframes: "
            "Price above the cloud → bullish bias, only take longs. "
            "Price below the cloud → bearish bias, only take shorts. "
            "Price inside the cloud → uncertain, reduce position size or avoid. "
            "The cloud provides dynamic support/resistance with a 26-period lookahead."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 1.0,
            "description": "Ichimoku cloud HTF filter: price below cloud penalizes long signals"
        },
        "keywords": ["ichimoku", "cloud", "above", "below", "bias", "filter", "higher timeframe"],
    },
    {
        "id": "kabbaj_ichimoku_tk_cross",
        "level": 2,
        "category": "signal",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Ichimoku",
        "rule": (
            "The Tenkan/Kijun cross (TK Cross) above the cloud is a strong bullish signal. "
            "Tenkan crossing above Kijun above the cloud = strong buy. "
            "Tenkan crossing below Kijun below the cloud = strong sell. "
            "Crosses inside the cloud are weak and should be avoided."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "Ichimoku TK Cross above/below cloud = directional confirmation"
        },
        "keywords": ["tenkan", "kijun", "TK cross", "ichimoku", "above cloud", "below cloud"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ROTATION SECTORIELLE — Macro comme filtre de direction
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "kabbaj_sector_rotation",
        "level": 2,
        "category": "strategy",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Analyse Inter-Marchés",
        "rule": (
            "Follow capital rotation between sectors to anticipate trend changes. "
            "When money flows from defensive sectors (utilities, healthcare) to cyclicals "
            "(tech, financials), the market is in a risk-on regime. "
            "Align individual trades with the prevailing sector rotation direction. "
            "Risk-on favors breakouts; risk-off favors mean-reversion."
        ),
        "confidence": 0.8,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Sector rotation as macro bias: risk-on boosts trending score"
        },
        "keywords": ["sector rotation", "capital flows", "risk-on", "risk-off", "cyclicals"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # PSYCHOLOGIE — Kabbaj sur la discipline
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "kabbaj_trading_is_psychology",
        "level": 2,
        "category": "psychology",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Psychologie du Trader",
        "rule": (
            "Trading is 90% psychology, 10% technique. "
            "A trader with average strategies but excellent discipline and emotional control "
            "will outperform a brilliant analyst who cannot control their emotions. "
            "Consistency in execution is more important than finding the perfect system."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: consistency in execution trumps system quality"
        },
        "keywords": ["psychology", "90%", "discipline", "consistency", "execution"],
    },
    {
        "id": "kabbaj_pre_trade_checklist",
        "level": 2,
        "category": "strategy",
        "book": "L'Art du Trading",
        "author": "Thami Kabbaj",
        "source_chapter": "Chapitre - Plan de Trading",
        "rule": (
            "Before every trade, run a pre-trade checklist: "
            "(1) Is the trend direction confirmed on higher timeframe? "
            "(2) Is there a valid price action setup at a key level? "
            "(3) Is the R:R at least 2:1? "
            "(4) Is position size within Kelly quarter-fraction? "
            "If any answer is NO, do not trade."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "4-point pre-trade checklist: HTF trend + setup + R:R + sizing"
        },
        "keywords": ["checklist", "pre-trade", "4 points", "trend", "setup", "R:R", "sizing"],
    },
]
