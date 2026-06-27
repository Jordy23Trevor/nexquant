# Plan de Developpement NexQuant — Phase 2

> **Document master** — 27 juin 2026
> Ce plan couvre l'integralite du cycle de vie du projet Phase 2.

---

test
## 1. Phase de Conception & Analyse

### 1.1 Definition du Projet

**Objectif :** Transformer NexQuant en plateforme SaaS commerciale.

**Probleme :** Pas d'acces a un outil pro de trading automatise avec interface web et supervision temps reel.

**Utilisateurs cibles :**
- Traders intermediaires
- Investisseurs passifs
- Scalpers crypto
- Gestionnaires de fonds

**Scope Phase 2 :**
1. Monetisation Stripe
2. Metriques avancees
3. Pilotage bidirectionnel
4. Gestion strategies web
5. Auto-update bot
6. Notifications + PWA

### 1.2 Etude de Faisabilite

**Ressources disponibles :**
- Backend Python bot : pret
- Frontend React (TanStack Start) : pret
- Schema DB Supabase : pret
- API Ingest/Config : pret
- Serveur Stripe : a implementer

**Technologies :**
- Frontend : TanStack Start + React 19 + Supabase
- Bot : Python 3.11+ avec brokers Binance/Alpaca/MT5
- DB : PostgreSQL 15 (Supabase)
- Paiement : Stripe
- Email : Resend/SendGrid
- Realtime : Supabase Realtime

**Risques identifies :**
1. Stripe webhooks non recus (mitigation : logging + retry)
2. Latence Realtime (mitigation : fallback polling 30s)
3. Calcul Sharpe errone (mitigation : tests unitaires vs Excel)
4. Compatibilite navigateur PWA (mitigation : test iOS/Android)

## 2. Phase de Specifications Fonctionnelles

### 2.1 User Stories

**US1 - Abonnement :** En tant qu'utilisateur, je veux m'abonner a un plan payant pour continuer a utiliser le bot apres la periode d'essai.

**US2 - Metriques :** En tant qu'utilisateur, je veux voir mon Sharpe ratio et mon Profit Factor pour evaluer la performance de mon bot.

**US3 - Pilotage :** En tant qu'utilisateur, je veux demarrer/arreter mon bot depuis le web pour le controler a distance.

**US4 - Strategies :** En tant qu'utilisateur, je veux configurer mes strategies depuis le dashboard pour personnaliser mon trading.

**US5 - Notifications :** En tant qu'utilisateur, je veux etre notifie quand un trade est pris ou que mon bot s'arrete.

**US6 - Auto-update :** En tant qu'utilisateur, je veux que mon bot se mette a jour automatiquement pour toujours avoir la derniere version.

### 2.2 Exigences Fonctionnelles

**RF1 - Paiement Stripe :**
- POST /api/payment/create-checkout : cree une session Stripe Checkout
- POST /api/payment/webhook : recoit les evenements Stripe
- Table subscriptions : lie user_id au stripe_subscription_id
- Gating : /api/public/ingest et /api/public/config verifient le statut

**RF2 - Metriques :**
- Fonction SQL calculate_daily_metrics(user_id)
- Sharpe ratio 30/60/90 jours rolling annualise
- Profit Factor, Win Rate, Max Drawdown, Calmar Ratio
- GET /analytics/metrics : retourne les KPIs calcules
- GET /analytics/trades : historique pagine et filtrable

**RF3 - Pilotage bidirectionnel :**
- Bot souscrit aux changements Realtime de bot_config
- Bot sync config via /api/public/config toutes les 30s
- is_running = false -> bot arrete sa boucle de trading
- risk_pct/score_min modifies -> appliques au prochain cycle

**RF4 - Strategies web :**
- Table strategies (user_id, name, type, params JSONB, is_active)
- Page /strategies : liste, creer, editer, activer/desactiver
- Formulaire parametres par type de strategie
- Page /webhook : URL, secret, test

**RF5 - Notifications :**
- Table notifications (user_id, type, title, message, read)
- Table notification_preferences
- Notifications email (Resend) : trade TP/SL, daily loss, digest
- Notifications in-app (dropdown)

**RF6 - Auto-update bot :**
- Module updater.py : verifie version au demarrage
- Download binaire depuis app_versions.download_url
- Remplacement + redemarrage automatique
- Banniere web si mise a jour disponible

