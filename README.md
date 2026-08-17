# 📈 NexQuant — Intelligence de Trading Quantitative Unifiée

**NexQuant** est un écosystème de trading algorithmique modulaire, distribué et automatisé conçu pour les marchés financiers modernes (**Cryptomonnaies, Actions/ETFs US et Forex**).

Il concilie :
1. **Un moteur d'exécution local en Python** (nom de code : **SuperBot**) — ultra-léger, asynchrone, ultra-rapide.
2. **Une console Web SaaS premium** construite avec **React, Vite, TypeScript, Tailwind CSS et Supabase** (facturation par abonnement Stripe intégrée).

---

## 🌌 Architecture Globale — Client Distribué

NexQuant utilise une architecture décentralisée pour garantir la confidentialité et la vitesse d'exécution :

`
              ┌────────────────────────────────────────┐
              │          NexQuant SaaS (Web App)       │
              │   - Front-end : React + Tailwind       │
              │   - Back-end  : Supabase (Vault)       │
              │   - Paiements : Stripe Subscription    │
              └──────────────────┬─────────────────────┘
                                 │
             Sécurisation        │  Jeton & Clés de Trading
             API (pgsodium)      │  (uniquement en RAM)
                                 ▼
              ┌────────────────────────────────────────┐
              │            Bot Client Local            │
              │   - Moteur de signaux techniques       │
              │   - Filtrage du risque & corrélation   │
              │   - Exécution directe sur les Brokers  │
              └──────┬───────────┬───────────┬─────────┘
                     │           │           │
                     ▼           ▼           ▼
                 [BINANCE]     [MT5]     [ALPACA]
                  Futures      Forex    Stocks/ETFs
`

- **Sécurisation des Clés (Supabase Vault & pgsodium)** : Les clés API sont chiffrées en base avec **pgsodium (AES-256)**, injectées dans la RAM du bot — elles ne touchent jamais le disque.
- **Télémétrie en Temps Réel** : Le bot pousse ses statistiques (solde, équité, positions, PnL, historique) vers Supabase pour affichage instantané sur le dashboard Web.
- **Contrôle à distance** : Pause/reprise du bot depuis l'interface Web via un canal de requêtes sécurisé.

---

## 📂 Structure du Dépôt

`
nexquant/
├── superbot/                  # 🐍 Backend : Bot de Trading Python
│   ├── broker/                # Adaptateurs brokers (Binance, MT5, Alpaca, Paper)
│   ├── risk/                  # RiskManager (Kelly, drawdown, break-even, corrélation)
│   ├── strategy/              # Logique de signal & filtres (trending vs ranging)
│   │   └── components/        # Scorer, RegimeDetector, RuleEngine, SignalGenerator
│   ├── indicators/            # Indicateurs techniques vectorisés (OHLCV)
│   ├── news/                  # Analyse sémantique NLP et calendrier économique
│   ├── dashboard/             # API locale + serveur Web (port 5000)
│   ├── monitoring/            # Bug watchdog & alertes proactives
│   ├── logs/                  # superbot.log + trades.jsonl + bug_log.md
│   └── main.py                # Point d'entrée & orchestration principale
├── NexQuant_Web_App/          # ⚛️ Frontend : Console SaaS React
│   ├── src/                   # Interface utilisateur, graphiques & intégration Supabase
│   └── supabase/              # Politiques de sécurité (RLS) et schémas SQL
├── resources/                 # 📚 Bases de connaissances & blogs de référence
│   ├── books/                 # PDF/TXT de livres de trading
│   ├── knowledge/             # Règles extraites (JSON auto-généré)
│   ├── blogs/                 # Articles de référence (Glassnode, QuantStart, etc.)
│   └── learning_engine.py     # Moteur d'extraction de règles
├── docs/                      # 📐 Architecture & plans (usage interne)
├── tests/                     # Tests unitaires et d'intégration (pytest)
├── .env.example               # Modèle de configuration (à copier en .env)
├── requirements.txt           # Dépendances Python
└── pyproject.toml             # Configuration du projet
`

---

## 🚀 Démarrage Rapide

### Prérequis

- **Python** 3.9 à 3.11
- **Node.js** 18+ avec **Bun** (recommandé) ou npm
- **MetaTrader 5** terminal installé (Windows uniquement, pour le broker MT5)

### 1. Bot Python (Backend)

`ash
# Depuis la racine du dépôt (nexquant/)
pip install -r requirements.txt

# Créer le fichier de configuration
cp .env.example .env
# → Renseignez vos clés API courtier ou vos jetons SaaS

# Démarrer le bot
python superbot/main.py
`

Lors du démarrage, le bot effectue automatiquement :
1. **Chargement de la configuration** — lecture des variables locales (.env) ou connexion à Supabase (mode SaaS).
2. **Validation des paramètres** — vérification de la cohérence des paramètres de risque.
3. **Synchronisation courtier** — téléchargement du solde, équité, et positions ouvertes.
4. **Initialisation des flux** — démarrage de la boucle de monitoring, récupération NLP des actualités, dashboard local.

### 2. Console Web React (Frontend)

`ash
cd NexQuant_Web_App

bun install   # ou npm install

# Créer .env.local :
# VITE_SUPABASE_URL=https://votre-url.supabase.co
# VITE_SUPABASE_ANON_KEY=votre-cle-anonyme

bun run dev   # ou npm run dev
`

---

