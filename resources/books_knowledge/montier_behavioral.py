"""
NexQuant — Knowledge Module: James Montier
===========================================
Livre : "The Little Book of Behavioral Investing" (2010)
Niveau : 2 — Systèmes (biais cognitifs, erreurs systématiques, contre-investissement)

Montier est un stratège chez GMO spécialisé dans les erreurs comportementales
des investisseurs. Ses règles permettent au bot d'identifier et de contrecarrer
les biais cognitifs qui détruisent la performance des traders.

Stratégies débloquées :
- CONTRARIAN_SIGNAL : détecter quand la foule est trop d'un côté (fade the crowd)
- BEHAVIORAL_BIAS_PENALTY : pénaliser les entrées en zone de biais connu
- Filtre de sur-confiance (réduire la taille après une bonne série)
- Détection du "recency bias" (surpondération des données récentes)

Source : James Montier — The Little Book of Behavioral Investing
Publisher : Wiley, 2010
"""
from typing import List, Dict, Any

MONTIER_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # BIAIS DE CONFIRMATION — L'ennemi de l'analyse objective
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "montier_confirmation_bias",
        "level": 2,
        "category": "psychology",
        "book": "The Little Book of Behavioral Investing",
        "author": "James Montier",
        "source_chapter": "Chapter 1 - I'm Right, You're Wrong",
        "rule": (
            "Confirmation bias causes traders to seek information that confirms their existing view "
            "and ignore contradictory evidence. "
            "Before entering a trade, actively seek REASONS NOT TO ENTER. "
            "If you cannot find a strong bear case for a long trade, you may be biased. "
            "A mechanical system removes confirmation bias from the equation."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "BEHAVIORAL_BIAS_PENALTY: require systematic checklist to counter confirmation bias"
        },
        "keywords": ["confirmation bias", "seek contrary", "mechanical", "ignore evidence"],
    },
    {
        "id": "montier_overconfidence_size",
        "level": 2,
        "category": "risk",
        "book": "The Little Book of Behavioral Investing",
        "author": "James Montier",
        "source_chapter": "Chapter 2 - Overconfidence",
        "rule": (
            "After a string of winning trades, overconfidence leads to oversizing. "
            "Studies show traders increase position sizes by 30-50% after win streaks, "
            "right before a mean-reversion loss. "
            "After 5+ consecutive wins, reduce position size by 25% as a precaution."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "After win streak (5+), reduce kelly_fraction by 25% against overconfidence"
        },
        "keywords": ["overconfidence", "win streak", "oversizing", "reduce", "mean reversion"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPORTEMENT DE FOULE — Contre-investissement systématique
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "montier_contrarian_extremes",
        "level": 2,
        "category": "signal",
        "book": "The Little Book of Behavioral Investing",
        "author": "James Montier",
        "source_chapter": "Chapter 5 - Running with the Crowd",
        "rule": (
            "When market sentiment reaches extreme consensus (everyone is bullish or bearish), "
            "the contrarian trade has the highest probability. "
            "Fear/Greed index extremes, VIX spikes, or RSI at multi-month extremes signal "
            "that the crowd is positioned heavily on one side — fade the crowd. "
            "Contrarian signals should only be acted upon with multiple confirming indicators."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "CONTRARIAN_SIGNAL: extreme sentiment = crowd fade opportunity"
        },
        "keywords": ["contrarian", "extreme", "consensus", "fade the crowd", "sentiment", "fear greed"],
    },
    {
        "id": "montier_herding_danger",
        "level": 2,
        "category": "filter",
        "book": "The Little Book of Behavioral Investing",
        "author": "James Montier",
        "source_chapter": "Chapter 5 - Running with the Crowd",
        "rule": (
            "Herding — following the crowd without independent analysis — leads to bubbles "
            "and subsequent crashes. "
            "If a trade is 'obvious' to everyone (widely discussed on social media, news), "
            "it is likely already priced in and potentially dangerous. "
            "The best trades are usually uncomfortable and counter-consensus."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": -0.5,
            "description": "Penalize trades that chase widely-publicized consensus momentum"
        },
        "keywords": ["herding", "crowd", "bubble", "obvious", "social media", "priced in"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # RECENCY BIAS — Sur-pondération du passé récent
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "montier_recency_bias",
        "level": 2,
        "category": "psychology",
        "book": "The Little Book of Behavioral Investing",
        "author": "James Montier",
        "source_chapter": "Chapter 3 - Act in Haste, Repent at Leisure",
        "rule": (
            "Recency bias causes traders to give disproportionate weight to recent events. "
            "After a big move, traders assume the trend will continue indefinitely. "
            "After a crash, they assume markets will continue falling. "
            "Base rate analysis (what usually happens after similar situations historically) "
            "is more reliable than intuition based on recent events."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "BEHAVIORAL_BIAS_PENALTY: recency bias check via historical base rate"
        },
        "keywords": ["recency bias", "recent events", "base rate", "historical", "intuition"],
    },
    {
        "id": "montier_loss_aversion",
        "level": 2,
        "category": "psychology",
        "book": "The Little Book of Behavioral Investing",
        "author": "James Montier",
        "source_chapter": "Chapter 4 - Why Can't We Accept Losses?",
        "rule": (
            "Loss aversion causes traders to hold losing positions too long (hoping for recovery) "
            "and cut winning positions too soon (fear of giving back gains). "
            "The solution is systematic, pre-defined exits based on price, not emotion. "
            "Never let a loss run beyond your predefined stop, regardless of conviction."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "ENFORCE_STRICT_SL: loss aversion override — mechanical stop execution"
        },
        "keywords": ["loss aversion", "hold losers", "cut winners", "hope", "mechanical", "stop"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # DISCIPLINE SYSTÉMATIQUE — La solution aux biais
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "montier_rules_based_system",
        "level": 2,
        "category": "strategy",
        "book": "The Little Book of Behavioral Investing",
        "author": "James Montier",
        "source_chapter": "Chapter 10 - The Art of Valuation",
        "rule": (
            "A rules-based system removes the biggest risk in investing: yourself. "
            "The system doesn't get overconfident, scared, or bored. "
            "Every variable in the decision process should be defined BEFORE encountering "
            "the situation. If it's not in the rules, you don't do it."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Rules-based execution: only trade what matches pre-defined criteria"
        },
        "keywords": ["rules-based", "mechanical", "system", "remove bias", "pre-defined"],
    },
    {
        "id": "montier_valuation_anchor",
        "level": 2,
        "category": "signal",
        "book": "The Little Book of Behavioral Investing",
        "author": "James Montier",
        "source_chapter": "Chapter 10 - The Art of Valuation",
        "rule": (
            "Anchoring bias: traders fixate on an arbitrary reference price (their entry, 52-week high) "
            "and make decisions relative to it rather than current fair value. "
            "The market doesn't know or care about your cost basis. "
            "Evaluate each trade as if entering fresh, ignoring sunk costs."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "BEHAVIORAL_BIAS_PENALTY: evaluate fresh, ignore anchoring to entry price"
        },
        "keywords": ["anchoring", "entry price", "cost basis", "sunk cost", "fresh evaluation"],
    },
]
