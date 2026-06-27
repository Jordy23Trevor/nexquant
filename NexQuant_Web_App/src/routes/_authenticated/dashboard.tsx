import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useState } from "react";
import {
  Activity, ArrowDown, ArrowUp, LogOut, Pause, Play, RefreshCw, TrendingUp,
  TrendingDown, Zap, Brain, Newspaper, Cpu, Settings, Shield, Key, Clock
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { ensureDemoData, getDashboardData, toggleBot, saveBrokerCredentials } from "@/lib/nexquant.functions";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — NexQuant" }] }),
  component: Dashboard,
});

function Dashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fetchData = useServerFn(getDashboardData);
  const seed = useServerFn(ensureDemoData);
  const toggle = useServerFn(toggleBot);

  // Seed once if empty
  useEffect(() => { seed().catch(() => {}); }, [seed]);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => fetchData(),
    refetchInterval: 15000,
  });

  const toggleMut = useMutation({
    mutationFn: (run: boolean) => toggle({ data: { run } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["dashboard"] }); },
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
          Initialisation du dashboard…
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
  const day = equity.length >= 2 ? equity[equity.length - 1].equity - equity[equity.length - 2].equity : 0;
  const dayPct = equity.length >= 2 ? (day / equity[equity.length - 2].equity) * 100 : 0;
  const maxDd = equity.reduce((m, p) => Math.max(m, p.drawdown), 0);

  const openTotal = data.openPositions.reduce((s, p) => s + Number(p.pnl), 0);

  return (
    <div className="min-h-screen">
      {/* Top bar */}
      <header className="sticky top-0 z-40 backdrop-blur bg-background/70 border-b border-border">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 h-14 flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-primary to-accent grid place-items-center">
              <Activity className="w-3.5 h-3.5 text-background" />
            </div>
            <span className="font-semibold tracking-tight">NexQuant</span>
          </Link>
          <span className="hidden md:inline text-xs text-muted-foreground font-mono">/ dashboard</span>

          <div className="ml-auto flex items-center gap-2">
            <span className={`text-xs px-2.5 py-1 rounded-md font-mono ${running ? "text-success bg-success/10" : "text-muted-foreground bg-muted/30"}`}>
              <span className={`badge-dot ${running ? "" : "text-muted-foreground"}`}>
                {running ? "RUNNING" : "STOPPED"}
              </span>
            </span>
            <button onClick={() => toggleMut.mutate(!running)}
              disabled={toggleMut.isPending}
              className={`text-xs px-3 py-1.5 rounded-md font-medium flex items-center gap-1.5 transition ${
                running ? "bg-destructive/15 text-destructive hover:bg-destructive/25"
                        : "bg-success/15 text-success hover:bg-success/25"
              }`}>
              {running ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {running ? "Arrêter" : "Démarrer"}
            </button>
            <button onClick={() => refetch()} disabled={isFetching}
              className="p-1.5 rounded-md hover:bg-card text-muted-foreground" title="Rafraîchir">
              <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
            </button>
            <button onClick={signOut} className="p-1.5 rounded-md hover:bg-card text-muted-foreground" title="Déconnexion">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 lg:px-6 py-6 space-y-6">
        {/* Bandeau Licence / Période d'essai */}
        {data.profile && (
          <div className="panel p-4 bg-gradient-to-r from-primary/10 to-accent/10 border border-primary/20 rounded-lg flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-primary animate-pulse" />
              <div>
                <h3 className="font-semibold text-sm">Période d'essai NexQuant Bêta</h3>
                <p className="text-xs text-muted-foreground">
                  Votre accès gratuit de 30 jours se termine le {data.profile.trial_end ? new Date(data.profile.trial_end).toLocaleDateString() : "—"} (
                  {data.profile.trial_end ? Math.max(0, Math.ceil((new Date(data.profile.trial_end).getTime() - Date.now()) / (24 * 3600 * 1000))) : 0} jours restants).
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {data.profile.role === "admin" && (
                <Link to="/admin" className="text-xs px-3 py-1.5 rounded-md bg-accent/20 text-accent hover:bg-accent/30 font-medium transition">
                  Portail Admin
                </Link>
              )}
              <button onClick={() => toast.info("Intégration Stripe en cours (Bêta)")} className="text-xs px-3 py-1.5 rounded-md bg-primary text-background font-medium hover:bg-primary/90 transition">
                S'abonner (29$/mois)
              </button>
            </div>
          </div>
        )}

        {/* KPIs */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Kpi label="Équity" value={`$${(last?.equity ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
               sub={`Initial $${(first?.equity ?? 0).toLocaleString()}`} />
          <Kpi label="P&L total" value={`${pnlTotal >= 0 ? "+" : ""}$${pnlTotal.toFixed(2)}`}
               sub={`${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}% · 90j`}
               tone={pnlTotal >= 0 ? "up" : "down"} />
          <Kpi label="P&L 24h" value={`${day >= 0 ? "+" : ""}$${day.toFixed(2)}`}
               sub={`${dayPct >= 0 ? "+" : ""}${dayPct.toFixed(2)}%`}
               tone={day >= 0 ? "up" : "down"} />
          <Kpi label="Max drawdown" value={`${maxDd.toFixed(2)}%`}
               sub={`${data.openPositions.length} positions ouvertes`}
               tone="warning" />
        </section>

        {/* Equity curve */}
        <section className="panel p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold">Équity curve</h2>
              <p className="text-xs text-muted-foreground">Capital sur 90 jours · open P&L: <span className={openTotal >= 0 ? "text-success" : "text-destructive"}>{openTotal >= 0 ? "+" : ""}${openTotal.toFixed(2)}</span></p>
            </div>
            <span className="text-xs font-mono text-muted-foreground">{equity.length} pts</span>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equity} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"  stopColor="oklch(0.64 0.19 280)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="oklch(0.64 0.19 280)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="oklch(1 0 0 / 0.06)" />
                <XAxis dataKey="ts" tick={{ fontSize: 10, fill: "oklch(0.66 0.02 270)" }}
                  tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  axisLine={false} tickLine={false} minTickGap={40} />
                <YAxis tick={{ fontSize: 10, fill: "oklch(0.66 0.02 270)" }} axisLine={false} tickLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`} domain={["dataMin - 200", "dataMax + 200"]} />
                <Tooltip contentStyle={{ background: "oklch(0.22 0.017 277)", border: "1px solid oklch(1 0 0 / 0.1)", borderRadius: 8, fontSize: 12 }}
                  labelFormatter={(v) => new Date(v).toLocaleString()}
                  formatter={(v: number) => [`$${Number(v).toFixed(2)}`, "Équity"]} />
                <Area type="monotone" dataKey="equity" stroke="oklch(0.64 0.19 280)" strokeWidth={2} fill="url(#eq)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Two cols: positions + regime */}
        <section className="grid lg:grid-cols-3 gap-6">
          <div className="panel p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Positions ouvertes</h2>
              <span className="text-xs text-muted-foreground">{data.openPositions.length} ouvertes</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-xs uppercase text-muted-foreground border-b border-border">
                    <th className="text-left py-2 pr-3">Symbole</th>
                    <th className="text-left py-2 pr-3">Sens</th>
                    <th className="text-right py-2 pr-3">Qté</th>
                    <th className="text-right py-2 pr-3">Entrée</th>
                    <th className="text-right py-2 pr-3">Prix</th>
                    <th className="text-right py-2">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {data.openPositions.map((p) => (
                    <tr key={p.id} className="border-b border-border/50 last:border-0">
                      <td className="py-2.5 pr-3">{p.symbol} <span className="text-xs text-muted-foreground">· {p.broker}</span></td>
                      <td className="py-2.5 pr-3">
                        <span className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded ${
                          p.side === "long" ? "bg-success/15 text-success" : "bg-destructive/15 text-destructive"
                        }`}>
                          {p.side === "long" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                          {p.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-right">{p.qty}</td>
                      <td className="py-2.5 pr-3 text-right text-muted-foreground">{Number(p.entry_price).toLocaleString()}</td>
                      <td className="py-2.5 pr-3 text-right">{Number(p.current_price).toLocaleString()}</td>
                      <td className={`py-2.5 text-right ${Number(p.pnl) >= 0 ? "ticker-glow-up" : "ticker-glow-down"}`}>
                        {Number(p.pnl) >= 0 ? "+" : ""}${Number(p.pnl).toFixed(2)}
                        <div className="text-xs opacity-70">{Number(p.pnl_pct) >= 0 ? "+" : ""}{Number(p.pnl_pct).toFixed(2)}%</div>
                      </td>
                    </tr>
                  ))}
                  {data.openPositions.length === 0 && (
                    <tr><td colSpan={6} className="py-8 text-center text-muted-foreground">Aucune position ouverte</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel p-5">
            <div className="flex items-center gap-2 mb-4">
              <Brain className="w-4 h-4 text-accent" />
              <h2 className="font-semibold">Régime de marché</h2>
            </div>
            <div className="space-y-3">
              {data.regime.map((r) => (
                <RegimeRow key={r.id} r={r} />
              ))}
            </div>
          </div>
        </section>

        {/* Closed + Logs */}
        <section className="grid lg:grid-cols-3 gap-6">
          <div className="panel p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Historique des trades</h2>
              <span className="text-xs text-muted-foreground">{data.closedPositions.length} trades</span>
            </div>
            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-sm font-mono">
                <thead className="sticky top-0 bg-card">
                  <tr className="text-xs uppercase text-muted-foreground border-b border-border">
                    <th className="text-left py-2 pr-3">Clos le</th>
                    <th className="text-left py-2 pr-3">Symbole</th>
                    <th className="text-left py-2 pr-3">Sens</th>
                    <th className="text-right py-2">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {data.closedPositions.map((p) => (
                    <tr key={p.id} className="border-b border-border/40">
                      <td className="py-2 pr-3 text-xs text-muted-foreground">
                        {p.closed_at ? new Date(p.closed_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                      </td>
                      <td className="py-2 pr-3">{p.symbol}</td>
                      <td className="py-2 pr-3 text-xs uppercase">{p.side}</td>
                      <td className={`py-2 text-right ${Number(p.pnl) >= 0 ? "text-success" : "text-destructive"}`}>
                        {Number(p.pnl) >= 0 ? "+" : ""}${Number(p.pnl).toFixed(2)}
                        <span className="text-xs opacity-70 ml-2">({Number(p.pnl_pct) >= 0 ? "+" : ""}{Number(p.pnl_pct).toFixed(2)}%)</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel p-5">
            <div className="flex items-center gap-2 mb-4">
              <Cpu className="w-4 h-4 text-primary" />
              <h2 className="font-semibold">Journal d'exécution</h2>
            </div>
            <LogStream logs={data.logs} />
          </div>
        </section>

        {/* Bot info */}
        <section className="panel p-5 grid md:grid-cols-3 gap-4 text-sm">
          <Info icon={<Zap className="w-4 h-4 text-warning" />} label="Broker"
                value={`${status?.broker_type ?? "—"} ${status?.testnet ? "· testnet" : ""}`} />
          <Info icon={<Activity className="w-4 h-4 text-success" />} label="Dernier heartbeat"
                value={status?.last_heartbeat ? new Date(status.last_heartbeat).toLocaleString() : "—"} />
          <Info icon={<Newspaper className="w-4 h-4 text-accent" />} label="Démarré"
                value={status?.started_at ? new Date(status.started_at).toLocaleString() : "—"} />
        </section>

        {/* Panneau de Configuration du Broker */}
        <section className="grid md:grid-cols-3 gap-6">
          <div className="panel p-5 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-4 h-4 text-primary" />
              <h2 className="font-semibold">Configuration du Broker & Clés API (SaaS)</h2>
            </div>
            <BrokerSettingsForm userBroker={data.userBroker} />
          </div>

          <div className="panel p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-4 h-4 text-accent" />
                <h2 className="font-semibold">Sécurité des Identifiants</h2>
              </div>
              <div className="space-y-3 text-xs text-muted-foreground leading-relaxed">
                <div className="flex items-start gap-2">
                  <Key className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  <p>
                    Vos clés de trading sont chiffrées de bout en bout avec l'algorithme de niveau bancaire AES-256-CBC.
                  </p>
                </div>
                <p>
                  Elles ne sont jamais écrites sur le disque dur. Le bot Python local s'authentifie via signature HMAC pour les récupérer en mémoire uniquement lors de son exécution.
                </p>
              </div>
            </div>
            <div className="pt-4 border-t border-border mt-4">
              <span className="block font-mono text-[10px] text-muted-foreground uppercase">Votre Jeton d'ingestion (HMAC) :</span>
              <code className="block mt-1 font-mono text-[10px] bg-muted/50 p-2 rounded select-all break-all text-primary">
                {data.profile?.ingest_token || "non généré"}
              </code>
            </div>
          </div>
        </section>

        <IngestHelp />
      </main>
    </div>
  );
}

function Kpi({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "up" | "down" | "warning" }) {
  return (
    <div className="panel p-4">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-2 text-2xl font-semibold font-mono ${
        tone === "up" ? "text-success" : tone === "down" ? "text-destructive" : tone === "warning" ? "text-warning" : ""
      }`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

function RegimeRow({ r }: { r: any }) {
  const tone =
    r.regime === "trending" ? "bg-success/10 text-success border-success/30" :
    r.regime === "ranging"  ? "bg-accent/10 text-accent border-accent/30" :
                              "bg-warning/10 text-warning border-warning/30";
  const sent = Number(r.news_sentiment);
  return (
    <div className="border border-border rounded-md p-3 bg-card/50">
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm">{r.symbol}</span>
        <span className={`text-xs px-1.5 py-0.5 rounded border ${tone} uppercase`}>{r.regime}</span>
      </div>
      <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
        <span>conf {(Number(r.confidence) * 100).toFixed(0)}%</span>
        {r.trend_direction === "up" && <TrendingUp className="w-3.5 h-3.5 text-success" />}
        {r.trend_direction === "down" && <TrendingDown className="w-3.5 h-3.5 text-destructive" />}
        <span className={sent > 0 ? "text-success" : sent < 0 ? "text-destructive" : ""}>
          news {sent > 0 ? "+" : ""}{sent.toFixed(2)}
        </span>
      </div>
      {r.nlp_signal && <p className="mt-2 text-xs italic text-muted-foreground">"{r.nlp_signal}"</p>}
    </div>
  );
}

function LogStream({ logs }: { logs: any[] }) {
  return (
    <div className="max-h-80 overflow-y-auto font-mono text-xs space-y-1.5 pr-1">
      {logs.map((l) => {
        const color =
          l.level === "error" ? "text-destructive" :
          l.level === "warn" ? "text-warning" :
          l.level === "success" ? "text-success" :
          "text-muted-foreground";
        return (
          <div key={l.id} className="flex gap-2 leading-relaxed">
            <span className="text-muted-foreground/60 shrink-0">
              {new Date(l.created_at).toLocaleTimeString()}
            </span>
            <span className={`${color} shrink-0`}>[{l.source ?? l.level}]</span>
            <span className="text-foreground/90">{l.message}</span>
          </div>
        );
      })}
      {logs.length === 0 && <div className="text-muted-foreground">Aucun log</div>}
    </div>
  );
}

function Info({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-md bg-card border border-border grid place-items-center">{icon}</div>
      <div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">{label}</div>
        <div className="font-mono">{value}</div>
      </div>
    </div>
  );
}

function IngestHelp() {
  const [open, setOpen] = useState(false);
  const url = typeof window !== "undefined" ? `${window.location.origin}/api/public/ingest` : "/api/public/ingest";
  return (
    <details onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)} className="panel p-5">
      <summary className="cursor-pointer flex items-center justify-between">
        <span className="font-semibold">Connecter votre bot Python à NexQuant</span>
        <span className="text-xs text-muted-foreground">{open ? "Masquer" : "Afficher"}</span>
      </summary>
      <div className="mt-4 space-y-3 text-sm">
        <p className="text-muted-foreground">
          Le bot pousse ses métriques via un endpoint public. Récupérez votre <code className="font-mono text-xs bg-card px-1.5 py-0.5 rounded">user_id</code> dans Cloud → Auth → Users.
        </p>
        <pre className="font-mono text-xs bg-background border border-border rounded-md p-4 overflow-x-auto">{`POST ${url}
Content-Type: application/json

{
  "user_id": "<votre-uuid>",
  "kind": "equity",          // equity | position | log | regime | heartbeat
  "payload": { "equity": 12438.20 }
}`}</pre>
        <p className="text-xs text-muted-foreground">
          Auth: l'endpoint requiert le header <code className="font-mono">x-user-id</code> matchant <code className="font-mono">user_id</code> (à enrichir avec un secret signé en production).
        </p>
        <button onClick={() => { navigator.clipboard.writeText(url); toast.success("URL copiée"); }}
          className="text-xs px-3 py-1.5 rounded-md bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25">
          Copier l'URL
        </button>
      </div>
    </details>
  );
}

function BrokerSettingsForm({ userBroker }: { userBroker: any }) {
  const [brokerType, setBrokerType] = useState<"binance" | "alpaca" | "mt5">(
    userBroker?.broker_type || "binance"
  );
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  
  // MT5 specific
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState("");
  const [path, setPath] = useState("C:\\Program Files\\MetaTrader 5");

  const [isSaving, setIsSaving] = useState(false);
  const saveCredentials = useServerFn(saveBrokerCredentials);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await saveCredentials({
        data: {
          broker_type: brokerType,
          api_key: brokerType !== "mt5" ? apiKey : undefined,
          api_secret: brokerType !== "mt5" ? apiSecret : undefined,
          login: brokerType === "mt5" ? login : undefined,
          password: brokerType === "mt5" ? password : undefined,
          server: brokerType === "mt5" ? server : undefined,
          path: brokerType === "mt5" ? path : undefined,
        }
      });
      toast.success("Configuration du broker sauvegardée avec succès !");
      setApiKey("");
      setApiSecret("");
      setPassword("");
    } catch (err: any) {
      toast.error(`Erreur de sauvegarde: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-sm">
      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-1">
          Sélectionner votre Courtier
        </label>
        <div className="grid grid-cols-3 gap-2">
          {(["binance", "alpaca", "mt5"] as const).map((b) => (
            <button
              key={b}
              type="button"
              onClick={() => setBrokerType(b)}
              className={`py-2 rounded-md border text-center font-medium capitalize transition ${
                brokerType === b
                  ? "bg-primary/10 border-primary text-primary"
                  : "bg-card border-border hover:bg-muted/50"
              }`}
            >
              {b === "mt5" ? "MetaTrader 5" : b}
            </button>
          ))}
        </div>
      </div>

      {brokerType !== "mt5" ? (
        <>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Clé API
            </label>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={userBroker?.broker_type === brokerType ? "•••••••••••••••• (sauvegardé)" : "Entrez votre clé API"}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
              required={!userBroker}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Secret API
            </label>
            <input
              type="password"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder={userBroker?.broker_type === brokerType ? "•••••••••••••••• (sauvegardé)" : "Entrez votre secret API"}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
              required={!userBroker}
            />
          </div>
        </>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Identifiant MT5 (Login)
            </label>
            <input
              type="text"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              placeholder="Ex: 384002"
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Mot de Passe MT5
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Mot de passe MT5"
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Serveur MT5
            </label>
            <input
              type="text"
              value={server}
              onChange={(e) => setServer(e.target.value)}
              placeholder="Ex: FusionMarkets-Demo"
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Chemin Executable MT5
            </label>
            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="Ex: C:\\Program Files\\MetaTrader 5\\terminal64.exe"
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
              required
            />
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isSaving}
        className="w-full md:w-auto px-5 py-2 rounded-md bg-primary text-background font-medium hover:bg-primary/95 transition disabled:opacity-50"
      >
        {isSaving ? "Sauvegarde en cours..." : "Sauvegarder la Configuration"}
      </button>
    </form>
  );
}
