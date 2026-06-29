# Charte Graphique & Design System — NexQuant

Ce document définit la charte graphique globale, le design system, les spécifications des composants réutilisables, et fournit un plan de conception filaire (wireframes) prêt à être transposé sur Miro pour les versions Web, Desktop et Mobile de NexQuant.

---

## 🎨 1. La Charte Graphique (Visual Brand Identity)

L'univers de NexQuant se veut **technologique, précis, haut de gamme et immersif**. L'esthétique repose sur un **sombre profond (Deep Dark)** contrasté par des accents de couleur néon, le tout enveloppé dans des conteneurs à effet de verre (**Glassmorphism**) évoquant la transparence des données et l'aspect institutionnel des terminaux de trading quantitatif.

---

### 🎨 Palette de Couleurs (Color System)

| Usage | Nom de Couleur | Code Hex | Description | Équivalence Tailwind |
| :--- | :--- | :--- | :--- | :--- |
| **Fond Principal** | Slate 950 | `#030712` / `#09090b` | Fond sombre profond pour le contraste | `bg-zinc-950` / `bg-slate-950` |
| **Fond Cartes/Verre** | Zinc 900 / 80 | `#18181b` (80% opacity) | Conteneur avec effet de verre dépoli | `bg-zinc-900/80` + `backdrop-blur-md` |
| **Accents Primaires** | Indigo Glow / Purple | `#6366f1` / `#8b5cf6` | Statuts système actifs, branding, highlights | `text-indigo-500` / `bg-indigo-600` |
| **Valeurs Positives** | Emerald Neon | `#10b981` / `#00f2fe` | Trades gagnants, PnL positif, Sharpe élevé | `text-emerald-400` |
| **Alertes / Drawdown** | Crimson Red | `#ef4444` / `#f43f5e` | Drawdown max, pertes, arrêt d'urgence bot | `text-red-500` |
| **Bordures/Séparateurs** | Border Gray | `rgba(255,255,255,0.08)` | Bordures fines et subtiles pour délimiter | `border-white/10` |

---

### 🔤 Typographie (Typography Scale)

*   **Police des Titres (Headings) :** `Space Grotesk` (Google Fonts). Un style géométrique, moderne et légèrement futuriste, idéal pour l'aspect quantitatif et technique.
*   **Police de Labeur (UI & Textes) :** `Inter` (Sans-serif). Pour une lisibilité irréprochable et compacte dans les grilles de nombres et graphes.

```css
/* Intégration CSS recommandée */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

body {
  font-family: 'Inter', sans-serif;
}
h1, h2, h3, h4, .font-technical {
  font-family: 'Space Grotesk', sans-serif;
}
```

---

### ✨ Principes du Glassmorphism & Micro-animations

1.  **Backdrop Blur :** Toutes les cartes doivent avoir une opacité réduite (`bg-zinc-900/80`) couplée à un flou d'arrière-plan (`backdrop-blur-md` ou `12px`).
2.  **Liseré Lumineux :** Les bordures doivent être ultra-fines (`1px solid rgba(255,255,255,0.08)`).
3.  **Glow Effet sur Survol :** Lors du survol des cartes interactives, appliquer une lueur subtile de la couleur de l'accent associé.
4.  **Transitions :** Toujours utiliser `transition-all duration-300 ease-in-out` sur les boutons, toggles et cartes pour adoucir le feedback visuel.

---

## 🧩 2. Les Composants Réutilisables (Design System)

Voici les spécifications et le code technique pour les composants clés. Chaque composant a été implémenté en TypeScript / React 19 et est disponible sous `src/components`.

