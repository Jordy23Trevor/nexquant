"""
Script de test pour valider l'intégration crescendo complète (133 règles) dans la stratégie.
"""
import sys
from pathlib import Path

# Ajouter la racine du projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from superbot.strategy.strategy import TradingStrategy

def main():
    print("=" * 80)
    print("  NexQuant Crescendo Strategy Integration Test (133 Rules)")
    print("=" * 80)

    # Configuration minimale requise par la stratégie
    config = {
        'SCORE_MIN': 5.0,
        'RISK_PCT': 5.0,        # On met 5% pour voir s'il plafonne à 2% (Elder)
        'KELLY_FRACTION': 0.5, # On met 50% pour voir si Kabbaj/Chan plafonne
        'EMA_FAST': 20,
        'EMA_SLOW': 50,
        'RSI_PERIOD': 14,
        'BB_PERIOD': 20,
        'BB_STD': 2.0,
    }

    strategy = TradingStrategy(config)

    print(f"Stratégie initialisée avec {len(strategy.knowledge_rules)} règles chargées.")
    print(f"Règles par niveau :")
    for level, rules in strategy._rules_by_level.items():
        print(f"  Level {level}: {len(rules)} règles")
    print(f"Filtres obligatoires : {len(strategy._filter_rules)} règles")

    # Création d'un contexte de test pour simuler un marché RANGING avec RSI survente extrême
    # Cela devrait déclencher CONTRARIAN_SIGNAL, BONUS_SCORE_RANGING, etc.
    latest_bar = {
        'close': 100.0,
        'ema_fast': 100.1,  # Près de la clôture -> EMA Squeeze possible
        'ema_slow': 99.8,
        'rsi': 18.0,        # RSI extrême (< 25)
        'volume': 15000.0,
        'volume_ma': 10000.0, # Volume supérieur à la moyenne
        'bb_width': 0.05,
        'bb_width_pct': 0.12, # BB Squeeze
        'atr': 2.5,
    }

    context = {
        'market_regime': 'RANGING',
        'latest_bar': latest_bar,
        'symbol': 'BTCUSDT',
        'recent_consecutive_wins': 6, # Déclenche overconfidence (reduction de kelly)
        'consecutive_losses': 0,
        'ml_confidence': 0.85, # ML confidence boost
    }

    # Score de départ
    start_score = 4.0
    start_risk = config['RISK_PCT']
    start_kelly = config['KELLY_FRACTION']

    print("\nApplication des règles crescendo ...")
    adj_score, adj_risk, adj_kelly = strategy._apply_knowledge_rules(
        current_score=start_score,
        risk_pct=start_risk,
        kelly_frac=start_kelly,
        context=context
    )

    print("\n--- RÉSULTATS DU TEST ---")
    print(f"Score : {start_score} -> {adj_score:.2f}")
    print(f"Risk Pct : {start_risk}% -> {adj_risk:.2f}% (Attendu: plafonné à 2% par Elder)")
    print(f"Kelly Fraction : {start_kelly} -> {adj_kelly:.4f} (Attendu: réduit/plafonné par Kabbaj/Montier)")
    print("-------------------------")

if __name__ == "__main__":
    main()
