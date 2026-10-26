import React, { useState } from "react";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Calendar,
  Clock,
  Download,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Activity,
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
} from "lucide-react";
import { DecisionResponse, RevisionsResponse } from "../lib/types";
import { api } from "../lib/api";
import { KPICard } from "./KPICard";

interface DecisionViewProps {
  selectedDate: string;
  setSelectedDate: (date: string) => void;
  cutoffTime: string;
  setCutoffTime: (cutoff: string) => void;
  decisionData: DecisionResponse | null;
  revisionsData: RevisionsResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const DecisionView: React.FC<DecisionViewProps> = ({
  selectedDate,
  setSelectedDate,
  cutoffTime,
  setCutoffTime,
  decisionData,
  revisionsData,
  isLoading,
  onRefresh,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<"timeseries" | "revisions" | "table">("timeseries");

  const summary = decisionData?.summary;
  const periods = decisionData?.periods || [];

  // Intraday 48 settlement periods data
  const chartData = periods.map((p) => ({
    period: p.settlementPeriod,
    timeLabel: p.startTime.substring(11, 16),
    actual: p.actual,
    forecast: p.forecast,
    error: p.error,
    shortfall: p.shortfall,
    publishTime: p.publishTime ? p.publishTime.substring(11, 16) + " UTC" : "—",
    label: `SP${p.settlementPeriod} (${p.startTime.substring(11, 16)} UTC)`,
  }));

  // Revisions data alignment
  const revisionsChartData = (revisionsData?.actuals || []).map((act) => {
    const row: Record<string, any> = {
      period: act.settlementPeriod,
      timeLabel: act.startTime.substring(11, 16),
      actual: act.actual,
    };
    if (revisionsData?.revisions) {
      revisionsData.revisions.forEach((rev) => {
        const match = rev.data?.find((s) => s.settlementPeriod === act.settlementPeriod);
        const colName = rev.isDecisionForecast
          ? "Decision forecast"
          : `Run ${rev.publishTime.substring(11, 16)}`;
        row[colName] = match ? match.forecast : null;
      });
    }
    return row;
  });

  const revisionColors = ["#6b7280", "#9ca3af", "#d1d5db", "#f59e0b", "#a855f7"];

  const handleDateStep = (delta: number) => {
    const current = new Date(selectedDate);
    current.setUTCDate(current.getUTCDate() + delta);
    const yyyy = current.getUTCFullYear();
    const mm = String(current.getUTCMonth() + 1).padStart(2, "0");
    const dd = String(current.getUTCDate()).padStart(2, "0");
    const nextStr = `${yyyy}-${mm}-${dd}`;
    if (nextStr >= "2026-01-01" && nextStr <= "2026-01-31") {
      setSelectedDate(nextStr);
    }
  };

  return (
    <div className="space-y-4">
      {/* Trading Desk Control Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#22262e] bg-[#121417] p-2.5">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Date Navigation Stepper */}
          <div className="flex items-center rounded border border-[#22262e] bg-[#16181d] px-1.5 py-0.5">
            <button
              onClick={() => handleDateStep(-1)}
              disabled={selectedDate === "2026-01-01"}
              className="rounded p-1 text-[#9ca3af] hover:text-[#f3f4f6] disabled:opacity-30"
              title="Previous Day"
              aria-label="Previous day"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>

            <div className="flex items-center gap-1.5 px-2">
              <Calendar className="h-3.5 w-3.5 text-[#38bdf8]" />
              <input
                type="date"
                min="2026-01-01"
                max="2026-01-31"
                value={selectedDate}
                onChange={(e) => e.target.value && setSelectedDate(e.target.value)}
                className="bg-transparent text-xs font-semibold text-[#f3f4f6] focus:outline-none"
                aria-label="Delivery date"
              />
            </div>

            <button
              onClick={() => handleDateStep(1)}
              disabled={selectedDate === "2026-01-31"}
              className="rounded p-1 text-[#9ca3af] hover:text-[#f3f4f6] disabled:opacity-30"
              title="Next Day"
              aria-label="Next day"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Cutoff Time Input */}
          <div className="flex items-center gap-2 rounded border border-[#22262e] bg-[#16181d] px-2.5 py-1 text-xs">
            <Clock className="h-3.5 w-3.5 text-[#f59e0b]" />
            <div className="flex items-center gap-1.5">
              <label htmlFor="cutoff-input" className="text-[11px] text-[#9ca3af]">
                Decision cutoff (D-1):
              </label>
              <input
                id="cutoff-input"
                type="text"
                pattern="^([01]\d|2[0-3]):([0-5]\d)$"
                value={cutoffTime}
                onChange={(e) => setCutoffTime(e.target.value)}
                className="w-12 rounded border border-[#2a2e37] bg-[#121417] px-1 py-0.5 text-center text-xs font-bold text-[#f3f4f6] focus:border-[#38bdf8] focus:outline-none"
                placeholder="09:00"
                aria-label="Cutoff time"
              />
              <span className="text-[11px] text-[#6b7280]">London time</span>
            </div>
          </div>

          {/* Quick Preset Chips */}
          <div className="hidden items-center gap-1.5 xl:flex">
            <span className="text-[11px] text-[#6b7280]">Quick jump:</span>
            <button
              onClick={() => setSelectedDate("2026-01-10")}
              className="rounded border border-[#22262e] bg-[#16181d] px-2 py-0.5 text-[11px] text-[#9ca3af] transition-colors hover:border-[#38bdf8] hover:text-[#f3f4f6]"
            >
              High wind (10 Jan)
            </button>
            <button
              onClick={() => setSelectedDate("2026-01-24")}
              className="rounded border border-[#22262e] bg-[#16181d] px-2 py-0.5 text-[11px] text-[#9ca3af] transition-colors hover:border-[#f59e0b] hover:text-[#f3f4f6]"
            >
              Peak shortfall (24 Jan)
            </button>
            <button
              onClick={() => setSelectedDate("2026-01-05")}
              className="rounded border border-[#22262e] bg-[#16181d] px-2 py-0.5 text-[11px] text-[#9ca3af] transition-colors hover:border-[#2e333d] hover:text-[#f3f4f6]"
            >
              Balanced day (5 Jan)
            </button>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded border border-[#22262e] bg-[#16181d] px-2.5 py-1 text-xs font-medium text-[#9ca3af] transition-colors hover:bg-[#1f232b] hover:text-[#f3f4f6]"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <a
            href={api.getExportCsvUrl(selectedDate, selectedDate, cutoffTime)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded bg-[#0284c7] px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-[#0369a1]"
          >
            <Download className="h-3 w-3" />
            Export Day CSV
          </a>
        </div>
      </div>

      {/* Decision Status Bar (Anti-Leakage Verification) */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#22262e] border-l-4 border-l-[#0284c7] bg-[#121417] p-3">
        <div className="flex items-start gap-2.5">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#38bdf8]" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-[#f3f4f6]">
                Decision timeline verified for {selectedDate}
              </h3>
              <span className="rounded border border-[#164164] bg-[#0c2438] px-1.5 py-0.2 text-[10px] font-semibold uppercase text-[#38bdf8]">
                Strict cutoff
              </span>
            </div>
            <p className="mt-0.5 text-[11px] text-[#9ca3af]">
              Gate closure cutoff enforced at{" "}
              <span className="font-semibold text-[#f3f4f6]">
                {decisionData?.cutoffUtc.replace("T", " ").replace(":00Z", " UTC")}
              </span>
              . Only forecasts published prior to this timestamp are incorporated, ensuring strict anti-leakage compliance.
            </p>
          </div>
        </div>

        {/* Quick Decision Metrics */}
        <div className="flex items-center gap-3 rounded border border-[#22262e] bg-[#16181d] px-3 py-1">
          <div>
            <span className="text-[10px] text-[#6b7280]">Decision bias</span>
            <p className={`tabular-nums text-xs font-bold ${summary?.biasMw && summary.biasMw > 0 ? "text-[#f59e0b]" : "text-[#10b981]"}`}>
              {summary?.biasMw !== null && summary?.biasMw !== undefined
                ? `${summary.biasMw > 0 ? "+" : ""}${Math.round(summary.biasMw).toLocaleString()} MW`
                : "—"}
            </p>
          </div>
          <div className="h-6 w-px bg-[#22262e]" />
          <div>
            <span className="text-[10px] text-[#6b7280]">P90 shortfall</span>
            <p className="tabular-nums text-xs font-bold text-[#f43f5e]">
              {summary?.shortfallP90Mw ? `${Math.round(summary.shortfallP90Mw)} MW` : "—"}
            </p>
          </div>
        </div>
      </div>

      {/* 5 Peer Metric KPI Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <KPICard
          title="Day mean forecast"
          value={summary?.meanForecastMw !== null && summary?.meanForecastMw !== undefined ? Math.round(summary.meanForecastMw).toLocaleString() : null}
          unit="MW"
          subtitle="Expected generation"
          badge={{ text: "Day-ahead", variant: "info" }}
          icon={<TrendingUp className="h-3.5 w-3.5 text-[#38bdf8]" />}
        />
        <KPICard
          title="Day mean actual"
          value={summary?.meanActualMw !== null && summary?.meanActualMw !== undefined ? Math.round(summary.meanActualMw).toLocaleString() : null}
          unit="MW"
          subtitle="Outturn generation"
          badge={{ text: "Elexon FUELHH", variant: "success" }}
          icon={<Activity className="h-3.5 w-3.5 text-[#10b981]" />}
        />
        <KPICard
          title="Mean absolute error"
          value={summary?.maeMw !== null && summary?.maeMw !== undefined ? Math.round(summary.maeMw).toLocaleString() : null}
          unit="MW"
          subtitle="Typical miss size"
          badge={{ text: "MAE", variant: "neutral" }}
        />
        <KPICard
          title="Day net bias"
          value={
            summary?.biasMw !== null && summary?.biasMw !== undefined
              ? `${summary.biasMw > 0 ? "+" : ""}${Math.round(summary.biasMw).toLocaleString()}`
              : null
          }
          unit="MW"
          subtitle={summary?.biasMw && summary.biasMw > 0 ? "Over-forecast (shortfall)" : "Under-forecast (surplus)"}
          badge={{ text: summary?.biasMw && summary.biasMw > 0 ? "Shortfall risk" : "Surplus", variant: summary?.biasMw && summary.biasMw > 0 ? "warning" : "success" }}
          icon={<AlertTriangle className="h-3.5 w-3.5 text-[#f59e0b]" />}
        />
        <KPICard
          title="P90 shortfall capacity"
          value={summary?.shortfallP90Mw !== null && summary?.shortfallP90Mw !== undefined ? Math.round(summary.shortfallP90Mw).toLocaleString() : null}
          unit="MW"
          subtitle="Safety buffer needed"
          badge={{ text: "90% confidence", variant: "danger" }}
          icon={<ShieldAlert className="h-3.5 w-3.5 text-[#f43f5e]" />}
        />
      </div>

      {/* Sub-tab Navigation */}
      <div className="flex items-center justify-between border-b border-[#22262e] pb-1.5 pt-1">
        <div className="flex items-center gap-1 rounded-lg border border-[#22262e] bg-[#14161b] p-0.5">
          <button
            onClick={() => setActiveSubTab("timeseries")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeSubTab === "timeseries"
                ? "bg-[#22262e] text-[#f3f4f6]"
                : "text-[#9ca3af] hover:text-[#f3f4f6]"
            }`}
          >
            Decision forecast vs actual (48 half-hours)
          </button>
          <button
            onClick={() => setActiveSubTab("revisions")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeSubTab === "revisions"
                ? "bg-[#22262e] text-[#f3f4f6]"
                : "text-[#9ca3af] hover:text-[#f3f4f6]"
            }`}
          >
            Forecast revisions evolution
          </button>
          <button
            onClick={() => setActiveSubTab("table")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeSubTab === "table"
                ? "bg-[#22262e] text-[#f3f4f6]"
                : "text-[#9ca3af] hover:text-[#f3f4f6]"
            }`}
          >
            Settlement periods table (48 periods)
          </button>
        </div>

        <span className="text-[11px] text-[#6b7280]">Power units in Megawatts (MW)</span>
      </div>

      {/* TAB 1: Intraday 48 SP Area Chart */}
      {activeSubTab === "timeseries" && (
        <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h4 className="text-xs font-bold text-[#f3f4f6]">
                Decision forecast tracks actual generation across 48 settlement periods with periodic shortfall
              </h4>
              <p className="text-[11px] text-[#6b7280]">
                {selectedDate} • Elexon FUELHH actuals vs D-1 WINDFOR decision stream (09:00 cutoff) • Power in Megawatts (MW)
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-[#38bdf8]" />
                <span className="text-[#9ca3af]">Decision forecast (MW)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-[#10b981]" />
                <span className="text-[#9ca3af]">Actual outturn (MW)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-[#f43f5e]" />
                <span className="text-[#6b7280]">Shortfall volume (MW)</span>
              </span>
            </div>
          </div>

          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 15, left: 5, bottom: 15 }}>
                <defs>
                  <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="shortfallGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 2" stroke="#1c1f26" />
                <XAxis
                  dataKey="timeLabel"
                  stroke="#6b7280"
                  fontSize={10}
                  tickLine={false}
                  interval={3}
                />
                <YAxis
                  stroke="#6b7280"
                  fontSize={10}
                  domain={[0, "auto"]}
                  tickLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)} GW`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#16191f",
                    borderColor: "#2a2e38",
                    borderRadius: "6px",
                    fontSize: "11px",
                    color: "#f3f4f6",
                  }}
                  formatter={(val: any, name: any) => [
                    `${Number(val).toLocaleString()} MW`,
                    name,
                  ]}
                  labelFormatter={(lbl, items) => {
                    const item = items && items[0] ? items[0].payload : null;
                    return item ? `${item.label} • Published: ${item.publishTime}` : lbl;
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="forecast"
                  name="Decision forecast"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#forecastGrad)"
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual outturn"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="shortfall"
                  name="Shortfall volume"
                  stroke="#f43f5e"
                  strokeWidth={1}
                  fillOpacity={1}
                  fill="url(#shortfallGrad)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 2: Revisions Evolution Chart */}
      {activeSubTab === "revisions" && (
        <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
          <div className="mb-3">
            <h4 className="text-xs font-bold text-[#f3f4f6]">
              Forecast revisions show meteorology updates across runs leading up to gate closure
            </h4>
            <p className="text-[11px] text-[#6b7280]">
              {selectedDate} • Successive WINDFOR publishes prior to cutoff vs final actual outturn • Units: MW
            </p>
          </div>

          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={revisionsChartData} margin={{ top: 10, right: 15, left: 5, bottom: 15 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1c1f26" />
                <XAxis
                  dataKey="timeLabel"
                  stroke="#6b7280"
                  fontSize={10}
                  interval={3}
                />
                <YAxis
                  stroke="#6b7280"
                  fontSize={10}
                  domain={[0, "auto"]}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)} GW`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#16191f",
                    borderColor: "#2a2e38",
                    borderRadius: "6px",
                    fontSize: "11px",
                    color: "#f3f4f6",
                  }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />

                {/* Earlier publishes */}
                {Object.keys(revisionsChartData[0] || {})
                  .filter((k) => k !== "period" && k !== "timeLabel" && k !== "actual" && k !== "Decision forecast")
                  .map((key, idx) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={revisionColors[idx % revisionColors.length]}
                      strokeWidth={1.2}
                      strokeDasharray="3 3"
                      dot={false}
                      isAnimationActive={false}
                    />
                  ))}

                {/* Decision Forecast */}
                <Line
                  type="monotone"
                  dataKey="Decision forecast"
                  stroke="#38bdf8"
                  strokeWidth={2.5}
                  dot={false}
                  isAnimationActive={false}
                />

                {/* Actual Outturn */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual outturn"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 3: 48 Settlement Periods Data Table */}
      {activeSubTab === "table" && (
        <div className="overflow-hidden rounded-lg border border-[#22262e] bg-[#121417]">
          <div className="flex items-center justify-between border-b border-[#22262e] px-4 py-3">
            <div>
              <h4 className="text-xs font-bold text-[#f3f4f6]">48 settlement periods breakdown</h4>
              <p className="text-[11px] text-[#6b7280]">Detailed target outturns, frozen forecasts, and signed procurement errors.</p>
            </div>
            <a
              href={api.getExportCsvUrl(selectedDate, selectedDate, cutoffTime)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 rounded border border-[#2a2e37] bg-[#16181d] px-2.5 py-1 text-xs text-[#9ca3af] transition-colors hover:text-[#f3f4f6]"
            >
              <Download className="h-3 w-3" />
              Download CSV
            </a>
          </div>

          <div className="max-h-[500px] overflow-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 border-b border-[#22262e] bg-[#16181d] text-[11px] text-[#9ca3af]">
                <tr>
                  <th className="py-2 px-3 font-semibold">SP</th>
                  <th className="py-2 px-3 font-semibold">Target time (UTC)</th>
                  <th className="py-2 px-3 text-right font-semibold">Actual (MW)</th>
                  <th className="py-2 px-3 text-right font-semibold">Forecast (MW)</th>
                  <th className="py-2 px-3 text-right font-semibold">Error (MW)</th>
                  <th className="py-2 px-3 text-right font-semibold">Shortfall (MW)</th>
                  <th className="py-2 px-3 font-semibold">Forecast publish time</th>
                  <th className="py-2 px-3 text-center font-semibold">Risk assessment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1c1f26] text-[#d1d5db]">
                {periods.map((p) => {
                  const isShortfall = p.error !== null && p.error > 0;
                  return (
                    <tr key={p.settlementPeriod} className="transition-colors hover:bg-[#16181d]">
                      <td className="py-1.5 px-3 font-mono font-medium text-[#6b7280]">{p.settlementPeriod}</td>
                      <td className="py-1.5 px-3 font-mono text-[#9ca3af]">{p.startTime.substring(11, 16)}</td>
                      <td className="py-1.5 px-3 text-right font-mono font-medium text-[#10b981] tabular-nums">
                        {p.actual !== null ? Math.round(p.actual).toLocaleString() : "—"}
                      </td>
                      <td className="py-1.5 px-3 text-right font-mono font-medium text-[#38bdf8] tabular-nums">
                        {p.forecast !== null ? Math.round(p.forecast).toLocaleString() : "—"}
                      </td>
                      <td
                        className={`py-1.5 px-3 text-right font-mono font-medium tabular-nums ${
                          isShortfall ? "text-[#f59e0b]" : "text-[#9ca3af]"
                        }`}
                      >
                        {p.error !== null ? `${p.error > 0 ? "+" : ""}${Math.round(p.error).toLocaleString()}` : "—"}
                      </td>
                      <td className="py-1.5 px-3 text-right font-mono text-[#f43f5e] tabular-nums">
                        {p.shortfall !== null && p.shortfall > 0 ? Math.round(p.shortfall).toLocaleString() : "0"}
                      </td>
                      <td className="py-1.5 px-3 font-mono text-[11px] text-[#6b7280]">
                        {p.publishTime ? p.publishTime.substring(11, 16) + " UTC" : "—"}
                      </td>
                      <td className="py-1.5 px-3 text-center">
                        {isShortfall ? (
                          <span className="rounded border border-[#581f2a] bg-[#2f1017] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#f43f5e]">
                            Shortfall risk
                          </span>
                        ) : (
                          <span className="rounded border border-[#125338] bg-[#092a1d] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#10b981]">
                            Surplus
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
