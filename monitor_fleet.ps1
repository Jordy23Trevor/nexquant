$scratchDir = "C:\Users\Pavillon\.gemini\antigravity\brain\e74f4141-811c-45fb-a2f2-327653312a06\scratch"
if (-not (Test-Path $scratchDir)) {
    New-Item -ItemType Directory -Path $scratchDir -Force | Out-Null
}
$statusFile = Join-Path $scratchDir "monitor_status.txt"
$logDir = "c:\Users\Pavillon\Desktop\nexquant_v2\nexquant\superbot\logs"

"--- FLEET MONITORING STARTED AT $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ---`r`n" | Out-File $statusFile -Encoding utf8

$duration = 1800 # 30 minutes
$interval = 30 # Check every 30 seconds
$steps = $duration / $interval

for ($step = 1; $step -le $steps; $step++) {
    Start-Sleep -Seconds $interval
    
    $currentTime = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    
    # Check running processes
    $processes = Get-Process -Name "python" -ErrorAction SilentlyContinue
    $pythonCount = 0
    if ($processes) {
        $pythonCount = $processes.Count
    }
    
    # Check log files
    $alpacaLog = Join-Path $logDir "superbot_alpaca.log"
    $binanceLog = Join-Path $logDir "superbot_binance.log"
    $mt5Log = Join-Path $logDir "superbot_mt5.log"
    
    # Get last lines of logs
    $alpacaTail = "No log file found"
    $binanceTail = "No log file found"
    $mt5Tail = "No log file found"
    
    if (Test-Path $alpacaLog) { 
        $alpacaTail = (Get-Content $alpacaLog -Tail 1) -join " "
    }
    if (Test-Path $binanceLog) { 
        $binanceTail = (Get-Content $binanceLog -Tail 1) -join " "
    }
    if (Test-Path $mt5Log) { 
        $mt5Tail = (Get-Content $mt5Log -Tail 1) -join " "
    }
    
    $statusText = "[$currentTime] Step $step/$steps | Active Python Processes: $pythonCount`r`n"
    $statusText += "  Alpaca: $alpacaTail`r`n"
    $statusText += "  Binance: $binanceTail`r`n"
    $statusText += "  MT5: $mt5Tail`r`n"
    $statusText += "----------------------------------------`r`n"
    
    $statusText | Out-File $statusFile -Append -Encoding utf8
}

"--- FLEET MONITORING COMPLETED AT $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ---`r`n" | Out-File $statusFile -Append -Encoding utf8