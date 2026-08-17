import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { getDashboardData, saveBrokerCredentials } from "@/lib/nexquant.functions";
import { toast } from "sonner";
import { Settings, Shield, Key, DownloadCloud, Trash2, Cpu, User } from "lucide-react";

const settingsTranslations = {
  fr: {
    title: "Paramètres du compte",
    desc: "Configurez vos clés d'API, vos préférences et gérez vos données personnelles",
    brokerConfig: "Configuration du Broker & Clés API",
    announcements: "Annonces Importantes",
    profilePrefs: "Profil & Préférences",
    uuid: "Identifiant Compte (UUID)",
    theme: "Thème de l'interface",
    light: "Clair",
    dark: "Sombre",
    notif: "Alertes Emails",
    notifSub: "Exécution de trades & erreurs critiques",
    gdpr: "Conformité RGPD",
    gdprSub: "Conformément au RGPD, vous avez le droit d'accéder, de rectifier ou de supprimer vos données personnelles.",
    export: "Exporter mes données",
    delete: "Supprimer mon compte",
    announcement1Date: "28 Juin 2026",
    announcement1Text: "Intégration Bêta des webhooks TradingView terminée. Vous pouvez désormais automatiser vos propres scripts via la page Stratégies.",
    announcement2Date: "15 Juin 2026",
    announcement2Text: "Maintenance serveur prévue ce week-end. Le trading ne sera pas affecté, mais l'interface web pourrait subir des latences.",
    loading: "Chargement des paramètres...",
    ingestTitle: "Connecter un bot Python local",
    ingestHide: "Masquer",
    ingestShow: "Afficher les instructions",
    ingestDesc: "Le bot pousse ses métriques via un endpoint public en utilisant votre",
    ingestCopy: "Copier l'URL de l'endpoint",
    copied: "URL copiée"
  },
  en: {
    title: "Account Settings",
    desc: "Configure your API keys, preferences and manage your personal data",
    brokerConfig: "Broker Configuration & API Keys",
    announcements: "Important Announcements",
    profilePrefs: "Profile & Preferences",
    uuid: "Account Identifier (UUID)",
    theme: "Interface Theme",
    light: "Light",
    dark: "Dark",
    notif: "Email Alerts",
    notifSub: "Trade execution & critical errors",
    gdpr: "GDPR Compliance",
    gdprSub: "In accordance with GDPR, you have the right to access, rectify or delete your personal data.",
    export: "Export my data",
    delete: "Delete my account",
    announcement1Date: "June 28, 2026",
    announcement1Text: "Beta integration of TradingView webhooks completed. You can now automate your own scripts via the Strategies page.",
    announcement2Date: "June 15, 2026",
    announcement2Text: "Server maintenance scheduled for this weekend. Trading will not be affected, but the web interface might experience latency.",
    loading: "Loading settings...",
    ingestTitle: "Connect a local Python bot",
    ingestHide: "Hide",
    ingestShow: "Show instructions",
    ingestDesc: "The bot pushes its metrics via a public endpoint using your",
    ingestCopy: "Copy endpoint URL",
    copied: "URL copied"
  },
  es: {
    title: "Configuración de la cuenta",
    desc: "Configure sus claves API, preferencias y gestione sus datos personales",
    brokerConfig: "Configuración de Broker y Claves API",
    announcements: "Anuncios Importantes",
    profilePrefs: "Perfil y Preferencias",
    uuid: "Identificador de cuenta (UUID)",
    theme: "Tema de la interfaz",
    light: "Claro",
    dark: "Oscuro",
    notif: "Alertas por correo",
    notifSub: "Ejecución de operaciones y errores críticos",
    gdpr: "Cumplimiento de RGPD",
    gdprSub: "De acuerdo con el RGPD, tiene derecho a acceder, rectificar o eliminar sus datos personales.",
    export: "Exportar mis datos",
    delete: "Eliminar mi cuenta",
    announcement1Date: "28 de Junio de 2026",
    announcement1Text: "Integración Beta de webhooks de TradingView completada. Ahora puede automatizar sus propios scripts a través de la página de Estrategias.",
    announcement2Date: "15 de Junio de 2026",
    announcement2Text: "Mantenimiento del servidor programado para este fin de semana. Las operaciones no se verán afectadas, pero la interfaz web puede experimentar latencia.",
    loading: "Cargando configuraciones...",
    ingestTitle: "Conectar un bot Python local",
    ingestHide: "Ocultar",
    ingestShow: "Mostrar instrucciones",
    ingestDesc: "El bot envía sus métricas a través de un endpoint público utilizando su",
    ingestCopy: "Copiar URL del endpoint",
    copied: "URL copiada"
  }
};

