"""
NexQuant ML Module
==================
Sous-module de Machine Learning pour NexQuant.

Contient :
  - MarketRegimeDetector : classification HMM des régimes de marché
  - train_regime.py      : script CLI d'entraînement
"""
from superbot.ml.regime_detector import MarketRegimeDetector

__all__ = ['MarketRegimeDetector']
