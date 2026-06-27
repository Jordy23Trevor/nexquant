# Plan de Développement NexQuant — Phase 2 (Révisé)

> **Document master révisé** — 27 juin 2026
> Révision basée sur l'audit du codebase existant. Les sections marquées **[RÉVISION]** sont modifiées par rapport à la v1.

---

## 0. État des Lieux — Ce qui Existe Déjà (Phase 1)

**[RÉVISION]** Avant de planifier, inventorions ce qui est déjà implémenté :

### ✅ Déjà en Place (Migration `20260627105700_commercial_features.sql`)

| Table/Fonction | Description | Fichier |
|---|---|---|
| `profiles.role` | Rôle user/admin | [`20260627105700_commercial_features.sql`](nexquant/NexQuant_Web_App/supabase/migrations/20260627105700_commercial_features.sql:1) |
| `profiles.trial_end` | Fin d'essai 30 jours | même migration |
| `profiles.ingest_token` | Jeton HMAC unique | même migration |
| `handle_new_user()` | Trigger auto avec trial 30j | même migration |
| `user_brokers` | Clés API chiffrées AES-256 | même migration |
| `bot_config` | `risk_pct`, `score_min`, `is_running` | même migration |
| `app_versions` | Versions disponibles pour auto-update | même migration |
| `is_admin()` | Fonction de vérification admin | même migration |

### ✅ Endpoints API Existants

| Endpoint | Description | Fichier |
|---|---|---|
| `POST /api/public/ingest` | Réception heartbeat/equity/position/log/regime + vérif HMAC + licence | [`ingest.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/ingest.ts:57) |
| `POST /api/public/config` | Retourne config bot + clés déchiffrées + version dispo | [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:33) |

### ✅ Dashboard Web Existant

| Fonctionnalité | Détail | Fichier |
|---|---|---|
| Courbe d'équité 90j | AreaChart Recharts | [`dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx:154) |
| KPIs (Equity, P&L, Drawdown) | 4 cards | [`dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx:140) |
| Bouton Start/Stop | Appelle `toggleBot()` | [`dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx:92) |
| Positions ouvertes | Tableau temps réel | [`dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx:207) |
| Bandeau licence | Trial countdown + bouton abonnement (placeholder) | [`dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx:114) |
| Admin panel | Gestion utilisateurs, trials | [`admin.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/admin.tsx) |
| Demo data seeding | 90j de données synthétiques | [`nexquant.functions.ts`](nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts:6) |

### ✅ Bot Python Existant

| Module | Fonctionnalité | Fichier |
|---|---|---|
| `TelemetryClient` | HMAC signing, push heartbeat/equity/position/log/regime | [`telemetry.py`](nexquant/superbot/telemetry.py:11) |
| `sync_config()` | Pull config + clés API + version check | [`telemetry.py`](nexquant/superbot/telemetry.py:159) |
| `TelemetryLoggingHandler` | Forward logs auto vers API | [`telemetry.py`](nexquant/superbot/telemetry.py:175) |
| `saveBrokerCredentials` | chiffrement + upsert | [`nexquant.functions.ts`](nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts:192) |

---

## 1. Phase de Conception & Analyse (Révisée)

### 1.1 Définition du Projet

**Objectif :** Transformer NexQuant en plateforme SaaS commerciale.

**Problème :** Pas d'accès à un outil pro de trading automatisé avec interface web et supervision temps réel.

**Utilisateurs cibles :**
- Traders intermédiaires
- Investisseurs passifs
- Scalpers crypto
- Gestionnaires de fonds

**Scope Phase 2 (Révisé) :**
1. **P1** — Monetisation Stripe (subscriptions + gating)
2. **P2** — Métriques avancées (Sharpe, PF, WinRate, Drawdown)
3. **P3** — Pilotage bidirectionnel (start/stop distant via polling + Realtime)
4. **P4** — Gestion stratégies web (CRUD + types de stratégies)
5. **P5** — Auto-update bot (updater.py + UI banner)
6. **P6** — Notifications (email Resend + in-app)
7. **P7** — PWA (bonus, priorité basse)

### 1.2 Etude de Faisabilité (Révisée)

**Ressources disponibles :**
- Backend Python bot : **existant** (telemetry, brokers, risk, strategy)
- Frontend React (TanStack Start) : **existant** (dashboard, admin, auth)
- Schema DB Supabase : **existant** (migration commerciale déjà déployée)
- API Ingest/Config : **existant** (HMAC, licence check, chiffrement)
- Serveur Stripe : **à implémenter**
- Métriques avancées : **à implémenter** (calculs Sharpe, PF, etc.)
- Notifications email : **à implémenter** (intégration Resend)

**Technologies :**
- Frontend : TanStack Start + React 19 + Supabase
- Bot : Python 3.11+ avec brokers Binance/Alpaca/MT5
- DB : PostgreSQL 15 (Supabase)
- Paiement : Stripe (+ Stripe Tax si UE)
- Email : Resend
- Realtime : Supabase Realtime (optionnel — polling comme mécanisme principal)

**Risques identifiés (Révisés) :**
1. Stripe webhooks non reçus (mitigation : logging + retry queue + alerte admin)
2. Latence Realtime (mitigation : **polling 30s comme mécanisme principal**, Realtime en bonus)
3. Calcul Sharpe erroné (mitigation : **tests avec fixtures CSV validées Excel**)
4. Compatibilité navigateur PWA (mitigation : **repousser PWA en P7**, priorité basse)
5. **Goulot d'étranglement développeur unique** (mitigation : réduire scope Semaine 2)
6. **TVA européenne non gérée par Stripe de base** (mitigation : évaluer Stripe Tax ou Lemon Squeezy)
7. **Migration utilisateurs existants** (mitigation : fenêtre de grâce 7 jours post-trial)

---

## 2. Phase de Spécifications Fonctionnelles

### 2.1 User Stories

**US1 — Abonnement :** En tant qu'utilisateur, je veux m'abonner à un plan payant pour continuer à utiliser le bot après la période d'essai.

**US2 — Métriques :** En tant qu'utilisateur, je veux voir mon Sharpe ratio et mon Profit Factor pour évaluer la performance de mon bot.

**US3 — Pilotage :** En tant qu'utilisateur, je veux démarrer/arrêter mon bot depuis le web pour le contrôler à distance.

**US4 — Stratégies :** En tant qu'utilisateur, je veux configurer mes stratégies depuis le dashboard pour personnaliser mon trading.

**US5 — Notifications :** En tant qu'utilisateur, je veux être notifié quand un trade est pris ou que mon bot s'arrête.

**US6 — Auto-update :** En tant qu'utilisateur, je veux que mon bot se mette à jour automatiquement pour toujours avoir la dernière version.

### 2.2 Exigences Fonctionnelles (Révisées)

**[RÉVISION]** Les RF marquées ★ s'appuient sur du code existant.

**RF1 — Paiement Stripe :** ★
- `POST /api/payment/create-checkout` : crée une session Stripe Checkout
- `POST /api/payment/webhook` : reçoit les événements Stripe
- Table `subscriptions` : lie `user_id` au `stripe_subscription_id`
- **Gating :** modifier [`ingest.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/ingest.ts:93) et [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:79) — remplacer la simple vérification `trial_end` par : `trial_end || subscription.status == active`
- Migration utilisateurs : tous les profils existants avec `trial_end` valide conservent l'accès jusqu'à expiration

