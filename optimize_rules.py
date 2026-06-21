#!/usr/bin/env python
"""
NexQuant Rules Optimizer & Backtester.
Simulates trading using the unified TradingStrategy and optimizes the weights
of dynamic knowledge rules (Ernest Chan, Bob Volman, Elder, etc.) using Optuna (or fallback random search).
"""
import os
import sys
import math
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np

# S'assurer que le répertoire racine est dans le path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import des modules NexQuant
from superbot.strategy.strategy import TradingStrategy
from superbot.indicators.technical_indicators import TechnicalIndicators

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("optimizer")

def generate_synthetic_data(length=500, regime='trending') -> pd.DataFrame:
    """Génère des données de marché synthétiques réalistes pour le backtest."""
    np.random.seed(42)
    time_index = pd.date_range(start="2026-01-01", periods=length, freq="1h")
    
    # Prix de départ
    price = 100.0
    prices = []
    
    # Paramètres du régime
    if regime == 'trending':
        drift = 0.05
        volatility = 0.5
    else:  # ranging
        drift = 0.0
        volatility = 0.8
        
    for i in range(length):
        if regime == 'ranging':
            # Mean reversion autour de 100
            price = price + 0.1 * (100.0 - price) + np.random.normal(drift, volatility)
        else:
            # Tendance avec fluctuations
            price = price + drift + np.random.normal(drift, volatility)
        prices.append(max(price, 5.0))
        
    df = pd.DataFrame(index=time_index)
    df['close'] = prices
    df['open'] = df['close'] * (1 + np.random.normal(0, 0.001, length))
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + abs(np.random.normal(0, 0.002, length)))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - abs(np.random.normal(0, 0.002, length)))
    df['volume'] = np.random.uniform(100, 1000, length)
    
    # Calcul de l'ATR approximatif
    df['atr'] = (df['high'] - df['low']).rolling(14).mean().fillna(1.0)
    
    return df

class RulesBacktester:
    """Simulateur de backtest léger pour évaluer les performances de la stratégie."""
    def __init__(self, data: pd.DataFrame, initial_balance: float = 10000.0):
        self.data = data
        self.initial_balance = initial_balance
        
    def run_backtest(self, strategy: TradingStrategy) -> Dict[str, Any]:
        # Pré-calculer tous les indicateurs une seule fois avec l'instance de la stratégie
        df_with_indicators = strategy.indicators.calculate_all_indicators(self.data.copy())
        
        # Surcharger calculate_all_indicators pour renvoyer directement le sous-ensemble pré-calculé
        original_calc = strategy.indicators.calculate_all_indicators
        strategy.indicators.calculate_all_indicators = lambda df_slice: df_with_indicators.loc[df_slice.index]
        
        balance = self.initial_balance
        equity = balance
        position = None  # None, 'LONG', 'SHORT'
        entry_price = 0.0
        position_size = 0.0
        sl = 0.0
        tp = 0.0
        
        trades = []
        equity_curve = []
        
        # Scanner l'historique en excluant les premières bougies nécessaires pour les indicateurs (50 bougies)
        for i in range(50, len(self.data)):
            current_bar = df_with_indicators.iloc[i]
            latest_idx = df_with_indicators.index[i]
            
            # Sous-ensemble historique disponible pour le calcul des indicateurs à cette étape
            historical_slice = self.data.iloc[:i+1]
            
            # Mettre à jour la valeur du compte (Equity)
            if position == 'LONG':
                current_value = balance + position_size * (current_bar['close'] - entry_price)
            elif position == 'SHORT':
                current_value = balance + position_size * (entry_price - current_bar['close'])
            else:
                current_value = balance
                
            equity_curve.append(current_value)
            
            # 1. Gérer les sorties (SL / TP)
            if position == 'LONG':
                if current_bar['low'] <= sl:
                    pnl = position_size * (sl - entry_price)
                    balance += pnl
                    trades.append({'type': 'LONG', 'entry': entry_price, 'exit': sl, 'pnl': pnl, 'result': 'SL'})
                    position = None
                elif current_bar['high'] >= tp:
                    pnl = position_size * (tp - entry_price)
                    balance += pnl
                    trades.append({'type': 'LONG', 'entry': entry_price, 'exit': tp, 'pnl': pnl, 'result': 'TP'})
                    position = None
            elif position == 'SHORT':
                if current_bar['high'] >= sl:
                    pnl = position_size * (entry_price - sl)
                    balance += pnl
                    trades.append({'type': 'SHORT', 'entry': entry_price, 'exit': sl, 'pnl': pnl, 'result': 'SL'})
                    position = None
                elif current_bar['low'] <= tp:
                    pnl = position_size * (entry_price - tp)
                    balance += pnl
                    trades.append({'type': 'SHORT', 'entry': entry_price, 'exit': tp, 'pnl': pnl, 'result': 'TP'})
                    position = None
                    
            # 2. Analyser les signaux si pas de position ouverte
            if position is None:
                try:
                    signal = strategy.analyze_market(historical_slice)
                    if signal['should_long']:
                        position = 'LONG'
                        entry_price = current_bar['close']
                        sl = signal['sl_price'] if signal['sl_price'] > 0 else entry_price - current_bar['atr'] * 2
                        tp = signal['tp_price'] if signal['tp_price'] > 0 else entry_price + current_bar['atr'] * 4
                        position_size = (balance * (strategy.risk_per_trade / 100.0)) / abs(entry_price - sl)
                    elif signal['should_short']:
                        position = 'SHORT'
                        entry_price = current_bar['close']
                        sl = signal['sl_price'] if signal['sl_price'] > 0 else entry_price + current_bar['atr'] * 2
                        tp = signal['tp_price'] if signal['tp_price'] > 0 else entry_price - current_bar['atr'] * 4
                        position_size = (balance * (strategy.risk_per_trade / 100.0)) / abs(entry_price - sl)
                except Exception as e:
                    pass
                    
        # Restaurer la fonction d'origine
        strategy.indicators.calculate_all_indicators = original_calc
        
        # Clôturer la position ouverte à la fin de la période
        if position is not None:
            final_price = self.data.iloc[-1]['close']
            if position == 'LONG':
                pnl = position_size * (final_price - entry_price)
            else:
                pnl = position_size * (entry_price - final_price)
            balance += pnl
            trades.append({'type': position, 'entry': entry_price, 'exit': final_price, 'pnl': pnl, 'result': 'CLOSE_END'})
            
        # Calculer les métriques
        win_trades = [t for t in trades if t['pnl'] > 0]
        win_rate = len(win_trades) / len(trades) if trades else 0.0
        total_pnl = balance - self.initial_balance
        pnl_pct = (total_pnl / self.initial_balance) * 100.0
        
        # Ratio de Sharpe approximatif
        returns = pd.Series(equity_curve).pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * math.sqrt(252 * 24)) if not returns.empty and returns.std() > 0 else 0.0
        
        return {
            'final_balance': balance,
            'pnl_pct': pnl_pct,
            'trades_count': len(trades),
            'win_rate': win_rate,
            'sharpe_ratio': sharpe
        }

