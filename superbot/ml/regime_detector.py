"""
NexQuant MarketRegimeDetector — Phase 2
=========================================
Classifie le régime de marché en 3 états cachés via un modèle HMM
(Hidden Markov Model à émissions gaussiennes).

Architecture :
  - 4 états cachés : BULLISH_TREND, BEARISH_TREND, LOW_VOL_RANGE, HIGH_VOL_RANGE
  - 5 features extraites des bougies OHLCV
  - Entraînement hors-ligne via train_regime.py
  - Prédiction en temps réel avec score de confiance (probabilité de l'état)
  - Fallback automatique sur la règle ADX si le modèle n'est pas entraîné

Features utilisées (toutes normalisées via StandardScaler) :
  1. log_return        : Rendement logarithmique de la bougie (ln(close/prev_close))
  2. rolling_vol_20    : Volatilité roulante des rendements sur 20 périodes
  3. volume_zscore     : Z-score du volume sur 20 périodes (anomalie de volume)
  4. bb_width_norm     : Bande passante Bollinger normalisée en percentile 0-100
  5. adx_delta_5       : Variation de l'ADX sur 5 périodes (accélération de tendance)

Mapping des états vers les régimes NexQuant :
  - BULLISH_TREND    -> 'TRENDING'
  - BEARISH_TREND    -> 'TRENDING'
  - LOW_VOL_RANGE    -> 'RANGING'
  - HIGH_VOL_RANGE   -> 'RANGING'

Utilisation :
    detector = MarketRegimeDetector()
    detector.fit(df_history)                    # Entraîner
    regime, confidence, state_id = detector.predict(df_recent)
    # -> ('TRENDING', 0.87, 0)

    # Avec persistence :
    detector.save('resources/hmm_model.pkl')
    detector2 = MarketRegimeDetector.load('resources/hmm_model.pkl')
"""
import logging
import warnings
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np
import pandas as pd

log = logging.getLogger("ml.regime_detector")

# Répertoire de sauvegarde du modèle
MODEL_DIR = Path(__file__).parent.parent / "resources"
DEFAULT_MODEL_PATH = MODEL_DIR / "hmm_regime_model.pkl"

# Noms des états (ordre déterminé post-entraînement par caractéristiques)
STATE_NAMES = {0: "BULLISH_TREND", 1: "BEARISH_TREND", 2: "LOW_VOL_RANGE", 3: "HIGH_VOL_RANGE"}

# Mapping état -> régime NexQuant
REGIME_MAP = {
    "BULLISH_TREND":   "TRENDING",
    "BEARISH_TREND":   "TRENDING",
    "LOW_VOL_RANGE":   "RANGING",
    "HIGH_VOL_RANGE":  "RANGING",
}


