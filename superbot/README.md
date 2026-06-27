# 🐍 NexQuant — SuperBot Execution Client

Ce répertoire contient l'exécuteur principal de trading algorithmique de **NexQuant** (nom de code : **SuperBot**). C'est un moteur asynchrone écrit en Python, conçu pour surveiller les cours du marché en temps réel, évaluer les signaux techniques et exécuter les ordres de manière ultra-sécurisée selon des règles de risque strictes.

---

## 🛠️ Prérequis et Installation

1. **Version de Python** : Python 3.9 à 3.11 recommandé.
2. **Dépendances** : Installez les packages listés à la racine du dépôt :
   ```bash
   pip install -r ../requirements.txt
   ```
3. **Spécificités par Courtier** :
   * **MetaTrader 5 (MT5)** : Nécessite Windows et l'installation préalable du terminal MT5 (ex: Fusion Markets). Configurez le chemin d'accès vers `terminal64.exe` dans le fichier `.env` si nécessaire.
   * **Binance Futures** : Nécessite des clés API avec droits de trading Futures activés.
   * **Alpaca** : Créez un compte Alpaca (Paper ou Live) et récupérez vos clés API.

---

## 🚀 Lancement

Le bot s'exécute à l'aide de la commande suivante depuis le dossier racine du dépôt (`nexquant/`) :
```bash
python superbot/main.py
```

Lors du démarrage, le bot effectue les étapes suivantes :
1. **Chargement de la configuration** : Lecture des variables locales (`.env`) ou connexion à Supabase (si exécuté en mode SaaS centralisé).
2. **Validation des paramètres** : Le moteur vérifie la cohérence des paramètres de risque (drawdown, taille limite de lot/ordre) pour protéger vos fonds.
3. **Synchronisation avec le courtier** : Téléchargement du solde réel du compte, de l'équité, et des positions ouvertes actuelles.
4. **Initialisation des flux** : Démarrage de la boucle de monitoring de marché, de la récupération des actualités NLP, et du serveur de dashboard de supervision local.

---

## 📂 Architecture des Modules

* **`broker/`** : Contient les connecteurs normalisés vers les courtiers. Chaque courtier implémente une interface unifiée (`get_balance()`, `get_position()`, `execute_order()`, etc.).
* **`risk/`** : Le cerveau de gestion de capital. Il implémente la formule de fraction de Kelly pour la taille dynamique, le calcul d'équité en temps réel, le calcul de la corrélation des actifs et les disjoncteurs consécutifs de pertes.
* **`strategy/`** : Analyse les graphiques historiques pour déterminer le régime du marché (Suivi de Tendance vs Retour à la Moyenne) et génère des scores d'entrée longs/courts.
* **`indicators/`** : Bibliothèque interne d'indicateurs (EMA, RSI, MACD, Ichimoku Cloud, ATR, Bandes de Bollinger, VWAP).
* **`news/`** : Module NLP qui scrape des flux d'actualités financières et calcule des scores de sentiment globaux (évitement de trading lors d'annonces à fort impact).
* **`dashboard/`** : API locale et serveur Web (port `5000`) permettant de visualiser les logs en direct, les positions ouvertes et le graphique de performance historique.
* **`logs/`** : Contient le fichier journal principal `superbot.log` et le fichier structuré de transactions `trades.jsonl`.

---

## ⚙️ Configuration Détaillée (`.env`)

Copiez le fichier `.env.backup` sous le nom de `.env` dans le répertoire `nexquant/` et configurez les variables suivantes :

### 1. Paramètres Généraux et Brokers
* `BROKER_TYPE` : Le courtier cible (`binance`, `mt5`, `alpaca` ou `paper_forex`).
* `INSTRUMENTS` : Liste d'actifs séparés par des virgules (ex: `BTC/USDT,ETH/USDT` pour Binance, `EUR/USD,GBP/USD` pour MT5, `SPY,QQQ` pour Alpaca).
* `GRANULARITY` : Unité de temps principale pour l'analyse (ex: `1h`, `4h`, `1d`).

### 2. Gestion du Risque de Base (Elder's Rules)
* `RISK_PCT` : Risque consenti par transaction en pourcentage du capital (recommandé : `1.0` % à `2.0` %).
* `MAX_DAILY_LOSS_PCT` : Drawdown quotidien autorisé avant coupure automatique (`3.0` % par défaut).
* `MAX_MONTHLY_LOSS_PCT` : Drawdown mensuel autorisé (`6.0` % par défaut).
* `MAX_OPEN_POSITIONS` : Nombre maximal de transactions simultanées autorisées (ex: `3`).

### 3. Nouveaux Filtres et Protections Avancées
* `MAX_CONSECUTIVE_LOSS` : Nombre de pertes d'affilée tolérées avant activation du **Circuit Breaker** (bloque le lancement de nouveaux trades).
* `CORRELATION_LOOKBACK` : Fenêtre de calcul historique pour la corrélation des rendements (ex: `20` bougies).
* `CORRELATION_THRESHOLD` : Seuil de corrélation moyenne. Au-delà de `0.7`, la taille de position est diminuée à `70%` du risque calculé pour éviter les doublons de risque systémique.
* `SIGNAL_STRENGTH_THRESHOLD` : Score minimum requis pour la force du signal (`0.0` à `1.0`). Les signaux faibles sous ce seuil sont rejetés.
* `FUNDING_RATE_THRESHOLD` : Seuil à partir duquel le taux de financement des contrats à terme Binance est jugé trop élevé (ex: `0.01` %).
* `FUNDING_RATE_FACTOR` : Pourcentage de réduction du risque appliqué si le financement joue contre la direction de la position.

### 4. Mode SaaS & Télémétrie
Si vous connectez le client à la console web centrale (Lovable) :
* `NEXQUANT_USER_ID` : Votre identifiant unique de compte utilisateur NexQuant.
* `NEXQUANT_INGEST_TOKEN` : Jeton d'accès sécurisé pour pousser la télémétrie en temps réel vers Supabase.
