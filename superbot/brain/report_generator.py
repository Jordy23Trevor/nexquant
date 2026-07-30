"""
🧠 NexQuant V3 — Report Generator
Génère chaque jour à 22:30 UTC un rapport journalier complet en Markdown.
- Performance par stratégie, régime, instrument
- Apprentissages du jour (décisions autonomes)
- Ajustements pour la prochaine session
- Sauvegarde en DB + fichier Markdown local
"""
import os
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

log = logging.getLogger("brain.report_generator")


class ReportGenerator:
    """
    Génère des rapports journaliers NexQuant V3.
    Peut être déclenché manuellement ou via timer à 22:30 UTC.
    """

    REPORTS_DIR = "reports"

    def __init__(self, db=None, session_manager=None, strategy_engine=None,
                 performance_learner=None, knowledge_feeder=None):
        self.db = db
        self.session_manager = session_manager
        self.strategy_engine = strategy_engine
        self.performance_learner = performance_learner
        self.knowledge_feeder = knowledge_feeder
        self._timer: Optional[threading.Timer] = None
        self._running = False
        os.makedirs(self.REPORTS_DIR, exist_ok=True)
        log.info("ReportGenerator initialisé")

    def generate_daily_report(self, force: bool = False) -> str:
        """
        Génère le rapport journalier complet.
        Retourne le Markdown du rapport.
        """
        now_utc = datetime.now(timezone.utc)
        date_str = now_utc.strftime('%Y-%m-%d')
        time_str = now_utc.strftime('%H:%M UTC')

        lines = []
        lines.append(f"# Rapport NexQuant V3 — {date_str}")
        lines.append(f"*Généré le {date_str} à {time_str}*")
        lines.append("")

        # ── Objectif du jour ─────────────────────────────────────────────────
        lines.append("## 🎯 Objectif du jour")
        target = 200.0
        achieved = 0.0
        balance_start = 0.0
        balance_end = 0.0

        if self.session_manager:
            try:
                progress = self.session_manager.get_daily_progress()
                achieved = progress.get('achieved_eur', 0)
                target = progress.get('target_eur', 200)
                balance_start = progress.get('balance_start', 0)
                balance_end = balance_start + achieved
                pct = progress.get('achievement_pct', 0)
                lines.append(f"| Métrique | Valeur |")
                lines.append(f"|---|---|")
                lines.append(f"| Target | {target:.2f} € |")
                lines.append(f"| Réalisé | {achieved:.2f} € ({pct:.1f}%) |")
                lines.append(f"| Solde début | {balance_start:.2f} € |")
                lines.append(f"| Solde fin | {balance_end:.2f} € |")
                status = "✅ Objectif atteint !" if pct >= 100 else (f"⚠️ {pct:.0f}% — objectif non atteint" if pct > 0 else "❌ Session déficitaire")
                lines.append(f"| Statut | {status} |")
            except Exception as e:
                lines.append(f"*Données de session non disponibles : {e}*")
        else:
            lines.append("*SessionManager non disponible*")
        lines.append("")

        # ── Stratégies utilisées ──────────────────────────────────────────────
        lines.append("## 📊 Stratégies utilisées")
        if self.strategy_engine:
            try:
                lb = self.strategy_engine.get_strategy_leaderboard()
                if lb:
                    lines.append("| Stratégie | Trades | Win% | Score |")
                    lines.append("|---|---|---|---|")
                    for item in lb[:8]:
                        wr_pct = f"{item.get('wr', 0)*100:.0f}%"
                        lines.append(
                            f"| {item.get('strategy', '—')} | {item.get('trades', 0)} "
                            f"| {wr_pct} | {item.get('score', 0):.1f} |"
                        )
                else:
                    lines.append("*Aucune stratégie utilisée aujourd'hui*")
            except Exception as e:
                lines.append(f"*Données stratégies non disponibles : {e}*")
        else:
            lines.append("*StrategyEngine non disponible*")
        lines.append("")

        # ── Paramètres adaptatifs (PerformanceLearner) ───────────────────────
        lines.append("## 🧠 Apprentissages du jour")
        if self.performance_learner:
            try:
                params = self.performance_learner.get_current_params()
                lines.append(f"- **Score Min actuel** : {params.get('score_min', '—')}")
                lines.append(f"- **Risque par trade** : {params.get('risk_pct', '—')}%")
                lines.append(f"- **Max positions** : {params.get('max_positions', '—')}")
                lines.append(f"- **SL Mult ATR** : {params.get('sl_atr_mult', '—')}×")
                lines.append(f"- **TP Mult ATR** : {params.get('tp_atr_mult', '—')}×")

                blocked = list(getattr(self.performance_learner, '_blocked_symbols', set()))
                if blocked:
                    lines.append(f"- **Symboles bloqués** : {', '.join(blocked)} (3+ pertes consécutives)")

                decisions = getattr(self.performance_learner, '_decisions_log', [])
                if decisions:
                    lines.append("")
                    lines.append("### Décisions autonomes")
                    for dec in decisions[-5:]:
                        lines.append(f"- **{dec.get('type', 'ajustement')}** — {dec.get('reason', '')} *(à {dec.get('time', '')})*")
            except Exception as e:
                lines.append(f"*Données learner non disponibles : {e}*")
        else:
            lines.append("*PerformanceLearner non disponible*")
        lines.append("")

        # ── Knowledge Feeder ──────────────────────────────────────────────────
        lines.append("## 🌐 Intelligence Marché (Knowledge Feeder)")
        if self.knowledge_feeder:
            try:
                sentiment = self.knowledge_feeder.get_current_sentiment()
                lines.append(f"- **Fear & Greed Index** : {sentiment.get('fear_greed_index', '—')}")
                lines.append(f"- **Sentiment global** : {sentiment.get('overall_sentiment', '—')}")
                lines.append(f"- **Items ingérés** : {getattr(self.knowledge_feeder, '_items_today', 0)}")
                lines.append(f"- **Dernière mise à jour** : {getattr(self.knowledge_feeder, '_last_refresh_time', '—')}")
            except Exception as e:
                lines.append(f"*KnowledgeFeeder non disponible : {e}*")
        else:
            lines.append("*KnowledgeFeeder non disponible*")
        lines.append("")

        # ── Ajustements pour demain ───────────────────────────────────────────
        lines.append("## 🔄 Ajustements pour la prochaine session")
        lines.append("")
        if self.performance_learner:
            try:
                params = self.performance_learner.get_current_params()
                lines.append(f"Le bot démarrera la prochaine session avec :")
                lines.append(f"- Score Min : **{params.get('score_min', 6)}**")
                lines.append(f"- Risque/trade : **{params.get('risk_pct', 1.0)}%**")
                lines.append(f"- Max positions : **{params.get('max_positions', 2)}**")
                if achieved >= target:
                    lines.append("- Mode **CONSERVATION** activé (objectif atteint)")
                elif achieved < 0:
                    lines.append("- Mode **DÉFENSIF** activé (session déficitaire)")
                else:
                    lines.append("- Mode **STANDARD** (progression normale)")
            except Exception:
                pass
        lines.append("")
        lines.append("---")
        lines.append(f"*NexQuant V3 — Rapport auto-généré*")

        report_md = "\n".join(lines)

        # Sauvegarder sur disque
        try:
            fname = os.path.join(self.REPORTS_DIR, f"report_{date_str}.md")
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(report_md)
            log.info(f"Rapport journalier sauvegardé : {fname}")
        except Exception as e:
            log.warning(f"Erreur sauvegarde rapport : {e}")

        # Sauvegarder en DB
        if self.db:
            try:
                self.db.insert_knowledge_item({
                    'url': f'report://{date_str}',
                    'source': 'ReportGenerator',
                    'title': f'Rapport journalier {date_str}',
                    'content': report_md[:4000],  # Tronquer si trop long
                    'category': 'daily_report',
                })
            except Exception as e:
                log.debug(f"DB insert report error: {e}")

        return report_md

    def start_daily_scheduler(self):
        """
        Lance le scheduler pour générer le rapport automatiquement
        à 22:30 UTC chaque jour.
        """
        self._running = True
        self._schedule_next()
        log.info("ReportGenerator scheduler démarré (rapport quotidien à 22:30 UTC)")

    def _schedule_next(self):
        """Planifie la prochaine génération de rapport."""
        if not self._running:
            return

        now_utc = datetime.now(timezone.utc)
        target_hour, target_min = 22, 30

        next_report = now_utc.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
        if next_report <= now_utc:
            # Programmer pour demain
            from datetime import timedelta
            next_report = next_report + timedelta(days=1)

        delay_seconds = (next_report - now_utc).total_seconds()
        log.info(f"Prochain rapport dans {delay_seconds/3600:.1f}h (à {next_report.strftime('%Y-%m-%d %H:%M UTC')})")

        self._timer = threading.Timer(delay_seconds, self._run_and_reschedule)
        self._timer.daemon = True
        self._timer.start()

    def _run_and_reschedule(self):
        """Génère le rapport et reprogramme."""
        try:
            log.info("Génération du rapport journalier automatique...")
            report = self.generate_daily_report()
            log.info(f"Rapport généré ({len(report)} caractères)")
        except Exception as e:
            log.error(f"Erreur génération rapport automatique: {e}")
        finally:
            if self._running:
                self._schedule_next()

    def stop(self):
        """Arrête le scheduler."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        log.info("ReportGenerator arrêté")
