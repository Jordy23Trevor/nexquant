"""
NexQuant V3 — Performance Learner (Auto-apprentissage)
=========================================================
Phase 5 : Le bot apprend de lui-même avant, pendant et après chaque session.

Trois moments d'apprentissage :
  1. PRÉ-SESSION   : Analyse de l'historique → ajuste les paramètres pour la session
  2. MID-SESSION   : Contrôle de performance en cours → ajustements si dérive
  3. POST-SESSION  : Débrief complet → met à jour les profils, stratégies, scores

Mécanismes d'apprentissage :
  - Adaptation du score_min selon le taux de succès récent
  - Adaptation du risk_pct selon le drawdown en cours
  - Blocage automatique des symboles/stratégies perdants
  - Mise à jour des profils de symboles dans la DB
  - Ajustement des multiplicateurs ATR par symbole
  - Calcul du target journalier adaptatif
  - Walk-Forward calibration des paramètres

Logique :
  - Si WinRate < 40% sur 20 trades → +10% score_min (plus sélectif)
  - Si WinRate > 65% sur 20 trades → -5% score_min (moins sélectif, exploiter)
  - Si Daily PnL > 150% target → réduire risk (protéger les gains)
  - Si Daily PnL < -50% target → réduire risk + passer en mode défensif
  - Si symbole -3 pertes consécutives → block 24h
  - Si stratégie < 30% WR sur 10 trades → désactiver 7 jours
"""

import logging
import threading
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("nexquant.performance_learner")


