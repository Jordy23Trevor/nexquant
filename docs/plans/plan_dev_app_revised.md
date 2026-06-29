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
1. **P1** — Monétisation Lemon Squeezy (subscriptions + gating + conformité TVA UE)
2. **P2** — Métriques avancées (Sharpe, PF, WinRate, Drawdown)
3. **P3** — Pilotage bidirectionnel (start/stop distant via polling + Realtime)
4. **P4** — Gestion stratégies web (CRUD + types de stratégies)
5. **P5** — Auto-update bot (updater.py + UI banner)
6. **P6** — Notifications (email Resend + in-app)
7. **P7** — Conformité RGPD (Privacy Policy, droit effacement, export, cookies)
*Note : Le support PWA est repoussé en v1.1/v2 pour des raisons de focus MVP.*

### 1.2 Etude de Faisabilité (Révisée)

**Ressources disponibles :**
- Backend Python bot : **existant** (telemetry, brokers, risk, strategy)
- Frontend React (TanStack Start) : **existant** (dashboard, admin, auth)
- Schema DB Supabase : **existant** (migration commerciale déjà déployée)
- API Ingest/Config : **existant** (HMAC, licence check, chiffrement)
- Serveur Lemon Squeezy : **à implémenter**
- Métriques avancées : **à implémenter** (calculs Sharpe, PF, etc.)
- Notifications email : **à implémenter** (intégration Resend)

**Technologies :**
- Frontend : TanStack Start + React 19 + Supabase
- Bot : Python 3.11+ avec brokers ccxt (Binance Futures), Alpaca (officiels), et MetaTrader 5 (supporté mais expérimental/non-officiel)
- DB : PostgreSQL 15 (Supabase)
- Paiement : Lemon Squeezy (Merchant of Record pour la gestion automatique de la TVA EU)
- Email : Resend
- Realtime : Supabase Realtime (optionnel — polling comme mécanisme principal)

**Risques identifiés (Révisés) :**
1. Lemon Squeezy webhooks non reçus (mitigation : logging + retry queue + alerte admin)
2. Latence Realtime (mitigation : **polling 30s comme mécanisme principal**, Realtime en bonus)
3. Calcul Sharpe erroné (mitigation : **tests avec fixtures CSV validées Excel**)
4. **Timeline trop optimiste de 4 semaines** (mitigation : étendre le plan de développement sur 6 semaines et exclure la PWA de la v1)
5. **Goulot d'étranglement développeur unique** (mitigation : répartition plus granulaire sur 6 semaines au lieu de 4)
6. **TVA européenne et facturation complexe** (mitigation : résolu par le choix de Lemon Squeezy comme MoR)
7. **Migration utilisateurs existants** (mitigation : fenêtre de grâce 7 jours post-trial)
8. **Conformité RGPD** (mitigation : politique de confidentialité via iubenda.com, suppression/export de compte, politique de rétention des logs)

---

## 2. Phase de Spécifications Fonctionnelles

### 2.1 User Stories

**US1 — Abonnement :** En tant qu'utilisateur, je veux m'abonner à un plan payant pour continuer à utiliser le bot après la période d'essai.

**US2 — Métriques :** En tant qu'utilisateur, je veux voir mon Sharpe ratio et mon Profit Factor pour évaluer la performance de mon bot.

**US3 — Pilotage :** En tant qu'utilisateur, je veux démarrer/arrêter mon bot depuis le web pour le contrôler à distance.

**US4 — Stratégies :** En tant qu'utilisateur, je veux configurer mes stratégies depuis le dashboard pour personnaliser mon trading.

**US5 — Notifications :** En tant qu'utilisateur, je veux être notifié quand un trade est pris ou que mon bot s'arrête.

**US6 — Auto-update :** En tant qu'utilisateur, je veux que mon bot se mette à jour automatiquement pour toujours avoir la dernière version.