**RF2 — Métriques :**
- Fonction SQL `calculate_daily_metrics(user_id)`
- Sharpe ratio 30/60/90 jours rolling annualisé
- Profit Factor, Win Rate, Max Drawdown, Calmar Ratio
- `GET /api/analytics/metrics` : retourne les KPIs calculés
- `GET /api/analytics/trades` : historique paginé et filtrable

**RF3 — Pilotage bidirectionnel :** ★
- **[Mécanisme primaire]** Bot pull config via `/api/public/config` toutes les 30s (déjà existant dans `sync_config()`)
- **[Mécanisme secondaire]** Bot souscrit aux changements Realtime de `bot_config` (optionnel, si la lib Python le supporte)
- `is_running = false` → bot arrête sa boucle de trading
- `risk_pct` / `score_min` modifiés → appliqués au prochain cycle
- **Le toggle `toggleBot()` existe déjà côté web** — voir [`dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx:156) et [`nexquant.functions.ts`](nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts:156)

**RF4 — Stratégies web :**
- Table `strategies` (user_id, name, type, params JSONB, is_active)
- Page `/strategies` : liste, créer, éditer, activer/désactiver
- Formulaire paramètres par type de stratégie
- Page `/webhook` : URL, secret, test

**RF5 — Notifications :**
- Table `notifications` (user_id, type, title, message, read)
- Table `notification_preferences`
- Notifications email (Resend) : trade TP/SL, daily loss, digest
- Notifications in-app (dropdown)

**RF6 — Auto-update bot :** ★
- Module `updater.py` : vérifie version au démarrage
- Download binaire depuis `app_versions.download_url`
- Remplacement + redémarrage automatique
- **Bannière web :** le champ `update.available` est déjà retourné par [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:143)
- **Vérification d'intégrité :** checksum SHA-256 du binaire

**RF7 — PWA (Bonus — Priorité Basse) :**
- `manifest.json` avec icônes
- Service worker pour cache offline
- Installation sur écran d'accueil mobile

### 2.3 Exigences Non-Fonctionnelles

**Performance :**
- Dashboard : chargement < 2s, rafraîchissement < 500ms
- API Ingest : réponse < 200ms
- Realtime : latence < 1s (fallback polling 30s si indisponible)
- Support : 100 utilisateurs concurrents

**Sécurité :**
- HMAC-SHA256 pour API publique (déjà en place)
- HTTPS uniquement
- JWT 24h + refresh rotation
- AES-256 pour clés API au repos (déjà en place)
- Rate limiting : 1000 req/min par utilisateur

**Disponibilité :**
- Uptime cible : 99.5%
- Graceful degradation si DB indisponible
- Backup quotidien S3
- Point-in-time recovery

**Maintenabilité :**
- Types TypeScript générés depuis Supabase (existant)
- Tests unitaires pour les calculs de métriques (avec fixtures CSV)
- Logs structurés pour debugging (déjà en place)
- Documentation API ouverte

---

## 3. Architecture & Choix Technologiques

### 3.1 Stack Technique (Confirmée)

**Frontend Web :**
- Framework : TanStack Start (React 19 + Vite)
- Routing : TanStack Router (file-based)
- State : TanStack Query (server state)
- UI : Shadcn/ui (Radix primitives)
- Charting : Recharts
- Auth : Supabase Auth + Google OAuth
- Realtime : Supabase Realtime

**Backend :**
- Server : TanStack Start (SSR + API routes)
- ORM : Supabase SDK (PostgreSQL)
- Validation : Zod
- Paiement : Stripe SDK
- Email : Resend SDK

**Bot Python :**
- Langage : Python 3.11+
- Brokers : ccxt (Binance), alpaca-py, MetaTrader5
- Data : pandas, numpy
- Télémétrie : requests + hmac (existant via `TelemetryClient`)
- Scheduler : threading + schedule

**Database :**
- Supabase (PostgreSQL 15)
- Tables existantes : `profiles`, `bot_status`, `bot_config`, `user_brokers`, `equity_snapshots`, `positions`, `market_regime`, `bot_logs`, `app_versions`
- Tables à créer : `subscriptions`, `daily_metrics`, `strategies`, `notifications`, `notification_preferences`

### 3.2 Architecture Applicative (Révisée)

**Modèle :** Client léger (SaaS web) + Bot local (client distribué).

Architecture :
```
[Utilisateur Web] → [TanStack Start SSR] → [Supabase DB]
                    → [Stripe API] (paiements)
                    → [Resend API] (emails)
                    
[Bot Python] → /api/public/ingest (push données) ★ EXISTANT
             → /api/public/config (pull configuration) ★ EXISTANT
             → Supabase Realtime (écoute commandes — OPTIONNEL)
```

**Flux de données :**
1. Bot pousse heartbeat/equity/positions/logs → `/api/public/ingest` ★ EXISTANT
2. Bot tire config → `/api/public/config` (clés déchiffrées) ★ EXISTANT
3. Webapp lit Supabase directement (via RLS policies) ★ EXISTANT
4. Stripe webhook → `/api/payment/webhook` → update subscriptions **NOUVEAU**
5. Bot pull `is_running` via config polling 30s ★ EXISTANT (mécanisme primaire)
6. Bot écoute Realtime sur `bot_config` **NOUVEAU** (mécanisme secondaire)

**Routes API :**
- `POST /api/payment/create-checkout` (crée session Stripe)
- `POST /api/payment/webhook` (reçoit événements Stripe)
- `GET /api/analytics/metrics` (retourne KPIs)
- `GET /api/analytics/trades` (historique paginé)
- `GET/POST /api/strategies` (CRUD strategies)
- `POST /api/notifications/preferences` (maj préférences)

---

## 4. Design UX/UI

### 4.1 Nouvelles Pages

**Page Billing (`/_authenticated/billing`) :**
- Carte du plan actuel avec prix et features
- Bouton Upgrade/Downgrade
- Historique des paiements
- Section Cancel subscription

**Page Strategies (`/_authenticated/strategies`) :**
- Liste des stratégies avec statut actif/inactif
- Carte par stratégie avec toggle on/off
- Formulaire paramètres par type (EMA, RSI, ATR)
- Bouton Ajouter une stratégie

**Page Webhook (`/_authenticated/webhook`) :**
- URL du webhook (copiable)
- Secret généré / regénéré
- Bouton Tester le webhook
- Instructions TradingView

**Page Notifications (`/_authenticated/notifications`) :**
- Préférences email, push, daily digest
- Types d'alertes (trades, risque, bot, licence)
- Horaires du digest quotidien

**Dashboard enrichi (modifications de l'existant) :**
- `MetricsGrid` : Sharpe, Win Rate, PF, Drawdown **NOUVEAU**
- `TradeHistoryTable` : liste paginée des trades clos (amélioration de l'existant)
- `EquityCurveAdvanced` : avec zone de drawdown (amélioration de l'existant)
- `BotStatusBadge` : running/stopped/error (amélioration de l'existant)
- Bannière mise à jour disponible (le champ `update.available` existe déjà)

---

## 5. Planification & Gestion de Projet

### 5.1 Méthodologie

**Approche :** Agile / Kanban avec sprints hebdomadaires.

**Outils :**
- Suivi : GitHub Issues / Projects
- Communication : Discord
- Documentation : GitHub Wiki + ce plan
- CI/CD : GitHub Actions (build + deploy automatique)

### 5.2 Roadmap Prioritaire (Révisée)

**[RÉVISION] Semaine 1** — Paiement & Abonnements (P1)
Sans cela, pas de revenus. C'est le bloc fondateur.

**[RÉVISION] Semaine 2a** — Métriques & Analytics (P2)
Les utilisateurs ont besoin de voir les performances pour justifier l'abonnement.

**[RÉVISION] Semaine 2b** — Pilotage bidirectionnel (P3)
Contrôler le bot depuis le web = valeur SaaS fondamentale. **S'appuie sur l'existant.**

**Semaine 3** — Stratégies web + Auto-update (P4+P5)
Configurer le bot depuis le web + mise à jour automatique.

**Semaine 4** — Notifications + QA + Documentation (P6+P7)
Qualité de vie, rétention, et préparation au lancement.

---

## 6. Découpage Phase 2 — Semaine par Semaine (Révisé)

### Semaine 1 : Monétisation & Paiement (P1)

**Objectif :** Permettre les souscriptions payantes via Stripe.

**Ce qui CHANGE dans l'existant :**

| Existant | Modification |
|---|---|
| [`ingest.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/ingest.ts:93) — vérif `trial_end` | Ajouter aussi vérif `subscription.status` |
| [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:79) — vérif `trial_end` | Ajouter aussi vérif `subscription.status` |
| [`dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx:132) — placeholder abonnement | Remplacer par vrai lien Stripe |
| [`nexquant.functions.ts`](nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts) | Ajouter `getSubscriptionStatus`, `createCheckoutSession` |

**Fichiers à créer :**
- [`nexquant/NexQuant_Web_App/src/routes/api/payment/create-checkout.ts`](nexquant/NexQuant_Web_App/src/routes/api/payment/create-checkout.ts) (POST endpoint Stripe)
- [`nexquant/NexQuant_Web_App/src/routes/api/payment/webhook.ts`](nexquant/NexQuant_Web_App/src/routes/api/payment/webhook.ts) (POST endpoint webhook Stripe)
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/billing.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/billing.tsx) (page abonnement)
- [`nexquant/NexQuant_Web_App/src/lib/stripe.ts`](nexquant/NexQuant_Web_App/src/lib/stripe.ts) (client Stripe serveur)
- [`nexquant/NexQuant_Web_App/src/components/BillingCard.tsx`](nexquant/NexQuant_Web_App/src/components/ui/BillingCard.tsx) (carte plan — dans `components/ui/`)
- [`nexquant/NexQuant_Web_App/src/components/SubscriptionStatus.tsx`](nexquant/NexQuant_Web_App/src/components/ui/SubscriptionStatus.tsx) (badge statut)
- [`nexquant/NexQuant_Web_App/supabase/migrations/20260701_subscriptions.sql`](nexquant/NexQuant_Web_App/supabase/migrations/20260701_subscriptions.sql)

**Tâches :**
1. Définir les tiers (Starter 29$, Pro 79$, Pro 199$)
2. Créer table `subscriptions` dans Supabase
3. Implémenter Stripe Checkout Session
4. Gérer webhook Stripe (completed, deleted, updated)
5. Modifier gating dans [`ingest.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/ingest.ts:93) + [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:79)
6. **Migration utilisateurs :** tous les profils avec `trial_end` futur gardent l'accès
7. UI page billing avec statut

