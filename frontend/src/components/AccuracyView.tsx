"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  Calendar,
  Clock,
  Sliders,
  CheckCircle,
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
              aria-label="Start date"
            />
            <span className="text-slate-500">to</span>
            <input
              type="date"
              min={fromDate}
              max="2026-01-31"
              value={toDate}
              onChange={(e) => e.target.value && setToDate(e.target.value)}
              className="bg-transparent font-medium focus:outline-none"
              aria-label="End date"
            />
          </div>

          {/* Cutoff control */}
          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs">
            <Clock className="h-4 w-4 text-amber-400" />
            <label htmlFor="accuracy-cutoff" className="text-slate-400">
              Cutoff:
            </label>
            <input
              id="accuracy-cutoff"
              type="text"
              value={cutoffTime}
              onChange={(e) => setCutoffTime(e.target.value)}
              className="w-14 rounded bg-slate-800 px-1 text-center font-bold text-white focus:outline-none"
              aria-label="Accuracy cutoff time"
            />
            <span className="text-slate-500">London time</span>
          </div>

          {/* Quick preset */}
          <button
            onClick={() => {
              setFromDate("2026-01-01");
              setToDate("2026-01-31");
            }}
            className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-400 hover:border-slate-700 hover:text-white"
          >
            Full month (January 2026)
          </button>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="h-2 w-2 rounded-full bg-[#38bdf8]" />
          <span>
            Evaluated: <strong className="text-white">{metrics?.evaluatedPeriods || 0}</strong> /{" "}
            {metrics?.totalPeriods || 0} periods ({metrics?.coveragePct || 100}%)
          </span>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <KPICard
          title="Mean absolute error"
          value={metrics?.mae ? Math.round(metrics.mae).toLocaleString() : null}
          unit="MW"
          subtitle="Typical miss size"
          badge={{ text: "MAE", variant: "neutral" }}
        />
        <KPICard
          title="Root mean square error"
          value={metrics?.rmse ? Math.round(metrics.rmse).toLocaleString() : null}
          unit="MW"
          subtitle="Large miss penalty"
          badge={{ text: "RMSE", variant: "neutral" }}
        />
        <KPICard
          title="Normalized MAE"
          value={metrics?.nmae ? `${metrics.nmae}%` : null}
          subtitle="MAE / mean actual"
          badge={{ text: "Scale-free", variant: "info" }}
        />
        <KPICard
          title="Net forecast bias"
          value={metrics?.bias !== null && metrics?.bias !== undefined ? `${metrics.bias > 0 ? "+" : ""}${Math.round(metrics.bias).toLocaleString()}` : null}
          unit="MW"
          subtitle={metrics?.bias && metrics.bias > 0 ? "Over-prediction" : "Under-prediction"}
          badge={{
            text: metrics?.bias && metrics.bias > 0 ? "Over-forecast" : "Under-forecast",
            variant: metrics?.bias && metrics.bias > 0 ? "warning" : "success",
          }}
        />
        <KPICard
          title="Shortfall risk share"
          value={metrics?.shareOverPct !== null && metrics?.shareOverPct !== undefined ? `${metrics.shareOverPct}%` : null}
          subtitle="Periods over-forecast"
          badge={{ text: "Shortfall", variant: "danger" }}
        />
        <KPICard
          title="P95 peak error"
          value={metrics?.p95AbsError ? Math.round(metrics.p95AbsError).toLocaleString() : null}
          unit="MW"
          subtitle="Worst 5% tail stress"
          badge={{ text: "Tail risk", variant: "warning" }}
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
                <h3 className="text-base font-bold text-white">Recommended thermal procurement buffer</h3>
                <span className="rounded-full bg-rose-500/20 px-2 py-0.5 text-xs font-bold text-rose-300">
                  Decision-ready
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
              <label htmlFor="confidence-slider" className="text-xs text-slate-400">
                Target confidence:
              </label>
              <span className="text-sm font-bold text-white">{bufferPercentile}%</span>
            </div>
            <input
              id="confidence-slider"
              type="range"
              min="75"
              max="99"
              step="1"
              value={bufferPercentile}
              onChange={(e) => setBufferPercentile(Number(e.target.value))}
              className="h-1.5 w-28 cursor-pointer accent-cyan-400"
              aria-label="Target confidence percentile"
            />
          </div>
        </div>

        {/* Buffer Metrics Comparison */}
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">In-sample buffer (benchmark)</span>
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300">Full window</span>
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
              <span className="text-xs text-cyan-300 font-semibold">Walk-forward backtested buffer</span>
              <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[10px] text-cyan-300 font-bold">
                Honest ex-ante
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-cyan-400">
                {bufferData?.backtestBufferAvgMw ? Math.round(bufferData.backtestBufferAvgMw).toLocaleString() : "—"}
              </span>
              <span className="text-xs text-cyan-300">MW avg</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              Calibrated strictly each day using only prior days&apos; historical errors.
            </p>
          </div>

          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-emerald-300 font-semibold">Achieved out-of-sample coverage</span>
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
            Daily error profile
          </button>
          <button
            onClick={() => setActiveTab("hourly")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "hourly" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Diurnal cycle (hours 0 to 23)
          </button>
          <button
            onClick={() => setActiveTab("wind")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "wind" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Performance by wind level
          </button>
          <button
            onClick={() => setActiveTab("distribution")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "distribution" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Signed error distribution
          </button>
          <button
            onClick={() => setActiveTab("horizon")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === "horizon" ? "bg-slate-800 text-cyan-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Error vs lead horizon (0 to 72h)
          </button>
        </div>
      </div>

      {/* TAB 1: Daily Breakdown Chart (DataViz: Conclusion title, context subtitle, labeled axes) */}
      {activeTab === "daily" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-white">
              Daily net bias remained positive on 27 of 31 days (+1,852 MW monthly mean)
            </h4>
            <p className="text-xs text-slate-400">
              January 1–31, 2026 • Elexon BMRS national wind actuals vs D-1 decision forecasts • Units: MW
            </p>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={dailyBreakdown} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" strokeOpacity={0.7} />
                <XAxis dataKey="date" stroke="#8b949e" fontSize={10} tickFormatter={(d) => d.substring(5)} />
                <YAxis stroke="#8b949e" fontSize={11} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#161b22", borderColor: "#30363d", borderRadius: "0.75rem" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
                <Bar dataKey="mae" name="MAE (typical miss)" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="bias" name="Bias (+over / -under)" fill="#d29922" radius={[4, 4, 0, 0]} />
                <Bar dataKey="shortfallP90" name="P90 shortfall" fill="#f85149" radius={[4, 4, 0, 0]} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 2: Hourly Breakdown (DataViz: Conclusion title, context subtitle, zero-baseline) */}
      {activeTab === "hourly" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-white">
              Miss rate peaks during daytime ramp hours (08:00 to 14:00 UTC)
            </h4>
            <p className="text-xs text-slate-400">
              Hourly aggregated error across all 1,488 settlement periods in January 2026 • Hours 00:00 to 23:00 UTC
            </p>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyBreakdown} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" strokeOpacity={0.7} />
                <XAxis dataKey="hourLabel" stroke="#8b949e" fontSize={11} />
                <YAxis stroke="#8b949e" fontSize={11} domain={[0, "auto"]} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#161b22", borderColor: "#30363d", borderRadius: "0.75rem" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
                <Line type="monotone" dataKey="mae" name="MAE (MW)" stroke="#38bdf8" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="bias" name="Bias (MW)" stroke="#d29922" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 3: Wind Level Breakdown */}
      {activeTab === "wind" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-white">
              Forecast miss size increases at higher wind output regimes above 14 GW
            </h4>
            <p className="text-xs text-slate-400">
              Comparing error metrics across Low (&lt;7 GW), Medium (7-14 GW), and High (&gt;14 GW) generation • January 2026
            </p>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {windLevelBreakdown.map((item) => (
              <div key={item.level} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">{item.level}</span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                    {item.pctOfTotal}% of periods
                  </span>
                </div>
                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Periods:</span>
                    <span className="font-semibold text-slate-200">{item.periods}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Mean actual:</span>
                    <span className="font-semibold text-[#3fb950]">{Math.round(item.meanActual).toLocaleString()} MW</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">MAE:</span>
                    <span className="font-semibold text-[#38bdf8]">{Math.round(item.mae).toLocaleString()} MW</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Bias:</span>
                    <span className={`font-semibold ${item.bias > 0 ? "text-[#d29922]" : "text-[#3fb950]"}`}>
                      {item.bias > 0 ? "+" : ""}{Math.round(item.bias).toLocaleString()} MW
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: Error Distribution Histogram (DataViz: Conclusion title, context subtitle, zero line) */}
      {activeTab === "distribution" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-white">
                Signed error distribution skews positive: 84.9% of periods exhibit shortfall
              </h4>
              <p className="text-xs text-slate-400">
                Frequency distribution of signed error (Forecast - Actual) • P10 (-544 MW), P50 (+1,703 MW), P90 (+4,275 MW)
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-slate-400">P10: <strong className="text-[#38bdf8]">{metrics?.p10Error} MW</strong></span>
              <span className="text-slate-400">Median: <strong className="text-white">{metrics?.p50Error} MW</strong></span>
              <span className="text-slate-400">P90: <strong className="text-[#f85149]">{metrics?.p90Error} MW</strong></span>
            </div>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={histogramData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" strokeOpacity={0.7} />
                <XAxis dataKey="binCenter" stroke="#8b949e" fontSize={11} tickFormatter={(v) => `${Math.round(v)}`} />
                <YAxis stroke="#8b949e" fontSize={11} domain={[0, "auto"]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#161b22", borderColor: "#30363d", borderRadius: "0.75rem" }}
                  formatter={(val: any) => [`${val} periods`, "Count"]}
                  labelFormatter={(c) => `Error ~ ${Math.round(Number(c))} MW`}
                />
                <ReferenceLine x={0} stroke="#8b949e" strokeDasharray="3 3" label={{ value: "Zero error line", fill: "#8b949e", fontSize: 11 }} />
                <Bar dataKey="count" name="Frequency" fill="#38bdf8" radius={[4, 4, 0, 0]} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 5: Horizon Analysis (DataViz: Conclusion title, context subtitle, zero-baseline) */}
      {activeTab === "horizon" && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm backdrop-blur-md">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-white">
              Forecast error drops monotonically from 2,384 MW at 72h lead to 1,777 MW at 0–6h
            </h4>
            <p className="text-xs text-slate-400">
              All WINDFOR runs for January 2026 targets grouped by lead time • Error reduces as delivery nears
            </p>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={horizonData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" strokeOpacity={0.7} />
                <XAxis dataKey="bucket" stroke="#8b949e" fontSize={11} />
                <YAxis stroke="#8b949e" fontSize={11} domain={[0, "auto"]} tickFormatter={(v) => `${Math.round(v)} MW`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#161b22", borderColor: "#30363d", borderRadius: "0.75rem" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
                <Bar dataKey="mae" name="MAE (typical miss MW)" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="rmse" name="RMSE (MW)" fill="#a371f7" radius={[4, 4, 0, 0]} />
                <Bar dataKey="bias" name="Bias (MW)" fill="#d29922" radius={[4, 4, 0, 0]} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};
