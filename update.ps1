 = 'c:\Users\Pavillon\Desktop\nexquant_v2\nexquant\.env'
 = Get-Content  -Raw

$content = $content -replace '(?m)^MAX_DAILY_LOSS_PCT=2\.0.*\r?\nMAX_MONTHLY_LOSS_PCT=5\.0.*\r?\nMAX_DAILY_LOSS_PCT=2\.0.*\r?\nMAX_MONTHLY_LOSS_PCT=5\.0.*\r?\nMAX_OPEN_POSITIONS=3.*\r?\nMAX_OPEN_POSITIONS_MT5=3.*\r?\nMAX_OPEN_POSITIONS=5.*\r?\nMAX_OPEN_POSITIONS_MT5=5.*', "MAX_DAILY_LOSS_PCT=2.0 # % max perte journalière avant arrêt
MAX_MONTHLY_LOSS_PCT=5.0 # % max perte mensuelle avant arrêt
MAX_OPEN_POSITIONS=3   # Nombre max de positions simultanées (fallback)
MAX_OPEN_POSITIONS_MT5=3 # 3 positions max pour MT5"

$content = $content -replace '(?m)^TRAIL_ATR_MULT=2\.0.*\r?\nBE_ATR_MULT=1\.5.*\r?\nTRAIL_ATR_MULT=1\.8.*\r?\nBE_ATR_MULT=1\.2.*', "TRAIL_ATR_MULT=1.8
BE_ATR_MULT=1.2"

$content = $content -replace '(?m)^SCORE_MIN=6', 'SCORE_MIN=8'
$content = $content -replace '(?m)^TSMOM_PLACE_ORDERS=true\r?\nTSMOM_PLACE_ORDERS=false', 'TSMOM_PLACE_ORDERS=false'
$content = $content -replace '(?m)^INSTRUMENTS_MT5=.*', 'WEEKDAY_INSTRUMENTS=EURUSD,GBPUSD,USDJPY,XAUUSD,XAGUSD'

Set-Content  $content

 = 'c:\Users\Pavillon\Desktop\nexquant_v2\nexquant\superbot\config.py'
 = Get-Content  -Raw
$content = $content -replace '(?m)^MAX_OPEN_POSITIONS = int\(os\.getenv\("MAX_OPEN_POSITIONS", "6"\)\)  # Max concurrent positions across fleet\r?\nMAX_OPEN_POSITIONS = int\(os\.getenv\("MAX_OPEN_POSITIONS", "5"\)\)  # Max concurrent positions across fleet', "MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))  # Max concurrent positions across fleet"

$content = $content -replace '(?s)    if not \(0\.5 <= MAX_DAILY_LOSS_PCT <= 15\.0\):  # V3: élargi à 15% pour stratégies x10\s*errors\.append\(f"MAX_DAILY_LOSS_PCT \(\{MAX_DAILY_LOSS_PCT\}%\) est hors limites\. Il doit être compris entre 0\.5% et 15\.0% pour protéger le capital\."\)\s*if ENABLE_LOSS_LIMIT:\s*if not \(0\.5 <= MAX_DAILY_LOSS_PCT <= 15\.0\):  # V3: élargi à 15% pour stratégies x10\s*errors\.append\(f"MAX_DAILY_LOSS_PCT \(\{MAX_DAILY_LOSS_PCT\}%\) est hors limites\. Il doit être compris entre 0\.5% et 15\.0% pour protéger le capital\."\)', "    if ENABLE_LOSS_LIMIT:
        if not (0.5 <= MAX_DAILY_LOSS_PCT <= 15.0):  # V3: élargi à 15% pour stratégies x10
            errors.append(f"MAX_DAILY_LOSS_PCT ({MAX_DAILY_LOSS_PCT}%) est hors limites. Il doit être compris entre 0.5% et 15.0% pour protéger le capital.")"

$content = $content -replace '(?s)    if not \(1\.0 <= MAX_MONTHLY_LOSS_PCT <= 20\.0\):\s*errors\.append\(f"MAX_MONTHLY_LOSS_PCT \(\{MAX_MONTHLY_LOSS_PCT\}%\) doit être compris entre 1\.0% et 20\.0%\."\)\s*if not \(1\.0 <= MAX_MONTHLY_LOSS_PCT <= 20\.0\):\s*errors\.append\(f"MAX_MONTHLY_LOSS_PCT \(\{MAX_MONTHLY_LOSS_PCT\}%\) doit être compris entre 1\.0% et 20\.0%\."\)', "    if not (1.0 <= MAX_MONTHLY_LOSS_PCT <= 20.0):
        errors.append(f"MAX_MONTHLY_LOSS_PCT ({MAX_MONTHLY_LOSS_PCT}%) doit être compris entre 1.0% et 20.0%.")"

$content = $content -replace '(?m)^    "RISK_PCT", "SL_ATR_MULT", "TP_ATR_MULT", "TRAIL_ATR_MULT", "TRAIL_ACTIVATE_ATR_MULT", "BE_ATR_MULT",\r?\n    "ENABLE_LOSS_LIMIT", "RISK_PCT", "SL_ATR_MULT", "TP_ATR_MULT", "TRAIL_ATR_MULT", "TRAIL_ACTIVATE_ATR_MULT", "BE_ATR_MULT",', "    "ENABLE_LOSS_LIMIT", "RISK_PCT", "SL_ATR_MULT", "TP_ATR_MULT", "TRAIL_ATR_MULT", "TRAIL_ACTIVATE_ATR_MULT", "BE_ATR_MULT","

$content = $content -replace '(?m)^    "DAILY_TARGET_EUR", "SESSION_AWARE", "TRADING_MODE",\r?\n    "DAILY_TARGET_EUR", "SESSION_TARGET_EQUITY_MIN", "SESSION_TARGET_EQUITY_MAX", "SESSION_AWARE", "TRADING_MODE",', "    "DAILY_TARGET_EUR", "SESSION_TARGET_EQUITY_MIN", "SESSION_TARGET_EQUITY_MAX", "SESSION_AWARE", "TRADING_MODE","

Set-Content  $content

 = 'c:\Users\Pavillon\Desktop\nexquant_v2\nexquant\superbot\brain\session_manager.py'
 = Get-Content  -Raw
$content = $content -replace '(?s)        "description": "Pré-London \(préparation, faible liquidité\)",\s*"liquidity": "low",\s*"score_multiplier": 1\.1,      # \+10% score requis\s*"max_positions_ratio": 0\.5,   # 50% des positions max\s*"risk_multiplier": 0\.7,       # -30% de risque\s*"priority_assets": \["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"\],\s*"pnl_target_pct": 0\.10,       # 10% de l''objectif journalier\s*"description": "Pré-London \(préparation, momentum pré-ouverture\)",', "        "description": "Pré-London (préparation, momentum pré-ouverture)","
Set-Content  $content