**Acceptance :**
- User peut s'abonner via Stripe → statut `active` dans Supabase
- Bot reçoit 403 si abonnement expiré → s'arrête proprement (déjà existant via le check `is_expired` dans [`telemetry.py`](nexquant/superbot/telemetry.py:60))
- Admin voit statut subscription de chaque user

---

### Semaine 2a : Métriques & Analytics (P2)

**Objectif :** Afficher les KPIs de performance.

**Fichiers à créer :**
- [`nexquant/NexQuant_Web_App/src/lib/metrics.ts`](nexquant/NexQuant_Web_App/src/lib/metrics.ts) (moteur de calcul Sharpe, PF, WinRate)
- [`nexquant/NexQuant_Web_App/src/components/ui/MetricsGrid.tsx`](nexquant/NexQuant_Web_App/src/components/ui/MetricsGrid.tsx)
- [`nexquant/NexQuant_Web_App/src/components/ui/SharpeRatioCard.tsx`](nexquant/NexQuant_Web_App/src/components/ui/SharpeRatioCard.tsx)
- [`nexquant/NexQuant_Web_App/src/components/ui/EquityCurveAdvanced.tsx`](nexquant/NexQuant_Web_App/src/components/ui/EquityCurveAdvanced.tsx) (remplace l'équity curve simple)
- [`nexquant/NexQuant_Web_App/src/components/ui/TradeHistoryTable.tsx`](nexquant/NexQuant_Web_App/src/components/ui/TradeHistoryTable.tsx) (remplace la table historique)
- [`nexquant/NexQuant_Web_App/src/components/ui/BotStatusBadge.tsx`](nexquant/NexQuant_Web_App/src/components/ui/BotStatusBadge.tsx)
- [`nexquant/NexQuant_Web_App/tests/metrics.test.ts`](nexquant/NexQuant_Web_App/tests/metrics.test.ts)
- [`nexquant/NexQuant_Web_App/tests/fixtures/sharpe_test_data.csv`](nexquant/NexQuant_Web_App/tests/fixtures/sharpe_test_data.csv) (fixtures de test)
- [`nexquant/NexQuant_Web_App/supabase/migrations/20260702_daily_metrics.sql`](nexquant/NexQuant_Web_App/supabase/migrations/20260702_daily_metrics.sql)

**Fichiers à modifier :**
- [`nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts`](nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts) — ajouter `getMetrics()`, `getTradeHistory()`
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx) — remplacer KPIs simples par MetricsGrid

