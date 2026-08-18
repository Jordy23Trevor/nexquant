import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable";
import { toast } from "sonner";
import { Activity, Loader2, Globe } from "lucide-react";

const translations = {
  fr: {
    signinTitle: "Se connecter",
    signupTitle: "Créer un compte",
    signinDesc: "Accédez à votre dashboard de trading.",
    signupDesc: "Lancez votre dashboard NexQuant en 30 secondes.",
    googleBtn: "Continuer avec Google",
    or: "ou",
    emailLabel: "Email",
    passwordLabel: "Mot de passe",
    signinBtn: "Se connecter",
    signupBtn: "Créer le compte",
    switchSignup: "Pas encore de compte ? S'inscrire",
    switchSignin: "Déjà inscrit ? Se connecter",
    toastSignupSuccess: "Compte créé. Vérifiez votre email si la confirmation est activée.",
    toastGoogleFail: "Échec de la connexion Google",
    toastAuthFail: "Échec de l'authentification",
    slogan: "Votre poste de commande",
    sloganHighlight: "algorithmique",
    sloganDesc: "Connectez-vous pour suivre votre bot en temps réel : P&L, positions ouvertes, régime de marché et journal d'exécution.",
    sessionReady: "SESSION READY",
    broker: "→ broker: binance · testnet",
    pairs: "→ pairs: BTCUSDT, ETHUSDT, EURUSD",
    regime: "→ regime engine:",
    rights: "© NexQuant Trading Intelligence",
  },
  en: {
    signinTitle: "Sign in",
    signupTitle: "Create an account",
    signinDesc: "Access your trading dashboard.",
    signupDesc: "Launch your NexQuant dashboard in 30 seconds.",
    googleBtn: "Continue with Google",
    or: "or",
    emailLabel: "Email",
    passwordLabel: "Password",
    signinBtn: "Sign in",
    signupBtn: "Create account",
    switchSignup: "Don't have an account? Sign up",
    switchSignin: "Already registered? Sign in",
    toastSignupSuccess: "Account created. Check your email if confirmation is enabled.",
    toastGoogleFail: "Google login failed",
    toastAuthFail: "Authentication failed",
    slogan: "Your algorithmic",
    sloganHighlight: "command post",
    sloganDesc: "Sign in to track your bot in real time: P&L, open positions, market regime and execution log.",
    sessionReady: "SESSION READY",
    broker: "→ broker: binance · testnet",
    pairs: "→ pairs: BTCUSDT, ETHUSDT, EURUSD",
    regime: "→ regime engine:",
    rights: "© NexQuant Trading Intelligence",
  },
  es: {
    signinTitle: "Iniciar sesión",
    signupTitle: "Crear una cuenta",
    signinDesc: "Accede a tu panel de trading.",
    signupDesc: "Lanza tu panel NexQuant en 30 segundos.",
    googleBtn: "Continuar con Google",
    or: "o",
    emailLabel: "Correo electrónico",
    passwordLabel: "Contraseña",
    signinBtn: "Iniciar sesión",
    signupBtn: "Crear cuenta",
    switchSignup: "¿Aún no tienes cuenta? Regístrate",
    switchSignin: "¿Ya estás registrado? Inicia sesión",
    toastSignupSuccess: "Cuenta creada. Revisa tu correo si la confirmación está activada.",
    toastGoogleFail: "Error en el inicio de sesión con Google",
    toastAuthFail: "Error de autenticación",
    slogan: "Tu puesto de mando",
    sloganHighlight: "algorítmico",
    sloganDesc: "Inicia sesión para seguir tu bot en tiempo real: P&L, posiciones abiertas, régimen de mercado y registro de ejecución.",
    sessionReady: "SESIÓN LISTA",
    broker: "→ broker: binance · testnet",
    pairs: "→ pairs: BTCUSDT, ETHUSDT, EURUSD",
    regime: "→ motor de régimen:",
    rights: "© NexQuant Trading Intelligence",
  }
};

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
  
  const [lang, setLang] = useState<"fr" | "en" | "es">("fr");
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("lang") as "fr" | "en" | "es";
      if (stored && stored !== lang) setLang(stored);
    }
  }, [lang]);

  const handleLangChange = (newLang: "fr" | "en" | "es") => {
    setLang(newLang);
    localStorage.setItem("lang", newLang);
    window.dispatchEvent(new Event("langChange"));
  };

  const t = translations[lang] || translations.fr;

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
        toast.success(t.toastSignupSuccess);
        navigate({ to: "/dashboard" });
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        navigate({ to: "/dashboard" });
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.toastAuthFail);
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle() {
    setLoading(true);
    const result = await lovable.auth.signInWithOAuth("google", { redirect_uri: window.location.origin + "/dashboard" });
    if (result.error) {
      toast.error(t.toastGoogleFail);
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

      {/* Language Selector Top Right */}
      <div className="absolute top-4 right-4 z-50 flex items-center gap-1 bg-zinc-900 border border-white/10 rounded px-2 py-1">
        <Globe className="w-4 h-4 text-zinc-500" />
        <select 
          value={lang} 
          onChange={(e) => handleLangChange(e.target.value as "fr" | "en" | "es")} 
          className="bg-transparent text-zinc-300 text-xs font-medium focus:outline-none cursor-pointer border-none p-0"
        >
          <option value="fr" className="bg-zinc-950 text-zinc-300">FR</option>
          <option value="en" className="bg-zinc-950 text-zinc-300">EN</option>
          <option value="es" className="bg-zinc-950 text-zinc-300">ES</option>
        </select>
      </div>

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
            {t.slogan} <span className="gradient-text">{t.sloganHighlight}</span>.
          </h2>
          <p className="mt-3 text-muted-foreground max-w-md">
            {t.sloganDesc}
          </p>
          <div className="mt-8 panel p-4 font-mono text-xs text-muted-foreground">
            <div className="text-success badge-dot">{t.sessionReady}</div>
            <div className="mt-2">{t.broker}</div>
            <div>{t.pairs}</div>
            <div>{t.regime} <span className="text-accent">adaptive-v1</span></div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">{t.rights}</p>
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
            {mode === "signin" ? t.signinTitle : t.signupTitle}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {mode === "signin" ? t.signinDesc : t.signupDesc}
          </p>

          <button onClick={handleGoogle} disabled={loading}
            className="mt-6 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md border border-border bg-card hover:bg-surface-2 transition disabled:opacity-50">
            <GoogleIcon /> {t.googleBtn}
          </button>

          <div className="flex items-center gap-3 my-6 text-xs text-muted-foreground">
            <div className="flex-1 h-px bg-border" /> {t.or} <div className="flex-1 h-px bg-border" />
          </div>

          <form onSubmit={handleEmail} className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground">{t.emailLabel}</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full px-3 py-2.5 rounded-md bg-card border border-border focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">{t.passwordLabel}</label>
              <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full px-3 py-2.5 rounded-md bg-card border border-border focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground font-medium glow-primary disabled:opacity-50">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {mode === "signin" ? t.signinBtn : t.signupBtn}
            </button>
          </form>

          <button onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
            className="mt-6 text-sm text-muted-foreground hover:text-foreground">
            {mode === "signin" ? t.switchSignup : t.switchSignin}
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
