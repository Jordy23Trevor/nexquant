# NexQuant — Trading Intelligence

NexQuant est un robot de trading algorithmique modulaire et automatisé multi-actifs (Cryptomonnaies, Actions US et Forex). Il intègre une boucle d'analyse technique en temps réel, un moteur de décision adaptatif au régime de marché, un classifieur sémantique NLP pour l'apprentissage autonome, un module d'actualités pour la gestion du sentiment fondamental et un tableau de bord web haute performance de suivi en direct.

---

## 🚀 Fonctionnalités Clés

* **Moteur Multi-Broker** : Intégration pour Binance Futures, Alpaca Markets et Paper Forex.
* **Régime de Marché Adaptatif** : Bascule automatique entre **Suivi de Tendance (Trending)** et **Retour à la Moyenne (Ranging)**.
* **Parseur Sémantique NLP** : Classification automatique de règles textuelles avec `sentence-transformers`.
* **Gestion Avancée du Risque** : Fraction de Kelly et règles de contrôle de drawdown.
* **Interface Web (Dashboard)** : Visualisation du P&L, des positions, et des journaux en direct.

---

## 🛠️ Démarrage Rapide

### 1. Prérequis
```bash
pip install -r requirements.txt
```

### 2. Configuration
Créez un fichier `.env` à la racine :
```env
BROKER_TYPE=binance
BINANCE_API_KEY=votre_cle_api
BINANCE_API_SECRET=votre_secret_api
BINANCE_TESTNET=true
```

### 3. Lancement
```bash
python superbot/main.py
```

---

## 📖 Documentation Multilingue Globale

Toute la documentation du projet (Manuel d'Utilisation, Guide Expert, Spécifications Techniques, et Configuration des Brokers Externes/Webhooks) a été consolidée.

* **[Documentation Interactive Premium (GLOBAL_DOCUMENTATION.html)](GLOBAL_DOCUMENTATION.html)** : Ouvrez ce fichier dans votre navigateur pour une expérience interactive complète avec recherche en direct et sélecteur de langue (Français 🇫🇷, English 🇬🇧, Español 🇪🇸).
* **[Documentation Globale Unifiée Markdown (GLOBAL_DOCUMENTATION.md)](GLOBAL_DOCUMENTATION.md)** : Version texte consolidée multilingue.