**RF1 — Paiement Lemon Squeezy :** ★
- Choix de Lemon Squeezy comme **Merchant of Record (MoR)** pour la gestion automatique de la facturation et de la TVA européenne.
- `POST /api/payment/create-checkout` : crée une session de paiement Lemon Squeezy Checkout.
- `POST /api/payment/webhook` : reçoit les webhooks Lemon Squeezy (abonnement créé, mis à jour, annulé).
- Table `subscriptions` : lie `user_id` à `lemon_squeezy_subscription_id`.
- **Gating :** modifier [`ingest.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/ingest.ts:93) et [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:79) — remplacer la simple vérification `trial_end` par : `trial_end || subscription.status == active` (conditionné à l'activation du feature flag `lemon_squeezy_enabled`).
- **Feature Flags :** La table `feature_flags` détermine l'activation de Lemon Squeezy (`lemon_squeezy_enabled = true`).
- Migration utilisateurs : tous les profils existants avec `trial_end` valide conservent l'accès jusqu'à expiration.

**RF2 — Métriques :**
- Fonction SQL `calculate_daily_metrics(user_id)`
- Sharpe ratio 30/60/90 jours rolling annualisé
- Profit Factor, Win Rate, Max Drawdown, Calmar Ratio
- `GET /api/analytics/metrics` : retourne les KPIs calculés
- `GET /api/analytics/trades` : historique paginé et filtrable

**RF3 — Pilotage bidirectionnel :** ★
- **[Mécanisme primaire]** Bot pull config via `/api/public/config` toutes les 30s (déjà existant dans `sync_config()`)
- **[Mécanisme secondaire]** Bot souscrit aux changements Realtime de `bot_config` si la lib Python le supporte. Cette fonctionnalité est pilotée par le flag `realtime_enabled` (Feature Flags).
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
- **Distribution du binaire :** Le binaire compilé est distribué via les GitHub Releases (le champ `download_url` dans `app_versions` pointe vers le release asset correspondant).
- **Signature du binaire :**
  - *Phase 1 (MVP) :* Sans signature. L'avertissement de sécurité de l'OS (ex: Windows SmartScreen ou warning de notarization macOS) est considéré comme acceptable. Des instructions d'ouverture manuelle (clic droit -> ouvrir) sont fournies dans le guide utilisateur.
  - *Phase 2 (Échelle) :* Signature automatisée via GitHub Actions + certificat de signature (Authenticode pour Windows, Apple Developer Certificate pour macOS).
- **Vérification d'intégrité :** checksum SHA-256 du binaire téléchargé vérifié avant remplacement.
- Remplacement + redémarrage automatique.
- **Bannière web :** le champ `update.available` est déjà retourné par [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:143)

**RF7 — PWA (Bonus — Repoussé en v1.1/v2) :**
- `manifest.json` avec icônes
- Service worker pour cache offline
- Installation sur écran d'accueil mobile

**RF8 — Conformité RGPD / GDPR (Nouveau) :**
- **Privacy Policy :** Création d'une page de politique de confidentialité détaillée (générée via iubenda.com pour un modèle basique conforme et gratuit).
- **Bandeau de consentement :** Intégration d'un bandeau de cookies/consentement RGPD sur le frontend.
- **Droit à l'effacement :** Implémentation de la route `DELETE /api/user/account` permettant à l'utilisateur de supprimer définitivement son compte et toutes ses clés API associées (`user_brokers`).
- **Droit à la portabilité (Export de données) :** Implémentation de la route `GET /api/user/export-data` (GDPR Art. 20) permettant d'exporter les données du profil et l'historique des transactions sous format JSON.
- **Politique de rétention :** Définition d'une durée de rétention des logs de trades système (ex: purge automatique des logs techniques au repos après 90 jours, archivage sécurisé des transactions réelles pendant 5 ans pour obligations fiscales).

**RF9 — Onboarding Broker Flexible (Nouveau) :**
- Le support pour connecter dynamiquement n'importe quel broker arbitraire via clé API est **exclu de la version v2** pour limiter la complexité et garantir la stabilité.
- La v2 se concentre exclusivement sur les brokers officiels : ccxt (Binance Futures) et Alpaca. Le support MetaTrader 5 est conservé en mode expérimental / non-officiel uniquement. L'onboarding flexible multi-broker générique est reporté en phase **v3**.

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
- Paiement : Lemon Squeezy (SDK ou API REST)
- Email : Resend SDK

**Bot Python :**
- Langage : Python 3.11+
- Brokers : ccxt (Binance Futures), alpaca-py (officiels) ; MetaTrader 5 (support expérimental / non-officiel)
- Data : pandas, numpy
- Télémétrie : requests + hmac (existant via `TelemetryClient`)
- Scheduler : threading + schedule

**Database :**
- Supabase (PostgreSQL 15)
- Tables existantes : `profiles`, `bot_status`, `bot_config`, `user_brokers`, `equity_snapshots`, `positions`, `market_regime`, `bot_logs`, `app_versions`
- Tables à créer : `subscriptions`, `daily_metrics`, `strategies`, `notifications`, `notification_preferences`, `feature_flags`

### 3.2 Architecture Applicative (Révisée)

**Modèle :** Client léger (SaaS web) + Bot local (client distribué).

Architecture :
```
[Utilisateur Web] → [TanStack Start SSR] → [Supabase DB]
                    → [Lemon Squeezy API] (paiements)
                    → [Resend API] (emails)
                    
[Bot Python] → /api/public/ingest (push données) ★ EXISTANT
             → /api/public/config (pull configuration) ★ EXISTANT
             → Supabase Realtime (écoute commandes — OPTIONNEL)
```

**Flux de données :**
1. Bot pousse heartbeat/equity/positions/logs → `/api/public/ingest` ★ EXISTANT
2. Bot tire config → `/api/public/config` (clés déchiffrées) ★ EXISTANT
3. Webapp lit Supabase directement (via RLS policies) ★ EXISTANT
4. Lemon Squeezy webhook → `/api/payment/webhook` → update subscriptions **NOUVEAU**
5. Bot pull `is_running` via config polling 30s ★ EXISTANT (mécanisme primaire)
6. Bot écoute Realtime sur `bot_config` **NOUVEAU** (mécanisme secondaire sous feature flag `realtime_enabled`)

**Routes API :**
- `POST /api/payment/create-checkout` (crée session Lemon Squeezy Checkout)
- `POST /api/payment/webhook` (reçoit événements Lemon Squeezy)
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
- `BotStatusBadge` : running/stopped/error (amélioration de l'exista### 5.2 Roadmap Prioritaire (Révisée — 6 Semaines)

**[RÉVISION] Semaine 1** — Paiement & Abonnements (P1 - Lemon Squeezy)
Mise en place de Lemon Squeezy (MoR) et configuration du gating. C'est le bloc commercial fondateur.

**[RÉVISION] Semaine 2** — Métriques & Analytics (P2)
Moteur de calcul des métriques avancées et intégration de la courbe d'équité complexe sur le dashboard.

**[RÉVISION] Semaine 3** — Pilotage bidirectionnel (P3)
Contrôle à distance du bot depuis le dashboard web via polling 30s + Supabase Realtime sous feature flag.

**Semaine 4** — Stratégies web & Webhook (P4)
Interface CRUD de gestion des stratégies et intégration de la réception de signaux webhook (TradingView).

**Semaine 5** — Auto-update bot (P5)
Développement de `updater.py` sur les GitHub Releases, vérification d'intégrité SHA-256 et bannière web.

**Semaine 6** — Notifications, RGPD, QA & Lancement (P6 + RGPD + QA)
Envoi de courriels (Resend), bandeau cookies, routes d'exportation/effacement RGPD, tests unitaires/intégration, et mise en production.

---

## 6. Découpage Phase 2 — Semaine par Semaine (Révisé — 6 Semaines)

### Semaine 1 : Monétisation & Paiement (P1)

**Objectif :** Permettre les souscriptions payantes via Lemon Squeezy (MoR pour gestion TVA EU).

**Ce qui CHANGE dans l'existant :**

| Existant | Modification |
|---|---|
| [`ingest.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/ingest.ts:93) — vérif `trial_end` | Ajouter aussi vérif `subscription.status` (si flag `lemon_squeezy_enabled` actif) |
| [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:79) — vérif `trial_end` | Ajouter aussi vérif `subscription.status` (si flag `lemon_squeezy_enabled` actif) |
| [`dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx:132) — placeholder abonnement | Remplacer par vrai lien Lemon Squeezy Checkout |
| [`nexquant.functions.ts`](nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts) | Ajouter `getSubscriptionStatus`, `createCheckoutSession` |

**Fichiers à créer :**
- [`nexquant/NexQuant_Web_App/src/routes/api/payment/create-checkout.ts`](nexquant/NexQuant_Web_App/src/routes/api/payment/create-checkout.ts) (POST endpoint Lemon Squeezy Checkout)
- [`nexquant/NexQuant_Web_App/src/routes/api/payment/webhook.ts`](nexquant/NexQuant_Web_App/src/routes/api/payment/webhook.ts) (POST endpoint webhook Lemon Squeezy)
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/billing.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/billing.tsx) (page abonnement)
- [`nexquant/NexQuant_Web_App/src/lib/lemonsqueezy.ts`](nexquant/NexQuant_Web_App/src/lib/lemonsqueezy.ts) (client d'intégration Lemon Squeezy)
- [`nexquant/NexQuant_Web_App/src/components/ui/BillingCard.tsx`](nexquant/NexQuant_Web_App/src/components/ui/BillingCard.tsx) (carte plan)
- [`nexquant/NexQuant_Web_App/src/components/ui/SubscriptionStatus.tsx`](nexquant/NexQuant_Web_App/src/components/ui/SubscriptionStatus.tsx) (badge statut)
- [`nexquant/NexQuant_Web_App/supabase/migrations/20260701_subscriptions.sql`](nexquant/NexQuant_Web_App/supabase/migrations/20260701_subscriptions.sql) (schema subscription + feature flags)

**Tâches :**
1. Créer le compte Lemon Squeezy, configurer le magasin et définir les plans (Starter 29$, Pro 79$, Pro 199$)
2. Créer la table `subscriptions` et la table `feature_flags` (avec flag `lemon_squeezy_enabled` à `false` par défaut) dans Supabase
3. Implémenter l'API de Checkout Lemon Squeezy (génère l'URL de paiement pré-remplie)
4. Configurer et implémenter le traitement du Webhook (events `subscription_created`, `subscription_updated`, `subscription_cancelled`)
5. Modifier le gating d'accès dans [`ingest.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/ingest.ts:93) + [`config.ts`](nexquant/NexQuant_Web_App/src/routes/api/public/config.ts:79) (vérifier l'abonnement si le flag `lemon_squeezy_enabled` est `true`)
6. **Migration utilisateurs :** tous les profils avec `trial_end` futur gardent l'accès sans abonnement requis
7. UI de la page billing avec cartes de prix et statut d'abonnement actif

**Acceptance :**
- L'utilisateur peut s'abonner via Lemon Squeezy → statut `active` mis à jour dans Supabase
- La TVA européenne est collectée automatiquement par Lemon Squeezy
- Le bot reçoit 403 si l'abonnement est expiré et s'arrête proprement
- Le flag `lemon_squeezy_enabled` permet d'activer/désactiver la vérification d'abonnement à chaud

---

### Semaine 2 : Métriques & Analytics (P2)

**Objectif :** Calculer et afficher les KPIs de performance quantitative (Sharpe, Profit Factor, Drawdown).

**Fichiers à créer :**
- [`nexquant/NexQuant_Web_App/src/lib/metrics.ts`](nexquant/NexQuant_Web_App/src/lib/metrics.ts) (moteur de calcul Sharpe, PF, WinRate)
- [`nexquant/NexQuant_Web_App/src/components/ui/MetricsGrid.tsx`](nexquant/NexQuant_Web_App/src/components/ui/MetricsGrid.tsx) (affichage grille KPIs)
- [`nexquant/NexQuant_Web_App/src/components/ui/SharpeRatioCard.tsx`](nexquant/NexQuant_Web_App/src/components/ui/SharpeRatioCard.tsx) (Sharpe annuel glissant)
- [`nexquant/NexQuant_Web_App/src/components/ui/EquityCurveAdvanced.tsx`](nexquant/NexQuant_Web_App/src/components/ui/EquityCurveAdvanced.tsx) (courbe avec zones de drawdown)
- [`nexquant/NexQuant_Web_App/src/components/ui/TradeHistoryTable.tsx`](nexquant/NexQuant_Web_App/src/components/ui/TradeHistoryTable.tsx) (historique paginé/filtrable)
- [`nexquant/NexQuant_Web_App/tests/metrics.test.ts`](nexquant/NexQuant_Web_App/tests/metrics.test.ts) (tests de validation)
- [`nexquant/NexQuant_Web_App/tests/fixtures/sharpe_test_data.csv`](nexquant/NexQuant_Web_App/tests/fixtures/sharpe_test_data.csv) (fixtures CSV)
- [`nexquant/NexQuant_Web_App/supabase/migrations/20260702_daily_metrics.sql`](nexquant/NexQuant_Web_App/supabase/migrations/20260702_daily_metrics.sql) (historique quotidien de l'équité)

**Fichiers à modifier :**
- [`nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts`](nexquant/NexQuant_Web_App/src/lib/nexquant.functions.ts) — ajouter `getMetrics()`, `getTradeHistory()`
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx) — remplacer les KPIs simples par `MetricsGrid` et `EquityCurveAdvanced`

**Tâches :**
1. Créer la fonction SQL `calculate_daily_metrics(user_id)` pour enregistrer l'équité historique quotidiennement
2. Implémenter le calcul TypeScript du Sharpe Ratio annualisé glissant (30/60/90 jours), Profit Factor et Win Rate
3. Créer des routes d'API pour paginer l'historique des trades clos
4. **Validation par Tests Unitaires :** Comparer les résultats du Sharpe Ratio TS avec les résultats Python/numpy grâce à la fixture CSV
5. Intégrer les zones de drawdown sur la courbe d'équité

**Acceptance :**
- Le dashboard affiche le Sharpe Ratio, Win Rate, Profit Factor et Drawdown validés
- Les tests unitaires passent et valident la précision des calculs par rapport au référentiel Python

---

### Semaine 3 : Pilotage Bidirectionnel (P3)

**Objectif :** Contrôler le bot en temps réel à distance (start/stop distant et modification de risque).

**Fichiers à modifier (Bot Python) :**
- [`superbot/telemetry.py`](superbot/telemetry.py) — améliorer `sync_config()` pour lire l'état `is_running` et les paramètres à chaud
- [`superbot/main.py`](superbot/main.py) — utiliser `is_running` du polling config pour suspendre/reprendre la boucle de trading principal

**Fichiers à modifier (Web) :**
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/dashboard.tsx) — bouton start/stop distant avec gestion d'état de chargement (feedback UX)
- [`nexquant/NexQuant_Web_App/src/hooks/useBotRealtime.ts`](nexquant/NexQuant_Web_App/src/hooks/useBotRealtime.ts) — souscription optionnelle Supabase Realtime sous le flag `realtime_enabled`