> [!TIP]
> Vous pouvez tester ces composants de manière interactive et consulter leur rendu en direct sur la route publique :
> **[/design-system](file:///c:/Users/Pavillon/Desktop/nexquant_v2/nexquant/NexQuant_Web_App/src/routes/design-system.tsx)**

---

### 📦 Composant A : `MetricCard` (Carte de performance quantitative)

#### 📝 Documentation & Rôle
Affiche une métrique clé de performance (Sharpe, Profit Factor, PnL, WinRate) avec un indicateur de tendance, une aide contextuelle (Tooltip) et une lueur de survol.

```tsx
import React from 'react';
import { HelpCircle, TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  isPositive?: boolean;
  tooltipText: string;
  glowColor?: 'indigo' | 'emerald' | 'rose';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  isPositive = true,
  tooltipText,
  glowColor = 'indigo'
}) => {
  const glowMap = {
    indigo: 'hover:shadow-[0_0_20px_rgba(99,102,241,0.15)] hover:border-indigo-500/30',
    emerald: 'hover:shadow-[0_0_20px_rgba(16,185,129,0.15)] hover:border-emerald-500/30',
    rose: 'hover:shadow-[0_0_20px_rgba(244,63,94,0.15)] hover:border-rose-500/30',
  };

  return (
    <div className={`relative overflow-hidden rounded-xl border border-white/10 bg-zinc-900/40 p-6 backdrop-blur-md transition-all duration-300 ${glowMap[glowColor]}`}>
      <div className="flex items-center justify-between text-zinc-400 text-xs font-medium uppercase tracking-wider">
        <span>{title}</span>
        <div className="group relative cursor-pointer">
          <HelpCircle className="h-4 w-4 text-zinc-500 transition-colors hover:text-zinc-300" />
          <span className="pointer-events-none absolute right-0 top-6 w-48 rounded bg-zinc-950 p-2 text-2xs text-zinc-300 opacity-0 shadow-lg border border-white/15 backdrop-blur-md transition-opacity group-hover:opacity-100 z-50">
            {tooltipText}
          </span>
        </div>
      </div>
      
      <div className="mt-4 flex items-baseline justify-between">
        <span className="text-3xl font-bold font-technical text-white tracking-tight">{value}</span>
        {change && (
          <span className={`flex items-center gap-1 text-xs font-semibold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isPositive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
            {change}
          </span>
        )}
      </div>
      <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-white/5 to-transparent" />
    </div>
  );
};
```

---

### 📦 Composant B : `BotStatusIndicator` (Indicateur de statut système)

#### 📝 Documentation & Rôle
Présente visuellement l'état d'exécution du bot quantitatif local avec un témoin lumineux pulsant, des données de latence et la dernière mise à jour.

```tsx
import React from 'react';

type StatusType = 'running' | 'stopped' | 'error';

interface BotStatusIndicatorProps {
  status: StatusType;
  lastHeartbeat: string;
  latencyMs: number;
}

