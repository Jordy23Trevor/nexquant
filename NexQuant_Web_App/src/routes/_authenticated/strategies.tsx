import { createFileRoute } from "@tanstack/react-router";
import { Plus, Check, Copy, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { getDashboardData } from "@/lib/nexquant.functions";
import { toast } from "sonner";
import { useState, useEffect } from "react";

const translations = {
  fr: {
    title: "Stratégies & Webhook",
    desc: "Configuration des règles de trading et signaux TradingView",
    newStrat: "Nouvelle stratégie",
    typeTrend: "Tendance",
    typeCounter: "Contre-tendance",
    active: "Actif",
    inactive: "Inactif",
    pair: "Paire:",
    trades30: "Trades 30j:",
    modify: "Modifier",
    backtest: "Backtester",
    webhookTitle: "Webhook TradingView",
    endpoint: "Endpoint URL",
    copied: "URL copiée",
    secret: "Secret HMAC",
    regen: "Régénérer",
    waiting: "En attente de connexion webhook...",
    history: "Historique des signaux",
    notGen: "non généré",
    waitingTrades: "En attente",
    emptySigs: "Aucun signal récent",
    fastEma: "Fast EMA",
    slowEma: "Slow EMA",
    timeframe: "Unité de temps",
    rsiPeriod: "Période RSI",
    oversold: "Survente",
    overbought: "Surachat"
  },
  en: {
    title: "Strategies & Webhook",
    desc: "Trading rules configuration and TradingView signals",
    newStrat: "New Strategy",
    typeTrend: "Trend",
    typeCounter: "Counter-trend",
    active: "Active",
    inactive: "Inactive",
    pair: "Pair:",
    trades30: "30d Trades:",
    modify: "Modify",
    backtest: "Backtest",
    webhookTitle: "TradingView Webhook",
    endpoint: "Endpoint URL",
    copied: "URL copied",
    secret: "HMAC Secret",
    regen: "Regenerate",
    waiting: "Waiting for webhook connection...",
    history: "Signal History",
    notGen: "not generated",
    waitingTrades: "Waiting",
    emptySigs: "No recent signals",
    fastEma: "Fast EMA",
    slowEma: "Slow EMA",
    timeframe: "Timeframe",
    rsiPeriod: "RSI Period",
    oversold: "Oversold",
    overbought: "Overbought"
  },
  es: {
    title: "Estrategias y Webhook",
    desc: "Configuración de reglas de trading y señales de TradingView",
    newStrat: "Nueva estrategia",
    typeTrend: "Tendencia",
    typeCounter: "Contra-tendencia",
    active: "Activo",
    inactive: "Inactivo",
    pair: "Par:",
    trades30: "Operaciones 30d:",
    modify: "Modificar",
    backtest: "Backtest",
    webhookTitle: "Webhook TradingView",
    endpoint: "URL de Endpoint",
    copied: "URL copiada",
    secret: "Secreto HMAC",
    regen: "Regenerar",
    waiting: "Esperando conexión de webhook...",
    history: "Historial de señales",
    notGen: "no generado",
    waitingTrades: "Esperando",
    emptySigs: "Sin señales recientes",
    fastEma: "EMA Rápida",
    slowEma: "EMA Lenta",
    timeframe: "Marco temporal",
    rsiPeriod: "Periodo RSI",
    oversold: "Sobrevendida",
    overbought: "Sobrecomprada"
  }
};

export const Route = createFileRoute("/_authenticated/strategies")({
  head: () => ({ meta: [{ title: "Stratégies — NexQuant" }] }),
  component: StrategiesPage,
});

function StrategiesPage() {
  const fetchData = useServerFn(getDashboardData);
  const { data } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => fetchData(),
  });

  const [lang, setLang] = useState<"fr" | "en" | "es">("fr");

  const [webhookUrl, setWebhookUrl] = useState("https://nexquant.io/api/public/webhook");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("lang") as "fr" | "en" | "es";
      if (stored && stored !== lang) setLang(stored);
      setWebhookUrl(`${window.location.origin}/api/public/webhook`);
    }
    const handleLangChange = () => {
      setLang((localStorage.getItem("lang") as "fr" | "en" | "es") || "fr");
    };
    window.addEventListener("langChange", handleLangChange);
    return () => window.removeEventListener("langChange", handleLangChange);
  }, []);

  const t = translations[lang] || translations.fr;

  const token = data?.profile?.ingest_token || t.notGen;
  
  const strategies = [
    { name: 'EMA Cross', type: t.typeTrend, active: true, params: [[t.fastEma, '9'], [t.slowEma, '21'], [t.timeframe, '5m']], pair: 'BTC/USDT', trades: '142', wr: '61%' },
    { name: 'RSI Scalper', type: t.typeCounter, active: false, params: [[t.rsiPeriod, '14'], [t.oversold, '30'], [t.overbought, '70']], pair: 'ETH/USDT', trades: t.waitingTrades, wr: '—' }
  ];



  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-2">
        <div>
          <h1 className="text-[15px] font-bold text-foreground font-technical tracking-tight">{t.title}</h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">{t.desc}</p>
        </div>
        <button onClick={() => toast.info("Fonctionnalité en cours de développement")} className="px-3 py-1.5 rounded-lg border border-primary/30 bg-primary/10 text-primary text-[12px] flex items-center gap-2 hover:bg-primary/20 transition">
          <Plus className="w-3.5 h-3.5" />
          {t.newStrat}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Strategies List */}
        <div className="flex flex-col gap-4">
          {strategies.map((s) => (
            <div key={s.name} className="panel p-4 rounded-xl border border-border">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-foreground text-sm">{s.name}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-primary/10 text-primary">{s.type}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[11px] ${s.active ? 'text-success' : 'text-muted-foreground'}`}>{s.active ? t.active : t.inactive}</span>
                  <div className={`w-9 h-5 rounded-full relative cursor-pointer border ${s.active ? 'bg-primary border-primary' : 'bg-muted border-border'}`}>
                    <div className={`w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-all ${s.active ? 'right-0.5' : 'left-0.5'}`}></div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 mb-4">
                {s.params.map(([k, v]) => (
                  <div key={k} className="bg-muted/30 rounded-lg p-2 border border-border">
                    <div className="text-[10px] text-muted-foreground mb-0.5">{k}</div>
                    <div className="text-[12px] text-foreground font-medium">{v}</div>
                  </div>
                ))}
              </div>

              <div className="border-t border-border pt-3 flex justify-between">
                <span className="text-[11px] text-muted-foreground">{t.pair} <span className="text-foreground">{s.pair}</span></span>
                <span className="text-[11px] text-muted-foreground">{t.trades30} <span className="text-foreground">{s.trades}</span></span>
                <span className="text-[11px] text-muted-foreground">WR: <span className={s.wr !== '—' ? 'text-success' : 'text-muted-foreground'}>{s.wr}</span></span>
              </div>

              <div className="flex gap-2 mt-4">
                <button onClick={() => toast.info("Fonctionnalité en cours de développement")} className="flex-1 py-1.5 rounded-lg border border-border text-muted-foreground text-[11px] hover:bg-muted/30 transition">{t.modify}</button>
                <button onClick={() => toast.info("Fonctionnalité en cours de développement")} className="flex-1 py-1.5 rounded-lg border border-primary/20 bg-primary/10 text-primary text-[11px] hover:bg-primary/20 transition">{t.backtest}</button>
              </div>
            </div>
          ))}
        </div>

        {/* Right: Webhook Config */}
        <div className="panel p-4 rounded-xl border border-border h-fit">
          <div className="text-[12px] font-semibold text-foreground mb-3">{t.webhookTitle}</div>
          
          <div className="bg-muted/30 rounded-lg p-3 mb-4 font-mono text-[11px] leading-relaxed text-muted-foreground border border-border">
            <span className="text-primary">{"{"}</span><br />
            &nbsp;&nbsp;<span className="text-primary">"secret"</span>: <span className="text-success">"{token}"</span>,<br />
            &nbsp;&nbsp;<span className="text-primary">"symbol"</span>: <span className="text-success">"BTCUSDT"</span>,<br />
            &nbsp;&nbsp;<span className="text-primary">"action"</span>: <span className="text-success">"buy"</span>,<br />
            &nbsp;&nbsp;<span className="text-primary">"risk_pct"</span>: <span className="text-amber-500">1.5</span>,<br />
            &nbsp;&nbsp;<span className="text-primary">"leverage"</span>: <span className="text-amber-500">5</span><br />
            <span className="text-primary">{"}"}</span>
          </div>

          <div className="mb-3">
            <div className="text-[10px] text-muted-foreground mb-1 uppercase tracking-wider">{t.endpoint}</div>
            <div className="flex gap-2 items-center">
              <div className="flex-1 bg-muted/50 border border-border rounded-lg py-1.5 px-3 text-[11px] text-foreground font-mono overflow-hidden text-ellipsis whitespace-nowrap">
                {webhookUrl}
              </div>
              <button onClick={() => { navigator.clipboard.writeText(webhookUrl); toast.success(t.copied); }} 
                className="p-1.5 rounded-lg border border-border text-muted-foreground hover:bg-muted/30 transition">
                <Copy className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="mb-4">
            <div className="text-[10px] text-muted-foreground mb-1 uppercase tracking-wider">{t.secret}</div>
            <div className="flex gap-2 items-center">
              <div className="flex-1 bg-muted/50 border border-border rounded-lg py-1.5 px-3 text-[11px] text-foreground font-mono">
                {token.substring(0, 15)}...
              </div>
              <button onClick={() => toast.info("Fonctionnalité en cours de développement")} className="py-1.5 px-3 rounded-lg border border-primary/20 bg-primary/10 text-primary text-[11px] hover:bg-primary/20 transition flex items-center gap-1.5">
                <RefreshCw className="w-3 h-3" /> {t.regen}
              </button>
            </div>
          </div>

          <div className="bg-success/10 border border-success/20 rounded-lg py-2 px-3 text-[11px] text-success flex items-center gap-2">
            <Check className="w-3.5 h-3.5" />
            {t.waiting}
          </div>

          <div className="mt-4 border-t border-border pt-4">
            <div className="text-[10px] text-muted-foreground mb-2 uppercase tracking-wider">{t.history}</div>
            <div className="space-y-1">
              {/* Fake empty state for realism */}
              <div className="flex justify-center items-center py-4">
                <span className="text-[11px] text-muted-foreground">{t.emptySigs}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
