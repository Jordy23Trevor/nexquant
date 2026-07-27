"""
Dashboard de monitoring pour SuperBot Trading Unifié.
Fournit une interface web moderne et dynamique pour visualiser les métriques, positions et performance du bot en temps réel.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

log = logging.getLogger("dashboard")


def load_global_trades():
    import glob
    folders_to_try = [
        "superbot/logs",
        "../logs",
        os.path.join(os.path.dirname(__file__), "..", "logs"),
        os.path.join(os.path.dirname(__file__), "logs")
    ]
    
    trades_files = []
    # Scanner trades_*.jsonl
    for folder in folders_to_try:
        if os.path.exists(folder):
            pattern = os.path.join(folder, "trades_*.jsonl")
            for f in glob.glob(pattern):
                if f not in trades_files:
                    trades_files.append(f)
            # Ajouter trades.jsonl historique
            h_file = os.path.join(folder, "trades.jsonl")
            if os.path.exists(h_file) and h_file not in trades_files:
                trades_files.append(h_file)

    if not trades_files:
        return [], []

    raw_trades = []
    for trades_file in trades_files:
        try:
            with open(trades_file, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    if line.strip():
                        try:
                            trade_data = json.loads(line)
                            # Si le broker n'est pas spécifié, l'inférer du nom du fichier
                            if 'broker' not in trade_data:
                                basename = os.path.basename(trades_file)
                                if basename.startswith("trades_") and basename.endswith(".jsonl"):
                                    broker_name = basename[7:-6]
                                    trade_data['broker'] = broker_name
                            raw_trades.append(trade_data)
                        except Exception:
                            continue
        except Exception as e:
            log.error(f"Erreur lors de la lecture de {trades_file} : {e}")

    # Dédupliquer les trades pour éviter d'afficher le même trade en double (ex: s'il est présent dans trades.jsonl et trades_*.jsonl)
    seen_trades = set()
    deduped_trades = []
    for t in raw_trades:
        ts = t.get('timestamp', '')
        if isinstance(ts, str) and 'T' in ts:
            ts = ts.split('.')[0]
        
        pnl = t.get('pnl')
        pnl_val = round(float(pnl), 4) if pnl is not None else None
        
        entry = t.get('entry_price')
        entry_val = round(float(entry), 4) if entry is not None else None
        
        qty = t.get('qty') or t.get('size')
        qty_val = round(float(qty), 6) if qty is not None else None
        
        key = (
            t.get('symbol'),
            t.get('side'),
            t.get('status'),
            ts,
            pnl_val,
            entry_val,
            qty_val
        )
        if key not in seen_trades:
            seen_trades.add(key)
            deduped_trades.append(t)
    raw_trades = deduped_trades

    # Trier par timestamp pour reconstruire l'état correctement
    from datetime import timezone as _tz
    def parse_time(t):
        ts = t.get('timestamp')
        if not ts:
            return datetime.min.replace(tzinfo=_tz.utc)
        try:
            import dateutil.parser
            dt = dateutil.parser.parse(str(ts))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_tz.utc)
            return dt
        except Exception:
            return datetime.min.replace(tzinfo=_tz.utc)

    raw_trades.sort(key=parse_time)

    active_positions = {}
    closed_history = []
    # Seuil : un trade ouvert de plus de 24h sans clôture est considéré orphelin
    from datetime import timezone as _tz
    now_utc = datetime.now(_tz.utc)
    ORPHAN_THRESHOLD_HOURS = 24

    def infer_broker(symbol):
        sym = symbol.upper()
        crypto_keywords = ["USDT", "BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOT", "LINK"]
        if any(kw in sym for kw in crypto_keywords):
            return "binance"
        stock_keywords = ["SPY", "QQQ", "AAPL", "TSLA", "MSFT"]
        if any(kw in sym for kw in stock_keywords):
            return "alpaca"
        return "mt5"

    def is_orphan(t):
        """Retourne True si le trade 'ouvert' date de plus de ORPHAN_THRESHOLD_HOURS heures."""
        ts_raw = t.get('timestamp')
        if not ts_raw:
            return True
        try:
            from datetime import datetime as _dt
            ts_str = str(ts_raw)
            # Tenter parse avec timezone
            try:
                import dateutil.parser
                ts = dateutil.parser.parse(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=_tz.utc)
            except Exception:
                # Fallback : parse sans timezone
                ts_clean = ts_str.split('+')[0].split('Z')[0].strip()
                ts = _dt.fromisoformat(ts_clean).replace(tzinfo=_tz.utc)
            age_hours = (now_utc - ts).total_seconds() / 3600
            return age_hours > ORPHAN_THRESHOLD_HOURS
        except Exception:
            return True  # En cas d'erreur de parsing, considérer comme orphelin

    for t in raw_trades:
        symbol = t.get('symbol')
        if not symbol:
            continue
        
        if 'broker' not in t:
            t['broker'] = infer_broker(symbol)
            
        if t.get('status') == 'closed':
            closed_history.append(t)
            key = (symbol, t.get('side'))
            if key in active_positions:
                del active_positions[key]
        else:
            # Filtrer les trades orphelins (ouverts mais trop anciens sans PnL)
            if is_orphan(t):
                # Les traiter comme fermés sans PnL connu plutôt que de les afficher "en cours"
                t_closed = dict(t)
                t_closed['status'] = 'closed'
                t_closed['pnl'] = t.get('pnl')  # None si pas de PnL
                if t_closed.get('pnl') is not None:
                    closed_history.append(t_closed)
                # Ne pas les ajouter dans active_positions
            else:
                key = (symbol, t.get('side'))
                active_positions[key] = t

    return closed_history, list(active_positions.values())


class DashboardHandler(BaseHTTPRequestHandler):
    """Gestionnaire HTTP pour le dashboard."""

    def __init__(self, *args, dashboard_data_func = None, **kwargs):
        self.dashboard_data_func = dashboard_data_func
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Traite les requêtes GET."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)

        try:
            if path == '/' or path == '/index.html':
                self._serve_dashboard()
            elif path == '/api/data':
                self._serve_api_data()
            elif path == '/api/logs':
                self._serve_api_logs()
            elif path == '/health':
                self._serve_health()
            else:
                self.send_error(404, "Not found")
        except Exception as e:
            log.error(f"Erreur lors du traitement de la requête dashboard: {e}")
            self.send_error(500, "Internal server error")

    def _serve_dashboard(self):
        """Sert la page principale du dashboard."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        html_content = self._generate_dashboard_html()
        self.wfile.write(html_content.encode('utf-8'))

    def _serve_api_data(self):
        """Sert les données du dashboard en format JSON."""
        if self.dashboard_data_func:
            try:
                raw_data = self.dashboard_data_func()
                
                # Mapper les données brutes de main.py au format attendu par le JS du dashboard
                data = raw_data
                if isinstance(raw_data, dict) and ('stats' in raw_data or 'account' in raw_data):
                    stats = raw_data.get('stats', {})
                    account = raw_data.get('account', {})
                    risk_metrics = raw_data.get('risk_metrics', {})
                    news_sentiment = raw_data.get('news_sentiment', {})
                    positions = raw_data.get('positions', {})
                    
                    total_trades = stats.get('total_trades', 0)
                    win_trades = stats.get('win_trades', 0)
                    win_rate = (win_trades / total_trades) if total_trades > 0 else 0.0

                    bot_running = stats.get('running', True)

                    global_closed, global_active = load_global_trades()

                    data = {
                        'timestamp': raw_data.get('timestamp', datetime.now().isoformat()),
                        'bot': {
                            'running': bot_running,
                            'uptime_seconds': stats.get('uptime_seconds', 0),
                            'start_time': stats.get('start_time')
                        },
                        'performance': {
                            'initial_balance': account.get('initial_balance') or 10000.0,
                            'current_balance': account.get('balance') or account.get('equity') or 10000.0,
                            'total_pnl':       account.get('pnl', 0.0) or 0.0,
                            'unrealized_pnl':  account.get('unrealized_pnl', 0.0) or 0.0,
                            'drawdown_pct':    risk_metrics.get('drawdown_pct', 0.0) or 0.0,
                            'win_rate':        win_rate,
                            'profit_factor':   risk_metrics.get('profit_factor', 1.0) or 1.0,
                            'broker':          account.get('broker', raw_data.get('broker_type', '')),
                            'account_type':    account.get('account_type', 'PAPER'),
                        },
                        'risk': {
                            'current_risk_pct': risk_metrics.get('current_risk_pct', 0.0) or 0.0,
                            'open_positions_count': len(positions),
                            'max_daily_trades': risk_metrics.get('max_daily_trades', 'N/A') or 'N/A',
                            'kelly_fraction': risk_metrics.get('kelly_fraction'),
                            'sentiment_factor': risk_metrics.get('sentiment_factor', 1.0) or 1.0
                        },
                        'positions': positions,
                        'stats': stats,
                        'history': raw_data.get('history', []),
                        'global_history': global_closed,
                        'global_active': global_active,
                        'market_data': raw_data.get('market_data', {}),
                        'broker_type': raw_data.get('broker_type', ''),
                        'asset_type': raw_data.get('asset_type', 'crypto'),
                        'news': {
                            'overall_score': news_sentiment.get('overall', {}).get('score', 0.0) or 0.0,
                            'confidence': news_sentiment.get('overall', {}).get('confidence', 0.0) or 0.0,
                            'fear_greed_value': news_sentiment.get('fear_greed', {}).get('value'),
                            'avoidance_active': news_sentiment.get('avoidance_active', False),
                            'recent_high_impact_count': news_sentiment.get('recent_high_impact_count', 0),
                            'recent_events': news_sentiment.get('recent_events', [])
                        }
                    }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                self.wfile.write(json.dumps(data, default=str).encode('utf-8'))
            except Exception as e:
                log.error(f"Erreur lors de la génération des données dashboard: {e}")
                self.send_error(500, "Internal server error")
        else:
            self.send_error(503, "Service unavailable")

    def _serve_api_logs(self):
        """Sert les dernières lignes du fichier de log."""
        paths_to_try = [
            "superbot/logs/superbot.log",
            "../logs/superbot.log",
            os.path.join(os.path.dirname(__file__), "..", "logs", "superbot.log"),
            os.path.join(os.path.dirname(__file__), "logs", "superbot.log")
        ]
        log_file = None
        for p in paths_to_try:
            if os.path.exists(p):
                log_file = p
                break
                
        content = ""
        if log_file and os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    last_lines = lines[-150:] if len(lines) > 150 else lines
                    content = "".join(last_lines)
            except Exception as e:
                content = f"Erreur lors de la lecture des logs : {e}"
        else:
            content = "En attente du fichier de log système..."
            
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def _serve_health(self):
        """Sert un endpoint de health check simple."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        health_data = {
            "status": "healthy",
            "service": "SuperBot Dashboard",
            "timestamp": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(health_data).encode('utf-8'))

    def _generate_dashboard_html(self) -> str:
        """Génère le HTML du dashboard."""
        return """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>NexQuant — Crypto & Trading Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<script>
  if (typeof ApexCharts === 'undefined') {
    document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/apexcharts/3.41.0/apexcharts.min.js"><' + '/script>');
  }
