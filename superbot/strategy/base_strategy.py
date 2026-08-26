from __future__ import annotations
"""
NexQuant SuperBot — Interface BaseStrategy & SignalResult
==========================================================
Contrat standardisé pour toutes les stratégies de trading Forex & Matières Premières.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from superbot.brain.regime_detector import RegimeResult


@dataclass
class SignalResult:
    """Résultat standardisé généré par une stratégie de trading."""
    should_long: bool = False
    should_short: bool = False
    trigger_long: bool = False
    trigger_short: bool = False
    total_score: float = 0.0          # Score de 0 à 10
    strategy_name: str = ""
    market_regime: str = ""
    confidence: float = 0.0          # 0.0 à 1.0
    entry_price: float = 0.0
    sl_price: float = 0.0
    tp_price: float = 0.0
    rr_ratio: float = 0.0
    reason: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_long": self.should_long,
            "should_short": self.should_short,
            "trigger_long": self.trigger_long,
            "trigger_short": self.trigger_short,
            "total_score": round(self.total_score, 2),
            "strategy_name": self.strategy_name,
            "market_regime": self.market_regime,
            "confidence": round(self.confidence, 3),
            "entry_price": round(self.entry_price, 5),
            "sl_price": round(self.sl_price, 5),
            "tp_price": round(self.tp_price, 5),
            "rr_ratio": round(self.rr_ratio, 2),
            "reason": self.reason,
            "extra_data": self.extra_data,
        }


class BaseStrategy(ABC):
    """Classe de base abstraite pour toutes les stratégies de trading."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def analyze(
        self,
        df: pd.DataFrame,
        symbol: str,
        regime: RegimeResult,
        asset_class: str,
        current_price: float,
        pip_size: float = 0.0001
    ) -> SignalResult:
        """
        Analyse les données du marché et produit un SignalResult.
        """
        pass
