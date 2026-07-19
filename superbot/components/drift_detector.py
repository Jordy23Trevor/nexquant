import logging

log = logging.getLogger("drift_detector")

def detect_model_drift(bot):
    """
    Détecte une éventuelle dérive du modèle en surveillant le taux de victoire récent.
    Si le taux de victoire chute de manière significative, un avertissement est enregistré.
    """
    # Filtrer uniquement les trades CLÔTURÉS avec P&L valide
    closed_trades = [t for t in bot.risk_manager.trade_history if t.get('status') == 'closed' and t.get('pnl') is not None]

    if len(closed_trades) < 10:
        return  # Pas assez de données pour détecter une dérive

    # Calculer le taux de victoire sur les 10 derniers trades clôturés
    recent = closed_trades[-10:]
    winning = sum(1 for t in recent if t.get('pnl', 0) > 0)
    win_rate = winning / len(recent) if recent else 0.0

    # Seuil d'alerte : taux de victoire inférieur à 30% sur les 10 derniers trades
    if win_rate < 0.3:
        log.warning(f"⚠️ Dérive du modèle détectée : taux de victoire récent ({win_rate:.2f}) inférieur au seuil critique de 0.30")