**RF7 - PWA :**
- manifest.json avec icones
- Service worker pour offline
- Installation sur ecran d'accueil mobile

### 2.3 Exigences Non-Fonctionnelles

**Performance :**
- Dashboard : chargement < 2s, rafraichissement < 500ms
- API Ingest : reponse < 200ms
- Realtime : latence < 1s
- Support : 100 utilisateurs concurrents

**Securite :**
- HMAC-SHA256 pour API publique
- HTTPS uniquement
- JWT 24h + refresh rotation
- AES-256 pour cles API au repos
- Rate limiting : 1000 req/min par utilisateur

**Disponibilite :**
- Uptime cible : 99.5%
- Graceful degradation si DB indisponible
- Backup quotidien S3
- Point-in-time recovery

**Maintenabilite :**
- Types TypeScript generes depuis Supabase
- Tests unitaires pour les calculs de metriques
- Logs structures pour debugging
- Documentation API ouverte

## 3. Architecture & Choix Technologiques

### 3.1 Stack Technique (Confirmee)

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
- Telemetry : requests + hmac
- Scheduler : threading + schedule

**Database :**
- Supabase (PostgreSQL 15)
- Tables : profiles, subscriptions, strategies
- Time-series : equity_snapshots, daily_metrics
- Logs : bot_logs, notifications

### 3.2 Architecture Applicative

**Modele :** Client leger (SaaS web) + Bot local (client distribue).

Architecture :
`
[Utilisateur Web] -> [TanStack Start SSR] -> [Supabase DB]
                    -> [Stripe API] (paiements)
                    -> [Resend API] (emails)
                    
[Bot Python] -> /api/public/ingest (push donnees)
             -> /api/public/config (pull configuration)
             -> Supabase Realtime (ecoute commandes)
`

**Flux de donnees :**
1. Bot pousse heartbeat/equity/positions/logs -> /api/public/ingest
2. Bot tire config -> /api/public/config (cles dechiffrees)
3. Webapp lit Supabase directement (via RLS policies)
4. Stripe webhook -> /api/payment/webhook -> update subscriptions
5. Bot ecoute Realtime sur bot_config (is_running, risk_pct)

**Routes API :**
- POST /api/payment/create-checkout (cree session Stripe)
- POST /api/payment/webhook (recsuper evenements Stripe)
- GET /api/analytics/metrics (retourne KPIs)
- GET /api/analytics/trades (historique pagine)
- GET/POST /api/strategies (CRUD strategies)
- POST /api/notifications/preferences (maj preferences)

## 4. Design UX/UI

### 4.1 Nouvelles Pages

**Page Billing (/billing) :**
- Carte du plan actuel avec prix et features
- Bouton Upgrade/Downgrade
- Historique des paiements
- Section Cancel subscription

**Page Strategies (/strategies) :**
- Liste des strategies avec statut actif/inactif
- Carte par strategie avec toggle on/off
- Formulaire parametres par type (EMA, RSI, ATR)
- Bouton Ajouter une strategie

**Page Webhook (/webhook) :**
- URL du webhook (cpiable)
- Secret genere / regenere
- Bouton Tester le webhook
- Instructions TradingView

**Page Notifications (/notifications) :**
- Preferences email, push, daily digest
- Types d alertes (trades, risque, bot, licence)
- Horaires du digest quotidien

**Dashboard enrichi :**
- MetricsGrid : Sharpe, Win Rate, PF, Drawdown
- TradeHistoryTable : liste paginee des trades clos
- EquityCurveAdvanced : avec zone de drawdown
- BotStatusBadge : running/stopped/error
- Banniere mise a jour disponible

## 5. Planification & Gestion de Projet

### 5.1 Methodologie

**Approche :** Agile / Kanban avec sprints hebdomadaires.

**Outils :**
- Suivi : GitHub Issues / Projects
- Communication : Discord
- Documentation : GitHub Wiki + ce plan
- CI/CD : GitHub Actions (build + deploy automatique)

### 5.2 Roadmap Prioritaire

**Priorite 1 (Semaine 1) : Paiement & Abonnements**
Sans cela, pas de revenus. C'est le bloc fondateur.

**Priorite 2 (Semaine 2) : Metriques & Analytics**
Les utilisateurs ont besoin de voir les performances pour justifier l'abonnement.

