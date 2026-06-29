"""
NexQuant — Knowledge Module: Machine Learning for Algorithmic Trading
=====================================================================
Livres :
  - "Machine Learning for Algorithmic Trading" — Stefan Jansen (2020)
  - "Advanced Algos: Outsmarting the Market" — Bissette, Strauss, Van Der Post (2021)
  - "Algorithm Trading: Mastering The Use Of Computer Algorithms" — Koru (2022)
Niveau : 3 — Avancé (ML features, régimes par clustering, gestion ML-augmentée)

Ces livres apportent le niveau 3 quantitatif augmenté par le Machine Learning.
Les règles débloquent de nouvelles métriques de confiance et de filtrage basées
sur des modèles statistiques appris plutôt que des règles codées.

Stratégies débloquées :
- ML_CONFIDENCE_BOOST : utiliser la confiance d'un modèle ML comme pondération de score
- Feature engineering : créer des signaux composites (RFM, volatility regime)
- Clustering de régimes : HMM ou k-means pour identifier bull/bear/range
- Walk-forward optimization : valider les paramètres sur données roulantes

Source : Stefan Jansen — Machine Learning for Algorithmic Trading (Packt, 2020)
         Bissette, Strauss, Van Der Post — Advanced Algos (2021)
         Koru — Algorithm Trading (2022)
"""
from typing import List, Dict, Any