</script>
<script>
  if (typeof ApexCharts === 'undefined') {
    document.write('<script src="https://unpkg.com/apexcharts"><' + '/script>');
  }
</script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg: #070913;
  --surface: #0a0e1a;
  --card: rgba(16, 22, 41, 0.75);
  --card-hover: rgba(22, 30, 56, 0.85);
  --border: rgba(255, 255, 255, 0.05);
  --border-focus: rgba(255, 255, 255, 0.12);
  --txt: #f3f4f6;
  --txt-secondary: #9ca3af;
  --txt-muted: #4b5563;
  --accent-cyan: #06b6d4;
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --green: #10b981;
  --red: #ef4444;
  --amber: #f59e0b;
  --radius-lg: 16px;
  --radius-md: 10px;
  --radius-sm: 6px;
  --glow-cyan: 0 0 20px rgba(6, 182, 212, 0.15);
  --glow-green: 0 0 20px rgba(16, 185, 129, 0.15);
}

.light-theme {
  --bg: #f3f4f6;
  --surface: #ffffff;
  --card: rgba(243, 244, 246, 0.8);
  --card-hover: rgba(229, 231, 235, 0.9);
  --border: rgba(0, 0, 0, 0.08);
  --border-focus: rgba(0, 0, 0, 0.15);
  --txt: #111827;
  --txt-secondary: #4b5563;
  --txt-muted: #9ca3af;
  --glow-cyan: 0 0 20px rgba(6, 182, 212, 0.05);
  --glow-green: 0 0 20px rgba(16, 185, 129, 0.05);
}

html,body{
  height:100%;
  background: var(--bg);
  color: var(--txt);
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  transition: background-color 0.3s, color 0.3s;
}

a{color:inherit;text-decoration:none}

/* Layout */
.layout{
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* Sidebar */
.sidebar{
  width: 250px;
  min-width: 250px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  flex-shrink: 0;
}

.sidebar-brand{
  padding: 24px;
  border-bottom: 1px solid var(--border);
}

.brand-logo{
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark{
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: var(--glow-cyan);
}

.brand-mark i{
  font-size: 16px;
  color: #fff;
}

.brand-name{
  font-family: 'Outfit', sans-serif;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--txt);
}

.brand-tag{
  font-size: 10px;
  color: var(--txt-secondary);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 600;
}

.sidebar-nav{
  flex: 1;
  padding: 24px 16px;
  overflow-y: auto;
}

.nav-label{
  font-size: 10px;
  color: var(--txt-muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 8px 12px 6px;
  font-weight: 700;
}

.nav-item{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  margin-bottom: 4px;
  color: var(--txt-secondary);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.nav-item:hover{
  background: var(--border);
  color: var(--txt);
}

.nav-item.active{
  background: linear-gradient(90deg, rgba(6, 182, 212, 0.12) 0%, rgba(59, 130, 246, 0.04) 100%);
  color: var(--accent-cyan);
  border-left: 3px solid var(--accent-cyan);
  padding-left: 9px;
  font-weight: 600;
}

.nav-item i{
  font-size: 16px;
  width: 20px;
  text-align: center;
  transition: transform 0.2s;
}

.nav-item:hover i{
  transform: translateX(2px);
}

.sidebar-footer{
  padding: 20px 16px;
  border-top: 1px solid var(--border);
}

/* Status Badge */
.status-badge{
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  backdrop-filter: blur(5px);
}

.status-dot{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--txt-muted);
  flex-shrink: 0;
}

.status-dot.live{
  background: var(--green);
  box-shadow: 0 0 10px var(--green);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.status-info{
  flex: 1;
  min-width: 0;
}

.status-label{
  font-size: 11px;
  color: var(--txt-secondary);
  font-weight: 500;
}

.status-val{
  font-size: 12px;
  font-weight: 600;
  color: var(--txt);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Main */
.main{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Topbar */
.topbar{
  height: 64px;
  min-height: 64px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  gap: 24px;
}

.search-container {
  position: relative;
  flex: 1;
  max-width: 400px;
}

.search-container i {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--txt-muted);
  font-size: 14px;
}

.search-input {
  width: 100%;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 8px 16px 8px 40px;
  color: var(--txt);
  font-size: 13px;
  outline: none;
  transition: all 0.2s;
}

.search-input:focus {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.1);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-left: auto;
}

.theme-toggle, .settings-btn {
  background: none;
  border: none;
  color: var(--txt-secondary);
  font-size: 18px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.theme-toggle:hover, .settings-btn:hover {
  background: var(--border);
  color: var(--txt);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
}

.top-pill{
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 12px;
  color: var(--txt-secondary);
}

.top-pill .dot{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--txt-muted);
}

.top-pill .dot.green{
  background: var(--green);
}

.clock{
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--txt-secondary);
  letter-spacing: 0.04em;
  font-weight: 500;
}

/* Content Area */
.content{
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Panels */
.panel{display:none}
.panel.active{display:flex; flex-direction:column; gap:24px}

/* Grid System */
.dashboard-grid {
  display: grid;
  grid-template-columns: 3fr 1fr;
  gap: 24px;
}

.left-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.right-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.balance-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sparkline-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

/* Cards */
.card {
  background: var(--card);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  width: 100%;
  max-width: 100%;
}

.card:hover {
  background: var(--card-hover);
  border-color: var(--border-focus);
}

/* Sparkline Card */
.sparkline-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
}

.spark-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.spark-symbol {
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.spark-symbol i {
  color: #f59e0b;
}

.spark-symbol.eth i {
  color: #8b5cf6;
}

.spark-symbol.bnb i {
  color: #f59e0b;
}

.spark-change {
  font-size: 12px;
  font-weight: 600;
}

.spark-change.up { color: var(--green); }
.spark-change.down { color: var(--red); }

.spark-body {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.spark-price {
  font-family: 'Outfit', sans-serif;
  font-size: 18px;
  font-weight: 700;
}

.spark-chart-mini {
  width: 80px;
  height: 30px;
}

/* Balance Widget */
.balance-widget {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.balance-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.balance-tabs {
  display: flex;
  gap: 8px;
}

.balance-tab {
  background: var(--border);
  border: none;
  color: var(--txt-secondary);
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 600;
}

.balance-tab.active {
  background: var(--accent-cyan);
  color: #070913;
}

.balance-currency {
  font-size: 12px;
  color: var(--txt-secondary);
  border: 1px solid var(--border);
  padding: 2px 8px;
  border-radius: 4px;
}

.balance-value-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.balance-amount {
  font-family: 'Outfit', sans-serif;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.balance-pnl-pct {
  font-size: 14px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.balance-pnl-pct.up {
  background: rgba(16, 185, 129, 0.1);
  color: var(--green);
}
.balance-pnl-pct.down {
  background: rgba(239, 68, 68, 0.1);
  color: var(--red);
}

.balance-subtitle {
  font-size: 12px;
  color: var(--txt-secondary);
}

/* Two-column sub-grid */
.widget-row-2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

/* Metrics widgets */
.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.metric-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--txt-secondary);
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}

.metric-item:last-child {
  border-bottom: none;
}

.metric-item-name {
  font-size: 13px;
  color: var(--txt-secondary);
}

.metric-item-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
}

/* Account Info Widget */
.account-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.action-btn {
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px;
  color: var(--txt);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--border-focus);
  border-color: var(--accent-cyan);
}

.action-btn i {
  font-size: 14px;
  color: var(--accent-cyan);
}

/* Exchange Widget */
.exchange-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-group {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-wrapper {
  display: flex;
  flex-direction: column;
}

.input-label {
  font-size: 11px;
  color: var(--txt-secondary);
}

.input-val {
  background: none;
  border: none;
  color: var(--txt);
  font-family: 'Outfit', sans-serif;
  font-size: 18px;
  font-weight: 600;
  outline: none;
  width: 120px;
}

.token-select {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--txt);
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  cursor: pointer;
}

.exchange-arrow-container {
  display: flex;
  justify-content: center;
  margin: -10px 0;
  z-index: 2;
}

.exchange-arrow-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--accent-cyan);
  color: #070913;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.exchange-submit {
  width: 100%;
  background: var(--accent-cyan);
  color: #070913;
  border: none;
  border-radius: var(--radius-md);
  padding: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.exchange-submit:hover {
  box-shadow: var(--glow-cyan);
}

/* Profit Loss Card */
.pnl-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pnl-metric {
  font-family: 'Outfit', sans-serif;
  font-size: 24px;
  font-weight: 700;
}

.pnl-badge {
  font-size: 10px;
  font-weight: 700;
  background: rgba(6, 182, 212, 0.1);
  color: var(--accent-cyan);
  padding: 3px 8px;
  border-radius: 10px;
}

.pnl-progress-container {
  margin-top: 14px;
  display: flex;
  gap: 16px;
}

.pnl-prog-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pnl-prog-lbl {
  font-size: 11px;
  color: var(--txt-secondary);
}

.pnl-prog-val {
  font-size: 13px;
  font-weight: 600;
}

.pnl-prog-bar {
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}

.pnl-prog-fill {
  height: 100%;
  background: var(--accent-blue);
  border-radius: 2px;
}

.pnl-prog-fill.green { background: var(--green); }
.pnl-prog-fill.red { background: var(--red); }

/* Apex chart styling */
.chart-card-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-title {
  font-family: 'Outfit', sans-serif;
  font-size: 14px;
  font-weight: 600;
}

.chart-tabs {
  display: flex;
  gap: 4px;
}

.chart-tab {
  background: var(--border);
  border: 1px solid var(--border);
  color: var(--txt-secondary);
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
}

.chart-tab.active {
  background: var(--accent-cyan);
  color: #070913;
  border-color: var(--accent-cyan);
}

#nexchart {
  min-height: 290px;
}

/* My Assets Grid */
.assets-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.asset-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.asset-box-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--txt-secondary);
}

.asset-box-hd.up { color: var(--green); }
.asset-box-hd.down { color: var(--red); }

.asset-box-val {
  font-family: 'Outfit', sans-serif;
  font-size: 15px;
  font-weight: 700;
  margin-top: 4px;
}

/* Tables */
.tbl-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

thead th {
  text-align: left;
  padding: 10px 12px;
  font-size: 10px;
  font-weight: 700;
  color: var(--txt-secondary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--border);
}

tbody td {
  padding: 12px;
  border-bottom: 1px solid var(--border);
  color: var(--txt-secondary);
  vertical-align: middle;
}

tbody tr:last-child td {
  border-bottom: none;
}

tbody tr:hover td {
  background: rgba(255, 255, 255, 0.01);
  color: var(--txt);
}

td.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

td.pos { color: var(--green); font-weight: 600; }
td.neg { color: var(--red); font-weight: 600; }
td.name { color: var(--txt); font-weight: 600; }

/* Badges */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.badge-long { background: rgba(16, 185, 129, 0.12); color: var(--green); }
.badge-short { background: rgba(239, 68, 68, 0.12); color: var(--red); }
.badge-neutral { background: rgba(59, 130, 246, 0.12); color: var(--accent-blue); }

