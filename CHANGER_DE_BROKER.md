# NexQuant — Guide : Changer de Broker

---

## Réponse courte

> **Oui, il faut redémarrer le bot** à chaque changement de broker.
> Le changement se fait **uniquement dans le fichier `.env`**, en 1 ligne.

---

## 1. La seule ligne à modifier dans `.env`

```env
BROKER_TYPE=binance        # ← Crypto (Binance Futures testnet)
# ou
BROKER_TYPE=alpaca         # ← Actions US (Alpaca paper trading)
# ou
BROKER_TYPE=paper_forex    # ← Forex simulé (EUR/USD, GBP/USD…)
```

Puis redémarrez le bot :
```bash
# Arrêter
Ctrl+C

# Relancer
python main.py
```

---

## 2. Ce qui change automatiquement au redémarrage

Quand vous changez de broker, le bot s'adapte **sans aucun autre changement** :

| Élément                | Binance              | Alpaca               | Paper Forex          |
|------------------------|----------------------|----------------------|----------------------|
| **Instruments**        | BTC/USDT, ETH/USDT… | SPY, QQQ, AAPL…     | EUR/USD, GBP/USD…   |
| **Devise du compte**   | USDT                 | USD                  | USD (simulé)         |
| **Données de marché**  | Binance Futures API  | Alpaca Market Data   | TwelveData / AlphaV  |
| **Unité des prix**     | Crypto (ex: 50 000) | Actions (ex: 480)    | Forex (ex: 1.0850)  |
| **Taille des ordres**  | En base asset (BTC)  | En nombre d'actions  | En lots (0.01…)     |
| **News / sentiment**   | Crypto (BTC, ETH…)   | Marché US (SPY, QQQ) | Forex (EUR, USD…)   |
| **Graphique dashboard**| Paires crypto        | Tickers actions      | Paires forex         |

> Le bot lit automatiquement `INSTRUMENTS_BINANCE`, `INSTRUMENTS_ALPACA`
> ou `INSTRUMENTS_PAPER_FOREX` selon `BROKER_TYPE`.

---

## 3. Ce qui NE change PAS (reste en mémoire)

- ✅ L'historique des trades (`superbot/logs/trades.jsonl`)
- ✅ Les règles du Knowledge Base (`resources/knowledge_index.json`)
- ✅ Les paramètres de risque (RISK_PCT, MAX_DAILY_LOSS_PCT…)
- ✅ La stratégie (indicateurs, score minimum…)

> **Important** : Le P&L affiché sur le dashboard repart de zéro à chaque redémarrage
> car le solde initial est détecté depuis le nouveau broker.

---

## 4. Personnaliser les instruments par broker

Dans `.env`, chaque broker a sa propre liste :

```env
# Crypto (Binance)
INSTRUMENTS_BINANCE=BTC/USDT,ETH/USDT,BNB/USDT,ADA/USDT,SOL/USDT

# Actions US (Alpaca)
INSTRUMENTS_ALPACA=SPY,QQQ,AAPL,TSLA,MSFT,NVDA

# Forex simulé
INSTRUMENTS_PAPER_FOREX=EUR/USD,GBP/USD,USD/JPY,AUD/USD,USD/CHF
```

Vous pouvez modifier ces listes **sans toucher au code**.

---

## 5. Pourquoi le redémarrage est obligatoire

Le bot charge la connexion broker **une seule fois au démarrage** :
- Il se connecte à l'API (Binance / Alpaca / Yahoo Finance)
- Il détecte le solde initial (pour calculer le P&L)
- Il charge les instruments compatibles avec ce broker
- Le dashboard démarre lié à ce broker

Changer `BROKER_TYPE` en cours de route ne serait pas sûr :
un trade Binance ouvert et une connexion Alpaca seraient incompatibles.

---

## 6. Que faire si le dashboard se bloque après redémarrage ?

Le dashboard se reconnecte **automatiquement** toutes les 5 secondes.
Si après 30 secondes il n'affiche toujours rien :

1. Rafraîchir la page navigateur (`F5`)
2. Vérifier que le bot tourne bien dans le terminal (pas d'erreur de connexion API)
3. Vérifier l'URL : `http://localhost:5000`

**Le message "Reconnexion (n)…"** en haut à droite est normal pendant les
quelques secondes que met le bot à démarrer. Il disparaît dès que les premières
données arrivent.

---

## 7. Résumé rapide par broker

### Binance Futures Testnet
```env
BROKER_TYPE=binance
BINANCE_TESTNET=true
INSTRUMENTS_BINANCE=BTC/USDT,ETH/USDT,SOL/USDT
```
- Données temps réel, zéro risque réel
- Solde fictif en USDT fourni par Binance testnet
- Idéal pour tester des stratégies crypto

### Alpaca Paper Trading
```env
BROKER_TYPE=alpaca
ALPACA_USE_PAPER=true
INSTRUMENTS_ALPACA=SPY,QQQ,AAPL,TSLA
```
- Données marchés US en temps réel (NYSE/NASDAQ)
- Solde fictif en USD fourni par Alpaca
- Uniquement disponible pendant les heures de marché US (15h30–22h00 heure française)

### Paper Forex (simulé)
```env
BROKER_TYPE=paper_forex
INSTRUMENTS_PAPER_FOREX=EUR/USD,GBP/USD,USD/JPY
```
- Données via TwelveData ou AlphaVantage (clés gratuites)
- Solde 100% simulé localement
- Disponible 24h/24, 5j/7 (marché forex)
