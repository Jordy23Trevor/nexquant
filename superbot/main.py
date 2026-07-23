import argparse
import os
import sys
import time
import traceback

def main():
    """Point d'entrée principal du SuperBot avec support multi-broker CLI."""
    parser = argparse.ArgumentParser(description="SuperBot Trading Unifié")
    parser.add_argument("--broker", type=str, default=None, help="Type de broker (binance, mt5, alpaca)")
    parser.add_argument("--dashboard-port", type=int, default=None, help="Port du dashboard Flask")
    parser.add_argument("--webhook-port", type=int, default=None, help="Port du serveur webhook")
    args = parser.parse_args()

    if args.broker:
        os.environ["BROKER_TYPE"] = args.broker.lower()
    if args.dashboard_port:
        os.environ["DASHBOARD_PORT"] = str(args.dashboard_port)
    if args.webhook_port:
        os.environ["WEBHOOK_PORT"] = str(args.webhook_port)

    from superbot.orchestrator import SuperBot

    broker_name = os.environ.get("BROKER_TYPE", "binance").upper()
    print(f"SuperBot Trading Unifié [{broker_name}]")
    print("=" * 50)

    # Créer et démarrer le bot
    bot = SuperBot()

    try:
        bot.start()

        # Boucle principale d'attente
        print(f"SuperBot [{broker_name}] démarré avec succès")
        print("Appuyez sur Ctrl+C pour arrêter le bot")
        print("=" * 50)

        # Attendre jusqu'à interruption
        while bot.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"\nErreur fatale : {e}")
        traceback.print_exc()
    finally:
        print("\nArrêt du SuperBot en cours...")
        bot.stop()
        print("SuperBot arrêté")
        print("Au revoir !")

if __name__ == "__main__":
    main()