/* Transactions list */
.tx-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tx-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--surface);
  border: 1px solid var(--border);
}

.tx-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tx-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.tx-icon.receive { background: rgba(16, 185, 129, 0.1); color: var(--green); }
.tx-icon.send { background: rgba(239, 68, 68, 0.1); color: var(--red); }
.tx-icon.swap { background: rgba(6, 182, 212, 0.1); color: var(--accent-cyan); }

.tx-details {
  display: flex;
  flex-direction: column;
}

.tx-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--txt);
}

.tx-time {
  font-size: 10px;
  color: var(--txt-muted);
}

.tx-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.tx-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 700;
  color: var(--txt);
}

.tx-status {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
}

.tx-status.success { color: var(--green); }
.tx-status.pending { color: var(--amber); }

/* Leaderboard */
.lead-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}

.lead-item:last-child {
  border-bottom: none;
}

.lead-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.lead-rank-icon {
  font-size: 14px;
  color: var(--amber);
}

.lead-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--txt);
}

.lead-val {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.lead-volume {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
}

.lead-pct {
  font-size: 10px;
  font-weight: 600;
}

.lead-pct.up { color: var(--green); }
.lead-pct.down { color: var(--red); }

/* Empty state */
.empty{
  padding: 40px 20px;
  text-align: center;
  color: var(--txt-secondary);
  font-size: 13px;
}

/* Log view */
.log-area{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #d1d5db;
  max-height: 480px;
  height: 480px;
  overflow-y: auto;
  line-height: 1.6;
  white-space: pre-wrap;
}

.log-warn{
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
  margin-bottom: 2px;
}

.log-err{
  color: #f87171;
  background: rgba(239, 110, 110, 0.08);
  padding: 2px 4px;
  border-radius: 3px;
  margin-bottom: 2px;
  font-weight: 600;
}

.log-info{
  color: #9ca3af;
  margin-bottom: 2px;
}

/* Scrollbars */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.08);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,0.15)}

/* Modal styling */
.modal {
  display: none;
  position: fixed;
  z-index: 100;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  max-width: 400px;
  width: 90%;
  text-align: center;
  box-shadow: 0 20px 50px rgba(0,0,0,0.5);
  animation: modalOpen 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalOpen {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.modal-icon {
  font-size: 48px;
  color: var(--green);
  margin-bottom: 16px;
}

.modal-title {
  font-family: 'Outfit', sans-serif;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 12px;
}

.modal-desc {
  color: var(--txt-secondary);
  font-size: 13px;
  margin-bottom: 20px;
}

.modal-btn {
  background: var(--accent-cyan);
  color: #070913;
  border: none;
  border-radius: var(--radius-md);
  padding: 10px 24px;
  font-weight: 700;
  cursor: pointer;
}

/* Mobile Toggle & Responsive Styles */
.mobile-menu-toggle {
  display: none;
  background: none;
  border: none;
  color: var(--txt);
  font-size: 20px;
  cursor: pointer;
  padding: 8px;
  border-radius: var(--radius-sm);
  align-items: center;
  justify-content: center;
  margin-right: 12px;
}
.mobile-menu-toggle:hover {
  background: var(--border);
}

.sidebar-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(7, 9, 19, 0.6);
  backdrop-filter: blur(4px);
  z-index: 99;
  transition: opacity 0.3s ease;
}

@media (max-width: 1024px) {
  .mobile-menu-toggle {
    display: flex;
  }
  
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    z-index: 100;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }
  
  .sidebar.open {
    transform: translateX(0);
    box-shadow: 10px 0 30px rgba(0, 0, 0, 0.5);
  }
  
  .sidebar-overlay.open {
    display: block;
  }
  
  .topbar {
    padding: 0 16px;
  }
  
  .content {
    padding: 16px;
  }
  
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  
  .balance-header-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .sparkline-row {
    width: 100%;
    grid-template-columns: 1fr;
  }
  
  .search-container {
    max-width: 200px;
  }
}