**Priorite 3 (Semaine 2-3) : Pilotage bidirectionnel & Strategies**
Controler le bot depuis le web = valeur SaaS fondamentale.

**Priorite 4 (Semaine 3-4) : Auto-update, Notifications, PWA**
Fonctionnalites de qualite de vie et retention.

## 6. Decoupage Phase 2 - Semaine par Semaine

### Semaine 1 : Monetisation & Paiement (P1)

**Objectif :** Permettre les souscriptions payantes via Stripe.

**Fichiers a creer :**
- routes/api/payment/create-checkout.ts (POST endpoint Stripe)
- routes/api/payment/webhook.ts (POST endpoint webhook Stripe)
- routes/_authenticated/billing.tsx (page abonnement)
- lib/stripe.ts (client Stripe serveur)
- components/BillingCard.tsx (carte plan)
- components/SubscriptionStatus.tsx (badge statut)
- supabase/migrations/20260628000000_subscriptions.sql

**Fichiers a modifier :**
- routes/api/public/ingest.ts (ajouter verif subscription)
- routes/api/public/config.ts (retourner subscription_status)
- lib/nexquant.functions.ts (ajouter getSubscriptionStatus)
- routes/_authenticated/dashboard.tsx (bouton Upgrade)

**Taches :**
1. Definir les tiers (Starter 29$, Pro 79$, Pro 199$)
2. Creer table subscriptions dans Supabase
3. Implementer Stripe Checkout Session
4. Gerer webhook Stripe (completed, deleted, updated)
5. Gating ingest.ts + config.ts
6. UI page billing avec statut

**Acceptance :**
- User peut s'abonner via Stripe -> statut active dans Supabase
- Bot recoit 403 si abonnement expire -> s'arrete proprement
- Admin voit statut subscription de chaque user

### Semaine 2 : Metriques & Pilotage (P2+P3)

**Objectif :** Afficher les KPIs de performance et controler le bot a distance.

**Fichiers a creer (Web) :**
- lib/metrics.ts (moteur de calcul Sharpe, PF, WinRate)
- components/MetricsGrid.tsx
- components/SharpeRatioCard.tsx
- components/EquityCurveAdvanced.tsx
- components/TradeHistoryTable.tsx
- components/WinRateChart.tsx
- components/BotStatusBadge.tsx
- hooks/useBotRealtime.ts (Supabase Realtime hook)
- supabase/migrations/20260629000000_metrics_strategies.sql

**Fichiers a modifier (Web) :**
- lib/nexquant.functions.ts (getMetrics, getTradeHistory)
- routes/_authenticated/dashboard.tsx (integrer MetricsGrid)

**Fichiers a modifier (Bot Python) :**
- superbot/telemetry.py (Realtime subscription sur bot_config)
- superbot/main.py (sync config periodique, start/stop via Realtime)

**Taches Metriques :**
1. Fonction SQL calculate_daily_metrics(user_id)
2. Fonction serveur getMetrics() : Sharpe 30/60/90d
3. Fonction serveur getTradeHistory() : pagination + filtres
4. Dashboard : integrer MetricsGrid dans 4 cards
5. Tests unitaires des calculs

**Taches Pilotage :**
1. Bot souscrit aux changements Realtime sur bot_config
2. Boucle de sync via /api/public/config toutes les 30s
3. is_running=false -> bot arrete la boucle
4. risk_pct, score_min modifies -> appliques au prochain cycle

**Acceptance :**
- Dashboard affiche Sharpe, WinRate, PF, Drawdown mis a jour en temps reel
- Bouton Start/Stop sur le web arrete/repart le bot en moins de 5s
- Modification risk_pct prise en compte au cycle suivant

### Semaine 3 : Strategies, Webhook & Auto-Update (P3+P4)

**Objectif :** Gerer les strategies depuis le web et mettre a jour le bot.

**Fichiers a creer (Web) :**
- routes/_authenticated/strategies.tsx
- routes/_authenticated/risk.tsx
- components/StrategyCard.tsx
- components/StrategyConfigForm.tsx
- components/RiskConfigForm.tsx
- components/WebhookSetup.tsx
- components/UpdateBanner.tsx
- components/NotificationsPanel.tsx

**Fichiers a modifier (Web) :**
- lib/nexquant.functions.ts (getStrategies, updateStrategy, etc.)
- routes/__root.tsx (PWA meta tags)
- routes/_authenticated/dashboard.tsx (UpdateBanner)

