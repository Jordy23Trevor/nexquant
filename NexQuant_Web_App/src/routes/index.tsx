import { createFileRoute, Link } from "@tanstack/react-router";
import { Activity, Brain, LineChart, Shield, Zap, Globe2, ArrowRight, CheckCircle2 } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "NexQuant — Trading algorithmique adaptatif" },
      { name: "description", content: "NexQuant : robot de trading multi-actifs (Crypto, Actions, Forex) avec moteur adaptatif, NLP et dashboard temps réel." },
      { property: "og:title", content: "NexQuant — Trading algorithmique adaptatif" },
      { property: "og:description", content: "Surveillez votre bot en direct : P&L, positions, régime de marché et signaux NLP." },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background grid + glow */}
      <div className="absolute inset-0 grid-bg opacity-60 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[600px] rounded-full bg-primary/20 blur-[140px] -z-0" />
      <div className="absolute top-40 right-10 w-[500px] h-[500px] rounded-full bg-accent/10 blur-[120px] -z-0" />

      {/* Nav */}
      <header className="relative z-10 flex items-center justify-between px-6 lg:px-12 py-5">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-gradient-to-br from-primary to-accent grid place-items-center">
            <Activity className="w-4 h-4 text-background" />
          </div>
          <span className="text-lg font-semibold tracking-tight">NexQuant</span>
        </Link>
        <nav className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
          <a href="#features" className="hover:text-foreground">Fonctionnalités</a>
          <a href="#brokers" className="hover:text-foreground">Brokers</a>
          <a href="#engine" className="hover:text-foreground">Moteur</a>
        </nav>
        <Link to="/auth" className="text-sm px-4 py-2 rounded-md bg-card border border-border hover:bg-surface-2">
          Se connecter
        </Link>
      </header>

      {/* Hero */}
      <section className="relative z-10 px-6 lg:px-12 pt-16 pb-24 max-w-7xl mx-auto">
        <div className="flex flex-col items-center text-center">
          <div className="inline-flex items-center gap-2 text-xs px-3 py-1 rounded-full bg-card border border-border text-muted-foreground mb-6">
            <span className="badge-dot text-success">en direct</span>
            Bot v1.0 — multi-actifs · multi-brokers
          </div>
          <h1 className="text-5xl md:text-7xl font-semibold tracking-tight leading-[1.05] max-w-4xl">
            Trading algorithmique <span className="gradient-text">adaptatif</span>,
            piloté par signal NLP.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
            NexQuant orchestre votre stratégie sur Crypto, Actions US et Forex. Bascule
            automatique entre suivi de tendance et retour à la moyenne, gestion du risque
            par fraction de Kelly, et dashboard de supervision temps réel.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link to="/auth" className="group inline-flex items-center gap-2 px-5 py-3 rounded-md bg-primary text-primary-foreground font-medium glow-primary">
              Ouvrir le dashboard
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <a href="#features" className="px-5 py-3 rounded-md border border-border bg-card hover:bg-surface-2">
              Voir les fonctionnalités
            </a>
          </div>

          {/* Mock terminal */}
          <div className="mt-16 w-full max-w-5xl panel p-1 glow-primary rounded-xl">
            <div className="rounded-lg bg-background/80 backdrop-blur p-6 font-mono text-xs md:text-sm text-left">
              <div className="flex items-center gap-2 pb-4 border-b border-border mb-4">
                <span className="w-3 h-3 rounded-full bg-destructive/60" />
                <span className="w-3 h-3 rounded-full bg-warning/60" />
                <span className="w-3 h-3 rounded-full bg-success/60" />
                <span className="ml-3 text-muted-foreground">nexquant://session/live</span>
                <span className="ml-auto text-success badge-dot">RUNNING</span>
              </div>
              <pre className="text-muted-foreground leading-relaxed overflow-x-auto"><span className="text-accent">[regime]</span>{"  "}BTCUSDT → <span className="text-foreground">TRENDING</span> (conf 0.87, dir ↑){"\n"}<span className="text-accent">[nlp]   </span>{"  "}news sentiment: +0.42 · "Fed pauses hikes"{"\n"}<span className="text-success">[entry] </span>{"  "}LONG  BTCUSDT 0.082 @ 67,420.50 — kelly 0.18{"\n"}<span className="text-accent">[regime]</span>{"  "}EURUSD  → RANGING (conf 0.71){"\n"}<span className="text-success">[exit]  </span>{"  "}SHORT EURUSD +0.34% (+$48.21){"\n"}<span className="text-foreground">[equity]</span>{"  "}{"$"}12,438.20  ·  P&L 24h <span className="ticker-glow-up">+2.41%</span>{"\n"}<span className="text-warning">[risk]  </span>{"  "}drawdown 1.8% — within limits{"\n"}</pre>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 px-6 lg:px-12 py-24 max-w-7xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-center">
          Un moteur, <span className="gradient-text">trois marchés</span>, zéro angle mort.
        </h2>
        <div className="mt-14 grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          <FeatureCard icon={<Brain />} title="Régime adaptatif"
            desc="Détection automatique Trending / Ranging / Volatile et bascule de stratégie en temps réel." />
          <FeatureCard icon={<Zap />} title="Parseur NLP"
            desc="Classification sémantique des règles avec sentence-transformers pour apprentissage autonome." />
          <FeatureCard icon={<Globe2 />} title="Multi-brokers"
            desc="Binance Futures, Alpaca Markets, Paper Forex. Un seul moteur, exécution unifiée." />
          <FeatureCard icon={<Shield />} title="Risque maîtrisé"
            desc="Sizing par fraction de Kelly, hard stops sur drawdown, kill-switch global." />
          <FeatureCard icon={<LineChart />} title="Dashboard temps réel"
            desc="P&L, équity curve, positions, régime, logs — tout en direct, latence < 1s." />
          <FeatureCard icon={<Activity />} title="Sentiment fondamental"
            desc="Module d'actualités intégré : score de sentiment news pondéré dans les décisions." />
        </div>
      </section>

      {/* Brokers */}
      <section id="brokers" className="relative z-10 px-6 lg:px-12 py-16 max-w-7xl mx-auto">
        <div className="panel p-10 text-center">
          <div className="text-xs uppercase tracking-widest text-muted-foreground">Brokers supportés</div>
          <div className="mt-6 flex flex-wrap justify-center items-center gap-8 text-lg font-mono">
            <BrokerPill name="Binance Futures" />
            <BrokerPill name="Alpaca Markets" />
            <BrokerPill name="Paper Forex" />
          </div>
          <ul className="mt-10 grid md:grid-cols-3 gap-4 text-left text-sm">
            {["Testnet & Live switch", "Webhooks externes (TradingView)", "Reporting fiscal exportable"].map((t) => (
              <li key={t} className="flex items-start gap-2 text-muted-foreground">
                <CheckCircle2 className="w-4 h-4 mt-0.5 text-success" /> {t}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* CTA */}
      <section id="engine" className="relative z-10 px-6 lg:px-12 py-24 max-w-5xl mx-auto text-center">
        <h2 className="text-4xl font-semibold tracking-tight">
          Branchez votre bot. <span className="gradient-text">Surveillez en direct.</span>
        </h2>
        <p className="mt-4 text-muted-foreground">
          Le bot Python pousse ses métriques via l'API publique. Le dashboard se met à jour
          en continu — aucune configuration côté frontend.
        </p>
        <Link to="/auth" className="mt-8 inline-flex items-center gap-2 px-6 py-3 rounded-md bg-primary text-primary-foreground font-medium glow-primary">
          Créer un compte gratuit <ArrowRight className="w-4 h-4" />
        </Link>
      </section>

      <footer className="relative z-10 border-t border-border px-6 lg:px-12 py-6 text-xs text-muted-foreground flex flex-wrap justify-between gap-4">
        <span>© {new Date().getFullYear()} NexQuant — Trading Intelligence</span>
        <span className="font-mono">v1.0 · build {new Date().toISOString().slice(0, 10)}</span>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="panel p-6 hover:border-primary/40 transition-colors">
      <div className="w-10 h-10 rounded-md bg-primary/10 border border-primary/20 grid place-items-center text-primary">
        {icon}
      </div>
      <h3 className="mt-4 text-lg font-medium">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{desc}</p>
    </div>
  );
}

function BrokerPill({ name }: { name: string }) {
  return (
    <span className="px-4 py-2 rounded-md bg-card border border-border text-foreground/90">
      {name}
    </span>
  );
}