@media (max-width: 640px) {
  .search-container {
    display: none; /* Hide search bar on very small devices to keep topbar clean */
  }
  
  .sparkline-row {
    grid-template-columns: 1fr;
  }
  
  .topbar-actions {
    gap: 8px;
  }
  
  .top-pill {
    padding: 4px 8px;
    font-size: 10px;
  }
  
  .clock {
    display: none; /* Hide clock to save space */
  }
}
.balance-currency-btn:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  border-color: rgba(255, 255, 255, 0.15) !important;
  color: var(--txt) !important;
}
.currency-option:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--txt) !important;
}
</style>
</head>
<body>
<div class="layout">
  <div class="sidebar-overlay" id="sidebar-overlay" onclick="toggleSidebar()"></div>

  <!-- ─── Sidebar ─────────────────────────── -->
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="brand-logo">
        <div class="brand-mark">
          <i class="fa-solid fa-chart-line"></i>
        </div>
        <div>
          <div class="brand-name">NexQuant</div>
          <div class="brand-tag">Trading Intelligence</div>
        </div>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-label">Tableau de bord</div>
      <div class="nav-item active" onclick="showPanel('overview')">
        <i class="fa-solid fa-shapes"></i>
        <span>Vue d'ensemble</span>
      </div>
      <div class="nav-item" onclick="showPanel('positions')">
        <i class="fa-solid fa-briefcase"></i>
        <span>Positions</span>
      </div>
      <div class="nav-item" onclick="showPanel('risk')">
        <i class="fa-solid fa-shield-halved"></i>
        <span>Gestion du Risque</span>
      </div>
      <div class="nav-label">Analyse & Logs</div>
      <div class="nav-item" onclick="showPanel('news')">
        <i class="fa-solid fa-newspaper"></i>
        <span>Actualités</span>
      </div>
      <div class="nav-item" onclick="showPanel('logs')">
        <i class="fa-solid fa-terminal"></i>
        <span>Journaux système</span>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="status-badge">
        <div class="status-dot" id="sb-dot"></div>
        <div class="status-info">
          <div class="status-label">Moteur de trading</div>
          <div class="status-val" id="sb-status">—</div>
          <div class="status-label" style="margin-top:2px" id="sb-uptime"><i class="fa-regular fa-clock"></i> 0h 00m</div>
        </div>
      </div>
    </div>
  </aside>

  <!-- ─── Main Content ─────────────────────────────── -->
  <div class="main">
    <header class="topbar">
      <button class="mobile-menu-toggle" onclick="toggleSidebar()" aria-label="Toggle Menu">
        <i class="fa-solid fa-bars"></i>
      </button>
      <div class="topbar-actions">
        <div class="top-pill">
          <div class="dot green" id="api-dot"></div>
          <span id="api-sync">Synchronisation...</span>
        </div>
        <div class="clock" id="tb-clock">—</div>
        <button class="theme-toggle" onclick="toggleTheme()" title="Changer le thème">
          <i class="fa-solid fa-moon" id="theme-icon"></i>
        </button>
        <div class="user-profile">
          <div class="user-avatar">NQ</div>
        </div>
      </div>
    </header>

    <div class="content">

      <!-- ═══ OVERVIEW ═══════════════════════════════════════════ -->
      <div class="panel active" id="panel-overview">
        
        <div class="balance-header-row">
          <div class="balance-widget">
            <div class="balance-title-row" style="display: flex; align-items: center; gap: 12px;">
              <div class="balance-subtitle">Solde Total du Portefeuille</div>
              <!-- Currency selector dropdown -->
              <div class="balance-currency-container" style="position: relative; display: inline-block;">
                <button class="balance-currency-btn" id="currency-dropdown-btn" onclick="toggleCurrencyDropdown()" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border); color: var(--txt-secondary); padding: 4px 10px; border-radius: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; transition: all 0.2s;">
                  <span id="active-currency-label">USD</span> <i class="fa-solid fa-chevron-down" style="font-size:8px;"></i>
                </button>
                <div class="balance-currency-menu" id="currency-menu" style="display: none; position: absolute; top: 100%; left: 0; margin-top: 6px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: 0 10px 25px rgba(0,0,0,0.5); z-index: 50; min-width: 100px; padding: 4px 0;">
                  <div class="currency-option" onclick="selectCurrency('USD')" style="padding: 8px 12px; font-size: 11px; cursor: pointer; color: var(--txt); transition: background 0.2s; text-align: left;">USD ($)</div>
                  <div class="currency-option" onclick="selectCurrency('EUR')" style="padding: 8px 12px; font-size: 11px; cursor: pointer; color: var(--txt-secondary); transition: background 0.2s; text-align: left;">EUR (€)</div>
                  <div class="currency-option" onclick="selectCurrency('BTC')" style="padding: 8px 12px; font-size: 11px; cursor: pointer; color: var(--txt-secondary); transition: background 0.2s; text-align: left;">BTC (₿)</div>
                </div>
              </div>
            </div>
            <div class="balance-value-row">
              <div class="balance-amount" id="kpi-balance">—</div>
              <div class="balance-pnl-pct up" id="kpi-pnl-pct">+0.00%</div>
            </div>
            <div class="balance-subtitle">Solde Initial : <strong id="kpi-init">—</strong> &nbsp;|&nbsp; Courtier actif : <strong id="tb-broker">—</strong></div>
          </div>

          <!-- Top Sparklines -->
          <div class="sparkline-row" id="top-sparklines-container">
            <div class="empty">Chargement des sparklines...</div>
          </div>
        </div>

        <!-- Dashboard Grid Layout -->
        <div class="dashboard-grid">
          
          <!-- Left Main Column -->
          <div class="left-column">

            <!-- Chart Card -->
            <div class="card">
              <div class="chart-card-hd">
                <div class="chart-title"><i class="fa-solid fa-chart-area"></i> Graphique en direct du marché</div>
                <div style="display:flex; gap: 12px; align-items:center;">
                  <div id="sym-tabs" class="chart-tabs"></div>
                  <div class="chart-tabs">
                    <button class="chart-tab active" id="ct-area" onclick="setChartType('area')">Aire</button>
                    <button class="chart-tab" id="ct-candle" onclick="setChartType('candlestick')">Bougies</button>
                  </div>
                </div>
              </div>
              <div class="chart-body">
                <div id="nexchart"><div class="empty">Initialisation du graphique...</div></div>
              </div>
            </div>

            <!-- Recent Signals & Trades Table -->
            <div class="card">
              <div class="chart-card-hd" style="flex-wrap: wrap; gap: 10px;">
                <div class="chart-title"><i class="fa-solid fa-list"></i> Signaux récents &amp; Historique de trading</div>
                <div style="display: flex; gap: 8px;">
                  <!-- Type Filter -->
                  <select id="filter-type" class="token-select" onchange="resetHistoryPageAndRender()" style="padding: 4px 10px; font-size: 11px; height: auto; outline: none; border-color: var(--border);">
                    <option value="all">Tous les Statuts</option>
                    <option value="active">En Cours</option>
                    <option value="closed">Clôturés</option>
                  </select>
                  <!-- Broker Filter -->
                  <select id="filter-broker" class="token-select" onchange="resetHistoryPageAndRender()" style="padding: 4px 10px; font-size: 11px; height: auto; outline: none; border-color: var(--border);">
                    <option value="all">Tous les Brokers</option>
                    <option value="binance">Binance (Crypto)</option>
                    <option value="alpaca">Alpaca (ETF)</option>
                    <option value="mt5">MT5 (Forex)</option>
                  </select>
                </div>
              </div>
              <div class="tbl-wrap">
                <table id="signals-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Actif</th>
                      <th>Type</th>
                      <th>Prix d'entrée</th>
                      <th>Stop Loss</th>
                      <th>Take Profit</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr><td colspan="7" class="empty">Aucun signal récent détecté</td></tr>
                  </tbody>
                </table>
              </div>
              <div id="history-pagination" class="chart-tabs" style="margin: 16px; justify-content: flex-end; align-items: center; gap: 6px;"></div>
            </div>

          </div>

          <!-- Right Sidebar Column -->
          <div class="right-column">
            
            <!-- Trading account card with real broker balance -->
            <div class="card">
              <div class="metric-header">
                <span class="metric-title"><i class="fa-solid fa-wallet"></i> Compte de Trading</span>
              </div>
              <div class="metric-item">
                <span class="metric-item-name"><i class="fa-solid fa-shield"></i> Solde total du portefeuille</span>
                <span class="metric-item-value" id="sub-acc-balance">—</span>
              </div>
            </div>

            <!-- Profit / Loss Widget -->
            <div class="card">
              <div class="metric-header">
                <span class="metric-title"><i class="fa-solid fa-receipt"></i> Performance Profit/Perte</span>
                <span class="pnl-badge"><i class="fa-solid fa-heart-shield"></i> Risque faible</span>
              </div>
              <div class="pnl-row">
                <span class="pnl-metric id" id="overview-pnl-raw">$0.00</span>
              </div>
              <div class="pnl-progress-container">
                <div class="pnl-prog-item">
                  <div class="pnl-prog-lbl">Ratio gains (Win Rate)</div>
                  <div class="pnl-prog-val" id="wr-val">0%</div>
                  <div class="pnl-prog-bar"><div class="pnl-prog-fill green" id="wr-bar" style="width: 0%"></div></div>
                </div>
                <div class="pnl-prog-item">
                  <div class="pnl-prog-lbl">Facteur profit</div>
                  <div class="pnl-prog-val" id="pf-val">0.00</div>
                  <div class="pnl-prog-bar"><div class="pnl-prog-fill" id="pf-bar" style="width: 0%"></div></div>
                </div>
              </div>
            </div>

            <!-- My Assets List -->
            <div class="card" id="my-assets-card">
              <div class="empty">Chargement des actifs...</div>
            </div>

            <!-- Leaderboard -->
            <div class="card" id="leaderboard-card">
              <div class="empty">Chargement du classement...</div>
            </div>

          </div>

        </div>

      </div><!-- /overview -->

      <!-- ═══ POSITIONS ══════════════════════════════════════════ -->
      <div class="panel" id="panel-positions">
        <div class="balance-header-row">
          <div>
            <h2 class="brand-name"><i class="fa-solid fa-briefcase"></i> Positions ouvertes</h2>
            <div class="balance-subtitle">Suivi en direct des trades actifs sur les marchés de contrats à terme.</div>
          </div>
        </div>
        
        <div class="card" style="padding:0">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>Symbole</th><th>Sens</th><th>Quantité</th>
                  <th>Entrée</th><th>Actuel</th><th>Liquidation</th><th>P&amp;L non réalisé</th>
                  <th>Stop loss</th><th>Take profit</th>
                </tr>
              </thead>
              <tbody id="pos-tbody"><tr><td colspan="9" class="empty">Aucune position ouverte</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- ═══ RISK ════════════════════════════════════════════════ -->
      <div class="panel" id="panel-risk">
        <div class="balance-header-row">
          <div>
            <h2 class="brand-name"><i class="fa-solid fa-shield-halved"></i> Métriques de Gestion du Risque</h2>
            <div class="balance-subtitle">Règles des 2% d'Elder, calcul de taille dynamique Kelly et protection du capital.</div>
          </div>
        </div>

        <div class="sparkline-row">
          <div class="card sparkline-card">
            <span class="status-label"><i class="fa-solid fa-percent"></i> Risque total courant</span>
            <div class="spark-price" id="r-risk">0.00 %</div>
            <span class="status-label" style="font-size:10px;">Cumulé sur toutes les positions</span>
          </div>
          <div class="card sparkline-card">
            <span class="status-label"><i class="fa-solid fa-calculator"></i> Taille de Kelly conseillée</span>
            <div class="spark-price" id="r-kelly">N/A</div>
            <span class="status-label" style="font-size:10px;">Fraction de Kelly active (25%)</span>
          </div>
          <div class="card sparkline-card">
            <span class="status-label"><i class="fa-solid fa-circle-exclamation"></i> Limite Drawdown</span>
            <div class="spark-price" id="r-dd">0.00 %</div>
            <div class="pnl-prog-bar" style="margin-top:6px;"><div class="pnl-prog-fill red" id="r-dd-bar" style="width: 0%"></div></div>
          </div>
        </div>

        <div class="widget-row-2">
          <div class="card">
            <div class="metric-header"><span class="metric-title">Paramètres de sécurité actifs</span></div>
            <div class="metric-item"><span class="metric-item-name">Max positions simultanées</span><span class="metric-item-value" id="r-maxpos">3</span></div>
            <div class="metric-item"><span class="metric-item-name">Perte max quotidienne</span><span class="metric-item-value">3.00 %</span></div>
            <div class="metric-item"><span class="metric-item-name">Perte max mensuelle</span><span class="metric-item-value">6.00 %</span></div>
            <div class="metric-item"><span class="metric-item-name">Nombre de positions actives</span><span class="metric-item-value" id="r-active-pos">0</span></div>
          </div>
          
          <div class="card">
            <div class="metric-header"><span class="metric-title">Configuration ATR (Volatility)</span></div>
            <div class="metric-item"><span class="metric-item-name">Multiplicateur Stop Loss</span><span class="metric-item-value">1.50 ATR</span></div>
            <div class="metric-item"><span class="metric-item-name">Multiplicateur Take Profit</span><span class="metric-item-value">3.00 ATR</span></div>
            <div class="metric-item"><span class="metric-item-name">Trailing Stop</span><span class="metric-item-value">1.00 ATR</span></div>
            <div class="metric-item"><span class="metric-item-name">Break-Even Trigger</span><span class="metric-item-value">1.00 ATR</span></div>
          </div>
        </div>
      </div>

      <!-- ═══ NEWS ════════════════════════════════════════════════ -->
      <div class="panel" id="panel-news">
        <div class="balance-header-row">
          <div>
            <h2 class="brand-name"><i class="fa-solid fa-newspaper"></i> Sentiments &amp; Actualités Marché</h2>
            <div class="balance-subtitle">Scores récoltés sur l'actualité crypto/finance et indices globaux.</div>
          </div>
        </div>

        <div class="widget-row-2">
          <div class="card">
            <div class="metric-header"><span class="metric-title"><i class="fa-solid fa-gauge"></i> Indice Fear &amp; Greed</span></div>
            <div class="spark-price" id="s-fg">—</div>
            <div class="pnl-prog-bar" style="margin-top:12px; height: 6px;"><div class="pnl-prog-fill green" id="s-fg-bar" style="width: 0%"></div></div>
            <div class="balance-subtitle" style="margin-top:8px;" id="s-fg-label">—</div>
          </div>
          <div class="card">
            <div class="metric-header"><span class="metric-title"><i class="fa-solid fa-chart-line"></i> Métriques globales de sentiment</span></div>
            <div class="metric-item"><span class="metric-item-name">Score de sentiment global</span><span class="metric-item-value" id="s-score">—</span></div>
            <div class="metric-item"><span class="metric-item-name">Indice de confiance</span><span class="metric-item-value" id="s-conf">—</span></div>
            <div class="metric-item"><span class="metric-item-name">Évitement de nouvelles</span><span class="metric-item-value" id="s-avoid">—</span></div>
          </div>
        </div>

        <div class="card">
          <div class="metric-header"><span class="metric-title">Actualités à fort impact récentes</span></div>
          <div class="empty" id="news-body">Chargement des actualités...</div>
        </div>
      </div>

      <!-- ═══ LOGS ════════════════════════════════════════════════ -->
      <div class="panel" id="panel-logs">
        <div class="balance-header-row">
          <div>
            <h2 class="brand-name"><i class="fa-solid fa-terminal"></i> Journaux système</h2>
            <div class="balance-subtitle">Fichier de log système du robot de trading en temps réel (`superbot.log`).</div>
          </div>
          <button class="action-btn" onclick="fetchLogs()" style="flex-direction:row; padding: 6px 12px; gap: 8px;"><i class="fa-solid fa-arrows-rotate"></i> Rafraîchir</button>
        </div>
        <div class="log-area" id="log-area">En attente des journaux...</div>
      </div>

    </div><!-- /content -->
  </div><!-- /main -->
</div><!-- /layout -->

<script>
let selectedCurrency = 'USD';
const EXCHANGE_RATES = { USD: 1.0, EUR: 0.92 };
let lastBalanceUsd = null;
let lastInitUsd = null;
let lastBtcPrice = 67000.0;
let latestAssetType = 'crypto';
let latestData = null;
let currentHistoryPage = 1;
const itemsPerPage = 10;

function getCurrencyPrefix() {
  if (selectedCurrency === 'USD') return '$';
  if (selectedCurrency === 'EUR') return '€';
  if (selectedCurrency === 'BTC') return '₿';
  return '';
}
function getDecimals() {
  if (latestAssetType === 'forex') return 5;
  return 2;
}
function getRate() {
  if (selectedCurrency === 'USD') return 1.0;
  if (selectedCurrency === 'EUR') return EXCHANGE_RATES.EUR;
  if (selectedCurrency === 'BTC') return 1.0 / lastBtcPrice;
  return 1.0;
}

