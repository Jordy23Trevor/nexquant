import React from "react";
import { HelpCircle, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  isPositive?: boolean;
  tooltipText: string;
  glowColor?: "indigo" | "emerald" | "rose" | "cyan";
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  isPositive = true,
  tooltipText,
  glowColor = "indigo",
  className,
}) => {
  const glowMap = {
    indigo: "hover:shadow-[0_0_25px_rgba(99,102,241,0.18)] hover:border-primary/50",
    emerald: "hover:shadow-[0_0_25px_rgba(16,185,129,0.18)] hover:border-success/50",
    rose: "hover:shadow-[0_0_25px_rgba(244,63,94,0.18)] hover:border-destructive/50",
    cyan: "hover:shadow-[0_0_25px_rgba(34,211,238,0.18)] hover:border-accent/50",
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border border-border bg-card/40 p-6 backdrop-blur-md transition-all duration-300",
        glowMap[glowColor],
        className
      )}
    >
      <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold uppercase tracking-wider">
        <span>{title}</span>
        <div className="group relative cursor-pointer">
          <HelpCircle className="h-4 w-4 text-muted-foreground/60 transition-colors hover:text-foreground" />
          <span className="pointer-events-none absolute right-0 top-6 w-48 rounded bg-popover p-2 text-[10px] text-popover-foreground opacity-0 shadow-xl border border-border backdrop-blur-md transition-all duration-200 group-hover:opacity-100 z-50">
            {tooltipText}
          </span>
        </div>
      </div>

      <div className="mt-4 flex items-baseline justify-between">
        <span className="text-3xl font-bold font-mono text-foreground tracking-tight">
          {value}
        </span>
        {change && (
          <span
            className={cn(
              "flex items-center gap-1 text-xs font-semibold",
              isPositive ? "text-success ticker-glow-up" : "text-destructive ticker-glow-down"
            )}
          >
            {isPositive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
            {change}
          </span>
        )}
      </div>

      {/* Subtle bottom border glow effect */}
      <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
    </div>
  );
};

export default MetricCard;