**Fichiers a creer (Bot Python) :**
- superbot/updater.py (module de mise a jour automatique)

**Fichiers a modifier (Bot Python) :**
- superbot/main.py (appeler updater au demarrage)
- superbot/telemetry.py (verif version + download)

**Taches Strategies :**
1. Table strategies + RLS policies
2. Page /strategies avec liste et creation
3. Formulaire parametres par type strategie
4. API serveur CRUD strategies
5. Page /webhook avec URL et test

**Taches Auto-Update :**
1. Module updater.py : verifier version au demarrage
2. Download binaire depuis app_versions.download_url
3. Remplacer executable + redemarrer
4. UI : UpdateBanner quand mise a jour dispo

**Taches Risk Config :**
1. Page /risk avec config complete
2. RiskConfigForm lie a bot_config
3. Validation cote serveur des limites

### Semaine 4 : Notifications, PWA, QA & Documentation (P4+P5)

**Objectif :** Finaliser les features et preparer le lancement.

**Fichiers a creer :**
- routes/_authenticated/notifications.tsx
- lib/notifications.ts (service email Resend)
- public/manifest.json (PWA)
- public/sw.js (service worker)
- public/icons/icon-192x192.png
- public/icons/icon-512x512.png
- routes/legal/privacy.tsx
- routes/legal/terms.tsx
- tests/metrics.test.ts
- tests/stripe.test.ts
- tests/ingest-security.test.ts
- supabase/migrations/20260701000000_notifications.sql

**Fichiers a modifier :**
- routes/__root.tsx (PWA link tags)
- routes/_authenticated/dashboard.tsx (polissage final)
- superbot/main.py (logging ameliore, gestion erreurs)

**Taches Notifications :**
1. Integration Resend pour envoi emails
2. Notifications : trade TP/SL, daily loss, license expiry
3. Daily digest email (P&L, positions, metriques)
4. Table notifications + preferences
5. Page /notifications avec configuration

**Taches PWA :**
1. manifest.json avec icones et theme color
2. Service worker pour cache offline
3. Installation sur ecran accueil mobile

**Taches QA :**
1. Tests unitaires metriques (valider Sharpe vs Excel)
2. Tests integration Stripe webhook
3. Tests securite ingest (HMAC, rate limiting)
4. Pages legales (privacy, terms)
5. Documentation API
6. UI polissage final

## 7. Validation avec les Stakeholders

### 7.1 Points de Validation

**Avant implementation (semaine 0) :**
- [ ] Valider ce plan avec l'equipe
- [ ] Confirmer les tiers de prix (Starter 29$/Pro 79$/Pro 199$)
- [ ] Decider Stripe vs Lemon Squeezy (gestion TVA)
- [ ] Valider le modele de distribution (client distribue vs cloud)
- [ ] Verifier la conformite legale (ToS, Privacy)

**Apres semaine 1 :**
- [ ] Demo Stripe Checkout + webhook fonctionnel
- [ ] Verifier que le gating bloque bien un bot sans abonnement

**Apres semaine 2 :**
- [ ] Demo des metriques (Sharpe, PF, WinRate)
- [ ] Demo du controle start/stop a distance

**Apres semaine 3 :**
- [ ] Demo des strategies configurables
- [ ] Demo de l'auto-update

**Apres semaine 4 :**
- [ ] Demo complete de toutes les features
- [ ] Revue de code et securite
- [ ] Approbation finale pour deploiement

### 7.2 Processus

1. Demo chaque vendredi (15 min)
2. Feedback collecte dans GitHub Issues
3. Ajustements avant le sprint suivant
4. Validation finale avant mise en production

## 8. Preparation de l'Environnement

### 8.1 Repository & Branches

**Structure Git :**
- main : production
- develop : integration
- feat/phase2-stripe : paiement
- feat/phase2-metrics : metriques
- feat/phase2-bot-control : pilotage
- feat/phase2-strategies : strategies
- feat/phase2-notifications : notifications
- feat/phase2-pwa : PWA

**Conventions :**
- feat/ prefix pour nouvelles fonctionnalites
- fix/ prefix pour corrections
- chore/ pour maintenance
- Nom de commit : type(scope): description
- Exemple : feat(stripe): ajouter checkout session endpoint

### 8.2 CI/CD Pipeline

