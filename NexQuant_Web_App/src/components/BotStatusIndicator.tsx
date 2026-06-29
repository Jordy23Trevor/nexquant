import React from "react";
import { cn } from "@/lib/utils";

export type BotStatusType = "running" | "stopped" | "error";

export interface BotStatusIndicatorProps {
  status: BotStatusType;
  lastHeartbeat: string;
  latencyMs: number;
  className?: string;
}

export const BotStatusIndicator: React.FC<BotStatusIndicatorProps> = ({
  status,
  lastHeartbeat,
  latencyMs,
  className,
}) => {
  const statusConfig = {
    running: {
      color: "bg-success",
      glow: "shadow-[0_0_12px_rgba(116,238,152,0.6)]",
      pulse: "animate-ping",
      text: "Opérationnel",
      textColor: "text-success",
    },
    stopped: {
      color: "bg-muted-foreground/60",
      glow: "shadow-[0_0_12px_rgba(161,161,170,0.4)]",
      pulse: "",
      text: "En Veille",
      textColor: "text-muted-foreground",
    },
    error: {
      color: "bg-destructive",
      glow: "shadow-[0_0_12px_rgba(239,68,68,0.6)]",
      pulse: "animate-pulse",
      text: "Erreur Système",
      textColor: "text-destructive",
    },
  };

  const current = statusConfig[status];

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-6 rounded-lg border border-border bg-card/60 p-4 backdrop-blur-md",
        className
      )}
    >
      <div className="flex items-center gap-3">
        <div className="relative flex h-3.5 w-3.5 items-center justify-center">
          {status === "running" && (
            <span
              className={cn(
                "absolute inline-flex h-full w-full rounded-full opacity-75",
                current.color,
                current.pulse
              )}
            />
          )}
          <span
            className={cn(
              "relative inline-flex h-2.5 w-2.5 rounded-full",
              current.color,
              current.glow
            )}
          />
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold leading-tight">
            Statut Bot
          </span>
          <span className={cn("text-xs font-bold", current.textColor)}>
            {current.text}
          </span>
        </div>
      </div>

      <div className="hidden sm:block h-8 w-[1px] bg-border" />

      <div className="flex flex-col">
        <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold leading-tight">
          Latence API
        </span>
        <span className="text-xs font-bold font-mono text-foreground">
          {latencyMs} ms
        </span>
      </div>

      <div className="hidden sm:block h-8 w-[1px] bg-border" />

      <div className="flex flex-col">
        <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold leading-tight">
          Dernière Activité
        </span>
        <span className="text-xs text-foreground font-mono">
          {lastHeartbeat}
        </span>
      </div>
    </div>
  );
};

export default BotStatusIndicator;