function updateDynamicWidgets(assetType, marketData) {
  const sparkContainer = document.getElementById('top-sparklines-container');
  const assetsCard = document.getElementById('my-assets-card');
  const leadCard = document.getElementById('leaderboard-card');

  if (!sparkContainer || !assetsCard || !leadCard) return;

  const symbols = Object.keys(marketData);
  let sparkHTML = '';
  let assetsHTML = `<div class="metric-header"><span class="metric-title"><i class="fa-solid fa-coins"></i> Mes Actifs</span></div><div class="assets-grid">`;
  let leadHTML = `<div class="metric-header"><span class="metric-title"><i class="fa-solid fa-ranking-star"></i> Classement des signaux</span></div>`;

  if (assetType === 'forex') {
    const forexItems = [
      { sym: 'EUR/USD', name: 'Euro / US Dollar', icon: 'fa-euro-sign', colorClass: '' },
      { sym: 'GBP/USD', name: 'Pound / US Dollar', icon: 'fa-sterling-sign', colorClass: 'eth' },
      { sym: 'USD/JPY', name: 'US Dollar / Yen', icon: 'fa-yen-sign', colorClass: 'bnb' }
    ];

    forexItems.forEach((item, index) => {
      const data = marketData[item.sym] || marketData[item.sym.replace('/', '')] || [];
      let priceStr = '—';
      let changeStr = '0.00%';
      let changeClass = 'up';
      let lastPrice = 0;
      let prevPrice = 0;

      if (data.length > 0) {
        lastPrice = parseFloat(data[data.length - 1].c);
        priceStr = fmt(lastPrice, 5);
        if (data.length > 1) {
          prevPrice = parseFloat(data[data.length - 2].c);
          const pct = ((lastPrice - prevPrice) / prevPrice) * 100;
          changeStr = (pct >= 0 ? '+' : '') + fmt(pct, 2) + '%';
          changeClass = pct >= 0 ? 'up' : 'down';
        }
      }

      sparkHTML += `
        <div class="card sparkline-card">
          <div class="spark-header">
            <span class="spark-symbol ${item.colorClass}"><i class="fa-solid ${item.icon}"></i> ${item.sym}</span>
            <span class="spark-change ${changeClass}">${changeStr}</span>
          </div>
          <div class="spark-body">
            <span class="spark-price">${getCurrencyPrefix()}${priceStr}</span>
            <div class="spark-chart-mini" id="spark-mini-${index}"></div>
          </div>
        </div>`;

      const allocatedBalance = (lastBalanceUsd || 10000.0) / 4;
      assetsHTML += `
        <div class="asset-box">
          <div class="asset-box-hd ${changeClass}">${item.sym.split('/')[0]} <span style="font-size:9px;">${changeStr}</span></div>
          <div class="asset-box-val">${getCurrencyPrefix()}${fmt(allocatedBalance * getRate(), 0)}</div>
        </div>`;

      const leadIcons = ['fa-trophy', 'fa-award', 'fa-award'];
      const leadColorStyle = index === 0 ? '' : index === 1 ? 'color:var(--txt-secondary);' : 'color:var(--txt-muted);';
      leadHTML += `
        <div class="lead-item">
          <div class="lead-left">
            <i class="fa-solid ${leadIcons[index]} lead-rank-icon" style="${leadColorStyle}"></i>
            <span class="lead-name">${item.sym} Grid</span>
          </div>
          <div class="lead-val">
            <span class="lead-volume">Vol. N/A</span>
            <span class="lead-pct ${changeClass}">${changeStr}</span>
          </div>
        </div>`;
    });

  } else if (assetType === 'stock' || assetType === 'stocks' || assetType === 'equity') {
    const stockItems = [
      { sym: 'SPY', name: 'S&P 500 ETF', icon: 'fa-chart-line', colorClass: '' },
      { sym: 'AAPL', name: 'Apple Inc.', icon: 'fa-apple', iconBrand: true, colorClass: 'eth' },
      { sym: 'TSLA', name: 'Tesla Inc.', icon: 'fa-car-side', colorClass: 'bnb' }
    ];

    stockItems.forEach((item, index) => {
      const data = marketData[item.sym] || [];
      let priceStr = '—';
      let changeStr = '0.00%';
      let changeClass = 'up';
      let lastPrice = 0;
      let prevPrice = 0;

      if (data.length > 0) {
        lastPrice = parseFloat(data[data.length - 1].c);
        priceStr = fmt(lastPrice, 2);
        if (data.length > 1) {
          prevPrice = parseFloat(data[data.length - 2].c);
          const pct = ((lastPrice - prevPrice) / prevPrice) * 100;
          changeStr = (pct >= 0 ? '+' : '') + fmt(pct, 2) + '%';
          changeClass = pct >= 0 ? 'up' : 'down';
        }
      }

      const iconHTML = item.iconBrand ? `<i class="fa-brands ${item.icon}"></i>` : `<i class="fa-solid ${item.icon}"></i>`;
      sparkHTML += `
        <div class="card sparkline-card">
          <div class="spark-header">
            <span class="spark-symbol ${item.colorClass}">${iconHTML} ${item.sym}</span>
            <span class="spark-change ${changeClass}">${changeStr}</span>
          </div>
          <div class="spark-body">
            <span class="spark-price">${getCurrencyPrefix()}${priceStr}</span>
            <div class="spark-chart-mini" id="spark-mini-${index}"></div>
          </div>
        </div>`;

      const allocatedBalance = (lastBalanceUsd || 10000.0) / 4;
      assetsHTML += `
        <div class="asset-box">
          <div class="asset-box-hd ${changeClass}">${item.sym} <span style="font-size:9px;">${changeStr}</span></div>
          <div class="asset-box-val">${getCurrencyPrefix()}${fmt(allocatedBalance * getRate(), 0)}</div>
        </div>`;

      const leadIcons = ['fa-trophy', 'fa-award', 'fa-award'];
      const leadColorStyle = index === 0 ? '' : index === 1 ? 'color:var(--txt-secondary);' : 'color:var(--txt-muted);';
      leadHTML += `
        <div class="lead-item">
          <div class="lead-left">
            <i class="fa-solid ${leadIcons[index]} lead-rank-icon" style="${leadColorStyle}"></i>
            <span class="lead-name">${item.sym} Momentum</span>
          </div>
          <div class="lead-val">
            <span class="lead-volume">Vol. N/A</span>
            <span class="lead-pct ${changeClass}">${changeStr}</span>
          </div>
        </div>`;
    });

  } else {
    const cryptoItems = [
      { sym: 'BTC/USDT', name: 'Bitcoin', icon: 'fa-bitcoin', iconBrand: true, colorClass: '' },
      { sym: 'ETH/USDT', name: 'Ethereum', icon: 'fa-ethereum', iconBrand: true, colorClass: 'eth' },
      { sym: 'BNB/USDT', name: 'Binance Coin', icon: 'fa-coins', colorClass: 'bnb' }
    ];

    cryptoItems.forEach((item, index) => {
      const data = marketData[item.sym] || [];
      let priceStr = '—';
      let changeStr = '0.00%';
      let changeClass = 'up';
      let lastPrice = 0;
      let prevPrice = 0;

      if (data.length > 0) {
        lastPrice = parseFloat(data[data.length - 1].c);
        priceStr = fmt(lastPrice, 2);
        if (data.length > 1) {
          prevPrice = parseFloat(data[data.length - 2].c);
          const pct = ((lastPrice - prevPrice) / prevPrice) * 100;
          changeStr = (pct >= 0 ? '+' : '') + fmt(pct, 2) + '%';
          changeClass = pct >= 0 ? 'up' : 'down';
        }
      }

      const iconHTML = item.iconBrand ? `<i class="fa-brands ${item.icon}"></i>` : `<i class="fa-solid ${item.icon}"></i>`;
      sparkHTML += `
        <div class="card sparkline-card">
          <div class="spark-header">
            <span class="spark-symbol ${item.colorClass}">${iconHTML} ${item.sym.replace('/USDT', '')}</span>
            <span class="spark-change ${changeClass}">${changeStr}</span>
          </div>
          <div class="spark-body">
            <span class="spark-price">${getCurrencyPrefix()}${priceStr}</span>
            <div class="spark-chart-mini" id="spark-mini-${index}"></div>
          </div>
        </div>`;

      const allocatedBalance = (lastBalanceUsd || 10000.0) / 4;
      assetsHTML += `
        <div class="asset-box">
          <div class="asset-box-hd ${changeClass}">${item.sym.split('/')[0]} <span style="font-size:9px;">${changeStr}</span></div>
          <div class="asset-box-val">${getCurrencyPrefix()}${fmt(allocatedBalance * getRate(), 0)}</div>
        </div>`;

      const leadIcons = ['fa-trophy', 'fa-award', 'fa-award'];
      const leadColorStyle = index === 0 ? '' : index === 1 ? 'color:var(--txt-secondary);' : 'color:var(--txt-muted);';
      leadHTML += `
        <div class="lead-item">
          <div class="lead-left">
            <i class="fa-solid ${leadIcons[index]} lead-rank-icon" style="${leadColorStyle}"></i>
            <span class="lead-name">${item.sym.replace('/USDT', '')} Trend</span>
          </div>
          <div class="lead-val">
            <span class="lead-volume">Vol. N/A</span>
            <span class="lead-pct ${changeClass}">${changeStr}</span>
          </div>
        </div>`;
    });
  }

  assetsHTML += `</div>`;
  sparkContainer.innerHTML = sparkHTML;
  assetsCard.innerHTML = assetsHTML;
  leadCard.innerHTML = leadHTML;

  if (assetType === 'forex') {
    const items = ['EUR/USD', 'GBP/USD', 'USD/JPY'];
    items.forEach((sym, index) => {
      const data = marketData[sym] || marketData[sym.replace('/', '')] || [];
      if (data.length > 0) {
        const prices = data.slice(-10).map(c => parseFloat(c.c));
        const color = prices[prices.length - 1] >= prices[0] ? '#10b981' : '#ef4444';
        renderSparkline(`spark-mini-${index}`, color, prices);
      }
    });
  } else if (assetType === 'stock' || assetType === 'stocks' || assetType === 'equity') {
    const items = ['SPY', 'AAPL', 'TSLA'];
    items.forEach((sym, index) => {
      const data = marketData[sym] || [];
      if (data.length > 0) {
        const prices = data.slice(-10).map(c => parseFloat(c.c));
        const color = prices[prices.length - 1] >= prices[0] ? '#10b981' : '#ef4444';
        renderSparkline(`spark-mini-${index}`, color, prices);
      }
    });
  } else {
    const items = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'];
    items.forEach((sym, index) => {
      const data = marketData[sym] || [];
      if (data.length > 0) {
        const prices = data.slice(-10).map(c => parseFloat(c.c));
        const color = prices[prices.length - 1] >= prices[0] ? '#10b981' : '#ef4444';
        renderSparkline(`spark-mini-${index}`, color, prices);
      }
    });
  }
}

function toggleCurrencyDropdown() {
  const menu = document.getElementById('currency-menu');
  if (menu) {
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
  }
}

window.addEventListener('click', function(e) {
  const btn = document.getElementById('currency-dropdown-btn');
  const menu = document.getElementById('currency-menu');
  if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
    menu.style.display = 'none';
  }
});

function selectCurrency(curr) {
  selectedCurrency = curr;
  document.getElementById('active-currency-label').textContent = curr;
  document.getElementById('currency-menu').style.display = 'none';
  
  const options = document.querySelectorAll('.currency-option');
  options.forEach(opt => {
    if (opt.textContent.startsWith(curr)) {
      opt.style.color = 'var(--txt)';
      opt.style.fontWeight = '600';
    } else {
      opt.style.color = 'var(--txt-secondary)';
      opt.style.fontWeight = 'normal';
    }
  });
  
  updateBalanceDisplay();
}

