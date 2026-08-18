import React, { useState, useEffect } from "react";
import { Play, Square, AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const translations = {
  fr: {
    title: "Console de Pilotage à distance",
    botState: "État du bot",
    botStateDesc: "Le changement d'état sera répercuté lors du prochain cycle de polling (30s maximum).",
    stopBot: "Arrêter le Bot",
    startBot: "Lancer le Bot",
    expo: "Exposition par Trade",
    high: "Élevé (Max rec: 2.5%)",
    applyHot: "Appliquer à chaud"
  },
  en: {
    title: "Remote Control Console",
    botState: "Bot status",
    botStateDesc: "State change will be reflected on the next polling cycle (30s maximum).",
    stopBot: "Stop Bot",
    startBot: "Start Bot",
    expo: "Exposure per Trade",
    high: "High (Max rec: 2.5%)",
    applyHot: "Apply Hot"
  },
  es: {
    title: "Consola de Control Remoto",
    botState: "Estado del bot",
    botStateDesc: "El cambio de estado se reflejará en el próximo ciclo de sondeo (máximo 30s).",
    stopBot: "Detener Bot",
    startBot: "Iniciar Bot",
    expo: "Exposición por Trade",
    high: "Alto (Máx rec: 2.5%)",
    applyHot: "Aplicar en caliente"
  }
};

export interface ControlPanelProps {
  initialIsRunning: boolean;
  onToggleStatus: (newStatus: boolean) => Promise<void>;
  initialRiskPct: number;
  onRiskChange: (newRisk: number) => Promise<void>;
  initialBrokerType?: string;
  initialTestnet?: boolean;
  onBrokerChange?: (brokerType: string, testnet: boolean) => Promise<void>;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  initialIsRunning,
  onToggleStatus,
  initialRiskPct,
  onRiskChange,
  initialBrokerType,
  initialTestnet,
  onBrokerChange,
  className,
}) => {
  const [isRunning, setIsRunning] = useState(initialIsRunning);
  const [risk, setRisk] = useState(initialRiskPct);
  const [brokerType, setBrokerType] = useState(initialBrokerType || "binance");
  const [testnet, setTestnet] = useState(initialTestnet ?? true);
  const [loading, setLoading] = useState(false);

  const [lang, setLang] = useState<"fr" | "en" | "es">("fr");
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("lang") as "fr" | "en" | "es";
      if (stored && stored !== lang) setLang(stored);
    }
    const handleLangChange = () => {
      setLang((localStorage.getItem("lang") as "fr" | "en" | "es") || "fr");
    };
    window.addEventListener("langChange", handleLangChange);
    return () => window.removeEventListener("langChange", handleLangChange);
  }, []);
  
  const t = translations[lang] || translations.fr;

  // BUG-D04 FIX: Resynchroniser l'état local si le serveur rapporte un changement
  // (ex: bot crashé, arrêté depuis un autre onglet, ou refetch de 15s)
  useEffect(() => { setIsRunning(initialIsRunning); }, [initialIsRunning]);
  useEffect(() => { setRisk(initialRiskPct); }, [initialRiskPct]);
  useEffect(() => { if (initialBrokerType) setBrokerType(initialBrokerType); }, [initialBrokerType]);
  useEffect(() => { if (initialTestnet !== undefined) setTestnet(initialTestnet); }, [initialTestnet]);

  const handleToggle = async () => {
    setLoading(true);
    try {
      await onToggleStatus(!isRunning);
      setIsRunning(!isRunning);
    } catch (err) {
      console.error("Error toggling bot status:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRiskSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRisk(Number(e.target.value));
  };

  const handleApplyRisk = async () => {
    setLoading(true);
    try {
      await onRiskChange(risk);
    } catch (err) {
      console.error("Error applying risk setting:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyBroker = async () => {
    setLoading(true);
    try {
      if (onBrokerChange) {
        await onBrokerChange(brokerType, testnet);
      }
    } catch (err) {
      console.error("Error applying broker setting:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card/50 p-6 backdrop-blur-md",
        className
      )}
    >
      <h3 className="text-base font-bold font-mono text-foreground mb-6 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        {t.title}
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Toggle principal */}
        <div className="flex flex-col justify-between p-4 rounded-lg bg-background/40 border border-border/50">
          <div>
            <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider block">
              {t.botState}
            </span>
            <p className="text-[11px] text-muted-foreground mt-1.5 leading-relaxed">
              {t.botStateDesc}
            </p>
          </div>
          <button
            onClick={handleToggle}
            disabled={loading}
            className={cn(
              "mt-4 w-full flex items-center justify-center gap-2 rounded-lg py-3 font-semibold text-sm transition-all duration-300 cursor-pointer disabled:opacity-60",
              isRunning
                ? "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-[0_0_15px_rgba(239,68,68,0.2)]"
                : "bg-primary text-primary-foreground hover:bg-primary/95 shadow-[0_0_15px_rgba(99,102,241,0.2)]"
            )}
          >
            {loading ? (
              <Loader2 className="h-4.5 w-4.5 animate-spin" />
            ) : isRunning ? (
              <>
                <Square className="h-4 w-4 fill-current" />
                {t.stopBot}
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                {t.startBot}
              </>
            )}
          </button>
        </div>

        {/* Configuration du Risque */}
        <div className="flex flex-col justify-between p-4 rounded-lg bg-background/40 border border-border/50">
          <div>
            <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider block">
              {t.expo}
            </span>
            <div className="flex items-center justify-between mt-3">
              <span className="text-2xl font-bold font-mono text-foreground">
                {risk.toFixed(1)}%
              </span>
              {risk > 2.5 && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-warning/10 text-warning border border-warning/20 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" /> {t.high}
                </span>
              )}
            </div>
          </div>
          <div className="mt-4 flex flex-col gap-2">
            <input
              type="range"
              min="0.1"
              max="5.0"
              step="0.1"
              value={risk}
              onChange={handleRiskSliderChange}
              className="w-full accent-primary cursor-pointer h-1 rounded bg-muted"
            />
            <button
              onClick={handleApplyRisk}
              disabled={loading || risk === initialRiskPct}
              className={cn(
                "mt-2 text-xs font-semibold text-muted-foreground hover:text-foreground bg-muted/50 hover:bg-muted border border-border py-1.5 rounded transition-all cursor-pointer",
                risk === initialRiskPct && "opacity-50 cursor-not-allowed"
              )}
            >
              {t.applyHot}
            </button>
          </div>
        </div>

        {/* Configuration du Broker */}
        <div className="flex flex-col justify-between p-4 rounded-lg bg-background/40 border border-border/50">
          <div>
            <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider block">
              Broker / Environnement
            </span>
            <p className="text-[11px] text-muted-foreground mt-1.5 leading-relaxed">
              Le changement redémarrera le bot automatiquement.
            </p>
          </div>
          <div className="mt-4 flex flex-col gap-2">
            <select
              value={brokerType}
              onChange={(e) => setBrokerType(e.target.value)}
              className="w-full bg-background border border-border rounded p-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="binance">Binance</option>
              <option value="alpaca">Alpaca (Stocks)</option>
              <option value="mt5">MetaTrader 5</option>
            </select>
            <div className="flex items-center gap-2 mt-1">
              <input
                type="checkbox"
                id="testnet-toggle"
                checked={testnet}
                onChange={(e) => setTestnet(e.target.checked)}
                className="rounded border-border bg-background text-primary focus:ring-primary h-4 w-4"
              />
              <label htmlFor="testnet-toggle" className="text-sm font-medium text-foreground cursor-pointer">
                Mode Testnet (Demo)
              </label>
            </div>
            <button
              onClick={handleApplyBroker}
              disabled={loading || (brokerType === initialBrokerType && testnet === initialTestnet)}
              className={cn(
                "mt-2 text-xs font-semibold text-muted-foreground hover:text-foreground bg-muted/50 hover:bg-muted border border-border py-1.5 rounded transition-all cursor-pointer",
                (brokerType === initialBrokerType && testnet === initialTestnet) && "opacity-50 cursor-not-allowed"
              )}
            >
              {t.applyHot || "Appliquer"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
