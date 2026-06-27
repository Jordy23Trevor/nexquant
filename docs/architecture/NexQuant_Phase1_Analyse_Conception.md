# NexQuant Web App - Phase 1 : Analyse & Conception Commerciale
**Version:** 1.0  
**Date:** Juin 2026  
**Statut:** Blueprint for Commercial Release

---

## 📋 TABLE DES MATIÈRES

1. [Clarification d'Objectif Commercial](#1-clarification-dobjectif-commercial)
2. [Identification des Utilisateurs](#2-identification-des-utilisateurs)
3. [Scope v1 Commerciale](#3-scope-v1-commerciale)
4. [Étude de Faisabilité](#4-étude-de-faisabilité)
5. [Exigences Fonctionnelles](#5-exigences-fonctionnelles)
6. [Exigences Non-Fonctionnelles](#6-exigences-non-fonctionnelles)
7. [Features Détaillées à Implémenter](#7-features-détaillées-à-implémenter)
8. [Système de Monitoring Multi-Utilisateurs](#8-système-de-monitoring-multi-utilisateurs)
9. [Architecture Technique Commerciale](#9-architecture-technique-commerciale)
10. [Stratégie Mobile & Desktop](#10-stratégie-mobile--desktop)
11. [Modèle de Monétisation](#11-modèle-de-monétisation)
12. [Gestion des Risques](#12-gestion-des-risques)
13. [Timeline & Jalons](#13-timeline--jalons)

---

## 1. Clarification d'Objectif Commercial

### Vision Générale
**NexQuant** est une plateforme SaaS de trading algorithmique multi-broker destinée aux traders retail souhaitant automatiser leurs stratégies avec une gestion de risque stricte, sans avoir besoin de coder.

### Objectif Principal
- Fournir un bot trading professionnel, fiable et rentable
- Démocratiser l'accès aux stratégies algorithmiques
- Générer des revenus via subscription + partage de performance

### Cible Commerciale
1. **Traders expérimentés** : Traders techniques, fondamentaux, scalpers
2. **Investisseurs passifs** : Cherchent croissance passive et automatisation
3. **Institutions legères** : Small hedge funds, trading desks indépendants

### Positionnement Produit
- **vs Competition** : Interface simple (pas de code), multi-broker, transparence complète des trades
- **Avantage clé** : Monitoring en temps réel, risk management intelligent, Sharpe ratio 1.2-1.8
- **Promesse** : "Profit = Discipline + Stratégie + Technologie"

---

## 2. Identification des Utilisateurs

### User Personas

#### Persona 1: "Alex le Trader Intermédiaire"
- **Profil** : Trader depuis 3-5 ans, utilise TradingView, connaît les basics du risque
- **Motivation** : Automatiser ses signaux TradingView, tester des stratégies sans émotions
- **Frustration** : Complexity des APIs, peur du code bugué, besoin de surveillance
- **Besoin clé** : Interface intuitive, webhooks TradingView, monitoring détaillé
- **Capital** : $5K - $50K

#### Persona 2: "Maya l'Investisseur Passif"
- **Profil** : Investisseur à long terme, peu technique, cherche "set and forget"
- **Motivation** : Générer 15-30% par an, pas de stress des trades manuels
- **Frustration** : Trop d'options, pas d'explications claires, peur de perdre tout
- **Besoin clé** : Presets stratégies éprouvées, dashboard simple, notifications claires
- **Capital** : $25K - $100K (minimum Alpaca PDT)

#### Persona 3: "Jordan le Scalper Crypto"
- **Profil** : Trader actif crypto 24/7, accro aux setups rapides, haute volatilité
- **Motivation** : Profiter de Binance Futures, scalping automatisé 24h/24
- **Frustration** : Latence, slippage, drawdowns imprévisibles
- **Besoin clé** : Binance Futures optimisé, risque/reward tight, logs détaillés
- **Capital** : $500 - $10K

#### Persona 4: "Sophie la Gestionnaire de Fonds"
- **Profil** : Gère $500K-$5M pour clients, besoin de compliance et reporting
- **Motivation** : Automatiser avec audit trail complet, reporting client professionnel
- **Frustration** : Pas de multi-compte, pas de reporting réglementaire, pas de white label
- **Besoin clé** : Multi-users, permissions role-based, export compliance-ready
- **Capital** : $50K - $500K+

### Use Cases Primaires

| User | Scénario | Flux |
|------|----------|------|
| Alex | Connecter TradingView → Activer bot | Setup broker → Test paper → Live 1% risk |
| Maya | Choisir stratégie prédéfinie → Laisser tourner | Select preset → Review & approve → Monitoring passif |
| Jordan | Scalp 15min sur BTC/USDT avec TP/SL auto | Setup Binance → Optimiser params → Activer 24/7 |
| Sophie | Setup multi-accounts, auto-reporting clients | Admin dashboard → Create users → Assign strategies → Export PDF monthly |

---

## 3. Scope v1 Commerciale

### Inclus dans v1

#### Fonctionnalités Core
✅ **Multi-Broker Support**
- Binance Futures (crypto, 24/7)
- Alpaca (US stocks, session-based)
- Paper Forex simulator (demo/testing)

✅ **Broker Setup & API Management**
- Interface onboarding intuitive
- API key encryption & rotation
- Broker health status real-time
- Auto-disconnect on API failures

✅ **Strategy Configuration**
- Pre-built strategies (Trend Following, Mean Reversion, Scalping)
- Customizable params (indicators, thresholds, TP/SL multiples)
- Paper trading for strategy validation
- TradingView webhook support

✅ **Risk Management**
- Per-trade risk % (configurable 0.5%-5%)
- Max daily loss limit
- Max open positions
- Drawdown monitoring
- Auto-stop on breach

✅ **Dashboard Utilisateur**
- Live position tracking (tous brokers)
- Real-time P&L (per trade, per strategy, cumulative)
- Trade log avec détails (entry/exit prices, fees, reasoning)
- Equity curve charts
- Daily/Weekly/Monthly performance snapshots

✅ **Monitoring & Analytics**
- Sharpe ratio calculation (rolling 30/60/90d)
- Profit factor & win rate
- Daily/monthly ROI tracking
- Max drawdown monitoring
- Risk-adjusted return metrics

✅ **Admin Panel (Demo Rollout)**
- Invite code generation & management
- User lifecycle (trial → active → expired)
- Performance monitoring per-user
- Cohort analytics (avg Sharpe, drawdown by broker)
- API health dashboard

✅ **Security & Compliance**
- User authentication (email/password + 2FA option)
- API key encryption (AES-256)
- Audit logs (trades, config changes, API calls)
- GDPR compliance (data export, deletion)
- Permission roles (admin, user, viewer)

---

### Exclus de v1 (Roadmap Post-Launch)

❌ **Post-v1 Features**
- White-label solution (v2)
- Advanced strategy builder (visual/formula editor) (v2)
- Machine learning signal optimization (v3)
- Advanced reporting & risk analytics (v2)
- ORB (Open Range Breakout) strategy module (v2 - needs backtesting first)
- Backtesting engine (v2 - critical gap identified)
- Options trading support (v3)
- Social copy-trading (v3)
- Mobile app launch (v2 - post web stability)

---

## 4. Étude de Faisabilité

### Ressources Disponibles

| Ressource | Statut | Notes |
|-----------|--------|-------|
| **Backend Python Bot** | ✅ Prêt | v2 architecture stable, multi-broker abstraction layer |
| **Frontend React** | 🔨 En cours | Lovable builder, core UI composants presque prêts |
| **Database Schema** | ✅ Prêt | Users, trades, daily metrics, invite codes définis |
| **TradingView Webhooks** | ✅ Prêt | Intégration fonctionnelle |
| **Monitoring System** | 🔨 À implémenter | Key feature for v1 - new development |
| **Admin Dashboard** | 🔨 À implémenter | New development |
| **Backtesting Engine** | ❌ Manquant | Risque identifié, déféré v2 |

### Timeline Estimée
- **Web App v1** : 8-12 semaines (si monitoring/admin bien scoped)
- **Launch Beta** : Semaine 9-10
- **Launch Commercial** : Semaine 12-16

### Risques Majeurs

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|-----------|
| Backtesting manquant | Haute | Haute | Lancer beta sans strategy optimization, ajouter v2 |
| API instabilité brokers | Moyenne | Très haute | Monitoring/alerts robustes, fallback graceful, docs SLA |
| Faux positifs monitoring | Moyenne | Moyenne | QA intensive sur daily metrics calculation |
| Onboarding complexity | Moyenne | Moyenne | Wizard step-by-step, video tutorials, support chat |
| Compliance réglementaire | Moyenne | Très haute | Legal review, disclaimer clear, pas de garanties profit |

---

## 5. Exigences Fonctionnelles

### RF-1 : Onboarding Utilisateur

```
RF-1.1 Inscription
  - Email/password signup avec validation
  - Email verification (link 24h)
  - 2FA optional (authenticator app)
  - Accepted ToS & risk disclaimer

RF-1.2 Profil Utilisateur
  - Bio (nom, trading style)
  - Capital size declaration (affects risk limits)
  - Broker preference selection
  - Notification preferences (email, SMS, push)

RF-1.3 Minimum Capital Enforcement
  - Binance Futures: min $500
  - Alpaca Live: min $25,000 (PDT rule)
  - Paper Forex: $0 (demo)
  - Validation on account connection
```

### RF-2 : Broker Integration

```
RF-2.1 API Key Management
  - Secure input (masked fields)
  - AES-256 encryption at rest
  - Vault storage with salted hash for verification
  - Auto-rotation capability
  - Test connection before save

RF-2.2 Broker Health Monitoring
  - Real-time API status check (every 30s)
  - Rate limit tracking
  - Latency measurement
  - Error rate alerting
  - Auto-disable on repeated failures (3x in 5min)

RF-2.3 Instrument Mapping
  - INSTRUMENTS_BINANCE, INSTRUMENTS_ALPACA, INSTRUMENTS_PAPER_FOREX
  - Prevent cross-broker mismatch
  - Currency normalization (USD, USDT)
  - Min position size validation per broker
```

### RF-3 : Strategy Configuration

```
RF-3.1 Pre-built Strategies (v1 Launch)
  - Trend Following (EMA-based, Binance/Alpaca)
  - Mean Reversion (RSI bounce, Binance/Alpaca)
  - Scalping (fast entries on 15min, Binance only)

RF-3.2 Strategy Customization
  - Indicator params (fast/slow periods, threshold levels)
  - TP/SL multiples (R:R ratio)
  - Max open positions per strategy
  - Entry filter (time of day, volatility range)
  - Test on paper before live

RF-3.3 Strategy Activation
  - Dry run mode (signal generation, no execution)
  - Paper mode (full simulation, no real capital)
  - Live mode (real execution)
  - One-click pause/resume
```

### RF-4 : Trade Execution & Management

```
RF-4.1 Order Placement
  - Webhook validation (TradingView source IP check)
  - Risk check (position size = account% → broker min size)
  - Broker-specific order types (market, limit, bracket Alpaca)
  - Slippage tracking (actual vs expected entry)

RF-4.2 Position Management
  - Real-time position tracking (entry price, current price, P&L)
  - Automatic TP/SL placement
  - Manual override capability
  - Partial close support

RF-4.3 Trade Logging
  - Complete trade record (entry, exit, entry reason, exit reason)
  - Fee calculation per broker
  - Slippage measurement
  - Duration tracking (ms to days)
  - Trade state machine (pending → open → closed)
```

### RF-5 : Risk Management

```
RF-5.1 Trade-Level Risk
  - 2% risk per trade (configurable 0.5%-5%)
  - Position size = (account × risk%) / (entry - SL)
  - Validate vs min/max position size
  - Max positions open = 5 (configurable)

RF-5.2 Account-Level Risk
  - Max daily loss limit (e.g., 5% of account)
  - Max drawdown limit (e.g., 15%)
  - Max open positions total (across all strategies)
  - Correlation check (avoid similar setups)

RF-5.3 Risk Breach Action
  - Alert to user (email + push)
  - Pause new orders
  - Allow existing positions to close naturally
  - Force close if drawdown continues (optional)
```

### RF-6 : Dashboard & Analytics

```
RF-6.1 Real-Time Dashboard
  - Active positions (entry, current price, P&L %, time open)
  - Daily/weekly/monthly P&L summary
  - Equity curve (connected to daily snapshots)
  - Win rate % (trades closed profitably / total)
  - Current Sharpe ratio (30d rolling)

RF-6.2 Performance Metrics
  - Sharpe ratio (30d, 60d, 90d rolling)
  - Profit factor (gross profit / gross loss)
  - Max drawdown (peak to trough %)
  - Calmar ratio (annual return / max drawdown)
  - Win rate & average trade duration

RF-6.3 Trade Log & Filtering
  - Full trade history (entry/exit prices, P&L, duration)
  - Filter by: date range, strategy, broker, symbol, status
  - Export as CSV/JSON
  - Sort by: P&L, duration, entry date
```

### RF-7 : Admin Dashboard (Commercial)

```
RF-7.1 Invite Code Management
  - Generate unique codes (tied to trial duration, feature limits)
  - Track usage (who, when, from IP)
  - Revoke codes
  - Bulk generate for marketing campaigns

RF-7.2 User Management
  - List all users (active, trial, expired)
  - Filter by: broker, performance level, signup date
  - Manual trial extension
  - Permission assignment (admin, user, viewer)
  - Account suspension/deletion

RF-7.3 Performance Monitoring
  - User leaderboard (by Sharpe, profit, ROI)
  - Cohort analytics (avg metrics by broker/strategy)
  - Trading activity heatmap (trades per hour/day)
  - API health dashboard (Binance/Alpaca uptime %)

RF-7.4 Reporting & Compliance
  - User KPIs export (CSV/JSON)
  - Tax-ready trade export (IRS Form 8949 compatible)
  - Monthly revenue report (if revenue-share model)
  - Usage analytics (DAU, MAU, churn rate)
```

### RF-8 : Notifications & Alerts

```
RF-8.1 Trade Notifications
  - Order filled (price, size, fee)
  - SL/TP hit
  - Position closed (profit/loss)
  - Unusual slippage detected

RF-8.2 Risk Alerts
  - Daily loss threshold hit
  - Max drawdown approaching
  - Broker API offline
  - Strategy paused due to error

RF-8.3 Delivery Channels
  - Email (daily digest + urgent alerts)
  - Push notifications (mobile/web)
  - SMS (optional, high-priority only)
  - In-app notifications (persistent until read)
```

---

## 6. Exigences Non-Fonctionnelles

### Performance

```
NF-1.1 Response Time
  - Dashboard load: < 2s (initial), < 500ms (updates)
  - Trade execution: < 100ms (webhook received → order sent)
  - Chart rendering (1000 candles): < 1s
  - Admin dashboard: < 3s (even 1000 users loaded)

NF-1.2 Scalability
  - Support 10K active users (v1 goal)
  - 100+ concurrent live traders
  - Database optimized for: frequent trade inserts, metric queries
  - Horizontal scaling via load balancer
```

### Fiabilité & Disponibilité

```
NF-2.1 Uptime SLA
  - 99.5% (3.7 hours downtime/month acceptable)
  - Goal: 99.9% (43 min/month) by v1.5
  - Graceful degradation (show cached data if DB unavailable)

NF-2.2 Trade Execution Reliability
  - No missed trades (100% webhook delivery)
  - Retry logic: 3x exponential backoff
  - Broker API fallback (if Binance down, try alternative)

NF-2.3 Data Integrity
  - ACID transactions for trade writes
  - Backup: daily snapshots + hourly incremental
  - Point-in-time recovery capability
```

### Sécurité

```
NF-3.1 Authentication & Authorization
  - HTTPS only (no HTTP)
  - JWT tokens with 24h expiry + refresh rotation
  - Password: min 12 chars, complexity rules
  - 2FA: TOTP (authenticator app) optional, SMS not for prod
  - Rate limiting: 5 failed logins → 15min lock

NF-3.2 Data Protection
  - API keys: AES-256 encryption, salted hash verification
  - Trade history: encrypted at rest (TDE if SQL)
  - No plaintext API keys in logs/backups
  - GDPR: data export/deletion within 30 days

NF-3.3 API Security
  - Webhook signature verification (HMAC-SHA256 from TradingView)
  - IP whitelisting option (TradingView IPs)
  - Rate limiting: 1000 requests/min per user
  - SQL injection protection: parameterized queries
```

### Observabilité

```
NF-4.1 Logging
  - All trades: entry signal → execution → exit (with timestamps)
  - All API calls (latency, status, retry count)
  - Strategy logic decisions (why entry? why not?)
  - Errors: stack traces + context (user, broker, instrument)

NF-4.2 Monitoring
  - Real-time metrics: active trades, P&L, error count
  - Alerting: critical errors (PagerDuty), warnings (email)
  - Dashboards: ops team views (uptime, latency, errors)

NF-4.3 Audit Trail
  - All user actions: strategy change, broker switch, trial extension
  - Immutable logs (append-only, no deletion)
  - Export for compliance audits
```

### Usabilité

```
NF-5.1 UI/UX
  - Responsive design (mobile 320px+, tablet, desktop)
  - Accessibility: WCAG 2.1 AA (keyboard nav, screen reader)
  - Consistent design language (NexQuant brand: dark, cyan, Inter font)
  - <5 min onboarding to first trade (paper trading)

NF-5.2 Help & Documentation
  - In-app tooltips (hover over settings)
  - FAQ section
  - Video tutorials (setup, strategy config, monitoring)
  - Email support <24h response
```

---

## 7. Features Détaillées à Implémenter

### Feature Set v1 Breakdown

#### **Tier 1: Critical Path (Must Have - Semaines 1-6)**

**F1.1: User Registration & Auth**
```
Scope: Email signup → email verification → password setup → 2FA optional
Files:
  - Frontend: SignupForm, EmailVerification, 2FASetup components
  - Backend: /auth/register, /auth/verify-email, /auth/setup-2fa endpoints
  - Database: users table (email, password_hash, 2fa_secret, verified_at)
Time: 1.5 weeks
Acceptance: User can signup → verify email → login with 2FA
```

**F1.2: Broker API Connection**
```
Scope: API key input → encryption → test connection → save
Files:
  - Frontend: BrokerSetup, APIKeyForm components
  - Backend: /brokers/connect, /brokers/test, /brokers/save endpoints
  - Crypto: AES-256 encryption utils
Database: user_broker_keys (user_id, broker, encrypted_key, key_hash, status)
Time: 2 weeks (Binance, Alpaca, Paper Forex)
Acceptance: User can connect live Binance/Alpaca account, paper forex auto-available
Blockers: Broker API testing environment (sandbox Alpaca, Binance testnet)
```

**F1.3: Real-Time Position Tracking**
```
Scope: Fetch live positions from broker → display in dashboard → update every 5s
Files:
  - Backend: /positions endpoint (fetches from broker, caches 30s)
  - Frontend: PositionsWidget component (real-time update via WebSocket)
  - Database: open_positions table (user_id, broker, symbol, size, entry_price, current_price)
Time: 2 weeks
Acceptance: Positions show live P&L, updates smooth without lag
Test: Open position on real broker, verify sync within 5s
```

**F1.4: Paper Trading**
```
Scope: Simulate trades without real capital → test strategies
Files:
  - Backend: Paper Forex simulator engine, /paper/trade endpoint
  - Frontend: PaperTradingToggle, SimulationResults components
  - Database: paper_trades (user_id, symbol, size, entry_price, exit_price, simulation_id)
Time: 2 weeks
Acceptance: User can paper trade, results stored, Sharpe calculated for simulations
```

---

#### **Tier 2: Strategy & Trading (Must Have - Semaines 5-9)**

**F2.1: Pre-built Strategies Setup**
```
Scope: 3 strategies (Trend Following, Mean Reversion, Scalping) with customizable params
Files:
  - Backend: /strategies endpoints (list, get, create, update)
  - Frontend: StrategyConfigForm, PresetSelector components
  - Database: strategies table (user_id, name, type, params JSON)
Time: 2.5 weeks
Acceptance: User can select Trend Following → adjust params → save → activate on paper
Details:
  - Trend Following: EMA 12/26, close above both → enter long, TP/SL auto
  - Mean Reversion: RSI < 30 → enter long, TP at center, SL at low
  - Scalping: Fast entry on 15min candles, tight stops, 3:1 R:R target
```

**F2.2: TradingView Webhook Integration**
```
Scope: Receive signals from TradingView Pine Script → validate → execute trade
Files:
  - Backend: /webhook/tradingview endpoint (POST), signature verification
  - Frontend: WebhookSetup, WebhookTestor components
  - Database: webhook_signals (user_id, timestamp, signal_data, executed)
Time: 2 weeks
Acceptance: Create Pine Script alert in TradingView → send signal → bot executes
Security: HMAC-SHA256 verification, IP whitelisting
Test: Send mock webhook, verify order placed on paper trading
```

**F2.3: Risk Management Configuration**
```
Scope: Set risk per trade, max daily loss, max positions, max drawdown
Files:
  - Backend: /risk-settings endpoints
  - Frontend: RiskConfigForm component
  - Database: risk_settings table (user_id, risk_per_trade, max_daily_loss, max_positions, max_drawdown)
Time: 1.5 weeks
Acceptance: User sets 2% risk per trade → bot enforces it on all orders
Validation: Position size = (account × 2%) / (entry - SL), min/max check
```

**F2.4: Trade Execution & Logging**
```
Scope: Place orders on broker → track execution → log complete trade record
Files:
  - Backend: /orders/place, /orders/update, /trades/log endpoints
  - Frontend: TradeExecutionWidget component
  - Database: trades table (user_id, broker, symbol, entry_price, exit_price, entry_time, exit_time, entry_reason, exit_reason, fee, slippage)
Time: 2.5 weeks
Acceptance: User sees trade executed → logged with entry/exit reasons → fee calculated
Complexity: Bracket orders (Alpaca), order status tracking, partial fills
```

---

#### **Tier 3: Monitoring & Analytics (Must Have - Semaines 8-11)**

**F3.1: Dashboard Real-Time Metrics**
```
Scope: Display Sharpe, profit factor, win rate, max drawdown, equity curve
Files:
  - Backend: /analytics/metrics endpoint (calculates from trade history)
  - Frontend: MetricsWidget, EquityCurveChart components
  - Database: daily_metrics table (user_id, date, equity, daily_pnl, sharpe_30d, max_dd, profit_factor)
Time: 2.5 weeks
Calculations:
  - Sharpe (30d rolling): (avg daily return - risk-free) / std dev daily return
  - Profit factor: sum(winning trades) / sum(losing trades)
  - Max drawdown: (peak equity - trough equity) / peak equity
  - Win rate: profitable trades / total trades
Acceptance: Sharpe 1.2+ achievable with Trend Following strategy, tracked daily
```

**F3.2: Trade Log & Filtering**
```
Scope: Historical view of all trades, filterable by date/strategy/broker/symbol
Files:
  - Frontend: TradeHistoryTable, FilterBar components
  - Backend: /trades/list endpoint with pagination & filtering
Time: 1.5 weeks
Acceptance: User can see all 500 past trades, filtered by last 30 days → export CSV
```

**F3.3: Daily Snapshots & Equity Tracking**
```
Scope: Record daily account state (equity, daily P&L, metrics) at market close
Files:
  - Backend: Scheduled job (runs at 16:30 ET for stocks, 00:00 UTC for crypto) → inserts daily_metrics
  - Database: daily_metrics table (user_id, date, open_equity, close_equity, daily_pnl, num_trades, sharpe_30d)
Time: 1.5 weeks
Acceptance: Every day at close, daily metrics captured, Sharpe recalculated, chart updated
```

---

#### **Tier 4: Admin & Demo Rollout (Must Have - Semaines 10-12)**

**F4.1: Invite Code System**
```
Scope: Generate codes → track usage → auto-expire trial accounts
Files:
  - Frontend: InviteCodeManager component (admin only)
  - Backend: /admin/invite-codes endpoints (generate, list, revoke, stats)
  - Database: invite_codes table (code, created_at, used_by_user_id, used_at, trial_days, feature_tier, valid_until)
Time: 1.5 weeks
Acceptance: Admin generates "NQ-BETA-001" → gives to user → user enters code at signup → trial enabled 14 days
```

**F4.2: User Management & Lifecycle**
```
Scope: List users, view stats, extend trial, suspend account, revoke API keys on expiry
Files:
  - Frontend: UserManagementTable, UserDetailView components (admin only)
  - Backend: /admin/users endpoints (list, get, extend-trial, suspend, delete)
  - Scheduler: Daily job checks expiry → marks user.trial_expires_at, disables API keys at midnight
Time: 2 weeks
Acceptance: Admin sees 50 beta users with stats → click user → see P&L → extend trial 7 more days
Cleanup: On expiry, API keys revoked, user notified, graceful UI message "Trial expired"
```

**F4.3: Admin Analytics Dashboard**
```
Scope: Cohort performance, API health, trading activity, revenue metrics
Files:
  - Frontend: AdminDashboard, UserLeaderboard, CohortAnalytics components
  - Backend: /admin/analytics endpoints (aggregated metrics)
Time: 2.5 weeks
Metrics:
  - User leaderboard (Sharpe, profit, ROI, days active)
  - Cohort stats (avg Sharpe by broker: Binance 1.1, Alpaca 1.4)
  - Trading activity (trades/day, peak hours)
  - Broker API uptime %
  - Churn rate (trial → inactive)
Acceptance: Admin opens dashboard → sees "10 users, avg Sharpe 1.3, Alpaca performing best"
```

**F4.4: Broker Health Monitoring**
```
Scope: Monitor API status, latency, error rates per broker
Files:
  - Backend: Scheduled health check job (every 30s), /brokers/health endpoint
  - Frontend: BrokerHealthWidget component
  - Database: broker_health_log table (timestamp, broker, status, latency_ms, error_count)
Time: 1 week
Acceptance: Binance API down → red indicator → alert sent → user notified
```

---

### Implementation Roadmap Table

| Feature | Week | Hours | Tier | Owner | Blocker |
|---------|------|-------|------|-------|---------|
| Auth & Registration | 1-2 | 40 | T1 | Backend | None |
| Broker API Connection | 2-4 | 60 | T1 | Backend | Alpaca API key testing |
| Position Tracking | 3-5 | 45 | T1 | Backend+Frontend | Real broker account |
| Paper Trading | 3-5 | 50 | T1 | Backend | None |
| Strategy Setup | 5-7 | 55 | T2 | Backend+Frontend | None |
| TradingView Webhooks | 5-7 | 40 | T2 | Backend | None |
| Risk Management | 5-6 | 35 | T2 | Backend | None |
| Trade Execution | 6-9 | 70 | T2 | Backend+Frontend | Alpaca bracket orders |
| Dashboard Metrics | 8-11 | 60 | T3 | Backend+Frontend | Daily snapshots logic |
| Trade Log | 8-9 | 30 | T3 | Frontend | None |
| Daily Snapshots | 9-10 | 35 | T3 | Backend | None |
| Invite Codes | 10-12 | 40 | T4 | Backend+Frontend | None |
| User Management | 10-12 | 50 | T4 | Backend+Frontend | None |
| Admin Dashboard | 10-12 | 70 | T4 | Backend+Frontend | None |
| Broker Health Monitoring | 11-12 | 30 | T4 | Backend | None |
| **TOTAL** | **1-12** | **615** | - | - | - |

---

## 8. Système de Monitoring Multi-Utilisateurs

### Objectif Global
Tracker les performances de tous les utilisateurs en temps réel pour:
1. **Admin** : Identifier top performers, détecter anomalies, optimiser system
2. **Users** : Voir leur performance vs cohort, benchmarking
3. **Investors** : Attester les performances réelles de NexQuant bot

### Architecture Monitoring

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Every Trade Executed:                                        │
│    1. Bot logs: entry_price, exit_price, size, fees, etc    │
│    2. Backend inserts → trades table                         │
│    3. Real-time metrics calculated                           │
│                                                               │
│  Daily Snapshots (00:00 UTC for crypto, 16:30 ET stocks):   │
│    1. Scheduler runs daily_snapshot_job                      │
│    2. For each user:                                         │
│       - Fetch open positions (current value)                 │
│       - Calculate equity (cash + open position value)        │
│       - Calc daily P&L (equity today - equity yesterday)     │
│       - Insert daily_metrics row                             │
│    3. Recalculate rolling Sharpe (30d, 60d, 90d)            │
│       - Formula: (avg daily return - 0%) / std dev           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    AGGREGATION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Cohort Aggregation (runs hourly):                           │
│    1. Group users by: broker, strategy, capital_tier        │
│    2. For each cohort:                                       │
│       - Avg Sharpe, median Sharpe, std dev                  │
│       - Avg profit factor, win rate                         │
│       - Max drawdown distribution (50th, 90th percentile)   │
│    3. Cache in cohort_metrics table                          │
│                                                               │
│  Anomaly Detection (runs every 15 min):                      │
│    1. Flag users with: -20% daily loss, 3+ consecutive loss |
│    2. Check API health (Binance/Alpaca status)              │
│    3. Alert admin if: avg user Sharpe drops > 0.3 points   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    VISUALIZATION LAYER                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  User Dashboard:                                             │
│    - Personal Sharpe, profit factor, win rate (live)        │
│    - Equity curve (last 30 days)                            │
│    - vs Cohort comparison (Your Sharpe 1.4 vs Avg 1.1)     │
│                                                               │
│  Admin Dashboard:                                            │
│    - User leaderboard (sortable by Sharpe, profit, ROI)     │
│    - Cohort breakdown (Binance avg 1.1, Alpaca avg 1.4)     │
│    - Activity heatmap (trades per hour, peak times)         │
│    - Anomaly alerts (high-loss users, API issues)           │
│    - Revenue metrics (if revenue-share model)               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema for Monitoring

```sql
-- Core trades tracking
CREATE TABLE trades (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  broker_id INT,
  symbol VARCHAR(20),
  entry_price DECIMAL(20, 8),
  exit_price DECIMAL(20, 8),
  size DECIMAL(20, 8),
  entry_time TIMESTAMP,
  exit_time TIMESTAMP,
  pnl DECIMAL(20, 8),  -- exit_pnl after fees
  pnl_pct DECIMAL(5, 2),  -- pnl / (entry * size) * 100
  fees DECIMAL(20, 8),
  slippage DECIMAL(20, 8),
  entry_reason VARCHAR(255),
  exit_reason VARCHAR(255),
  strategy_id INT,
  status VARCHAR(20),  -- pending, open, closed
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Daily snapshots for equity curve
CREATE TABLE daily_metrics (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  date DATE,
  opening_equity DECIMAL(20, 8),  -- end of previous day
  closing_equity DECIMAL(20, 8),  -- current account value
  daily_pnl DECIMAL(20, 8),  -- closing - opening
  daily_pnl_pct DECIMAL(5, 2),
  num_trades_today INT,
  num_winning_trades INT,
  win_rate_today DECIMAL(5, 2),
  sharpe_30d DECIMAL(5, 2),  -- rolling 30-day Sharpe
  sharpe_60d DECIMAL(5, 2),
  sharpe_90d DECIMAL(5, 2),
  profit_factor DECIMAL(5, 2),
  max_drawdown DECIMAL(5, 2),
  max_open_positions INT,
  peak_equity DECIMAL(20, 8),  -- all-time high at this date
  created_at TIMESTAMP
);

-- Cohort aggregation (cached for performance)
CREATE TABLE cohort_metrics (
  id UUID PRIMARY KEY,
  cohort_type VARCHAR(50),  -- 'broker', 'strategy', 'capital_tier'
  cohort_value VARCHAR(50),  -- 'binance', 'trend_following', '10k-50k'
  date DATE,
  num_users INT,
  avg_sharpe_30d DECIMAL(5, 2),
  median_sharpe_30d DECIMAL(5, 2),
  p90_sharpe_30d DECIMAL(5, 2),  -- 90th percentile
  avg_profit_factor DECIMAL(5, 2),
  avg_win_rate DECIMAL(5, 2),
  avg_max_drawdown DECIMAL(5, 2),
  created_at TIMESTAMP
);

-- Broker API health tracking
CREATE TABLE broker_health (
  id UUID PRIMARY KEY,
  broker_id INT,
  timestamp TIMESTAMP,
  status VARCHAR(20),  -- 'healthy', 'degraded', 'down'
  latency_ms INT,
  error_count INT,
  requests_succeeded INT,
  requests_failed INT,
  uptime_pct DECIMAL(5, 2)
);
```

### Real-Time Monitoring Workflow

#### Example: User Opens Dashboard

```
1. Frontend calls GET /dashboard/metrics?user_id=123
2. Backend executes:
   a. Query trades WHERE user_id=123 AND exit_time IS NOT NULL
   b. Calculate: win rate, profit factor, Sharpe from daily_metrics
   c. Query open positions from broker (cached 30s)
   d. Calculate current P&L (current_price - entry_price) * size
   e. Query daily_metrics.sharpe_30d for chart data
   f. Query cohort_metrics for benchmarking
3. Response contains:
   {
     "personal": {
       "sharpe_30d": 1.42,
       "profit_factor": 2.1,
       "win_rate": 0.58,
       "max_drawdown": 0.11,
       "daily_pnl": 1250.50
     },
     "cohort": {  // vs other Binance traders
       "avg_sharpe": 1.05,
       "percentile": 85,  // Top 15%
       "peer_avg_profit_factor": 1.8
     },
     "open_positions": [
       { "symbol": "AAPL", "entry": 150.00, "current": 151.50, "pnl_pct": 1.0 }
     ],
     "equity_curve": [  // last 30 daily snapshots
       { "date": "2026-06-01", "equity": 50000 },
       { "date": "2026-06-02", "equity": 51200 },
       ...
     ]
   }
4. Frontend renders live dashboard, charts update
```

### Monitoring KPIs

| Metric | Calculation | Update Freq | Alert Threshold |
|--------|-----------|-------------|-----------------|
| **Sharpe 30d** | (avg daily ret) / (std dev) | Daily 00:00 | < 0.5 = warning, < 0 = critical |
| **Profit Factor** | sum(win trades) / sum(loss trades) | After each trade | < 1.0 = consistent loss |
| **Win Rate** | profitable trades / total | After each trade | < 40% + low Sharpe = strategy issue |
| **Max Drawdown** | (peak - trough) / peak | Daily 00:00 | > 15% = breach risk limit |
| **Daily P&L %** | daily_pnl / opening_equity | Daily 00:00 | < -5% = approaching limit |
| **Slippage %** | (actual entry - expected) / expected | After each trade | > 0.5% = API latency warning |
| **Trade Duration** | exit_time - entry_time | After each trade | Stat tracking for strategy eval |

### Anomaly Detection Rules

```python
def detect_anomalies(user_id):
    """Runs every 15 minutes for active users"""
    
    # Rule 1: Consecutive losses
    recent_trades = get_trades(user_id, limit=5)
    if all(t.pnl < 0 for t in recent_trades):
        alert(f"User {user_id}: 5 consecutive losses, strategy drift detected")
    
    # Rule 2: Severe daily loss
    daily_pnl_pct = get_daily_pnl(user_id, today=True)
    if daily_pnl_pct < -0.05:  # -5%
        alert(f"User {user_id}: Daily loss -5%, approaching account limit")
    
    # Rule 3: Sharpe degradation
    sharpe_today = get_daily_metrics(user_id, today=True).sharpe_30d
    sharpe_yesterday = get_daily_metrics(user_id, yesterday=True).sharpe_30d
    if sharpe_today < sharpe_yesterday - 0.3:
        alert(f"User {user_id}: Sharpe dropped 0.3 points, performance degradation")
    
    # Rule 4: API failures
    api_errors = count_recent_errors(user_id, minutes=15)
    if api_errors > 10:
        alert(f"User {user_id}: 10+ API errors in 15min, broker connectivity issue")
    
    # Rule 5: Unusual position sizing
    avg_position_size = get_avg_position_size(user_id, days=30)
    latest_trade = get_latest_trade(user_id)
    if latest_trade.size > avg_position_size * 2:
        alert(f"User {user_id}: Position 2x larger than usual, risk check")
```

### Admin Monitoring Dashboard Features

**Real-Time Leaderboard**
- Users ranked by: Sharpe 30d, Daily P&L %, YTD Return, Win Rate
- Click user → see full trade log + strategy config
- Filter: broker, strategy, capital tier, signup date range

**Cohort Performance**
- Binance Futures cohort: avg Sharpe 1.1, avg daily vol 2.3%
- Alpaca cohort: avg Sharpe 1.4, avg daily vol 1.8%
- Trend Following users: avg Sharpe 1.3
- Mean Reversion users: avg Sharpe 1.0
- **Action**: Disable underperforming strategies, promote top strategies

**Activity Heatmap**
- Trades per hour (UTC) → identify peak trading times
- Identify when users typically trade (early EU, late US)
- Volume by broker (Binance dominates at 20:00-04:00 UTC)

**API Health Monitoring**
- Binance: 99.8% uptime, avg latency 45ms
- Alpaca: 99.9% uptime, avg latency 120ms
- Paper Forex: 100% (local simulator)
- Alert if any broker drops below 99%

**Revenue Metrics** (if using revenue-share model)
- Total AUM managed by platform
- % of revenue from Binance vs Alpaca users
- Churn rate (trial → inactive)
- Feature usage heatmap (% using TradingView webhooks)

---

## 9. Architecture Technique Commerciale

### High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Web Browser (React + Tailwind)       → Desktop & Tablet         │
│  └─ Dashboard, Strategy Config, Admin Panel                      │
│  └─ Real-time updates via WebSocket                              │
│                                                                   │
└───────────────────────┬────────────────────────────────────────┘
                        │
                        ↓ HTTPS
┌──────────────────────────────────────────────────────────────────┐
│                    API GATEWAY & AUTH                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  /api/v1/*                                                        │
│  ├─ JWT validation                                               │
│  ├─ Rate limiting (1000 req/min per user)                        │
│  ├─ CORS: nexquant.com only                                      │
│  └─ Request logging (audit trail)                                │
│                                                                   │
└───────────────────────┬────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   AUTH       │ │   DASHBOARD  │ │  ADMIN       │
│   SERVICE    │ │   SERVICE    │ │  SERVICE     │
├──────────────┤ ├──────────────┤ ├──────────────┤
│ Register     │ │ Position     │ │ User mgmt    │
│ Login        │ │ Metrics      │ │ Invite codes │
│ 2FA          │ │ Trade log    │ │ Analytics    │
│ Password     │ │ Alerts       │ │ Reporting    │
│ reset        │ │ Notifications│ │ API health   │
└──────────────┘ └──────────────┘ └──────────────┘

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  BROKER      │ │  STRATEGY    │ │  RISK        │
│  SERVICE     │ │  SERVICE     │ │  SERVICE     │
├──────────────┤ ├──────────────┤ ├──────────────┤
│ API connect  │ │ Strategy     │ │ Position     │
│ Order place  │ │ config       │ │ size calc    │
│ Position     │ │ TradingView  │ │ Daily loss   │
│ tracking     │ │ webhooks     │ │ Max drawdown │
│ Health       │ │ Backtest data│ │ Alerts       │
│ monitoring   │ │ (v2)         │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ↓                               ↓
┌───────────────────┐        ┌──────────────────┐
│  TRADING BOT      │        │  DATA SERVICES   │
│  (Python)         │        │  (Aggregation)   │
├───────────────────┤        ├──────────────────┤
│ Broker connectors │        │ Metrics calc     │
│ Risk manager      │        │ Cohort analytics │
│ Strategy engine   │        │ Daily snapshots  │
│ Order executor    │        │ Anomaly detect   │
│ Logging & audit   │        │ Caching (Redis)  │
└───────────────────┘        └──────────────────┘
        │                               │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
    BINANCE        ALPACA          PAPER FOREX
    (Live)         (Live)          (Simulator)
```

### Technology Stack

```
┌─ FRONTEND ─────────────────────────┐
│ React 18 + TypeScript              │
│ Tailwind CSS                       │
│ Lovable builder (component library)│
│ Recharts (charting)                │
│ Real-time: WebSocket (Socket.io)   │
│ State: Zustand (lightweight Redux) │
└────────────────────────────────────┘

┌─ BACKEND SERVICES ─────────────────┐
│ FastAPI (Python 3.11+)             │
│ Uvicorn (ASGI server)              │
│ SQLAlchemy (ORM)                   │
│ Pydantic (validation)              │
│ APScheduler (scheduled jobs)       │
│ Celery (async tasks, if needed)    │
│ Redis (caching, rate limiting)     │
│ JWT (auth tokens)                  │
└────────────────────────────────────┘

┌─ TRADING BOT ──────────────────────┐
│ Python 3.11                        │
│ Existing: broker abstraction layer │
│ Risk manager, Strategy engine      │
│ ccxt (crypto), alpaca-py, forex    │
└────────────────────────────────────┘

┌─ DATABASE ─────────────────────────┐
│ PostgreSQL 15 (primary)            │
│ TimescaleDB extension (time series)│
│ Redis (cache, sessions)            │
│ S3 (backup, export storage)        │
└────────────────────────────────────┘

┌─ INFRASTRUCTURE ───────────────────┐
│ Docker + Docker Compose            │
│ Kubernetes (EKS or managed)        │
│ Load Balancer (AWS ALB)            │
│ CDN (CloudFront for static assets) │
│ CI/CD: GitHub Actions              │
│ Logging: ELK stack or Datadog      │
│ Monitoring: Prometheus + Grafana   │
└────────────────────────────────────┘
```

### API Endpoints Summary

```
AUTH
  POST   /api/v1/auth/register
  POST   /api/v1/auth/login
  POST   /api/v1/auth/verify-email
  POST   /api/v1/auth/setup-2fa
  POST   /api/v1/auth/logout
  POST   /api/v1/auth/refresh-token

USER
  GET    /api/v1/user/profile
  PUT    /api/v1/user/profile
  GET    /api/v1/user/preferences
  PUT    /api/v1/user/preferences

BROKERS
  POST   /api/v1/brokers/connect
  POST   /api/v1/brokers/test
  GET    /api/v1/brokers/status
  GET    /api/v1/brokers/health
  DELETE /api/v1/brokers/{broker_id}

POSITIONS
  GET    /api/v1/positions
  GET    /api/v1/positions/{position_id}
  PATCH  /api/v1/positions/{position_id}/tp-sl

STRATEGIES
  GET    /api/v1/strategies
  POST   /api/v1/strategies
  PUT    /api/v1/strategies/{strategy_id}
  POST   /api/v1/strategies/{strategy_id}/activate
  POST   /api/v1/strategies/{strategy_id}/pause

TRADES
  GET    /api/v1/trades
  GET    /api/v1/trades/{trade_id}
  POST   /api/v1/trades/export

ANALYTICS
  GET    /api/v1/analytics/metrics
  GET    /api/v1/analytics/equity-curve
  GET    /api/v1/analytics/sharpe-rolling
  GET    /api/v1/analytics/trade-log

WEBHOOKS
  POST   /api/v1/webhooks/tradingview
  POST   /api/v1/webhooks/verify

RISK
  GET    /api/v1/risk/settings
  PUT    /api/v1/risk/settings
  GET    /api/v1/risk/alerts

ALERTS
  GET    /api/v1/alerts
  PATCH  /api/v1/alerts/{alert_id}/read
  PUT    /api/v1/alerts/preferences

ADMIN (requires admin role)
  GET    /api/v1/admin/users
  GET    /api/v1/admin/users/{user_id}
  POST   /api/v1/admin/users/{user_id}/extend-trial
  DELETE /api/v1/admin/users/{user_id}
  
  GET    /api/v1/admin/invite-codes
  POST   /api/v1/admin/invite-codes/generate
  DELETE /api/v1/admin/invite-codes/{code}
  
  GET    /api/v1/admin/analytics/cohort
  GET    /api/v1/admin/analytics/leaderboard
  GET    /api/v1/admin/analytics/activity-heatmap
```

### Deployment Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    CLOUD (AWS)                            │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─ VPC (Private Network) ───────────────────────────┐   │
│  │                                                    │   │
│  │  ┌─ Public Subnets ─────────────────────────────┐ │   │
│  │  │ ALB (Load Balancer)                           │ │   │
│  │  └────────────────────────────────────────────────┘ │   │
│  │              │                                        │   │
│  │              ↓                                        │   │
│  │  ┌─ Private Subnets ────────────────────────────┐ │   │
│  │  │                                              │ │   │
│  │  │ ┌─ EKS Cluster ────────────────────────┐    │ │   │
│  │  │ │                                      │    │ │   │
│  │  │ │  ┌─ Pods ──────────────┐             │    │ │   │
│  │  │ │  │ API Service         │  (3 replicas)   │ │   │
│  │  │ │  │ Dashboard Service   │             │    │ │   │
│  │  │ │  │ Admin Service       │             │    │ │   │
│  │  │ │  │ WebSocket Gateway   │             │    │ │   │
│  │  │ │  └─────────────────────┘             │    │ │   │
│  │  │ │                                      │    │ │   │
│  │  │ │  ┌─ Scheduled Jobs ────────────────┐ │   │ │   │
│  │  │ │  │ Daily Snapshots                 │ │   │ │   │
│  │  │ │  │ Metrics Recalc                  │ │   │ │   │
│  │  │ │  │ Anomaly Detection               │ │   │ │   │
│  │  │ │  └─────────────────────────────────┘ │   │ │   │
│  │  │ └──────────────────────────────────────┘   │ │   │
│  │  │                                             │ │   │
│  │  │ ┌─ Trading Bot (EC2 or separate) ───┐     │ │   │
│  │  │ │ Python bot instance               │     │ │   │
│  │  │ │ Monitoring & logging              │     │ │   │
│  │  │ └───────────────────────────────────┘     │ │   │
│  │  │                                             │ │   │
│  │  └─────────────────────────────────────────────┘ │   │
│  │              │                                    │   │
│  │              ↓                                    │   │
│  │  ┌─ Data Layer ──────────────────────────────┐  │   │
│  │  │ RDS (PostgreSQL + TimescaleDB)            │  │   │
│  │  │ ElastiCache (Redis)                       │  │   │
│  │  │ S3 (backups, exports)                     │  │   │
│  │  └─────────────────────────────────────────────┘  │   │
│  │                                                    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌─ Monitoring & Logging ────────────────────────────┐   │
│  │ CloudWatch (metrics)                               │   │
│  │ ELK Stack or Datadog (logs)                        │   │
│  │ PagerDuty (alerting)                              │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

---

## 10. Stratégie Mobile & Desktop

### Mobile App (React Native) - v2 Post-Launch

#### Rationale
- **Why v2**: Web app must be stable first (v1 = 12 weeks)
- **Why React Native**: Code sharing (40% of logic), faster dev than native iOS + Android separately
- **What's needed**: Dashboard read access + critical alerts, push notifications

#### Scope v2 Mobile

```
MINIMAL MVP (Week 1-6 post web launch)
✅ Authentication (login, 2FA)
✅ Dashboard (real-time P&L, positions, equity curve)
✅ Trade log (view past trades, no editing)
✅ Notifications (push alerts for key events)
✅ Alerts management (mark as read, snooze)
❌ Broker setup (too complex, use web)
❌ Strategy configuration (too complex, use web)
```

#### Features Mobile v2

| Feature | Scope | Rationale |
|---------|-------|-----------|
| **Real-time Dashboard** | Position tracking, P&L, Sharpe, win rate | Main use case: check status on the go |
| **Trade Notifications** | Order filled, SL hit, TP hit, daily loss alert | Critical info must reach user immediately |
| **Equity Curve Chart** | Last 30 days, monthly breakdown | Reassure user strategy working |
| **Trade History View** | Scrollable list, no editing (edit on web) | Review past trades while traveling |
| **Settings** | Notification preferences, logout | Basic account management |
| **Broker Status** | Green/red indicator, latency | Know if API is healthy |

#### Technology Stack Mobile

```
Framework: React Native + TypeScript
Libraries:
  - Navigation: React Navigation
  - Charts: react-native-chart-kit
  - Notifications: react-native-push-notification
  - Storage: @react-native-async-storage/async-storage (local cache)
  - HTTP: axios (shared with web)
  - State: Zustand (shared store with web)

Build & Deploy:
  - Expo (easier than bare React Native)
  - EAS Build (cloud building)
  - TestFlight (iOS beta)
  - Google Play Console (Android beta)
```

#### Desktop App (Tauri or Electron) - v2 Option

**Option A: Tauri Desktop App** (Recommended)
- Lightweight (~10MB vs 200MB with Electron)
- Native system tray alerts
- System notifications via native APIs
- Smaller bundle, faster startup
- **Use Case**: Traders who want persistent app, system-level alerts

**Option B: Progressive Web App (PWA)** (Simpler)
- No app download needed
- Works offline (service workers)
- Home screen icon (mobile + desktop)
- Less complex than full app
- **Drawback**: Limited system integration

**Option C: Electron App** (Heavy)
- Full OS integration
- Standalone executable
- System notifications, keyboard shortcuts
- Heavier (~200MB), slower startup
- **Use Case**: Traders wanting feature-rich desktop app

**Recommendation for NexQuant**: **Option B (PWA) + Tauri Desktop**
- PWA covers most users (web + offline)
- Tauri for power users wanting system tray + native notifications

---

## 11. Modèle de Monétisation

### Options de Monétisation

#### Option 1: Subscription Tiers (Recommended v1)

```
STARTER ($29/month)
  - Up to 3 brokers connected
  - Up to 2 strategies active
  - TradingView webhooks
  - Basic analytics (Sharpe, profit factor, win rate)
  - Email support
  → Target: Maya (passive), beginner traders

PRO ($79/month)
  - Unlimited brokers & strategies
  - Advanced analytics (Calmar ratio, Sortino, custom metrics)
  - Priority support (chat <2h response)
  - API access (for advanced users)
  - Private Discord community
  → Target: Alex (intermediate), active traders

PROFESSIONAL ($199/month or custom)
  - Everything from Pro
  - Dedicated account manager
  - Custom strategy consultation (1h/month)
  - White-label option (custom domain)
  - Multi-user teams (up to 5 users)
  → Target: Sophie (funds manager), institutions
```

**Revenue Model**: 
- Assume 500 Starter users at $29 = $14,500/mo
- Assume 200 Pro users at $79 = $15,800/mo
- Assume 20 Professional users at $199 = $3,980/mo
- **Total MRR = ~$34,280 at 720 users**

#### Option 2: Revenue Share (Alternative, High-Risk)

```
NexQuant takes 20% of monthly user profits (if > $0)
  - Alignment: NexQuant only makes money if users profit
  - Issue: Creates perverse incentives (encourage risky trading)
  - Issue: Requires insurance, compliance complexity
  - Requires: Legal review, clear ToS disclaimers

Example:
  - User makes $1000 profit → NexQuant takes $200
  - User loses $500 → NexQuant pays nothing
  - Aggregate: 500 users avg $500/mo profit = $50K / mo
  - NexQuant takes $10K / mo (20% cut)
```

**Recommendation**: Start with **Option 1 (Subscription)** for clarity and stability. Option 2 adds regulatory complexity and isn't necessary for launch.

### Pricing Psychology

**Free Trial Strategy**
- 14 days free after invite code
- Full access to all Starter features
- Encourages commitment: user sets up broker, makes trades
- If user doesn't trade in trial → low conversion risk

**Annual Discount**
- Pay yearly, get 2 months free (16.7% discount)
- Starter: $348/year (vs $348 normal, but perceived value)
- Pro: $948/year (vs $948 normal)
- **Goal**: Lock in longer commitment

**Waitlist Tier**
- Invite-only beta ($9/month or free)
- Users share feedback, evangelize product
- After beta, upgrade to standard tiers
- Creates FOMO effect: "Why wait list when beta exists?"

---

## 12. Gestion des Risques

### Risques Identifiés & Mitigation

#### Risque 1: Backtesting Engine Manquant

| Aspect | Détail |
|--------|--------|
| **Description** | Aucun backtest engine n'existe. Les stratégies ne sont pas validées sur données historiques. |
| **Impact** | High. Users may deploy unproven strategies → heavy losses → churn & reputation damage |
| **Probabilité** | Haute (100% known gap) |
| **Mitigation v1** | Launch with 3 pre-built strategies already backtested by team. Disable user custom strategies until v2. Document: "Strategies validated on 2023-2025 data, past performance ≠ future." |
| **Mitigation v2** | Implement full backtesting engine (8-10 weeks) with walk-forward validation. |
| **Owner** | Backend lead |

#### Risque 2: API Broker Failures Cascading

| Aspect | Détail |
|--------|--------|
| **Description** | Broker API (Binance, Alpaca) goes down → bot executes trades on stale data → slippage explosion |
| **Impact** | Very high. Users see unexpected losses, lose trust |
| **Probabilité** | Moyenne (1-2x/year per broker) |
| **Mitigation** | Health checks every 30s. Auto-pause bot if API latency > 1000ms. Notify user. Allow manual resume. |
| **Owner** | Backend lead |

#### Risque 3: Regulatory Compliance

| Aspect | Détail |
|--------|--------|
| **Description** | NexQuant may be considered "investment advice" or "fund management" in some jurisdictions |
| **Impact** | Very high. Fines, account seizure, product shutdown |
| **Probabilité** | Moyenne (depends on user location, if US users = high) |
| **Mitigation** | Clear ToS: "NexQuant is a technology platform, not investment advice. User assumes all trading risk." Disclaimer on every page. Consider white-label user agreements for institutional tier. Consult securities lawyer before launch. |
| **Owner** | Founder + Legal counsel |

#### Risque 4: Data Integrity / Trade Execution Errors

| Aspect | Détail |
|--------|--------|
| **Description** | Bug in risk calculation → bot places wrong position size → user loses 10x expected |
| **Impact** | Very high. Lawsuit-level incident. |
| **Probabilité** | Faible if well-tested, moyenne if rushed |
| **Mitigation** | Unit tests for all risk math. Integration tests with paper trading first. Limit trade size to 1% account for beta users. Manual approval workflow for trades > 5% account (initially). |
| **Owner** | Backend lead + QA |

#### Risque 5: False Positive Alerts (Monitoring)

| Aspect | Détail |
|--------|--------|
| **Description** | Sharpe calculation includes closed trades only, but dashboard shows "live Sharpe" mixing open position P&L |
| **Impact** | Moyenne. Users make bad decisions based on wrong metrics. |
| **Probabilité** | Moyenne if calculation not carefully defined |
| **Mitigation** | Clearly separate: "Closed-Trade Sharpe" (only closed) vs "Live Sharpe" (includes unrealized). Color-code differently. Add timestamp: "Last updated 2026-06-27 00:00 UTC". |
| **Owner** | Backend lead |

#### Risque 6: Onboarding Complexity (User Churn)

| Aspect | Détail |
|--------|--------|
| **Description** | Users struggle with API key setup, can't connect brokers → abandon after 5 min |
| **Impact** | Moyenne. Low conversion, high support load. |
| **Probabilité** | Haute if UX not polished |
| **Mitigation** | Step-by-step wizard with screenshots. Video tutorials (3-5 min). Live chat support. Auto-detect errors: "API key invalid, paste this exact format: ...". Test in beta with 20 non-technical users, iterate UX. |
| **Owner** | Frontend lead + UX designer |

#### Risque 7: Trade History Data Loss

| Aspect | Détail |
|--------|--------|
| **Description** | Database corruption → all user trade history deleted → legal liability |
| **Impact** | Very high. Lawsuits, regulatory fines. |
| **Probabilité** | Très faible if proper backups |
| **Mitigation** | Automated daily backups (S3). Point-in-time recovery capability. Immutable audit log (append-only). Test restore procedure monthly. |
| **Owner** | DevOps lead |

#### Risque 8: Sharpe Ratio Miscalculation

| Aspect | Détail |
|--------|--------|
| **Description** | Sharpe formula implemented wrong → users see inflated metrics → make unrealistic decisions |
| **Impact** | Moyenne. Damages credibility, but not financial liability. |
| **Probabilité** | Moyenne if not carefully validated |
| **Mitigation** | Unit test Sharpe calculation against known historical datasets. Compare with manual Excel calc. Validate for corner cases: 0 trades, all losses, single day. |
| **Owner** | Backend lead + QA |

#### Risque 9: Mobile App Store Rejection

| Aspect | Détail |
|--------|--------|
| **Description** | Apple/Google reject app for involving financial trading, unsubstantiated profit claims, etc. |
| **Impact** | Moyenne. Delays mobile launch by 4-8 weeks. |
| **Probabilité** | Moyenne (depends on how app marketed) |
| **Mitigation** | Review Apple/Google financial app guidelines early. Avoid: "Guaranteed profits", "Make $10K/month", testimonials. Focus: "Automated trading tool" + disclaimers. Get lawyer to review app description. Submit early to identify issues. |
| **Owner** | Mobile lead + Founder |

### Risk Mitigation Timeline

| Risque | Mitigation Timing | Owner |
|--------|-------------------|-------|
| Backtesting gap | Pre-launch review (week 11) | Founder, Backend |
| API failures | Implement health checks (week 3) | Backend |
| Compliance | Legal review (week 1, ongoing) | Founder, Lawyer |
| Trade errors | Unit tests, integration tests (week 4-8) | Backend, QA |
| Monitoring false positives | Validation, beta testing (week 10) | Backend, QA |
| Onboarding UX | Iterative design, user testing (week 2-8) | Frontend, Design |
| Data loss | Backup strategy, testing (week 1) | DevOps |
| Sharpe calc | Unit tests, validation (week 7) | Backend, QA |
| App store rejection | Review guidelines, submit early (week 14) | Mobile, Founder |

---

## 13. Timeline & Jalons

### Gantt Chart (Weeks 1-16)

```
Week 1-2 (Setup & Auth)
  ├─ Auth system (register, login, 2FA) ............ ████░░░░░░░░░░░░ Backend
  ├─ Database schema setup ....................... ███░░░░░░░░░░░░░░ Backend
  ├─ Frontend basic layout (Lovable) ............. ████░░░░░░░░░░░░ Frontend
  └─ Legal review begins (ToS, compliance) ....... █░░░░░░░░░░░░░░░░ Legal

Week 2-4 (Broker Integration)
  ├─ Binance API connector ....................... ████░░░░░░░░░░░░ Backend
  ├─ Alpaca API connector ........................ ████░░░░░░░░░░░░ Backend
  ├─ Broker setup UI (wizard) .................... ████░░░░░░░░░░░░ Frontend
  ├─ API key encryption & vault ................. ███░░░░░░░░░░░░░░ Backend
  └─ Paper Forex simulator ...................... ███░░░░░░░░░░░░░░ Backend

Week 3-5 (Core Trading Features)
  ├─ Real-time position tracking ................ ████░░░░░░░░░░░░ Backend
  ├─ Paper trading mode ......................... ████░░░░░░░░░░░░ Backend
  ├─ Trade execution & logging .................. █████░░░░░░░░░░░░ Backend
  ├─ Dashboard UI (positions, P&L) .............. ████░░░░░░░░░░░░ Frontend
  └─ WebSocket real-time updates ................ ███░░░░░░░░░░░░░░ Backend

Week 5-7 (Strategy & Risk)
  ├─ Pre-built strategies implementation ........ █████░░░░░░░░░░░░ Backend
  ├─ Strategy configuration UI .................. ████░░░░░░░░░░░░ Frontend
  ├─ TradingView webhook integration ............ ████░░░░░░░░░░░░ Backend
  ├─ Risk management rules ...................... ████░░░░░░░░░░░░ Backend
  ├─ Risk configuration UI ...................... ███░░░░░░░░░░░░░░ Frontend
  └─ Unit tests for risk calculations .......... ██░░░░░░░░░░░░░░░ QA

Week 6-9 (Monitoring & Analytics)
  ├─ Trade logging & analytics engine ........... █████░░░░░░░░░░░░ Backend
  ├─ Daily snapshots scheduler .................. ███░░░░░░░░░░░░░░ Backend
  ├─ Sharpe ratio calculation & validation ..... ████░░░░░░░░░░░░ Backend
  ├─ Trade history UI & filtering .............. ████░░░░░░░░░░░░ Frontend
  ├─ Metrics dashboard UI ....................... ████░░░░░░░░░░░░ Frontend
  ├─ Equity curve charting ...................... ███░░░░░░░░░░░░░░ Frontend
  └─ Anomaly detection rules .................... ███░░░░░░░░░░░░░░ Backend

Week 8-12 (Admin Panel & Demo Rollout)
  ├─ Invite code system ......................... ███░░░░░░░░░░░░░░ Backend
  ├─ User management endpoints .................. ███░░░░░░░░░░░░░░ Backend
  ├─ Admin dashboard UI (users, analytics) ...... █████░░░░░░░░░░░░ Frontend
  ├─ Broker health monitoring ................... ██░░░░░░░░░░░░░░░░ Backend
  ├─ Cohort analytics ........................... ███░░░░░░░░░░░░░░ Backend
  ├─ Trial expiry & auto-revocation ............ ███░░░░░░░░░░░░░░ Backend
  └─ Notifications system (email, push) ......... ███░░░░░░░░░░░░░░ Backend

Week 9-11 (QA, Testing & Bug Fixes)
  ├─ Integration testing ........................ ████░░░░░░░░░░░░ QA
  ├─ Broker sandbox testing (Binance testnet) .. ███░░░░░░░░░░░░░░ QA
  ├─ Paper trading validation .................. ███░░░░░░░░░░░░░░ QA
  ├─ UI/UX bug fixes & polish ................... ████░░░░░░░░░░░░ Frontend
  ├─ Performance testing (load, latency) ....... ███░░░░░░░░░░░░░░ QA
  └─ Security audit ............................ ██░░░░░░░░░░░░░░░░ Security

Week 10-12 (Beta Rollout Prep)
  ├─ Deploy to staging .......................... ██░░░░░░░░░░░░░░░░ DevOps
  ├─ Documentation & video tutorials ........... ████░░░░░░░░░░░░ Content
  ├─ Support system setup (email, chat) ........ ██░░░░░░░░░░░░░░░░ Support
  ├─ Marketing prep (landing page, email) ..... ███░░░░░░░░░░░░░░ Marketing
  └─ **BETA LAUNCH** (limited users, 14-day trial)

Week 12-16 (Commercial Launch)
  ├─ Monitor beta (feedback, bugs) ............. ████░░░░░░░░░░░░ Full team
  ├─ Deploy to production ...................... ██░░░░░░░░░░░░░░░░ DevOps
  ├─ Payment processing setup (Stripe/Paddle) . ██░░░░░░░░░░░░░░░░ Backend
  ├─ Subscription management UI ................ ███░░░░░░░░░░░░░░ Frontend
  ├─ Onboarding optimization (user feedback) .. ███░░░░░░░░░░░░░░ Product
  └─ **COMMERCIAL LAUNCH** (public signup, paid subscriptions)

Post-Launch (Weeks 17+)
  ├─ Mobile app development (React Native) .... ███████░░░░░░░░░░ 10 weeks
  ├─ Backtesting engine v2 ..................... ████████░░░░░░░░░ 12 weeks
  ├─ Advanced analytics & reporting ............ ███████░░░░░░░░░░ 8 weeks
  └─ White-label / institutional features .... ███████░░░░░░░░░░ 10 weeks
```

### Key Milestones

| Milestone | Date (Estimate) | Criteria |
|-----------|-----------------|----------|
| **Alpha Ready** | Week 2 | Auth + broker setup + paper trading working |
| **Core Trading Ready** | Week 5 | Position tracking + strategy execution + risk mgmt |
| **Analytics Ready** | Week 9 | Sharpe calculation + daily snapshots validated |
| **Beta Ready** | Week 12 | Admin panel + invite codes + monitoring all working, QA passed |
| **Commercial Ready** | Week 16 | Payments, subscriptions, support, full compliance review |
| **Mobile v2 Ready** | Week 26 (post-launch +10w) | React Native app, TestFlight/Play Store submit |

### Go-Live Checklist

```
BEFORE BETA (Week 11):
☐ All Tier 1-2 features tested (integration tests passed)
☐ Sharpe calculation validated against known datasets
☐ Database backup/restore tested
☐ SSL certificate installed
☐ CORS whitelist configured
☐ Rate limiting active
☐ Admin panel tested with 50 mock users
☐ Legal: ToS + privacy policy finalized
☐ Compliance: Risk disclaimer visible
☐ Support email/chat ready

BEFORE COMMERCIAL (Week 15):
☐ Beta feedback incorporated
☐ Payment processing (Stripe) integrated & tested
☐ Subscription tiers live
☐ 50+ beta users monitored, no critical bugs
☐ Broker API connections stable (< 1% error rate)
☐ Average Sharpe of beta users > 1.0 (validates strategy)
☐ Load tested: 100 concurrent users, no lag
☐ Onboarding: < 5min from signup to first trade
☐ All analytics calculated and visible
☐ Mobile roadmap documented (not launched)
```

---

## Conclusion

This Phase 1 blueprint defines NexQuant's commercial architecture, features, monitoring strategy, and go-to-market plan. The next steps are:

1. **Validate with stakeholders** (investors, early users, advisors)
2. **Allocate team resources** (assign owners to each feature)
3. **Set up infrastructure** (AWS account, databases, CI/CD)
4. **Begin Week 1 implementation** (auth + database schema)

The timeline of 12-16 weeks to commercial launch is aggressive but achievable with focused execution. Critical success factors:

- **Quality over speed**: Trading bot bugs are existential; better to slip deadline than launch broken
- **User feedback loop**: Beta with real traders, iterate rapidly
- **Compliance**: Legal review early, not last-minute
- **Monitoring infrastructure**: Multi-user platform requires robust alerting

**Estimated Team Size**: 8-10 people (4-5 backend/fullstack, 2-3 frontend, 1 DevOps, 1 QA, 1 Product lead)

**Total Development Cost**: ~$300-500K (labor + infrastructure, depending on location)

**Expected ROI**: Break-even at ~500 Pro users ($15.8K/MRR), reaching profitability at 1000+ users within 6 months of commercial launch.

---

**Document Version**: 1.0  
**Last Updated**: June 2026  
**Next Review**: Before Week 1 kickoff (when team alignment confirmed)