**Tâches :**
1. Configurer la boucle du bot Python pour interroger toutes les 30s (polling) l'API `/api/public/config`
2. Si `is_running` passe à `false`, suspendre l'envoi de nouveaux ordres et vider les files de traitement en cours
3. Mettre en place la table `feature_flags` et le flag `realtime_enabled` pour activer Supabase Realtime côté client si désiré
4. Appliquer immédiatement les modifications de `risk_pct` et `score_min` lors du prochain cycle d'évaluation du bot

**Acceptance :**
- Le bouton Web toggle met à jour Supabase et le bot s'arrête/reprend sous 30 secondes (polling) ou < 5 secondes (si Realtime activé)
- L'état de marche/arrêt du bot local est affiché sur le Dashboard Web

---

### Semaine 4 : Stratégies Web & Webhook (P4)

**Objectif :** Permettre le CRUD des stratégies depuis le web et la réception de signaux externes (TradingView).

**Fichiers à créer :**
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/strategies.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/strategies.tsx) (page de gestion)
- [`nexquant/NexQuant_Web_App/src/components/ui/StrategyCard.tsx`](nexquant/NexQuant_Web_App/src/components/ui/StrategyCard.tsx) (composant carte stratégie)
- [`nexquant/NexQuant_Web_App/src/components/ui/StrategyConfigForm.tsx`](nexquant/NexQuant_Web_App/src/components/ui/StrategyConfigForm.tsx) (formulaire dynamique de configuration)
- [`nexquant/NexQuant_Web_App/src/components/ui/WebhookSetup.tsx`](nexquant/NexQuant_Web_App/src/components/ui/WebhookSetup.tsx) (instructions et clé webhook TradingView)
- [`nexquant/NexQuant_Web_App/supabase/migrations/20260703_strategies.sql`](nexquant/NexQuant_Web_App/supabase/migrations/20260703_strategies.sql)

