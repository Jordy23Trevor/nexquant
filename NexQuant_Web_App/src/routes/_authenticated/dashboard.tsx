import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useState } from "react";
import {
  Activity, ArrowDown, ArrowUp, LogOut, Pause, Play, RefreshCw, TrendingUp,
  TrendingDown, Zap, Brain, Newspaper, Cpu, Settings, Shield, Key, Clock, Square, Database, History
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { MetricCard } from "@/components/MetricCard";
import { BotStatusIndicator } from "@/components/BotStatusIndicator";
import { ControlPanel } from "@/components/ControlPanel";
import { getDashboardData, toggleBot, updateRisk, saveBrokerCredentials, updateBrokerConfig } from "@/lib/nexquant.functions";
import { useMemo } from "react";

const translations = {
  fr: {
    init: "Initialisation du dashboard…",
    equityTitle: "Équity",
    equityTT: "Capital total actuel incluant les P&L non réalisés.",
    initial: "Initial",
    pnl90: "P&L Total (90j)",
    pnl90TT: "Gains et pertes cumulés sur les 90 derniers jours.",
    pnl24: "P&L 24h",
    pnl24TT: "Gains et pertes sur les dernières 24 heures.",
    maxDd: "Max Drawdown",
    maxDdTT: "La plus grande baisse de capital depuis le sommet historique (High Water Mark).",
    posOpen: "pos. ouvertes",
    curveTitle: "Courbe de Croissance (Équity)",
    curveSub: "Capital sur 90 jours",
    openPnlLabel: "P&L Ouvert:",
    pts: "pts",
    openPositionsTitle: "Positions ouvertes",
    thSym: "Symbole",
    thSide: "Sens",
    thQty: "Qté",
    thEntry: "Entrée",
    thCurrent: "Prix Actuel",
    thPnl: "P&L",
    emptyPos: "Aucune position ouverte.",
    riskUpdated: "Niveau de risque mis à jour"
  },
  en: {
    init: "Initializing dashboard…",
    equityTitle: "Equity",
    equityTT: "Current total capital including unrealized P&L.",
    initial: "Initial",
    pnl90: "Total P&L (90d)",
    pnl90TT: "Cumulative gains and losses over the last 90 days.",
    pnl24: "24h P&L",
    pnl24TT: "Gains and losses over the last 24 hours.",
    maxDd: "Max Drawdown",
    maxDdTT: "The largest peak-to-drop drop in capital (High Water Mark).",
    posOpen: "open pos.",
    curveTitle: "Growth Curve (Equity)",
    curveSub: "Capital over 90 days",
    openPnlLabel: "Open P&L:",
    pts: "pts",
    openPositionsTitle: "Open Positions",
    thSym: "Symbol",
    thSide: "Side",
    thQty: "Qty",
    thEntry: "Entry",
    thCurrent: "Current Price",
    thPnl: "P&L",
    emptyPos: "No open positions.",
    riskUpdated: "Risk level updated"
  },
  es: {
    init: "Inicializando panel…",
    equityTitle: "Capital",
    equityTT: "Capital total actual incluyendo P&L no realizados.",
    initial: "Inicial",
    pnl90: "P&L Total (90d)",
    pnl90TT: "Ganancias y pérdidas acumuladas en los últimos 90 días.",
    pnl24: "P&L 24h",
    pnl24TT: "Ganancias y pérdidas en las últimas 24 horas.",
    maxDd: "Max Drawdown",
    maxDdTT: "La mayor caída de capital desde el pico máximo.",
    posOpen: "pos. abiertas",
    curveTitle: "Curva de Crecimiento (Capital)",
    curveSub: "Capital en 90 días",
    openPnlLabel: "P&L Abierto:",
    pts: "pts",
    openPositionsTitle: "Posiciones abiertas",
    thSym: "Símbolo",
    thSide: "Lado",
    thQty: "Cant",
    thEntry: "Entrada",
    thCurrent: "Precio Actual",
    thPnl: "P&L",
    emptyPos: "No hay posiciones abiertas.",
    riskUpdated: "Nivel de riesgo actualizado"
  }
};

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — NexQuant" }] }),
  component: Dashboard,
});

function Dashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fetchData = useServerFn(getDashboardData);
  const toggle = useServerFn(toggleBot);

  const [lang, setLang] = useState<"fr" | "en" | "es">("fr");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("lang") as "fr" | "en" | "es";
      if (stored && stored !== lang) {
        setLang(stored);
      }
    }

    const handleLangChange = () => {
      setLang((localStorage.getItem("lang") as "fr" | "en" | "es") || "fr");
    };
    window.addEventListener("langChange", handleLangChange);
    return () => window.removeEventListener("langChange", handleLangChange);
  }, []);

  const t = translations[lang] || translations.fr;

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => fetchData(),
    refetchInterval: 15000,
  });

  const toggleMut = useMutation({
    mutationFn: (run: boolean) => toggle({ data: { run } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["dashboard"] }); },
  });

  const riskMut = useMutation({
    mutationFn: (risk: number) => updateRisk({ data: { risk } }),
    onSuccess: () => { 
      toast.success(t.riskUpdated);
      qc.invalidateQueries({ queryKey: ["dashboard"] }); 
    },
  });

  const updateBrokerFn = useServerFn(updateBrokerConfig);
  const brokerMut = useMutation({
    mutationFn: (args: { brokerType: string, testnet: boolean }) => updateBrokerFn({ data: args }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["dashboard"] }); },
  });

  const handleToggleStatus = async (run: boolean) => {
    await toggleMut.mutateAsync(run);
  };

  const handleRiskChange = async (risk: number) => {
    await riskMut.mutateAsync(risk);
  };

  const handleBrokerChange = async (brokerType: string, testnet: boolean) => {
    await brokerMut.mutateAsync({ brokerType, testnet });
    toast.success("Broker mis à jour !");
  };

  async function signOut() {
    await qc.cancelQueries();
    qc.clear();
    await supabase.auth.signOut();
    navigate({ to: "/auth", replace: true });
  }

  const equity = data?.equity || [];

  const isRedArray = useMemo(() => {
    const N = equity.length;
    const isRed = new Array(N).fill(false);
    if (N > 1) {
      let runStart = -1;
      for (let i = 1; i < N; i++) {
        const isDown = equity[i].equity < equity[i - 1].equity;
        if (isDown) {
          if (runStart === -1) runStart = i;
        } else {
          if (runStart !== -1) {
            if (i - runStart >= 3) for (let k = runStart; k < i; k++) isRed[k] = true;
            runStart = -1;
          }
        }
      }
      if (runStart !== -1 && N - runStart >= 3)
        for (let k = runStart; k < N; k++) isRed[k] = true;
    }
    return isRed;
  }, [equity]);

  if (isError) {
    return (
      <div className="min-h-screen grid place-items-center">
        <div className="flex flex-col items-center gap-3 text-destructive">
          <Activity className="w-8 h-8 opacity-50" />
          <p className="font-semibold">Erreur de chargement</p>
          <p className="text-sm opacity-80">{error?.message || "Accès non autorisé ou erreur réseau"}</p>
        </div>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="min-h-screen grid place-items-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Activity className="w-5 h-5 animate-pulse text-primary" />
          {t.init}
        </div>
      </div>
    );
  }

  const status = data.status;
  const running = status?.is_running ?? false;
  const last = equity[equity.length - 1];
  const first = equity[0];
  const pnlTotal = last && first ? last.equity - first.equity : 0;
  const pnlPct = last && first ? ((last.equity - first.equity) / first.equity) * 100 : 0;
  const maxDd = equity.reduce((m: number, p: {drawdown: number}) => Math.max(m, p.drawdown), 0);

  const openTotal = data.openPositions.reduce((s: number, p: {pnl: unknown}) => s + Number(p.pnl), 0);

  const target24h = Date.now() - 86400000;
  const snap24h = equity.reduce((best: typeof equity[0] | null, p: typeof equity[0]) => {
    if (!best) return p;
    return Math.abs(new Date(p.ts).getTime() - target24h) <
           Math.abs(new Date(best.ts).getTime() - target24h) ? p : best;
  }, null as typeof equity[0] | null);
  const day = last && snap24h ? last.equity - snap24h.equity : 0;
  const dayPct = last && snap24h && snap24h.equity > 0
    ? (day / snap24h.equity) * 100 : 0;


  return (
    <div className="min-h-screen">
      <main className="max-w-7xl mx-auto px-4 lg:px-6 py-6 space-y-6">

        {/* KPIs */}
        <section className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-6">
          <MetricCard 
            title={t.equityTitle} 
            value={`$${(last?.equity ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
            change={`${t.initial} $${(first?.equity ?? 0).toLocaleString()}`}
            isPositive={true}
            tooltipText={t.equityTT}
            glowColor="indigo"
          />
          <MetricCard 
            title={t.pnl90} 
            value={`${pnlTotal >= 0 ? "+" : ""}$${pnlTotal.toFixed(2)}`}
            change={`${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%`}
            isPositive={pnlTotal >= 0}
            tooltipText={t.pnl90TT}
            glowColor={pnlTotal >= 0 ? "emerald" : "rose"}
          />
          <MetricCard 
            title={t.pnl24} 
            value={`${day >= 0 ? "+" : ""}$${day.toFixed(2)}`}
            change={`${dayPct >= 0 ? "+" : ""}${dayPct.toFixed(2)}%`}
            isPositive={day >= 0}
            tooltipText={t.pnl24TT}
            glowColor={day >= 0 ? "emerald" : "rose"}
          />
          <MetricCard 
            title={t.maxDd} 
            value={`${maxDd.toFixed(2)}%`}
            change={`${data.openPositions.length} ${t.posOpen}`}
            isPositive={false}
            tooltipText={t.maxDdTT}
            glowColor="rose"
          />
          <MetricCard 
            title="Win Rate" 
            value={`${((status?.win_rate ?? 0) * 100).toFixed(1)}%`}
            change="Trades Gagnants"
            isPositive={(status?.win_rate ?? 0) > 0.5}
            tooltipText="Pourcentage de trades profitables"
            glowColor={(status?.win_rate ?? 0) > 0.5 ? "emerald" : "rose"}
          />
          <MetricCard 
            title="Profit Factor" 
            value={`${(status?.profit_factor ?? 0).toFixed(2)}`}
            change="Ratio Gains/Pertes"
            isPositive={(status?.profit_factor ?? 0) > 1}
            tooltipText="Gain brut divisé par la perte brute"
            glowColor={(status?.profit_factor ?? 0) > 1 ? "emerald" : "rose"}
          />
        </section>

        {/* Advanced Metrics / Market Mood */}
        <section className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-6">
          <MetricCard 
            title="Kelly Fraction" 
            value={`${((status?.kelly_fraction ?? 0) * 100).toFixed(1)}%`}
            change="Risque suggéré"
            isPositive={true}
            tooltipText="La fraction de Kelly actuelle calculée par le bot"
            glowColor="indigo"
          />
          <MetricCard 
            title="News Sentiment" 
            value={`${(status?.news_sentiment ?? 0).toFixed(2)}`}
            change="Score"
            isPositive={(status?.news_sentiment ?? 0) >= 0}
            tooltipText="Sentiment global du marché via NLP"
            glowColor={(status?.news_sentiment ?? 0) >= 0 ? "emerald" : "rose"}
          />
          <MetricCard 
            title="Fear & Greed" 
            value={`${(status?.fear_greed ?? 50).toFixed(0)}`}
            change={(status?.fear_greed ?? 50) > 50 ? "Greed" : "Fear"}
            isPositive={(status?.fear_greed ?? 50) > 50}
            tooltipText="Indice de peur et d'avidité"
            glowColor={(status?.fear_greed ?? 50) > 50 ? "emerald" : "rose"}
          />
          <MetricCard 
            title="Bot Uptime" 
            value={`${((status?.uptime_seconds ?? 0) / 3600).toFixed(1)}h`}
            change="Temps en ligne"
            isPositive={true}
            tooltipText="Durée de fonctionnement de la session actuelle"
            glowColor="indigo"
          />
          <MetricCard 
            title="Market Regime" 
            value={`${status?.regime || 'Inconnu'}`}
            change={`${((status?.regime_confidence ?? 0) * 100).toFixed(0)}% conf`}
            isPositive={status?.regime?.includes('bull')}
            tooltipText="Le régime de marché actuellement détecté par l'IA"
            glowColor={status?.regime?.includes('bull') ? "emerald" : status?.regime?.includes('bear') ? "rose" : "indigo"}
          />
          <MetricCard 
            title="Objectif Jour" 
            value={`$${(status?.daily_achieved_eur ?? 0).toFixed(2)}`}
            change={`/ $${(status?.daily_target_eur ?? 0).toFixed(2)}`}
            isPositive={(status?.daily_achieved_eur ?? 0) >= (status?.daily_target_eur ?? 1)}
            tooltipText="Progression vers l'objectif journalier"
            glowColor={(status?.daily_achieved_eur ?? 0) >= (status?.daily_target_eur ?? 1) ? "emerald" : "indigo"}
          />
        </section>

        {/* Main Content Area: Graph & Control Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Equity curve */}
          <section className="panel p-5 lg:col-span-2 rounded-xl border border-border">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-foreground">{t.curveTitle}</h2>
                <p className="text-xs text-muted-foreground">{t.curveSub} · {t.openPnlLabel} <span className={openTotal >= 0 ? "text-success" : "text-destructive"}>{openTotal >= 0 ? "+" : ""}${openTotal.toFixed(2)}</span></p>
              </div>
              <span className="text-xs font-mono text-muted-foreground">{equity.length} {t.pts}</span>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equity} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorEqStroke" x1="0" y1="0" x2="1" y2="0">
                      {equity.length > 1 && equity.map((_: unknown, i: number) => {
                        if (i === 0) return null;
                        const color = isRedArray[i] ? "#f87171" : "#34d399";
                        const offsetPrev = ((i - 1) / (equity.length - 1)) * 100;
                        const offsetCurr = (i / (equity.length - 1)) * 100;
                        return [
                          <stop key={`s-${i}`} offset={`${offsetPrev}%`} stopColor={color} />,
                          <stop key={`e-${i}`} offset={`${offsetCurr}%`} stopColor={color} />,
                        ];
                      })}
                    </linearGradient>
                    <linearGradient id="colorEqFill" x1="0" y1="0" x2="1" y2="0">
                      {equity.length > 1 && equity.map((_: unknown, i: number) => {
                        if (i === 0) return null;
                        const color = isRedArray[i] ? "#f87171" : "#34d399";
                        const offsetPrev = ((i - 1) / (equity.length - 1)) * 100;
                        const offsetCurr = (i / (equity.length - 1)) * 100;
                        return [
                          <stop key={`sf-${i}`} offset={`${offsetPrev}%`} stopColor={color} stopOpacity={0.2} />,
                          <stop key={`ef-${i}`} offset={`${offsetCurr}%`} stopColor={color} stopOpacity={0.2} />,
                        ];
                      })}
                    </linearGradient>
                  </defs>

                  <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="ts" tick={{ fontSize: 10, fill: "#71717a" }}
                    tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                    axisLine={false} tickLine={false} minTickGap={40} />
                  <YAxis tick={{ fontSize: 10, fill: "#71717a" }} axisLine={false} tickLine={false}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`} domain={["dataMin - 200", "dataMax + 200"]} />
                  <Tooltip contentStyle={{ background: "#09090b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12, color: '#fff' }}
                    labelFormatter={(v) => new Date(v).toLocaleString()}
                    formatter={(v: number) => [`$${Number(v).toFixed(2)}`, "Équity"]} />
                  <Area type="monotone" dataKey="equity" stroke="url(#colorEqStroke)" strokeWidth={2} fill="url(#colorEqFill)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* Control Panel */}
          <section className="flex flex-col">
            <ControlPanel
              initialIsRunning={running}
              onToggleStatus={handleToggleStatus}
              initialRiskPct={status?.risk_pct ?? 1.0}
              onRiskChange={handleRiskChange}
              initialBrokerType={status?.broker_type}
              initialTestnet={status?.testnet}
              onBrokerChange={handleBrokerChange}
            />
          </section>

        </div>

        {/* Positions ouvertes */}
        <section className="panel p-0 overflow-hidden rounded-xl border border-border">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h2 className="font-semibold text-foreground">{t.openPositionsTitle}</h2>
            <span className="text-xs text-muted-foreground">{data.openPositions.length} {t.posOpen} · {t.openPnlLabel} <span className={openTotal >= 0 ? "text-success" : "text-destructive"}>{openTotal >= 0 ? "+" : ""}${openTotal.toFixed(2)}</span></span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm font-mono">
              <thead>
                <tr className="text-[11px] uppercase text-muted-foreground border-b border-border bg-background/50">
                  <th className="text-left py-3 px-4 font-medium">{t.thSym}</th>
                  <th className="text-left py-3 px-4 font-medium">{t.thSide}</th>
                  <th className="text-right py-3 px-4 font-medium">{t.thQty}</th>
                  <th className="text-right py-3 px-4 font-medium">{t.thEntry}</th>
                  <th className="text-right py-3 px-4 font-medium">{t.thCurrent}</th>
                  <th className="text-right py-3 px-4 font-medium">{t.thPnl}</th>
                </tr>
              </thead>
              <tbody>
                {data.openPositions.map((p) => (
                  <tr key={p.id} className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-4 text-foreground font-semibold">{p.symbol} <span className="text-[10px] font-normal text-muted-foreground ml-1">· {p.broker}</span></td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded ${
                        p.side === "long" ? "bg-success/15 text-success" : "bg-destructive/15 text-destructive"
                      }`}>
                        {p.side.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-muted-foreground">{p.qty}</td>
                    <td className="py-3 px-4 text-right text-muted-foreground">{Number(p.entry_price).toLocaleString()}</td>
                    <td className="py-3 px-4 text-right text-muted-foreground">{Number(p.current_price).toLocaleString()}</td>
                    <td className={`py-3 px-4 text-right font-bold ${Number(p.pnl) >= 0 ? "text-success" : "text-destructive"}`}>
                      {Number(p.pnl) >= 0 ? "+" : ""}${Number(p.pnl).toFixed(2)}
                      <span className="text-[10px] opacity-70 font-normal ml-2">{Number(p.pnl_pct) >= 0 ? "+" : ""}{Number(p.pnl_pct).toFixed(2)}%</span>
                    </td>
                  </tr>
                ))}
                {data.openPositions.length === 0 && (
                  <tr><td colSpan={6} className="py-8 text-center text-muted-foreground text-xs">{t.emptyPos}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Global History */}
        <section className="panel p-5 rounded-xl border border-border">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <History className="w-5 h-5 text-indigo-400" />
              Historique Global des Trades
            </h2>
          </div>
          
          <div className="overflow-x-auto">
            <div className="min-w-[800px]">
              <div className="grid grid-cols-7 gap-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground pb-2 border-b border-border">
                <div>Actif</div>
                <div>Side</div>
                <div>Entrée</div>
                <div>Sortie</div>
                <div>Quantité</div>
                <div>Date</div>
                <div className="text-right">PnL</div>
              </div>

              <div className="divide-y divide-border/50 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar mt-2">
                {!data.closedPositions || data.closedPositions.length === 0 ? (
                  <div className="py-8 text-center text-muted-foreground bg-background/50 rounded-lg border border-dashed border-border/50">
                    <p>Aucun trade clôturé pour le moment.</p>
                  </div>
                ) : (
                  data.closedPositions.map((pos: any) => (
                    <div key={pos.id} className="grid grid-cols-7 gap-4 py-3 items-center hover:bg-white/5 transition-colors rounded px-2 -mx-2">
                      <div className="font-medium flex items-center gap-2">
                        {pos.symbol}
                      </div>
                      <div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          pos.side === 'buy' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                        }`}>
                          {pos.side}
                        </span>
                      </div>
                      <div className="font-mono text-sm">${(pos.entry_price ?? 0).toLocaleString()}</div>
                      <div className="font-mono text-sm">${(pos.current_price ?? pos.entry_price ?? 0).toLocaleString()}</div>
                      <div className="font-mono text-sm">{(pos.qty ?? 0).toLocaleString()}</div>
                      <div className="text-muted-foreground text-xs">{new Date(pos.updated_at).toLocaleString()}</div>
                      <div className={`text-right font-bold font-mono text-sm ${pos.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {pos.pnl >= 0 ? '+' : ''}{pos.pnl?.toFixed(2) || '0.00'}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}


