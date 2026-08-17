import { createFileRoute, Outlet, redirect, Link, useLocation } from "@tanstack/react-router";
import { supabase } from "@/integrations/supabase/client";
import { Bell, AlertTriangle, Sun, Moon, Globe } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { getDashboardData } from "@/lib/nexquant.functions";
import { useEffect, useState } from "react";

const translations = {
  fr: {
    dashboard: "Tableau de bord",
    history: "Historique",
    strategies: "Stratégies",
    billing: "Facturation",
    settings: "Paramètres",
    botActive: "Bot ACTIF",
    botInactive: "Bot INACTIF",
    trialBanner: "Il reste {days} jours avant obligation de licence.",
    activateSub: "Activer un abonnement →"
  },
  en: {
    dashboard: "Dashboard",
    history: "History",
    strategies: "Strategies",
    billing: "Billing",
    settings: "Settings",
    botActive: "Bot ACTIVE",
    botInactive: "Bot INACTIVE",
    trialBanner: "{days} days left before license is required.",
    activateSub: "Activate subscription →"
  },
  es: {
    dashboard: "Panel de control",
    history: "Historial",
    strategies: "Estrategias",
    billing: "Facturación",
    settings: "Configuración",
    botActive: "Bot ACTIVO",
    botInactive: "Bot INACTIVO",
    trialBanner: "Quedan {days} días antes del requisito de licencia.",
    activateSub: "Activar suscripción →"
  }
};

export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  beforeLoad: async () => {
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) throw redirect({ to: "/auth" });
    return { user: data.user };
  },
  component: AuthenticatedLayout,
});

function AuthenticatedLayout() {
  const loc = useLocation();
  const fetchData = useServerFn(getDashboardData);

  const [theme, setTheme] = useState("dark");

  const [lang, setLang] = useState<"fr" | "en" | "es">("fr");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedTheme = localStorage.getItem("theme");
      if (storedTheme && storedTheme !== theme) setTheme(storedTheme);
      const storedLang = localStorage.getItem("lang") as "fr" | "en" | "es";
      if (storedLang && storedLang !== lang) setLang(storedLang);
    }
    const root = window.document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    const handleThemeChange = () => {
      setTheme(localStorage.getItem("theme") || "dark");
    };
    window.addEventListener("themeChange", handleThemeChange);
    return () => window.removeEventListener("themeChange", handleThemeChange);
  }, []);

  useEffect(() => {
    localStorage.setItem("lang", lang);
    // Custom event to notify pages of language change
    window.dispatchEvent(new Event("langChange"));
  }, [lang]);

  const { data } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => fetchData(),
    refetchInterval: 15000,
  });

  const running = data?.status?.is_running ?? false;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const profile = data?.profile as any;
  const trialEnd = profile?.trial_end as string | undefined;
  const daysLeft = trialEnd ? Math.max(0, Math.ceil((new Date(trialEnd).getTime() - Date.now()) / (24 * 3600 * 1000))) : 0;
  // BUG-D09 FIX: Lire la latence depuis bot_status au lieu d'un '12ms' hardcodé
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cycleLatency = (data?.status as any)?.cycle_latency_ms;
  const latencyLabel = cycleLatency != null ? `· ${Math.round(cycleLatency)}ms` : "";
  // BUG-D12 FIX: Badge notification conditionnel sur erreurs récentes (< 30 min)
  const recentErrors = (data?.logs ?? []).filter((l: { level: string; created_at: string }) => {
    const isAlert = l.level === "error" || l.level === "warn";
    const isRecent = (Date.now() - new Date(l.created_at).getTime()) < 30 * 60 * 1000;
    return isAlert && isRecent;
  });
  const hasAlerts = recentErrors.length > 0;

  const t = translations[lang] || translations.fr;

  const TABS = [
    { id: "/dashboard", label: t.dashboard },
    { id: "/history", label: t.history },
    { id: "/strategies", label: t.strategies },
    { id: "/billing", label: t.billing },
    { id: "/settings", label: t.settings },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      {/* Top Bar */}
      <div className="bg-zinc-950 dark:bg-[#0d0d0f] border-b border-white/10 dark:border-white/5 px-4 h-11 flex items-center justify-between shrink-0 sticky top-0 z-50 transition-colors">
        <div className="flex items-center gap-5">
          <span className="font-technical font-bold text-[15px] text-indigo-500 tracking-tight">NexQuant</span>
          <div className="flex gap-0.5">
            {TABS.map(tItem => (
              <Link 
                key={tItem.id}
                to={tItem.id}
                className={`px-3 py-1.5 rounded-md border text-[11px] font-medium transition-all ${
                  loc.pathname.includes(tItem.id) 
                    ? "border-indigo-500/30 bg-indigo-500/10 text-zinc-50" 
                    : "border-transparent bg-transparent text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {tItem.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Language Selector */}
          <div className="flex items-center gap-1 bg-zinc-900 border border-white/10 rounded px-1.5 py-0.5">
            <Globe className="w-3 h-3 text-zinc-500" />
            <select 
              value={lang} 
              onChange={(e) => setLang(e.target.value as "fr" | "en" | "es")} 
              className="bg-transparent text-zinc-300 text-[10px] font-medium focus:outline-none cursor-pointer border-none p-0"
            >
              <option value="fr" className="bg-zinc-950 text-zinc-300">FR</option>
              <option value="en" className="bg-zinc-950 text-zinc-300">EN</option>
              <option value="es" className="bg-zinc-950 text-zinc-300">ES</option>
            </select>
          </div>

          {/* Theme Toggle */}
          <button 
            onClick={() => {
              const nextTheme = theme === "dark" ? "light" : "dark";
              setTheme(nextTheme);
              localStorage.setItem("theme", nextTheme);
              window.dispatchEvent(new Event("themeChange"));
            }} 
            className="text-zinc-400 hover:text-zinc-200 transition cursor-pointer p-1 rounded hover:bg-white/5"
            title="Changer de thème"
          >
            {theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          </button>

          <Link to="/settings" className="relative cursor-pointer text-zinc-400 hover:text-zinc-200 transition">
            <Bell className="w-4 h-4" />
            {/* BUG-D12 FIX: Badge conditionnel sur erreurs/warnings récents (< 30min) */}
            {hasAlerts && (
              <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-indigo-500 border border-zinc-950"></span>
            )}
          </Link>
          <div className={`flex items-center gap-1.5 text-[11px] font-medium ${running ? 'text-emerald-400' : 'text-zinc-500'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${running ? 'bg-emerald-400' : 'bg-zinc-500'}`}></span>
            {/* BUG-D09 FIX: latence dynamique depuis bot_status.cycle_latency_ms */}
            {running ? t.botActive : t.botInactive} {running && latencyLabel}
          </div>
          <div className="w-7 h-7 rounded-full bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-[11px] text-indigo-300 font-bold">
            {profile?.display_name?.charAt(0).toUpperCase() || 'U'}
          </div>
        </div>
      </div>

      {/* Trial Banner */}
      {trialEnd && daysLeft <= 14 && (
        <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-1.5 text-[11px] text-amber-500 flex items-center gap-1.5 shrink-0">
          <AlertTriangle className="w-3.5 h-3.5" />
          {t.trialBanner.replace("{days}", daysLeft.toString())}
          <Link to="/billing" className="text-indigo-400 underline ml-1 hover:text-indigo-300">{t.activateSub}</Link>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-y-auto bg-background text-foreground transition-colors">
        <Outlet />
      </div>
    </div>
  );
}
