# 🛠️ Plan d'implémentation des recommandations — Bot nexquant

**Date** : 2026-07-11
**Pré-requis** : Avant toute exécution, le bot doit être redémarré après avoir corrigé le bug `calculate_ema is not defined` (cf. Quick Win #0 ci-dessous) — sinon le bot est actuellement en panne silencieuse.

**Périmètre** : 4 phases, ~14 items, durée estimée 5-6 sprints.

---

## 🎯 Phase 0 — Quick wins (à faire aujourd'hui, ~4h)

### QW-0. **Réparer le crash `calculate_ema is not defined`** 🔴
- **Symptôme** : Depuis 2026-07-10 00:18, le bot crashe sur **chaque symbole** avec `name 'calculate_ema' is not defined`.
- **Cause probable** : Un refactor partiel de `superbot/strategy/knowledge_base.py` (où `calculate_ema` est défini) a supprimé ou renommé la fonction, sans mettre à jour les imports dans `indicators/technical_indicators.py` (ligne 108 : `from superbot.strategy.knowledge_base import calculate_ema, ...`).
- **Action** :
  1. `git log --oneline -20 superbot/strategy/knowledge_base.py` pour identifier le commit fautif
  2. Vérifier que `calculate_ema` est bien exporté depuis `knowledge_base.py` (sinon le rajouter / décommenter)
  3. Vider `__pycache__` (Python ne voit pas les changements tant que les `.pyc` ne sont pas invalidés) : `find . -name __pycache__ -type d -exec rm -rf {} +`
  4. Relancer et confirmer un cycle complet sans erreur

### QW-1. **Activer la rotation des logs** (15 min)
- **Symptôme** : `superbot.log` = 135 Mo, grossit indéfiniment.
- **Action** : Remplacer `FileHandler(LOG_FILE, ...)` (main.py:126) par `RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')`. Garde 5 fichiers × 10 Mo max.

### QW-2. **Logger les métriques de risque périodiquement** (30 min)
- **Symptôme** : `get_risk_metrics()` n'est jamais appelée dans la boucle principale. L'opérateur est aveugle sur drawdown, win rate, profit factor.
- **Action** : Dans `_main_loop`, après l'envoi d'équité télémétrie (ligne ~830), ajouter un appel à `self.risk_manager.get_risk_metrics(equity)` et logger en INFO les champs clés : `drawdown_pct`, `win_rate`, `profit_factor`, `current_risk_pct`.

### QW-3. **Stopper le spam BTC** (1h)
- **Symptôme** : 11 ordres SELL BTC identiques en 10 min, taille qui croît de quelques satoshis.
- **Cause probable** : Position déjà ouverte, le bot redéduit `position_size` à partir d'un solde qui n'a pas été resync.
- **Action** : Dans `_process_symbol`, **AVANT** de calculer la taille :
  ```python
  if symbol in self.positions:
      log.debug(f"{symbol} : position déjà ouverte, skip sizing")
      return
  ```
  Vérifier aussi qu'il n'y a pas d'accumulation dans `_update_position_tracking` (le size ne devrait jamais changer tant que la position est ouverte).

### QW-4. **Persister `failed_execution_cooldowns`** (1h)
- **Symptôme** : Au restart du bot, les cooldowns sont perdus. Un trade qui a échoué pour cause de marge sera réessayé immédiatement.
- **Action** : Sérialiser `self.failed_execution_cooldowns` dans un fichier JSON à chaque modification, recharger au démarrage. Idem pour `self.blocked_symbols` et `self.session_pnl_by_symbol`.

---

## 🔴 Phase 1 — Critique (avant mise en prod live, ~2 sprints)

### 1.1. **Mode DRY_RUN forcé** (1 sprint)
- **Objectif** : Empêcher un démarrage en live sans double confirmation explicite.
- **Fichiers** : `superbot/main.py`, `superbot/config.py`
- **Implémentation** :
  1. Ajouter `ALLOW_LIVE_TRADING` dans `config.py` (défaut : `False`)
  2. Dans `_initialize_components` après création du broker, si `broker.get_asset_type() != "paper"` et `not ALLOW_LIVE_TRADING` :
     - Logger une bannière 🚨 avec demande de confirmation
     - `sys.exit(1)` sauf si variable d'env `I_UNDERSTAND_LIVE_RISK=1`
  3. Ajouter un test unitaire : démarrer avec `BROKER_TYPE=binance` et `ALLOW_LIVE_TRADING=False` doit faire échouer proprement le bot
- **Critère d'acceptation** : Aucune commande shell ne peut démarrer le bot en live sans triple opt-in.

### 1.2. **Durcir le multi-threading** (1 sprint)
- **Objectif** : Éliminer les race conditions sur `self.positions` et les caches de cycle.
- **Fichiers** : `superbot/main.py`
- **Implémentation** :
  1. Ajouter `self._lock = threading.RLock()` dans `SuperBot.__init__`
  2. Wrapper toutes les mutations de `self.positions`, `self.market_data`, `self.active_orders` dans `with self._lock:`
  3. Réduire `max_workers` de 16 à 4 (la plupart des brokers limitent à 5-10 req/s)
  4. Ajouter un `threading.Event` pour signaler aux workers qu'un cycle de sync est en cours
- **Test** : `pytest tests/test_concurrency.py` qui lance 50 cycles en parallèle et vérifie l'invariant "position_count = broker_count"
- **Critère d'acceptation** : Aucune exception `RuntimeError: dictionary changed size during iteration` dans 24h de paper trading.

### 1.3. **Modéliser les coûts de transaction** (1 sprint)
- **Objectif** : Le R:R annoncé doit refléter la réalité économique.
- **Fichiers** : `superbot/risk/risk_manager.py`, `superbot/strategy/strategy.py`, `superbot/config.py`
- **Implémentation** :
  1. Ajouter dans `config.py` :
     ```python
     COMMISSION_PCT = 0.1   # % par côté (Binance: 0.075, Alpaca: 0, MT5 variable)
     SLIPPAGE_PCT = 0.05    # % conservateur par trade
     ```
  2. Dans `calculate_potential_rr()` (strategy.py:1100) :
     - Coût total = `entry_price * (COMMISSION_PCT*2 + SLIPPAGE_PCT) / 100`
     - `effective_rr = (potential_gain - cost) / (potential_risk + cost)`
  3. Le seuil `rr_ratio >= 2.0` doit être testé sur `effective_rr` (pas le brut)
  4. Idem dans `calculate_position_size` : le risque doit inclure le coût (sinon vous sous-évaluez le risque réel)
- **Critère d'acceptation** : Backtest paper sur 1 mois montre que le R:R effectif est ≥ 1.5:1 pour tous les trades.

### 1.4. **Valider le sizing multi-devises** (3 jours)
- **Objectif** : Le PnL latent doit être correct pour CHF, CAD, AUD en plus de JPY/USD.
- **Fichiers** : `superbot/main.py`, `superbot/risk/risk_manager.py`
- **Implémentation** :
  1. Étendre `_convert_pnl_to_account_currency` (main.py:1618) avec un mapping complet des quote currencies → vers USD
  2. Ajouter une validation au démarrage : pour chaque instrument, vérifier que sa quote currency est supportée
  3. Si non supportée, logger un warning et **désactiver le symbole** (ne pas le scanner)
- **Critère d'acceptation** : Le PnL latent affiché dans la télémétrie est à ±0.5% du PnL réel broker pour toute devise.

---

## 🟠 Phase 2 — Important (1-2 sprints)

### 2.1. **Découper `main.py`** (2 sprints)
- **Objectif** : Casser le monolithe de 2 100 lignes en unités testables.
- **Cible** : aucun module > 500 lignes.
- **Structure cible** :
  ```
  superbot/
    main.py                 # entrypoint uniquement (< 100 lignes)
    orchestrator.py         # SuperBot class, cycle principal
    components/
      broker_factory.py     # déjà dans broker/base.py, à nettoyer
      cycle_runner.py       # _main_loop
      position_syncer.py    # _sync_positions_with_broker
      signal_executor.py    # _execute_signal_trade
      forex_filters.py      # session, spread, corrélation, pivots
      crypto_filters.py     # BTC dominance, blacklist, volume
      drift_detector.py     # _detect_model_drift
      adaptive_params.py    # _update_adaptive_parameters
  ```
- **Stratégie de migration** (pour ne pas tout casser d'un coup) :
  1. Créer `components/forex_filters.py` et y déplacer les fonctions `is_london_session()`, `check_spread()`, `check_currency_correlation()`, `check_pivot_obstacle()` — pas de changement de signature
  2. Répéter pour chaque composant, commit par commit
  3. À la fin, `main.py` ne contient plus que `if __name__ == '__main__': main()`
- **Critère d'acceptation** : `python -m superbot` démarre en < 5 secondes (pas de double init).

### 2.2. **Tests unitaires** (2 sprints, en parallèle)
- **Objectif** : Couvrir les chemins critiques pour éviter les régressions comme `calculate_ema`.
- **Fichiers** : créer `tests/` (racine projet) + `pytest` dans requirements
- **Couverture cible** :
  - `tests/risk/test_risk_manager.py` : balance=0, balance<0, ATR=0, JPY→USD, edge cases de Kelly
  - `tests/strategy/test_strategy.py` : scoring déterministe (input fixe → output fixe), régime, R:R
  - `tests/indicators/test_indicators.py` : DataFrame vide, colonnes manquantes, NaN, inf
  - `tests/broker/test_brokers.py` : mock des 4 brokers, vérifier les conversions de devise
  - `tests/integration/test_cycle.py` : un cycle complet en paper, vérifie qu'aucun trade fantôme n'est créé
- **Critère d'acceptation** : `pytest` passe en CI, coverage > 60% sur `risk/` et `strategy/`.

### 2.3. **Backtest out-of-sample** (1 sprint)
- **Objectif** : Valider statistiquement les paramètres avant chaque changement.
- **Fichiers** : `superbot/backtest/engine.py` (existe déjà, à intégrer)
- **Implémentation** :
  1. Script `scripts/run_backtest.py` qui prend en argument une période (ex: "2025-01-01..2025-12-31") et un jeu de paramètres
  2. Calculer les métriques : Sharpe, Sortino, max drawdown, win rate, profit factor, expectancy
  3. Générer un rapport HTML ou PDF avec equity curve
  4. Ajouter en CI : `python scripts/run_backtest.py --period 2024-01-01..2024-12-31` doit afficher un Sharpe > 0.5 pour qu'un merge soit accepté
- **Critère d'acceptation** : Tous les paramètres (`score_min`, `RSI_OB`, `ADX_TREND`, etc.) ont été backtestés sur 1 an out-of-sample.

### 2.4. **Persistance complète des états** (3 jours, partie de 1.2)
- **Objectif** : Le bot peut redémarrer sans perdre son état de session.
- **Fichiers** : `superbot/state.py` (nouveau module)
- **Implémentation** :
  - Sauvegarder toutes les heures dans `logs/state.json` : `failed_execution_cooldowns`, `blocked_symbols`, `session_pnl_by_symbol`, `consecutive_losses`, `last_trade_close_time`, `adaptation_counter`
  - Charger au démarrage, avec un TTL de 24h (au-delà, on reset)

---

## 🟡 Phase 3 — Amélioration continue (3-4 sprints)

### 3.1. **Scoring probabiliste** (2 sprints)
- Remplacer le score 0-10 par une régression logistique entraînée sur les trades historiques
- Features : valeurs continues des indicateurs (RSI, MACD hist, ADX, BB position, etc.) au moment de l'entrée
- Target : 1 si le trade a été gagnant, 0 sinon
- Réévaluation mensuelle
- Output : `should_long`/`should_short` basés sur `predict_proba() > 0.6` au lieu d'un seuil magique de 6

### 3.2. **Walk-forward adaptatif** (1 sprint)
- Tous les 30 jours, re-calibrer `score_min`, `RSI_OB`, `ADX_TREND` sur les 90 derniers jours
- Garder en mémoire la combinaison optimale
- Logger les paramètres utilisés à chaque trade

### 3.3. **Monitoring Prometheus** (3 jours)
- Exposer `/metrics` sur un port dédié (séparé du dashboard)
- Métriques :
  - `bot_balance` (gauge)
  - `bot_pnl_session` (gauge)
  - `bot_drawdown_pct` (gauge)
  - `bot_open_positions` (gauge)
  - `bot_cycle_duration_seconds` (histogram)
  - `bot_api_errors_total{broker,error_code}` (counter)
  - `bot_trades_executed_total{symbol,side}` (counter)
- Ajouter un dashboard Grafana minimal

### 3.4. **Dédoublonnage TradingStrategy / TechnicalIndicators** (1 jour)
- Aujourd'hui : la stratégie instancie son propre `TechnicalIndicators` (strategy.py:43) + main en instancie un autre → double calcul
- Solution : passer l'instance `self.technical_indicators` de `main.py` à `TradingStrategy` au lieu d'en créer une nouvelle

### 3.5. **Vol regime detection** (1 sprint)
- Étendre le HMM à 4 états : bull-trend, bear-trend, low-vol-range, high-vol-range
- Adapter le sizing : taille ÷ 2 en high-vol, taille × 1.5 en low-vol (si win rate stable)

### 3.6. **Tests de charge + chaos** (1 sprint)
- `tests/chaos/test_broker_failures.py` : tuer la connexion broker au milieu d'un trade
- `tests/chaos/test_clock_skew.py` : avancer/retarder l'horloge système
- `tests/chaos/test_data_corruption.py` : renvoyer des NaN, des prix négatifs, des timestamps farfelus
- Critère : le bot ne perd **jamais** d'argent dans ces scénarios

---

## 📅 Roadmap visuelle

```
Sprint 0 (cette semaine)     ▓░░░░  QW-0..4 (quick wins)
Sprint 1                    ▓▓░░░  1.1 (DRY_RUN) + 1.2 (multi-threading)
Sprint 2                    ▓▓▓░░  1.3 (coûts tx) + 1.4 (multi-devises) + 2.1 début
Sprint 3                    ▓▓▓▓░  2.1 fin (découpage main) + 2.2 (tests)
Sprint 4                    ▓▓▓▓▓  2.3 (backtest) + 2.4 (persistance) + 3.4
Sprint 5+                   ▓▓▓▓▓▓ 3.1, 3.2, 3.3, 3.5, 3.6
```

## 🎯 Ordre d'exécution recommandé

1. **QW-0** (aujourd'hui) : sans ça, le bot ne tourne pas
2. **QW-1, QW-2, QW-3** (demain) : 2h cumulées
3. **1.1** (sprint 1) : DRY_RUN — c'est le **vrai bloqueur** pour la mise en prod live
4. **1.2** (sprint 1) : multi-threading — c'est le **deuxième bloqueur**
5. **1.3, 1.4** (sprint 2) : réalisme économique
6. **2.x** (sprints 3-4) : qualité & validation
7. **3.x** (sprints 5+) : amélioration continue

## 💡 Recommandation finale

**Ne pas toucher au scoring (3.1, 3.2) tant que les phases 0-2 ne sont pas terminées.** Améliorer un scoring sur un bot qui a des bugs de threading et des PnL incorrects, c'est optimiser dans le vide. D'abord la fondation, puis la finesse.
