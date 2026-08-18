# NexQuant WebApp - Design System

Ce document définit les règles d'interface utilisateur (UI), d'expérience utilisateur (UX) et l'esthétique générale de la WebApp NexQuant, garantissant ainsi la cohérence visuelle avec l'application actuelle.

## Philosophie Générale
L'esthétique de NexQuant est orientée **Fintech Premium & Cyberpunk Soft**.
- **Ambiance** : Sombre, épurée, avec des touches de couleurs néon/glow subtiles.
- **Focus** : Les données et les graphiques doivent être les éléments les plus visibles.
- **Micro-interactions** : Les boutons et les cartes utilisent des transitions fluides (hover, focus) pour donner vie à l'interface.

## 1. Palette de Couleurs (Tailwind / CSS Variables)

La WebApp utilise un thème sombre natif basé sur le système de variables CSS standardisées.

### Couleurs de Base (Backgrounds & Surfaces)
- **Background Principal** : `hsl(var(--background))` (Typiquement un noir très profond ou gris très sombre : `#09090b`).
- **Foreground (Texte)** : `hsl(var(--foreground))` (Typiquement un blanc cassé : `#fafafa`).
- **Cartes & Panneaux (Muted/Cards)** : Utiliser des fonds avec opacité comme `bg-background/40`, combiné à un flou d'arrière-plan (glassmorphism) `backdrop-blur-md` pour la Navbar, ou des bordures semi-transparentes `border-border/50`.

### Couleurs d'Accentuation (Accents)
- **Primaire (Primary)** : `hsl(var(--primary))` - Souvent un indigo ou bleu électrique utilisé pour les boutons d'action principale.
- **Succès (Success)** : `text-emerald-400` ou `text-success` - Utilisé pour les PnL positifs, indicateurs de hausse.
- **Danger/Erreur (Destructive/Rose)** : `text-rose-400` ou `text-destructive` - Utilisé pour les PnL négatifs, drawdown, alertes.
- **Muted (Texte secondaire)** : `text-muted-foreground` - Utilisé pour les sous-titres, dates, légendes.

## 2. Typographie

- **Police Principale** : Sans-serif moderne (Inter, Geist, ou la police système par défaut de Tailwind).
- **Titres (h1, h2, h3)** : Poids `font-semibold` ou `font-bold`, couleur `text-foreground`.
- **Chiffres (KPIs)** : Taille imposante (`text-3xl` ou `text-2xl`), poids `font-bold`, couleur de valeur (blanc, vert ou rouge selon l'état).

## 3. Composants Réutilisables

### Metric Cards (`MetricCard.tsx`)
Les MetricCards sont utilisées pour afficher les KPI (Capital, Drawdown, etc.).
- **Style** : Bordure subtile, fond transparent ou très sombre (`bg-background/40`), bordures arrondies (`rounded-xl`).
- **Glow Effect** : Utilisation d'un effet lumineux subtil au survol ou de manière permanente (ex: `shadow-[0_0_15px_rgba(52,211,153,0.1)]`).
- **Icônes** : Les icônes Lucide (lucide-react) sont utilisées avec des teintes pastel ou lumineuses (ex: `text-indigo-400`).

### Panneaux de Contrôle (`ControlPanel.tsx`)
- Divisés en sections claires avec des titres discrets (ex: `text-xs uppercase tracking-wider`).
- Les champs de formulaire (inputs, selects) doivent avoir un fond `bg-background`, une bordure `border-border`, et un outline sur le focus (`focus:ring-1 focus:ring-primary`).

### Graphiques (Recharts)
- Les graphiques (AreaChart, LineChart) doivent s'intégrer parfaitement dans le thème sombre.
- Utilisation de dégradés (Gradients) pour le remplissage des courbes (ex: vert pour gain, rouge pour perte).
- Tooltips sombres avec bordures de la même couleur que `border-border`.

## 4. Règles d'Intégration (Checklist)

Lors de l'ajout de nouvelles fonctionnalités au Dashboard WebApp, assurez-vous de :
1. **Pas de style en ligne** (sauf pour les valeurs dynamiques de gradient Recharts). Utilisez toujours Tailwind.
2. **Ne pas introduire de nouvelles palettes**. Restez sur les variables `--primary`, `--muted`, `emerald-400`, `rose-400`, `indigo-400`.
3. **Glassmorphism** : Si un élément flotte (Modal, Toast, Navbar), il doit utiliser `backdrop-blur-md` et un fond semi-transparent.
4. **Cohérence structurelle** : Les nouveaux panneaux doivent utiliser la même classe `panel p-5 rounded-xl border border-border` que les sections existantes dans `dashboard.tsx`.
5. **Responsive** : Tout nouveau tableau ou grille doit utiliser les classes Tailwind `grid-cols-1 md:grid-cols-2 lg:grid-cols-X` pour s'adapter aux mobiles et tablettes.
