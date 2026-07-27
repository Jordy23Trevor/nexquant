@echo off
echo ===================================================
echo 🚀 Lancement de la flotte NexQuant SuperBot
echo ===================================================
echo.
echo Lancement du Bot Crypto (Binance)...
start "NexQuant Crypto (Binance)" cmd /k "set PYTHONPATH=. && python superbot/main.py --broker binance --dashboard-port 5000 --webhook-port 9000"

echo Lancement du Bot Forex (MT5)...
start "NexQuant Forex (MT5)" cmd /k "set PYTHONPATH=. && python superbot/main.py --broker mt5 --dashboard-port 5001 --webhook-port 9001"

echo Lancement du Bot ETF (Alpaca)...
start "NexQuant ETF (Alpaca)" cmd /k "set PYTHONPATH=. && python superbot/main.py --broker alpaca --dashboard-port 5002 --webhook-port 9002"

echo.
echo ===================================================
echo ✅ Les 3 sessions ont ete lancees dans des fenetres separees !
echo - Dashboard Crypto : http://localhost:5000
echo - Dashboard Forex  : http://localhost:5001
echo - Dashboard ETF    : http://localhost:5002
echo ===================================================
pause