export const Route = createFileRoute("/_authenticated/settings")({
  head: () => ({ meta: [{ title: "Paramètres — NexQuant" }] }),
  component: SettingsPage,
});

function SettingsPage() {
  const fetchData = useServerFn(getDashboardData);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => fetchData(),
  });

  const [theme, setTheme] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("theme") || "dark";
    }
    return "dark";
  });

  const [lang, setLang] = useState<"fr" | "en" | "es">("fr");

  const [notif, setNotif] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("lang") as "fr" | "en" | "es";
      if (stored && stored !== lang) setLang(stored);
    }
    const handleThemeChange = () => {
      setTheme(localStorage.getItem("theme") || "dark");
    };
    const handleLangChange = () => {
      setLang((localStorage.getItem("lang") as "fr" | "en" | "es") || "fr");
    };

    window.addEventListener("themeChange", handleThemeChange);
    window.addEventListener("langChange", handleLangChange);
    return () => {
      window.removeEventListener("themeChange", handleThemeChange);
      window.removeEventListener("langChange", handleLangChange);
    };
  }, []);

  const handleThemeToggle = (newTheme: string) => {
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    const root = window.document.documentElement;
    if (newTheme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    window.dispatchEvent(new Event("themeChange"));
  };

  const t = settingsTranslations[lang] || settingsTranslations.fr;

  if (isError) {
    return <div className="p-6 text-rose-500 font-mono text-sm">Erreur de chargement: {error?.message || "Accès non autorisé"}</div>;
  }

  if (isLoading || !data) {
    return <div className="p-6 text-zinc-500 animate-pulse font-mono text-sm">{t.loading}</div>;
  }

  return (
    <div className="p-4 lg:p-6 max-w-5xl mx-auto space-y-6">
      <div className="mb-2">
        <h1 className="text-[15px] font-bold text-zinc-100 dark:text-zinc-100 font-technical tracking-tight">{t.title}</h1>
        <p className="text-[11px] text-zinc-500 mt-0.5">{t.desc}</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="md:col-span-2 space-y-6">
          
          {/* Broker Settings */}
          <div className="panel p-5 rounded-xl border border-white/10 bg-zinc-900/40 backdrop-blur-md">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-indigo-400" />
                <h2 className="font-semibold text-zinc-800 dark:text-white">{t.brokerConfig}</h2>
              </div>
            </div>
            <BrokerSettingsForm userBroker={data.userBroker} lang={lang} />
          </div>

          {/* Annonces Importantes */}
          <div className="panel p-5 rounded-xl border border-indigo-500/20 bg-indigo-500/5 backdrop-blur-md">
            <h2 className="font-semibold text-indigo-500 dark:text-indigo-300 mb-3 text-sm flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
              {t.announcements}
            </h2>
            <div className="space-y-3">
              <div className="bg-zinc-950/50 p-3 rounded-lg border border-white/5">
                <span className="text-[10px] text-indigo-400 font-mono mb-1 block">{t.announcement1Date}</span>
                <p className="text-xs text-zinc-700 dark:text-zinc-300">{t.announcement1Text}</p>
              </div>
              <div className="bg-zinc-950/50 p-3 rounded-lg border border-white/5">
                <span className="text-[10px] text-zinc-500 font-mono mb-1 block">{t.announcement2Date}</span>
                <p className="text-xs text-zinc-600 dark:text-zinc-400">{t.announcement2Text}</p>
              </div>
            </div>
          </div>

          {/* Ingestion Help */}
          <IngestHelp userId={data.profile?.id} lang={lang} />

        </div>

        {/* Right Column */}
        <div className="space-y-6">
          
          {/* Profil & Préférences (Notifications & Thème) */}
          <div className="panel p-5 rounded-xl border border-white/10 bg-zinc-900/40 backdrop-blur-md">
            <div className="flex items-center gap-2 mb-4">
              <User className="w-4 h-4 text-emerald-400" />
              <h2 className="font-semibold text-zinc-800 dark:text-white">{t.profilePrefs}</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <span className="block font-medium text-[11px] text-zinc-500 dark:text-zinc-400 mb-1">{t.uuid}</span>
                <span className="block font-mono text-[10px] bg-zinc-950 py-1.5 px-2 rounded select-all break-all text-zinc-500 border border-white/5">
                  {data.profile?.id}
                </span>
              </div>

              <div className="flex items-center justify-between border-t border-white/5 pt-4">
                <span className="text-[11px] font-medium text-zinc-700 dark:text-zinc-300">{t.theme}</span>
                <div className="flex bg-zinc-950 rounded-lg p-0.5 border border-white/5">
                  <button onClick={() => handleThemeToggle("light")} className={`px-2 py-1 text-[10px] rounded-md transition ${theme === "light" ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"}`}>{t.light}</button>
                  <button onClick={() => handleThemeToggle("dark")} className={`px-2 py-1 text-[10px] rounded-md transition ${theme === "dark" ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"}`}>{t.dark}</button>
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-white/5 pt-4">
                <div>
                  <span className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-300">{t.notif}</span>
                  <span className="block text-[9px] text-zinc-500">{t.notifSub}</span>
                </div>
                <div onClick={() => setNotif(!notif)} className={`w-8 h-4 rounded-full relative cursor-pointer border transition-colors ${notif ? 'bg-emerald-500/20 border-emerald-500/50' : 'bg-zinc-800 border-white/10'}`}>
                  <div className={`w-2.5 h-2.5 rounded-full bg-white absolute top-[2px] transition-all ${notif ? 'right-1' : 'left-1'}`}></div>
                </div>
              </div>
            </div>
          </div>

          {/* GDPR / Conformité */}
          <div className="panel p-5 rounded-xl border border-white/10 bg-zinc-900/40 backdrop-blur-md">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-indigo-400" />
              <h2 className="font-semibold text-zinc-800 dark:text-white">{t.gdpr}</h2>
            </div>
            <p className="text-[10px] text-zinc-500 mb-4 leading-relaxed">
              {t.gdprSub}
            </p>
            <div className="space-y-2">
              <button onClick={() => toast.info("Téléchargement de vos données en cours...")} className="w-full py-2 px-3 rounded-lg border border-white/10 bg-zinc-950 text-zinc-300 text-[11px] flex items-center justify-center gap-2 hover:bg-white/5 transition">
                <DownloadCloud className="w-3.5 h-3.5" />
                {t.export}
              </button>
              <button onClick={() => toast.error("Procédure de suppression irréversible initiée.")} className="w-full py-2 px-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-400 text-[11px] flex items-center justify-center gap-2 hover:bg-rose-500/20 transition">
                <Trash2 className="w-3.5 h-3.5" />
                {t.delete}
              </button>
            </div>
          </div>

          {/* Bot Version */}
          <div className="flex items-center justify-center gap-2 text-[10px] text-zinc-600 font-mono">
            <Cpu className="w-3 h-3" />
            NexQuant Trading Engine v2.1.0-beta
          </div>

        </div>
      </div>
    </div>
  );
}