**Tâches :**
1. Fonction SQL `calculate_daily_metrics(user_id)`
2. Fonction serveur `getMetrics()` : Sharpe 30/60/90d, PF, WinRate
3. Fonction serveur `getTradeHistory()` : pagination + filtres
4. Remplacer les KPIs du dashboard par MetricsGrid
5. **Tests unitaires avec fixtures CSV** (comparer résultats vs numpy/excel)
6. Remplacer `EquityCurveAdvanced` avec zone de drawdown

**Acceptance :**
- Dashboard affiche Sharpe, WinRate, PF, Drawdown mis à jour en temps réel
- Les calculs sont validés par tests unitaires avec données de référence

---

### Semaine 2b : Pilotage Bidirectionnel (P3)

**Objectif :** Contrôler le bot à distance (start/stop, paramètres).

**[RÉVISION]** Le toggle start/stop existe déjà côté web. L'effort ici est :
1. Côté bot Python : consommer `is_running` du polling config pour démarrer/arrêter la boucle
2. Côté bot Python : optionnellement, souscrire au Realtime Supabase
3. Côté web : améliorer l'UX existant (feedback, état)

**Fichiers à créer :**
- [`nexquant/NexQuant_Web_App/src/components/ui/StartStopButton.tsx`](nexquant/NexQuant_Web_App/src/components/ui/StartStopButton.tsx) (extraction du composant depuis dashboard.tsx)
- [`nexquant/NexQuant_Web_App/src/hooks/useBotRealtime.ts`](nexquant/NexQuant_Web_App/src/hooks/useBotRealtime.ts) (Supabase Realtime hook — optionnel)

**Fichiers à modifier (Bot Python) :**
- [`superbot/telemetry.py`](superbot/telemetry.py) — ajouter Realtime subscription (optionnel) + améliorer `sync_config()`
- [`superbot/main.py`](superbot/main.py) — utiliser `is_running` du config pull pour la boucle de trading

**Fichiers à modifier (Web) :**
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx) — extraire le bouton start/stop et améliorer le feedback utilisateur

**Tâches :**
1. Bot Python : utiliser `config.is_running` du polling pour contrôler la boucle
2. Bot Python : (optionnel) souscrire aux changements Realtime sur `bot_config`
3. Bot Python : appliquer `risk_pct`, `score_min` au prochain cycle
4. Web : extraire et améliorer le composant start/stop
5. **Mécanisme primaire : polling 30s garantit que le bot réagit en < 30s**
6. **Mécanisme secondaire : Realtime réduit la latence à < 1s si fonctionnel**

**Acceptance :**
- Bouton Start/Stop sur le web arrête/repart le bot en moins de 30s (polling) ou 5s (Realtime)
- Modification `risk_pct` prise en compte au cycle suivant
- L'état du bot est correctement réflété dans le dashboard

---

### Semaine 3 : Stratégies Web, Webhook & Auto-Update (P4+P5)

**Objectif :** Gérer les stratégies depuis le web et mettre à jour le bot.

