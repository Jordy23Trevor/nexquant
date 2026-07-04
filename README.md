# 📈 NexQuant — Intelligence de Trading Quantitative Unifiée

**NexQuant** est un écosystème de trading algorithmique modulaire, distribué et automatisé conçu pour les marchés financiers modernes (**Cryptomonnaies, Actions/ETFs US et Forex**). 

Il concilie :
1. **Un moteur d'exécution local en Python** (nom de code : **SuperBot**) ultra-léger et ultra-rapide.
2. **Une console Web SaaS premium** construite avec **React, Vite, TypeScript, Tailwind CSS, et Supabase** (comprenant la facturation par abonnement Stripe).

---

## 🌌 Architecture Globale en Client Distribué

NexQuant utilise une architecture décentralisée pour garantir la confidentialité et la vitesse d'exécution :

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

* **Sécurisation des Clés (Supabase Vault & pgsodium)** : Les clés d'API des courtiers sont renseignées sur la console SaaS, chiffrées en base de données avec l'extension cryptographique **pgsodium (AES-256)**. Elles sont injectées dans la RAM du bot local lors de l'authentification et ne touchent jamais son disque dur.
* **Télémétrie en Temps Réel** : Le bot pousse ses statistiques de performance (solde, équité, positions ouvertes, PnL, historique des trades clos) vers Supabase pour affichage instantané sur le dashboard Web.
* **Contrôle à distance** : Permet de mettre en pause ou de reprendre le bot local à distance depuis l'interface Web via un canal de requêtes sécurisé.

---

## 🚀 Fonctionnalités Clés & Filtres de Risque Avancés

Pour stabiliser le bot Forex & Crypto et viser un **winrate cible de 50-55%**, plusieurs filtres quantitatifs et de gestion de capital ont été intégrés :

### 1. Garde-fous et Filtres Forex
* **Filtre Temporel de Session (Session Filter)** : Restreint l'ouverture des trades Forex aux heures de haute liquidité (de **08h00 à 18h00 heure de Londres**, calculant automatiquement l'heure d'été/BST et d'hiver/GMT). Bloque les entrées la nuit et le **vendredi soir après 17h00** (et le week-end) pour éviter les fausses cassures de faible volume.
* **Garde-fou sur le Spread (Spread Guard)** : Récupère le spread réel Bid/Ask du courtier. Si le spread est supérieur à `MAX_SPREAD_PIPS` (ex: `1.5` ou `2.0` pips), le trade est rejeté. Idéal pour éviter le slippage pendant le Rollover quotidien de 23h00.
* **Calculateur d'Exposition de Devise (Correlation Filter)** : Évalue l'exposition nette sur chaque devise (ex: si vous avez déjà un LONG `EUR/USD`, une exposition de `+1 EUR` et `-1 USD` est enregistrée). Si un signal sur `GBP/USD` survient, il est rejeté car l'exposition cumulée sur l'USD dépasserait `MAX_FOREX_CURRENCY_EXPOSURE = 1`. Cela protège le portefeuille du risque systémique lié à une devise unique.
* **Filtre d'Obstacle Pivot (Pivot R:R Filter)** : Calcule les points pivots quotidiens (Pivot, R1, S1, R2, S2) à partir des bougies de la veille resamplées. Si le premier niveau pivot faisant obstacle (R1/R2 pour LONG, S1/S2 pour SHORT) est plus proche de l'entrée que le Stop Loss (R:R réel potentiel < 1:1), le trade est rejeté.

### 2. Protections de Portefeuille Globales
* **Break-Even Adaptatif Précoce (R:R 1:1)** : Dès qu'une position atteint un gain latent égal à son risque initial (R:R de 1:1), le Stop Loss est déplacé au point d'entrée pour éliminer définitivement le risque de perte sur ce trade. Si le trailing stop est déjà plus avantageux, il est préservé.
* **News Filter (Évitement d'Annonces)** : Se connecte à Forex Factory et bloque le trading **30 minutes avant et 30 minutes après** les annonces économiques majeures classées "Rouges" (taux d'intérêt de la FED/BCE, CPI/inflation, NFP/emploi).
* **Crypto Range Prevention (Trend-Following Strict)** : Le range trading est entièrement désactivé sur les cryptomonnaies. Si un signal crypto survient en régime `RANGING`, il est immédiatement bloqué. Le trading crypto est uniquement effectué en suivi de tendance (`TRENDING`) pour éviter les manipulations de liquidité.
* **Altcoin Pruning** : Pruning des altcoins secondaires illiquides. Seul le top 10 des cryptomonnaies est autorisé, avec une blacklist stricte (`SOL/USDT`) et un score d'entrée plus exigeant (`CRYPTO_SCORE_MIN = 7`).
* **Disjoncteur (Circuit Breaker)** : Coupe le bot après un nombre de pertes d'affilée (`MAX_CONSECUTIVE_LOSS`) ou si le drawdown quotidien max (`MAX_DAILY_LOSS_PCT`) est atteint.