function updateBalanceDisplay() {
  // Afficher 0 si pas encore de données plutôt que de ne rien afficher
  if (lastBalanceUsd === null) {
    setEl('kpi-balance', '$0.00');
    setEl('kpi-init', '$0.00');
    setEl('sub-acc-balance', '$0.00');
    return;
  }
  
  // Essayer d'extraire le prix du BTC depuis cachedData s'il est disponible
  if (cachedData && cachedData['BTC/USDT'] && cachedData['BTC/USDT'].length) {
    const lastCandle = cachedData['BTC/USDT'][cachedData['BTC/USDT'].length - 1];
    if (lastCandle && lastCandle.y && lastCandle.y[3]) {
      lastBtcPrice = parseFloat(lastCandle.y[3]);
    }
  }
  
  let formattedBal = '';
  let formattedInit = '';
  let formattedSubBal = '';
  
  if (selectedCurrency === 'USD') {
    formattedBal = '$' + fmt(lastBalanceUsd);
    formattedInit = '$' + fmt(lastInitUsd);
    formattedSubBal = '$' + fmt(lastBalanceUsd);
  } else if (selectedCurrency === 'EUR') {
    const rate = EXCHANGE_RATES.EUR;
    formattedBal = '€' + fmt(lastBalanceUsd * rate);
    formattedInit = '€' + fmt(lastInitUsd * rate);
    formattedSubBal = '€' + fmt(lastBalanceUsd * rate);
  } else if (selectedCurrency === 'BTC') {
    const btcBal = lastBalanceUsd / lastBtcPrice;
    const btcInit = lastInitUsd / lastBtcPrice;
    formattedBal = '₿' + fmt(btcBal, 5);
    formattedInit = '₿' + fmt(btcInit, 5);
    formattedSubBal = '₿' + fmt(btcBal, 5);
  }
  
  setEl('kpi-balance', formattedBal);
  setEl('kpi-init', formattedInit);
  setEl('sub-acc-balance', formattedSubBal);
}

// ─── Nav ──────────────────────────────────────────────────────────────────
const PANELS = ['overview','positions','risk','news','logs'];
function showPanel(id) {
  PANELS.forEach(p => {
    document.getElementById('panel-' + p).classList.toggle('active', p === id);
  });
  document.querySelectorAll('.nav-item').forEach(el => {
    // Vérifier si le onclick contient l'id
    const hasClick = el.getAttribute('onclick').includes(`'${id}'`);
    el.classList.toggle('active', hasClick);
  });
  if (id === 'logs') {
    fetchLogs();
  }
  
  // Fermer la sidebar mobile lors du clic sur un onglet
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
  }
}

// ─── Sidebar Mobile Toggle ──────────────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar && overlay) {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('open');
  }
}

// ─── Theme Toggle ──────────────────────────────────────────────────────────
function toggleTheme() {
  document.body.classList.toggle('light-theme');
  const icon = document.getElementById('theme-icon');
  if (document.body.classList.contains('light-theme')) {
    icon.className = 'fa-solid fa-sun';
  } else {
    icon.className = 'fa-solid fa-moon';
  }
}



// ─── Clock ────────────────────────────────────────────────────────────────
function tickClock() {
  document.getElementById('tb-clock').textContent =
    new Date().toLocaleTimeString('fr-FR', {hour12: false});
}
setInterval(tickClock, 1000); tickClock();

// ─── Sparklines ──────────────────────────────────────────────────────────
function renderSparkline(elementId, color, dataPoints) {
  const options = {
    series: [{ data: dataPoints }],
    chart: { type: 'line', width: 80, height: 30, sparkline: { enabled: true } },
    stroke: { curve: 'smooth', width: 2, colors: [color] },
    tooltip: { enabled: false }
  };
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = '';
    const chart = new ApexCharts(element, options);
    chart.render();
  }
}

// Simuler les mini-sparklines au démarrage
setTimeout(() => {
  renderSparkline('spark-btc-chart', '#10b981', [65000, 65200, 64900, 65800, 66300, 67420]);
  renderSparkline('spark-eth-chart', '#ef4444', [3550, 3520, 3540, 3490, 3500, 3480]);
  renderSparkline('spark-bnb-chart', '#10b981', [560, 565, 570, 568, 573, 578]);
}, 1000);

// ─── Chart ───────────────────────────────────────────────────────────────
let chart        = null;
let chartType    = 'area';
let cachedData   = {};
let activeSymbol = null;
let chartReady   = false;

function setChartType(t) {
  chartType = t;
  document.getElementById('ct-area').classList.toggle('active',   t === 'area');
  document.getElementById('ct-candle').classList.toggle('active', t === 'candlestick');
  if (activeSymbol && cachedData[activeSymbol]) renderChart(cachedData[activeSymbol], activeSymbol);
}

function switchSymbol(sym) {
  activeSymbol = sym;
  document.querySelectorAll('[data-sym]').forEach(el =>
    el.classList.toggle('active', el.dataset.sym === sym));
  if (cachedData[sym]) renderChart(cachedData[sym], sym);
}

function renderSymbolTabs(symbols) {
  const container = document.getElementById('sym-tabs');
  const cur = Array.from(container.querySelectorAll('[data-sym]')).map(e => e.dataset.sym);
  if (cur.length === symbols.length && symbols.every(s => cur.includes(s))) return;
  container.innerHTML = '';
  symbols.forEach(sym => {
    const btn = document.createElement('button');
    btn.className  = 'chart-tab' + (sym === activeSymbol ? ' active' : '');
    btn.dataset.sym = sym;
    btn.textContent = sym.replace('/USDT','').replace('/USD','').replace('USD','');
    btn.onclick = () => switchSymbol(sym);
    container.appendChild(btn);
  });
}

function buildSeries(rawData) {
  if (!Array.isArray(rawData) || !rawData.length) return [];
  return rawData
    .filter(c => c && c.t && !isNaN(c.o))
    .map(c => ({ x: c.t, y: [parseFloat(c.o), parseFloat(c.h), parseFloat(c.l), parseFloat(c.c)] }));
}

function renderChart(rawData, symbol) {
  if (typeof ApexCharts === 'undefined') {
    document.getElementById('nexchart').innerHTML =
      '<div class="empty">ApexCharts indisponible — vérifiez votre connexion.</div>';
    return;
  }
  const seriesData = buildSeries(rawData);
  if (!seriesData.length) {
    document.getElementById('nexchart').innerHTML =
      '<div class="empty">En attente de données de marché pour ' + symbol + '…</div>';
    return;
  }

  const areaData = seriesData.map(c => ({ x: c.x, y: c.y[3] }));

  const baseOpts = {
    chart: {
      type: chartType, height: 290, background: 'transparent',
      toolbar: { show: false }, animations: { enabled: false },
      fontFamily: "'JetBrains Mono', monospace", foreColor: '#6B85A8',
    },
    grid: { borderColor: 'rgba(255, 255, 255, 0.05)', strokeDashArray: 3,
            xaxis: { lines: { show: false } }, yaxis: { lines: { show: true } } },
    xaxis: {
      type: 'datetime',
      labels: { style: { colors: '#6B85A8', fontSize: '10px' }, datetimeUTC: false },
      axisBorder: { show: false }, axisTicks: { show: false },
    },
    yaxis: {
      labels: {
        style: { colors: '#6B85A8', fontSize: '10px' },
        formatter: v => v == null ? '' : parseFloat(v).toLocaleString('fr-FR', {maximumFractionDigits: 5})
      }
    },
    tooltip: {
      theme: 'dark',
      style: { fontSize: '11px', fontFamily: "'JetBrains Mono', monospace" },
      x: { format: 'dd/MM HH:mm' }
    },
    dataLabels: { enabled: false },
  };

  let opts;
  if (chartType === 'area') {
    opts = { ...baseOpts,
      series: [{ name: symbol, data: areaData }],
      stroke: { curve: 'smooth', width: 3, colors: ['#06b6d4'] },
      fill: { type: 'gradient', gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.45,
        opacityTo: 0.0,
        colorStops: [
          { offset: 0, color: '#06b6d4', opacity: 0.4 },
          { offset: 100, color: '#06b6d4', opacity: 0.0 }
        ]
      }},
      markers: { size: 0 },
    };
  } else {
    opts = { ...baseOpts,
      series: [{ name: 'Bougie', data: seriesData }],
      plotOptions: { candlestick: {
        colors: { upward: '#10b981', downward: '#ef4444' },
        wick: { useFillColor: true }
      }},
    };
  }

  const el = document.getElementById('nexchart');
  el.innerHTML = '';
  const inner = document.createElement('div');
  el.appendChild(inner);
  if (chart) { try { chart.destroy(); } catch(_) {} chart = null; }
  try {
    chart = new ApexCharts(inner, opts);
    chart.render().then(() => { chartReady = true; });
  } catch(e) {
    el.innerHTML = '<div class="empty">Erreur rendu graphique: ' + e.message + '</div>';
  }
}

// ─── Utils ────────────────────────────────────────────────────────────────
function safe(val, fallback = '—') {
  if (val == null || val === undefined || val === '' || (typeof val === 'number' && isNaN(val))) return fallback;
  return val;
}
function fmt(n, dec=2) {
  const v = parseFloat(n);
  if (isNaN(v)) return '—';
  return v.toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = (val === null || val === undefined) ? '—' : val;
}
function setHTML(id, val) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = (val === null || val === undefined) ? '—' : val;
}

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ─── Connection state ─────────────────────────────────────────────────────
let failCount = 0;
function setConnState(ok) {
  const dot   = document.getElementById('api-dot');
  const label = document.getElementById('api-sync');
  if (ok) {
    failCount = 0;
    if (dot)   dot.className   = 'dot green';
    if (label) label.textContent = 'Synchronisé : ' + new Date().toLocaleTimeString('fr-FR', {hour12:false});
  } else {
    failCount++;
    if (dot)   dot.className   = 'dot';
    if (label) label.textContent = 'Reconnexion (' + failCount + ')…';
  }
}

// ─── Logs update ──────────────────────────────────────────────────────────
async function fetchLogs() {
  // Uniquement si le panel logs est visible
  const logsPanel = document.getElementById('panel-logs');
  if (!logsPanel || !logsPanel.classList.contains('active')) return;
  
  try {
    const res = await fetch('/api/logs');
    if (res.ok) {
      const text = await res.text();
      const container = document.getElementById('log-area');
      if (container) {
        const lines = text.split('\\n');
        const formattedLines = lines.map(line => {
          if (!line.trim()) return '';
          if (line.includes(' - ERROR - ')) {
            return `<div class="log-err"><i class="fa-solid fa-circle-exclamation"></i> ${escapeHtml(line)}</div>`;
          } else if (line.includes(' - WARNING - ')) {
            return `<div class="log-warn"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(line)}</div>`;
          } else {
            return `<div class="log-info">${escapeHtml(line)}</div>`;
          }
        }).join('');
        container.innerHTML = formattedLines;
        container.scrollTop = container.scrollHeight;
      }
    }
  } catch(e) {
    console.warn('fetchLogs error:', e);
  }
}

function resetHistoryPageAndRender() {
  currentHistoryPage = 1;
  renderSignalsAndTradesTable();
}

