"""
NexQuant — Knowledge Module: Brett N. Steenbarger
==================================================
Livre : "Trading Psychology 2.0" (2015)
Niveau : 2 — Systèmes (psychologie de la performance, coaching, métriques comportementales)

Steenbarger est un psychologue clinicien qui coache des traders professionnels.
Ses règles apportent une dimension unique : mesurer et gérer la PERFORMANCE
du trader lui-même, pas seulement la performance du système.

Stratégies débloquées :
- Performance tracking comportemental (win/loss streaks → taille)
- Détection des états de flow vs. d'anxiété (réduction de taille)
- Métriques de qualité d'exécution (slippage comportemental)
- Circuit breaker psychologique personnalisé

Source : Brett N. Steenbarger — Trading Psychology 2.0
Publisher : Wiley, 2015
"""
from typing import List, Dict, Any

STEENBARGER_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # PERFORMANCE METRICS — Mesurer pour améliorer
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "steenbarger_process_metrics",
        "level": 2,
        "category": "performance",
        "book": "Trading Psychology 2.0",
        "author": "Brett N. Steenbarger",
        "source_chapter": "Chapter 1 - Developing Best Practices",
        "rule": (
            "Track process metrics, not just P&L: "
            "Entry timing quality (how close to intended entry), "
            "stop adherence rate (% trades where stop was respected), "
            "plan adherence (% trades matching pre-defined criteria). "
            "A high-quality process precedes consistent P&L results."
        ),
        "confidence": 0.95,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Track process quality metrics: stop adherence, plan adherence"
        },
        "keywords": ["process metrics", "P&L", "entry timing", "stop adherence", "quality"],
    },
    {
        "id": "steenbarger_consecutive_losses",
        "level": 2,
        "category": "risk",
        "book": "Trading Psychology 2.0",
        "author": "Brett N. Steenbarger",
        "source_chapter": "Chapter 2 - Building on Strengths",
        "rule": (
            "After 3 consecutive losses, reduce position size by 50%. "
            "After 5 consecutive losses, stop trading and review. "
            "Loss streaks indicate either market regime change or degraded execution quality. "
            "Halving size during a losing streak prevents account destruction."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "LOSING_STREAK_PROTECTION: after 3 consecutive losses, halve position size"
        },
        "keywords": ["consecutive losses", "3 losses", "reduce size", "losing streak", "review"],
    },
    {
        "id": "steenbarger_win_rate_context",
        "level": 2,
        "category": "performance",
        "book": "Trading Psychology 2.0",
        "author": "Brett N. Steenbarger",
        "source_chapter": "Chapter 3 - Radical Acceptance",
        "rule": (
            "Win rate alone is meaningless without knowing the average win/loss ratio. "
            "A 40% win rate with 3:1 reward-risk has higher expectancy than a 60% win rate "
            "with 1:1 reward-risk. "
            "Always evaluate system quality using expectancy = (WR * avg_win) - (LR * avg_loss)."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Expectancy = (WR * avg_win) - (LR * avg_loss) > 0 required"
        },
        "keywords": ["win rate", "expectancy", "reward risk", "average win", "average loss"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTATS PSYCHOLOGIQUES — Détecter et corriger
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "steenbarger_flow_state",
        "level": 2,
        "category": "psychology",
        "book": "Trading Psychology 2.0",
        "author": "Brett N. Steenbarger",
        "source_chapter": "Chapter 4 - Cultivating Flow",
        "rule": (
            "The flow state (optimal performance) occurs when challenge matches skill level. "
            "Trade at a position size where losses don't cause emotional distress. "
            "If a potential loss would significantly affect your emotional state, "
            "the position is too large — reduce to a 'sleep at night' size."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: position size must allow flow state — emotional comfort"
        },
        "keywords": ["flow state", "challenge", "skill", "emotional", "sleep at night", "size"],
    },
    {
        "id": "steenbarger_overtrading_signal",
        "level": 2,
        "category": "risk",
        "book": "Trading Psychology 2.0",
        "author": "Brett N. Steenbarger",
        "source_chapter": "Chapter 5 - Overcoming Weaknesses",
        "rule": (
            "Overtrading is a psychological symptom, not a strategy. "
            "Signs of overtrading: taking trades outside your defined criteria, "
            "increasing size after losses, feeling compelled to 'be in the market'. "
            "When detected, immediately reduce to minimum size until the urge passes."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Overtrading detection: flag high trade frequency as psychological symptom"
        },
        "keywords": ["overtrading", "compelled", "criteria", "urge", "size", "psychological"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ADAPTATION — Steenbarger sur l'évolution continue
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "steenbarger_market_regime_adaptation",
        "level": 2,
        "category": "strategy",
        "book": "Trading Psychology 2.0",
        "author": "Brett N. Steenbarger",
        "source_chapter": "Chapter 6 - Adapting to Market Cycles",
        "rule": (
            "Markets evolve — strategies that worked in trending conditions fail in ranging ones. "
            "The elite trader's edge is the ability to recognize regime changes early and adapt. "
            "Keep a running score of current strategy performance: if win rate drops below "
            "statistical expectation for 20+ trades, pause and reassess the strategy."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Regime adaptation: detect strategy degradation via rolling win rate"
        },
        "keywords": ["market regime", "adaptation", "evolve", "win rate drop", "reassess"],
    },
    {
        "id": "steenbarger_deliberate_practice",
        "level": 2,
        "category": "psychology",
        "book": "Trading Psychology 2.0",
        "author": "Brett N. Steenbarger",
        "source_chapter": "Chapter 7 - The Developing Trader",
        "rule": (
            "Deliberate practice — not mere repetition — creates expertise. "
            "Review every trade: what was the plan, what happened, what would you do differently. "
            "The trader who reviews 1000 trades with intent learns faster than one who "
            "takes 10,000 trades without reflection."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "PSYCHOLOGY_FLAG: deliberate practice — systematic trade review"
        },
        "keywords": ["deliberate practice", "review", "reflection", "expertise", "plan"],
    },
]
