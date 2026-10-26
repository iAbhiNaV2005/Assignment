import React from "react";

interface KPICardProps {
  title: string;
  value: string | number | null;
  unit?: string;
  subtitle?: string;
  badge?: {
    text: string;
    variant: "neutral" | "success" | "warning" | "danger" | "info";
  };
  icon?: React.ReactNode;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  unit,
  subtitle,
  badge,
  icon,
}) => {
  const badgeColors = {
    neutral: "bg-slate-800 text-slate-300 border-slate-700",
    success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    warning: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    danger: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    info: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
  };

  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 shadow-sm backdrop-blur-sm transition-all hover:border-slate-700">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">{title}</span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-white">
          {value !== null && value !== undefined ? value : "—"}
        </span>
        {unit && <span className="text-xs font-medium text-slate-400">{unit}</span>}
      </div>

      <div className="mt-2 flex items-center justify-between">
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
        {badge && (
          <span
            className={`rounded-md border px-1.5 py-0.5 text-[11px] font-semibold ${
              badgeColors[badge.variant]
            }`}
          >
            {badge.text}
          </span>
        )}
      </div>
    </div>
  );
};
