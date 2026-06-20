# NexQuant — Trading Intelligence

NexQuant est un robot de trading algorithmique modulaire et automatisé multi-actifs (Cryptomonnaies, Actions US et Forex). Il intègre une boucle d'analyse technique en temps réel, un moteur de décision adaptatif au régime de marché, un module d'actualités pour la gestion du sentiment fondamental et un tableau de bord web haute performance de suivi en direct.

---

## 🚀 Fonctionnalités Clés

* **Moteur Multi-Broker** : Intégration native pour Binance Futures (Testnet & Live), Alpaca Markets (Actions US) et Paper Forex (Forex simulé en direct).
* **Régime de Marché Adaptatif** : Analyse de la dynamique du marché pour basculer automatiquement entre les algorithmes de **Suivi de Tendance (Trending)** et de **Retour à la Moyenne (Ranging)**.
* **Gestion Avancée du Risque** : Calcul de la taille de lot par la formule de Kelly, calcul dynamique des Stop Loss / Take Profit via l'ATR (Average True Range), et gestion globale du drawdown quotidien/mensuel.
* **Synchronisation Broker-Bot** : Synchronisation continue et automatique de l'état interne du bot et de la gestion des risques avec les positions et ordres réels chez le courtier.
* **Dashboard Premium** : Interface web moderne et réactive (Flask, ApexCharts) pour suivre le solde réel, le P&L, les positions ouvertes, les graphiques de prix en direct et les journaux système (`superbot.log`).

---

## 🛠️ Démarrage Rapide

### 1. Prérequis
Assurez-vous d'avoir Python 3.8+ installé, ainsi que les dépendances du projet :
```bash
pip install -r requirements.txt
```
*(Si le fichier de dépendances n'existe pas, installez les packages requis : `pip install pandas numpy flask requests python-binance websocket-client alpaca-trade-api python-dotenv`)*

### 2. Configuration des Variables d'Environnement
Créez ou modifiez le fichier `.env` à la racine du projet (exclu de Git par sécurité) :
```env
# Type de courtier actif : binance, alpaca, ou paper_forex
BROKER_TYPE=binance

# Clés API Binance Futures Testnet (exemple)
BINANCE_API_KEY=votre_cle_api_ici
BINANCE_API_SECRET=votre_secret_api_ici
BINANCE_TESTNET=true

# Paramètres généraux
MAX_OPEN_POSITIONS=5
RISK_PCT=1.0
SCORE_MIN=4
ENABLE_DASHBOARD=true
```

### 3. Lancement du Bot
Exécutez le script principal pour démarrer le bot et le serveur web du dashboard :
```bash
python superbot/main.py
```

### 4. Accès au Dashboard
Une fois le bot démarré, ouvrez votre navigateur et accédez à l'URL suivante :
* **[http://localhost:5000](http://localhost:5000)**

---

## 📂 Documentation

Pour approfondir les détails techniques de l'architecture, de la stratégie mathématique, du cycle de vie du moteur de trading ou pour ajouter vos propres indicateurs et courtiers, consultez :
* **[Documentation Technique Complète (TECHNICAL_DOCUMENTATION.md)](TECHNICAL_DOCUMENTATION.md)**
* **[Guide de changement de courtier (CHANGER_DE_BROKER.md)](CHANGER_DE_BROKER.md)**