## 🛡️ Filtres de Risque & Garde-fous

### Filtres Forex

| Filtre | Description |
|---|---|
| **Session Filter** | Trades limités à 08h00–18h00 heure de Londres (BST/GMT auto). Bloque vendredi après 17h00. |
| **Spread Guard** | Rejette le trade si le spread dépasse MAX_SPREAD_PIPS (ex : 1.5 pips). |
| **Correlation Filter** | Calcule l'exposition nette par devise. Rejette si l'exposition cumulée dépasse MAX_FOREX_CURRENCY_EXPOSURE. |
| **Pivot R:R Filter** | Calcule les pivots quotidiens (R1/S1/R2/S2). Rejette si l'obstacle est plus proche que le SL. |

### Protections Globales

| Protection | Description |
|---|---|
| **Break-Even Adaptatif** | Déplace le SL au point d'entrée dès que le trade atteint R:R 1:1. |
| **News Filter** | Bloque le trading 30 min avant/après les annonces majeures (FED, BCE, CPI, NFP). |
| **Crypto Range Prevention** | Trading crypto uniquement en régime TRENDING. Les régimes RANGING sont bloqués. |
| **Altcoin Pruning** | Uniquement le top 10 des cryptos. Score minimum plus élevé (CRYPTO_SCORE_MIN = 7). |
| **Circuit Breaker** | Coupe le bot après MAX_CONSECUTIVE_LOSS pertes d'affilée ou si MAX_DAILY_LOSS_PCT est atteint. |

> **Objectif** : Profit Factor > 1.3, winrate 38–45% avec R:R 2:1 (SL = 1.5×ATR / TP = 3×ATR).

---

## ⚙️ Paramètres Clés de Configuration (.env)

| Variable | Description | Valeur Recommandée |
|---|---|---|
| BROKER_TYPE | Courtier actif : inance, mt5, lpaca | mt5 (Forex Live) |
| INSTRUMENTS | Liste d'actifs séparés par des virgules | EUR/USD,GBP/USD (MT5) |
| GRANULARITY | Unité de temps principale | 1h, 4h, 1d |
| RISK_PCT | Capital risqué par transaction | 1.0 % |
| MAX_DAILY_LOSS_PCT | Drawdown quotidien avant coupure auto | 3.0 % |
| MAX_MONTHLY_LOSS_PCT | Drawdown mensuel avant coupure auto | 6.0 % |
| MAX_OPEN_POSITIONS | Nombre max de transactions simultanées | 3 |
| MAX_CONSECUTIVE_LOSS | Pertes d'affilée avant Circuit Breaker | 3 |
| MAX_FOREX_CURRENCY_EXPOSURE | Positions max exposées à une même devise | 1 |
| MAX_SPREAD_PIPS | Spread max toléré (en pips) | 1.5 |
| BE_DYN_RR | Active le Break-Even au R:R 1:1 | 	rue |
| NEWS_AVOIDANCE_BEFORE | Minutes de blocage avant annonce | 30 |
| NEWS_AVOIDANCE_AFTER | Minutes de blocage après annonce | 30 |
| CRYPTO_SCORE_MIN | Score minimum pour signaux crypto | 7 |
| CORRELATION_THRESHOLD | Seuil de corrélation (réduit risque à 70%) |  .7 |
| SIGNAL_STRENGTH_THRESHOLD | Score minimum pour valider un signal |  .6 |
| NEXQUANT_USER_ID | ID utilisateur NexQuant SaaS (optionnel) | — |
| NEXQUANT_INGEST_TOKEN | Jeton de télémétrie Supabase (optionnel) | — |

---

## 📚 Moteur de Connaissances

Le bot intègre une base de connaissances issue de livres de trading de référence :

| Auteur | Livre | Catégories |
|---|---|---|
| Alexander Elder | Vivre du Trading | Risque, Stratégie, Signaux |
| Thami Kabbaj | L'Art du Trading | Sizing, R:R, Psychologie |
| Mark Douglas | Trading in the Zone | Psychologie, Discipline |
| Van Tharp | Trade Your Way to Financial Freedom | SQN, R-multiples, Sizing |
| Jesse Livermore | Reminiscences of a Stock Operator | Tendance, Pyramidage |
| Jack Schwager | Market Wizards | Synthèse des grands traders |

`ash
# Ajouter de nouveaux livres (copier PDF/TXT dans resources/books/) puis :
python resources/learning_engine.py           # Traiter les nouveaux livres
python resources/learning_engine.py --summary  # Afficher les règles chargées
python resources/learning_engine.py --reset    # Reconstruire l'index
`

---

## 🔧 Workflow Git Sécurisé

1. **Ne poussez JAMAIS directement sur main** (force-push et commit direct interdits).
2. Créez toujours une **branche de fonctionnalité** : eature/nom-feature ou ix/nom-fix.
3. Utilisez la **convention de commits** :
   - eat(risk): add dynamic sl
   - ix(mt5): resolve lot size calculation
   - docs: update setup manual
4. Poussez la branche et ouvrez une **Pull Request** sur GitHub.
5. Attendez les validations CI/CD avant de fusionner en mode **Squash and Merge**.

---

## 🧪 Tests

`ash
pytest                                  # Tous les tests
pytest --cov=superbot tests/            # Avec couverture
pytest tests/test_v3_integration.py -v  # Test spécifique
`

---

## 📄 Licence

Projet privé — © NexQuant. Tous droits réservés.
