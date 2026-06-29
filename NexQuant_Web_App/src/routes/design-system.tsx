import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import {
  Activity, Copy, Check, Palette, Type, Layers, Grid, FileText, Sparkles,
  ExternalLink, Laptop, ShieldCheck, ChevronRight
} from "lucide-react";
import { toast } from "sonner";
import MetricCard from "@/components/MetricCard";
import BotStatusIndicator, { BotStatusType } from "@/components/BotStatusIndicator";
import ControlPanel from "@/components/ControlPanel";
import GDPRBanner from "@/components/GDPRBanner";

export const Route = createFileRoute("/design-system")({
  head: () => ({
    meta: [
      { title: "Design System & Charte Graphique — NexQuant" },
      { name: "description", content: "Charte graphique, bibliothèque de composants interactifs et plans d'interfaces Miro pour NexQuant." },
    ],
  }),
  component: DesignSystemShowcase,
});

type TabType = "aesthetics" | "components" | "miro";

function DesignSystemShowcase() {
  const [activeTab, setActiveTab] = useState<TabType>("aesthetics");
  const [copiedText, setCopiedText] = useState<string | null>(null);

  // States for Component Demos
  const [metricTitle, setMetricTitle] = useState("Ratio de Sharpe");
  const [metricValue, setMetricValue] = useState("2.42");
  const [metricChange, setMetricChange] = useState("+0.18");
  const [metricPositive, setMetricPositive] = useState(true);
  const [metricGlow, setMetricGlow] = useState<"indigo" | "emerald" | "rose" | "cyan">("indigo");

  const [botStatus, setBotStatus] = useState<BotStatusType>("running");
  const [botLatency, setBotLatency] = useState(12);
  const [botHeartbeat, setBotHeartbeat] = useState("11:23:42");

  const [controlRunning, setControlRunning] = useState(true);
  const [controlRisk, setControlRisk] = useState(1.5);

  const [glassBlur, setGlassBlur] = useState<"sm" | "md" | "lg">("md");

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copié avec succès !`);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const colors = [
    { name: "Fond Principal (Deep Dark)", hex: "#030712", tailwind: "bg-slate-950", use: "Arrière-plan global" },
    { name: "Fond Cartes (Dark Glass)", hex: "#18181b", tailwind: "bg-zinc-900/80", use: "Conteneur avec effet dépoli" },
    { name: "Accent Primaire (Indigo Glow)", hex: "#6366f1", tailwind: "text-indigo-500", use: "Branding, boutons actifs, highlights" },
    { name: "Valeurs Positives (Emerald)", hex: "#10b981", tailwind: "text-emerald-400", use: "Trades gagnants, PnL positif, Sharpe élevé" },
    { name: "Alertes / Drawdown (Crimson)", hex: "#ef4444", tailwind: "text-red-500", use: "Drawdown maximum, stop-loss, alertes" },
    { name: "Accent Secondaire (Cyan)", hex: "#22d3ee", tailwind: "text-cyan-400", use: "Régimes de marché, badges secondaires" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-foreground relative overflow-hidden font-display">
      {/* Background decoration */}
      <div className="absolute inset-0 grid-bg opacity-30 [mask-image:radial-gradient(ellipse_at_top,black,transparent_75%)]" />
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full bg-primary/10 blur-[130px] -z-0" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] rounded-full bg-accent/5 blur-[120px] -z-0" />

      {/* Nav */}
      <header className="relative z-10 sticky top-0 backdrop-blur-md bg-slate-950/80 border-b border-white/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-md bg-gradient-to-br from-primary to-accent grid place-items-center">
                <Activity className="w-4.5 h-4.5 text-slate-950" />
              </div>
              <span className="text-xl font-bold tracking-tight font-display text-white">NexQuant</span>
            </Link>
            <span className="text-xs font-mono text-muted-foreground bg-white/5 border border-white/10 px-2 py-0.5 rounded">
              v1.0 Design System
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-sm font-semibold hover:text-primary transition-colors">
              Retour au Dashboard
            </Link>
            <a
              href="https://miro.com"
              target="_blank"
              rel="noreferrer"
              className="text-xs px-3 py-1.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 font-medium transition flex items-center gap-1.5"
            >
              Ouvrir Miro <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </header>

      <main className="relative z-10 max-w-7xl mx-auto px-6 py-12">
        {/* Title */}
        <div className="text-center md:text-left mb-12">
          <div className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1 rounded-full bg-white/5 border border-white/10 text-primary mb-4">
            <Sparkles className="h-3.5 w-3.5" />
            Système Visuel Unifié (Web, Desktop, Mobile)
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white">
            Charte Graphique & <span className="gradient-text">Design System</span>
          </h1>
          <p className="mt-4 text-base md:text-lg text-muted-foreground max-w-3xl leading-relaxed">
            Spécifications de marque, bibliothèque de composants interactifs haut de gamme et guides
            filaires structurés pour assembler rapidement vos interfaces de trading quantitatif.
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex border-b border-white/10 mb-8 overflow-x-auto whitespace-nowrap">
          <button
            onClick={() => setActiveTab("aesthetics")}
            className={`flex items-center gap-2 px-6 py-3 border-b-2 text-sm font-semibold transition-all cursor-pointer ${
              activeTab === "aesthetics"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Palette className="h-4 w-4" />
            1. Charte Graphique & Esthétique
          </button>
          <button
            onClick={() => setActiveTab("components")}
            className={`flex items-center gap-2 px-6 py-3 border-b-2 text-sm font-semibold transition-all cursor-pointer ${
              activeTab === "components"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Layers className="h-4 w-4" />
            2. Bibliothèque de Composants
          </button>
          <button
            onClick={() => setActiveTab("miro")}
            className={`flex items-center gap-2 px-6 py-3 border-b-2 text-sm font-semibold transition-all cursor-pointer ${
              activeTab === "miro"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Grid className="h-4 w-4" />
            3. Blueprints Miro (Copier-Coller)
          </button>
        </div>

        {/* TAB 1: AESTHETICS */}
        {activeTab === "aesthetics" && (
          <div className="space-y-12">
            {/* Colors */}
            <section className="panel p-8 bg-zinc-900/20 backdrop-blur-md">
              <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <Palette className="text-primary h-5 w-5" />
                Palette de Couleurs (Hex & OKLCH)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {colors.map((c) => (
                  <div
                    key={c.name}
                    className="group border border-white/5 rounded-xl bg-slate-900/60 p-4 transition-all duration-300 hover:border-white/15"
                  >
                    <div className={`h-24 w-full rounded-lg ${c.tailwind} border border-white/10 mb-4 relative overflow-hidden flex items-end p-2`}>
                      <span className="text-[10px] uppercase font-mono font-bold bg-slate-950/70 px-2 py-0.5 rounded text-white border border-white/5">
                        {c.hex}
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-white mb-1">{c.name}</h4>
                    <p className="text-xs text-muted-foreground mb-4">{c.use}</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => copyToClipboard(c.hex, c.name)}
                        className="text-[10px] font-semibold flex items-center gap-1 px-2.5 py-1 rounded bg-white/5 border border-white/10 hover:bg-white/10 text-muted-foreground hover:text-foreground transition cursor-pointer"
                      >
                        <Copy className="h-3 w-3" /> Hex
                      </button>
                      <button
                        onClick={() => copyToClipboard(`oklch(${c.tailwind === "bg-slate-950" ? "0.16 0.013 275" : "0.64 0.19 280"})`, c.name)}
                        className="text-[10px] font-semibold flex items-center gap-1 px-2.5 py-1 rounded bg-white/5 border border-white/10 hover:bg-white/10 text-muted-foreground hover:text-foreground transition cursor-pointer"
                      >
                        <Copy className="h-3 w-3" /> OKLCH
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Typography */}
            <section className="panel p-8 bg-zinc-900/20 backdrop-blur-md">
              <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <Type className="text-primary h-5 w-5" />
                Typographie & Échelle Visuelle
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-slate-900/60 border border-white/5">
                    <span className="text-[10px] font-mono text-muted-foreground block mb-2">
                      headings - Space Grotesk
                    </span>
                    <h1 className="text-3xl font-bold font-display text-white">
                      NexQuant Trading Adaptatif
                    </h1>
                    <p className="text-xs text-muted-foreground mt-2">
                      Utilisé pour les grands titres de pages, en-têtes et chiffres de performance.
                    </p>
                  </div>

                  <div className="p-4 rounded-lg bg-slate-900/60 border border-white/5">
                    <span className="text-[10px] font-mono text-muted-foreground block mb-2">
                      body & UI - Inter
                    </span>
                    <p className="text-sm text-foreground leading-relaxed">
                      L'expérience utilisateur NexQuant repose sur une lisibilité absolue des données
                      quantitatives. Le texte principal utilise la police Inter pour rester compact.
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Utilisé pour les textes longs, labels d'inputs, alertes et paragraphes.
                    </p>
                  </div>
                </div>

                <div className="flex flex-col justify-between p-6 rounded-lg bg-slate-900/40 border border-white/5">
                  <div>
                    <h4 className="text-sm font-bold text-white mb-3">Bac à sable typographique</h4>
                    <textarea
                      defaultValue="Modifiez ce texte pour tester les polices du Design System de NexQuant."
                      className="w-full h-32 bg-slate-950 border border-white/10 rounded-lg p-3 text-sm focus:outline-none focus:border-primary resize-none font-display text-white"
                    />
                  </div>
                  <div className="flex items-center gap-2 mt-4 text-xs text-muted-foreground">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    Rendu de texte en direct
                  </div>
                </div>
              </div>
            </section>

            {/* Glassmorphism sandbox */}
            <section className="panel p-8 bg-zinc-900/20 backdrop-blur-md">
              <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <Layers className="text-primary h-5 w-5" />
                Effet de Verre & Glassmorphism
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="flex flex-col justify-between">
                  <p className="text-sm text-muted-foreground leading-relaxed mb-6">
                    NexQuant utilise un effet de verre dépoli à l'arrière-plan de ses conteneurs pour
                    évoquer la profondeur, le haut de gamme et la transparence des algorithmes.
                  </p>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold uppercase text-muted-foreground mb-2">
                        Ajuster le niveau de flou (backdrop-blur)
                      </label>
                      <div className="flex gap-2">
                        {(["sm", "md", "lg"] as const).map((b) => (
                          <button
                            key={b}
                            onClick={() => setGlassBlur(b)}
                            className={`px-4 py-2 rounded text-xs font-bold capitalize transition border cursor-pointer ${
                              glassBlur === b
                                ? "bg-primary text-primary-foreground border-primary"
                                : "bg-white/5 border-white/10 hover:bg-white/10 text-muted-foreground"
                            }`}
                          >
                            Blur {b.toUpperCase()}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="relative h-48 rounded-xl border border-white/10 overflow-hidden flex items-center justify-center p-6 bg-gradient-to-br from-indigo-500/10 to-cyan-500/10">
                  {/* Decorative glowing orbits */}
                  <div className="absolute w-24 h-24 rounded-full bg-primary/30 blur-xl animate-pulse" />
                  <div className="absolute top-4 right-12 w-16 h-16 rounded-full bg-accent/40 blur-xl animate-bounce" />

                  {/* Card with dynamic blur */}
                  <div
                    className={`relative z-10 w-full max-w-sm rounded-lg border border-white/15 bg-zinc-900/40 p-5 shadow-2xl text-center transition-all duration-300 ${
                      glassBlur === "sm"
                        ? "backdrop-blur-sm"
                        : glassBlur === "md"
                        ? "backdrop-blur-md"
                        : "backdrop-blur-lg"
                    }`}
                  >
                    <Laptop className="h-6 w-6 text-primary mx-auto mb-2" />
                    <h4 className="text-sm font-bold text-white">Conteneur Glassmorphic</h4>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      Effet de profondeur interactif.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* TAB 2: COMPONENTS */}
        {activeTab === "components" && (
          <div className="space-y-12">
            {/* Component A: MetricCard */}
            <section className="panel p-8 bg-zinc-900/20 backdrop-blur-md">
              <div className="flex flex-col lg:flex-row gap-8">
                {/* Visual Demo */}
                <div className="lg:w-1/2 space-y-6">
                  <div>
                    <h3 className="text-xl font-bold text-white mb-2">Composant A : `MetricCard`</h3>
                    <p className="text-sm text-muted-foreground">
                      Affiche une métrique quantitative clé (Sharpe, Profit Factor, etc.) avec indicateur de tendance et info-bulle d'aide.
                    </p>
                  </div>

                  <div className="p-8 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-center min-h-[220px]">
                    <MetricCard
                      title={metricTitle}
                      value={metricValue}
                      change={metricChange}
                      isPositive={metricPositive}
                      tooltipText="Exemple contextuel d'info-bulle sur le calcul de la métrique."
                      glowColor={metricGlow}
                      className="w-full max-w-xs"
                    />
                  </div>

                  {/* Interactive Knobs */}
                  <div className="grid grid-cols-2 gap-4 p-4 rounded-lg bg-slate-900/40 border border-white/5 text-xs">
                    <div>
                      <label className="block text-muted-foreground mb-1 font-semibold">Titre :</label>
                      <input
                        type="text"
                        value={metricTitle}
                        onChange={(e) => setMetricTitle(e.target.value)}
                        className="w-full bg-slate-950 border border-white/10 rounded px-2.5 py-1 focus:outline-none focus:border-primary text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-muted-foreground mb-1 font-semibold">Valeur :</label>
                      <input
                        type="text"
                        value={metricValue}
                        onChange={(e) => setMetricValue(e.target.value)}
                        className="w-full bg-slate-950 border border-white/10 rounded px-2.5 py-1 focus:outline-none focus:border-primary text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-muted-foreground mb-1 font-semibold font-semibold">Tendance delta :</label>
                      <input
                        type="text"
                        value={metricChange}
                        onChange={(e) => setMetricChange(e.target.value)}
                        className="w-full bg-slate-950 border border-white/10 rounded px-2.5 py-1 focus:outline-none focus:border-primary text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-muted-foreground mb-1 font-semibold">Couleur du Glow :</label>
                      <select
                        value={metricGlow}
                        onChange={(e) => setMetricGlow(e.target.value as any)}
                        className="w-full bg-slate-950 border border-white/10 rounded px-2.5 py-1 focus:outline-none focus:border-primary text-white"
                      >
                        <option value="indigo">Indigo</option>
                        <option value="emerald">Emerald</option>
                        <option value="rose">Rose</option>
                        <option value="cyan">Cyan</option>
                      </select>
                    </div>
                    <div className="col-span-2 flex items-center justify-between pt-2">
                      <span className="font-semibold text-muted-foreground">Tendance positive ?</span>
                      <input
                        type="checkbox"
                        checked={metricPositive}
                        onChange={(e) => setMetricPositive(e.target.checked)}
                        className="accent-primary h-4 w-4 cursor-pointer"
                      />
                    </div>
                  </div>
                </div>

                {/* Docs & Code */}
                <div className="lg:w-1/2 flex flex-col justify-between">
                  <div className="space-y-4">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                      Documentation & Props API
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left border-collapse">
                        <thead>
                          <tr className="border-b border-white/10 text-muted-foreground font-semibold">
                            <th className="pb-2">Prop</th>
                            <th className="pb-2">Type</th>
                            <th className="pb-2">Défaut</th>
                            <th className="pb-2">Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">title</td>
                            <td className="py-2 text-muted-foreground">string</td>
                            <td className="py-2">—</td>
                            <td className="py-2">Titre du KPI</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">value</td>
                            <td className="py-2 text-muted-foreground">string | number</td>
                            <td className="py-2">—</td>
                            <td className="py-2">Valeur principale</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">change</td>
                            <td className="py-2 text-muted-foreground">string</td>
                            <td className="py-2">—</td>
                            <td className="py-2">Delta (ex: +2.18%)</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">isPositive</td>
                            <td className="py-2 text-muted-foreground">boolean</td>
                            <td className="py-2">true</td>
                            <td className="py-2">Affiche en vert si vrai, rouge si faux</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">glowColor</td>
                            <td className="py-2 text-muted-foreground">"indigo" | "emerald" | "rose" | "cyan"</td>
                            <td className="py-2">"indigo"</td>
                            <td className="py-2">Couleur de la lueur au survol</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="mt-6">
                    <div className="flex items-center justify-between bg-slate-900 border-t border-x border-white/10 px-4 py-2 rounded-t-lg">
                      <span className="text-[10px] font-mono text-muted-foreground">TSX Usage Example</span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            `<MetricCard\n  title="${metricTitle}"\n  value="${metricValue}"\n  change="${metricChange}"\n  isPositive={${metricPositive}}\n  tooltipText="Info Sharpe"\n  glowColor="${metricGlow}"\n/>`,
                            "Code MetricCard"
                          )
                        }
                        className="text-[10px] font-semibold text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer"
                      >
                        <Copy className="h-3 w-3" /> Copier
                      </button>
                    </div>
                    <pre className="p-4 rounded-b-lg bg-slate-950 border border-white/10 text-xs font-mono text-muted-foreground overflow-x-auto">
{`<MetricCard
  title="${metricTitle}"
  value="${metricValue}"
  change="${metricChange}"
  isPositive={${metricPositive}}
  tooltipText="Indicateur de performance."
  glowColor="${metricGlow}"
/>`}
                    </pre>
                  </div>
                </div>
              </div>
            </section>

            {/* Component B: BotStatusIndicator */}
            <section className="panel p-8 bg-zinc-900/20 backdrop-blur-md">
              <div className="flex flex-col lg:flex-row gap-8">
                {/* Visual Demo */}
                <div className="lg:w-1/2 space-y-6">
                  <div>
                    <h3 className="text-xl font-bold text-white mb-2">Composant B : `BotStatusIndicator`</h3>
                    <p className="text-sm text-muted-foreground">
                      Indicateur de télémétrie locale du bot, affichant son état (pulsant), le temps de réponse et la dernière synchronisation.
                    </p>
                  </div>

                  <div className="p-8 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-center min-h-[160px]">
                    <BotStatusIndicator
                      status={botStatus}
                      latencyMs={botLatency}
                      lastHeartbeat={botHeartbeat}
                      className="w-full max-w-md"
                    />
                  </div>

                  {/* Interactive Knobs */}
                  <div className="grid grid-cols-3 gap-4 p-4 rounded-lg bg-slate-900/40 border border-white/5 text-xs">
                    <div>
                      <label className="block text-muted-foreground mb-1 font-semibold">Statut :</label>
                      <select
                        value={botStatus}
                        onChange={(e) => setBotStatus(e.target.value as any)}
                        className="w-full bg-slate-950 border border-white/10 rounded px-2.5 py-1 focus:outline-none focus:border-primary text-white"
                      >
                        <option value="running">Running</option>
                        <option value="stopped">Stopped</option>
                        <option value="error">Error</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-muted-foreground mb-1 font-semibold font-semibold">Ping Latence (ms) :</label>
                      <input
                        type="number"
                        value={botLatency}
                        onChange={(e) => setBotLatency(Number(e.target.value))}
                        className="w-full bg-slate-950 border border-white/10 rounded px-2.5 py-1 focus:outline-none focus:border-primary text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-muted-foreground mb-1 font-semibold font-semibold">Dernier Beat :</label>
                      <input
                        type="text"
                        value={botHeartbeat}
                        onChange={(e) => setBotHeartbeat(e.target.value)}
                        className="w-full bg-slate-950 border border-white/10 rounded px-2.5 py-1 focus:outline-none focus:border-primary text-white"
                      />
                    </div>
                  </div>
                </div>

                {/* Docs & Code */}
                <div className="lg:w-1/2 flex flex-col justify-between">
                  <div className="space-y-4">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                      Documentation & Props API
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left border-collapse">
                        <thead>
                          <tr className="border-b border-white/10 text-muted-foreground font-semibold">
                            <th className="pb-2">Prop</th>
                            <th className="pb-2">Type</th>
                            <th className="pb-2">Défaut</th>
                            <th className="pb-2">Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">status</td>
                            <td className="py-2 text-muted-foreground">"running" | "stopped" | "error"</td>
                            <td className="py-2">—</td>
                            <td className="py-2">État du processus bot local</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">latencyMs</td>
                            <td className="py-2 text-muted-foreground">number</td>
                            <td className="py-2">—</td>
                            <td className="py-2">Latence réseau en ms</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">lastHeartbeat</td>
                            <td className="py-2 text-muted-foreground">string</td>
                            <td className="py-2">—</td>
                            <td className="py-2">Heure du dernier battement de cœur</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="mt-6">
                    <div className="flex items-center justify-between bg-slate-900 border-t border-x border-white/10 px-4 py-2 rounded-t-lg">
                      <span className="text-[10px] font-mono text-muted-foreground">TSX Usage Example</span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            `<BotStatusIndicator\n  status="${botStatus}"\n  latencyMs={${botLatency}}\n  lastHeartbeat="${botHeartbeat}"\n/>`,
                            "Code BotStatusIndicator"
                          )
                        }
                        className="text-[10px] font-semibold text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer"
                      >
                        <Copy className="h-3 w-3" /> Copier
                      </button>
                    </div>
                    <pre className="p-4 rounded-b-lg bg-slate-950 border border-white/10 text-xs font-mono text-muted-foreground overflow-x-auto">
{`<BotStatusIndicator
  status="${botStatus}"
  latencyMs={${botLatency}}
  lastHeartbeat="${botHeartbeat}"
/>`}
                    </pre>
                  </div>
                </div>
              </div>
            </section>

            {/* Component C: ControlPanel */}
            <section className="panel p-8 bg-zinc-900/20 backdrop-blur-md">
              <div className="flex flex-col lg:flex-row gap-8">
                {/* Visual Demo */}
                <div className="lg:w-1/2 space-y-6">
                  <div>
                    <h3 className="text-xl font-bold text-white mb-2">Composant C : `ControlPanel`</h3>
                    <p className="text-sm text-muted-foreground">
                      Panneau de contrôle distant permettant d'arrêter/démarrer l'automate de trading et d'ajuster l'exposition au risque.
                    </p>
                  </div>

                  <div className="p-6 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-center min-h-[220px]">
                    <ControlPanel
                      initialIsRunning={controlRunning}
                      initialRiskPct={controlRisk}
                      onToggleStatus={async (newStatus) => {
                        setControlRunning(newStatus);
                        toast.info(`Ordre envoyé: ${newStatus ? "Démarrage" : "Arrêt"} du bot`);
                      }}
                      onRiskChange={async (newRisk) => {
                        setControlRisk(newRisk);
                        toast.success(`Exposition au risque mise à jour : ${newRisk}%`);
                      }}
                      className="w-full"
                    />
                  </div>
                </div>

                {/* Docs & Code */}
                <div className="lg:w-1/2 flex flex-col justify-between">
                  <div className="space-y-4">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                      Documentation & Action Handlers
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left border-collapse">
                        <thead>
                          <tr className="border-b border-white/10 text-muted-foreground font-semibold">
                            <th className="pb-2">Prop</th>
                            <th className="pb-2">Type</th>
                            <th className="pb-2">Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">initialIsRunning</td>
                            <td className="py-2 text-muted-foreground">boolean</td>
                            <td className="py-2">État initial marche/arrêt du bot</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">initialRiskPct</td>
                            <td className="py-2 text-muted-foreground">number</td>
                            <td className="py-2">Exposition initiale au risque (%)</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">onToggleStatus</td>
                            <td className="py-2 text-muted-foreground">{"(newStatus: boolean) => Promise<void>"}</td>
                            <td className="py-2">Handler asynchrone lors du clic sur Démarrer/Arrêter</td>
                          </tr>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">onRiskChange</td>
                            <td className="py-2 text-muted-foreground">{"(newRisk: number) => Promise<void>"}</td>
                            <td className="py-2">Handler asynchrone lors de la mise à jour du slider</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="mt-6">
                    <div className="flex items-center justify-between bg-slate-900 border-t border-x border-white/10 px-4 py-2 rounded-t-lg">
                      <span className="text-[10px] font-mono text-muted-foreground">TSX Usage Example</span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            `<ControlPanel\n  initialIsRunning={${controlRunning}}\n  initialRiskPct={${controlRisk}}\n  onToggleStatus={async (status) => console.log(status)}\n  onRiskChange={async (risk) => console.log(risk)}\n/>`,
                            "Code ControlPanel"
                          )
                        }
                        className="text-[10px] font-semibold text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer"
                      >
                        <Copy className="h-3 w-3" /> Copier
                      </button>
                    </div>
                    <pre className="p-4 rounded-b-lg bg-slate-950 border border-white/10 text-xs font-mono text-muted-foreground overflow-x-auto">
{`<ControlPanel
  initialIsRunning={${controlRunning}}
  initialRiskPct={${controlRisk}}
  onToggleStatus={handleToggleStatus}
  onRiskChange={handleRiskChange}
/>`}
                    </pre>
                  </div>
                </div>
              </div>
            </section>

            {/* Component D: GDPRBanner */}
            <section className="panel p-8 bg-zinc-900/20 backdrop-blur-md">
              <div className="flex flex-col lg:flex-row gap-8">
                {/* Visual Demo */}
                <div className="lg:w-1/2 space-y-6">
                  <div>
                    <h3 className="text-xl font-bold text-white mb-2">Composant D : `GDPRBanner`</h3>
                    <p className="text-sm text-muted-foreground">
                      Bandeau d'information et de consentement relatif aux cookies et au RGPD.
                    </p>
                  </div>

                  <div className="p-6 rounded-xl bg-slate-950/60 border border-white/5 relative min-h-[160px] flex items-center justify-center">
                    <div className="absolute inset-0 bg-slate-950/30 overflow-hidden flex items-center justify-center p-4">
                      {/* Simulating banner viewport constraints */}
                      <GDPRBanner className="relative bottom-0 inset-x-0 w-full" />
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground text-center italic bg-slate-900/40 border border-white/5 p-3 rounded-lg">
                    Le bandeau de test s'affiche ci-dessus et persiste son état dans votre localStorage.
                  </div>
                </div>

                {/* Docs & Code */}
                <div className="lg:w-1/2 flex flex-col justify-between">
                  <div className="space-y-4">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                      Documentation & RGPD
                    </h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      Ce composant permet la mise en conformité de l'application avec l'article 7 du RGPD (consentement).
                      Il vérifie la clé <code className="font-mono bg-white/5 px-1 rounded text-primary">nexquant_gdpr_consent</code> dans le
                      localStorage lors de son chargement.
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left border-collapse">
                        <thead>
                          <tr className="border-b border-white/10 text-muted-foreground font-semibold">
                            <th className="pb-2">Prop</th>
                            <th className="pb-2">Type</th>
                            <th className="pb-2">Défaut</th>
                            <th className="pb-2">Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-b border-white/5">
                            <td className="py-2 font-mono text-primary">privacyPolicyUrl</td>
                            <td className="py-2 text-muted-foreground">string</td>
                            <td className="py-2">"/legal/privacy"</td>
                            <td className="py-2">Lien vers la politique de confidentialité</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="mt-6">
                    <div className="flex items-center justify-between bg-slate-900 border-t border-x border-white/10 px-4 py-2 rounded-t-lg">
                      <span className="text-[10px] font-mono text-muted-foreground">TSX Usage Example</span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            `<GDPRBanner privacyPolicyUrl="/legal/privacy" />`,
                            "Code GDPRBanner"
                          )
                        }
                        className="text-[10px] font-semibold text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer"
                      >
                        <Copy className="h-3 w-3" /> Copier
                      </button>
                    </div>
                    <pre className="p-4 rounded-b-lg bg-slate-950 border border-white/10 text-xs font-mono text-muted-foreground overflow-x-auto">
{`<GDPRBanner privacyPolicyUrl="/legal/privacy" />`}
                    </pre>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* TAB 3: MIRO BLUEPRINTS */}
        {activeTab === "miro" && (
          <div className="space-y-8">
            <div className="panel p-6 bg-amber-500/5 border border-amber-500/20 rounded-xl text-xs text-amber-400 leading-relaxed">
              <h4 className="font-bold flex items-center gap-1.5 mb-1.5 uppercase tracking-wider">
                💡 Comment utiliser ces plans dans Miro ?
              </h4>
              <p>
                1. Cliquez sur le bouton <strong>"Copier pour Miro"</strong> du panneau désiré.
                <br />
                2. Ouvrez votre tableau Miro, créez une note adhésive (Sticky Note) ou cliquez directement sur le canvas.
                <br />
                3. Appuyez sur <strong>Ctrl+V</strong> (ou Cmd+V) pour coller les éléments structurés sous forme de cadres visuels prêts à être maquettés.
              </p>
            </div>

            {/* Frame 1: Dashboard */}
            <div className="panel p-6 bg-zinc-900/40">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h4 className="font-bold text-white text-base">Frame 1 : Dashboard de Trading & Console Bot</h4>
                  <span className="text-xs text-muted-foreground">Résolution recommandée : 1920x1080px | Fond : #09090B</span>
                </div>
                <button
                  onClick={() =>
                    copyToClipboard(
                      `[FRAME 1: DASHBOARD DE TRADING]\nDimension: 1920 x 1080\nBackground: #09090B (Zinc 950)\n\n-- NAV BAR --\n- Logo (Glow violet): "NexQuant" (Space Grotesk Bold, #FFFFFF)\n- Navigation: Dashboard (Active, #FFFFFF) | Strategies (Inactive, #A1A1AA) | Billing (#A1A1AA) | Settings (#A1A1AA)\n- Widget: [BotStatusIndicator] Status: Operational | Latency: 12ms | Heartbeat: 3s ago\n\n-- METRICS GRID (3 columns) --\n- Column 1: [MetricCard] Title: Sharpe Ratio (90d) | Value: 2.42 | Trend: +0.18 (Green Glow)\n- Column 2: [MetricCard] Title: Profit Factor | Value: 1.84 | Trend: +0.05 (Green Glow)\n- Column 3: [MetricCard] Title: Max Drawdown | Value: -4.12% | Trend: -0.85% (Red Glow)\n\n-- MAIN SECTION (2 columns, 2/3 - 1/3) --\n- Col Left (2/3): [Card] Equity Curve Chart (Recharts line chart with gradient fill #6366f1 + Red shaded Drawdown zones)\n- Col Right (1/3): [ControlPanel] Remote dashboard controller | Play/Pause toggle | Risk per trade slider (0.1% - 5.0%)\n\n-- BOTTOM ROW --\n- Table: Active Positions (Symbol | Side | Size | Entry Price | Current Price | Unrealized P&L)`,
                      "Frame 1 Miro"
                    )
                  }
                  className="px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/95 text-xs font-semibold rounded flex items-center gap-1.5 cursor-pointer"
                >
                  <Copy className="h-3.5 w-3.5" /> Copier pour Miro
                </button>
              </div>
              <pre className="p-4 rounded bg-slate-950 text-xs font-mono text-muted-foreground overflow-x-auto">
{`[FRAME 1: DASHBOARD DE TRADING]
Dimension: 1920 x 1080
Background: #09090B (Zinc 950)

-- NAV BAR --
- Logo (Glow violet): "NexQuant" (Space Grotesk Bold, #FFFFFF)
- Navigation: Dashboard (Active, #FFFFFF) | Strategies (Inactive, #A1A1AA) | Billing (#A1A1AA) | Settings (#A1A1AA)
- Widget: [BotStatusIndicator] Status: Operational | Latency: 12ms | Heartbeat: 3s ago

-- METRICS GRID (3 columns) --
- Column 1: [MetricCard] Title: Sharpe Ratio (90d) | Value: 2.42 | Trend: +0.18 (Green Glow)
- Column 2: [MetricCard] Title: Profit Factor | Value: 1.84 | Trend: +0.05 (Green Glow)
- Column 3: [MetricCard] Title: Max Drawdown | Value: -4.12% | Trend: -0.85% (Red Glow)

-- MAIN SECTION (2 columns, 2/3 - 1/3) --
- Col Left (2/3): [Card] Equity Curve Chart (Recharts line chart with gradient fill #6366f1 + Red shaded Drawdown zones)
- Col Right (1/3): [ControlPanel] Remote dashboard controller | Play/Pause toggle | Risk per trade slider (0.1% - 5.0%)

-- BOTTOM ROW --
- Table: Active Positions (Symbol | Side | Size | Entry Price | Current Price | Unrealized P&L)`}
              </pre>
            </div>

            {/* Frame 2: Strategies */}
            <div className="panel p-6 bg-zinc-900/40">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h4 className="font-bold text-white text-base">Frame 2 : Stratégies & Signaux Webhook</h4>
                  <span className="text-xs text-muted-foreground">Objectif : Configurer les règles de trading et relier TradingView</span>
                </div>
                <button
                  onClick={() =>
                    copyToClipboard(
                      `[FRAME 2: STRATEGIES & WEBHOOKS]\nDimension: 1920 x 1080\nBackground: #09090B (Zinc 950)\n\n-- COLUMN LEFT: STRATEGIES LIST --\n- Card 1: EMA Cross (Active)\n  - Badge: "Tendance"\n  - Toggle: ON (Indigo Glow)\n  - Params: Fast EMA: 9 | Slow EMA: 21 | Timeframe: 5m\n- Card 2: RSI Scalper (Inactive)\n  - Badge: "Contre-tendance"\n  - Toggle: OFF\n  - Params: RSI Period: 14 | Oversold: 30 | Overbought: 70\n\n-- COLUMN RIGHT: WEBHOOK DOCUMENTATION --\n- Input box (Readonly): Webhook URL: "https://nexquant.io/api/public/webhook" + [Copy button]\n- Input box (Hidden): Secret HMAC Key: "nq_sec_*********************" + [Reveal button]\n- Code Block: TradingView JSON Payload Format\n{\n  "secret": "{{USER_SECRET_KEY}}",\n  "symbol": "BTCUSDT",\n  "action": "buy",\n  "risk_pct": 1.5,\n  "leverage": 5\n}`,
                      "Frame 2 Miro"
                    )
                  }
                  className="px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/95 text-xs font-semibold rounded flex items-center gap-1.5 cursor-pointer"
                >
                  <Copy className="h-3.5 w-3.5" /> Copier pour Miro
                </button>
              </div>
              <pre className="p-4 rounded bg-slate-950 text-xs font-mono text-muted-foreground overflow-x-auto">
{`[FRAME 2: STRATEGIES & WEBHOOKS]
Dimension: 1920 x 1080
Background: #09090B (Zinc 950)

-- COLUMN LEFT: STRATEGIES LIST --
- Card 1: EMA Cross (Active)
  - Badge: "Tendance"
  - Toggle: ON (Indigo Glow)
  - Params: Fast EMA: 9 | Slow EMA: 21 | Timeframe: 5m
- Card 2: RSI Scalper (Inactive)
  - Badge: "Contre-tendance"
  - Toggle: OFF
  - Params: RSI Period: 14 | Oversold: 30 | Overbought: 70

-- COLUMN RIGHT: WEBHOOK DOCUMENTATION --
- Input box (Readonly): Webhook URL: "https://nexquant.io/api/public/webhook" + [Copy button]
- Input box (Hidden): Secret HMAC Key: "nq_sec_*********************" + [Reveal button]
- Code Block: TradingView JSON Payload Format
{
  "secret": "{{USER_SECRET_KEY}}",
  "symbol": "BTCUSDT",
  "action": "buy",
  "risk_pct": 1.5,
  "leverage": 5
}`}
              </pre>
            </div>

            {/* Frame 3: Billing */}
            <div className="panel p-6 bg-zinc-900/40">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h4 className="font-bold text-white text-base">Frame 3 : Facturation & Gating (Lemon Squeezy)</h4>
                  <span className="text-xs text-muted-foreground">Objectif : Présentation des offres de prix et de la licence</span>
                </div>
                <button
                  onClick={() =>
                    copyToClipboard(
                      `[FRAME 3: BILLING & GATING]\nDimension: 1920 x 1080\nBackground: #09090B (Zinc 950)\n\n-- TOP WARNING BANNER --\n- Alert Banner (Amber): "Période d'essai gratuite. Il vous reste 4 jours avant l'activation obligatoire d'une licence pour continuer à trader."\n\n-- PRICING GRIDS (3 Columns) --\n- Card 1: "Starter" Plan\n  - Price: $29/month\n  - Features: 1 active bot | Binance Futures | Standard support\n  - Button: "Souscrire"\n- Card 2: "Pro" Plan (Recommended - Indigo Glow border)\n  - Price: $79/month\n  - Features: 3 active bots | Binance & Alpaca | Priority support\n  - Button: "Choisir Pro" (Glow Purple)\n- Card 3: "Professional" Plan\n  - Price: $199/month\n  - Features: Unlimited bots | All Brokers | Ultra-fast execution API\n  - Button: "Contacter le support commerciale"`,
                      "Frame 3 Miro"
                    )
                  }
                  className="px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/95 text-xs font-semibold rounded flex items-center gap-1.5 cursor-pointer"
                >
                  <Copy className="h-3.5 w-3.5" /> Copier pour Miro
                </button>
              </div>
              <pre className="p-4 rounded bg-slate-950 text-xs font-mono text-muted-foreground overflow-x-auto">
{`[FRAME 3: BILLING & GATING]
Dimension: 1920 x 1080
Background: #09090B (Zinc 950)

-- TOP WARNING BANNER --
- Alert Banner (Amber): "Période d'essai gratuite. Il vous reste 4 jours avant l'activation obligatoire d'une licence pour continuer à trader."

-- PRICING GRIDS (3 Columns) --
- Card 1: "Starter" Plan
  - Price: $29/month
  - Features: 1 active bot | Binance Futures | Standard support
  - Button: "Souscrire"
- Card 2: "Pro" Plan (Recommended - Indigo Glow border)
  - Price: $79/month
  - Features: 3 active bots | Binance & Alpaca | Priority support
  - Button: "Choisir Pro" (Glow Purple)
- Card 3: "Professional" Plan
  - Price: $199/month
  - Features: Unlimited bots | All Brokers | Ultra-fast execution API
  - Button: "Contacter le support commerciale"`}
              </pre>
            </div>

            {/* Frame 4: Settings & GDPR */}
            <div className="panel p-6 bg-zinc-900/40">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h4 className="font-bold text-white text-base">Frame 4 : Paramètres du Profil & Conformité RGPD</h4>
                  <span className="text-xs text-muted-foreground">Objectif : Sécurité des clés API, export des données et droit à l'oubli</span>
                </div>
                <button
                  onClick={() =>
                    copyToClipboard(
                      `[FRAME 4: SETTINGS & GDPR]\nDimension: 1920 x 1080\nBackground: #09090B (Zinc 950)\n\n-- API KEY VAULT SECTION --\n- Form: Add Binance / Alpaca API Keys\n- Warning Card (Green): "Vos clés sont cryptées en base de données avec l'algorithme AES-256."\n\n-- GDPR & PRIVACY CONTROL PANEL --\n- Column 1: Droit à la portabilité (Export de données)\n  - Button: "Exporter mes données (JSON)"\n  - Sticky Note: "Envoie un e-mail contenant l'archive complète des positions passées, logs de trading et configurations."\n- Column 2: Droit à l'oubli (Suppression définitive)\n  - Button: "Supprimer définitivement mon compte" (Red Crimson)\n  - Sticky Note: "Révoque immédiatement toutes les connexions de bots, supprime le compte et efface les clés API du Vault."\n- Retention note: "Les logs techniques système de vos bots locaux sont purgés de nos serveurs après 90 jours."`,
                      "Frame 4 Miro"
                    )
                  }
                  className="px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/95 text-xs font-semibold rounded flex items-center gap-1.5 cursor-pointer"
                >
                  <Copy className="h-3.5 w-3.5" /> Copier pour Miro
                </button>
              </div>
              <pre className="p-4 rounded bg-slate-950 text-xs font-mono text-muted-foreground overflow-x-auto">
{`[FRAME 4: SETTINGS & GDPR]
Dimension: 1920 x 1080
Background: #09090B (Zinc 950)

-- API KEY VAULT SECTION --
- Form: Add Binance / Alpaca API Keys
- Warning Card (Green): "Vos clés sont cryptées en base de données avec l'algorithme AES-256."

-- GDPR & PRIVACY CONTROL PANEL --
- Column 1: Droit à la portabilité (Export de données)
  - Button: "Exporter mes données (JSON)"
  - Sticky Note: "Envoie un e-mail contenant l'archive complète des positions passées, logs de trading et configurations."
- Column 2: Droit à l'oubli (Suppression définitive)
  - Button: "Supprimer définitivement mon compte" (Red Crimson)
  - Sticky Note: "Révoque immédiatement toutes les connexions de bots, supprime le compte et efface les clés API du Vault."
- Retention note: "Les logs techniques système de vos bots locaux sont purgés de nos serveurs après 90 jours."`}
              </pre>
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-white/10 px-6 py-6 text-xs text-muted-foreground mt-12">
        <div className="max-w-7xl mx-auto flex flex-wrap justify-between gap-4">
          <span>© {new Date().getFullYear()} NexQuant — Design System Charter</span>
          <span className="font-mono">v1.0.0 · build 2026</span>
        </div>
      </footer>
    </div>
  );
}
