"""
NexQuant Books Knowledge — Package complet
==========================================
Intégration crescendo de 11 livres de trading sur 3 niveaux.

NIVEAU 1 — Fondations (lecture du marché)
  Murphy    : 24 règles — Analyse technique, tendances, S/R, volume
  Volman    : 10 règles — Price action pure, squeeze, EMA25, setups BB Break

NIVEAU 2 — Systèmes (structure du trading)
  Elder     : 20 règles — Triple Screen, Impulse, Iron Triangle 2%/6%
  Kabbaj    : 11 règles — Kelly 25%, squeeze BB, Ichimoku, pin bar
  Steenbarger: 7 règles — Psychologie performance, losing streaks
  Montier   :  8 règles — Biais comportementaux, contrarian
  Crypto    :  8 règles — NVT, halving, BTC.D, on-chain, 24/7
  Contrarian: 10 règles — RSI<20 4-confirmations, dopamine, Lustig

NIVEAU 3 — Quantitatif (optimisation mathématique)
  Chan      : 18 règles — Kelly, ADF, momentum lookback, fat tails
  ML Algo   : 11 règles — Composite signals, HMM, Z-score, walk-forward
  Python Algo: 10 règles — Bid-ask, saisonnalité, options, autocorrélation
"""

# ── Niveau 1 — Fondations ────────────────────────────────────────────────────
from .murphy_technical_analysis import MURPHY_RULES
from .volman_price_action import VOLMAN_RULES

# ── Niveau 2 — Systèmes ──────────────────────────────────────────────────────
from .elder_trading import ELDER_RULES
from .kabbaj_art_trading import KABBAJ_RULES
from .steenbarger_psychology import STEENBARGER_RULES
from .montier_behavioral import MONTIER_RULES
from .burniske_crypto import CRYPTO_RULES
from .contrarian_trading import CONTRARIAN_RULES

# ── Niveau 3 — Quantitatif ───────────────────────────────────────────────────
from .chan_algorithmic_trading import CHAN_RULES
from .ml_algo_trading import ML_RULES
from .python_algo_advanced import PYTHON_ALGO_RULES

# ── Aggregation complète (ordre crescendo) ───────────────────────────────────
ALL_BOOK_RULES = (
    # Niveau 1
    MURPHY_RULES
    + VOLMAN_RULES
    # Niveau 2
    + ELDER_RULES
    + KABBAJ_RULES
    + STEENBARGER_RULES
    + MONTIER_RULES
    + CRYPTO_RULES
    + CONTRARIAN_RULES
    # Niveau 3
    + CHAN_RULES
    + ML_RULES
    + PYTHON_ALGO_RULES
)

__all__ = [
    # Niveau 1
    "MURPHY_RULES",
    "VOLMAN_RULES",
    # Niveau 2
    "ELDER_RULES",
    "KABBAJ_RULES",
    "STEENBARGER_RULES",
    "MONTIER_RULES",
    "CRYPTO_RULES",
    "CONTRARIAN_RULES",
    # Niveau 3
    "CHAN_RULES",
    "ML_RULES",
    "PYTHON_ALGO_RULES",
    # Agrégation
    "ALL_BOOK_RULES",
]
