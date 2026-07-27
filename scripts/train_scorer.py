import os
import sys
import numpy as np
import pandas as pd
import logging
from sklearn.linear_model import LogisticRegression
import joblib

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from superbot.ml.probabilistic_scorer import ProbabilisticScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("train_scorer")

def generate_synthetic_trades(num_trades: int = 883) -> pd.DataFrame:
    """
    Génère 883 trades synthétiques pour l'entraînement du modèle.
    """
    log.info(f"Génération de {num_trades} trades historiques synthétiques...")
    np.random.seed(42)
    
    # RSI (0-100) : typiquement autour de 30 pour les longs rebonds, 70 pour shorts
    rsi = np.random.normal(loc=50, scale=15, size=num_trades)
    rsi = np.clip(rsi, 0, 100)
    
    # ADX (0-100) : Tendance forte si > 25
    adx = np.random.normal(loc=20, scale=10, size=num_trades)
    adx = np.clip(adx, 0, 100)
    
    # MACD Histogram : Oscillations autour de 0
    macd_hist = np.random.normal(loc=0, scale=5, size=num_trades)
    
    # BB Position (0 to 1)
    bb_pos = np.random.uniform(0, 1, size=num_trades)
    
    # ATR PCT (0.1 to 3.0)
    atr_pct = np.random.uniform(0.1, 3.0, size=num_trades)
    
    df = pd.DataFrame({
        'rsi': rsi,
        'macd_hist': macd_hist,
        'adx': adx,
        'bb_pos': bb_pos,
        'atr_pct': atr_pct
    })
    
    # Logique cible (1 = Gagnant, 0 = Perdant)
    # Plus l'ADX est fort (>25), plus le trade a de chances de réussir.
    # Un RSI extrême augmente aussi la probabilité (mean reversion).
    win_prob = 0.40  # Base 40% win rate
    
    # Modificateurs de probabilité
    win_prob += (df['adx'] > 25) * 0.15
    win_prob += ((df['rsi'] < 35) | (df['rsi'] > 65)) * 0.10
    win_prob += (df['macd_hist'] > 0) * 0.05
    win_prob -= (df['atr_pct'] > 2.0) * 0.10
    
    # Ajout de bruit aléatoire
    random_factor = np.random.uniform(0, 1, size=num_trades)
    df['target'] = (random_factor < win_prob).astype(int)
    
    win_rate = df['target'].mean() * 100
    log.info(f"Trades générés. Win Rate global : {win_rate:.1f}%")
    
    return df
 
def train_and_save():
    df = generate_synthetic_trades(883)
    
    # Instancier le scorer
    scorer = ProbabilisticScorer(model_path="resources/logistic_scorer.pkl")
    
    # Entraîner via l'interface officielle
    log.info("Entraînement de la Régression Logistique avec StandardScaler...")
    success = scorer.train(df)
    if success:
        log.info("✅ Modèle et Scaler entraînés et sauvegardés via ProbabilisticScorer.")
    else:
        log.error("❌ Échec de l'entraînement du modèle.")
 
if __name__ == "__main__":
    train_and_save()