class MarketRegimeDetector:
    """
    Détecteur de régime de marché basé sur un HMM gaussien à 4 états.

    Le modèle identifie automatiquement 4 phases de marché distinctes
    à partir de l'historique OHLCV, sans supervision humaine.
    """

    N_STATES = 4
    N_ITER = 200           # Itérations EM pour la convergence
    N_FEATURES = 5         # Nombre de features extraites
    MIN_BARS_FOR_FIT = 200 # Minimum de bougies pour entraîner
    LOOKBACK_PREDICT = 30  # Bougies utilisées pour la prédiction

    def __init__(self):
        self._model = None           # hmmlearn.GaussianHMM
        self._scaler = None          # sklearn.StandardScaler
        self._state_labels: Dict[int, str] = {}  # {0: "BULLISH_STABLE", ...}
        self._is_trained = False
        self._training_stats: Dict[str, Any] = {}

    # ─── API publique ─────────────────────────────────────────────────────────

    def fit(self, df: pd.DataFrame) -> "MarketRegimeDetector":
        """
        Entraîne le HMM sur un historique de bougies OHLCV.

        L'algorithme EM (Expectation-Maximization / Baum-Welch) ajuste
        automatiquement les paramètres du modèle pour maximiser la
        vraisemblance des données observées.

        Args:
            df: DataFrame OHLCV avec au moins MIN_BARS_FOR_FIT bougies.

        Returns:
            self (pour le chaînage)
        """
        from hmmlearn.hmm import GaussianHMM
        from sklearn.preprocessing import StandardScaler

        if len(df) < self.MIN_BARS_FOR_FIT:
            raise ValueError(
                f"Pas assez de données pour entraîner le HMM : "
                f"{len(df)} bougies < minimum requis ({self.MIN_BARS_FOR_FIT})"
            )

        log.info(f"[HMM] Extraction des features sur {len(df)} bougies...")
        features = self._extract_features(df)

        # Supprimer les lignes avec NaN (début de séries roulantes)
        valid_mask = ~np.isnan(features).any(axis=1)
        X = features[valid_mask]

        log.info(f"[HMM] {X.shape[0]} observations valides, {X.shape[1]} features")

        # Normalisation (StandardScaler : moyenne 0, écart-type 1)
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        # Entraînement du HMM gaussien
        log.info(f"[HMM] Entraînement GaussianHMM ({self.N_STATES} états, {self.N_ITER} itérations)...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Supprimer les warnings de convergence
            self._model = GaussianHMM(
                n_components=self.N_STATES,
                covariance_type="full",
                n_iter=self.N_ITER,
                random_state=42,
                tol=1e-4,
            )
            self._model.fit(X_scaled)

        # Prédire les états sur l'ensemble d'entraînement
        hidden_states = self._model.predict(X_scaled)

        # Labelliser les états automatiquement
        self._label_states(X, hidden_states, df[valid_mask])

        # Statistiques d'entraînement
        self._training_stats = self._compute_training_stats(X, hidden_states)
        self._is_trained = True

        log.info(
            f"[HMM] Modele entraine. Log-likelihood: {self._model.score(X_scaled):.2f} | "
            f"Labels: {self._state_labels}"
        )
        return self

    def predict(self, df: pd.DataFrame) -> Tuple[str, float, int]:
        """
        Prédit le régime de marché sur les dernières bougies.

        Args:
            df: DataFrame OHLCV (au moins 30 bougies récentes recommandées)

        Returns:
            Tuple (regime_str, confidence, state_id)
            - regime_str : 'TRENDING' ou 'RANGING'
            - confidence : probabilité de l'état prédit (0.0 à 1.0)
            - state_id   : indice de l'état HMM (0, 1 ou 2)
        """
        if not self._is_trained:
            log.debug("[HMM] Modele non entraîné — fallback ADX")
            return self._fallback_prediction(df)

        # Utiliser les N dernières bougies pour la prédiction
        df_recent = df.iloc[-max(self.LOOKBACK_PREDICT, 30):].copy()

        try:
            features = self._extract_features(df_recent)
            valid_mask = ~np.isnan(features).any(axis=1)
            X = features[valid_mask]

            if len(X) < 5:
                return self._fallback_prediction(df)

            X_scaled = self._scaler.transform(X)

            # Décoder la séquence d'états la plus probable (algorithme de Viterbi)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                states = self._model.predict(X_scaled)

            # État courant = dernier état de la séquence
            current_state = int(states[-1])

            # Confiance = proportion de l'état courant dans les 10 dernières bougies
            # (plus robuste que predict_proba sur des séquences courtes)
            recent_states = states[-min(10, len(states)):]
            confidence = float(np.sum(recent_states == current_state) / len(recent_states))
            # Arrondir à 2 décimales et garantir >= 0.5 (l'état dominant est toujours majoritaire)
            confidence = max(0.50, round(confidence, 2))

            # Mapper vers le label et le régime NexQuant
            state_label = self._state_labels.get(current_state, "RANGING_QUIET")
            regime = REGIME_MAP.get(state_label, "RANGING")

            log.debug(
                f"[HMM] Etat={current_state} ({state_label}) | "
                f"Regime={regime} | Confiance={confidence:.2%}"
            )
            return regime, confidence, current_state

        except Exception as e:
            log.warning(f"[HMM] Erreur de prédiction : {e} — fallback ADX")
            return self._fallback_prediction(df)

    def get_state_label(self, state_id: int) -> str:
        """Retourne le nom de l'état HMM (ex: 'BULLISH_STABLE')."""
        return self._state_labels.get(state_id, f"STATE_{state_id}")

    def print_training_summary(self):
        """Affiche un résumé des statistiques d'entraînement dans le terminal."""
        if not self._is_trained:
            print("[HMM] Modele non entraîné.")
            return

        sep = "=" * 60
        print(f"\n{sep}")
        print("  HMM — Résumé des régimes détectés")
        print(sep)
        for state_id, label in self._state_labels.items():
            stats = self._training_stats.get(state_id, {})
            regime = REGIME_MAP.get(label, "?")
            freq = stats.get("frequency_pct", 0)
            mean_ret = stats.get("mean_log_return", 0)
            mean_vol = stats.get("mean_volatility", 0)
            print(
                f"  Etat {state_id} [{label}]"
                f"\n    -> Régime NexQuant : {regime}"
                f"\n    -> Fréquence       : {freq:.1f}% du temps"
                f"\n    -> Rendement moyen : {mean_ret*100:+.4f}%/bougie"
                f"\n    -> Volatilité moy. : {mean_vol*100:.4f}%"
            )
        print(sep + "\n")

    # ─── Persistence ─────────────────────────────────────────────────────────

    def save(self, path: Optional[str] = None) -> Path:
        """Sauvegarde le modèle entraîné (modèle + scaler + labels)."""
        import joblib
        if not self._is_trained:
            raise RuntimeError("Le modèle n'est pas encore entraîné.")

        save_path = Path(path) if path else DEFAULT_MODEL_PATH
        save_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model": self._model,
            "scaler": self._scaler,
            "state_labels": self._state_labels,
            "training_stats": self._training_stats,
            "n_states": self.N_STATES,
        }
        joblib.dump(payload, save_path)
        log.info(f"[HMM] Modele sauvegardé -> {save_path}")
        return save_path

    @classmethod
    def load(cls, path: Optional[str] = None) -> "MarketRegimeDetector":
        """Charge un modèle sauvegardé. Retourne un détecteur non-entraîné si le fichier est absent."""
        import joblib
        load_path = Path(path) if path else DEFAULT_MODEL_PATH

        detector = cls()

        if not load_path.exists():
            log.warning(
                f"[HMM] Modele introuvable : {load_path} — "
                "Le détecteur utilisera la règle ADX (fallback) jusqu'au premier entraînement.\n"
                "Lancez : python superbot/ml/train_regime.py pour entraîner le modèle."
            )
            return detector

        try:
            payload = joblib.load(load_path)
            detector._model = payload["model"]
            detector._scaler = payload["scaler"]
            detector._state_labels = payload["state_labels"]
            detector._training_stats = payload.get("training_stats", {})
            detector._is_trained = True
            log.info(
                f"[HMM] Modele chargé depuis {load_path.name} | "
                f"Labels: {detector._state_labels}"
            )
        except Exception as e:
            log.error(f"[HMM] Erreur au chargement du modèle ({e}) — fallback ADX activé.")

        return detector

    # ─── Extraction de features ───────────────────────────────────────────────

    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extrait la matrice de features (T × 5) depuis les bougies OHLCV.

        Feature 1 — log_return (rendement log)
          Mesure la direction et la force du mouvement de prix.
          Avantage vs pct_change : symétrique, additivité temporelle.

        Feature 2 — rolling_vol_20 (volatilité roulante)
          Écart-type des log_returns sur 20 barres.
          Distingue les régimes calmes (faible vol) des régimes agités.

        Feature 3 — volume_zscore (anomalie de volume)
          Z-score du volume courant vs moyenne 20 barres.
          Les breakouts valides sont accompagnés d'un volume anormal.

        Feature 4 — bb_width_norm (largeur Bollinger normalisée)
          Percentile 0-100 de la largeur des BB sur une fenêtre de 100 barres.
          Proche de 0 = squeeze (pré-breakout), proche de 100 = expansion.

        Feature 5 — adx_delta_5 (variation ADX sur 5 barres)
          Mesure l'accélération ou la décélération de la tendance.
          Positif = tendance qui se renforce, négatif = tendance qui s'affaiblit.
        """
        close = df["close"].values.astype(float)
        volume = df["volume"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)

        n = len(close)
        features = np.full((n, self.N_FEATURES), np.nan)

        # Feature 1 : Log return
        log_ret = np.zeros(n)
        log_ret[1:] = np.log(close[1:] / np.where(close[:-1] > 0, close[:-1], np.nan))
        features[:, 0] = log_ret

        # Feature 2 : Volatilité roulante 20 barres
        for i in range(20, n):
            features[i, 1] = np.std(log_ret[i-19:i+1])

        # Feature 3 : Volume Z-score 20 barres
        for i in range(20, n):
            vol_window = volume[i-19:i+1]
            vol_mean = np.mean(vol_window)
            vol_std = np.std(vol_window)
            features[i, 2] = (volume[i] - vol_mean) / vol_std if vol_std > 0 else 0.0

        # Feature 4 : BB width normalisé (percentile sur 100 barres)
        if "bb_width" in df.columns:
            bb_width = df["bb_width"].values.astype(float)
        else:
            # Calculer BB width depuis OHLCV
            bb_width = np.full(n, np.nan)
            window = 20
            for i in range(window, n):
                c_win = close[i-window:i]
                sma = np.mean(c_win)
                std = np.std(c_win)
                if sma > 0:
                    bb_width[i] = (4 * std) / sma  # (upper - lower) / middle

        for i in range(100, n):
            window_bw = bb_width[i-99:i+1]
            valid = window_bw[~np.isnan(window_bw)]
            if len(valid) > 0:
                pct = np.sum(valid <= bb_width[i]) / len(valid) * 100
                features[i, 3] = pct

        # Feature 5 : ADX delta 5 barres
        if "adx" in df.columns:
            adx = df["adx"].values.astype(float)
        else:
            # Approximation via True Range si ADX absent
            adx = np.full(n, 0.0)
            for i in range(1, n):
                tr = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
                adx[i] = tr

        for i in range(5, n):
            if not np.isnan(adx[i]) and not np.isnan(adx[i-5]):
                features[i, 4] = adx[i] - adx[i-5]

        return features

    # ─── Labellisation automatique des états ──────────────────────────────────

    def _label_states(self, X: np.ndarray, states: np.ndarray, df_valid: pd.DataFrame):
        # Assigne automatiquement un label sémantique à 4 états
        state_stats = {}
        for s in range(self.N_STATES):
            mask = states == s
            if mask.sum() == 0:
                state_stats[s] = {"mean_ret": 0, "mean_vol": 0}
                continue
            state_stats[s] = {
                "mean_ret": np.nanmean(X[mask, 0]),   # log_return
                "mean_vol": np.nanmean(X[mask, 1]),   # rolling_vol
                "count": int(mask.sum()),
            }

        self._state_labels = {}
        
        if len(state_stats) < 4:
            # Fallback en cas de non convergence sur 4 états (ex: peu de données)
            for s in state_stats:
                self._state_labels[s] = f"STATE_{s}"
            return
            
        # 1. Trier par volatilité pour identifier LOW_VOL_RANGE et HIGH_VOL_RANGE
        sorted_by_vol = sorted(state_stats.items(), key=lambda x: x[1]["mean_vol"])
        low_vol_state = sorted_by_vol[0][0]      # La plus faible vol
        high_vol_state = sorted_by_vol[-1][0]    # La plus forte vol
        
        self._state_labels[low_vol_state] = "LOW_VOL_RANGE"
        self._state_labels[high_vol_state] = "HIGH_VOL_RANGE"
        
        # 2. Les deux états restants sont classés par rendement pour BULLISH/BEARISH
        remaining_states = [s[0] for s in sorted_by_vol[1:-1]]
        if state_stats[remaining_states[0]]["mean_ret"] > state_stats[remaining_states[1]]["mean_ret"]:
            bullish_state = remaining_states[0]
            bearish_state = remaining_states[1]
        else:
            bullish_state = remaining_states[1]
            bearish_state = remaining_states[0]
            
        self._state_labels[bullish_state] = "BULLISH_TREND"
        self._state_labels[bearish_state] = "BEARISH_TREND"

        log.info(f"[HMM] Labels assignés automatiquement : {self._state_labels}")
        for s, stats in state_stats.items():
            log.info(
                f"  Etat {s} [{self._state_labels.get(s, '?')}] : "
                f"n={stats.get('count', 0)} | "
                f"ret_moy={stats.get('mean_ret', 0)*100:+.4f}%/bar | "
                f"vol_moy={stats.get('mean_vol', 0)*100:.4f}%"
            )

    def _compute_training_stats(self, X: np.ndarray, states: np.ndarray) -> Dict:
        """Calcule les statistiques par état pour les rapports."""
        total = len(states)
        stats = {}
        for s in range(self.N_STATES):
            mask = states == s
            count = int(mask.sum())
            stats[s] = {
                "count": count,
                "frequency_pct": (count / total * 100) if total > 0 else 0,
                "mean_log_return": float(np.nanmean(X[mask, 0])) if count > 0 else 0.0,
                "mean_volatility": float(np.nanmean(X[mask, 1])) if count > 0 else 0.0,
                "mean_volume_zscore": float(np.nanmean(X[mask, 2])) if count > 0 else 0.0,
            }
        return stats

    # ─── Fallback ADX ────────────────────────────────────────────────────────

    def _fallback_prediction(self, df: pd.DataFrame, adx_threshold: float = 22.0) -> Tuple[str, float, int]:
        """
        Prédiction de secours basée uniquement sur l'ADX.
        Retourne une confiance de 0.5 pour signaler l'incertitude.
        """
        if len(df) > 0 and "adx" in df.columns:
            adx_val = float(df["adx"].iloc[-1])
            if adx_val > adx_threshold:
                return "TRENDING", 0.50, -1
        return "RANGING", 0.50, -1
