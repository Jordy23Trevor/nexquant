#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NexQuant -- Script d'entrainement du modele HMM de regime de marche (Phase 2)
==============================================================================
Telecharge les donnees historiques reelles, entraine le modele HMM sur
plusieurs actifs, valide les performances et sauvegarde le modele final.

Exemples d'utilisation :

  python superbot/ml/train_regime.py --broker yfinance --symbol BTC-USD --timeframe 1d --start 2022-01-01
  python superbot/ml/train_regime.py --broker yfinance --symbols BTC-USD,SPY,GC=F --timeframe 1d --start 2020-01-01
  python superbot/ml/train_regime.py --broker binance --symbol BTCUSDT --timeframe 1h --start 2023-01-01
  python superbot/ml/train_regime.py --broker yfinance --symbol BTC-USD --timeframe 1d --start 2022-01-01 --dry-run
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List

import pandas as pd

# Assurer que la racine du projet est dans le path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("train_regime")


def load_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les indicateurs techniques necessaires aux features HMM."""
    try:
        from superbot.strategy.knowledge_base import calculate_adx, calculate_bollinger_bands
        high = df["high"]
        low = df["low"]
        close = df["close"]

        df["adx"] = calculate_adx(high, low, close, period=14)

        upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(close, 20, 2.0)
        df["bb_width"] = (upper_bb - lower_bb) / middle_bb.replace(0, 1)

    except Exception as e:
        log.warning(f"Impossible de calculer les indicateurs ({e}). Le HMM utilisera ses propres calculs.")

    return df


def fetch_training_data(broker: str, symbols: List[str], timeframe: str,
                        start: str, end: str = None, periods: int = 3000) -> pd.DataFrame:
    """
    Telecharge les donnees de plusieurs actifs et les concatene.
    La concatenation sur plusieurs actifs permet au HMM de detecter
    des regimes universels non specifiques a un seul instrument.
    """
    from superbot.backtest.data_fetcher import DataFetcher
    fetcher = DataFetcher(broker_type=broker)

    all_dfs = []
    for symbol in symbols:
        log.info(f"Telechargement : {symbol} {timeframe}...")
        try:
            df = fetcher.fetch(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                periods=periods,
            )
            df = load_indicators(df)
            all_dfs.append(df)
            log.info(f"  {symbol} : {len(df)} bougies chargees")
        except Exception as e:
            log.warning(f"  {symbol} ignore : {e}")

    if not all_dfs:
        raise ValueError("Aucune donnee valide telechargee. Verifiez les parametres.")

    combined = pd.concat(all_dfs, ignore_index=True)
    log.info(f"Dataset total : {len(combined)} observations ({len(all_dfs)} actif(s))")
    return combined


def validate_model(detector, df: pd.DataFrame) -> dict:
    """
    Valide le modele sur un jeu de donnees de test (Out-of-Sample).
    Mesure la stabilite des predictions et la distribution des regimes.
    """
    predictions = []
    confidences = []
    window = 50

    for i in range(window, len(df), 10):
        slice_df = df.iloc[max(0, i-30):i+1]
        try:
            regime, conf, state = detector.predict(slice_df)
            predictions.append(regime)
            confidences.append(conf)
        except Exception:
            pass

    if not predictions:
        return {"error": "Aucune prediction reussie"}

    regime_counts = {}
    for r in predictions:
        regime_counts[r] = regime_counts.get(r, 0) + 1

    return {
        "total_predictions": len(predictions),
        "avg_confidence": sum(confidences) / len(confidences),
        "min_confidence": min(confidences),
        "max_confidence": max(confidences),
        "regime_distribution": {k: v/len(predictions)*100 for k, v in regime_counts.items()},
    }


def main():
    parser = argparse.ArgumentParser(
        description="NexQuant -- Entraineur du modele HMM de regime de marche",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--broker",     default="yfinance",
                        help="Source de donnees (yfinance/binance/alpaca) [defaut: yfinance]")
    parser.add_argument("--symbol",     default="BTC-USD",
                        help="Symbole unique a utiliser [defaut: BTC-USD]")
    parser.add_argument("--symbols",    default=None,
                        help="Liste de symboles separes par des virgules (ex: BTC-USD,SPY,GC=F)")
    parser.add_argument("--timeframe",  default="1d",
                        help="Timeframe des bougies [defaut: 1d]")
    parser.add_argument("--start",      default="2022-01-01",
                        help="Date de debut [defaut: 2022-01-01]")
    parser.add_argument("--end",        default=None,
                        help="Date de fin (defaut: aujourd'hui)")
    parser.add_argument("--periods",    type=int, default=3000,
                        help="Nombre max de bougies [defaut: 3000]")
    parser.add_argument("--model-path", default=None,
                        help="Chemin de sauvegarde (defaut: superbot/resources/hmm_regime_model.pkl)")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Entrainer et afficher les resultats sans sauvegarder")
    parser.add_argument("--no-cache",   action="store_true",
                        help="Forcer le re-telechargement des donnees")

    args = parser.parse_args()

    # Resoudre la liste de symboles
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    else:
        symbols = [args.symbol]

    end_label = args.end if args.end else "maintenant"

    print("\n" + "=" * 60)
    print("  NexQuant -- Entrainement du modele HMM (Phase 2)")
    print(f"  Actifs     : {', '.join(symbols)}")
    print(f"  Timeframe  : {args.timeframe}")
    print(f"  Periode    : {args.start} -> {end_label}")
    print("=" * 60 + "\n")

    # 1. Telecharger les donnees
    df_all = fetch_training_data(
        broker=args.broker,
        symbols=symbols,
        timeframe=args.timeframe,
        start=args.start,
        end=args.end,
        periods=args.periods,
    )

    # 2. Division train/test (80/20)
    split_idx = int(len(df_all) * 0.8)
    df_train = df_all.iloc[:split_idx]
    df_test = df_all.iloc[split_idx:]
    log.info(f"Train: {len(df_train)} obs | Test: {len(df_test)} obs")

    # 3. Entrainer le modele
    from superbot.ml.regime_detector import MarketRegimeDetector
    detector = MarketRegimeDetector()

    log.info("Debut de l'entrainement HMM...")
    detector.fit(df_train)

    # 4. Afficher le resume des regimes
    detector.print_training_summary()

    # 5. Valider sur le jeu de test
    log.info("Validation Out-of-Sample...")
    val_results = validate_model(detector, df_test)

    print("=" * 60)
    print("  VALIDATION OUT-OF-SAMPLE")
    print("=" * 60)
    print(f"  Predictions totales   : {val_results.get('total_predictions', 0)}")
    print(f"  Confiance moyenne     : {val_results.get('avg_confidence', 0):.2%}")
    print(f"  Confiance min/max     : {val_results.get('min_confidence', 0):.2%} / {val_results.get('max_confidence', 0):.2%}")
    print("  Distribution des regimes :")
    for regime, pct in val_results.get("regime_distribution", {}).items():
        print(f"    {regime:<15} : {pct:.1f}%")
    print("=" * 60)

    # Diagnostic de qualite
    avg_conf = val_results.get("avg_confidence", 0)
    if avg_conf >= 0.70:
        print("  [OK] Modele de haute qualite (confiance >= 70%)")
    elif avg_conf >= 0.55:
        print("  [~~] Modele acceptable (confiance >= 55%)")
    else:
        print("  [!!] Modele incertain (confiance < 55%) -- envisagez plus de donnees")

    # 6. Sauvegarder si demande
    if not args.dry_run:
        saved_path = detector.save(args.model_path)
        print(f"\n  [SAVE] Modele sauvegarde -> {saved_path}")
        print(
            "\n  Le bot chargera automatiquement ce modele au prochain demarrage."
        )
    else:
        print("\n  [DRY-RUN] Modele non sauvegarde (--dry-run actif)")

    print()


if __name__ == "__main__":
    main()