**GitHub Actions :**
- Build : npm run build (verification TypeScript)
- Lint : eslint . (qualite code)
- Tests : npm test (tests unitaires)
- Deploy : automatique sur deploiement main

**Environnements :**
- Dev : localhost (vite dev)
- Staging : supabase project staging
- Production : supabase project prod + Vercel/Cloudflare

### 8.3 Variables d'Environnement

**Nouvelles variables necessaires :**
- STRIPE_SECRET_KEY (clest Stripe serveur)
- STRIPE_WEBHOOK_SECRET (signature webhook)
- RESEND_API_KEY (envoi emails)
- NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY (frontend)
- NEXT_PUBLIC_APP_URL (URL de l'application)

## 9. Documentations Essentielles

### 9.1 Documentation Technique

**Architecture :** (ce document)
- Diagramme de flux
- Schema de donnees
- Routes API
- Flux d'authentification

**API :**
- POST /api/payment/create-checkout : cree une session Stripe
- POST /api/payment/webhook : recoit evenements Stripe
- GET /api/analytics/metrics : retourne les KPIs calcules
- GET /api/analytics/trades : historique pagine
- GET/POST /api/strategies : CRUD strategies
- POST /api/notifications/preferences : maj preferences

### 9.2 Guides

**Setup developpement local :**
1. Cloner le repo
2. Creer fichier .env (copier .env.example)
3. Installer dependances : npm install
4. Demarrer dev : npm run dev
5. Lancer Supabase local : supabase start

**Conventions de code :**
- TypeScript strict mode
- Noms de fichiers en kebab-case
- Composants React en PascalCase
- Fonctions serveur prefixees par action (get, create, update)
- Validation des entrees avec Zod

**Standards :**
- Tests unitaires pour toute fonction de calcul
- Logs structures (source, level, message)
- Gestion d'erreurs avec ErrorBoundary
- Responsive design (mobile d'abord)

### 9.3 Base de Connaissances

**FAQ courantes :**
- Q: Comment obtenir mes cles API Binance ?
  R: Suivre le guide dans le dashboard > Config Broker
- Q: Le bot peut-il trader sur plusieurs comptes ?
  R: Oui, chaque compte utilisateur est isole
- Q: Les cles API sont-elles stockees en securite ?
  R: Oui, chiffrees AES-256 et jamais en clair dans les logs
- Q: Que se passe-t-il si mon abonnement expire ?
  R: Le bot s'arrete automatiquement et affiche un message

**Troubleshooting :**
- Erreur 401 sur ingest : verifier HMAC signature
- Erreur 403 sur config : verifier abonnement
- Bot ne demarre pas : verifier les logs dans le dashboard
- Stripe webhook 400 : verifier WEBHOOK_SECRET

## 10. Annexes

### 10.1 Interfaces TypeScript (Nouvelles)

`	ypescript
// Types Phase 2 - NexQuant

// 1. PAIEMENT & ABONNEMENT
export type SubscriptionTier = starter | pro | professional;
export type SubscriptionStatus = active | past_due | canceled | incomplete | trialing | expired;

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

// 2. METRIQUES ET ANALYTICS
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

// 3. STRATEGIES
export interface Strategy {
  id: string;
  user_id: string;
  name: string;
  type: string;
  params: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

// 4. RISK SETTINGS
export interface RiskSettings {
  risk_per_trade: number;
  max_daily_loss: number;
  max_open_positions: number;
  kelly_fraction: number;
  use_correlation_adjustment: boolean;
  use_funding_rate_filter: boolean;
}
`

### 10.2 Migrations SQL (Nouvelles Tables)

`sql
-- Migration 4: Subscriptions
CREATE TABLE public.subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  tier TEXT NOT NULL DEFAULT starter,
  status TEXT NOT NULL DEFAULT incomplete,
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
`

### 10.3 GitHub Issues (Prets a Importer)

**Issue 1: Integration Stripe**
- Labels: Phase-2, payment, P1
- Taches: Checkout session, webhook, subscription gating, UI billing
- Definition of Done: User peut sabonner, bot bloque si expire

**Issue 2: Metriques avancees**
- Labels: Phase-2, analytics, P2
- Taches: Sharpe, PF, WinRate, daily_metrics, TradeHistoryTable
- Definition of Done: Dashboard affiche toutes les metriques

**Issue 3: Pilotage bidirectionnel**
- Labels: Phase-2, bot-control, P3
- Taches: Realtime Supabase, sync config 30s, start/stop distant
- Definition of Done: Bouton web arrete/repart le bot en moins de 5s

**Issue 4: Gestion strategies web**
- Labels: Phase-2, strategies, P3
- Taches: Table strategies, page /strategies, formulaire params
- Definition of Done: User peut configurer ses strategies depuis le web

**Issue 5: Auto-update bot**
- Labels: Phase-2, updater, P4
- Taches: updater.py, verif version, download, restart
- Definition of Done: Bot se met a jour automatiquement

**Issue 6: Notifications + PWA**
- Labels: Phase-2, notifications, PWA, P4
- Taches: Emails Resend, manifest.json, service worker
- Definition of Done: User recoit notifs et peut installer PWA

**Issue 7: QA et pre-lancement**
- Labels: Phase-2, QA, P5
- Taches: Tests, documentation, pages legales, polissage UI
- Definition of Done: Tout est pret pour le deploiement

### 10.4 Arborescence des Fichiers a Creer (Phase 2)

`
nexquant/NexQuant_Web_App/src/
  routes/api/payment/
    create-checkout.ts       [NOUVEAU]
    webhook.ts               [NOUVEAU]
  routes/_authenticated/
    billing.tsx              [NOUVEAU]
    strategies.tsx           [NOUVEAU]
    risk.tsx                 [NOUVEAU]
    notifications.tsx        [NOUVEAU]
  components/
    BillingCard.tsx          [NOUVEAU]
    MetricsGrid.tsx          [NOUVEAU]
    SharpeRatioCard.tsx      [NOUVEAU]
    EquityCurveAdvanced.tsx  [NOUVEAU]
    TradeHistoryTable.tsx    [NOUVEAU]
    StrategyCard.tsx         [NOUVEAU]
    StrategyConfigForm.tsx   [NOUVEAU]
    RiskConfigForm.tsx       [NOUVEAU]
    WebhookSetup.tsx         [NOUVEAU]
    BotStatusBadge.tsx       [NOUVEAU]
    UpdateBanner.tsx         [NOUVEAU]
    NotificationsPanel.tsx   [NOUVEAU]
  hooks/
    useBotRealtime.ts        [NOUVEAU]
  lib/
    metrics.ts               [NOUVEAU]
    stripe.ts                [NOUVEAU]
    notifications.ts         [NOUVEAU]
  public/
    manifest.json            [NOUVEAU]
    sw.js                    [NOUVEAU]
  tests/
    metrics.test.ts          [NOUVEAU]
    stripe.test.ts           [NOUVEAU]
    ingest-security.test.ts  [NOUVEAU]
  routes/legal/
    privacy.tsx              [NOUVEAU]
    terms.tsx                [NOUVEAU]
supabase/migrations/
  20260628000000_subscriptions.sql  [NOUVEAU]
  20260629000000_metrics.sql       [NOUVEAU]
  20260701000000_notifications.sql [NOUVEAU]
nexquant/superbot/
  updater.py                [NOUVEAU]
`

### 10.5 Priorite des Fonctionnalites (Resume)

`
P1 - Semaine 1 : Paiement Stripe (indispensable au business)
P2 - Semaine 2 : Metriques (les users doivent voir les perfs)
P3 - Semaine 2-3 : Pilotage + Strategies (valeur SaaS)
P4 - Semaine 3-4 : Auto-update + Notifs + PWA (qualite de vie)
P5 - Semaine 4 : QA + Documentation + Legal (pre-lancement)
`

---

## Conclusion

Ce plan couvre l'integralite du cycle de developpement Phase 2 :
- **Conception** : objectifs, utilisateurs, faisabilite
- **Specifications** : user stories, exigences fonctionnelles et non-fonctionnelles
- **Architecture** : stack, design, flux de donnees
- **Design UX** : nouvelles pages, navigation
- **Planification** : 4 semaines, 7 issues, priorites claires
- **Validation** : demos hebdomadaires, approbation par etapes
- **Preparation** : CI/CD, variables, conventions
- **Documentation** : API, guides, FAQ
- **Annexes** : interfaces TypeScript, migrations SQL, issues GitHub

**Prochaine etape :** Valider ce plan avec les stakeholders, puis commencer l'implementation semaine 1 (Stripe).

---
*Document genere le 27 juin 2026 - NexQuant Phase 2 Development Plan*
