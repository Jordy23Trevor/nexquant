"""Configuration de test partagée.

L'ancien `pytest.ini` s'appuyait sur le plugin `pytest-env` (`env = BROKER_TYPE=paper`),
qui n'est pas installé : l'option était ignorée (warning « Unknown config option: env »)
et le code n'était de toute façon jamais exécuté. De plus, « paper » n'est pas un type
de broker valide ici (`binance`, `alpaca`, `mt5`) — le mode « sûr » est `BACKTEST_MODE`,
qui court-circuite la validation des identifiants broker dans `superbot.config`.

On l'active ici avant tout import de `superbot.config`, pour que la suite ne dépende
jamais des clés API / identifiants MT5 du `.env` et ne puisse pas toucher un broker live.
"""

import os

os.environ["BACKTEST_MODE"] = "true"