**Fichiers à créer (Web) :**
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/strategies.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/strategies.tsx)
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/risk.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/risk.tsx)
- [`nexquant/NexQuant_Web_App/src/components/ui/StrategyCard.tsx`](nexquant/NexQuant_Web_App/src/components/ui/StrategyCard.tsx)
- [`nexquant/NexQuant_Web_App/src/components/ui/StrategyConfigForm.tsx`](nexquant/NexQuant_Web_App/src/components/ui/StrategyConfigForm.tsx)
- [`nexquant/NexQuant_Web_App/src/components/ui/RiskConfigForm.tsx`](nexquant/NexQuant_Web_App/src/components/ui/RiskConfigForm.tsx)
- [`nexquant/NexQuant_Web_App/src/components/ui/WebhookSetup.tsx`](nexquant/NexQuant_Web_App/src/components/ui/WebhookSetup.tsx)
- [`nexquant/NexQuant_Web_App/src/components/ui/UpdateBanner.tsx`](nexquant/NexQuant_Web_App/src/components/ui/UpdateBanner.tsx)

**Fichiers à modifier (Web) :**
- [`nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts`](nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts) — ajouter CRUD strategies
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx) — intégrer UpdateBanner

**Fichiers à créer (Bot Python) :**
- [`superbot/updater.py`](superbot/updater.py) (module de mise à jour automatique)

**Fichiers à modifier (Bot Python) :**
- [`superbot/main.py`](superbot/main.py) — appeler updater au démarrage
- [`superbot/telemetry.py`](superbot/telemetry.py) — vérif version + download (le champ `update` existe déjà dans la réponse config)

**Tâches Stratégies :**
1. Table `strategies` + RLS policies
2. Page `/strategies` avec liste et création
3. Formulaire paramètres par type stratégie
4. API serveur CRUD strategies
5. Page `/webhook` avec URL et test

**Tâches Auto-Update :**
1. Module `updater.py` : vérifier version au démarrage
2. Download binaire depuis `app_versions.download_url`
3. **Vérification d'intégrité** (checksum SHA-256)
4. Remplacer executable + redémarrer
5. UI : UpdateBanner (le champ `update.available` existe déjà dans `config.ts`)

**Tâches Risk Config :**
1. Page `/risk` avec config complète
2. RiskConfigForm lié à `bot_config` (table existante)
3. Validation côté serveur des limites

---

### Semaine 4 : Notifications, PWA, QA & Documentation (P6+P7)

**Objectif :** Finaliser les features et préparer le lancement.

**Fichiers à créer :**
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/notifications.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/notifications.tsx)
- [`nexquant/NexQuant_Web_App/src/lib/notifications.ts`](nexquant/NexQuant_Web_App/src/lib/notifications.ts) (service email Resend)
- [`nexquant/NexQuant_Web_App/tests/metrics.test.ts`](nexquant/NexQuant_Web_App/tests/metrics.test.ts) (si pas fait en S2a)
- [`nexquant/NexQuant_Web_App/tests/fixtures/sharpe_test_data.csv`](nexquant/NexQuant_Web_App/tests/fixtures/sharpe_test_data.csv)
- [`nexquant/NexQuant_Web_App/tests/stripe.test.ts`](nexquant/NexQuant_Web_App/tests/stripe.test.ts)
- [`nexquant/NexQuant_Web_App/tests/ingest-security.test.ts`](nexquant/NexQuant_Web_App/tests/ingest-security.test.ts)
- [`nexquant/NexQuant_Web_App/supabase/migrations/20260704_notifications.sql`](nexquant/NexQuant_Web_App/supabase/migrations/20260704_notifications.sql)
- [`nexquant/NexQuant_Web_App/src/routes/legal/privacy.tsx`](nexquant/NexQuant_Web_App/src/routes/legal/privacy.tsx)
- [`nexquant/NexQuant_Web_App/src/routes/legal/terms.tsx`](nexquant/NexQuant_Web_App/src/routes/legal/terms.tsx)

**Fichiers à créer (PWA — Bonus) :**
- [`nexquant/NexQuant_Web_App/public/manifest.json`](nexquant/NexQuant_Web_App/public/manifest.json)
- [`nexquant/NexQuant_Web_App/public/sw.js`](nexquant/NexQuant_Web_App/public/sw.js) (service worker simple)

**Fichiers à modifier :**
- [`nexquant/NexQuant_Web_App/src/routes/__root.tsx`](nexquant/NexQuant_Web_App/src/routes/__root.tsx) (PWA link tags + meta)
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx) (polissage final)

**Tâches Notifications :**
1. Intégration Resend pour envoi emails
2. Notifications : trade TP/SL, daily loss, license expiry
3. Daily digest email (P&L, positions, métriques)
4. Table `notifications` + `notification_preferences`
5. Page `/notifications` avec configuration

**Tâches PWA (Bonus) :**
1. `manifest.json` avec icônes et theme color
2. Service worker pour cache offline basique
3. Installation sur écran accueil mobile

**Tâches QA :**
1. Tests unitaires métriques (valider Sharpe vs Excel avec fixtures CSV)
2. Tests intégration Stripe webhook (signature, idempotency)
3. Tests sécurité ingest (HMAC, rate limiting)
4. Pages légales (privacy, terms)
5. Documentation API
6. UI polissage final

---

## 7. Validation avec les Stakeholders

### 7.1 Points de Validation

**Avant implémentation (semaine 0) :**
- [ ] Valider ce plan révisé avec l'équipe
- [ ] Confirmer les tiers de prix (Starter 29$/Pro 79$/Pro 199$)
- [ ] **Décider Stripe Tax (addon) vs Lemon Squeezy (TVA incluse)**
- [ ] Valider le modèle de distribution (client distribué vs cloud)
- [ ] Vérifier la conformité légale (ToS, Privacy)
- [ ] **Valider la stratégie de migration des utilisateurs existants**

