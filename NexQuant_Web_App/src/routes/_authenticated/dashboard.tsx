import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useState } from "react";
import {
  Activity, ArrowDown, ArrowUp, LogOut, Pause, Play, RefreshCw, TrendingUp,
  TrendingDown, Zap, Brain, Newspaper, Cpu, Settings, Shield, Key, Clock
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { MetricCard } from "@/components/MetricCard";
import { BotStatusIndicator } from "@/components/BotStatusIndicator";
import { ControlPanel } from "@/components/ControlPanel";
import { getDashboardData, toggleBot, updateRisk, saveBrokerCredentials } from "@/lib/nexquant.functions";
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

  const [lang, setLang] = useState<"fr" | "en" | "es">(() => {
    if (typeof window !== "undefined") {
      return (localStorage.getItem("lang") as "fr" | "en" | "es") || "fr";
    }
    return "fr";
  });

  useEffect(() => {
    const handleLangChange = () => {
      setLang((localStorage.getItem("lang") as "fr" | "en" | "es") || "fr");
    };
    window.addEventListener("langChange", handleLangChange);
    return () => window.removeEventListener("langChange", handleLangChange);
  }, []);

  const t = translations[lang] || translations.fr;

  const { data, isLoading, refetch, isFetching } = useQuery({
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

  async function signOut() {
    await qc.cancelQueries();
    qc.clear();
    await supabase.auth.signOut();
    navigate({ to: "/auth", replace: true });
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
  const equity = data.equity;
  const last = equity[equity.length - 1];
  const first = equity[0];
  const pnlTotal = last && first ? last.equity - first.equity : 0;
  const pnlPct = last && first ? ((last.equity - first.equity) / first.equity) * 100 : 0;
  const maxDd = equity.reduce((m: number, p: {drawdown: number}) => Math.max(m, p.drawdown), 0);

  const openTotal = data.openPositions.reduce((s: number, p: {pnl: unknown}) => s + Number(p.pnl), 0);

  // BUG-D03 FIX: Trouver le snapshot le plus proche de il y a 24h au lieu d'utiliser
  // les 2 derniers points (qui peuvent être séparés de 15 minutes seulement)
  const target24h = Date.now() - 86400000;
  const snap24h = equity.reduce((best: typeof equity[0] | null, p: typeof equity[0]) => {
    if (!best) return p;
    return Math.abs(new Date(p.ts).getTime() - target24h) <
           Math.abs(new Date(best.ts).getTime() - target24h) ? p : best;
  }, null as typeof equity[0] | null);
  const day = last && snap24h ? last.equity - snap24h.equity : 0;
  const dayPct = last && snap24h && snap24h.equity > 0
    ? (day / snap24h.equity) * 100 : 0;

  // BUG-D10 FIX: Factoriser le calcul isRed avec useMemo (avant dupliqué ~40 lignes x2)
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


  return (
    <div className="min-h-screen">
      <main className="max-w-7xl mx-auto px-4 lg:px-6 py-6 space-y-6">

        {/* KPIs */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
                      {/* BUG-D10 FIX: isRedArray factorisé, plus de code dupliqué */}
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
              onToggleStatus={async (r) => { await toggleMut.mutateAsync(r); }}
              initialRiskPct={((data.status ?? {}) as Record<string, unknown>).risk_pct as number ?? 1.5}
              onRiskChange={async (r) => { await riskMut.mutateAsync(r); }}
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

      </main>
    </div>
  );
}


