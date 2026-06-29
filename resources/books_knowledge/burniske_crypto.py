"""
NexQuant — Knowledge Module: Chris Burniske + Crypto Fundamentals
==================================================================
Livres :
  - "Cryptoassets: The Innovative Investor's Guide" — Burniske & Tatar (2017)
  - "Crypto Investing for Beginners" — James Bruwer (2021)
Niveau : 2 — Systèmes (valorisation crypto, métriques on-chain, régimes crypto)

Burniske apporte des frameworks de valorisation fondamentale pour les cryptoassets,
distinguant les différentes classes d'actifs crypto et leurs métriques propres.
Bruwer complète avec les bases du cycle crypto et la gestion des positions.

Stratégies débloquées :
- CRYPTO_FUNDAMENTAL_FILTER : filtre on-chain (NVT, network activity)
- Régime crypto (bull/bear market macro) comme contexte directionnel
- Cycle de halving Bitcoin comme signal saisonnier
- Divergence volume/prix dans le contexte crypto

Source : Chris Burniske & Jack Tatar — Cryptoassets (Wiley, 2017)
         James Bruwer — Crypto Investing for Beginners (2021)
"""
from typing import List, Dict, Any

CRYPTO_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # VALORISATION CRYPTO — Métriques fondamentales
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "burniske_nvt_ratio",
        "level": 2,
        "category": "signal",
        "book": "Cryptoassets",
        "author": "Chris Burniske",
        "source_chapter": "Chapter 9 - Cryptoasset Valuation",
        "rule": (
            "The NVT Ratio (Network Value to Transactions) is the crypto equivalent of P/E ratio. "
            "NVT = Market Cap / Daily Transaction Volume on-chain. "
            "NVT > 95 (90th percentile) signals overvaluation — avoid longs, consider shorts. "
            "NVT < 25 (10th percentile) signals undervaluation — favorable for longs."
        ),
        "confidence": 0.8,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "CRYPTO_FUNDAMENTAL_FILTER: NVT extreme signals over/undervaluation"
        },
        "keywords": ["NVT", "network value", "transactions", "valuation", "on-chain", "P/E"],
    },
    {
        "id": "burniske_metcalfe_law",
        "level": 2,
        "category": "signal",
        "book": "Cryptoassets",
        "author": "Chris Burniske",
        "source_chapter": "Chapter 9 - Cryptoasset Valuation",
        "rule": (
            "Metcalfe's Law: network value grows proportionally to the square of active users. "
            "If active addresses grow 10%, fair value grows ~20%. "
            "Price diverging significantly above Metcalfe-implied value (>3x) signals speculation. "
            "Price significantly below Metcalfe value signals opportunity."
        ),
        "confidence": 0.75,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Metcalfe Law: active user growth vs price divergence as fundamental signal"
        },
        "keywords": ["Metcalfe", "network", "active users", "addresses", "speculation"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CYCLES CRYPTO — Bitcoin halving et cycles de marché
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "burniske_bitcoin_halving_cycle",
        "level": 2,
        "category": "strategy",
        "book": "Cryptoassets",
        "author": "Chris Burniske",
        "source_chapter": "Chapter 6 - Bitcoin's Historical Performance",
        "rule": (
            "Bitcoin's 4-year halving cycle historically creates predictable bull/bear phases: "
            "Year 1 after halving: accumulation and early bull run. "
            "Year 2: acceleration of bull market. "
            "Year 3: peak and beginning of bear market. "
            "Year 4: deep bear and accumulation before next halving. "
            "Use this macro context to bias long vs short directional exposure."
        ),
        "confidence": 0.75,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Bitcoin halving cycle provides macro directional bias for crypto assets"
        },
        "keywords": ["halving", "cycle", "4 year", "bull market", "bear market", "accumulation"],
    },
    {
        "id": "burniske_crypto_correlation",
        "level": 2,
        "category": "risk",
        "book": "Cryptoassets",
        "author": "Chris Burniske",
        "source_chapter": "Chapter 11 - Portfolio Construction",
        "rule": (
            "Crypto assets are highly correlated during market stress. "
            "In a crypto bear market, altcoins fall faster than Bitcoin (beta > 1). "
            "Do not treat different crypto positions as uncorrelated. "
            "Reduce all crypto exposure simultaneously when BTC shows macro weakness (below 200W MA)."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": 0.0,
            "description": "Crypto correlation risk: high-beta altcoins need reduced sizing in bear markets"
        },
        "keywords": ["correlation", "altcoins", "beta", "bear market", "bitcoin", "reduce"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # GESTION CRYPTO — Règles spécifiques aux marchés 24/7
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "bruwer_crypto_24h_risk",
        "level": 2,
        "category": "risk",
        "book": "Crypto Investing for Beginners",
        "author": "James Bruwer",
        "source_chapter": "Chapter - Risk Management in Crypto",
        "rule": (
            "Crypto markets run 24/7 — gaps and extreme overnight moves are common. "
            "Position sizing must account for the inability to exit during weekends or low-liquidity hours. "
            "Reduce crypto position sizes by 20-30% versus equivalent positions in traditional markets. "
            "Never hold oversized crypto positions over major macroeconomic events."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Crypto 24/7 risk: reduce sizing by 20-30% for weekend/overnight exposure"
        },
        "keywords": ["24/7", "overnight", "weekend", "gap", "crypto", "reduce", "position size"],
    },
    {
        "id": "bruwer_dont_chase_pumps",
        "level": 2,
        "category": "filter",
        "book": "Crypto Investing for Beginners",
        "author": "James Bruwer",
        "source_chapter": "Chapter - Common Crypto Mistakes",
        "rule": (
            "Never chase a pump: when an asset has already moved 20-50%+ in 24 hours, "
            "the risk of a sharp reversal ('dump the pump') is very high. "
            "Wait for consolidation and a re-test of a key level before entering. "
            "FOMO is the biggest destroyer of crypto trading accounts."
        ),
        "confidence": 0.95,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": True,
            "score_weight": -1.0,
            "description": "Pump-chasing filter: penalize entries after extreme 24h moves"
        },
        "keywords": ["pump", "FOMO", "chase", "50%", "dump", "reversal", "24 hours"],
    },
    {
        "id": "burniske_bitcoin_dominance",
        "level": 2,
        "category": "strategy",
        "book": "Cryptoassets",
        "author": "Chris Burniske",
        "source_chapter": "Chapter 11 - Portfolio Construction",
        "rule": (
            "Bitcoin Dominance (BTC.D) is the ratio of Bitcoin market cap to total crypto market cap. "
            "Rising BTC.D = flight to safety, altcoins underperform. "
            "Falling BTC.D = risk-on altcoin season, altcoins outperform BTC. "
            "Use BTC.D trend as a sector rotation signal within crypto markets."
        ),
        "confidence": 0.8,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Bitcoin dominance trend = altcoin vs BTC allocation signal"
        },
        "keywords": ["bitcoin dominance", "BTC.D", "altcoin season", "flight to safety", "rotation"],
    },
    {
        "id": "burniske_on_chain_activity",
        "level": 2,
        "category": "signal",
        "book": "Cryptoassets",
        "author": "Chris Burniske",
        "source_chapter": "Chapter 9 - Cryptoasset Valuation",
        "rule": (
            "On-chain activity (active addresses, transactions per day, hash rate) "
            "provides a leading indicator of price direction. "
            "Rising on-chain activity with flat price = accumulation (bullish). "
            "Falling on-chain activity with rising price = distribution (bearish divergence). "
            "Price should confirm on-chain fundamental trends."
        ),
        "confidence": 0.8,
        "applicable_regimes": ["TRENDING", "RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "CRYPTO_FUNDAMENTAL_FILTER: on-chain activity divergence as leading indicator"
        },
        "keywords": ["on-chain", "active addresses", "transactions", "hash rate", "accumulation", "distribution"],
    },
]