**Après semaine 1 :**
- [ ] Demo Stripe Checkout + webhook fonctionnel
- [ ] Vérifier que le gating bloque bien un bot sans abonnement (déjà testable avec `trial_end` expiré)

**Après semaine 2a :**
- [ ] Demo des métriques (Sharpe, PF, WinRate) avec données réelles

**Après semaine 2b :**
- [ ] Demo du contrôle start/stop à distance via polling

**Après semaine 3 :**
- [ ] Demo des stratégies configurables
- [ ] Demo de l'auto-update

**Après semaine 4 :**
- [ ] Demo complète de toutes les features
- [ ] Revue de code et sécurité
- [ ] Approbation finale pour déploiement

### 7.2 Processus

1. Demo chaque vendredi (15 min)
2. Feedback collecté dans GitHub Issues
3. Ajustements avant le sprint suivant
4. Validation finale avant mise en production

---

## 8. Préparation de l'Environnement

### 8.1 Repository & Branches

**Structure Git :**
- `main` : production
- `develop` : intégration
- `feat/phase2-stripe` : paiement
- `feat/phase2-metrics` : métriques
- `feat/phase2-bot-control` : pilotage
- `feat/phase2-strategies` : stratégies
- `feat/phase2-notifications` : notifications
- `feat/phase2-pwa` : PWA (bonus)

**Conventions :**
- `feat/` prefix pour nouvelles fonctionnalités
- `fix/` prefix pour corrections
- `chore/` pour maintenance
- Nom de commit : `type(scope): description`
- Exemple : `feat(stripe): ajouter checkout session endpoint`

### 8.2 CI/CD Pipeline

**GitHub Actions :**
- Build : `npm run build` (vérification TypeScript)
- Lint : `eslint .` (qualité code)
- Tests : `npm test` (tests unitaires)
- Deploy : automatique sur déploiement main

**Environnements :**
- Dev : localhost (vite dev)
- Staging : supabase project staging
- Production : supabase project prod + Vercel/Cloudflare

### 8.3 Variables d'Environnement