---

## 🛠️ Démarrage Rapide

### 📂 Structure du Répertoire

```
nexquant/
├── superbot/                  # 🐍 Backend : Bot de Trading Python
│   ├── broker/                # Adaptateurs brokers (Binance, MT5, Alpaca, Paper)
│   ├── risk/                  # RiskManager (Kelly, drawdown, BE, corrélation)
│   ├── strategy/              # Logique de signal & filtres (trending vs ranging)
│   ├── indicators/            # Calculateurs techniques vectorisés (OHLCV)
│   ├── news/                  # Analyse sémantique NLP et calendrier économique
│   └── main.py                # Boucle d'exécution et orchestration principale
├── NexQuant_Web_App/          # ⚛️ Frontend : Console SaaS React
│   ├── src/                   # Interface utilisateur, graphiques & intégration Supabase
│   └── supabase/              # Politiques de sécurité (RLS) et schémas SQL
```

### 1. Installation et Lancement du Bot Python
1. Accédez au répertoire racine :
   ```bash
   cd nexquant
   pip install -r requirements.txt
   ```
2. Créez votre fichier de variables d'environnement `.env` :
   ```bash
   cp .env.backup .env
   ```
   Renseignez vos clés API courtier ou vos jetons SaaS.
3. Démarrez l'exécuteur :
   ```bash
   python superbot/main.py
   ```

### 2. Installation et Lancement de la Console Web React
1. Allez dans le répertoire de la Web App :
   ```bash
   cd nexquant/NexQuant_Web_App
   ```
2. Installez les packages (avec **Bun** recommandé ou **npm**) :
   ```bash
   bun install   # ou npm install
   ```
3. Configurez le fichier `.env.local` :
   ```env
   VITE_SUPABASE_URL=https://votre-url-supabase.supabase.co
   VITE_SUPABASE_ANON_KEY=votre-cle-anonyme-supabase
   ```
4. Démarrez le serveur de développement :
   ```bash
   bun run dev   # ou npm run dev
   ```

---

## ⚙️ Paramètres Clés de Configuration (`.env`)

| Variable | Description | Valeur Recommandée |
|---|---|---|
| `BROKER_TYPE` | Courtier actif (`binance`, `mt5`, `alpaca`, `paper_forex`) | `mt5` (Forex Live) / `paper_forex` (Test) |
| `RISK_PCT` | Capital risqué par transaction | `1.0` % (conservateur) |
| `MAX_FOREX_CURRENCY_EXPOSURE` | Nombre maximal de positions exposées à une même devise | `1` |
| `MAX_SPREAD_PIPS` | Spread maximum en pips toléré pour entrer en position | `1.5` ou `2.0` |
| `BE_DYN_RR` | Active le déplacement du SL à l'entrée au R:R 1:1 | `true` |
| `NEWS_AVOIDANCE_BEFORE` / `_AFTER` | Minutes de blocage autour des publications majeures | `30` |
| `CRYPTO_SCORE_MIN` | Score minimum requis pour les signaux crypto | `7` |

---

## 🛡️ Guide de Workflow Git Sécurisé

Pour maintenir la stabilité de l'application et éviter toute coupure de synchronisation avec Lovable :
1. **Ne poussez JAMAIS directement sur `main`**. Le commit direct ou le force-push sur la branche de production est interdit.
2. Créez toujours une branche de fonctionnalité (`feature/nom-feature` ou `docs/nom-doc`).
3. Suivez la convention des messages de commits (ex: `feat(risk): add dynamic sl`, `fix(mt5): resolve lot size calculation`, `docs: update setup manual`).
4. Poussez la branche et ouvrez une **Pull Request** sur GitHub. Attendez les validations CI/CD et la relecture de code avant de fusionner en mode **Squash and Merge**.
