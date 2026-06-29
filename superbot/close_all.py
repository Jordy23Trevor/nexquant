import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from superbot.broker.base import create_broker

def close_all_positions():
    load_dotenv()
    try:
        broker = create_broker()
        print(f"Connexion au broker : {broker.get_asset_type()}...")
        
        instruments = broker.get_default_instruments()
        broker_type = os.getenv("BROKER_TYPE", "binance").upper()
        env_instruments = os.getenv(f"INSTRUMENTS_{broker_type}") or os.getenv("INSTRUMENTS")
        if env_instruments:
            instruments = [s.strip() for s in env_instruments.split(",") if s.strip()]
            
        print(f"Verification des positions sur : {instruments}")
        positions_closed = 0
        for symbol in instruments:
            try:
                pos = broker.get_position(symbol)
                if pos and pos.get("size", 0) > 0:
                    print(f"Fermeture de la position sur {symbol} (Taille: {pos.get('size')})...")
                    success = broker.close_position(symbol, reason="Emergency Close User Request")
                    if success:
                        print(f"[OK] Position {symbol} fermee avec succes.")
                        positions_closed += 1
                    else:
                        print(f"[FAILED] Echec de la fermeture pour {symbol}.")
            except Exception as e:
                print(f"Erreur lors de la verification/fermeture de {symbol} : {e}")
                
        print(f"Bilan : {positions_closed} position(s) fermee(s).")
    except Exception as e:
        print(f"Erreur globale : {e}")

if __name__ == "__main__":
    close_all_positions()