function renderSignalsAndTradesTable() {
  const sigTableBody = document.querySelector('#signals-table tbody');
  const paginationContainer = document.getElementById('history-pagination');
  if (!sigTableBody || !latestData) return;

  const typeFilter = document.getElementById('filter-type') ? document.getElementById('filter-type').value : 'all';
  const brokerFilter = document.getElementById('filter-broker') ? document.getElementById('filter-broker').value : 'all';

  const pos = latestData.global_active || Object.values(latestData.positions || {});
  const hist = latestData.global_history || latestData.history || [];

  let combined = [];

  const posArray = Array.isArray(pos) ? pos : Object.values(pos);
  posArray.forEach(p => {
    combined.push({
      ...p,
      is_active: true,
      broker: p.broker || inferBrokerFromSymbol(p.symbol)
    });
  });

  hist.forEach(t => {
    combined.push({
      ...t,
      is_active: false,
      broker: t.broker || inferBrokerFromSymbol(t.symbol)
    });
  });

  function inferBrokerFromSymbol(symbol) {
    if (!symbol) return 'mt5';
    const sym = symbol.toUpperCase();
    const crypto_keywords = ["USDT", "BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOT", "LINK"];
    if (crypto_keywords.some(kw => sym.includes(kw))) return "binance";
    const stock_keywords = ["SPY", "QQQ", "AAPL", "TSLA", "MSFT"];
    if (stock_keywords.some(kw => sym.includes(kw))) return "alpaca";
    return "mt5";
  }

  let filtered = combined;

  if (typeFilter === 'active') {
    filtered = filtered.filter(x => x.is_active);
  } else if (typeFilter === 'closed') {
    filtered = filtered.filter(x => !x.is_active);
  }

  if (brokerFilter !== 'all') {
    filtered = filtered.filter(x => x.broker === brokerFilter);
  }

  // Sort: active positions first, then closed positions. Within each category, sort by timestamp desc.
  filtered.sort((a, b) => {
    if (a.is_active && !b.is_active) return -1;
    if (!a.is_active && b.is_active) return 1;
    const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    return timeB - timeA;
  });

  // Pagination logic
  const totalItems = filtered.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
  if (currentHistoryPage > totalPages) currentHistoryPage = totalPages;
  if (currentHistoryPage < 1) currentHistoryPage = 1;

  const startIndex = (currentHistoryPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedItems = filtered.slice(startIndex, endIndex);

  const dec = getDecimals();
  const pref = getCurrencyPrefix();
  const rate = getRate();
  let rows = '';
  let lastGroupDate = '';

  paginatedItems.forEach(t => {
    const side = (t.side || '').toUpperCase();
    const dateObj = new Date(t.timestamp);
    
    let groupDate = 'Date Inconnue';
    let timeStr = '—';
    if (!isNaN(dateObj.getTime())) {
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      groupDate = dateObj.toLocaleDateString('fr-FR', options);
      timeStr = dateObj.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'});
    }

    // Grouping row
    if (groupDate !== lastGroupDate) {
      lastGroupDate = groupDate;
      rows += `<tr class="date-group-row">
        <td colspan="7" style="background: rgba(255, 255, 255, 0.02); font-weight: 700; color: var(--accent-cyan); padding: 10px 16px; border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">
          <i class="fa-solid fa-calendar-day" style="margin-right: 8px;"></i>${groupDate}
        </td>
      </tr>`;
    }

    const brokerName = t.broker === 'binance' ? 'Binance' : t.broker === 'alpaca' ? 'Alpaca' : 'MT5';
    const brokerBadge = `<span class="badge" style="background: var(--border); color: var(--txt-secondary); margin-left: 6px; font-size: 9px; font-weight: 600; padding: 2px 6px; border-radius: 4px;">${brokerName}</span>`;

    if (t.is_active) {
      rows += `<tr>
        <td class="mono">${timeStr}</td>
        <td class="name mono">${t.symbol} ${brokerBadge}</td>
        <td><span class="badge badge-${side === 'LONG' || side === 'BUY' ? 'long' : 'short'}">${side || '—'}</span></td>
        <td class="mono">${pref}${fmt(t.entry_price, dec)}</td>
        <td class="mono">${t.stop_loss > 0 ? pref + fmt(t.stop_loss, dec) : '—'}</td>
        <td class="mono">${t.take_profit > 0 ? pref + fmt(t.take_profit, dec) : '—'}</td>
        <td><span class="tx-status success"><i class="fa-solid fa-spinner fa-spin" style="margin-right: 4px;"></i>En Cours</span></td>
      </tr>`;
    } else {
      const pnlVal = parseFloat(t.pnl || 0) * (selectedCurrency === 'USD' ? 1.0 : rate);
      const pnlStr = (pnlVal >= 0 ? '+' : '') + fmt(pnlVal, 2) + ' ' + selectedCurrency;
      rows += `<tr>
        <td class="mono">${timeStr}</td>
        <td class="name mono">${t.symbol} ${brokerBadge}</td>
        <td><span class="badge badge-${side === 'LONG' || side === 'BUY' ? 'long' : 'short'}">${side || '—'}</span></td>
        <td class="mono">${pref}${fmt(t.entry_price || 0, dec)}</td>
        <td class="mono">${pref}${fmt(t.exit_price || 0, dec)} (Sortie)</td>
        <td class="mono">—</td>
        <td><span class="tx-status ${pnlVal >= 0 ? 'success' : 'danger'}">${pnlVal >= 0 ? 'Gain' : 'Perte'} (${pnlStr})</span></td>
      </tr>`;
    }
  });

  if (!rows) {
    sigTableBody.innerHTML = '<tr><td colspan="7" class="empty"><i class="fa-solid fa-circle-nodes"></i> Aucun trade correspondant aux filtres</td></tr>';
  } else {
    sigTableBody.innerHTML = rows;
  }

  // Render pagination controls
  if (paginationContainer) {
    if (totalPages <= 1) {
      paginationContainer.innerHTML = '';
      return;
    }

    let paginationHtml = '';
    
    // Previous button
    paginationHtml += `<button class="chart-tab" ${currentHistoryPage === 1 ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : `onclick="changeHistoryPage(${currentHistoryPage - 1})"`}>Précédent</button>`;
    
    // Page numbers — max 4 onglets visibles centrés sur la page courante
    const maxVisible = 4;
    let startPage = Math.max(1, currentHistoryPage - Math.floor(maxVisible / 2));
    let endPage   = startPage + maxVisible - 1;
    if (endPage > totalPages) {
      endPage   = totalPages;
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
      paginationHtml += `<span style="color:var(--txt-muted); padding: 0 4px; align-self:center;">...</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
      if (i === currentHistoryPage) {
        paginationHtml += `<button class="chart-tab active">${i}</button>`;
      } else {
        paginationHtml += `<button class="chart-tab" onclick="changeHistoryPage(${i})">${i}</button>`;
      }
    }

    if (endPage < totalPages) {
      paginationHtml += `<span style="color:var(--txt-muted); padding: 0 4px; align-self:center;">...</span>`;
    }

    // Next button
    paginationHtml += `<button class="chart-tab" ${currentHistoryPage === totalPages ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : `onclick="changeHistoryPage(${currentHistoryPage + 1})"`}>Suivant</button>`;
    
    paginationContainer.innerHTML = paginationHtml;
  }
}

function changeHistoryPage(page) {
  currentHistoryPage = page;
  renderSignalsAndTradesTable();
}

// ─── Data update ──────────────────────────────────────────────────────────
async function fetchData() {
  try {
    const res = await fetch('/api/data', { cache: 'no-store' });
    if (!res.ok) { setConnState(false); return; }
    const d = await res.json();
    latestData = d;
    setConnState(true);

    const bot  = d.bot  || {};
    const perf = d.performance || {};
    const risk = d.risk  || {};
    const news = d.news  || {};
    const stats = d.stats || {};

    // ── Sidebar status ──
    const alive = bot.running !== false;
    const sbDot = document.getElementById('sb-dot');
    if (sbDot) sbDot.className = 'status-dot' + (alive ? ' live' : '');
    setEl('sb-status', alive ? 'Moteur Actif' : 'Moteur Inactif');

    // ── Topbar broker ──
    const broker = (perf.broker || d.broker_type || '').toUpperCase() || 'NEXQUANT';
    const accType = (perf.account_type || '').toUpperCase();
    setEl('tb-broker', broker + (accType ? ' · ' + accType : ''));

    // ── KPI: Solde ──
    const bal  = perf.current_balance;
    const init = perf.initial_balance;
    lastBalanceUsd = bal;
    lastInitUsd = init;
    updateBalanceDisplay();

    // ── KPI: P&L ──
    const pnl   = parseFloat(perf.total_pnl ?? 0);
    const upnl  = parseFloat(perf.unrealized_pnl ?? 0);
    
    const pnlPctEl = document.getElementById('kpi-pnl-pct');
    if (pnlPctEl && init > 0) {
      const pnlPctVal = (pnl / init) * 100;
      const display = (pnlPctVal >= 0 ? '+' : '') + fmt(pnlPctVal, 2) + '%';
      pnlPctEl.textContent = display;
      pnlPctEl.className = 'balance-pnl-pct ' + (pnlPctVal >= 0 ? 'up' : 'down');
    }
    
    const rawPnlEl = document.getElementById('overview-pnl-raw');
    if (rawPnlEl) {
      rawPnlEl.textContent = (pnl >= 0 ? '+' : '') + fmt(pnl) + ' USD';
      rawPnlEl.className = 'pnl-metric ' + (pnl >= 0 ? 'pos' : 'neg');
    }

    const wr = parseFloat(perf.win_rate ?? 0);
    const pf = parseFloat(perf.profit_factor ?? 1);
    setEl('wr-val', fmt(wr * 100, 1) + ' %');
    setEl('pf-val', fmt(pf, 2));
    
    const wrBar = document.getElementById('wr-bar');
    if (wrBar) wrBar.style.width = (wr * 100) + '%';
    const pfBar = document.getElementById('pf-bar');
    if (pfBar) pfBar.style.width = Math.min((pf / 3) * 100, 100) + '%';

    // ── KPI: Drawdown ──
    const dd = Math.abs(parseFloat(perf.drawdown_pct ?? 0));
    setEl('r-dd', fmt(dd) + ' %');
    const ddBar = document.getElementById('r-dd-bar');
    if (ddBar) ddBar.style.width = Math.min(dd * 10, 100) + '%';

    // ── Uptime ──
    const up = parseInt(bot.uptime_seconds ?? 0);
    const hh = Math.floor(up / 3600), mm = Math.floor((up % 3600) / 60);
    setHTML('sb-uptime', `<i class="fa-regular fa-clock"></i> ` + hh + 'h ' + String(mm).padStart(2,'0') + 'm');

    // ── Sentiment ──
    const fg = news.fear_greed_value;
    setEl('s-fg', fg != null ? fg : '—');
    if (fg != null) {
      const pct = Math.min(Math.max(parseInt(fg), 0), 100);
      const bar = document.getElementById('s-fg-bar');
      if (bar) {
        bar.style.width = pct + '%';
        bar.className   = 'pnl-prog-fill' + (pct < 25 ? ' red' : pct < 55 ? ' amber' : ' green');
      }
      const labels = ['Peur extrême','Peur','Neutre','Cupidité','Cupidité extrême'];
      const li = pct < 20 ? 0 : pct < 40 ? 1 : pct < 60 ? 2 : pct < 80 ? 3 : 4;
      setEl('s-fg-label', labels[li]);
    }
    const sc = parseFloat(news.overall_score ?? news.score);
    setEl('s-score', isNaN(sc) ? '—' : (sc >= 0 ? '+' : '') + sc.toFixed(3));
    setEl('s-conf',  safe(fmt(news.confidence, 2)));
    setEl('s-avoid', news.avoidance_active ? 'Actif' : 'Inactif');

    // ── News body list ──
    const newsBody = document.getElementById('news-body');
    if (newsBody) {
      const events = news.recent_events || [];
      if (!events.length) {
        newsBody.innerHTML = '<div class="empty"><i class="fa-solid fa-circle-info"></i> Aucune actualité à fort impact récente</div>';
        newsBody.className = 'empty';
      } else {
        newsBody.className = '';
        newsBody.innerHTML = events.map(ev => {
          const dateObj = new Date(ev.timestamp);
          const timeStr = isNaN(dateObj.getTime()) ? '' : dateObj.toLocaleDateString('fr-FR', {month:'2-digit', day:'2-digit'}) + ' ' + dateObj.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'});
          const impactBadge = ev.impact === 'HIGH' ? '<span class="badge badge-short" style="background:#ef4444; color:#fff; border:none; padding:2px 6px;">HIGH</span>' : `<span class="badge" style="background:#f59e0b; color:#fff; border:none; padding:2px 6px;">${ev.impact}</span>`;
          return `<div style="padding: 12px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 11px; color: var(--txt-secondary); font-weight:600">${ev.currency || 'ALL'} · ${ev.source || 'Unknown'}</span>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span style="font-size: 10px; color: var(--txt-muted); font-family: monospace;">${timeStr}</span>
                ${impactBadge}
              </div>
            </div>
            <div style="font-size: 12px; color: var(--txt); font-weight: 500;">${escapeHtml(ev.title || '')}</div>
            ${ev.description ? `<div style="font-size: 11px; color: var(--txt-secondary); margin-top: 2px;">${escapeHtml(ev.description)}</div>` : ''}
          </div>`;
        }).join('');
      }
    }

    // ── Risk panel ──
    const exp = parseFloat(risk.current_risk_pct ?? 0);
    setEl('r-risk',   isNaN(exp) ? '—' : fmt(exp) + ' %');
    setEl('r-active-pos', safe(risk.open_positions_count));
    const kf = risk.kelly_fraction;
    setEl('r-kelly',  kf != null && !isNaN(parseFloat(kf)) ? parseFloat(kf * 100).toFixed(2) + ' %' : 'N/A');
    setEl('r-maxpos', safe(risk.max_daily_trades));

    latestAssetType = d.asset_type || 'crypto';
    updateDynamicWidgets(latestAssetType, d.market_data || {});

    // ── Positions table ──
    const tbody = document.getElementById('pos-tbody');
    if (tbody) {
      const pos  = d.positions || {};
      const keys = Object.keys(pos);
      if (!keys.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty"><i class="fa-solid fa-briefcase"></i> Aucune position ouverte</td></tr>';
      } else {
        tbody.innerHTML = keys.map(sym => {
          const p    = pos[sym] || {};
          const side = (p.side || '').toUpperCase();
          const upnl = parseFloat(p.unrealized_pnl ?? 0);
          const dec = getDecimals();
          const pref = getCurrencyPrefix();
          const rate = getRate();
          const liq = parseFloat(p.liquidation_price || 0);
          return `<tr>
            <td class="name mono">${sym}</td>
            <td><span class="badge badge-${side === 'LONG' ? 'long' : 'short'}">${side || '—'}</span></td>
            <td class="mono">${fmt(p.size, 4)}</td>
            <td class="mono">${pref}${fmt(p.entry_price, dec)}</td>
            <td class="mono">${pref}${fmt(p.current_price || p.mark_price, dec)}</td>
            <td class="mono neg" style="font-weight: 600; color: #ef4444;">${liq > 0 ? pref + fmt(liq, dec) : '—'}</td>
            <td class="mono ${upnl >= 0 ? 'pos' : 'neg'}">${(upnl >= 0 ? '+' : '') + fmt(upnl * rate)} ${selectedCurrency}</td>
            <td class="mono ${p.stop_loss ? 'neg' : ''}">${p.stop_loss > 0 ? pref + fmt(p.stop_loss, dec) : '—'}</td>
            <td class="mono ${p.take_profit ? 'pos' : ''}">${p.take_profit > 0 ? pref + fmt(p.take_profit, dec) : '—'}</td>
          </tr>`;
        }).join('');
      }
    }

    // ── Signals/trades list under overview ──
    renderSignalsAndTradesTable();

    // ── Chart ──
    const md   = d.market_data || {};
    const syms = Object.keys(md);
    if (syms.length) {
      cachedData = md;
      const needInit = !activeSymbol || !syms.includes(activeSymbol);
      if (needInit) activeSymbol = syms[0];
      renderSymbolTabs(syms);
      if (needInit || !chartReady) renderChart(md[activeSymbol], activeSymbol);
    }

  } catch(e) {
    setConnState(false);
    console.warn('fetchData error:', e);
  }
}

// Poll data and logs
fetchData();
setInterval(fetchData, 5000);

setInterval(fetchLogs, 3000);
</script>
</body>
</html>
"""

    def log_message(self, format, *args):
        """Override pour désactiver les logs HTTP par défaut."""
        log.debug("%s - - [%s] %s" %
                  (self.address_string(),
                   self.log_date_time_string(),
                   format % args))


class DashboardServer:
    """Serveur de dashboard pour SuperBot."""

    def __init__(self, host: str = "0.0.0.0", port: int = 5000,
                 dashboard_data_func = None):
        """
        Initialise le serveur de dashboard.

        Args:
            host: Adresse d'écoute
            port: Port d'écoute
            dashboard_data_func: Fonction qui retourne les données à afficher
        """
        self.host = host
        self.port = port
        self.data = {}
        if dashboard_data_func is None:
            self.dashboard_data_func = lambda: self.data
        else:
            self.dashboard_data_func = dashboard_data_func
        self.server = None
        self.server_thread = None
        self.running = False

        log.info(f"DashboardServer configuré sur {host}:{port}")

    def update_data(self, data):
        """Met à jour les données du dashboard."""
        self.data = data

    def start(self):
        """Démarre le serveur de dashboard en arrière-plan."""
        if self.running:
            log.warning("⚠️ Le serveur dashboard est déjà en cours d'exécution")
            return

        def handler_factory(*args, **kwargs):
            return DashboardHandler(*args,
                                dashboard_data_func=self.dashboard_data_func,
                                **kwargs)

        self.server = HTTPServer((self.host, self.port), handler_factory)
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        log.info(f"Serveur dashboard démarré sur {self.host}:{self.port}")

    def stop(self):
        """Arrête le serveur de dashboard."""
        if not self.running:
            log.warning("⚠️ Le serveur dashboard n'est pas en cours d'exécution")
            return

        log.info("Arrêt du serveur dashboard...")
        self.running = False
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5.0)
        log.info("Serveur dashboard arrêté")

    def _run_server(self):
        """Boucle principale du serveur."""
        log.info(f"Serveur dashboard en écoute sur {self.host}:{self.port}")
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Ne pas logger l'erreur si on est en train d'arrêter
                log.error(f"Erreur dans le serveur dashboard: {e}")
        finally:
            log.info("Boucle du serveur dashboard terminée")


# Fonction utilitaire pour créer une fonction de données de dashboard simple
def create_dashboard_data_func(broker, strategy, risk_manager, news_manager):
    """
    Crée une fonction pour récupérer les données du dashboard à partir des composants du bot.

    Args:
        broker: Instance du broker
        strategy: Instance de la stratégie
        risk_manager: Instance du gestionnaire de risque
        news_manager: Instance du gestionnaire de nouvelles

    Returns:
        Fonction qui retourne un dictionnaire avec les données du dashboard
    """
    def get_dashboard_data() -> Dict[str, Any]:
        """Récupère toutes les données nécessaires pour le dashboard."""
        try:
            # Données du bot
            bot_running = False
            uptime_seconds = 0
            start_time = None

            # Performance
            performance = {
                'initial_balance': 10000.0,
                'current_balance': 10000.0,
                'total_pnl': 0.0,
                'daily_pnl': 0.0,
                'monthly_pnl': 0.0,
                'drawdown_pct': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0
            }

            # Métriques de risque
            risk_metrics = {}
            try:
                account_balance = getattr(broker, 'get_balance', lambda: 10000.0)()
                if hasattr(risk_manager, 'get_risk_metrics'):
                    risk_metrics = risk_manager.get_risk_metrics(account_balance)
            except Exception as e:
                log.debug(f"Impossible d'obtenir les métriques de risque: {e}")

            risk_data = {
                'current_risk_pct': risk_metrics.get('current_risk_pct', 0),
                'open_positions_count': risk_metrics.get('open_positions_count', 0),
                'max_daily_trades': getattr(risk_manager, 'MAX_OPEN_POSITIONS', 'N/A'),
                'kelly_fraction': risk_metrics.get('kelly_fraction'),
                'sentiment_factor': 1.0
            }

            # Positions ouvertes
            positions = {}
            try:
                if hasattr(broker, 'get_open_positions'):
                    positions = broker.get_open_positions() or {}
                elif hasattr(risk_manager, 'open_positions'):
                    positions = risk_manager.open_positions or {}
            except Exception as e:
                log.debug(f"Impossible d'obtenir les positions: {e}")

            # Nouvelles et sentiment
            news_data = {}
            try:
                if hasattr(news_manager, 'get_sentiment_summary'):
                    news_summary = news_manager.get_sentiment_summary()
                    news_data = {
                        'overall_score': news_summary.get('overall', {}).get('score', 0),
                        'confidence': news_summary.get('overall', {}).get('confidence', 0),
                        'fear_greed_value': news_summary.get('fear_greed', {}).get('value'),
                        'avoidance_active': news_summary.get('avoidance_active', False),
                        'recent_high_impact_count': news_summary.get('recent_high_impact_count', 0)
                    }
            except Exception as e:
                log.debug(f"Impossible d'obtenir les données de nouvelles: {e}")

            return {
                'timestamp': datetime.now().isoformat(),
                'bot': {
                    'running': bot_running,
                    'uptime_seconds': uptime_seconds,
                    'start_time': start_time.isoformat() if start_time else None
                },
                'performance': performance,
                'risk': risk_data,
                'positions': positions,
                'news': news_data
            }

        except Exception as e:
            log.error(f"Erreur lors de la collecte des données du dashboard: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'bot': {'running': False},
                'performance': {},
                'risk': {},
                'positions': {},
                'news': {}
            }

    return get_dashboard_data


# Export des classes et fonctions publiques
__all__ = [
    'DashboardServer',
    'DashboardHandler',
    'create_dashboard_data_func'
]