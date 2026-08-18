"""Calibration empirique du win rate, contre les trades réalisés.

Le score de la stratégie ne prédit pas sa probabilité de gain : l'ancienne
formule linéaire (`0.35 + score/10 * 0.40`) annonçait 59-75% là où le win rate
réalisé est ~25%. Ce module remplace cette fabrication par une mesure empirique :
on découpe les scores en buckets et on estime le win rate réalisé par bucket,
avec un lissage bayésien vers un prior prudent quand les échantillons sont rares.

Usage :
    cal = WinRateCalibrator()
    cal.fit(scores, outcomes)          # outcomes: 1 = gagnant, 0 = perdant
    cal.save()                          # resources/win_rate_calibration.json
    p = WinRateCalibrator.load().predict(score)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("ml.win_rate_calibrator")

CALIBRATION_PATH = Path(__file__).parent.parent / "resources" / "win_rate_calibration.json"

# Prior prudent : win rate de base quand la calibration manque de données.
# Proche du win rate réalisé observé (~25%) plutôt que de l'optimisme historique.
DEFAULT_PRIOR = 0.30
# Force du prior (lissage de Laplace) : équivaut à N trades fictifs au prior.
PRIOR_STRENGTH = 10.0
MIN_SAMPLES = 20

# Bornes des buckets de score (score entier 0-10).
BUCKET_EDGES = [0.0, 4.0, 6.0, 8.0, 10.01]


class WinRateCalibrator:
    """Mappe un score vers un win rate empirique calibré sur l'historique."""

    def __init__(self):
        self._buckets: Dict[Tuple[float, float], Dict[str, float]] = {}
        self._total: int = 0

    @property
    def is_fitted(self) -> bool:
        return self._total >= MIN_SAMPLES

    def fit(self, scores: List[float], outcomes: List[int]) -> "WinRateCalibrator":
        """Ajuste la calibration. `outcomes` : 1 = gagnant, 0 = perdant."""
        self._buckets = {}
        for i in range(len(BUCKET_EDGES) - 1):
            low, high = BUCKET_EDGES[i], BUCKET_EDGES[i + 1]
            n = 0
            wins = 0
            for s, o in zip(scores, outcomes):
                if low <= s < high:
                    n += 1
                    wins += 1 if o > 0 else 0
            self._buckets[(low, high)] = {"n": n, "wins": wins}
        self._total = len(scores)
        log.info(
            f"[WinRateCalibrator] Calibration ajustée sur {self._total} trades : "
            f"{self.table()}"
        )
        return self

    def predict(self, score: float) -> float:
        """Retourne le win rate calibré pour un score, ou le prior si non calibré."""
        if not self.is_fitted:
            return DEFAULT_PRIOR
        for (low, high), b in self._buckets.items():
            if low <= score < high:
                # Shrinkage bayésien vers le prior (robuste aux petits échantillons).
                return (b["wins"] + PRIOR_STRENGTH * DEFAULT_PRIOR) / (b["n"] + PRIOR_STRENGTH)
        return DEFAULT_PRIOR

    def table(self) -> str:
        """Représentation lisible de la calibration (bucket -> win rate)."""
        parts = []
        for (low, high), b in self._buckets.items():
            n = int(b["n"])
            if n == 0:
                parts.append(f"[{low:.0f}-{high - 0.01:.0f}]: n/a")
                continue
            wr = b["wins"] / n
            parts.append(f"[{low:.0f}-{high - 0.01:.0f}]: {wr:.1%} ({n})")
        return ", ".join(parts)

    def save(self, path: Optional[str] = None) -> Path:
        save_path = Path(path) if path else CALIBRATION_PATH
        save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "buckets": {f"{low},{high}": b for (low, high), b in self._buckets.items()},
            "total": self._total,
        }
        save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log.info(f"[WinRateCalibrator] Calibration sauvegardée -> {save_path}")
        return save_path

    @classmethod
    def load(cls, path: Optional[str] = None) -> "WinRateCalibrator":
        load_path = Path(path) if path else CALIBRATION_PATH
        cal = cls()
        if not load_path.exists():
            log.info("[WinRateCalibrator] Aucune calibration sur disque — prior prudent actif.")
            return cal
        try:
            payload = json.loads(load_path.read_text(encoding="utf-8"))
            cal._buckets = {
                tuple(float(x) for x in k.split(",")): v
                for k, v in payload.get("buckets", {}).items()
            }
            cal._total = int(payload.get("total", 0))
            log.info(f"[WinRateCalibrator] Calibration chargée ({cal._total} trades).")
        except Exception as e:
            log.warning(f"[WinRateCalibrator] Erreur chargement ({e}) — prior prudent actif.")
        return cal


_cached_calibrator: Optional[WinRateCalibrator] = None


def get_calibrator() -> WinRateCalibrator:
    """Singleton chargé une seule fois (évite de relire le fichier à chaque signal)."""
    global _cached_calibrator
    if _cached_calibrator is None:
        _cached_calibrator = WinRateCalibrator.load()
    return _cached_calibrator