**Nouvelles variables nécessaires :**
- `STRIPE_SECRET_KEY` (clé Stripe serveur)
- `STRIPE_WEBHOOK_SECRET` (signature webhook)
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (frontend)
- `NEXT_PUBLIC_APP_URL` (URL de l'application)
- `RESEND_API_KEY` (envoi emails)

**Variables existantes (déjà utilisées) :**
- `NEXQUANT_ENCRYPTION_SECRET` (chiffrement AES-256)

---

## 9. Documentations Essentielles

### 9.1 Documentation Technique

**Architecture :** (ce document)
- Diagramme de flux
- Schéma de données
- Routes API
- Flux d'authentification

**API :**
- `POST /api/payment/create-checkout` : crée une session Stripe
- `POST /api/payment/webhook` : reçoit événements Stripe
- `GET /api/analytics/metrics` : retourne les KPIs calculés
- `GET /api/analytics/trades` : historique paginé
- `GET/POST /api/strategies` : CRUD strategies
- `POST /api/notifications/preferences` : maj préférences

### 9.2 Guides

**Setup développement local :**
1. Cloner le repo
2. Créer fichier `.env` (copier `.env.example`)
3. Installer dépendances : `cd nexquant/NexQuant_Web_App && npm install`
4. Démarrer dev : `npm run dev`
5. Lancer Supabase local : `supabase start`

**Conventions de code :**
- TypeScript strict mode
- Noms de fichiers en kebab-case
- Composants React en PascalCase
- Fonctions serveur préfixées par action (get, create, update)
- Validation des entrées avec Zod

**Standards :**
- Tests unitaires pour toute fonction de calcul
- Logs structurés (source, level, message) — déjà en place
- Gestion d'erreurs avec ErrorBoundary
- Responsive design (mobile d'abord)

### 9.3 Base de Connaissances

**FAQ courantes :**
- **Q:** Comment obtenir mes clés API Binance ?
  **R:** Suivre le guide dans le dashboard > Config Broker (existant)
- **Q:** Le bot peut-il trader sur plusieurs comptes ?
  **R:** Oui, chaque compte utilisateur est isolé
- **Q:** Les clés API sont-elles stockées en sécurité ?
  **R:** Oui, chiffrées AES-256 et jamais en clair dans les logs (existant)
- **Q:** Que se passe-t-il si mon abonnement expire ?
  **R:** Le bot s'arrête automatiquement et affiche un message (déjà implémenté côté bot via 403 handling)

**Troubleshooting :**
- Erreur 401 sur ingest : vérifier HMAC signature
- Erreur 403 sur config : vérifier abonnement ou trial
- Bot ne démarre pas : vérifier les logs dans le dashboard
- Stripe webhook 400 : vérifier `WEBHOOK_SECRET`

---

## 10. Annexes (Révisées)

### 10.1 Interfaces TypeScript (Nouvelles + Mises à Jour)

```typescript
// Types Phase 2 - NexQuant
// Les types des tables existantes (bot_status, equity_snapshots, etc.)
// sont déjà générés depuis Supabase dans:
//   nexquant/NexQuant_Web_App/src/integrations/supabase/types.ts

// 1. PAIEMENT & ABONNEMENT
export type SubscriptionTier = "starter" | "pro" | "professional";
export type SubscriptionStatus = "active" | "past_due" | "canceled" | "incomplete" | "trialing" | "expired";

export interface Subscription {
  id: string;
  user_id: string;
  stripe_subscription_id: string;
  stripe_customer_id: string;
  tier: SubscriptionTier;
  status: SubscriptionStatus;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  created_at: string;
}

// 2. MÉTRIQUES ET ANALYTICS
export interface PerformanceMetrics {
  sharpe_30d: number;
  sharpe_60d: number;
  sharpe_90d: number;
  profit_factor: number;
  win_rate: number;
  max_drawdown: number;
  calmar_ratio: number;
  total_trades: number;
  daily_pnl: number;
}

export interface PaginatedTrades {
  trades: Trade[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// 3. STRATÉGIES
export interface Strategy {
  id: string;
  user_id: string;
  name: string;
  type: string;
  params: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

// 4. RISK SETTINGS (s'appuie sur bot_config existante)
export interface RiskSettings {
  risk_per_trade: number;
  max_daily_loss: number;
  max_open_positions: number;
  kelly_fraction: number;
  use_correlation_adjustment: boolean;
  use_funding_rate_filter: boolean;
}
```

### 10.2 Migrations SQL (Nouvelles Tables Uniquement)

**[RÉVISION]** Les migrations suivantes sont **nouvelles** — ne pas dupliquer les tables déjà créées par `20260627105700_commercial_features.sql`.

```sql
-- Migration 4: Subscriptions (Stripe)
CREATE TABLE public.subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  tier TEXT NOT NULL DEFAULT 'starter',
  status TEXT NOT NULL DEFAULT 'incomplete',
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX idx_subscriptions_user ON public.subscriptions(user_id);

-- Migration 5: Daily Metrics & Strategies
CREATE TABLE public.daily_metrics (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  date DATE NOT NULL,
  equity NUMERIC NOT NULL,
  daily_pnl NUMERIC DEFAULT 0,
  sharpe_30d NUMERIC DEFAULT 0,
  profit_factor NUMERIC DEFAULT 0,
  win_rate NUMERIC DEFAULT 0,
  max_drawdown NUMERIC DEFAULT 0,
  trades_count INT DEFAULT 0,
  UNIQUE(user_id, date)
);

CREATE TABLE public.strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  params JSONB DEFAULT {},
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Migration 6: Notifications
CREATE TABLE public.notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.notification_preferences (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id),
  email_enabled BOOLEAN DEFAULT true,
  push_enabled BOOLEAN DEFAULT true,
  daily_digest BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 10.3 GitHub Issues (Révisés — Reflétant l'Existant)

**Issue 1: Intégration Stripe**
- Labels: `Phase-2`, `payment`, `P1`
- **Prérequis :** La table `profiles` a déjà `trial_end` et `ingest_token`. Les endpoints ingest/config existent déjà.
- Tâches: Checkout session, webhook, subscription gating (modifier ingest.ts + config.ts), UI billing
- **Fichiers impactés :** voir Semaine 1
- Definition of Done: User peut s'abonner, bot bloqué si expiré

**Issue 2: Métriques avancées**
- Labels: `Phase-2`, `analytics`, `P2`
- **Prérequis :** Le dashboard existe déjà avec KPIs basiques et courbe d'équité.
- Tâches: Sharpe, PF, WinRate, daily_metrics, remplacer les KPIs du dashboard
- Definition of Done: Dashboard affiche toutes les métriques

**Issue 3: Pilotage bidirectionnel**
- Labels: `Phase-2`, `bot-control`, `P3`
- **Prérequis :** Le toggle start/stop existe déjà côté web. Le bot a déjà `sync_config()`.
- Tâches: Consommer `is_running` du polling, Realtime optionnel
- Definition of Done: Bouton web arrête/repart le bot en moins de 30s

**Issue 4: Gestion stratégies web**
- Labels: `Phase-2`, `strategies`, `P4`
- Tâches: Table strategies, page /strategies, formulaire params, page /webhook
- Definition of Done: User peut configurer ses stratégies depuis le web

**Issue 5: Auto-update bot**
- Labels: `Phase-2`, `updater`, `P5`
- **Prérequis :** Table `app_versions` existe déjà. Le champ `update` est déjà retourné par config.ts.
- Tâches: `updater.py`, téléchargement, remplacement, restart
- Definition of Done: Bot se met à jour automatiquement

**Issue 6: Notifications**
- Labels: `Phase-2`, `notifications`, `P6`
- Tâches: Emails Resend, table notifications, page /notifications
- Definition of Done: User reçoit notifications email + in-app

**Issue 7: PWA (Bonus)**
- Labels: `Phase-2`, `PWA`, `P7`
- Tâches: manifest.json, service worker simple
- Definition of Done: User peut installer l'app sur mobile

**Issue 8: QA et pré-lancement**
- Labels: `Phase-2`, `QA`, `P5`
- Tâches: Tests (métriques, Stripe, sécurité), documentation, pages légales, polissage UI
- Definition of Done: Tout est prêt pour le déploiement

### 10.4 Arborescence des Fichiers (Révisée — Chemins Corrects)

```
nexquant/NexQuant_Web_App/src/
  routes/api/payment/
    create-checkout.ts        [NOUVEAU]
    webhook.ts                [NOUVEAU]
  routes/_authenticated/
    billing.tsx               [NOUVEAU]
    strategies.tsx            [NOUVEAU]
    risk.tsx                  [NOUVEAU]
    notifications.tsx         [NOUVEAU]
  components/
    ui/
      BillingCard.tsx         [NOUVEAU]
      MetricsGrid.tsx         [NOUVEAU]
      SharpeRatioCard.tsx     [NOUVEAU]
      EquityCurveAdvanced.tsx [NOUVEAU]
      TradeHistoryTable.tsx   [NOUVEAU]
      StrategyCard.tsx        [NOUVEAU]
      StrategyConfigForm.tsx  [NOUVEAU]
      RiskConfigForm.tsx      [NOUVEAU]
      WebhookSetup.tsx        [NOUVEAU]
      BotStatusBadge.tsx      [NOUVEAU]
      UpdateBanner.tsx        [NOUVEAU]
      NotificationsPanel.tsx  [NOUVEAU]
  hooks/
    useBotRealtime.ts         [NOUVEAU]
  lib/
    metrics.ts                [NOUVEAU]
    stripe.ts                 [NOUVEAU]
    notifications.ts          [NOUVEAU]
  tests/
    fixtures/
      sharpe_test_data.csv    [NOUVEAU]
    metrics.test.ts           [NOUVEAU]
    stripe.test.ts            [NOUVEAU]
    ingest-security.test.ts   [NOUVEAU]
  routes/legal/
    privacy.tsx               [NOUVEAU]
    terms.tsx                 [NOUVEAU]
supabase/migrations/
  20260701_subscriptions.sql  [NOUVEAU]
  20260702_daily_metrics.sql  [NOUVEAU]
  20260704_notifications.sql  [NOUVEAU]
superbot/
  updater.py                  [NOUVEAU]
```

### 10.5 Priorité des Fonctionnalités (Révisée)

```
P1 — Semaine 1   : Paiement Stripe (indispensable au business)
P2 — Semaine 2a  : Métriques (les users doivent voir les perfs)
P3 — Semaine 2b  : Pilotage bidirectionnel (valeur SaaS)
P4 — Semaine 3   : Stratégies web (valeur SaaS)
P5 — Semaine 3   : Auto-update + Notifs (qualité de vie)
P6 — Semaine 4   : Notifications email + in-app (rétention)
P7 — Semaine 4   : PWA (bonus)
```

---

## 11. Stratégie de Migration Utilisateurs (NOUVEAU)

**[RÉVISION]** Point critique non couvert dans la v1.

### Scénarios de migration

| Cas | Situation existante | Action |
|-----|---------------------|--------|
| **A** | User inscrit avec `trial_end` dans le futur | Conserve l'accès jusqu'à `trial_end`. À l'expiration, redirigé vers Stripe. |
| **B** | User avec `trial_end` déjà expiré | Bloqué immédiatement (déjà le cas via ingest.ts). Redirigé vers `/billing`. |
| **C** | User admin | Exempté de vérification (déjà le cas via `isAdmin` dans ingest.ts:95). |
| **D** | Nouvel utilisateur après déploiement Stripe | Redirigé vers Stripe après les 30 jours de trial. |

### Fenêtre de grâce

Pour éviter de bloquer des utilisateurs entre le déploiement Stripe et l'expiration réelle de leur trial :
- Tous les utilisateurs avec `trial_end` futur gardent leur accès
- Lors de la première connexion après déploiement, afficher un bandeau : *"Votre période d'essai se termine le XX/XX/XXXX. Choisissez un abonnement pour continuer."*
- À `trial_end + 7 days` (grace period), activation du blocage 403

### Logique de gating modifiée (ingest.ts + config.ts)

```typescript
const isExpired = !isAdmin && (
  (profile.trial_end && new Date() > new Date(profile.trial_end)
    && (!subscription || subscription.status !== 'active'))
  || (subscription && subscription.status === 'expired')
);
```

---

## 12. Stratégie de Test des Métriques (NOUVEAU)

**[RÉVISION]** Détail de la méthodologie de validation.

### Fixtures CSV

Fichier : [`tests/fixtures/sharpe_test_data.csv`](nexquant/NexQuant_Web_App/tests/fixtures/sharpe_test_data.csv)

```csv
date,equity,expected_sharpe_30d
2026-01-01,10000,
2026-01-02,10050,
2026-01-03,10020,
... (90 days of data)
```

### Calcul de référence

Les résultats attendus sont calculés avec :
```python
import numpy as np
returns = np.diff(equities) / equities[:-1]
sharpe = np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(252)
```

### Tests TypeScript

```typescript
// metrics.test.ts
import { calculateSharpe } from '@/lib/metrics';
import { parseCSV } from './fixtures/helpers';

describe('Sharpe Ratio', () => {
  it('calcule correctement le Sharpe 30j vs Python/numpy', () => {
    const data = parseCSV('sharpe_test_data.csv');
    const result = calculateSharpe(data.equities, 30);
    expect(result).toBeCloseTo(data.expected_sharpe_30d, 4);
  });
});
```

---

## 13. Risques Non Couverts dans la v1 (NOUVEAU)

| Risque | Impact | Mitigation |
|--------|--------|------------|
| **TVA européenne** | Stripe ne gère pas la TVA automatiquement | Évaluer Stripe Tax (addon) ou Lemon Squeezy avant la Semaine 1 |
| **Un seul développeur** | Semaine 2 originale trop chargée | Scinder en 2a + 2b comme proposé |
| **Pas de feature flags** | Migration Stripe binaire risquée | Ajouter `feature_flags` table + flag `stripe_enabled` pour activation progressive |
| **Monitoring Stripe** | Webhooks silencieux pendant des heures | Ajouter alerte admin si pas de webhook reçu en 24h |
| **Corruption binaire auto-update** | Bot cassé après mise à jour | Checksum SHA-256 + rollback automatique si échec |
| **Conflit PWA + SSR** | Service worker instable avec TanStack Start | PWA en bonus, service worker minimal (cache des assets statiques uniquement) |

---

## Conclusion

Ce plan révisé corrige les incohérences identifiées dans la v1 :

1. ✅ **Reconnaissance de l'existant** — migrations, endpoints, dashboard, bot télémetry
2. ✅ **Chemins de fichiers réels** — `nexquant/NexQuant_Web_App/src/` et `superbot/`
3. ✅ **Semaine 2 scindée** — métriques (2a) + pilotage (2b)
4. ✅ **Architecture réaliste** — polling comme mécanisme primaire, Realtime optionnel
5. ✅ **Stratégie de migration** — fenêtre de grâce de 7 jours
6. ✅ **Stratégie de test** — fixtures CSV pour validation des métriques
7. ✅ **PWA en bonus** — priorité basse, pas de blocage
8. ✅ **Risques identifiés** — TVA, goulot développeur unique, feature flags

**Prochaine étape :** Valider ce plan révisé avec les stakeholders, confirmer Stripe vs Lemon Squeezy, puis commencer l'implémentation Semaine 1 (Stripe).

---

*Document révisé le 27 juin 2026 — NexQuant Phase 2 Development Plan (Révision v2)*