function IngestHelp({ userId, lang }: { userId?: string, lang: string }) {
  const [open, setOpen] = useState(false);
  const url = typeof window !== "undefined" ? `${window.location.origin}/api/public/ingest` : "/api/public/ingest";
  const t = settingsTranslations[lang as "fr" | "en" | "es"] || settingsTranslations.fr;
  return (
    <details onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)} className="panel p-5 rounded-xl border border-white/10 bg-zinc-900/40 backdrop-blur-md">
      <summary className="cursor-pointer flex items-center justify-between">
        <span className="font-semibold text-sm text-zinc-100">{t.ingestTitle}</span>
        <span className="text-xs text-indigo-400 font-medium">{open ? t.ingestHide : t.ingestShow}</span>
      </summary>
      <div className="mt-4 space-y-3 text-sm">
        <p className="text-zinc-400 text-xs">
          {t.ingestDesc} <code className="font-mono text-[10px] bg-zinc-950 border border-white/10 px-1.5 py-0.5 rounded text-indigo-300">user_id</code>.
        </p>
        <pre className="font-mono text-[10px] bg-zinc-950/70 border border-white/5 rounded-md p-4 overflow-x-auto text-zinc-400">
{`POST ${url}
Content-Type: application/json
x-user-id: ${userId || '<votre-uuid>'}

{
  "user_id": "${userId || '<votre-uuid>'}",
  "kind": "equity",          // equity | position | log | regime | heartbeat
  "payload": { "equity": 12438.20 }
}`}
        </pre>
        <button onClick={() => { navigator.clipboard.writeText(url); toast.success(t.copied); }}
          className="text-[11px] px-3 py-1.5 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition">
          {t.ingestCopy}
        </button>
      </div>
    </details>
  );
}

