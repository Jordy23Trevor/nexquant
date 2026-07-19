import logging
import itertools
import time
import pandas as pd
from typing import Dict, Any

log = logging.getLogger("ml.walk_forward")

class WalkForwardOptimizer:
    """
    Phase 3.2 : Moteur de recalibration Walk-Forward Adaptatif.
    Ce module permet de trouver dynamiquement les meilleurs paramètres
    du bot tous les 30 jours, en fonction du comportement du marché.
    """
    def __init__(self):
        # Grille de recherche des hyperparamètres (Grid Search)
        self.param_grid = {
            'SCORE_MIN': [5, 6, 7],
            'RSI_OB': [65, 70, 75],
            'ADX_TREND': [20, 22, 25]
        }
        self.best_params = {
            'SCORE_MIN': 6,
            'RSI_OB': 70,
            'ADX_TREND': 22
        }
        self.last_calibration_time = time.time()
        self.is_optimizing = False

    def optimize(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Recherche la meilleure combinaison sur les trades récents.
        Note: Sur un système de production réel, ceci invoquerait un subprocess
        exécutant `scripts/run_backtest.py`. Ici nous approchons le filtrage.
        """
        if len(trades_df) < 20:
            log.warning("Pas assez de trades pour l'optimisation Walk-Forward (min 20).")
            return self.best_params

        self.is_optimizing = True
        log.info("Démarrage de l'optimisation Walk-Forward (Asynchrone)...")
        
        best_pf = -1.0
        best_combo = self.best_params.copy()
        
        # Génération de toutes les combinaisons possibles
        keys, values = zip(*self.param_grid.items())
        combos = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        for combo in combos:
            # On simule le Profit Factor qu'aurait donné cette combinaison
            pf = self._simulate_profit_factor(trades_df, combo)
            if pf > best_pf:
                best_pf = pf
                best_combo = combo
                
        self.best_params = best_combo
        self.last_calibration_time = time.time()
        self.is_optimizing = False
        
        log.info(f"✅ Walk-Forward terminé ! Nouveaux paramètres optimaux : {self.best_params} (PF simulé: {best_pf:.2f})")
        return self.best_params
        
    def _simulate_profit_factor(self, df: pd.DataFrame, params: dict) -> float:
        """
        Simule le filtrage des trades selon les paramètres.
        Pour un bot complet, on rejouerait les signaux sur l'historique Klines.
        """
        # Exclure virtuellement les trades qui n'auraient pas passé le SCORE_MIN
        # Note: on part du principe que la donnée historique contient ces features
        valid_trades = df.copy()
        
        if 'signal_score' in valid_trades.columns:
            valid_trades = valid_trades[valid_trades['signal_score'] >= params['SCORE_MIN']]
            
        gross_profit = valid_trades[valid_trades['pnl'] > 0]['pnl'].sum() if 'pnl' in valid_trades else 100.0
        gross_loss = abs(valid_trades[valid_trades['pnl'] < 0]['pnl'].sum()) if 'pnl' in valid_trades else 50.0
        
        # Simplification mathématique pour illustrer l'optimisation
        gross_loss += (params['SCORE_MIN'] * 1.5)
        
        if gross_loss == 0:
            return float('inf')
        return float(gross_profit / gross_loss)
