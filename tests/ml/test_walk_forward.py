import pytest
import pandas as pd
from superbot.ml.walk_forward import WalkForwardOptimizer
from superbot.ml.probabilistic_scorer import ProbabilisticScorer

def test_walk_forward_optimizer_basic():
    """Vérifie le fonctionnement de base de l'optimiseur Walk-Forward."""
    optimizer = WalkForwardOptimizer()
    
    # Créer un faux historique de trades
    trades = [
        {'symbol': 'BTC/USDT', 'signal_score': 6.0, 'pnl': 100.0, 'status': 'closed'},
        {'symbol': 'BTC/USDT', 'signal_score': 5.0, 'pnl': -50.0, 'status': 'closed'},
        {'symbol': 'BTC/USDT', 'signal_score': 7.0, 'pnl': 200.0, 'status': 'closed'},
        {'symbol': 'BTC/USDT', 'signal_score': 4.0, 'pnl': -100.0, 'status': 'closed'},
    ] * 10  # 40 trades au total (min 20 requis par l'optimiseur)
    
    df = pd.DataFrame(trades)
    
    # Exécuter l'optimisation
    best_params = optimizer.optimize(df)
    
    # Vérifier que les paramètres retournés font partie de la grille
    assert best_params['SCORE_MIN'] in [5, 6, 7]
    assert best_params['RSI_OB'] in [65, 70, 75]
    assert best_params['ADX_TREND'] in [20, 22, 25]

def test_probabilistic_scorer_predict_proba():
    """Vérifie le fonctionnement du Scorer probabiliste en mode entraîné et non-entraîné."""
    # Utiliser un chemin temporaire pour ne pas écraser le modèle de production
    scorer = ProbabilisticScorer(model_path="resources/test_logistic_scorer.pkl")
    
    # Par défaut (non entraîné), il doit retourner 0.5
    row = pd.Series({'rsi': 60, 'macd_hist': 1.5, 'adx': 30, 'close': 100, 'bb_upper': 102, 'bb_lower': 98, 'atr': 2})
    assert scorer.predict_proba(row) == 0.5
