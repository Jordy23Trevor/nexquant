"""
NexQuant ML Module
==================
Sous-module de Machine Learning pour NexQuant.

Contient :
  - OnlineLearner : apprentissage continu en ligne sur les trades fermés
  - EnsembleScorer : ensemble de 3 modèles (LR, RF, GB) avec vote adaptatif
  - WalkForwardOptimizer : optimisation des hyperparamètres sur historique
"""
from superbot.ml.online_learner import OnlineLearner
from superbot.ml.probabilistic_scorer import EnsembleScorer
from superbot.ml.walk_forward import WalkForwardOptimizer

__all__ = ['OnlineLearner', 'EnsembleScorer', 'WalkForwardOptimizer']
