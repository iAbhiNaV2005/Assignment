"use client";

import React, { useState, useMemo } from "react";
import {
  Calendar,
  Clock,
  Download,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { DecisionResponse, RevisionsResponse } from "../lib/types";
import { KPICard } from "./KPICard";
import { api } from "../lib/api";

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

  // Step date +/- 1 day
  const handleDateStep = (delta: number) => {
    const curDay = parseInt(selectedDate.split("-")[2], 10);
    const newDay = Math.min(31, Math.max(1, curDay + delta));
    const newDate = `2026-01-${String(newDay).padStart(2, "0")}`;
    setSelectedDate(newDate);
  };

  const summary = decisionData?.summary;
  const periods = decisionData?.periods || [];

  // Memoized chart data for render performance (vercel-react-best-practices)
  const chartData = useMemo(() => {
    return periods.map((p) => {
      const timeLabel = p.startTime.substring(11, 16);
      const act = p.actual !== null ? Math.round(p.actual) : null;
      const fc = p.forecast !== null ? Math.round(p.forecast) : null;
      const err = p.error !== null ? Math.round(p.error) : null;
      const sf = p.shortfall !== null ? Math.round(p.shortfall) : 0;

      return {
        period: p.settlementPeriod,
        label: `Settlement Period ${p.settlementPeriod} (${timeLabel} UTC)`,
        timeLabel,
        actual: act,
        forecast: fc,
        error: err,
        shortfall: sf,
        publishTime: p.publishTime ? p.publishTime.substring(11, 16) + " UTC" : "—",
      };
    });
  }, [periods]);

  // Memoized revisions evolution data (vercel-react-best-practices)
  const revisionsChartData = useMemo(() => {
    const revisionLines = revisionsData?.revisions || [];
    const actualsList = revisionsData?.actuals || [];

    return Array.from({ length: 48 }, (_, i) => {
      const sp = i + 1;
      const actItem = actualsList.find((a) => a.settlementPeriod === sp);
      const point: Record<string, string | number | null> = {
        period: sp,
        timeLabel: `${String(Math.floor(i / 2)).padStart(2, "0")}:${i % 2 === 0 ? "00" : "30"}`,
        actual: actItem && actItem.actual !== null ? Math.round(actItem.actual) : null,
      };

      revisionLines.forEach((rev) => {
        const dp = rev.data.find((d) => d.settlementPeriod === sp);
        const key = rev.isDecisionForecast
          ? "Decision forecast"
          : `Published ${rev.publishTime.substring(11, 16)} UTC`;
        point[key] = dp && dp.forecast !== null ? Math.round(dp.forecast) : null;
      });

      return point;
    });
  }, [revisionsData]);

  const revisionColors = ["#64748b", "#94a3b8", "#a78bfa", "#818cf8", "#f59e0b", "#06b6d4"];

  return (
    <div className="space-y-6">
      {/* Control Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4 shadow-sm backdrop-blur-md">
        <div className="flex flex-wrap items-center gap-3">
          {/* Day Stepper */}
          <div className="flex items-center gap-1 rounded-xl border border-slate-700 bg-slate-950 p-1">
            <button
              onClick={() => handleDateStep(-1)}
              disabled={selectedDate === "2026-01-01"}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-40"
              title="Previous Day"
              aria-label="Previous day"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <div className="flex items-center gap-2 px-2">
              <Calendar className="h-4 w-4 text-cyan-400" />
              <input
                type="date"
                min="2026-01-01"
                max="2026-01-31"
                value={selectedDate}
                onChange={(e) => e.target.value && setSelectedDate(e.target.value)}
                className="bg-transparent text-sm font-semibold text-white focus:outline-none"
                aria-label="Delivery date"
              />
            </div>

            <button
              onClick={() => handleDateStep(1)}
              disabled={selectedDate === "2026-01-31"}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-40"
              title="Next Day"
              aria-label="Next day"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Cutoff Time Input */}
          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-1.5">
            <Clock className="h-4 w-4 text-amber-400" />
            <div className="flex items-center gap-1.5">
              <label htmlFor="cutoff-input" className="text-xs text-slate-400">
                Decision cutoff (D-1):
              </label>
              <input
                id="cutoff-input"
                type="text"
                pattern="^([01]\d|2[0-3]):([0-5]\d)$"
                value={cutoffTime}
                onChange={(e) => setCutoffTime(e.target.value)}
                className="w-14 rounded bg-slate-800 px-1.5 py-0.5 text-center text-xs font-bold text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
                placeholder="09:00"
                aria-label="Cutoff time"
              />
              <span className="text-[11px] text-slate-500">London time</span>
            </div>
          </div>

          {/* Quick presets */}
          <div className="hidden items-center gap-1.5 xl:flex">
            <span className="text-xs text-slate-500">Quick jump:</span>
            <button
              onClick={() => setSelectedDate("2026-01-10")}
              className="rounded-md border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs text-slate-400 hover:border-slate-700 hover:text-cyan-400"
            >
              High wind (10 Jan)
            </button>
            <button
              onClick={() => setSelectedDate("2026-01-24")}
              className="rounded-md border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs text-slate-400 hover:border-slate-700 hover:text-amber-400"
            >
              Peak shortfall (24 Jan)
            </button>
            <button
              onClick={() => setSelectedDate("2026-01-05")}
              className="rounded-md border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs text-slate-400 hover:border-slate-700 hover:text-slate-300"
            >
              Balanced day (5 Jan)
            </button>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-slate-700"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <a
            href={api.getExportCsvUrl(selectedDate, selectedDate, cutoffTime)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm shadow-cyan-600/30 transition hover:bg-cyan-500"
          >
            <Download className="h-3.5 w-3.5" />
            Export Day CSV
          </a>
        </div>
      </div>

      {/* Decision Context Callout Banner */}
      <div className="rounded-2xl border border-cyan-500/20 bg-gradient-to-r from-cyan-950/40 via-slate-900/40 to-blue-950/30 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 rounded-lg bg-cyan-500/10 p-2 text-cyan-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white">
                  Decision timeline verified for {selectedDate}
                </h3>
                <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-cyan-300">
                  Strict cutoff
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-300">
                Gate closure cutoff enforced at{" "}
                <span className="font-semibold text-cyan-200">
                  {decisionData?.cutoffUtc.replace("T", " ").replace(":00Z", " UTC")}
                </span>
                . Only forecasts published prior to this timestamp are incorporated, ensuring strict anti-leakage compliance.
              </p>
            </div>
          </div>

          {/* Quick Stats Pill */}
          <div className="flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2">
            <div>
              <span className="text-[10px] font-medium text-slate-400">Decision bias</span>
              <p className={`text-sm font-bold ${summary?.biasMw && summary.biasMw > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                {summary?.biasMw !== null && summary?.biasMw !== undefined
                  ? `${summary.biasMw > 0 ? "+" : ""}${Math.round(summary.biasMw).toLocaleString()} MW`
                  : "—"}
              </p>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div>
              <span className="text-[10px] font-medium text-slate-400">P90 shortfall</span>
              <p className="text-sm font-bold text-rose-400">
                {summary?.shortfallP90Mw ? `${Math.round(summary.shortfallP90Mw).toLocaleString()} MW` : "—"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Headline KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <KPICard
          title="Day mean forecast"
          value={summary?.meanForecastMw !== null && summary?.meanForecastMw !== undefined ? Math.round(summary.meanForecastMw).toLocaleString() : null}
          unit="MW"
          subtitle="Expected generation"
          badge={{ text: "Day-ahead", variant: "info" }}
          icon={<TrendingUp className="h-4 w-4 text-cyan-400" />}
        />
        <KPICard
          title="Day mean actual"
          value={summary?.meanActualMw !== null && summary?.meanActualMw !== undefined ? Math.round(summary.meanActualMw).toLocaleString() : null}
          unit="MW"
          subtitle="Outturn generation"
          badge={{ text: "Elexon FUELHH", variant: "success" }}
          icon={<CheckCircle2 className="h-4 w-4 text-emerald-400" />}
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
          value={summary?.biasMw !== null && summary?.biasMw !== undefined ? `${summary.biasMw > 0 ? "+" : ""}${Math.round(summary.biasMw).toLocaleString()}` : null}
          unit="MW"
          subtitle={summary?.biasMw && summary.biasMw > 0 ? "Over-forecast (shortfall)" : "Under-forecast"}
          badge={{
            text: summary?.biasMw && summary.biasMw > 0 ? "Shortfall risk" : "Excess wind",
            variant: summary?.biasMw && summary.biasMw > 0 ? "warning" : "success",
          }}
          icon={<AlertTriangle className="h-4 w-4 text-amber-400" />}
        />
        <KPICard
          title="P90 shortfall capacity"
          value={summary?.shortfallP90Mw !== null && summary?.shortfallP90Mw !== undefined ? Math.round(summary.shortfallP90Mw).toLocaleString() : null}
          unit="MW"
          subtitle="Safety buffer needed"
          badge={{ text: "90% confidence", variant: "danger" }}
        />
      </div>

      {/* Chart & Table Navigation Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab("timeseries")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeSubTab === "timeseries"
                ? "bg-slate-800 text-cyan-400 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Decision forecast vs actual (48 half-hours)
          </button>
          <button
            onClick={() => setActiveSubTab("revisions")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeSubTab === "revisions"
                ? "bg-slate-800 text-cyan-400 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Forecast revisions evolution
          </button>
          <button
            onClick={() => setActiveSubTab("table")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeSubTab === "table"
                ? "bg-slate-800 text-cyan-400 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Settlement periods table (48 periods)
          </button>
        </div>

        <span className="text-xs text-slate-500">Power units in Megawatts (MW)</span>
      </div>

      {/* TAB 1: Primary Time Series Chart */}
      {activeSubTab === "timeseries" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-bold text-white">
                Intraday wind generation profile ({selectedDate})
              </h4>
              <p className="text-xs text-slate-400">
                Comparing the frozen day-ahead decision forecast against actual national wind generation.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-cyan-400" />
                <span className="text-slate-300">Decision forecast (MW)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="text-slate-300">Actual outturn (MW)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-500/40" />
                <span className="text-slate-400">Shortfall volume (MW)</span>
              </span>
            </div>
          </div>

          <div className="h-[380px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <defs>
                  <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="shortfallGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="timeLabel"
                  stroke="#64748b"
                  fontSize={11}
                  tickLine={false}
                  interval={3}
                />
                <YAxis
                  stroke="#64748b"
                  fontSize={11}
                  domain={[0, "auto"]}
                  tickLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)} GW`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: "0.75rem",
                    boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
                    fontSize: "12px",
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
                  stroke="#06b6d4"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#forecastGrad)"
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual outturn"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="shortfall"
                  name="Shortfall volume"
                  stroke="#ef4444"
                  strokeWidth={1}
                  fillOpacity={1}
                  fill="url(#shortfallGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 2: Revisions Evolution Chart */}
      {activeSubTab === "revisions" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-bold text-white">
                Forecast revisions prior to gate closure ({selectedDate})
              </h4>
              <p className="text-xs text-slate-400">
                Visualizing how weather models adjusted wind expectations leading up to cutoff time.
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-cyan-400" />
                <span className="text-cyan-300 font-semibold">Final decision forecast</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <span className="text-emerald-300 font-semibold">Actual outturn</span>
              </span>
            </div>
          </div>

          <div className="h-[380px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={revisionsChartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="timeLabel"
                  stroke="#64748b"
                  fontSize={11}
                  interval={3}
                />
                <YAxis
                  stroke="#64748b"
                  fontSize={11}
                  domain={[0, "auto"]}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)} GW`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: "0.75rem",
                    fontSize: "12px",
                  }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />

                {/* Earlier publishes */}
                {Object.keys(revisionsChartData[0] || {})
                  .filter((k) => k !== "period" && k !== "timeLabel" && k !== "actual" && k !== "Decision forecast")
                  .map((key, idx) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={revisionColors[idx % revisionColors.length]}
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  ))}

                {/* Decision Forecast */}
                <Line
                  type="monotone"
                  dataKey="Decision forecast"
                  stroke="#06b6d4"
                  strokeWidth={3}
                  dot={false}
                />

                {/* Actual Outturn */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual outturn"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 3: 48 Settlement Periods Table */}
      {activeSubTab === "table" && (
        <div className="overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-900/60 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-slate-800 p-4">
            <div>
              <h4 className="text-sm font-bold text-white">48 settlement periods breakdown</h4>
              <p className="text-xs text-slate-400">Detailed target outturns, frozen forecasts, and signed procurement errors.</p>
            </div>
            <a
              href={api.getExportCsvUrl(selectedDate, selectedDate, cutoffTime)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-200 hover:bg-slate-700"
            >
              <Download className="h-3 w-3" />
              Download CSV
            </a>
          </div>

          <div className="max-h-[500px] overflow-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-950 text-slate-400">
                <tr className="border-b border-slate-800">
                  <th className="py-2.5 px-3">SP</th>
                  <th className="py-2.5 px-3">Target time (UTC)</th>
                  <th className="py-2.5 px-3">Actual (MW)</th>
                  <th className="py-2.5 px-3">Forecast (MW)</th>
                  <th className="py-2.5 px-3">Error (MW)</th>
                  <th className="py-2.5 px-3">Shortfall (MW)</th>
                  <th className="py-2.5 px-3">Forecast publish time</th>
                  <th className="py-2.5 px-3">Risk assessment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 text-slate-300">
                {periods.map((p) => {
                  const isShortfall = p.error !== null && p.error > 0;
                  return (
                    <tr key={p.settlementPeriod} className="hover:bg-slate-800/40">
                      <td className="py-2 px-3 font-mono font-bold text-slate-400">{p.settlementPeriod}</td>
                      <td className="py-2 px-3 font-mono">{p.startTime.substring(11, 16)}</td>
                      <td className="py-2 px-3 font-semibold text-emerald-400">
                        {p.actual !== null ? Math.round(p.actual).toLocaleString() : "—"}
                      </td>
                      <td className="py-2 px-3 font-semibold text-cyan-400">
                        {p.forecast !== null ? Math.round(p.forecast).toLocaleString() : "—"}
                      </td>
                      <td
                        className={`py-2 px-3 font-mono font-bold ${
                          isShortfall ? "text-amber-400" : "text-slate-300"
                        }`}
                      >
                        {p.error !== null ? `${p.error > 0 ? "+" : ""}${Math.round(p.error).toLocaleString()}` : "—"}
                      </td>
                      <td className="py-2 px-3 font-mono text-rose-400">
                        {p.shortfall !== null && p.shortfall > 0 ? Math.round(p.shortfall).toLocaleString() : "0"}
                      </td>
                      <td className="py-2 px-3 text-slate-400 font-mono">
                        {p.publishTime ? p.publishTime.substring(11, 16) + " UTC" : "—"}
                      </td>
                      <td className="py-2 px-3">
                        {isShortfall ? (
                          <span className="rounded bg-rose-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-rose-400 border border-rose-500/20">
                            Shortfall risk
                          </span>
                        ) : (
                          <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
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
