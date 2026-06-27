# 📈 NexQuant — Intelligence de Trading Quantitative

**NexQuant** est un écosystème de trading algorithmique modulaire, automatisé et distribué conçu pour les marchés financiers modernes (Cryptomonnaies, Actions/ETFs US et Forex). Il allie un client d'exécution Python léger et ultra-rapide à une interface web SaaS premium et réactive (React + Vite + Supabase).

---

## 🌌 Architecture Globale de la v2

NexQuant utilise une architecture en **client distribué** permettant de concilier la rapidité d'exécution locale et la puissance de contrôle centralisée d'un SaaS moderne.

```
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
```

---

## 🚀 Fonctionnalités Majeures

### 1. Moteur Multi-Broker Flexible
* **Binance Futures** : Trading de dérivés crypto avec levier réglable et gestion dynamique des marges.
* **MetaTrader 5 (MT5)** : Intégration pour le Forex (Fusion Markets) avec exécution au volume (lots) et gestion des heures de marché.
* **Alpaca Markets** : Trading d'actions et d'ETFs US avec détection et respect automatique des heures d'ouverture de la bourse de New York (NYSE).
* **Paper Forex Engine** : Simulateur interne complet pour le test de stratégies Forex hors ligne sans risque.

### 2. Gestion de Risque et Filtres Quantitatifs de Pointe
* **Filtre de Qualité de Signal** : Analyse de la force d'un signal (score sur 10) et exigences minimales de Risk/Reward avant exécution.
* **Ajustement de Risque par Corrélation** : Analyse de la corrélation historique des rendements d'un actif. Si deux actifs ou plus sont fortement corrélés, le dimensionnement des positions est réduit automatiquement (facteur de réduction) pour éviter la sur-exposition.
* **Disjoncteur de Pertes (Circuit Breaker)** : Blocage temporaire ou arrêt des transactions après un nombre configurable de pertes consécutives (`MAX_CONSECUTIVE_LOSS`) ou un dépassement du drawdown maximum autorisé.
* **Gestion Avancée de la Fraction de Kelly** : Calcul dynamique de la taille optimale de position ajustée selon le taux de réussite historique du robot.
* **Intégration du Funding Rate** : Prise en compte du taux de financement (Funding Rate) sur Binance Futures pour optimiser les stratégies de Carry Trade (réduction automatique de la taille si les frais de financement pénalisent la direction du trade).

### 3. Écosystème SaaS & Facturation Commerciale
* **Chiffrement Centralisé des Clés (Supabase Vault)** : Vos clés API de trading sont configurées sur le site web et chiffrées de manière ultra-sécurisée avec **pgsodium (AES-256)**. Elles sont envoyées au bot local lors de l'authentification et stockées uniquement en RAM, sans jamais toucher au disque dur du client.
* **Vérification de Licence & Bêta** : Une période d'essai de 1 mois s'active automatiquement à l'inscription. Passé ce délai, le bot local est bloqué automatiquement via l'API d'ingestion sécurisée si aucun abonnement Stripe n'est actif.
* **Mise à Jour Automatique (Auto-Update)** : Le bot interroge le serveur au démarrage pour comparer sa version avec la version officielle et télécharge de manière transparente les correctifs nécessaires.

---

## 📂 Structure du Répertoire Git

```
nexquant/
├── superbot/                  # 🐍 Backend : Bot de Trading Python
│   ├── broker/                # Adaptateurs de courtiers (Binance, MT5, Alpaca...)
│   ├── risk/                  # Module de calcul de risque et d'historique
│   ├── strategy/              # Logique algorithmique adaptative (trend vs range)
│   ├── indicators/            # Indicateurs techniques (EMA, RSI, MACD, Ichimoku...)
│   ├── news/                  # Analyse sémantique de sentiment NLP (Sentence-Transformers)
│   ├── dashboard/             # API locale et dashboard de supervision en direct
│   └── main.py                # Point d'entrée de l'exécuteur du bot
├── NexQuant_Web_App/          # ⚛️ Frontend : Application Web React
│   ├── src/                   # Composants de l'interface client, graphiques & intégrations
│   └── tsconfig.json, etc.    # Configurations TypeScript/Vite/Bun
├── docs/                      # 📖 Centre de Documentation
│   ├── architecture/          # Spécifications et diagrammes d'architecture broker
│   └── plans/                 # Plans de développement et historique d'implémentation
├── GLOBAL_DOCUMENTATION.md    # Guide de référence multilingue complet (Markdown)
└── GLOBAL_DOCUMENTATION.html  # Guide interactif avec sélecteur de langue et recherche
```

---

## 🛠️ Démarrage Rapide (Développement)

### 1. Lancement du Bot Python
1. Installez les dépendances nécessaires :
   ```bash
   cd nexquant
   pip install -r requirements.txt
   ```
2. Dupliquez et renommez le fichier `.env.backup` en `.env`, puis configurez vos variables (clés API ou jetons SaaS).
3. Démarrez l'exécuteur :
   ```bash
   python superbot/main.py
   ```

### 2. Lancement de la Console Web (Vite React)
1. Installez les packages Node (de préférence avec Bun pour plus de rapidité) :
   ```bash
   cd nexquant/NexQuant_Web_App
   bun install   # ou npm install
   ```
2. Copiez le fichier `.env` du frontend et configurez les clés d'accès à Supabase.
3. Démarrez le serveur de développement :
   ```bash
   bun run dev   # ou npm run dev
   ```

---

## 📖 Accès à la Documentation Expert

Pour une plongée en profondeur dans les détails mathématiques de nos stratégies adaptatives ou le paramétrage des webhooks TradingView, ouvrez le fichier interactif **`GLOBAL_DOCUMENTATION.html`** dans n'importe quel navigateur internet. Il dispose d'un moteur de recherche dynamique et est traduit en Français 🇫🇷, Anglais 🇬🇧 et Espagnol 🇪🇸.
