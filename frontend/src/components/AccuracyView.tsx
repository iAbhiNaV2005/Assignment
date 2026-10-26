"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  Calendar,
  Clock,
  TrendingDown,
  BarChart,
  Layers,
  Sparkles,
  Sliders,
  CheckCircle,
  HelpCircle,
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  BufferResponse,
  DailyBreakdownItem,
  HistogramBin,
  HorizonItem,
  HourlyBreakdownItem,
  MetricsResponse,
  WindLevelBreakdownItem,
} from "../lib/types";
import { KPICard } from "./KPICard";

interface AccuracyViewProps {
  fromDate: string;
  setFromDate: (d: string) => void;
  toDate: string;
  setToDate: (d: string) => void;
  cutoffTime: string;
  setCutoffTime: (c: string) => void;
  metrics: MetricsResponse | null;
  dailyBreakdown: DailyBreakdownItem[];
  hourlyBreakdown: HourlyBreakdownItem[];
  windLevelBreakdown: WindLevelBreakdownItem[];
  histogramData: HistogramBin[];
  horizonData: HorizonItem[];
  bufferData: BufferResponse | null;
  bufferPercentile: number;
  setBufferPercentile: (p: number) => void;
  isLoading: boolean;
}

export const AccuracyView: React.FC<AccuracyViewProps> = ({
  fromDate,
  setFromDate,
  toDate,
  setToDate,
  cutoffTime,
  setCutoffTime,
  metrics,
  dailyBreakdown,
  hourlyBreakdown,
  windLevelBreakdown,
  histogramData,
  horizonData,
  bufferData,
  bufferPercentile,
  setBufferPercentile,
  isLoading,
}) => {
  const [activeTab, setActiveTab] = useState<"daily" | "hourly" | "wind" | "distribution" | "horizon">("daily");

  return (
    <div className="space-y-6">
      {/* Date Range & Controls Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4 shadow-sm backdrop-blur-md">
        <div className="flex flex-wrap items-center gap-3">
          {/* Range picker */}
          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white">
            <Calendar className="h-4 w-4 text-cyan-400" />
            <span className="text-slate-400">Range:</span>
            <input
              type="date"
              min="2026-01-01"
              max={toDate}
              value={fromDate}
              onChange={(e) => e.target.value && setFromDate(e.target.value)}
              className="bg-transparent font-medium focus:outline-none"
            />
            <span className="text-slate-500">to</span>
            <input
              type="date"
              min={fromDate}
              max="2026-01-31"
              value={toDate}
              onChange={(e) => e.target.value && setToDate(e.target.value)}
              className="bg-transparent font-medium focus:outline-none"
            />
          </div>

          {/* Cutoff control */}
          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs">
            <Clock className="h-4 w-4 text-amber-400" />
            <span className="text-slate-400">Cutoff:</span>
            <input
              type="text"
              value={cutoffTime}
              onChange={(e) => setCutoffTime(e.target.value)}
              className="w-14 rounded bg-slate-800 px-1 text-center font-bold text-white focus:outline-none"
            />
            <span className="text-slate-500">London</span>
          </div>

          {/* Quick preset */}
          <button
            onClick={() => {
              setFromDate("2026-01-01");
              setToDate("2026-01-31");
            }}
            className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-400 hover:border-slate-700 hover:text-white"
          >
            Full Month (Jan 2026)
          </button>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="h-2 w-2 rounded-full bg-cyan-400" />
          <span>
            Evaluated: <strong className="text-white">{metrics?.evaluatedPeriods || 0}</strong> /{" "}
            {metrics?.totalPeriods || 0} periods ({metrics?.coveragePct || 100}%)
          </span>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <KPICard
          title="Mean Absolute Error"
          value={metrics?.mae ? Math.round(metrics.mae).toLocaleString() : null}
          unit="MW"
          subtitle="Typical Miss"
          badge={{ text: "MAE", variant: "neutral" }}
        />
        <KPICard
          title="Root Mean Sq Error"
          value={metrics?.rmse ? Math.round(metrics.rmse).toLocaleString() : null}
          unit="MW"
          subtitle="Large Miss Penalty"
          badge={{ text: "RMSE", variant: "neutral" }}
        />
        <KPICard
          title="Normalized MAE"
          value={metrics?.nmae ? `${metrics.nmae}%` : null}
          subtitle="Safe Relative Scale"
          badge={{ text: "Scale-free", variant: "info" }}
        />
        <KPICard
          title="Overall Bias"
          value={metrics?.bias !== null && metrics?.bias !== undefined ? `${metrics.bias > 0 ? "+" : ""}${Math.round(metrics.bias).toLocaleString()}` : null}
          unit="MW"
          subtitle={metrics?.bias && metrics.bias > 0 ? "Over-prediction" : "Under-prediction"}
          badge={{
            text: metrics?.bias && metrics.bias > 0 ? "Over-forecast" : "Under-forecast",
            variant: metrics?.bias && metrics.bias > 0 ? "warning" : "success",
          }}
        />
        <KPICard
          title="Shortfall Risk Share"
          value={metrics?.shareOverPct !== null && metrics?.shareOverPct !== undefined ? `${metrics.shareOverPct}%` : null}
          subtitle="Periods Over-forecast"
          badge={{ text: "Shortfall", variant: "danger" }}
        />
        <KPICard
          title="P95 Peak Abs Error"
          value={metrics?.p95AbsError ? Math.round(metrics.p95AbsError).toLocaleString() : null}
          unit="MW"
          subtitle="Worst 5% Stress"
          badge={{ text: "Tail Risk", variant: "warning" }}
        />
      </div>

      {/* SAFETY BUFFER PANEL (The Product Pitch Feature) */}
      <div className="relative overflow-hidden rounded-2xl border border-rose-500/30 bg-gradient-to-br from-rose-950/20 via-slate-900/60 to-slate-950/80 p-6 shadow-lg backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-rose-500/10 p-2.5 text-rose-400 border border-rose-500/20 shadow-inner">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Recommended Thermal Procurement Buffer</h3>
                <span className="rounded-full bg-rose-500/20 px-2 py-0.5 text-xs font-bold text-rose-300">
                  Trader Decision Tool
                </span>
              </div>
              <p className="mt-0.5 text-xs text-slate-300">
                Actionable extra generation buffer required to protect against unexpected wind shortfall in the day-ahead auction.
              </p>
            </div>
          </div>

          {/* Percentile Slider Control */}
          <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2">
            <Sliders className="h-4 w-4 text-cyan-400" />
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Target Confidence:</span>
              <span className="text-sm font-bold text-white">{bufferPercentile}%</span>
            </div>
            <input
              type="range"
              min="75"
              max="99"
              step="1"
              value={bufferPercentile}
              onChange={(e) => setBufferPercentile(Number(e.target.value))}
              className="h-1.5 w-28 cursor-pointer accent-cyan-400"
            />
          </div>
        </div>

        {/* Buffer Metrics Comparison */}
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">In-Sample Buffer (Full Month)</span>
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300">Benchmark</span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-white">
                {bufferData?.inSampleBufferMw ? Math.round(bufferData.inSampleBufferMw).toLocaleString() : "—"}
              </span>
              <span className="text-xs text-slate-400">MW</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              {bufferPercentile}th percentile of shortfall across the chosen window.
            </p>
          </div>

          <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-4 shadow-sm shadow-cyan-500/10">
            <div className="flex items-center justify-between">
              <span className="text-xs text-cyan-300 font-semibold">Walk-Forward Backtested Buffer</span>
              <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[10px] text-cyan-300 font-bold">
                Honest Ex-Ante
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-cyan-400">
                {bufferData?.backtestBufferAvgMw ? Math.round(bufferData.backtestBufferAvgMw).toLocaleString() : "—"}
              </span>
              <span className="text-xs text-cyan-300">MW avg</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              Strictly calibrated each day using only prior days&apos; historical errors.
            </p>
          </div>

          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-emerald-300 font-semibold">Achieved Out-of-Sample Coverage</span>
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-emerald-400">
                {bufferData?.achievedCoveragePct ? `${bufferData.achievedCoveragePct}%` : "—"}
              </span>
              <span className="text-xs text-slate-400">target: {bufferPercentile}%</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              {bufferData?.coveredPeriods || 0} of {bufferData?.totalEvaluatedPeriods || 0} evaluated half-hours fully protected.
            </p>
          </div>
        </div>
      </div>

      {/* Analysis Views Navigation Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setActiveTab("daily")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "daily" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Daily Error Profile
          </button>
          <button
            onClick={() => setActiveTab("hourly")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "hourly" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Diurnal Profile (Hour 0-23)
          </button>
          <button
            onClick={() => setActiveTab("wind")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "wind" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Error by Wind Generation Level
          </button>
          <button
            onClick={() => setActiveTab("distribution")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "distribution" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Error Histogram Distribution
          </button>
          <button
            onClick={() => setActiveTab("horizon")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "horizon" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Error vs. Lead Horizon (0-72h)
          </button>
        </div>
      </div>

      {/* TAB 1: Daily Breakdown Chart */}
      {activeTab === "daily" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-white">Daily Mean Absolute Error & Net Bias (MW)</h4>
            <p className="text-xs text-slate-400">Day-by-day evolution of forecast error throughout the period.</p>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={dailyBreakdown} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={10} tickFormatter={(d) => d.substring(5)} />
                <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.75rem" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
                <Bar dataKey="mae" name="MAE (Typical Miss)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                <Bar dataKey="bias" name="Bias (+Over / -Under)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="shortfallP90" name="P90 Shortfall" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 2: Hourly Breakdown */}
      {activeTab === "hourly" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-white">Intraday Diurnal Error Cycle (Hours 0 to 23)</h4>
            <p className="text-xs text-slate-400">Analysis of whether forecasts systematically degrade during specific hours of the day.</p>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyBreakdown} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="hourLabel" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.75rem" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
                <Line type="monotone" dataKey="mae" name="MAE (MW)" stroke="#06b6d4" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="bias" name="Bias (MW)" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 3: Wind Level Breakdown */}
      {activeTab === "wind" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-white">Forecast Performance by Actual Wind Generation Level</h4>
            <p className="text-xs text-slate-400">Comparing error metrics across Low (&lt;7 GW), Medium (7-14 GW), and High (&gt;14 GW) output.</p>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {windLevelBreakdown.map((item) => (
              <div key={item.level} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">{item.level}</span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                    {item.pctOfTotal}% of time
                  </span>
                </div>
                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Periods:</span>
                    <span className="font-semibold text-slate-200">{item.periods}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Mean Actual:</span>
                    <span className="font-semibold text-emerald-400">{Math.round(item.meanActual).toLocaleString()} MW</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">MAE:</span>
                    <span className="font-semibold text-cyan-400">{Math.round(item.mae).toLocaleString()} MW</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Bias:</span>
                    <span className={`font-semibold ${item.bias > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                      {item.bias > 0 ? "+" : ""}{Math.round(item.bias).toLocaleString()} MW
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: Error Distribution Histogram */}
      {activeTab === "distribution" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-white">Signed Forecast Error Distribution (MW)</h4>
              <p className="text-xs text-slate-400">Positive error = Over-prediction (Shortfall). Marked with P10, P50, and P90 percentiles.</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-slate-400">P10: <strong className="text-cyan-400">{metrics?.p10Error} MW</strong></span>
              <span className="text-slate-400">Median: <strong className="text-white">{metrics?.p50Error} MW</strong></span>
              <span className="text-slate-400">P90: <strong className="text-rose-400">{metrics?.p90Error} MW</strong></span>
            </div>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={histogramData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="binCenter" stroke="#64748b" fontSize={11} tickFormatter={(v) => `${Math.round(v)}`} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.75rem" }}
                  formatter={(val: any) => [`${val} periods`, "Count"]}
                  labelFormatter={(c) => `Error ~ ${Math.round(Number(c))} MW`}
                />
                <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="2 2" label="Zero Error" />
                <Bar dataKey="count" name="Frequency" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 5: Horizon Analysis */}
      {activeTab === "horizon" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-white">Error vs. Forecast Horizon (Lead Time Ahead of Delivery)</h4>
            <p className="text-xs text-slate-400">
              Evaluates all forecast publishes to demonstrate how forecast accuracy improves as gate closure and delivery approach.
            </p>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={horizonData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="bucket" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => `${Math.round(v)} MW`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.75rem" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
                <Bar dataKey="mae" name="MAE (Typical Miss MW)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                <Bar dataKey="rmse" name="RMSE (MW)" fill="#818cf8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="bias" name="Bias (MW)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};
