"""
superbot/brain/session_target_tracker.py

Moteur de suivi d'objectif de session journalière.
Suit en direct l'évolution de la balance et de l'équité du compte vers la cible
définie par l'utilisateur (35.00€ à 40.00€ sur la session en cours).
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import os

log = logging.getLogger("session_target_tracker")


class SessionTargetTracker:
    """
    Traqueur d'objectif de capital pour la session journalière.
    Cible : 35.00€ à 40.00€
    """

    def __init__(
        self,
        start_balance: float = 0.0,
        target_min: float = 35.0,
        target_max: float = 40.0,
    ):
        self.target_min = float(os.getenv("SESSION_TARGET_EQUITY_MIN", target_min))
        self.target_max = float(os.getenv("SESSION_TARGET_EQUITY_MAX", target_max))
        self.start_balance = float(start_balance)
        self.current_balance = float(start_balance)
        self.current_equity = float(start_balance)
        self.peak_equity = float(start_balance)
        self.goal_reached: bool = False
        self.goal_reached_at: Optional[datetime] = None
        self._last_logged_pct: float = -1.0

    def update(self, balance: float, equity: Optional[float] = None) -> Dict[str, Any]:
        """
        Met à jour l'état du traqueur avec les valeurs du compte en temps réel.
        """
        if balance <= 0:
            return self.get_status()

        if self.start_balance <= 0:
            self.start_balance = balance

        self.current_balance = balance
        self.current_equity = equity if equity is not None and equity > 0 else balance
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

        # Vérifier si l'objectif minimal (35€) est franchi
        if self.current_equity >= self.target_min and not self.goal_reached:
            self.goal_reached = True
            self.goal_reached_at = datetime.now(timezone.utc)
            log.info(
                f"🎉🎉 [OBJECTIF SESSION ATTEINT] L'équité du compte ({self.current_equity:.2f}€) "
                f"a atteint la cible journalière de {self.target_min:.2f}€ - {self.target_max:.2f}€ ! "
                f"Sécurisation des profits en cours."
            )

        return self.get_status()

    def get_progress_pct(self) -> float:
        """Calcule le pourcentage de progression vers la cible minimale (35€)."""
        if self.start_balance >= self.target_min:
            return 100.0 if self.current_equity >= self.target_min else 0.0

        needed = self.target_min - self.start_balance
        if needed <= 0:
            return 100.0

        gained = self.current_equity - self.start_balance
        progress = (gained / needed) * 100.0
        return max(0.0, round(progress, 1))

    def get_remaining_amount(self) -> float:
        """Montant restant à gagner pour atteindre la cible minimale."""
        rem = self.target_min - self.current_equity
        return max(0.0, round(rem, 2))

    def log_progress(self, force: bool = False):
        """Affiche un log synthétique de la progression."""
        prog = self.get_progress_pct()
        if force or abs(prog - self._last_logged_pct) >= 5.0:
            self._last_logged_pct = prog
            status_symbol = "🏆" if self.goal_reached else "🎯"
            rem = self.get_remaining_amount()
            log.info(
                f"{status_symbol} [Cible {self.target_min:.1f}€-{self.target_max:.1f}€] "
                f"Solde: {self.current_balance:.2f}€ | Équité: {self.current_equity:.2f}€ | "
                f"Progression: {prog:.1f}% | Reste: {rem:+.2f}€"
            )

    def get_status(self) -> Dict[str, Any]:
        """Retourne un dictionnaire récapitulatif pour les dashboards et rapports."""
        return {
            "start_balance": round(self.start_balance, 2),
            "current_balance": round(self.current_balance, 2),
            "current_equity": round(self.current_equity, 2),
            "peak_equity": round(self.peak_equity, 2),
            "target_min": round(self.target_min, 2),
            "target_max": round(self.target_max, 2),
            "progress_pct": self.get_progress_pct(),
            "remaining_amount": self.get_remaining_amount(),
            "goal_reached": self.goal_reached,
            "goal_reached_at": self.goal_reached_at.isoformat() if self.goal_reached_at else None,
        }