ML_RULES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # FEATURE ENGINEERING — Les signaux d'entrée du ML
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "ml_feature_composite_signal",
        "level": 3,
        "category": "signal",
        "book": "Machine Learning for Algorithmic Trading",
        "author": "Stefan Jansen",
        "source_chapter": "Chapter 4 - Financial Features",
        "rule": (
            "Composite signals that combine multiple weak indicators outperform single strong ones. "
            "Create a composite score from: momentum (3m return), mean reversion (Z-score of price), "
            "volatility (ATR percentile), and volume (OBV trend). "
            "A composite signal with all 4 components aligned in the same direction "
            "has statistically higher predictive power than any single component."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.5,
            "description": "ML_CONFIDENCE_BOOST: composite multi-factor signal adds to score"
        },
        "keywords": ["composite", "signal", "momentum", "Z-score", "ATR", "OBV", "multi-factor"],
    },
    {
        "id": "ml_volatility_regime_features",
        "level": 3,
        "category": "strategy",
        "book": "Machine Learning for Algorithmic Trading",
        "author": "Stefan Jansen",
        "source_chapter": "Chapter 5 - Engineered Features",
        "rule": (
            "Volatility regime features help ML models distinguish market conditions: "
            "ATR percentile (vs 52-week range): < 20% = low vol (mean reversion), "
            "> 80% = high vol (trending or crisis). "
            "Realized volatility vs implied volatility ratio: ratio < 0.8 = calm trend, "
            "ratio > 1.2 = turbulent, reduce position."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.5,
            "description": "Volatility percentile-based regime detection for strategy selection"
        },
        "keywords": ["volatility", "regime", "ATR percentile", "realized", "implied", "features"],
    },
    {
        "id": "ml_zscore_mean_reversion",
        "level": 3,
        "category": "signal",
        "book": "Machine Learning for Algorithmic Trading",
        "author": "Stefan Jansen",
        "source_chapter": "Chapter 7 - Time Series Strategies",
        "rule": (
            "The Z-score of price relative to its rolling mean is the most reliable "
            "mean-reversion trigger: Z = (price - rolling_mean) / rolling_std. "
            "Z > +2.0 = overbought, sell signal for mean reversion. "
            "Z < -2.0 = oversold, buy signal for mean reversion. "
            "Only valid in stationary markets (ADF confirmed) with Hurst < 0.5."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.5,
            "description": "Z-score ±2 sigma trigger for mean reversion in stationary markets"
        },
        "keywords": ["Z-score", "mean reversion", "rolling", "2 sigma", "stationary"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # RÉGIMES PAR CLUSTERING — Détection ML
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "ml_hidden_markov_regime",
        "level": 3,
        "category": "strategy",
        "book": "Machine Learning for Algorithmic Trading",
        "author": "Stefan Jansen",
        "source_chapter": "Chapter 16 - Unsupervised Learning",
        "rule": (
            "Hidden Markov Models (HMM) identify latent market regimes more accurately than "
            "simple ADX thresholds. Typical HMM states: "
            "State 0 = Low volatility trend (momentum strategies work), "
            "State 1 = High volatility trending (reduce size), "
            "State 2 = Mean-reverting range (range strategies work). "
            "Switch strategy based on current HMM state."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "ML_CONFIDENCE_BOOST: HMM regime detection improves strategy selection"
        },
        "keywords": ["HMM", "hidden markov", "regime", "state", "clustering", "latent"],
    },
    {
        "id": "ml_walk_forward_validation",
        "level": 3,
        "category": "strategy",
        "book": "Machine Learning for Algorithmic Trading",
        "author": "Stefan Jansen",
        "source_chapter": "Chapter 3 - Strategy Evaluation",
        "rule": (
            "Walk-forward optimization (WFO) prevents overfitting in ML strategies: "
            "Train on window T, test on T+1, roll forward. "
            "If the strategy's Sharpe degrades by > 30% from in-sample to OOS across "
            "multiple WFO periods, the model is overfit and should not be deployed. "
            "Minimum 5 walk-forward periods for statistical validity."
        ),
        "confidence": 1.0,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Walk-forward validation: minimum 5 periods, <30% Sharpe degradation"
        },
        "keywords": ["walk-forward", "WFO", "overfitting", "Sharpe degradation", "rolling"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ALGOS AVANCÉS — Bissette / Van Der Post
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "advanced_momentum_factor",
        "level": 3,
        "category": "signal",
        "book": "Advanced Algos",
        "author": "Bissette, Strauss, Van Der Post",
        "source_chapter": "Chapter - Momentum Factors",
        "rule": (
            "The momentum factor (12-month return, skipping last month) is the most robust "
            "quantitative anomaly. Assets with strong 12-month momentum tend to continue outperforming. "
            "Skip the last month to avoid short-term reversal (1-month reversal effect). "
            "Rebalance monthly to maintain factor exposure."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["TRENDING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "Momentum factor: 12M return (skip 1M) as signal, monthly rebalance"
        },
        "keywords": ["momentum factor", "12 month", "skip last month", "reversal", "rebalance"],
    },
    {
        "id": "advanced_mean_reversion_zscore",
        "level": 3,
        "category": "signal",
        "book": "Advanced Algos",
        "author": "Bissette, Strauss, Van Der Post",
        "source_chapter": "Chapter - Mean Reversion",
        "rule": (
            "For intraday mean reversion: use VWAP deviation as the trigger. "
            "Price > 2 std dev above VWAP → short, target VWAP return. "
            "Price > 2 std dev below VWAP → long, target VWAP return. "
            "VWAP mean reversion works best in stocks during regular trading hours "
            "and in crypto during the first 4-6 hours of the UTC day."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["RANGING"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 1.0,
            "description": "VWAP ±2 std as intraday mean reversion trigger"
        },
        "keywords": ["VWAP", "deviation", "intraday", "mean reversion", "2 std dev"],
    },
    {
        "id": "koru_execution_algo_twap",
        "level": 3,
        "category": "strategy",
        "book": "Algorithm Trading: Mastering The Use Of Computer Algorithms",
        "author": "Koru",
        "source_chapter": "Chapter - Execution Algorithms",
        "rule": (
            "For large orders, use Time-Weighted Average Price (TWAP) execution to minimize market impact. "
            "Split the order into equal slices across a defined time window. "
            "TWAP is preferred when urgency is low and minimizing slippage is prioritized. "
            "VWAP execution (volume-weighted) is preferred when market participation rate matters."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Large order execution: TWAP slicing to minimize market impact"
        },
        "keywords": ["TWAP", "execution", "large order", "slippage", "VWAP", "split"],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # GESTION ML — Confiance du modèle comme pondération
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "ml_model_confidence_sizing",
        "level": 3,
        "category": "sizing",
        "book": "Machine Learning for Algorithmic Trading",
        "author": "Stefan Jansen",
        "source_chapter": "Chapter 11 - Risk Management with ML",
        "rule": (
            "Scale position size proportionally to model confidence (predicted probability). "
            "P(signal) > 0.7: full position. P(signal) 0.6-0.7: 75% position. "
            "P(signal) 0.5-0.6: 50% position. P(signal) < 0.5: no trade. "
            "This translates model uncertainty directly into risk management."
        ),
        "confidence": 0.9,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "ML_CONFIDENCE_BOOST: scale position size by model probability"
        },
        "keywords": ["model confidence", "probability", "0.7", "position size", "uncertainty"],
    },
    {
        "id": "ml_feature_importance",
        "level": 3,
        "category": "strategy",
        "book": "Machine Learning for Algorithmic Trading",
        "author": "Stefan Jansen",
        "source_chapter": "Chapter 4 - Feature Engineering",
        "rule": (
            "Periodically evaluate which features are driving model predictions (SHAP values). "
            "If a model is primarily driven by a single feature (> 50% importance), "
            "it is fragile — rebuild with more diverse features. "
            "Feature importance changes over time — retrain models quarterly."
        ),
        "confidence": 0.85,
        "applicable_regimes": ["ALL"],
        "parameter_impact": {
            "filter": False,
            "score_weight": 0.0,
            "description": "Model robustness: diversify features, retrain quarterly, monitor SHAP"
        },
        "keywords": ["SHAP", "feature importance", "model", "fragile", "retrain", "quarterly"],
    },
]