**Tâches :**
1. Créer la table `strategies` (user_id, name, type, params JSONB, is_active)
2. Développer l'interface d'administration des stratégies (CRUD avec formulaire de paramètres dynamiques selon le type d'indicateur)
3. Implémenter l'endpoint `/api/public/webhook` pour recevoir les alertes JSON formatées par TradingView (vérification par clé secrète générée)
4. Lier les stratégies actives aux configurations envoyées au bot Python via `/api/public/config`

**Acceptance :**
- L'utilisateur peut ajouter, activer et paramétrer une stratégie EMA/RSI sur le dashboard
- Le bot Python charge les paramètres de la stratégie active lors de sa synchronisation

---

### Semaine 5 : Auto-Update Bot (P5)

**Objectif :** Déployer et automatiser la mise à jour du bot client Python.

**Fichiers à créer :**
- [`superbot/updater.py`](superbot/updater.py) (module autonome de mise à jour)
- [`nexquant/NexQuant_Web_App/src/components/ui/UpdateBanner.tsx`](nexquant/NexQuant_Web_App/src/components/ui/UpdateBanner.tsx) (bannière de mise à jour web)

**Fichiers à modifier :**
- [`superbot/main.py`](superbot/main.py) — exécuter la vérification `updater.py` au démarrage du programme
- [`superbot/telemetry.py`](superbot/telemetry.py) — télécharger le binaire et valider son intégrité

**Tâches :**
1. **Distribution :** Publier les binaires compilés sur les GitHub Releases du projet.
2. **Intégrité :** Implémenter la vérification du hash SHA-256 du binaire téléchargé par rapport au hash fourni par l'API config.
3. **Signature (Stratégie progressive) :**
   - *Phase 1 (MVP) :* Distribution sans signature commerciale (les warnings de l'OS type Windows SmartScreen sont acceptés ; notice d'installation fournie).
   - *Phase 2 :* Intégration de la signature Authenticode/Apple via GitHub Actions.
4. Développer le remplacement à chaud du fichier exécutable et le redémarrage automatique du processus principal.

**Acceptance :**
- Le bot détecte une version supérieure, télécharge le binaire depuis les GitHub Releases, vérifie son SHA-256, l'applique et redémarre de manière autonome.

---

### Semaine 6 : Notifications, RGPD, QA & Lancement (P6 + RGPD + QA)

**Objectif :** Mettre l'application en conformité RGPD, ajouter les notifications de rétention et finaliser la QA.

**Fichiers à créer :**
- [`nexquant/NexQuant_Web_App/src/routes/_authenticated/notifications.tsx`](nexquant/NexQuant_Web_App/src/routes/_authenticated/notifications.tsx) (préférences et historique)
- [`nexquant/NexQuant_Web_App/src/lib/notifications.ts`](nexquant/NexQuant_Web_App/src/lib/notifications.ts) (intégration service email Resend)
- [`nexquant/NexQuant_Web_App/src/routes/legal/privacy.tsx`](nexquant/NexQuant_Web_App/src/routes/legal/privacy.tsx) (Politique de Confidentialité)
- [`nexquant/NexQuant_Web_App/src/routes/legal/terms.tsx`](nexquant/NexQuant_Web_App/src/routes/legal/terms.tsx) (ToS)
- [`nexquant/NexQuant_Web_App/tests/gdpr.test.ts`](nexquant/NexQuant_Web_App/tests/gdpr.test.ts)
- [`nexquant/NexQuant_Web_App/supabase/migrations/20260706_notifications_gdpr.sql`](nexquant/NexQuant_Web_App/supabase/migrations/20260706_notifications_gdpr.sql)

**Tâches :**
1. **Conformité RGPD :**
   - Rédiger la page Privacy Policy (via iubenda.com).
   - Ajouter une bannière de consentement cookies sur le site.
   - Créer l'API `DELETE /api/user/account` (droit à l'effacement complet des données et clés API brokers).
   - Créer l'API `GET /api/user/export-data` pour exporter les données utilisateur au format JSON (GDPR Art. 20).
   - Mettre en place un cron de purge automatique des logs système datant de plus de 90 jours (durée de rétention).