def run_optimization(trials=20):
    """Fonction principale d'optimisation (Optuna ou fallback)."""
    # 1. Générer des données historiques
    log.info("Génération de l'historique de marché synthétique (Ranging + Trending)...")
    data_ranging = generate_synthetic_data(250, regime='ranging')
    data_trending = generate_synthetic_data(250, regime='trending')
    data = pd.concat([data_ranging, data_trending]).reset_index(drop=True)
    
    # Recalculer l'index temporel
    data.index = pd.date_range(start="2026-01-01", periods=len(data), freq="1h")
    
    backtester = RulesBacktester(data)
    
    log.info("Recherche de la présence de la librairie Optuna...")
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        HAS_OPTUNA = True
    except ImportError:
        HAS_OPTUNA = False
        log.warning("Optuna n'est pas installé. Utilisation d'une recherche aléatoire classique.")
        
    best_pnl = -9999.0
    best_params = {}
    
    if HAS_OPTUNA:
        def objective(trial):
            # Définir les paramètres à optimiser
            score_min = trial.suggest_int('score_min', 4, 8)
            risk_pct = trial.suggest_float('risk_pct', 0.5, 3.0)
            
            config = {
                'SCORE_MIN': score_min,
                'RISK_PCT': risk_pct,
                'SL_ATR_MULT': 1.5,
                'TP_ATR_MULT': 3.0
            }
            
            strategy = TradingStrategy(config)
            result = backtester.run_backtest(strategy)
            return result['pnl_pct']
            
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=trials)
        best_params = study.best_params
        best_pnl = study.best_value
        log.info(f"✨ Optimisation Optuna terminée avec succès !")
    else:
        # Recherche aléatoire simplifiée (Fallback)
        log.info(f"Début de la recherche aléatoire ({trials} essais)...")
        for t in range(trials):
            score_min = random.randint(4, 8)
            risk_pct = random.uniform(0.5, 3.0)
            
            config = {
                'SCORE_MIN': score_min,
                'RISK_PCT': risk_pct,
                'SL_ATR_MULT': 1.5,
                'TP_ATR_MULT': 3.0
            }
            
            strategy = TradingStrategy(config)
            result = backtester.run_backtest(strategy)
            
            if result['pnl_pct'] > best_pnl:
                best_pnl = result['pnl_pct']
                best_params = {'score_min': score_min, 'risk_pct': risk_pct}
                
    log.info("=========================================")
    log.info("       RÉSULTAT DE L'OPTIMISATION        ")
    log.info("=========================================")
    log.info(f"Meilleur PnL obtenu : {best_pnl:.2f}%")
    log.info(f"Paramètres optimaux : {best_params}")
    log.info("=========================================")
    
    # Tester la meilleure stratégie sur les données
    best_config = {
        'SCORE_MIN': best_params['score_min'],
        'RISK_PCT': best_params['risk_pct'],
        'SL_ATR_MULT': 1.5,
        'TP_ATR_MULT': 3.0
    }
    best_strategy = TradingStrategy(best_config)
    final_res = backtester.run_backtest(best_strategy)
    
    log.info(f"Statistiques finales de la stratégie optimisée :")
    log.info(f"  - Nombre de trades : {final_res['trades_count']}")
    log.info(f"  - Taux de réussite : {final_res['win_rate']*100:.1f}%")
    log.info(f"  - Sharpe Ratio : {final_res['sharpe_ratio']:.2f}")

if __name__ == "__main__":
    trials_count = 25
    if len(sys.argv) > 1:
        try:
            trials_count = int(sys.argv[1])
        except ValueError:
            pass
    run_optimization(trials_count)