export const BotStatusIndicator: React.FC<BotStatusIndicatorProps> = ({
  status,
  lastHeartbeat,
  latencyMs
}) => {
  const statusConfig = {
    running: {
      color: 'bg-emerald-500',
      glow: 'shadow-[0_0_12px_rgba(16,185,129,0.6)]',
      pulse: 'animate-ping',
      text: 'Opérationnel',
      textColor: 'text-emerald-400'
    },
    stopped: {
      color: 'bg-amber-500',
      glow: 'shadow-[0_0_12px_rgba(245,158,11,0.6)]',
      pulse: '',
      text: 'En Veille',
      textColor: 'text-amber-400'
    },
    error: {
      color: 'bg-rose-500',
      glow: 'shadow-[0_0_12px_rgba(244,63,94,0.6)]',
      pulse: 'animate-pulse',
      text: 'Erreur Système',
      textColor: 'text-rose-400'
    }
  };

  const current = statusConfig[status];

  return (
    <div className="flex items-center gap-6 rounded-lg border border-white/10 bg-zinc-900/60 p-4 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <div className="relative flex h-3.5 w-3.5">
          {status === 'running' && (
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${current.color} ${current.pulse}`} />
          )}
          <span className={`relative inline-flex h-3.5 w-3.5 rounded-full ${current.color} ${current.glow}`} />
        </div>
        <div className="flex flex-col">
          <span className="text-2xs text-zinc-500 uppercase tracking-widest font-semibold">Statut Bot</span>
          <span className={`text-sm font-bold ${current.textColor}`}>{current.text}</span>
        </div>
      </div>

      <div className="h-8 w-[1px] bg-white/10" />

      <div className="flex flex-col">
        <span className="text-2xs text-zinc-500 uppercase tracking-widest font-semibold">Ping API</span>
        <span className="text-sm font-semibold font-technical text-white">{latencyMs} ms</span>
      </div>

      <div className="h-8 w-[1px] bg-white/10" />

      <div className="flex flex-col">
        <span className="text-2xs text-zinc-500 uppercase tracking-widest font-semibold">Dernier Signe</span>
        <span className="text-xs text-zinc-300 font-technical">{lastHeartbeat}</span>
      </div>
    </div>
  );
};
```

---

### 📦 Composant C : `ControlPanel` (Panneau d'activation & Risque)

#### 📝 Documentation & Rôle
Permet à l'utilisateur de déclencher le démarrage ou l'arrêt d'urgence du bot local à distance, et de gérer le niveau d'exposition au risque.

```tsx
import React, { useState } from 'react';
import { Play, Square, AlertTriangle } from 'lucide-react';

interface ControlPanelProps {
  initialIsRunning: boolean;
  onToggleStatus: (newStatus: boolean) => Promise<void>;
  initialRiskPct: number;
  onRiskChange: (newRisk: number) => Promise<void>;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  initialIsRunning,
  onToggleStatus,
  initialRiskPct,
  onRiskChange
}) => {
  const [isRunning, setIsRunning] = useState(initialIsRunning);
  const [risk, setRisk] = useState(initialRiskPct);
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    setLoading(true);
    try {
      await onToggleStatus(!isRunning);
      setIsRunning(!isRunning);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRiskSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRisk(Number(e.target.value));
  };

  const handleApplyRisk = async () => {
    setLoading(true);
    try {
      await onRiskChange(risk);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/50 p-6 backdrop-blur-md">
      <h3 className="text-lg font-bold font-technical text-white mb-6">Console de Pilotage</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Toggle principal */}
        <div className="flex flex-col justify-between p-4 rounded-lg bg-zinc-950/40 border border-white/5">
          <div>
            <span className="text-xs text-zinc-400 font-semibold uppercase tracking-wider block">Mode de Fonctionnement</span>
            <p className="text-2xs text-zinc-500 mt-1">Le changement d'état sera répercuté lors du prochain cycle de polling (30s maximum).</p>
          </div>
          <button
            onClick={handleToggle}
            disabled={loading}
            className={`mt-4 w-full flex items-center justify-center gap-2 rounded-lg py-3.5 font-bold transition-all duration-300 ${
              isRunning
                ? 'bg-rose-500 hover:bg-rose-600 text-white shadow-[0_0_15px_rgba(239,68,68,0.2)]'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-[0_0_15px_rgba(99,102,241,0.2)]'
            } disabled:opacity-50`}
          >
            {isRunning ? (
              <>
                <Square className="h-5 w-5 fill-white" />
                Arrêter le Bot (Stop)
              </>
            ) : (
              <>
                <Play className="h-5 w-5 fill-white" />
                Lancer le Bot (Start)
              </>
            )}
          </button>
        </div>

        {/* Configuration du Risque */}
        <div className="flex flex-col justify-between p-4 rounded-lg bg-zinc-950/40 border border-white/5">
          <div>
            <span className="text-xs text-zinc-400 font-semibold uppercase tracking-wider block">Exposition par Trade</span>
            <div className="flex items-center justify-between mt-3">
              <span className="text-2xl font-bold font-technical text-white">{risk}%</span>
              <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> Max recommandé: 2.5%
              </span>
            </div>
          </div>
          <div className="mt-4 flex flex-col gap-2">
            <input
              type="range"
              min="0.1"
              max="5"
              step="0.1"
              value={risk}
              onChange={handleRiskSliderChange}
              className="w-full accent-indigo-500 cursor-pointer h-1.5 rounded bg-zinc-800"
            />
            <button
              onClick={handleApplyRisk}
              disabled={loading || risk === initialRiskPct}
              className="mt-2 text-xs font-semibold text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 border border-white/5 py-2 rounded transition-all"
            >
              Appliquer à chaud
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

### 📦 Composant D : `CookieConsentModal` & `GDPRBanner` (Sécurité & Consentement)

#### 📝 Documentation & Rôle
Garantit la conformité RGPD/GDPR de l'application en demandant le consentement des cookies et en exposant les paramètres de gestion de données.

```tsx
import React, { useState, useEffect } from 'react';
import { Shield, Eye } from 'lucide-react';

export const GDPRBanner: React.FC = () => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('nexquant_gdpr_consent');
    if (!consent) {
      setShow(true);
    }
  }, []);

  const handleAcceptAll = () => {
    localStorage.setItem('nexquant_gdpr_consent', 'all');
    setShow(false);
  };

  const handleDeclineAll = () => {
    localStorage.setItem('nexquant_gdpr_consent', 'essential');
    setShow(false);
  };

  if (!show) return null;

  return (
    <div className="fixed bottom-6 inset-x-6 z-[999] max-w-4xl mx-auto rounded-xl border border-white/10 bg-zinc-950/90 p-5 shadow-2xl backdrop-blur-lg animate-in slide-in-from-bottom duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">Respect de votre vie privée (RGPD)</h4>
            <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
              Nous utilisons des cookies essentiels au bon fonctionnement (gating de licence) et des outils de mesure anonymes. Vous pouvez configurer ou accepter notre <a href="/legal/privacy" className="text-indigo-400 hover:underline">Politique de Confidentialité</a>.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 md:self-end">
          <button
            onClick={handleDeclineAll}
            className="text-xs text-zinc-400 hover:text-white px-3 py-2 rounded bg-transparent hover:bg-white/5 transition-all"
          >
            Refuser les cookies tiers
          </button>
          <button
            onClick={handleAcceptAll}
            className="text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2.5 rounded-lg shadow-lg transition-all"
          >
            Tout accepter
          </button>
        </div>
      </div>
    </div>
  );
};
```

---

## 🗺️ 3. Plan Design des Interfaces pour Copier-Coller dans Miro

Cette section fournit les **blueprints textuels** structurés en grilles et l'agencement exact des écrans, directement prêts à être traduits en formes visuelles dans Miro (boutons, containers, inputs).

```
   ┌─────────────────────────────────────────────────────────────┐
   │                        MIRO GRID LAYOUT                     │
   │                                                             │
   │  ┌───────────────────────┐       ┌───────────────────────┐  │
   │  │   FRAME 1: DASHBOARD   │       │ FRAME 2: STRATÉGIES   │  │
   │  │   & PORTFOLIO CONTROL │ ────> │ & ALERTE TRADINGVIEW  │  │
   │  └───────────────────────┘       └───────────────────────┘  │
   │              │                                │             │
   │              ▼                                ▼             │
   │  ┌───────────────────────┐       ┌───────────────────────┐  │
   │  │   FRAME 3: BILLING    │       │   FRAME 4: SETTINGS   │  │
   │  │   & ABONNEMENTS (LS)  │       │   & CONFORMITÉ RGPD   │  │
   │  └───────────────────────┘       └───────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
```

---

### 🔲 Frame 1 : Dashboard de Trading & Console Bot
*   **Dimensions Miro recommandées :** `1920 x 1080` (Standard Desktop)
*   **Fond de Frame :** Noir Zinc `#09090B`
*   **Notes adhésives de disposition (Layout Grid) :**

#### A. En-tête (Navbar)
*   [ ] **Logo Shape (Glow violet) :** `NexQuant` (Space Grotesk Bold, `#FFFFFF` avec ombre portée Violette)
*   [ ] **Navigation Links (Horizontal) :** `Tableau de bord` (actif, blanc), `Stratégies`, `Facturation`, `Paramètres` (gris, `#A1A1AA`)
*   [ ] **Composant Status :** Placer le widget `BotStatusIndicator` (Opérationnel, 12 ms, Mise à jour il y a 3s) dans le coin supérieur droit.

#### B. Grille de Métriques (3 Colonnes)
*   [ ] **Col 1 (Card Sharpe) :**
    *   Titre : Ratio Sharpe (90j)
    *   Valeur principale : `2.42`
    *   Delta tendance : `+0.18` (Vert Emerald)
    *   Tooltip : "Mesure de rentabilité ajustée au risque. > 2.0 = Excellent"
*   [ ] **Col 2 (Card Profit Factor) :**
    *   Titre : Profit Factor
    *   Valeur principale : `1.84`
    *   Delta tendance : `+0.05` (Vert Emerald)
    *   Tooltip : "Rapport entre les gains cumulés et les pertes cumulées."
*   [ ] **Col 3 (Card Max Drawdown) :**
    *   Titre : Drawdown Maximum
    *   Valeur principale : `-4.12%`
    *   Delta tendance : `-0.85%` (Rouge Crimson)
    *   Tooltip : "La plus grande baisse de capital historique subie à partir d'un sommet."

#### C. Section Centrale (2 Colonnes : 2/3 - 1/3)
*   **Colonne Gauche (Large) :**
    *   [ ] **Card Equity Curve :** Graphe linéaire Recharts avec dégradé transparent sous la ligne d'équité (Dégradé Emerald pour la croissance, liseré rouge en cas de creux sous le sommet historique).
    *   [ ] Zones de Drawdown hachurées en rouge clair (`rgba(239,68,68,0.15)`).
*   **Colonne Droite (Étroite) :**
    *   [ ] **Widget Control Panel :** Bouton d'activation Start/Stop et Slider d'exposition au risque.

#### D. Section Basse
*   [ ] **Table des positions ouvertes :** Colonnes `Symbole` \| `Sens` \| `Taille` \| `Entrée` \| `Prix Actuel` \| `PnL Non Réalisé (Glow Vert/Rouge)`.

---

### 🔲 Frame 2 : Stratégies & Signaux Webhook
*   **Objectif :** Permettre le paramétrage des règles de trading à distance.
*   **Note de Design :** Grid à 2 colonnes asymétriques.

#### A. Liste des Stratégies actives (Col 1)
*   [ ] **Card Stratégie 1 (Active) :**
    *   Badge : `EMA Cross` (Tendance)
    *   Toggle : Activé (Glow Indigo)
    *   Paramètres visibles : `Fast EMA: 9` \| `Slow EMA: 21` \| `Timeframe: 5m`
*   [ ] **Card Stratégie 2 (Inactive) :**
    *   Badge : `RSI Scalper` (Contre-tendance)
    *   Toggle : Désactivé
    *   Paramètres visibles : `RSI Period: 14` \| `Oversold: 30` \| `Overbought: 70`

#### B. Panneau d'instructions Webhook (Col 2)
*   [ ] **Input Box (Lecture seule) :** URL Webhook TradingView (`https://nexquant.io/api/public/webhook`) avec bouton "Copier dans le presse-papier".
*   [ ] **Secret Key Box (Chiffrée) :** Token d'authentification HMAC unique (`nq_sec_*********************`)
*   [ ] **Code Block JSON (Exemple de payload TradingView à copier dans Miro) :**
```json
{
  "secret": "{{USER_SECRET_KEY}}",
  "symbol": "BTCUSDT",
  "action": "buy",
  "risk_pct": 1.5,
  "leverage": 5
}
```

---

### 🔲 Frame 3 : Facturation & Gating (Lemon Squeezy Integration)
*   **Objectif :** Configurer les abonnements et informer de l'état de la licence.

#### A. Bandeau d'état (Si Version d'essai active)
*   [ ] **Banner d'information (Jaune/Orange d'avertissement) :** "Version d'essai gratuite. Il vous reste 4 jours avant l'activation obligatoire d'une licence pour continuer le trading automatisé."