2. **Notifications :** Intégrer Resend pour notifier par courriel l'utilisateur lors de déclenchements de TP/SL, drawdown critique ou fin de validité de licence.
3. **QA & Sécurité :** Tests d'intégration sur les webhooks Lemon Squeezy, vérification de la robustesse des signatures HMAC d'ingest, et audits finaux.

**Acceptance :**
- L'utilisateur peut supprimer son compte et exporter ses données conformément au RGPD
- Les courriels de notification sont envoyés correctement via Resend
- Les tests de sécurité et de conformité passent avec succès

---

## 7. Validation avec les Stakeholders

### 7.1 Points de Validation

**Avant implémentation (semaine 0) :**
- [ ] Valider ce plan révisé avec l'équipe (6 semaines de timeline)
- [ ] Confirmer les tiers de prix (Starter 29$/Pro 79$/Pro 199$)
- [x] **Décider Stripe Tax (addon) vs Lemon Squeezy (TVA incluse)** $\rightarrow$ *Décision : Lemon Squeezy choisi pour simplifier la TVA et la comptabilité.*
- [ ] Valider le modèle de distribution (client distribué vs cloud)
- [ ] Vérifier la conformité légale (ToS, Privacy Policy, cookies)
- [ ] Valider la stratégie de migration des utilisateurs existants

