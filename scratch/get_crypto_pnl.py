"""
Analyse le fichier trades.jsonl pour extraire le P&L crypto de la journée du 29 Juin 2026.
"""
import json
import os
from datetime import datetime

trades_file = 'superbot/logs/trades.jsonl'
if not os.path.exists(trades_file):
    print("Fichier trades.jsonl introuvable à l'emplacement indiqué.")
    exit(1)

# Liste des actifs crypto typiques configurés dans le bot (ou par mot-clé)
def is_crypto(symbol):
    sym = symbol.upper()
    # Si le symbole contient USDT, BTC, ETH, SOL, ou s'il n'a pas de slash type Forex (EURUSD)
    # ou de suffixe boursier type actions (.US, SPY)
    crypto_keywords = ["USDT", "BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOT", "LINK"]
    if any(kw in sym for kw in crypto_keywords):
        return True
    # Fallback si ce n'est pas du forex connu ou action
    forex_keywords = ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
    # Si c'est du type EURUSD, ce n'est pas crypto
    if len(sym) == 6 and any(sym[:3] in forex_keywords for kw in forex_keywords) and any(sym[3:] in forex_keywords for kw in forex_keywords):
        return False
    return False

total_crypto_pnl = 0.0
crypto_trades_today = []

target_date = "2026-06-29"

with open(trades_file, 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip():
            continue
        try:
            trade = json.loads(line)
            # Vérifier s'il est fermé, s'il a un P&L, si c'est de la crypto, et si c'est aujourd'hui
            status = trade.get('status')
            pnl = trade.get('pnl')
            symbol = trade.get('symbol', '')
            timestamp_str = trade.get('timestamp', '')
            
            if status == 'closed' and pnl is not None and is_crypto(symbol):
                # Extraire la date
                if timestamp_str.startswith(target_date):
                    total_crypto_pnl += float(pnl)
                    crypto_trades_today.append(trade)
        except Exception as e:
            continue

print(f"==================================================")
print(f" BILAN P&L CRYPTO POUR LE {target_date}")
print(f"==================================================")
print(f"Nombre de trades crypto clos aujourd'hui : {len(crypto_trades_today)}")
print(f"Détail des trades :")
for t in crypto_trades_today:
    side = t.get('side', '').upper()
    symbol = t.get('symbol', '')
    pnl = t.get('pnl', 0.0)
    entry = t.get('entry_price', 0.0)
    exit_p = t.get('exit_price', 0.0)
    qty = t.get('position_size', 0.0)
    print(f"  - {symbol} ({side}) : Qty={qty:.4f} | Entry={entry:.2f} | Exit={exit_p:.2f} | P&L = {pnl:.2f} USD")

print(f"--------------------------------------------------")
print(f"P&L CRYPTO TOTAL DU JOUR : {total_crypto_pnl:.2f} USD")
print(f"==================================================")
