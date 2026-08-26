# NexQuant — Plateforme de Trading Quantitatif

NexQuant est une plateforme modulaire pour le développement, le test et l'exécution d'algorithmes de trading (cryptomonnaies, actions/ETFs, Forex).

Objectifs principaux

- Fournir un moteur d'exécution Python léger et asynchrone (SuperBot).
- Offrir une console Web (React + TypeScript) pour la supervision, la télémétrie et la gestion des abonnements.
- Garantir la sécurité des clés (chiffrement côté serveur, injection en RAM) et des garde-fous de risque.

Principales composantes

- superbot/: moteur Python (exécution, gestion brokers, stratégies, risk manager)
- NexQuant_Web_App/: frontend React pour supervision et gestion
- resources/: livres, règles et index de connaissances
- docs/: architecture, spécifications
- tests/: tests unitaires et d'intégration

Prérequis

- Python 3.9–3.11
- Node.js 18+ (Bun ou npm)
- (Optionnel) MetaTrader 5 pour le broker MT5 (Windows)

Installation rapide

1) Backend (bot Python)

```bash
# depuis la racine du dépôt
pip install -r requirements.txt
cp .env.example .env        # remplir les variables nécessaires
python superbot/main.py
```

2) Frontend (console Web)

```bash
cd NexQuant_Web_App
bun install   # ou npm install
# créer .env.local avec VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY
bun run dev    # ou npm run dev
```

Configuration (.env)

Remplissez les variables essentielles dans `.env` (ou `.env.local` pour le frontend) :

- BROKER_TYPE — courtier actif (binance | mt5 | alpaca)
- INSTRUMENTS — liste d'instruments séparés par des virgules
- RISK_PCT — pourcentage du capital par trade
- MAX_DAILY_LOSS_PCT — stop quotidien
- NEXQUANT_INGEST_TOKEN — (optionnel) jeton de télémétrie pour Supabase

Démarrage et vérifications

Au lancement, le bot :
- charge la configuration
- valide les paramètres de risque
- synchronise l'état avec le broker
- démarre les boucles de monitoring et télémétrie

Tests

```bash
pytest
pytest --cov=superbot tests/
```

Bonnes pratiques Git

- Ne pas pousser directement sur `main`.
- Créer des branches de fonctionnalité `feature/…` ou `fix/…`.
- Ouvrir une Pull Request et attendre CI avant de fusionner (Squash & merge recommandé).

Licence

Projet détenu par NexQuant. Tous droits réservés.
