import logging

log = logging.getLogger("crypto_filters")

def check_crypto_volume(symbol: str, df_with_indicators) -> bool:
    """
    Vérifie que le volume de la bougie actuelle est suffisant par rapport à la moyenne mobile 
    (protection contre le slippage sur des actifs illiquides).
    """
    last_bar = df_with_indicators.iloc[-1]
    volume = float(last_bar.get('volume', 0))
    volume_ma = float(last_bar.get('volume_ma', 0))
    
    # Rejeter si le volume de la bougie est inférieur à 20% de la moyenne mobile de volume
    if volume_ma > 0 and volume < volume_ma * 0.20:
        log.info(f"🚨 Volume insuffisant pour {symbol} ({volume:.0f} < 20% de {volume_ma:.0f}) — risque de slippage, trade rejeté")
        return False
    return True
