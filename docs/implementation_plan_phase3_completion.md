# Plan de Parachèvement — Phase 3

Ce plan vise à clôturer définitivement les sous-tâches restantes de la Phase 3 (Amélioration continue) qui n'avaient pas été intégralement couvertes lors de la passe précédente.

## User Review Required

> [!IMPORTANT]
> Pour la Phase 3.2 (Walk-Forward adaptatif), la vraie recalibration exige une simulation de backtest sur 90 jours. Pour ne pas alourdir le runtime en production, je propose que cette optimisation se fasse de manière **asynchrone** (via un `Thread` dédié) pour ne pas bloquer les cycles de 60s du bot. Êtes-vous d'accord avec cette approche ?

## Proposed Changes

### 1. Phase 3.2 : Walk-Forward Adaptatif
**Objectif** : Ajuster la configuration dynamique de la stratégie aux conditions de marché récentes.
#### [NEW] `superbot/ml/walk_forward.py`
- Création d'un module d'optimisation (Grid Search simplifié).
- Fonctionnalité : Tester des combinaisons de (`score_min`, `RSI_OB`, `ADX_TREND`) sur les historiques de trades pour maximiser le Sharpe Ratio.
#### [MODIFY] `superbot/components/cycle_runner.py`
- Ajouter un déclencheur mensuel (tous les 30 jours) qui lance le `WalkForwardOptimizer` en arrière-plan.
- Logger explicitement les paramètres utilisés lors de la prise de position dans `signal_executor.py`.

---

### 2. Phase 3.3 : Dashboard Grafana Minimal
**Objectif** : Fournir une interface prête à l'emploi pour les métriques Prometheus.
#### [NEW] `grafana_dashboard.json` (à la racine ou dans `resources/`)
- Modèle JSON d'un dashboard Grafana pré-configuré.
- Panneaux : 
  - `bot_balance` et `bot_pnl_session` (Time series)
  - `bot_drawdown_pct` (Gauge rouge/verte)
  - Erreurs d'API (Bar chart)

---

### 3. Phase 3.6 : Test de Chaos (Horloge système)
**Objectif** : S'assurer que le bot gère les problèmes de NTP (désynchronisation horaire).
#### [NEW] `tests/chaos/test_clock_skew.py`
- Utilisation d'un mock du module `time` et `datetime` pour avancer brutalement l'horloge du serveur de 24h.
- Vérification que la réinitialisation quotidienne (`session_date`, PnL journalier) se déroule sans crash et sans ré-ouverture incontrôlée de positions clôturées.

## Verification Plan

1. **Exécution des tests unitaires** : Lancement de `pytest tests/chaos/test_clock_skew.py` pour valider la robustesse temporelle (Exit code 0 attendu).
2. **Inspection visuelle du JSON** : S'assurer que le dashboard Grafana cible bien les bonnes variables Prometheus (`bot_drawdown_pct`, etc.).
