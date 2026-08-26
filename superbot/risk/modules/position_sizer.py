import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import math
from typing import Dict, Any, Tuple, Optional
log = logging.getLogger(__name__)

def calculate_position_size(rm, account_balance: float, entry_price: float,
                           stop_loss: float, symbol: str = "",
                           sentiment_factor: float = 1.0,
                           volatility_data: Optional[Dict[str, Any]] = None,
                           correlation_data: Optional[Dict[str, Any]] = None,
                           broker: Optional[Any] = None,
                           hmm_regime: str = "") -> Tuple[float, Dict[str, Any]]:
    """
    Calcule la taille de position optimale basée sur le risque, Kelly, et divers facteurs.

    Args:
        rm: Instance du RiskManager
        account_balance: Solde du compte
        entry_price: Prix d'entrée proposé
        stop_loss: Niveau de stop loss proposé
        symbol: Symbole de l'instrument
        sentiment_factor: Facteur de sentiment des nouvelles (0-2, où 1 = neutre)
        volatility_data: Données de volatilité pour ajustement
        correlation_data: Données de corrélation pour ajustement de portefeuille
        broker: Instance du courtier actif
        hmm_regime: Label du régime HMM (ex: 'HIGH_VOL_RANGE', 'TRENDING')
                    Utilisé pour la Phase 3 §1 — dimensionnement dynamique par régime.

    Returns:
        Tuple de (taille_de_position, détails_du_calcul)
    """
    try:
        # 1. Récupérer les spécifications du symbole (taille du contrat, tick size, tick value)
        contract_size = 1.0
        tick_size = 0.01
        tick_value = 0.01

        if broker is not None and hasattr(broker, 'get_symbol_info'):
            try:
                sym_info = broker.get_symbol_info(symbol)
                contract_size = sym_info.get('contract_size', 1.0)
                tick_size = sym_info.get('tick_size', 0.01)
                tick_value = sym_info.get('tick_value', 0.01)
            except Exception as e:
                log.warning(f"Impossible de récupérer les spécifications de symbole pour {symbol}: {e}")

        # 2. Calculer le risque par unité en devise de compte
        raw_price_risk = abs(entry_price - stop_loss)

        # Intégrer les coûts de transaction dans le risque par unité
        from superbot.config import COMMISSION_PCT, SLIPPAGE_PCT
        cost_pct = (COMMISSION_PCT * 2) + SLIPPAGE_PCT
        cost_abs = entry_price * (cost_pct / 100.0)

        price_risk = raw_price_risk + cost_abs

        if price_risk <= 0:
            log.warning(f"Risque par unité invalide pour {symbol}: {price_risk}")
            return 0.0, {'error': 'Invalid risk per unit'}

        # Formule universelle de risque par unité dans la monnaie de compte
        tick_size = max(tick_size, 1e-10)
        risk_per_unit = (price_risk / tick_size) * tick_value
        
        if risk_per_unit <= 0:
            log.warning(f"Risk per unit is zero or negative for {symbol}")
            return getattr(rm, 'MIN_POSITION_SIZE', 0.01), {'error': 'Zero risk per unit'}

        # 3. Calculer le risque en pourcentage du compte
        base_risk = rm.RISK_PCT
        # 🧠 V3 : Target-aware risk si applicable
        daily_target = getattr(rm, 'daily_target', 0)
        if daily_target > 0:
            base_risk = rm.get_target_aware_risk_pct(rm.daily_pnl, daily_target, base_risk)
        
        risk_pct = base_risk / 100.0  # Convertir en décimal

        # Dimensionnement dynamique par régime HMM : le risque par trade est ajusté :
        # - TRENDING / LOW_VOL_TREND : +20% (tendance claire, alpha plus élevé)
        # - LOW_VOL_RANGE / RANGING  : -30% (range, moins de certitude)
        # - HIGH_VOL_RANGE           : -50% (chaos, protection maximale)
        regime_upper = hmm_regime.upper() if hmm_regime else ""
        regime_risk_multiplier = 1.0
        if regime_upper in ("TRENDING", "LOW_VOL_TREND"):
            regime_risk_multiplier = 1.20  # +20% en tendance forte
            log.debug(f"[Régime-Risk] {regime_upper} → risque ×1.20 pour {symbol}")
        elif regime_upper in ("LOW_VOL_RANGE", "RANGING"):
            regime_risk_multiplier = 0.70  # -30% en range
            log.debug(f"[Régime-Risk] {regime_upper} → risque ×0.70 pour {symbol}")
        elif regime_upper == "HIGH_VOL_RANGE":
            regime_risk_multiplier = 0.50  # -50% en haute volatilité
            log.info(f"[Régime-Risk] HIGH_VOL_RANGE → risque ×0.50 pour {symbol} (protection haute volatilité)")
        risk_pct *= regime_risk_multiplier

        # Réduction du risque selon le drawdown courant : -20% à 5% DD, -50% à 10% DD.
        # Se réinitialise automatiquement quand le capital récupère.
        drawdown_multiplier = 1.0
        if rm.drawdown_pct >= rm.DRAWDOWN_THRESH_2:
            drawdown_multiplier = 1.0 - rm.DRAWDOWN_REDUCE_10PCT  # ex: 0.50
            log.info(
                f"[DD-Protection] Drawdown {rm.drawdown_pct:.1f}% >= {rm.DRAWDOWN_THRESH_2}% "
                f"→ risque réduit de {rm.DRAWDOWN_REDUCE_10PCT*100:.0f}% (multiplicateur={drawdown_multiplier:.2f})"
            )
        elif rm.drawdown_pct >= rm.DRAWDOWN_THRESH_1:
            drawdown_multiplier = 1.0 - rm.DRAWDOWN_REDUCE_5PCT   # ex: 0.80
            log.info(
                f"[DD-Protection] Drawdown {rm.drawdown_pct:.1f}% >= {rm.DRAWDOWN_THRESH_1}% "
                f"→ risque réduit de {rm.DRAWDOWN_REDUCE_5PCT*100:.0f}% (multiplicateur={drawdown_multiplier:.2f})"
            )
        risk_pct *= drawdown_multiplier

        # 4. Ajuster le risque basé sur le sentiment des nouvelles
        # sentiment_factor: < 1 = réduire le risque, > 1 = augmenter légèrement
        adjusted_risk_pct = risk_pct * sentiment_factor

        # S'assurer que le risque ajusté reste dans des limites raisonnables
        adjusted_risk_pct = max(0.005, min(0.05, adjusted_risk_pct))  # Entre 0.5% et 5%

        # 5. Ajuster basé sur la corrélation du portefeuille (si disponible)
        correlation_adjustment = 1.0
        if correlation_data and 'average_correlation' in correlation_data:
            avg_corr = correlation_data['average_correlation']
            # Plus forte corrélation moyenne = réduire la taille pour éviter la surconcentration
            if avg_corr > 0.7:  # Forte corrélation
                correlation_adjustment = 0.7
            elif avg_corr > 0.5:  # Corrélation modérée
                correlation_adjustment = 0.85

        # 6. Calculer la taille de position de base basée sur le risque
        risk_amount = account_balance * adjusted_risk_pct * correlation_adjustment
        base_position_size = risk_amount / risk_per_unit

        # 7. Appliquer la fraction de Kelly si on a suffisamment de données historiques.
        # ⚠️ Clarification d'unités : `kelly_fraction` est une fraction du bankroll.
        # On l'interprète ici comme la fraction du capital à RISQUER par trade pour
        # rester homogène avec `base_position_size` (les deux termes sont des unités
        # d'actif = capital_risqué / risk_per_unit). Le Kelly pur pouvant atteindre
        # 50 % du bankroll, on plafonne sa contribution à 5 % — le même plafond de
        # risque que le sizing fixe (voir `max_allowed_risk_pct` plus bas).
        kelly_fraction = rm._calculate_kelly_fraction()
        if kelly_fraction is not None and len(rm.trade_history) >= rm.MIN_TRADES_FOR_KELLY:
            kelly_risk_pct = min(max(kelly_fraction, 0.0), 0.05)
            kelly_position_size = account_balance * kelly_risk_pct / risk_per_unit
            # Combiner approche risque fixe et Kelly (mêmes unités : taille d'actif)
            position_size = (base_position_size * (1 - rm.KELLY_FRACTION) +
                           kelly_position_size * rm.KELLY_FRACTION)
            log.debug(f"Kelly appliqué: base={base_position_size:.4f}, kelly={kelly_position_size:.4f}, final={position_size:.4f}")
        else:
            position_size = base_position_size
            if kelly_fraction is not None:
                log.debug(f"Pas assez de données pour Kelly ({len(rm.trade_history)}/{rm.MIN_TRADES_FOR_KELLY}), utilisation du risque fixe")
            else:
                log.debug("Kelly non disponible, utilisation du risque fixe")

        position_size = float(position_size)

        # 8. Récupérer les limites de taille spécifiques au broker
        min_size = getattr(rm, 'MIN_POSITION_SIZE', 0.01)
        step_size = None
        if broker is not None:
            try:
                if hasattr(broker, 'get_min_order_size'):
                    min_size = broker.get_min_order_size(symbol)
                elif hasattr(broker, 'get_symbol_info'):
                    sym_info = broker.get_symbol_info(symbol)
                    if isinstance(sym_info, dict) and 'volume_min' in sym_info:
                        min_size = sym_info['volume_min']

                if hasattr(broker, 'get_step_size'):
                    step_size = broker.get_step_size(symbol)
                elif hasattr(broker, 'get_symbol_info'):
                    sym_info = broker.get_symbol_info(symbol)
                    if isinstance(sym_info, dict) and 'volume_step' in sym_info:
                        step_size = sym_info['volume_step']
            except Exception as e:
                log.warning(f"Impossible de récupérer les limites broker pour {symbol}: {e}")

        # 8.5. Restreindre la taille par rapport à la marge disponible chez le broker
        free_margin = account_balance
        leverage = 1
        if broker is not None:
            try:
                summary = broker.get_account_summary()
                if summary:
                    # Chercher la marge disponible
                    free_margin = summary.get("free_margin")
                    if free_margin is None:
                        free_margin = summary.get("buying_power")
                    if free_margin is None:
                        free_margin = summary.get("available_balance")
                    if free_margin is None:
                        free_margin = summary.get("balance", account_balance)

                    # Chercher l'effet de levier
                    leverage = summary.get("leverage", 1)
            except Exception as e:
                log.warning(f"Impossible de récupérer la marge disponible du broker pour {symbol}: {e}")

        # Calculer la taille maximale autorisée par la marge disponible (avec 5% de buffer)
        is_buying_power_direct = (broker is not None and hasattr(broker, 'get_asset_type') and broker.get_asset_type() == "stock")
        unit_notional = entry_price * contract_size
        if is_buying_power_direct:
            max_nominal = free_margin * 0.95
            max_size_by_margin = max_nominal / unit_notional if unit_notional > 0 else 0.0
        else:
            max_nominal = free_margin * leverage * 0.95
            max_size_by_margin = max_nominal / unit_notional if unit_notional > 0 else 0.0

        # Si la taille maximale par rapport à la marge est inférieure au minimum du symbole
        if max_size_by_margin < min_size:
            log.warning(
                f"❌ Marge disponible insuffisante pour la taille minimale sur {symbol}. "
                f"Taille min requise: {min_size:.6f}, Max autorisé par marge: {max_size_by_margin:.6f} "
                f"(Marge dispo: {free_margin:.2f}, Levier: {leverage}x)"
            )
            return 0.0, {
                'error': 'Insufficient margin for minimum position size',
                'free_margin': free_margin,
                'leverage': leverage,
                'min_size': min_size,
                'max_size_by_margin': max_size_by_margin
            }

        if position_size > max_size_by_margin:
            log.info(
                f"⚠️ Taille de position restreinte par la marge disponible pour {symbol} : "
                f"{position_size:.6f} -> {max_size_by_margin:.6f} "
                f"(Marge disponible: {free_margin:.2f}, Levier: {leverage}x, Max nominal: {max_nominal:.2f})"
            )
            position_size = max_size_by_margin

        # Appliquer les limites de taille de position
        position_size = max(min_size, min(position_size, rm.MAX_POSITION_SIZE))

        if step_size is not None and step_size > 0:
            position_size = math.floor(position_size / step_size) * step_size
            position_size = round(position_size, 8)
            
        position_size = max(position_size, min_size)
        if position_size < min_size:
            return 0.0, {'error': 'Position size below minimum after step flooring'}

        # 9. Calculer le risque réel en pourcentage
        actual_risk_amount = position_size * risk_per_unit
        actual_risk_pct = (actual_risk_amount / account_balance) * 100 if account_balance > 0 else 0

        # Si le risque réel dépasse la limite de sécurité
        max_allowed_risk_pct = min(rm.MAX_DAILY_LOSS_PCT, max(3.0, rm.RISK_PCT * 2.0))
        if actual_risk_pct > max_allowed_risk_pct:
            if position_size <= min_size:
                log.warning(
                    f"Risque réel de {actual_risk_pct:.2f}% dépasse la limite autorisée de {max_allowed_risk_pct:.2f}% "
                    f"pour {symbol} (taille minimale de contrat trop grande pour la taille du compte). Trade rejeté."
                )
                return 0.0, {'error': 'Risk too high for account size due to contract minimums'}
            else:
                # Capper la taille pour respecter la limite
                log.info(f"Capping de la taille de position de {position_size:.6f} à la limite de risque de {max_allowed_risk_pct:.2f}%")
                position_size = (max_allowed_risk_pct / 100.0) * account_balance / risk_per_unit
                if step_size is not None and step_size > 0:
                    position_size = math.floor(position_size / step_size) * step_size
                    position_size = round(position_size, 8)
                actual_risk_amount = position_size * risk_per_unit
                actual_risk_pct = (actual_risk_amount / account_balance) * 100 if account_balance > 0 else 0

        # Détails du calcul pour le logging et le débogage
        details = {
            'account_balance': account_balance,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'risk_per_unit': risk_per_unit,
            'price_risk': price_risk,
            'base_risk_pct': risk_pct * 100,
            'sentiment_factor': sentiment_factor,
            'correlation_adjustment': correlation_adjustment,
            'kelly_fraction': kelly_fraction,
            'adjusted_risk_pct': adjusted_risk_pct * 100,
            'position_size': position_size,
            'actual_risk_amount': actual_risk_amount,
            'actual_risk_pct': actual_risk_pct,
            'free_margin': free_margin,
            'leverage': leverage,
            'max_size_by_margin': max_size_by_margin,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        position_size = float(position_size)
        actual_risk_pct = float(actual_risk_pct)
        log.info(f"Taille de position calculée pour {symbol}: {position_size:.6f} | Risque: {actual_risk_pct:.2f}% du compte")
        return position_size, details

    except Exception as e:
        log.error(f"Erreur lors du calcul de la taille de position pour {symbol}: {e}")
        return 0.0, {'error': str(e)}

def _calculate_kelly_fraction(rm) -> Optional[float]:
    """
    Calcule la fraction de Kelly basée sur l'historique des trades.
    Utilise une approche plus robuste avec gestion des cas extrêmes.

    Returns:
        Fraction de Kelly (0 à 1) ou None si pas assez de données
    """
    # Verrou partagé avec record_trade pour une lecture cohérente de trade_history.
    with rm._history_lock:
        return _calculate_kelly_fraction_impl(rm)


def _calculate_kelly_fraction_impl(rm) -> Optional[float]:
    if len(rm.trade_history) < rm.MIN_TRADES_FOR_KELLY:
        return None

    try:
        # Filtrer uniquement les trades CLÔTURÉS avec un P&L valide
        trades_with_pnl = [t for t in rm.trade_history if t.get('pnl') is not None and t.get('status') == 'closed']

        # Pas assez de trades clôturés pour Kelly
        if len(trades_with_pnl) < rm.MIN_TRADES_FOR_KELLY:
            log.debug(f"Pas assez de trades clôturés pour Kelly: {len(trades_with_pnl)}/{rm.MIN_TRADES_FOR_KELLY}")
            return None

        # Séparer gagnants et perdants uniquement sur les trades avec P&L valide
        winning_trades = [t for t in trades_with_pnl if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades_with_pnl if t.get('pnl', 0) <= 0]

        if len(winning_trades) == 0 or len(losing_trades) == 0:
            log.debug(f"Kelly: winning={len(winning_trades)}, losing={len(losing_trades)} - impossible de calculer")
            return None

        # Calculer le win rate sur les trades clôturés uniquement
        win_rate = len(winning_trades) / len(trades_with_pnl)

        # Extraire les R-Multiples (PnL / Risque Initial)
        wins_r = []
        for t in winning_trades:
            pnl = t.get('pnl', 0)
            # Tenter de trouver le risque initial
            initial_risk = t.get('initial_risk_amount')
            if not initial_risk:
                entry = t.get('entry_price', 0)
                sl = t.get('stop_loss', 0)
                size = t.get('size', 1)
                if entry > 0 and sl > 0 and entry != sl:
                    initial_risk = abs(entry - sl) * size
            # Fallback empirique pour les vieux trades: on assume que les gains sont de ~1.5 R
            if not initial_risk or initial_risk <= 0:
                initial_risk = abs(pnl) / 1.5

            wins_r.append(pnl / initial_risk)

        losses_r = []
        for t in losing_trades:
            pnl = abs(t.get('pnl', 0))
            initial_risk = t.get('initial_risk_amount')
            if not initial_risk:
                entry = t.get('entry_price', 0)
                sl = t.get('stop_loss', 0)
                size = t.get('size', 1)
                if entry > 0 and sl > 0 and entry != sl:
                    initial_risk = abs(entry - sl) * size
            # Fallback empirique: on assume qu'une perte correspond à 1 R complet
            if not initial_risk or initial_risk <= 0:
                initial_risk = abs(pnl)

            losses_r.append(pnl / initial_risk)

        if not wins_r or not losses_r:
            log.debug(f"Kelly: pas de données R-Multiples valides pour le calcul")
            return None

        # Utiliser la médiane des R-Multiples pour réduire l'impact des valeurs aberrantes
        avg_win = np.median(wins_r) if wins_r else 0
        avg_loss = np.median(losses_r) if losses_r else 0

        if avg_loss == 0:
            log.debug("Kelly: avg_loss = 0, impossible de calculer")
            return None

        # Ratio gain/perte
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        if win_loss_ratio <= 0:
            log.debug(f"Kelly: win_loss_ratio={win_loss_ratio} <= 0")
            return None

        # Formule de Kelly: f* = (bp - q) / b
        # où b = ratio gain/perte, p = probabilité de gain, q = probabilité de perte (1-p)
        kelly_fraction = (win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio

        # Appliquer une fraction de Kelly conservatrice pour éviter l'over-betting
        # Utiliser la moitié de Kelly pour réduire la volatilité
        conservative_kelly = kelly_fraction * 0.5

        # Kelly peut être négatif (pas d'avantage) ou trop élevé, on le borne
        kelly_fraction = max(0.0, min(conservative_kelly, 0.5))  # Maximum 50% (Kelly conservateur)

        log.debug(f"Kelly calculé: win_rate={win_rate:.2%}, win_loss_ratio={win_loss_ratio:.2f}, kelly_raw={kelly_fraction*2:.2%}, kelly_final={kelly_fraction:.2%}")
        return kelly_fraction

    except KeyError as e:
        log.error(f"Erreur KeyError lors du calcul de la fraction de Kelly: clé manquante {e} - Vérifiez que tous les trades ont un champ 'pnl'")
        return None
    except Exception as e:
        log.error(f"Erreur lors du calcul de la fraction de Kelly: {e}")
        return None