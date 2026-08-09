import { createFileRoute } from "@tanstack/react-router";
import { Download } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { getDashboardData } from "@/lib/nexquant.functions";
import { useState, useEffect, useMemo } from "react";

const translations = {
  fr: {
    title: "Historique des trades",
    desc: "Journal complet des positions fermées depuis la création du compte.",
    export: "Exporter CSV",
    totalTrades: "Total trades",
    winners: "Gagnants",
    totalPnl: "P&L total",
    avgDuration: "Durée moy.",
    fees: "Frais cumulés",
    filters: ["Tous les brokers", "Toutes directions", "30 derniers jours"],
    search: "Rechercher symbole...",
    thSym: "Symbole",
    thSide: "Sens",
    thClose: "Fermeture",
    thSize: "Taille",
    thPnl: "P&L",
    thStrat: "Stratégie",
    thBroker: "Broker",
    empty: "Aucun historique disponible.",
    loading: "Chargement de l'historique..."
  },
  en: {
    title: "Trade History",
    desc: "Complete log of closed positions since account creation.",
    export: "Export CSV",
    totalTrades: "Total Trades",
    winners: "Winners",
    totalPnl: "Total P&L",
    avgDuration: "Avg Duration",
    fees: "Total Fees",
    filters: ["All brokers", "All directions", "Last 30 days"],
    search: "Search symbol...",
    thSym: "Symbol",
    thSide: "Side",
    thClose: "Close Time",
    thSize: "Size",
    thPnl: "P&L",
    thStrat: "Strategy",
    thBroker: "Broker",
    empty: "No history available.",
    loading: "Loading history..."
  },
  es: {
    title: "Historial de operaciones",
    desc: "Registro completo de posiciones cerradas desde la creación de la cuenta.",
    export: "Exportar CSV",
    totalTrades: "Operaciones totales",
    winners: "Ganadores",
    totalPnl: "P&L Total",
    avgDuration: "Duración Prom.",
    fees: "Comisiones",
    filters: ["Todos los brokers", "Todas las direcciones", "Últimos 30 días"],
    search: "Buscar símbolo...",
    thSym: "Símbolo",
    thSide: "Lado",
    thClose: "Cierre",
    thSize: "Tamaño",
    thPnl: "P&L",
    thStrat: "Estrategia",
    thBroker: "Broker",
    empty: "Sin historial disponible.",
    loading: "Cargando historial..."
  }
};

export const Route = createFileRoute("/_authenticated/history")({
  head: () => ({ meta: [{ title: "Historique — NexQuant" }] }),
  component: HistoryPage,
});

