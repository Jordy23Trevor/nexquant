import React, { useState, useEffect } from "react";
import { Play, Square, AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ControlPanelProps {
  initialIsRunning: boolean;
  onToggleStatus: (newStatus: boolean) => Promise<void>;
  initialRiskPct: number;
  onRiskChange: (newRisk: number) => Promise<void>;
  className?: string;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  initialIsRunning,
  onToggleStatus,
  initialRiskPct,
  onRiskChange,
  className,
}) => {
  const [isRunning, setIsRunning] = useState(initialIsRunning);
  const [risk, setRisk] = useState(initialRiskPct);
  const [loading, setLoading] = useState(false);

  // BUG-D04 FIX: Resynchroniser l'état local si le serveur rapporte un changement
  // (ex: bot crashé, arrêté depuis un autre onglet, ou refetch de 15s)
  useEffect(() => { setIsRunning(initialIsRunning); }, [initialIsRunning]);
  useEffect(() => { setRisk(initialRiskPct); }, [initialRiskPct]);

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

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card/50 p-6 backdrop-blur-md",
        className
      )}
    >
      <h3 className="text-base font-bold font-mono text-foreground mb-6 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        Console de Pilotage à distance
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Toggle principal */}
        <div className="flex flex-col justify-between p-4 rounded-lg bg-background/40 border border-border/50">
          <div>
            <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider block">
              État du bot
            </span>
            <p className="text-[11px] text-muted-foreground mt-1.5 leading-relaxed">
              Le changement d'état sera répercuté lors du prochain cycle de polling (30s maximum).
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
                Arrêter le Bot
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                Lancer le Bot
              </>
            )}
          </button>
        </div>

        {/* Configuration du Risque */}
        <div className="flex flex-col justify-between p-4 rounded-lg bg-background/40 border border-border/50">
          <div>
            <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider block">
              Exposition par Trade
            </span>
            <div className="flex items-center justify-between mt-3">
              <span className="text-2xl font-bold font-mono text-foreground">
                {risk.toFixed(1)}%
              </span>
              {risk > 2.5 && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-warning/10 text-warning border border-warning/20 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" /> Élevé (Max rec: 2.5%)
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
              Appliquer à chaud
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
