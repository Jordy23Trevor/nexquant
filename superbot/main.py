import time
import traceback
from superbot.orchestrator import SuperBot

def main():
    """Point d'entrée principal du SuperBot."""
    print("SuperBot Trading Unifié")
    print("=" * 50)

    # Créer et démarrer le bot
    bot = SuperBot()

    try:
        bot.start()

        # Boucle principale d'attente (le bot travaille dans des threads séparés)
        print("SuperBot démarré avec succès")
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