function BrokerSettingsForm({ userBroker, lang }: { userBroker: any, lang: string }) {
  const [brokerType, setBrokerType] = useState<"binance" | "alpaca" | "mt5">(
    userBroker?.broker_type || "binance"
  );
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  
  // MT5 specific
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState("");
  const [path, setPath] = useState("C:\\\\Program Files\\\\MetaTrader 5\\\\terminal64.exe");

  const [isSaving, setIsSaving] = useState(false);
  const saveCredentials = useServerFn(saveBrokerCredentials);
  const qc = useQueryClient();

  const labels = {
    fr: {
      selectBroker: "Sélectionner votre Courtier",
      apiKey: "Clé API",
      apiSecret: "Secret API",
      apiKeySaved: "•••••••••••••••• (sauvegardé)",
      apiSecretSaved: "•••••••••••••••• (sauvegardé)",
      apiKeyPlaceholder: "Entrez votre clé API",
      apiSecretPlaceholder: "Entrez votre secret API",
      saveBtn: "Enregistrer la Configuration",
      savingBtn: "Sauvegarde en cours...",
      successMsg: "Configuration du broker sauvegardée !",
      mt5Info: "Renseignez vos identifiants courtier.",
      manageBinance: "Gérer mes clés sur Binance ↗",
      manageAlpaca: "Gérer mes clés sur Alpaca ↗"
    },
    en: {
      selectBroker: "Select your Broker",
      apiKey: "API Key",
      apiSecret: "API Secret",
      apiKeySaved: "•••••••••••••••• (saved)",
      apiSecretSaved: "•••••••••••••••• (saved)",
      apiKeyPlaceholder: "Enter your API Key",
      apiSecretPlaceholder: "Enter your API Secret",
      saveBtn: "Save Configuration",
      savingBtn: "Saving...",
      successMsg: "Broker configuration saved!",
      mt5Info: "Fill in your broker credentials.",
      manageBinance: "Manage my keys on Binance ↗",
      manageAlpaca: "Manage my keys on Alpaca ↗"
    },
    es: {
      selectBroker: "Seleccione su Broker",
      apiKey: "Clave API",
      apiSecret: "Secreto API",
      apiKeySaved: "•••••••••••••••• (guardado)",
      apiSecretSaved: "•••••••••••••••• (guardado)",
      apiKeyPlaceholder: "Ingrese su clave API",
      apiSecretPlaceholder: "Ingrese su secreto API",
      saveBtn: "Guardar Configuración",
      savingBtn: "Guardando...",
      successMsg: "¡Configuración de broker guardada!",
      mt5Info: "Complete sus credenciales de broker.",
      manageBinance: "Gestionar mis claves en Binance ↗",
      manageAlpaca: "Gestionar mis claves en Alpaca ↗"
    }
  };

  const l = labels[lang as "fr" | "en" | "es"] || labels.fr;

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
      toast.success(l.successMsg);
      setApiKey("");
      setApiSecret("");
      setPassword("");
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (err: any) {
      toast.error(`Erreur: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 text-sm">
      <div>
        <label className="block text-[11px] uppercase tracking-wider font-medium text-zinc-500 mb-2">
          {l.selectBroker}
        </label>
        <div className="grid grid-cols-3 gap-2">
          {(["binance", "alpaca", "mt5"] as const).map((b) => (
            <button
              key={b}
              type="button"
              onClick={() => setBrokerType(b)}
              className={`py-2.5 rounded-lg border text-center text-[11px] font-medium capitalize transition ${
                brokerType === b
                  ? "bg-indigo-500/15 border-indigo-500/50 text-indigo-300 shadow-[0_0_10px_rgba(99,102,241,0.1)]"
                  : "bg-zinc-950/50 border-white/5 text-zinc-400 hover:bg-white/5"
              }`}
            >
              {b === "mt5" ? "MetaTrader 5" : b}
            </button>
          ))}
        </div>
        <div className="mt-2 text-right">
          {brokerType === "binance" && <a href={`https://www.binance.com/${lang}/my/settings/api-management`} target="_blank" rel="noreferrer" className="text-[10px] text-indigo-400 hover:underline">{l.manageBinance}</a>}
          {brokerType === "alpaca" && <a href="https://app.alpaca.markets/api-keys" target="_blank" rel="noreferrer" className="text-[10px] text-indigo-400 hover:underline">{l.manageAlpaca}</a>}
          {brokerType === "mt5" && <span className="text-[10px] text-zinc-500">{l.mt5Info}</span>}
        </div>
      </div>

      {brokerType !== "mt5" ? (
        <div className="space-y-4">
          <div>
            <label className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-400 mb-1">
              {l.apiKey}
            </label>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={userBroker?.broker_type === brokerType ? l.apiKeySaved : l.apiKeyPlaceholder}
              className="w-full bg-zinc-950/50 border border-white/10 rounded-lg px-3 py-2 text-[12px] text-zinc-200 focus:outline-none focus:border-indigo-500/50 transition"
              required={!userBroker}
            />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-400 mb-1">
              {l.apiSecret}
            </label>
            <input
              type="password"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder={userBroker?.broker_type === brokerType ? l.apiSecretSaved : l.apiSecretPlaceholder}
              className="w-full bg-zinc-950/50 border border-white/10 rounded-lg px-3 py-2 text-[12px] text-zinc-200 focus:outline-none focus:border-indigo-500/50 transition"
              required={!userBroker}
            />
          </div>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-400 mb-1">Identifiant MT5 (Login)</label>
            <input type="text" value={login} onChange={(e) => setLogin(e.target.value)} placeholder="Ex: 384002" className="w-full bg-zinc-950/50 border border-white/10 rounded-lg px-3 py-2 text-[12px] text-zinc-200 focus:outline-none focus:border-indigo-500/50 transition" required />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-400 mb-1">Mot de Passe MT5</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Mot de passe" className="w-full bg-zinc-950/50 border border-white/10 rounded-lg px-3 py-2 text-[12px] text-zinc-200 focus:outline-none focus:border-indigo-500/50 transition" required />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-400 mb-1">Serveur MT5</label>
            <input type="text" value={server} onChange={(e) => setServer(e.target.value)} placeholder="Ex: FusionMarkets-Demo" className="w-full bg-zinc-950/50 border border-white/10 rounded-lg px-3 py-2 text-[12px] text-zinc-200 focus:outline-none focus:border-indigo-500/50 transition" required />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-400 mb-1">Chemin Executable MT5</label>
            <input type="text" value={path} onChange={(e) => setPath(e.target.value)} placeholder="Ex: C:\\Program Files\\..." className="w-full bg-zinc-950/50 border border-white/10 rounded-lg px-3 py-2 text-[12px] text-zinc-200 focus:outline-none focus:border-indigo-500/50 transition" required />
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isSaving}
        className="w-full py-2.5 rounded-xl bg-indigo-500 text-white text-[12px] font-medium hover:bg-indigo-600 transition disabled:opacity-50 shadow-[0_0_15px_rgba(99,102,241,0.2)]"
      >
        {isSaving ? l.savingBtn : l.saveBtn}
      </button>
    </form>
  );
}
