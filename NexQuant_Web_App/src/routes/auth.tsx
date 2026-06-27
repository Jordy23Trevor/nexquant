import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable";
import { toast } from "sonner";
import { Activity, Loader2 } from "lucide-react";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Connexion — NexQuant" },
      { name: "description", content: "Connectez-vous à votre dashboard NexQuant." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) navigate({ to: "/dashboard" });
    });
  }, [navigate]);

  async function handleEmail(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({
          email, password,
          options: { emailRedirectTo: window.location.origin + "/dashboard" },
        });
        if (error) throw error;
        toast.success("Compte créé. Vérifiez votre email si la confirmation est activée.");
        navigate({ to: "/dashboard" });
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        navigate({ to: "/dashboard" });
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Échec de l'authentification");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle() {
    setLoading(true);
    const result = await lovable.auth.signInWithOAuth("google", { redirect_uri: window.location.origin + "/dashboard" });
    if (result.error) {
      toast.error("Échec de la connexion Google");
      setLoading(false);
      return;
    }
    if (result.redirected) return;
    navigate({ to: "/dashboard" });
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 relative overflow-hidden">
      <div className="absolute inset-0 grid-bg opacity-40 -z-0" />
      <div className="absolute top-1/3 -left-40 w-[600px] h-[600px] rounded-full bg-primary/20 blur-[140px] -z-0" />

      {/* Left panel (visual) */}
      <div className="hidden lg:flex flex-col justify-between p-12 relative z-10 border-r border-border">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-gradient-to-br from-primary to-accent grid place-items-center">
            <Activity className="w-4 h-4 text-background" />
          </div>
          <span className="text-lg font-semibold">NexQuant</span>
        </Link>
        <div>
          <h2 className="text-3xl font-semibold tracking-tight max-w-md">
            Votre poste de commande <span className="gradient-text">algorithmique</span>.
          </h2>
          <p className="mt-3 text-muted-foreground max-w-md">
            Connectez-vous pour suivre votre bot en temps réel : P&L, positions ouvertes,
            régime de marché et journal d'exécution.
          </p>
          <div className="mt-8 panel p-4 font-mono text-xs text-muted-foreground">
            <div className="text-success badge-dot">SESSION READY</div>
            <div className="mt-2">→ broker: binance · testnet</div>
            <div>→ pairs: BTCUSDT, ETHUSDT, EURUSD</div>
            <div>→ regime engine: <span className="text-accent">adaptive-v1</span></div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">© NexQuant Trading Intelligence</p>
      </div>

      {/* Right panel (form) */}
      <div className="flex items-center justify-center p-6 lg:p-12 relative z-10">
        <div className="w-full max-w-sm">
          <Link to="/" className="lg:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-md bg-gradient-to-br from-primary to-accent grid place-items-center">
              <Activity className="w-4 h-4 text-background" />
            </div>
            <span className="text-lg font-semibold">NexQuant</span>
          </Link>

          <h1 className="text-2xl font-semibold">
            {mode === "signin" ? "Se connecter" : "Créer un compte"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {mode === "signin"
              ? "Accédez à votre dashboard de trading."
              : "Lancez votre dashboard NexQuant en 30 secondes."}
          </p>

          <button onClick={handleGoogle} disabled={loading}
            className="mt-6 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md border border-border bg-card hover:bg-surface-2 transition disabled:opacity-50">
            <GoogleIcon /> Continuer avec Google
          </button>

          <div className="flex items-center gap-3 my-6 text-xs text-muted-foreground">
            <div className="flex-1 h-px bg-border" /> ou <div className="flex-1 h-px bg-border" />
          </div>

          <form onSubmit={handleEmail} className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground">Email</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full px-3 py-2.5 rounded-md bg-card border border-border focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Mot de passe</label>
              <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full px-3 py-2.5 rounded-md bg-card border border-border focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground font-medium glow-primary disabled:opacity-50">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {mode === "signin" ? "Se connecter" : "Créer le compte"}
            </button>
          </form>

          <button onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
            className="mt-6 text-sm text-muted-foreground hover:text-foreground">
            {mode === "signin" ? "Pas encore de compte ? S'inscrire" : "Déjà inscrit ? Se connecter"}
          </button>
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.49h4.84a4.14 4.14 0 0 1-1.79 2.72v2.26h2.9c1.7-1.57 2.69-3.88 2.69-6.63z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.95-2.18l-2.9-2.26c-.8.54-1.83.86-3.05.86-2.34 0-4.32-1.58-5.03-3.71H.96v2.33A9 9 0 0 0 9 18z"/>
      <path fill="#FBBC05" d="M3.97 10.71A5.4 5.4 0 0 1 3.68 9c0-.59.1-1.17.29-1.71V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3.01-2.33z"/>
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58A9 9 0 0 0 9 0 9 9 0 0 0 .96 4.96l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
    </svg>
  );
}
