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
  const badgeStyles = {
    neutral: "bg-[#181b20] text-[#9ca3af] border-[#2a2e37]",
    success: "bg-[#092a1d] text-[#10b981] border-[#125338]",
    warning: "bg-[#2c1d0a] text-[#f59e0b] border-[#543813]",
    danger: "bg-[#2f1017] text-[#f43f5e] border-[#581f2a]",
    info: "bg-[#0c2438] text-[#38bdf8] border-[#164164]",
  };

  return (
    <div className="flex flex-col justify-between rounded-lg border border-[#22262e] bg-[#121417] p-4 transition-colors hover:border-[#2e333d]">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-[#9ca3af]">{title}</span>
        {icon && <div className="text-[#6b7280]">{icon}</div>}
      </div>

      <div className="mt-2.5 flex items-baseline gap-1.5">
        <span className="tabular-nums text-2xl font-bold tracking-tight text-[#f3f4f6]">
          {value !== null && value !== undefined ? value : "—"}
        </span>
        {unit && <span className="text-xs font-medium text-[#6b7280]">{unit}</span>}
      </div>

      <div className="mt-2.5 flex items-center justify-between gap-2 pt-2 border-t border-[#1b1e24]">
        {subtitle ? (
          <p className="truncate text-[11px] text-[#6b7280]">{subtitle}</p>
        ) : (
          <span />
        )}
        {badge && (
          <span
            className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
              badgeStyles[badge.variant]
            }`}
          >
            {badge.text}
          </span>
        )}
      </div>
    </div>
  );
};