**Après semaine 1 (Lemon Squeezy) :**
- [ ] Demo Lemon Squeezy Checkout + webhook fonctionnel
- [ ] Vérifier que le gating bloque bien un bot sans abonnement (avec feature flag `lemon_squeezy_enabled`)

**Après semaine 2 (Métriques) :**
- [ ] Demo des métriques (Sharpe, PF, WinRate) avec données réelles et passage des tests CSV

**Après semaine 3 (Pilotage) :**
- [ ] Demo du contrôle start/stop à distance via polling et Supabase Realtime

**Après semaine 4 (Stratégies) :**
- [ ] Demo des stratégies configurables et test du webhook TradingView

**Après semaine 5 (Auto-Update) :**
- [ ] Demo de l'auto-update avec validation SHA-256 (binaire non-signé Phase 1)

**Après semaine 6 (Notifications, RGPD & QA) :**
- [ ] Demo de la suppression de compte, de l'export des données et du bandeau cookies (RGPD)
- [ ] Demo complète de toutes les features
- [ ] Revue de code, audit de sécurité et approbation finale pour déploiement**Après semaine 1 :**
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
- `LEMON_SQUEEZY_API_KEY` (clé d'API Lemon Squeezy serveur)
- `LEMON_SQUEEZY_WEBHOOK_SECRET` (signature de validation du webhook)
- `LEMON_SQUEEZY_STORE_ID` (identifiant unique de la boutique)
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
- `POST /api/payment/create-checkout` : crée une session de checkout Lemon Squeezy
- `POST /api/payment/webhook` : reçoit les événements de webhook Lemon Squeezy
- `GET /api/analytics/metrics` : retourne les KPIs calculés
- `GET /api/analytics/trades` : historique paginé
- `GET/POST /api/strategies` : CRUD strategies
- `POST /api/notifications/preferences` : maj préférences
- `DELETE /api/user/account` : suppression de compte et des clés brokers (RGPD)
- `GET /api/user/export-data` : export des données de profil et de trades en JSON (RGPD)

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
-- Migration 4: Subscriptions (Lemon Squeezy) & Feature Flags
CREATE TABLE public.subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  lemon_squeezy_customer_id TEXT,
  lemon_squeezy_subscription_id TEXT,
  tier TEXT NOT NULL DEFAULT 'starter',
  status TEXT NOT NULL DEFAULT 'unpaid',
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX idx_subscriptions_user ON public.subscriptions(user_id);

CREATE TABLE public.feature_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  is_enabled BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Seed feature flags par défaut
INSERT INTO public.feature_flags (name, description, is_enabled) VALUES
  ('lemon_squeezy_enabled', 'Activer la vérification des abonnements Lemon Squeezy pour le gating', false),
  ('realtime_enabled', 'Activer la synchronisation Realtime du bot via Supabase Realtime', false);

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

**Issue 1: Intégration Lemon Squeezy**
- Labels: `Phase-2`, `payment`, `P1`
- **Prérequis :** La table `profiles` a déjà `trial_end` et `ingest_token`. Les endpoints ingest/config existent déjà.
- Tâches: Checkout session Lemon Squeezy, traitement du webhook (created, updated, cancelled), subscription gating (modifier ingest.ts + config.ts), UI billing.
- **Fichiers impactés :** voir Semaine 1
- Definition of Done: L'utilisateur peut s'abonner, la TVA est gérée de manière transparente, et le bot est bloqué si l'abonnement expire (sous condition du flag `lemon_squeezy_enabled`).

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
- Tâches: `updater.py` autonome, téléchargement via GitHub Releases, validation SHA-256, Phase 1 (binaire non-signé) et Phase 2 (signature Authenticode/Apple via Actions).
- Definition of Done: Le bot télécharge le binaire intègre depuis GitHub Releases et redémarre avec succès.

**Issue 6: Notifications & RGPD**
- Labels: `Phase-2`, `notifications`, `P6`, `GDPR`
- Tâches: Emails Resend, tables notifications/preferences, page de politique de confidentialité (iubenda), bandeau de cookies, route `DELETE /api/user/account` (effacement), route `GET /api/user/export-data` (export), purge des logs techniques > 90 jours.
- Definition of Done: L'utilisateur est notifié et dispose d'un contrôle total de ses données personnelles (exportation et effacement) conformément au RGPD.

**Issue 7: PWA (Bonus)**
- Labels: `Phase-2`, `PWA`, `P7`
- Tâches: manifest.json, service worker simple (repoussé en v1.1/v2).
- Definition of Done: Livré comme bonus hors scope v1.

**Issue 8: QA et pré-lancement**
- Labels: `Phase-2`, `QA`
- Tâches: Tests (métriques Sharpe vs Excel, Lemon Squeezy webhook signature, sécurité ingest), documentation, pages ToS/Privacy, polissage UI.
- Definition of Done: Tous les tests unitaires et de sécurité passent, et les pages légales sont en ligne.

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

### 10.5 Priorité des Fonctionnalités (Révisée — 6 Semaines)

```
P1 — Semaine 1 : Paiement Lemon Squeezy (gestion TVA européenne)
P2 — Semaine 2 : Métriques & Analytics (performance quantitative)
P3 — Semaine 3 : Pilotage bidirectionnel (start/stop via config polling)
P4 — Semaine 4 : Stratégies web & Webhooks TradingView
P5 — Semaine 5 : Auto-update bot (distribution GitHub Releases)
P6 — Semaine 6 : Notifications, Conformité RGPD, QA & Lancement
P7 — Post-v1   : PWA (PWA repoussée en v1.1/v2)
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
// Si le flag feature_flags.lemon_squeezy_enabled est actif, appliquer la vérification d'abonnement
const isExpired = !isAdmin && (
  lemonSqueezyEnabled ? (
    (profile.trial_end && new Date() > new Date(profile.trial_end)
      && (!subscription || subscription.status !== 'active'))
    || (subscription && subscription.status === 'expired')
  ) : (
    profile.trial_end && new Date() > new Date(profile.trial_end)
  )
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
| **TVA européenne** | Stripe Tax trop complexe comptablement | Choix définitif de Lemon Squeezy comme Merchant of Record (MoR) |
| **Un seul développeur** | Surcharge de travail et retards de livraison | Passage du plan de 4 à 6 semaines, simplification du scope v1 (PWA post-v1) |
| **Pas de feature flags** | Lancement de fonctionnalités critiques risqué | Table `feature_flags` intégrée pour activer/désactiver Lemon Squeezy ou Realtime à chaud |
| **Monitoring Webhook** | Webhooks de paiement silencieux pendant des heures | Alertes admin configurées si aucun webhook reçu en 24h |
| **Corruption binaire auto-update** | Bot hors service suite à une mauvaise mise à jour | Checksum SHA-256 vérifié et conservation de la version précédente pour rollback |
| **Signature de binaire updater** | Blocage par Defender ou Gatekeeper | Phase 1 (MVP) : non-signé avec guide d'aide ; Phase 2 : signature automatique avec GitHub Actions |
| **Conformité légale / RGPD** | Non-conformité avec réglementation européenne | Bandeau de consentement, Privacy Policy (iubenda), routes d'effacement complet et d'exportation |

---

## Conclusion

Ce plan révisé intègre l'ensemble des recommandations d'amélioration identifiées :

1. ✅ **Décision Bloquante Monétisation** — Choix de Lemon Squeezy (MoR) pour s'affranchir de la gestion comptable de la TVA européenne.
2. ✅ **Conformité RGPD** — Inclusion de la politique de confidentialité, du consentement des cookies, du droit à l'effacement et de la portabilité des données.
3. ✅ **Clarification MT5** — MetaTrader 5 est officiellement qualifié de broker expérimental / non-officiel dans la stack.
4. ✅ **Distribution de l'Auto-update** — Distribution documentée via GitHub Releases (avertissement de signature Phase 1, signature automatisée Phase 2).
5. ✅ **Timeline Réaliste** — Extension à 6 semaines pour garantir la faisabilité par un développeur unique.
6. ✅ **Feature Flags Formalisés** — Modèle SQL et API configurés avec des flags pour un déploiement sécurisé.
7. ✅ **Broker Flexible Clarifié** — La connexion à un broker flexible arbitraire est officiellement reportée en phase v3.

**Prochaine étape :** Valider ce plan révisé avec les stakeholders et commencer l'implémentation Semaine 1 (Lemon Squeezy).

---

*Document révisé le 28 juin 2026 — NexQuant Phase 2 Development Plan (Révision v2)*
