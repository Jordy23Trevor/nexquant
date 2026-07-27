import os
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import joblib
import logging

log = logging.getLogger("ml.scorer")

class ProbabilisticScorer:
    """
    Phase 3.1 & 3.2 : Scoring probabiliste et Walk-Forward.
    Remplace le système de pointage fixe par une prédiction ML basée
    sur l'historique de trading réel.
    """
    def __init__(self, model_path="resources/logistic_scorer.pkl"):
        self.model_path = model_path
        self.model = LogisticRegression(class_weight='balanced', random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.load()
        
    def _extract_features(self, df_row: pd.Series) -> np.ndarray:
        """Extrait les features depuis une ligne (bougie enrichie d'indicateurs)."""
        rsi = df_row.get('rsi', 50)
        macd_hist = df_row.get('macd_hist', 0)
        adx = df_row.get('adx', 20)
        
        # BB Position: (close - lower) / (upper - lower)
        close = df_row.get('close', 1)
        bb_upper = df_row.get('bb_upper', close * 1.01)
        bb_lower = df_row.get('bb_lower', close * 0.99)
        bb_pos = (close - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
        
        atr_pct = (df_row.get('atr', 0) / close) * 100 if close > 0 else 0
        
        return np.array([[rsi, macd_hist, adx, bb_pos, atr_pct]])
        
    def train(self, trade_history_df: pd.DataFrame):
        """
        Entraîne le modèle logistique. (Logique Walk-Forward Phase 3.2)
        trade_history_df doit contenir les features au moment de l'entrée 
        ET une colonne 'target' (1 si gagnant, 0 si perdant).
        """
        if len(trade_history_df) < 50:
            log.warning("Pas assez de données pour entraîner le scorer (min 50 trades).")
            return False
            
        features = ['rsi', 'macd_hist', 'adx', 'bb_pos', 'atr_pct']
        
        # S'assurer que les features sont présentes
        for f in features:
            if f not in trade_history_df.columns:
                trade_history_df[f] = 0.0 # Fallback 
                
        X = trade_history_df[features].values
        y = trade_history_df['target'].values
        
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        train_acc = self.model.score(X_scaled, y)
        log.info(f"Scorer logistique entraîné. Précision: {train_acc:.2%}")
        self.save()
        return True
        
    def predict_proba(self, df_row: pd.Series) -> float:
        """Retourne la probabilité de gain (0.0 à 1.0) pour le setup actuel."""
        if not self.is_trained:
            # Fallback si non entrainé : on retourne un neutre biaisé
            return 0.5
            
        X = self._extract_features(df_row)
        X_scaled = self.scaler.transform(X)
        
        # get proba of class 1 (Gagnant)
        proba = self.model.predict_proba(X_scaled)[0][1]
        return float(proba)
        
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump({"model": self.model, "scaler": self.scaler}, self.model_path)
            log.info(f"Scorer sauvegardé -> {self.model_path}")
        except Exception as e:
            log.error(f"Erreur sauvegarde Scorer: {e}")
            
    def load(self):
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                if isinstance(data, dict) and "model" in data:
                    self.model = data["model"]
                    self.scaler = data.get("scaler", StandardScaler())
                    self.is_trained = hasattr(self.scaler, "mean_")
                    if self.is_trained:
                        log.info(f"Scorer chargé depuis {self.model_path} (format dictionnaire)")
                    else:
                        log.warning(f"Le Scorer dans {self.model_path} a un scaler non ajusté. Entraînement requis.")
                elif isinstance(data, LogisticRegression):
                    self.model = data
                    self.scaler = StandardScaler()
                    self.is_trained = False
                    log.warning(f"Modèle brut trouvé dans {self.model_path} sans paramètres de mise à l'échelle. Entraînement requis.")
                else:
                    self.is_trained = False
                    log.warning(f"Format de scorer non supporté dans {self.model_path}")
            except Exception as e:
                log.error(f"Erreur chargement Scorer: {e}")
                self.is_trained = False