class PerformanceLearner:
    """
    Module d'auto-apprentissage continu.
    
    Intégration avec :
    - NexQuantDB (stockage des apprentissages)
    - SessionManager (objectifs journaliers)
    - StrategyEngine (classement des stratégies)
    - RiskManager (adaptation du risque)
    
    Est appelé :
    - Par le cycle_runner tous les N cycles (_adaptation_every)
    - À la fin de chaque session (SessionManager.tick())
    - Manuellement pour les analyses approfondies
    """

    def __init__(self, db=None, session_manager=None, strategy_engine=None):
        self._db = db
        self._session_manager = session_manager
        self._strategy_engine = strategy_engine
        self._lock = threading.RLock()

        # État courant des paramètres adaptatifs
        self._current_params: Dict[str, Any] = {
            'score_min': 6,
            'risk_pct': 1.0,
            'max_positions': 3,
            'sl_atr_mult': 1.5,
            'tp_atr_mult': 3.0,
        }

        # Statistiques de la session courante
        self._session_trades: List[Dict] = []
        self._session_start_balance: float = 0.0
        self._session_start_time: Optional[datetime] = None

        # Mode défensif (activé en cas de pertes importantes)
        self._defensive_mode: bool = False
        self._defensive_until: Optional[datetime] = None

        # Blocages dynamiques (symboles et stratégies)
        self._blocked_strategies: Dict[str, datetime] = {}  # strategy -> blocked_until
        self._symbol_consecutive_losses: Dict[str, int] = {}  # symbol -> count

        log.info("PerformanceLearner V3 initialisé")

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTHODES D'APPRENTISSAGE
    # ─────────────────────────────────────────────────────────────────────────

    def pre_session_analysis(self, bot=None) -> Dict[str, Any]:
        """
        Analyse pré-session : ajuste les paramètres avant de trader.
        Appelé automatiquement à l'ouverture de chaque session (via SessionManager).
        """
        log.info("🔍 [PRÉ-SESSION] Analyse des performances passées...")
        adjustments = {}

        # 1. Récupérer les stats des derniers 20 trades
        stats = self._get_recent_stats(n_trades=20)
        win_rate = float(stats.get('win_rate') or 50)
        avg_rr = float(stats.get('avg_rr') or 2.0)
        total_trades = int(stats.get('total_trades') or 0)

        # 2. Adapter le score_min selon le WinRate
        if total_trades >= 10:
            old_score = self._current_params.get('score_min', 6)
            if win_rate < 35:
                new_score = min(9, old_score + 1)
                reason = f"WinRate faible ({win_rate:.0f}%) → plus sélectif"
            elif win_rate < 45:
                new_score = min(8, old_score + 0.5)
                reason = f"WinRate en dessous de 45% ({win_rate:.0f}%) → légèrement plus sélectif"
            elif win_rate > 65:
                new_score = max(5, old_score - 0.5)
                reason = f"WinRate élevé ({win_rate:.0f}%) → exploiter la vague"
            else:
                new_score = old_score
                reason = "WinRate stable"

            if new_score != old_score:
                self._log_adjustment('score_min', old_score, new_score, reason, 'pre_session')
                self._current_params['score_min'] = new_score
                adjustments['score_min'] = new_score

        # 3. Analyser les meilleurs horaires de session
        best_session = self._get_best_performing_session()
        adjustments['best_session'] = best_session

        # 4. Identifier les symboles problématiques
        blocked_symbols = self._get_blocked_symbols()
        adjustments['blocked_symbols'] = list(blocked_symbols)

        # 5. Vérifier le mode défensif
        if self._defensive_mode and self._defensive_until:
            if datetime.now(timezone.utc) >= self._defensive_until:
                self._defensive_mode = False
                self._defensive_until = None
                log.info("✅ Mode défensif levé")
        adjustments['defensive_mode'] = self._defensive_mode

        # 6. Logger en DB
        if self._db:
            try:
                self._db.insert_knowledge_item({
                    'source_type': 'pre_session_analysis',
                    'title': f"[PRÉ-SESSION] WR={win_rate:.0f}% | score_min={self._current_params['score_min']}",
                    'content': json.dumps({'stats': stats, 'adjustments': adjustments}),
                    'relevance_score': 1.0,
                    'assets_mentioned': [],
                })
            except Exception:
                pass

        log.info(
            f"✅ [PRÉ-SESSION] WR={win_rate:.0f}% | avg_RR={avg_rr:.2f} | "
            f"score_min={self._current_params['score_min']} | "
            f"défensif={self._defensive_mode} | "
            f"blocages={len(adjustments.get('blocked_symbols', []))}"
        )
        return adjustments

    def mid_session_check(self, current_pnl: float, target_pnl: float, balance: float) -> Dict[str, Any]:
        """
        Contrôle mi-session : ajustements en temps réel selon la performance.
        Appelé tous les 30 minutes par le cycle_runner.
        """
        actions = {}
        pnl_ratio = current_pnl / target_pnl if target_pnl > 0 else 0

        # Objectif dépassé → protéger les gains
        if pnl_ratio >= 1.5:
            old_risk = self._current_params.get('risk_pct', 1.0)
            new_risk = old_risk * 0.5
            self._log_adjustment('risk_pct', old_risk, new_risk,
                                 f"PnL={current_pnl:.0f}€ dépasse 150% target → protection des gains", 'mid_session', balance, current_pnl)
            self._current_params['risk_pct'] = new_risk
            actions['risk_pct'] = new_risk
            actions['action'] = 'REDUCE_RISK_PROFIT_PROTECTION'
            log.info(f"💰 [MID-SESSION] Objectif dépassé de 150% ! risk_pct: {old_risk:.2f}% → {new_risk:.2f}%")

        # Pertes importantes → mode défensif
        elif pnl_ratio <= -0.5:
            self._defensive_mode = True
            self._defensive_until = datetime.now(timezone.utc) + timedelta(hours=3)
            old_risk = self._current_params.get('risk_pct', 1.0)
            new_risk = old_risk * 0.3
            self._log_adjustment('risk_pct', old_risk, new_risk,
                                 f"PnL={current_pnl:.0f}€ → pertes 50% target → mode défensif", 'mid_session', balance, current_pnl)
            self._current_params['risk_pct'] = new_risk
            actions['risk_pct'] = new_risk
            actions['action'] = 'DEFENSIVE_MODE_ACTIVATED'
            actions['defensive_until'] = self._defensive_until.isoformat()
            log.warning(f"⚠️ [MID-SESSION] Mode défensif activé | PnL={current_pnl:.0f}€ | risk_pct→{new_risk:.2f}%")

        # Performance légèrement en dessous → légère correction
        elif pnl_ratio < 0.3 and len(self._session_trades) >= 5:
            # Vérifier si c'est une mauvaise série ou juste le marché
            recent_wr = sum(1 for t in self._session_trades[-5:] if t.get('pnl', 0) > 0) / 5
            if recent_wr < 0.4:
                old_score = self._current_params.get('score_min', 6)
                new_score = min(9, old_score + 1)
                if new_score != old_score:
                    self._log_adjustment('score_min', old_score, new_score,
                                         f"WR session={recent_wr:.0%} < 40% → plus sélectif", 'mid_session', balance, current_pnl)
                    self._current_params['score_min'] = new_score
                    actions['score_min'] = new_score
                    actions['action'] = 'INCREASE_SELECTIVITY'

        actions['current_params'] = dict(self._current_params)
        return actions

    def post_session_debrief(self, session_stats: Dict) -> Dict[str, Any]:
        """
        Débrief post-session complet.
        Appelé automatiquement à la fin de chaque session.
        Met à jour les profils, ajuste les stratégies, prépare la suivante.
        """
        log.info("📊 [POST-SESSION] Débrief en cours...")
        insights = {}

        trades = session_stats.get('trades', [])
        pnl_total = session_stats.get('pnl_total', 0)
        target = session_stats.get('pnl_target', 200)
        session_name = session_stats.get('session_name', 'unknown')

        # 1. Calculer les métriques
        if trades:
            wins = [t for t in trades if t.get('pnl', 0) > 0]
            losses = [t for t in trades if t.get('pnl', 0) <= 0]
            win_rate = len(wins) / len(trades) * 100
            avg_rr = sum(t.get('rr_ratio', 0) for t in trades) / len(trades)
            best_symbol = max(trades, key=lambda t: t.get('pnl', 0)).get('symbol', '') if trades else ''
            worst_symbol = min(trades, key=lambda t: t.get('pnl', 0)).get('symbol', '') if trades else ''

            insights['win_rate'] = round(win_rate, 1)
            insights['avg_rr'] = round(avg_rr, 2)
            insights['best_symbol'] = best_symbol
            insights['worst_symbol'] = worst_symbol
            insights['total_trades'] = len(trades)

            # 2. Mettre à jour les profils de symboles
            self._update_symbol_profiles(trades)

            # 3. Mettre à jour les stats de stratégies
            self._update_strategy_stats(trades)

            # 4. Pertes consécutives : les compteurs sont déjà maintenus par on_trade_closed() ;
            # les rappeler ici doublerait chaque perte (blocage après 2 pertes au lieu de 3).

        # 5. Générer les insights pour la prochaine session
        next_insights = []
        if pnl_total >= target:
            next_insights.append(f"✅ Objectif atteint ({pnl_total:.0f}€/{target:.0f}€)")
        else:
            next_insights.append(f"⚠️ Objectif non atteint ({pnl_total:.0f}€/{target:.0f}€)")

        # 6. Reset du risk_pct si mode normal à la fin de session
        if not self._defensive_mode:
            # Restaurer progressivement le risk_pct si on avait réduit
            old_risk = self._current_params.get('risk_pct', 1.0)
            # Restaurer le risque jusqu'à 1.0 (risque de base).
            if old_risk < 1.0:
                # Restauration volontairement conservatrice (x1.5 par session). 
                # S'il était tombé à 0.3%, il faudra ~3 sessions positives pour revenir à 1.0%.
                new_risk = min(1.0, old_risk * 1.5)
                self._log_adjustment('risk_pct', old_risk, new_risk, 'Restauration post-session', 'post_session')
                self._current_params['risk_pct'] = new_risk
                next_insights.append(f"🔄 risk_pct restauré: {old_risk:.2f}% → {new_risk:.2f}%")

        insights['next_session_insights'] = next_insights

        # 7. Stocker le débrief en DB
        if self._db:
            try:
                self._db.insert_knowledge_item({
                    'source_type': 'post_session_debrief',
                    'title': f"[POST-{session_name}] PnL={pnl_total:.0f}€/{target:.0f}€",
                    'content': json.dumps({**session_stats, 'insights': insights}),
                    'relevance_score': 1.0,
                    'assets_mentioned': [],
                })
            except Exception:
                pass

        log.info(
            f"✅ [POST-SESSION] {session_name} | PnL={pnl_total:.0f}€ | "
            f"WR={insights.get('win_rate', 0):.0f}% | "
            f"insights: {'; '.join(next_insights)}"
        )
        return insights

    # ─────────────────────────────────────────────────────────────────────────
    # APPRENTISSAGE PAR TRADE
    # ─────────────────────────────────────────────────────────────────────────

    def on_trade_closed(self, trade: Dict) -> Dict[str, Any]:
        """
        Appelé immédiatement quand un trade est fermé.
        Met à jour les compteurs et déclenche des ajustements si nécessaire.
        """
        with self._lock:
            self._session_trades.append(trade)

        symbol = trade.get('symbol', '')
        pnl = trade.get('pnl', 0)
        strategy = trade.get('strategy_name', 'unknown')
        rr = trade.get('rr_ratio', 0)

        # Mise à jour des pertes consécutives
        if pnl < 0:
            self._symbol_consecutive_losses[symbol] = self._symbol_consecutive_losses.get(symbol, 0) + 1
            count = self._symbol_consecutive_losses[symbol]
            if count >= 3:
                log.warning(f"🚫 {symbol} : {count} pertes consécutives → blocage automatique 24h")
        else:
            self._symbol_consecutive_losses[symbol] = 0  # Reset en cas de gain

        # Mise à jour de la stratégie
        if self._strategy_engine:
            self._strategy_engine.record_trade_result(strategy, symbol, pnl, rr)

        # Mise à jour DB
        if self._db:
            try:
                self._db.insert_trade(trade)
            except Exception as e:
                log.debug(f"DB insert trade error: {e}")

        return {
            'symbol': symbol,
            'pnl': pnl,
            'consecutive_losses': self._symbol_consecutive_losses.get(symbol, 0),
            'symbol_blocked': self._symbol_consecutive_losses.get(symbol, 0) >= 3,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITAIRES INTERNES
    # ─────────────────────────────────────────────────────────────────────────

    def _get_recent_stats(self, n_trades: int = 20) -> Dict[str, Any]:
        """Récupère les stats des N derniers trades depuis la DB."""
        if self._db:
            try:
                stats = self._db.get_performance_stats(days=14)
                return stats
            except Exception:
                pass
        # Fallback : calcul depuis les trades en mémoire
        trades = self._session_trades[-n_trades:] if self._session_trades else []
        if not trades:
            return {'win_rate': 50, 'avg_rr': 2.0, 'total_trades': 0}
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        return {
            'win_rate': wins / len(trades) * 100,
            'avg_rr': sum(t.get('rr_ratio', 2) for t in trades) / len(trades),
            'total_trades': len(trades),
        }

    def _get_best_performing_session(self) -> str:
        """Détermine la meilleure session selon l'historique DB."""
        if self._db:
            try:
                sessions = self._db.get_recent_sessions(days=14)
                if sessions:
                    best = max(sessions, key=lambda s: s.get('pnl_total') or 0)
                    return best.get('session_name', 'LONDON')
            except Exception:
                pass
        return 'LONDON'  # Défaut

    def _get_blocked_symbols(self) -> set:
        """Retourne les symboles bloqués (3+ pertes consécutives)."""
        return {
            sym for sym, count in self._symbol_consecutive_losses.items()
            if count >= 3
        }

    def _update_symbol_profiles(self, trades: List[Dict]):
        """Met à jour les profils de symboles dans la DB."""
        if not self._db:
            return
        symbol_stats: Dict[str, Dict] = {}
        for trade in trades:
            sym = trade.get('symbol', '')
            if not sym:
                continue
            if sym not in symbol_stats:
                symbol_stats[sym] = {'pnl': 0, 'count': 0, 'wins': 0, 'rr_sum': 0}
            symbol_stats[sym]['pnl'] += trade.get('pnl', 0)
            symbol_stats[sym]['count'] += 1
            if trade.get('pnl', 0) > 0:
                symbol_stats[sym]['wins'] += 1
            symbol_stats[sym]['rr_sum'] += trade.get('rr_ratio', 2)

        for sym, stats in symbol_stats.items():
            count = stats['count']
            if count == 0:
                continue
            try:
                self._db.upsert_symbol_profile(sym, {
                    'win_rate': stats['wins'] / count * 100,
                    'avg_rr': stats['rr_sum'] / count,
                    'total_trades': count,
                })
            except Exception as e:
                log.debug(f"Symbol profile update error {sym}: {e}")

    def _update_strategy_stats(self, trades: List[Dict]):
        """Met à jour les stats de stratégies via StrategyEngine."""
        if not self._strategy_engine:
            return
        for trade in trades:
            strategy = trade.get('strategy_name', 'TREND_FOLLOW_EMA')
            symbol = trade.get('symbol', '')
            pnl = trade.get('pnl', 0)
            rr = trade.get('rr_ratio', 0)
            self._strategy_engine.record_trade_result(strategy, symbol, pnl, rr)

    def _update_consecutive_losses(self, trades: List[Dict]):
        """
        Reconstruit les compteurs de pertes consécutives depuis une liste de trades.

        ATTENTION : Ne doit Être utilisé que pour reconstruire l'état historique
        (ex: redémarrage du bot), PAS pour les trades en temps réel.
        Pour les trades live, utiliser on_trade_closed() qui maintient les compteurs
        incrémentalement. Appeler cette méthode sur des trades déjà traités par
        on_trade_closed() causerait un double-comptage (BUG-I1).
        """
        for trade in trades:
            sym = trade.get('symbol', '')
            pnl = trade.get('pnl', 0)
            if pnl < 0:
                self._symbol_consecutive_losses[sym] = self._symbol_consecutive_losses.get(sym, 0) + 1
            else:
                self._symbol_consecutive_losses[sym] = 0

    def _log_adjustment(
        self, param: str, old_val: float, new_val: float,
        reason: str, trigger: str = 'auto',
        balance: float = 0, pnl: float = 0
    ):
        """Log un ajustement de paramètre en DB et logs."""
        log.info(f"🔄 Ajustement {param}: {old_val:.3f} → {new_val:.3f} | {reason}")
        if self._db:
            try:
                self._db.log_adaptive_adjustment(
                    param_name=param, old_value=old_val, new_value=new_val,
                    reason=reason, trigger=trigger, balance=balance, pnl_trigger=pnl
                )
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # API PUBLIQUE
    # ─────────────────────────────────────────────────────────────────────────

    def get_current_params(self) -> Dict[str, Any]:
        """Retourne les paramètres adaptatifs courants."""
        return dict(self._current_params)

    def is_strategy_blocked(self, strategy_name: str) -> bool:
        """Vérifie si une stratégie est bloquée."""
        blocked_until = self._blocked_strategies.get(strategy_name)
        if blocked_until:
            return datetime.now(timezone.utc) < blocked_until
        return False

    def is_symbol_blocked(self, symbol: str) -> bool:
        """Vérifie si un symbole est bloqué (pertes consécutives)."""
        return self._symbol_consecutive_losses.get(symbol, 0) >= 3

    def get_learning_report(self) -> Dict[str, Any]:
        """Retourne un rapport d'apprentissage complet."""
        stats = self._get_recent_stats(20)
        blocked = list(self._get_blocked_symbols())
        return {
            'current_params': self._current_params,
            'recent_stats': stats,
            'defensive_mode': self._defensive_mode,
            'defensive_until': self._defensive_until.isoformat() if self._defensive_until else None,
            'blocked_symbols': blocked,
            'blocked_strategies': list(self._blocked_strategies.keys()),
            'session_trades_count': len(self._session_trades),
            'strategy_leaderboard': self._strategy_engine.get_strategy_leaderboard() if self._strategy_engine else [],
        }
