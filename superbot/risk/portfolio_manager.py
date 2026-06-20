"""
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╩
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
import logging
from datetime import datetime, timedelta

log = logging.getLogger("portfolio_manager")


class PortfolioManager:
    """
    Gestionnaire de portfolio pour l'analyse de corrélation, la heat map et l'optimisation
    de la répartition du risque entre différents actifs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le gestionnaire de portfolio.

        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        self.price_history: Dict[str, List[float]] = {}  # Symbol -> liste de prix
        self.timestamp_history: List[datetime] = []  # Timestamps correspondant à l'historique
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.max_history_length = self.config.get('max_history_length', 100)  # Nombre de périodes à garder
        self.update_frequency = self.config.get('update_frequency', 20)  # Mettre à jour la corrélation toutes les N mises à jour
        self.update_counter = 0
        log.info("PortfolioManager initialisé")

    def add_price_data(self, symbol: str, price: float, timestamp: Optional[datetime] = None):
        """
        Ajoute des données de prix pour un symbole.

        Args:
            symbol: Symbole de l'instrument
            price: Prix de l'instrument
            timestamp: Timestamp des données (si None, utilise maintenant)
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Initialiser l'historique pour ce symbole si nécessaire
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        # Ajouter le prix et le timestamp
        self.price_history[symbol].append(price)
        if len(self.timestamp_history) == 0 or len(self.timestamp_history) < len(self.price_history[symbol]):
            self.timestamp_history.append(timestamp)

        # Garder seulement l'historique récent
        if len(self.price_history[symbol]) > self.max_history_length:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history_length:]

        # Mettre à jour la matrice de corrélation périodiquement
        self.update_counter += 1
        if self.update_counter >= self.update_frequency:
            self._update_correlation_matrix()
            self.update_counter = 0

        log.debug(f"Données de prix ajoutées pour {symbol}: {price}")

    def _update_correlation_matrix(self):
        """Met à jour la matrice de corrélation basée sur l'historique des prix."""
        try:
            # Vérifier qu'on a suffisamment de données pour au moins 2 symboles
            symbols_with_data = [sym for sym, prices in self.price_history.items() if len(prices) >= 2]
            if len(symbols_with_data) < 2:
                log.debug("Pas assez de données pour calculer la corrélation (besoin d'au moins 2 symboles avec 2+ points)")
                return

            # Créer un DataFrame avec l'historique des prix
            # Aligner toutes les séries sur la même longueur (minimum commun)
            min_length = min(len(self.price_history[sym]) for sym in symbols_with_data)
            if min_length < 2:
                return

            data_dict = {}
            for symbol in symbols_with_data:
                # Prendre les derniers 'min_length' points
                data_dict[symbol] = self.price_history[symbol][-min_length:]

            df = pd.DataFrame(data_dict)

            # Calculer les rendements logarithmiques (meilleure stationnarité pour la corrélation)
            returns_df = np.log(df / df.shift(1)).dropna()

            if len(returns_df) < 2:
                log.debug("Pas assez de rendements pour calculer la corrélation")
                return

            # Calculer la matrice de corrélation
            self.correlation_matrix = returns_df.corr()

            log.debug(f"Matrice de corrélation mise à jour pour {len(symbols_with_data)} symboles")

        except Exception as e:
            log.error(f"Erreur lors de la mise à jour de la matrice de corrélation: {e}")

    def get_average_correlation(self, symbol: Optional[str] = None) -> float:
        """
        Retourne la corrélation moyenne d'un symbole avec les autres,
        ou la corrélation moyenne globale du portfolio.

        Args:
            symbol: Symbole spécifique (si None, retourne la moyenne globale)

        Returns:
            Corrélation moyenne (0 à 1, ou -1 à 1 selon le contexte)
        """
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            return 0.0

        try:
            if symbol is None:
                # Corrélation moyenne globale (excluant la diagonale)
                mask = ~np.eye(self.correlation_matrix.shape[0], dtype=bool)
                avg_corr = self.correlation_matrix.where(mask).stack().mean()
                return max(-1.0, min(1.0, avg_corr))  # Borner entre -1 et 1
            else:
                if symbol not in self.correlation_matrix.columns:
                    return 0.0
                # Corrélation moyenne du symbole avec les autres (excluant lui-même)
                symbol_corrs = self.correlation_matrix[symbol].drop(symbol, errors='ignore')
                avg_corr = symbol_corrs.mean()
                return max(-1.0, min(1.0, avg_corr))

        except Exception as e:
            log.error(f"Erreur lors du calcul de la corrélation moyenne: {e}")
            return 0.0

    def get_correlation_data(self) -> Dict[str, Any]:
        """
        Retourne les données de corrélation pour l'ajustement de risque.

        Returns:
            Dictionnaire avec les données de corrélation
        """
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            return {
                'average_correlation': 0.0,
                'max_correlation': 0.0,
                'correlation_matrix': None,
                'symbols': [],
                'timestamp': datetime.now().isoformat()
            }

        try:
            # Corrélation moyenne globale
            mask = ~np.eye(self.correlation_matrix.shape[0], dtype=bool)
            avg_correlation = self.correlation_matrix.where(mask).stack().mean()

            # Corrélation maximale (excluant la diagonale)
            max_correlation = self.correlation_matrix.where(mask).max().max()

            return {
                'average_correlation': max(-1.0, min(1.0, avg_correlation)),
                'max_correlation': max(-1.0, min(1.0, max_correlation)),
                'correlation_matrix': self.correlation_matrix.copy(),
                'symbols': list(self.correlation_matrix.columns),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            log.error(f"Erreur lors de la préparation des données de corrélation: {e}")
            return {
                'average_correlation': 0.0,
                'max_correlation': 0.0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_portfolio_heatmap(self) -> Dict[str, Any]:
        """
        Retourne les données pour une heat map de corrélation du portfolio.

        Returns:
            Dictionnaire formaté pour l'affichage d'une heat map
        """
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            return {
                'error': 'No correlation data available',
                'timestamp': datetime.now().isoformat()
            }

        try:
            # Préparer les données pour la heat map
            z = self.correlation_matrix.values.tolist()
            x = list(self.correlation_matrix.columns)
            y = list(self.correlation_matrix.columns)

            return {
                'z': z,  # Matrice de corrélation
                'x': x,  # Symboles sur l'axe X
                'y': y,  # Symboles sur l'axe Y
                'colorscale': [
                    [0.0, "red"],      # Forte corrélation négative
                    [0.4, "orange"],   # Corrélation négative modérée
                    [0.45, "yellow"],  # Corrélation faible négative
                    [0.5, "lightyellow"], # Corrélation très faible
                    [0.55, "lightgreen"], # Corrélation faible positive
                    [0.6, "green"],    # Corrélation positive modérée
                    [1.0, "darkgreen"] # Forte corrélation positive
                ],
                'colorbar': {
                    'title': 'Corrélation',
                    'tickvals': [-1, -0.5, 0, 0.5, 1],
                    'ticktext': ['-1.0', '-0.5', '0.0', '0.5', '1.0']
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            log.error(f"Erreur lors de la préparation de la heat map: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def calculate_diversification_ratio(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calcule le ratio de diversification du portfolio.
        Un ratio plus élevé indique une meilleure diversification.

        Args:
            weights: Poids des actifs dans le portfolio (si None, poids égaux)

        Returns:
            Ratio de diversification (>= 1.0, où 1.0 = pas de diversification)
        """
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            return 1.0

        try:
            symbols = list(self.correlation_matrix.columns)
            n_assets = len(symbols)

            if n_assets < 2:
                return 1.0

            # Poids égaux si non spécifiés
            if weights is None:
                weights = {symbol: 1.0 / n_assets for symbol in symbols}
            else:
                # Normaliser les poids pour qu'ils somment à 1
                total_weight = sum(weights.get(symbol, 0) for symbol in symbols)
                if total_weight > 0:
                    weights = {symbol: weights.get(symbol, 0) / total_weight for symbol in symbols}
                else:
                    weights = {symbol: 1.0 / n_assets for symbol in symbols}

            # Calculer la variance du portfolio
            portfolio_variance = 0.0
            for i, symbol_i in enumerate(symbols):
                for j, symbol_j in enumerate(symbols):
                    w_i = weights.get(symbol_i, 0)
                    w_j = weights.get(symbol_j, 0)
                    corr_ij = self.correlation_matrix.loc[symbol_i, symbol_j]
                    portfolio_variance += w_i * w_j * corr_ij

            # Calculer la moyenne pondérée des volatilités individuelles
            # Pour simplifier, on suppose que toutes les volatilités sont égales à 1
            # Dans une implémentation réelle, on utiliserait les volatilités réelles
            weighted_avg_volatility = sum(weights.get(symbol, 0) * 1.0 for symbol in symbols)

            # Ratio de diversification = volatilité moyenne pondérée / volatilité du portfolio
            if portfolio_variance > 0:
                diversification_ratio = weighted_avg_volatility / np.sqrt(portfolio_variance)
            else:
                diversification_ratio = 1.0

            # Le ratio de diversification est toujours >= 1.0
            return max(1.0, diversification_ratio)

        except Exception as e:
            log.error(f"Erreur lors du calcul du ratio de diversification: {e}")
            return 1.0

    def get_risk_contribution(self, weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Calcule la contribution au risque de chaque actif dans le portfolio.

        Args:
            weights: Poids des actifs dans le portfolio (si None, poids égaux)

        Returns:
            Dictionnaire symbole -> contribution au risque (en pourcentage)
        """
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            return {}

        try:
            symbols = list(self.correlation_matrix.columns)
            n_assets = len(symbols)

            if n_assets == 0:
                return {}

            # Poids égaux si non spécifiés
            if weights is None:
                weights = {symbol: 1.0 / n_assets for symbol in symbols}
            else:
                # Normaliser les poids pour qu'ils somment à 1
                total_weight = sum(weights.get(symbol, 0) for symbol in symbols)
                if total_weight > 0:
                    weights = {symbol: weights.get(symbol, 0) / total_weight for symbol in symbols}
                else:
                    weights = {symbol: 1.0 / n_assets for symbol in symbols}

            # Calculer la variance du portfolio
            portfolio_variance = 0.0
            for i, symbol_i in enumerate(symbols):
                for j, symbol_j in enumerate(symbols):
                    w_i = weights.get(symbol_i, 0)
                    w_j = weights.get(symbol_j, 0)
                    corr_ij = self.correlation_matrix.loc[symbol_i, symbol_j]
                    portfolio_variance += w_i * w_j * corr_ij

            # Calculer la contribution au risque de chaque actif
            risk_contribution = {}
            if portfolio_variance > 0:
                for symbol in symbols:
                    w_i = weights.get(symbol, 0)
                    # Marginal contribution to risk
                    marginal_contrib = 0.0
                    for symbol_j in symbols:
                        w_j = weights.get(symbol_j, 0)
                        corr_ij = self.correlation_matrix.loc[symbol, symbol_j]
                        marginal_contrib += w_j * corr_ij

                    # Component contribution to risk
                    component_contrib = w_i * marginal_contrib
                    # Pourcentage de la variance totale du portfolio
                    pct_contribution = (component_contrib / portfolio_variance) * 100
                    risk_contribution[symbol] = pct_contribution
            else:
                # Si la variance du portfolio est zéro, répartir équitablement
                for symbol in symbols:
                    risk_contribution[symbol] = 100.0 / n_assets

            return risk_contribution

        except Exception as e:
            log.error(f"Erreur lors du calcul de la contribution au risque: {e}")
            return {}

    def suggest_rebalancing(self, current_weights: Dict[str, float],
                          target_risk_contribution: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Suggère un rééquilibrage du portfolio basé sur la contribution au risque.

        Args:
            current_weights: Poids actuels de chaque actif
            target_risk_contribution: Contribution au risque souhaitée pour chaque actif
                                    (si None, répartition égale du risque)

        Returns:
            Dictionnaire avec les suggestions de rééquilibrage
        """
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            return {
                'error': 'No correlation data available for rebalancing suggestions',
                'suggested_weights': current_weights,
                'timestamp': datetime.now().isoformat()
            }

        try:
            symbols = list(self.correlation_matrix.columns)

            # Vérifier que tous les symboles présents dans current_weights sont dans la matrice
            valid_symbols = [sym for sym in current_weights.keys() if sym in symbols]
            if not valid_symbols:
                return {
                    'error': 'No valid symbols found in current weights',
                    'suggested_weights': current_weights,
                    'timestamp': datetime.now().isoformat()
                }

            # Contribution au risque souhaitée (égale par défaut si non spécifiée)
            if target_risk_contribution is None:
                n_valid = len(valid_symbols)
                target_risk_contribution = {symbol: 100.0 / n_valid for symbol in valid_symbols}
            else:
                # Normaliser pour que la somme soit 100%
                total_target = sum(target_risk_contribution.get(symbol, 0) for symbol in valid_symbols)
                if total_target > 0:
                    target_risk_contribution = {
                        symbol: (target_risk_contribution.get(symbol, 0) / total_target) * 100.0
                        for symbol in valid_symbols
                    }
                else:
                    n_valid = len(valid_symbols)
                    target_risk_contribution = {symbol: 100.0 / n_valid for symbol in valid_symbols}

            # Calculer la contribution au risque actuelle
            current_risk_contribution = self.get_risk_contribution(current_weights)

            # Calculer l'écart entre l'actuel et le souhaité
            risk_gaps = {}
            for symbol in valid_symbols:
                current = current_risk_contribution.get(symbol, 0.0)
                target = target_risk_contribution.get(symbol, 0.0)
                risk_gaps[symbol] = target - current  # Positif = besoin d'augmenter, négatif = besoin de diminuer

            # Pour simplifier, on suggère d'ajuster les poids proportionnellement aux écarts de risque
            # Dans une implémentation plus sophistiquée, on utiliserait une optimisation
            suggested_weights = current_weights.copy()

            # Ajuster les poids basé sur les écarts de risque (approche simple)
            total_adjustment_needed = sum(abs(gap) for gap in risk_gaps.values())
            if total_adjustment_needed > 0:
                for symbol in valid_symbols:
                    gap = risk_gaps.get(symbol, 0.0)
                    # Proportion de l'ajustement total
                    adjustment_ratio = abs(gap) / total_adjustment_needed if total_adjustment_needed > 0 else 0
                    # Direction de l'ajustement
                    direction = 1 if gap > 0 else -1
                    # Facteur d'ajustement (limité pour éviter des changements trop brusques)
                    adjustment_factor = 0.1 * adjustment_ratio * direction  # Max 10% d'ajustement par iteration
                    suggested_weights[symbol] = current_weights.get(symbol, 0.0) * (1.0 + adjustment_factor)

            # Renormaliser les poids suggérés
            total_suggested = sum(suggested_weights.get(symbol, 0) for symbol in valid_symbols)
            if total_suggested > 0:
                suggested_weights = {
                    symbol: (suggested_weights.get(symbol, 0) / total_suggested) * 100.0
                    for symbol in valid_symbols
                }

            return {
                'current_weights': current_weights,
                'current_risk_contribution': current_risk_contribution,
                'target_risk_contribution': target_risk_contribution,
                'risk_gaps': risk_gaps,
                'suggested_weights': suggested_weights,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            log.error(f"Erreur lors du calcul des suggestions de rééquilibrage: {e}")
            return {
                'error': str(e),
                'suggested_weights': current_weights,
                'timestamp': datetime.now().isoformat()
            }

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé complet du portfolio.

        Returns:
            Dictionnaire avec le résumé du portfolio
        """
        try:
            symbols_with_data = [sym for sym, prices in self.price_history.items() if len(prices) > 0]

            summary = {
                'tracked_symbols': len(symbols_with_data),
                'symbols_list': symbols_with_data,
                'history_length': min((len(prices) for prices in self.price_history.values() if len(prices) > 0), default=0),
                'correlation_data_available': self.correlation_matrix is not None and not self.correlation_matrix.empty,
                'timestamp': datetime.now().isoformat()
            }

            if self.correlation_matrix is not None and not self.correlation_matrix.empty:
                summary.update({
                    'average_correlation': self.get_average_correlation(),
                    'max_correlation': self.get_correlation_data()['max_correlation'],
                    'diversification_ratio': self.calculate_diversification_ratio()
                })

            return summary

        except Exception as e:
            log.error(f"Erreur lors de la génération du résumé du portfolio: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Fonctions utilitaires pour une utilisation facile
def update_portfolio_price(symbol: str, price: float,
                          portfolio_manager: PortfolioManager,
                          timestamp: Optional[datetime] = None):
    """
    Fonction utilitaire pour mettre à jour facilement les données de prix dans le portfolio manager.

    Args:
        symbol: Symbole de l'instrument
        price: Prix de l'instrument
        portfolio_manager: Instance du PortfolioManager
        timestamp: Timestamp des données (si None, utilise maintenant)
    """
    portfolio_manager.add_price_data(symbol, price, timestamp)


# Export des classes et fonctions publiques
__all__ = [
    'PortfolioManager',
    'update_portfolio_price'
]