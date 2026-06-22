"""
Test script to validate market data and connectivity for individual brokers.
Usage: python artifacts/test_single_broker.py --broker [binance|alpaca|paper_forex|oanda|mt5] --symbol [symbol]
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# S'assurer que le dossier racine du projet est dans le path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from superbot.broker import create_broker

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("test_broker")


def main():
    parser = argparse.ArgumentParser(description="Testeur de connectivité Broker pour SuperBot")
    parser.add_argument(
        "--broker",
        type=str,
        default="paper_forex",
        choices=["binance", "alpaca", "paper_forex", "oanda", "mt5"],
        help="Nom du broker à tester"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Symbole à tester (ex: EUR/USD, BTC/USDT, SPY)"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1h",
        help="Timeframe des bougies à tester (ex: 1m, 5m, 1h, 1d)"
    )

    args = parser.parse_args()

    # Déterminer les symboles par défaut si non fournis
    symbol = args.symbol
    if not symbol:
        default_symbols = {
            "binance": "BTC/USDT",
            "alpaca": "SPY",
            "paper_forex": "EUR/USD",
            "oanda": "EUR_USD",
            "mt5": "EURUSD"
        }
        symbol = default_symbols.get(args.broker, "EUR/USD")

    log.info(f"🧪 Initialisation du test pour le broker : {args.broker.upper()}")
    log.info(f"Actif cible : {symbol} | Timeframe : {args.timeframe}")

    try:
        # Création du broker
        broker = create_broker(args.broker)
        log.info("✅ Broker créé avec succès")

        # 1. Tester le solde / résumé de compte
        log.info("--- 1. Récupération des informations de compte ---")
        try:
            balance = broker.get_balance()
            log.info(f"💰 Solde disponible : {balance}")
            
            summary = broker.get_account_summary()
            log.info("📊 Résumé du compte :")
            for k, v in summary.items():
                log.info(f"  - {k}: {v}")
        except Exception as e:
            log.error(f"❌ Échec de la récupération du solde / résumé: {e}")

        # 2. Tester le prix en temps réel
        log.info("--- 2. Récupération du prix actuel ---")
        try:
            price = broker.get_current_price(symbol)
            log.info(f"📈 Prix de marché actuel pour {symbol} : {price}")
        except Exception as e:
            log.error(f"❌ Échec du prix actuel : {e}")

        # 3. Tester le téléchargement de bougies
        log.info(f"--- 3. Téléchargement des bougies historiques ({args.timeframe}) ---")
        try:
            df = broker.fetch_candles(symbol, args.timeframe, limit=10)
            if df is not None and not df.empty:
                log.info(f"✅ Reçu {len(df)} bougies avec succès :")
                log.info(f"\n{df.tail(5).to_string()}")
            else:
                log.warning("⚠️ Aucune bougie retournée ou DataFrame vide")
        except Exception as e:
            log.error(f"❌ Échec du téléchargement des bougies : {e}")

        # 4. Tester la normalisation de symbole
        log.info("--- 4. Normalisation de symbole ---")
        try:
            norm = broker.normalize_symbol(symbol)
            log.info(f"Symbole original : '{symbol}' -> Normalisé : '{norm}'")
        except Exception as e:
            log.error(f"❌ Échec de la normalisation : {e}")

        log.info("🎉 Test terminé !")

    except Exception as e:
        log.critical(f"💥 Erreur critique lors de l'exécution du test : {e}", exc_info=True)


if __name__ == "__main__":
    main()
