"""
NexQuant — Knowledge Module: Bob Volman
========================================
Livre : "Forex Price Action Scalping" (2011)
Niveau : 1 — Fondations (price action pure, setups de scalping, lecture du flux)

Volman est le maître du price action pur — zéro indicateur, lecture directe
du carnet d'ordres via la bougie et l'EMA 25.
Ses règles enrichissent le niveau 1 de Murphy avec des setups d'entrée
de haute précision basés sur la structure du prix.

Stratégies débloquées :
- Setup "Break-Build-Break" (BB Break) : consolidation → push → re-break
- Setup "Double Doji Break" (DDB) : 2 dojis en squeeze → breakout directionnel
- Setup "Reversal Block" (RB) : prise de liquidité au-delà d'un niveau, retour
- Confirmation par la distance au EMA 25 (squeeze vs extension)

Source : Bob Volman — Forex Price Action Scalping
Publisher : Harriman House, 2011
"""
from typing import List, Dict, Any

VOLMAN_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # EMA 25 — L'axe central de Volman
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "volman_ema25_axis",
        "level": 1,
        "category": "filter",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 3 - The 25 EMA",
        "rule": (
            "The 25-period EMA is the central axis of the chart. "
            "Price above the 25 EMA favors long setups; price below favors short setups. "
            "Never initiate a long trade when price is significantly below the 25 EMA, "
            "and never go short when price is well above it."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["TRENDING", "RANGING"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 1.0,
            "description": "EMA25 axis determines bias; signals against EMA direction penalized"
        },
        "keywords": ["25 EMA", "axis", "central", "bias", "above", "below"],
    },
    {
        "id": "volman_double_bends",
        "level": 1,
        "category": "signal",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 5 - Pattern Recognition",
        "rule": (
            "A 'double bend' or 'triple tap' on the 25 EMA — price touches, bounces, "
            "touches again and bounces — creates a compressed spring effect. "
            "After 2-3 touches of the EMA without breaking it, a breakout setup forms. "
            "Enter on the first bar that closes clearly beyond the recent high/low after the taps."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["RANGING", "TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.5,
            "description": "Double bends on EMA25 = high probability setup; BONUS_EMA_SQUEEZE"
        },
        "keywords": ["double bends", "triple taps", "25 EMA", "bounce", "compressed", "spring"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # SETUPS CLÉS — Break-Build-Break, Squeeze, Reversal Block
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "volman_bb_break_setup",
        "level": 1,
        "category": "signal",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 6 - Setups",
        "rule": (
            "The Break-Build-Break (BB Break) setup: "
            "(1) Price breaks a significant level with momentum, "
            "(2) Consolidates tightly near the broken level (building), "
            "(3) Breaks out again in the same direction. "
            "The consolidation phase 'builds' orders before the second push. "
            "Enter on the second break close, not the first."
        ),
        "confidence": 0.95,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.5,
            "description": "BB Break setup: breakout + consolidation + re-break = high probability"
        },
        "keywords": ["break build break", "BB break", "consolidation", "second break", "momentum"],
    },
    {
        "id": "volman_squeeze_buildup",
        "level": 1,
        "category": "signal",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 6 - Setups",
        "rule": (
            "A 'squeeze' or 'build-up' forms when price compresses into a tight range "
            "against a significant horizontal support or resistance level. "
            "The longer the compression and the more bars involved, the more explosive the breakout. "
            "A build-up of 5+ bars against a level is a very high probability breakout signal."
        ),
        "confidence": 0.95,
        "applicable_regimes": ["RANGING", "TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.5,
            "description": "Price squeeze against S/R with 5+ bars = explosive breakout potential; BONUS_EMA_SQUEEZE"
        },
        "keywords": ["squeeze", "build-up", "compression", "horizontal level", "5 bars", "breakout"],
    },
    {
        "id": "volman_reversal_block",
        "level": 1,
        "category": "signal",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 7 - Reversal Patterns",
        "rule": (
            "The Reversal Block: price spikes beyond a key level (false break / stop hunt), "
            "then immediately reverses and closes back inside the range. "
            "The spike liquidates weak hands and traps breakout traders on the wrong side. "
            "Enter in the reverse direction as price recaptures the level."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["RANGING", "TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "False break / reversal block = trap detection, contrarian entry"
        },
        "keywords": ["reversal block", "false break", "stop hunt", "spike", "trap", "recapture"],
    },
    {
        "id": "volman_no_trade_zone",
        "level": 1,
        "category": "filter",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 4 - The No-Trade Zone",
        "rule": (
            "If price is in 'no man's land' — too far from both the EMA 25 and any significant "
            "level — there is no valid setup. Do not force trades. "
            "Wait for price to either return to the EMA or compress against a key level. "
            "The best trades come from clear, well-defined setups, not from chasing."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": -1.0,
            "description": "No-trade zone: reject entries when price is isolated from structure"
        },
        "keywords": ["no-trade zone", "no man's land", "wait", "force", "isolated", "structure"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # GESTION DES STOPS — Volman sur la précision des stops
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "volman_tight_stop",
        "level": 1,
        "category": "risk",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 8 - Targets and Stops",
        "rule": (
            "Scalping setups require tight, precise stop-losses placed just beyond the "
            "setup's defining structure (last swing, build-up boundary). "
            "A stop wider than 10-15 pips for a scalp negates the risk-reward. "
            "If the structure-based stop is too wide, skip the trade."
        ),
        "confidence": 0.95,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "ENFORCE_STRICT_SL: stop must be at structural level, reject if too wide"
        },
        "keywords": ["tight stop", "scalping", "pips", "structure", "stop loss", "boundary"],
    },
    {
        "id": "volman_partial_exit_buildup",
        "level": 1,
        "category": "exit",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 8 - Targets and Stops",
        "rule": (
            "For scalp trades, target the next significant level as the first take-profit. "
            "Exit 50-75% of the position at the first target, "
            "move stop to breakeven on the remainder. "
            "This approach locks in profit while leaving room for extended moves."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Partial exit: 50-75% at first target, move stop to breakeven"
        },
        "keywords": ["partial exit", "first target", "breakeven", "remainder", "scalp"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # LECTURE DU FLUX — Patience et sélectivité
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "volman_fewer_better_trades",
        "level": 1,
        "category": "psychology",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 2 - Trading Principles",
        "rule": (
            "Quality over quantity. Fewer, better-selected trades outperform high-frequency "
            "mediocre trades. A professional scalper may take only 1-3 setups per session. "
            "If no clear setup presents itself, the correct action is to wait — do nothing."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: selectivity — raise score_min if overtrading detected"
        },
        "keywords": ["fewer trades", "quality", "selectivity", "patience", "do nothing"],
    },
    {
        "id": "volman_session_awareness",
        "level": 1,
        "category": "filter",
        "book": "Forex Price Action Scalping",
        "author": "Bob Volman",
        "source_chapter": "Chapter 2 - Trading Principles",
        "rule": (
            "Avoid trading during low-liquidity periods: Asian session for forex, "
            "or outside primary market hours for crypto/stocks. "
            "Setups during low-volume sessions are prone to false breaks and erratic behavior. "
            "Best setups occur during high-volume overlapping sessions."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Session filter: penalize entries during low-liquidity periods"
        },
        "keywords": ["session", "liquidity", "Asian session", "low volume", "overlap", "hours"],
    },
]
