# ⚛️ NexQuant — Web App Frontend Console

Ce répertoire contient l'application web frontend de la console SaaS de **NexQuant**. Elle est construite avec **React**, **Vite**, **TypeScript** et **Tailwind CSS**. Elle permet aux utilisateurs de gérer leurs abonnements Stripe, de configurer leurs clés d'API broker de manière sécurisée et de superviser leurs bots locaux à distance en temps réel.

---

## ⚠️ Avertissement Important : Intégration Lovable

> [!CAUTION]
> **Règle de Synchronisation Git & Lovable**
> Ce projet est connecté à la plateforme [Lovable.dev](https://lovable.dev).
> 
> * **Ne réécrivez JAMAIS l'historique Git publié** (pas de `git push --force`, `git rebase` ou `git commit --amend` sur les commits déjà poussés). Cela perturbe la synchronisation de Lovable et pourrait entraîner la perte définitive de l'historique du projet.
> * Gardez toujours la branche connectée dans un état fonctionnel et stable, car chaque commit poussé est immédiatement synchronisé avec l'éditeur de Lovable.

---

## 🛠️ Démarrage Rapide (Développement)

### 1. Prérequis
Assurez-vous d'avoir installé **Node.js** (v18+) ou de préférence **Bun** pour une vitesse de traitement optimale des packages.

### 2. Installation des dépendances
Utilisez Bun (recommandé) ou npm pour installer les dépendances du projet :
```bash
bun install
# ou
npm install
```

### 3. Configuration des Variables d'Environnement
Créez un fichier `.env.local` dans ce répertoire et renseignez les identifiants d'accès à votre instance Supabase :
```env
VITE_SUPABASE_URL=https://votre-url-supabase.supabase.co
VITE_SUPABASE_ANON_KEY=votre-cle-anonyme-supabase
```

### 4. Lancement du Serveur de Développement
Pour démarrer le serveur de développement local avec rechargement automatique :
```bash
bun run dev
# ou
npm run dev
```
L'interface sera alors accessible dans votre navigateur à l'adresse par défaut : `http://localhost:5173`.

---

## 🚀 Construction pour la Production

Pour compiler le code source et générer le bundle de production optimisé dans le dossier `dist/` :
```bash
bun run build
# ou
npm run build
```

---

## 📂 Organisation du Code Source

* **`src/components/`** : Composants graphiques réutilisables (graphiques P&L, cartes de performance, tableaux de positions, indicateurs d'état).
* **`src/pages/`** : Pages principales (Dashboard principal, Configuration des API Brokers, Profil utilisateur, Facturation Stripe).
* **`src/integrations/`** : Clients d'intégration pour Supabase, synchronisation de la télémétrie, et requêtes de contrôle à distance (pause/reprise).
* **`supabase/`** : Schémas des tables SQL, fonctions de chiffrement de Supabase Vault, et politiques de sécurité (RLS) pour les comptes clients.