function HistoryPage() {
  const fetchData = useServerFn(getDashboardData);
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => fetchData(),
  });

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

  // BUG-D08 FIX: États pour filtres et pagination
  const [filterBroker, setFilterBroker] = useState("");
  const [filterSide, setFilterSide] = useState("");
  const [search, setSearch] = useState("");
  const PAGE_SIZE = 20;
  const [page, setPage] = useState(1);

  const closed = (data?.closedPositions || []) as any[];

  // BUG-D08 FIX: Filtrage et pagination côté client
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const filtered = useMemo(() =>
    closed.filter((p) => {
      const brokerOk = !filterBroker || p.broker === filterBroker;
      const sideOk = !filterSide || p.side === filterSide;
      const searchOk = !search || String(p.symbol ?? "").toLowerCase().includes(search.toLowerCase());
      return brokerOk && sideOk && searchOk;
    }), [closed, filterBroker, filterSide, search]);

  if (isLoading || !data) {
    return <div className="p-6 text-muted-foreground animate-pulse font-mono text-sm">{t.loading}</div>;
  }

  const totalTrades = closed.length;
  const winners = closed.filter((p: {pnl: unknown}) => Number(p.pnl) > 0);
  const winRate = totalTrades > 0 ? ((winners.length / totalTrades) * 100).toFixed(1) : "0.0";
  const totalPnl = closed.reduce((acc: number, p: {pnl: unknown}) => acc + Number(p.pnl), 0);

  // BUG-D06 FIX: Calculer la durée moyenne réelle depuis opened_at / closed_at
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const closedAny = closed as any[];
  const durations = closedAny
    .filter((p) => p.opened_at && p.closed_at)
    .map((p) => new Date(p.closed_at).getTime() - new Date(p.opened_at).getTime());
  const avgMs = durations.length > 0 ? durations.reduce((a: number, b: number) => a + b, 0) / durations.length : 0;
  const avgHours = Math.floor(avgMs / 3600000);
  const avgMins = Math.floor((avgMs % 3600000) / 60000);
  const avgDurationStr = avgMs > 0 ? `${avgHours}h ${avgMins}min` : "—";

  // BUG-D06 FIX: Calculer les frais cumulatifs si le champ commission existe
  const totalFees = closedAny.reduce((acc: number, p) => acc + (Number(p.commission) || 0), 0);
  const feesStr = totalFees > 0 ? `$${totalFees.toFixed(2)}` : "N/A";

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-2">
        <div>
          <h1 className="text-[15px] font-bold text-foreground font-technical tracking-tight">{t.title}</h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">{t.desc}</p>
        </div>
        {/* BUG-D08: Export CSV réel */}
        <button
          onClick={() => {
            const headers = ["symbol","side","closed_at","qty","pnl","pnl_pct","broker","strategy"];
            const rows = filtered.map((p: Record<string, unknown>) =>
              headers.map(h => JSON.stringify(p[h] ?? "")).join(",")
            );
            const csv = [headers.join(","), ...rows].join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a"); a.href = url; a.download = "trades.csv"; a.click();
          }}
          className="px-3 py-1.5 rounded-lg border border-primary/30 bg-primary/10 text-primary text-[12px] flex items-center gap-2 hover:bg-primary/20 transition"
        >
          <Download className="w-3.5 h-3.5" />
          {t.export}
        </button>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KpiCard label={t.totalTrades} value={totalTrades.toString()} />
        <KpiCard label={t.winners} value={`${winners.length} (${winRate}%)`} />
        <KpiCard label={t.totalPnl} value={`${totalPnl >= 0 ? "+" : ""}$${totalPnl.toFixed(2)}`} isPositive={totalPnl >= 0} />
        {/* BUG-D06 FIX: valeurs calculées depuis les données réelles */}
        <KpiCard label={t.avgDuration} value={avgDurationStr} />
        <KpiCard label={t.fees} value={feesStr} />
      </div>

      {/* BUG-D08 FIX: Filtres fonctionnels */}
      <div className="flex flex-wrap gap-2 mb-2">
        <select
          value={filterBroker}
          onChange={e => { setFilterBroker(e.target.value); setPage(1); }}
          className="px-3 py-1.5 rounded-md border border-border bg-background text-muted-foreground text-[11px] cursor-pointer focus:outline-none"
        >
          <option value="">{t.filters[0]}</option>
          {[...new Set(closed.map((p: {broker?: string}) => p.broker).filter(Boolean))].map((b) => (
            <option key={b as string} value={b as string}>{b as string}</option>
          ))}
        </select>
        <select
          value={filterSide}
          onChange={e => { setFilterSide(e.target.value); setPage(1); }}
          className="px-3 py-1.5 rounded-md border border-border bg-background text-muted-foreground text-[11px] cursor-pointer focus:outline-none"
        >
          <option value="">{t.filters[1]}</option>
          <option value="long">LONG</option>
          <option value="short">SHORT</option>
        </select>
        <input
          type="text"
          placeholder={t.search}
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="px-3 py-1.5 rounded-md border border-border bg-background text-foreground text-[11px] flex-1 min-w-[120px] focus:outline-none"
        />
      </div>


      {/* Table */}
      <div className="panel p-0 overflow-hidden rounded-xl border border-border">
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
          <table className="w-full text-[11px] font-mono">
            <thead className="sticky top-0 bg-background/95 backdrop-blur-xl z-10">
              <tr className="uppercase text-muted-foreground border-b border-border">
                <th className="text-left py-2 px-4 font-medium">{t.thSym}</th>
                <th className="text-left py-2 px-4 font-medium">{t.thSide}</th>
                <th className="text-left py-2 px-4 font-medium">{t.thClose}</th>
                <th className="text-right py-2 px-4 font-medium">{t.thSize}</th>
                <th className="text-right py-2 px-4 font-medium">{t.thPnl}</th>
                <th className="text-left py-2 px-4 font-medium">{t.thStrat}</th>
                <th className="text-left py-2 px-4 font-medium">{t.thBroker}</th>
              </tr>
            </thead>
            <tbody>
              {/* BUG-D08 FIX: afficher la page courante */}
              {pageItems.map((p: Record<string, unknown>) => {
                const isWin = Number(p.pnl) >= 0;
                return (
                  <tr key={p.id as string} className="border-b border-border hover:bg-muted/30 transition-colors">
                    <td className="py-2.5 px-4 font-bold text-foreground">{p.symbol as string}</td>
                    <td className="py-2.5 px-4">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${p.side === 'long' ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'}`}>
                        {(p.side as string).toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-muted-foreground">
                      {p.closed_at ? new Date(p.closed_at as string).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                    </td>
                    <td className="py-2.5 px-4 text-right text-muted-foreground">{p.qty as number}</td>
                    <td className={`py-2.5 px-4 text-right font-bold ${isWin ? 'text-success' : 'text-destructive'}`}>
                      {isWin ? "+" : ""}${Number(p.pnl).toFixed(2)}
                      <span className="text-[10px] opacity-70 font-normal ml-1.5">
                        ({Number(p.pnl_pct) >= 0 ? "+" : ""}{Number(p.pnl_pct).toFixed(2)}%)
                      </span>
                    </td>
                    {/* BUG-D07 FIX: afficher p.strategy au lieu de 'NexQuant Core' */}
                    <td className="py-2.5 px-4"><span className="text-primary">{(p.strategy as string) ?? "NexQuant Core"}</span></td>
                    <td className="py-2.5 px-4 text-muted-foreground capitalize">{p.broker as string}</td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-muted-foreground">{t.empty}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* BUG-D08 FIX: pagination fonctionnelle */}
        <div className="p-3 border-t border-border flex justify-between items-center bg-background/50">
          <span className="text-[11px] text-muted-foreground">
            {filtered.length} trades · Page {page} / {totalPages || 1}
          </span>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-2 py-1 rounded border border-border text-muted-foreground text-[10px] hover:bg-muted/30 disabled:opacity-40"
            >←</button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const pageNum = i + 1;
              return (
                <button key={pageNum} onClick={() => setPage(pageNum)}
                  className={`px-2 py-1 rounded border text-[10px] ${
                    page === pageNum ? 'border-primary/30 bg-primary/15 text-primary' : 'border-border text-muted-foreground hover:bg-muted/30'
                  }`}
                >{pageNum}</button>
              );
            })}
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-2 py-1 rounded border border-border text-muted-foreground text-[10px] hover:bg-muted/30 disabled:opacity-40"
            >→</button>
          </div>
        </div>
      </div>
    </div>
  );
}


function KpiCard({ label, value, isPositive }: { label: string; value: string; isPositive?: boolean }) {
  return (
    <div className="panel p-3 rounded-xl border border-border">
      <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">{label}</div>
      <div className={`text-base font-bold font-technical ${isPositive === true ? 'text-success' : isPositive === false ? 'text-destructive' : 'text-foreground'}`}>
        {value}
      </div>
    </div>
  );
}