#### B. Tarifs (3 Cartes Miro distinctes)
*   [ ] **Card Tiers 1 : "Starter"**
    *   Prix : `29$ / mois`
    *   Avantages : 1 Bot actif \| Binance Futures uniquement \| Support standard.
    *   Bouton d'achat : `Souscrire`
*   [ ] **Card Tiers 2 : "Pro" (Recommandée - Contour violet glow)**
    *   Prix : `79$ / mois`
    *   Avantages : 3 Bots actifs \| Binance & Alpaca \| Support prioritaire.
    *   Bouton d'achat : `Choisir Pro` (Glow violet)
*   [ ] **Card Tiers 3 : "Professional"**
    *   Prix : `199$ / mois`
    *   Avantages : Bots illimités \| Tous brokers (y compris MT5 expérimental) \| API d'exécution ultra-rapide.
    *   Bouton d'achat : `Contacter la vente`

---

### 🔲 Frame 4 : Paramètres du Profil & Conformité RGPD
*   **Objectif :** Paramètres personnels et exercice des droits légaux.

#### A. Bloc API Keys (Stockage chiffré Vault)
*   [ ] Formulaire d'ajout des clés API Binance / Alpaca avec encart d'avertissement vert : "Vos clés d'API sont cryptées en base de données avec l'algorithme AES-256."

#### B. Bloc RGPD & Vie Privée (Zone Critique de Conformité)
*   [ ] **Bouton 1 (Export des données) :** `Exporter mes données (Format JSON)`
    *   *Miro Sticky Note :* "Déclenche l'envoi d'une archive JSON contenant l'historique complet des trades, les configurations de risque passées et les informations de profil (Article 20 RGPD - Portabilité)."
*   [ ] **Bouton 2 (Effacement complet - Rouge Crimson) :** `Supprimer définitivement mon compte`
    *   *Miro Sticky Note :* "Supprime le profil, l'abonnement et révoque instantanément toutes les clés API du coffre-fort de données (Article 17 RGPD - Droit à l'oubli)."
*   [ ] **Politique de conservation :** "Les logs système techniques de vos bots sont purgés automatiquement de nos serveurs après 90 jours."
