import logging

log = logging.getLogger("adaptive_params")

def get_recent_win_rate(bot) -> float:
    """
    Calcule le taux de victoire sur les 20 derniers trades CLÔTURÉS.
    Returns:
        Taux de victoire entre 0.0 et 1.0, ou 0.0 si pas assez de trades.
    """
    # Filtrer uniquement les trades clôturés avec P&L valide
    closed_trades = [t for t in bot.risk_manager.trade_history if t.get('status') == 'closed' and t.get('pnl') is not None]

    if not closed_trades:
        return 0.0

    recent = closed_trades[-20:]
    if not recent:
        return 0.0

    winning = sum(1 for t in recent if t.get('pnl', 0) > 0)
    return winning / len(recent)


def update_adaptive_parameters(bot):
    """
    Ajuste les paramètres de risque et de score en fonction de la performance récente.
    """
    if len(bot.risk_manager.trade_history) < 5:
        return  # Pas assez de données pour ajuster

    # Guard : ne pas ajuster si aucun trade n'est clôturé (win_rate=0.0 par défaut serait trompeur)
    closed_trades = [t for t in bot.risk_manager.trade_history if t.get('status') == 'closed' and t.get('pnl') is not None]
    if len(closed_trades) < 5:
        log.debug(f"Adaptation ignorée : seulement {len(closed_trades)} trade(s) clôturé(s), minimum 5 requis.")
        return

    recent_win_rate = get_recent_win_rate(bot)
    log.debug(f"Taux de victoire récent (20 derniers trades) : {recent_win_rate:.2f}")

    # Seuils d'ajustement
    if recent_win_rate > 0.6:
        # Performance bonne : augmenter légèrement le risque et abaisser le seuil de score
        old_risk = bot.adaptive_risk_pct
        old_score = bot.adaptive_score_min
        bot.adaptive_risk_pct = min(bot.adaptive_risk_pct * 1.05, 2.5)  # max 2.5%
        bot.adaptive_score_min = max(bot.adaptive_score_min - 0.5, 2.0)  # min 2.0
        if old_risk != bot.adaptive_risk_pct or old_score != bot.adaptive_score_min:
            log.info(f"Adaptation paramètres : risque {old_risk:.2f}% -> {bot.adaptive_risk_pct:.2f}%, score min {old_score:.1f} -> {bot.adaptive_score_min:.1f}")
    elif recent_win_rate < 0.4:
        # Performance mauvaise : réduire le risque et augmenter le seuil de score
        old_risk = bot.adaptive_risk_pct
        old_score = bot.adaptive_score_min
        bot.adaptive_risk_pct = max(bot.adaptive_risk_pct * 0.95, 0.5)  # min 0.5%
        bot.adaptive_score_min = min(bot.adaptive_score_min + 0.5, 8.0)  # max 8.0
        if old_risk != bot.adaptive_risk_pct or old_score != bot.adaptive_score_min:
            log.info(f"Adaptation paramètres : risque {old_risk:.2f}% -> {bot.adaptive_risk_pct:.2f}%, score min {old_score:.1f} -> {bot.adaptive_score_min:.1f}")
    # else: garder les paramètres actuels
