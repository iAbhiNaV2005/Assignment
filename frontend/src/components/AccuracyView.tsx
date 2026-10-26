import React, { useState } from "react";
import {
  BarChart as RechartsBarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import {
  Calendar,
  Clock,
  ShieldAlert,
  Sliders,
  AlertTriangle,
  Activity,
  Layers,
  Percent,
} from "lucide-react";
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
}) => {
  const [activeTab, setActiveTab] = useState<"daily" | "hourly" | "wind" | "distribution" | "horizon">("daily");

  return (
    <div className="space-y-4">
      {/* Date Range & Controls Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#22262e] bg-[#121417] p-2.5">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Range picker */}
          <div className="flex items-center gap-2 rounded border border-[#22262e] bg-[#16181d] px-2.5 py-1 text-xs text-[#f3f4f6]">
            <Calendar className="h-3.5 w-3.5 text-[#38bdf8]" />
            <span className="text-[#9ca3af]">Range:</span>
            <input
              type="date"
              min="2026-01-01"
              max={toDate}
              value={fromDate}
              onChange={(e) => e.target.value && setFromDate(e.target.value)}
              className="bg-transparent font-medium focus:outline-none"
              aria-label="Start date"
            />
            <span className="text-[#6b7280]">to</span>
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
          <div className="flex items-center gap-2 rounded border border-[#22262e] bg-[#16181d] px-2.5 py-1 text-xs">
            <Clock className="h-3.5 w-3.5 text-[#f59e0b]" />
            <label htmlFor="accuracy-cutoff" className="text-[11px] text-[#9ca3af]">
              Cutoff:
            </label>
            <input
              id="accuracy-cutoff"
              type="text"
              pattern="^([01]\d|2[0-3]):([0-5]\d)$"
              value={cutoffTime}
              onChange={(e) => setCutoffTime(e.target.value)}
              className="w-12 rounded border border-[#2a2e37] bg-[#121417] px-1 py-0.5 text-center text-xs font-bold text-[#f3f4f6] focus:border-[#38bdf8] focus:outline-none"
              aria-label="Accuracy cutoff time"
            />
            <span className="text-[11px] text-[#6b7280]">London time</span>
          </div>

          <span className="hidden text-xs text-[#6b7280] md:inline">
            Full month (January 2026)
          </span>
        </div>

        {/* Coverage pill */}
        <div className="flex items-center gap-1.5 text-xs text-[#9ca3af]">
          <span className="h-2 w-2 rounded-full bg-[#38bdf8]" />
          <span>
            Evaluated: <strong className="tabular-nums font-semibold text-[#f3f4f6]">{metrics?.evaluatedPeriods || 0}</strong> / {metrics?.totalPeriods || 0} periods (100%)
          </span>
        </div>
      </div>

      {/* 6 Peer Headline Performance KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <KPICard
          title="Mean absolute error"
          value={metrics?.mae !== null && metrics?.mae !== undefined ? Math.round(metrics.mae).toLocaleString() : null}
          unit="MW"
          subtitle="Typical miss size"
          badge={{ text: "MAE", variant: "neutral" }}
        />
        <KPICard
          title="Root mean square error"
          value={metrics?.rmse !== null && metrics?.rmse !== undefined ? Math.round(metrics.rmse).toLocaleString() : null}
          unit="MW"
          subtitle="Large miss penalty"
          badge={{ text: "RMSE", variant: "neutral" }}
        />
        <KPICard
          title="Normalized MAE"
          value={metrics?.nmae !== null && metrics?.nmae !== undefined ? `${metrics.nmae.toFixed(2)}%` : null}
          subtitle="MAE / mean actual"
          badge={{ text: "Scale-free", variant: "info" }}
          icon={<Percent className="h-3.5 w-3.5 text-[#38bdf8]" />}
        />
        <KPICard
          title="Net forecast bias"
          value={
            metrics?.bias !== null && metrics?.bias !== undefined
              ? `${metrics.bias > 0 ? "+" : ""}${Math.round(metrics.bias).toLocaleString()}`
              : null
          }
          unit="MW"
          subtitle="Over-prediction"
          badge={{ text: "Over-forecast", variant: "warning" }}
          icon={<AlertTriangle className="h-3.5 w-3.5 text-[#f59e0b]" />}
        />
        <KPICard
          title="Shortfall risk share"
          value={metrics?.shareOverPct !== null && metrics?.shareOverPct !== undefined ? `${metrics.shareOverPct.toFixed(1)}%` : null}
          subtitle="Periods over-forecast"
          badge={{ text: "Shortfall", variant: "danger" }}
          icon={<ShieldAlert className="h-3.5 w-3.5 text-[#f43f5e]" />}
        />
        <KPICard
          title="P95 peak error"
          value={metrics?.p95AbsError !== null && metrics?.p95AbsError !== undefined ? Math.round(metrics.p95AbsError).toLocaleString() : null}
          unit="MW"
          subtitle="Worst 5% tail stress"
          badge={{ text: "Tail risk", variant: "warning" }}
          icon={<Activity className="h-3.5 w-3.5 text-[#f59e0b]" />}
        />
      </div>

      {/* Recommended Thermal Procurement Buffer (Decision-Ready Risk Panel) */}
      <div className="rounded-lg border border-[#22262e] border-l-4 border-l-[#f43f5e] bg-[#121417] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1b1e24] pb-3">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="h-5 w-5 text-[#f43f5e]" />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-bold text-[#f3f4f6]">Recommended thermal procurement buffer</h3>
                <span className="rounded border border-[#581f2a] bg-[#2f1017] px-1.5 py-0.2 text-[10px] font-semibold uppercase text-[#f43f5e]">
                  Decision-ready
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-[#9ca3af]">
                Actionable extra generation buffer required to protect against unexpected wind shortfall in the day-ahead auction.
              </p>
            </div>
          </div>

          {/* Percentile Slider Control */}
          <div className="flex items-center gap-3 rounded border border-[#22262e] bg-[#16181d] px-3 py-1.5">
            <Sliders className="h-3.5 w-3.5 text-[#38bdf8]" />
            <div className="flex items-center gap-1.5">
              <label htmlFor="confidence-slider" className="text-[11px] text-[#9ca3af]">
                Target confidence:
              </label>
              <span className="tabular-nums text-xs font-bold text-[#f3f4f6]">{bufferPercentile}%</span>
            </div>
            <input
              id="confidence-slider"
              type="range"
              min="75"
              max="99"
              step="1"
              value={bufferPercentile}
              onChange={(e) => setBufferPercentile(Number(e.target.value))}
              className="h-1.5 w-24 cursor-pointer"
              aria-label="Target confidence percentile"
            />
          </div>
        </div>

        {/* Buffer Metrics Comparison */}
        <div className="mt-3.5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded border border-[#22262e] bg-[#16181d] p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-[#9ca3af]">In-sample buffer (benchmark)</span>
              <span className="rounded border border-[#2a2e37] bg-[#121417] px-1.5 py-0.2 text-[9px] uppercase text-[#6b7280]">Full window</span>
            </div>
            <div className="mt-1.5 flex items-baseline gap-1.5">
              <span className="tabular-nums text-xl font-bold text-[#f3f4f6]">
                {bufferData?.inSampleBufferMw ? Math.round(bufferData.inSampleBufferMw).toLocaleString() : "—"}
              </span>
              <span className="text-[11px] text-[#6b7280]">MW</span>
            </div>
            <p className="mt-0.5 text-[10px] text-[#6b7280]">
              {bufferPercentile}th percentile of shortfall across the chosen window.
            </p>
          </div>

          <div className="rounded border border-[#164164] bg-[#0c2438]/50 p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-[#38bdf8]">Walk-forward backtested buffer</span>
              <span className="rounded border border-[#164164] bg-[#0c2438] px-1.5 py-0.2 text-[9px] font-semibold uppercase text-[#38bdf8]">Honest ex-ante</span>
            </div>
            <div className="mt-1.5 flex items-baseline gap-1.5">
              <span className="tabular-nums text-xl font-bold text-[#38bdf8]">
                {bufferData?.backtestBufferAvgMw ? Math.round(bufferData.backtestBufferAvgMw).toLocaleString() : "—"}
              </span>
              <span className="text-[11px] text-[#6b7280]">MW avg</span>
            </div>
            <p className="mt-0.5 text-[10px] text-[#9ca3af]">
              Calibrated strictly each day using only prior days' historical errors.
            </p>
          </div>

          <div className="rounded border border-[#125338] bg-[#092a1d]/50 p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-[#10b981]">Achieved out-of-sample coverage</span>
              <span className="text-[10px] font-mono text-[#10b981]">✓</span>
            </div>
            <div className="mt-1.5 flex items-baseline gap-1.5">
              <span className="tabular-nums text-xl font-bold text-[#10b981]">
                {bufferData?.achievedCoveragePct ? `${bufferData.achievedCoveragePct}%` : "—"}
              </span>
              <span className="text-[11px] text-[#6b7280]">target: {bufferPercentile}%</span>
            </div>
            <p className="mt-0.5 text-[10px] text-[#9ca3af]">
              {bufferData?.coveredPeriods || 0} of {bufferData?.totalEvaluatedPeriods || 0} evaluated half-hours fully protected.
            </p>
          </div>
        </div>
      </div>

      {/* Analysis Views Navigation Tabs */}
      <div className="flex items-center justify-between border-b border-[#22262e] pb-1.5 pt-1">
        <div className="flex flex-wrap items-center gap-1 rounded-lg border border-[#22262e] bg-[#14161b] p-0.5">
          <button
            onClick={() => setActiveTab("daily")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "daily" ? "bg-[#22262e] text-[#f3f4f6]" : "text-[#9ca3af] hover:text-[#f3f4f6]"
            }`}
          >
            Daily error profile
          </button>
          <button
            onClick={() => setActiveTab("hourly")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "hourly" ? "bg-[#22262e] text-[#f3f4f6]" : "text-[#9ca3af] hover:text-[#f3f4f6]"
            }`}
          >
            Diurnal cycle (hours 0 to 23)
          </button>
          <button
            onClick={() => setActiveTab("wind")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "wind" ? "bg-[#22262e] text-[#f3f4f6]" : "text-[#9ca3af] hover:text-[#f3f4f6]"
            }`}
          >
            Performance by wind level
          </button>
          <button
            onClick={() => setActiveTab("distribution")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "distribution" ? "bg-[#22262e] text-[#f3f4f6]" : "text-[#9ca3af] hover:text-[#f3f4f6]"
            }`}
          >
            Signed error distribution
          </button>
          <button
            onClick={() => setActiveTab("horizon")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "horizon" ? "bg-[#22262e] text-[#f3f4f6]" : "text-[#9ca3af] hover:text-[#f3f4f6]"
            }`}
          >
            Error vs lead horizon (0 to 72h)
          </button>
        </div>
      </div>

      {/* TAB 1: Daily Breakdown Chart */}
      {activeTab === "daily" && (
        <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
          <div className="mb-3">
            <h4 className="text-xs font-bold text-[#f3f4f6]">
              Daily net bias remained positive on 27 of 31 days (+1,852 MW monthly mean)
            </h4>
            <p className="text-[11px] text-[#6b7280]">
              January 1–31, 2026 • Elexon BMRS national wind actuals vs D-1 decision forecasts • Units: MW
            </p>
          </div>
          <div className="h-[340px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={dailyBreakdown} margin={{ top: 10, right: 15, left: 5, bottom: 15 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1c1f26" />
                <XAxis dataKey="date" stroke="#6b7280" fontSize={10} tickFormatter={(d) => d.substring(5)} />
                <YAxis stroke="#6b7280" fontSize={10} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#16191f", borderColor: "#2a2e38", borderRadius: "6px", fontSize: "11px", color: "#f3f4f6" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                <Bar dataKey="mae" name="MAE (typical miss)" fill="#38bdf8" radius={[2, 2, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="bias" name="Bias (+over / -under)" fill="#f59e0b" radius={[2, 2, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="shortfallP90" name="P90 shortfall" fill="#f43f5e" radius={[2, 2, 0, 0]} isAnimationActive={false} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 2: Hourly Breakdown */}
      {activeTab === "hourly" && (
        <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
          <div className="mb-3">
            <h4 className="text-xs font-bold text-[#f3f4f6]">
              Miss rate peaks during daytime ramp hours (08:00 to 14:00 UTC)
            </h4>
            <p className="text-[11px] text-[#6b7280]">
              Hourly aggregated error across all 1,488 settlement periods in January 2026 • Hours 00:00 to 23:00 UTC
            </p>
          </div>
          <div className="h-[340px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyBreakdown} margin={{ top: 10, right: 15, left: 5, bottom: 15 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1c1f26" />
                <XAxis dataKey="hourLabel" stroke="#6b7280" fontSize={10} />
                <YAxis stroke="#6b7280" fontSize={10} domain={[0, "auto"]} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#16191f", borderColor: "#2a2e38", borderRadius: "6px", fontSize: "11px", color: "#f3f4f6" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                <Line type="monotone" dataKey="mae" name="MAE (MW)" stroke="#38bdf8" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
                <Line type="monotone" dataKey="bias" name="Bias (MW)" stroke="#f59e0b" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 3: Wind Level Breakdown */}
      {activeTab === "wind" && (
        <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
          <div className="mb-3">
            <h4 className="text-xs font-bold text-[#f3f4f6]">
              Forecast miss size increases at higher wind output regimes above 14 GW
            </h4>
            <p className="text-[11px] text-[#6b7280]">
              Comparing error metrics across Low (&lt;7 GW), Medium (7-14 GW), and High (&gt;14 GW) generation • January 2026
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {windLevelBreakdown.map((item) => (
              <div key={item.level} className="rounded border border-[#22262e] bg-[#16181d] p-3.5">
                <div className="flex items-center justify-between border-b border-[#22262e] pb-2">
                  <span className="text-xs font-bold text-[#f3f4f6]">{item.level}</span>
                  <span className="rounded border border-[#2a2e37] bg-[#121417] px-1.5 py-0.2 text-[10px] text-[#9ca3af]">
                    {item.pctOfTotal}% of periods
                  </span>
                </div>
                <div className="mt-3 space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-[#6b7280]">Periods:</span>
                    <span className="tabular-nums font-mono text-[#f3f4f6]">{item.periods}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6b7280]">Mean actual:</span>
                    <span className="tabular-nums font-mono font-medium text-[#10b981]">{Math.round(item.meanActual).toLocaleString()} MW</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6b7280]">MAE:</span>
                    <span className="tabular-nums font-mono font-medium text-[#38bdf8]">{Math.round(item.mae).toLocaleString()} MW</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6b7280]">Bias:</span>
                    <span className={`tabular-nums font-mono font-medium ${item.bias > 0 ? "text-[#f59e0b]" : "text-[#10b981]"}`}>
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
        <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h4 className="text-xs font-bold text-[#f3f4f6]">
                Signed error distribution skews positive: 84.9% of periods exhibit shortfall
              </h4>
              <p className="text-[11px] text-[#6b7280]">
                Frequency distribution of signed error (Forecast - Actual) • P10 (-544 MW), P50 (+1,703 MW), P90 (+4,275 MW)
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-[#6b7280]">P10: <strong className="tabular-nums font-mono text-[#38bdf8]">{metrics?.p10Error} MW</strong></span>
              <span className="text-[#6b7280]">Median: <strong className="tabular-nums font-mono text-[#f3f4f6]">{metrics?.p50Error} MW</strong></span>
              <span className="text-[#6b7280]">P90: <strong className="tabular-nums font-mono text-[#f43f5e]">{metrics?.p90Error} MW</strong></span>
            </div>
          </div>
          <div className="h-[340px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={histogramData} margin={{ top: 10, right: 15, left: 5, bottom: 15 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1c1f26" />
                <XAxis dataKey="binCenter" stroke="#6b7280" fontSize={10} tickFormatter={(v) => `${Math.round(v)}`} />
                <YAxis stroke="#6b7280" fontSize={10} domain={[0, "auto"]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#16191f", borderColor: "#2a2e38", borderRadius: "6px", fontSize: "11px", color: "#f3f4f6" }}
                  formatter={(val: any) => [`${val} periods`, "Count"]}
                  labelFormatter={(c) => `Error ~ ${Math.round(Number(c))} MW`}
                />
                <ReferenceLine x={0} stroke="#6b7280" strokeDasharray="3 3" label={{ value: "Zero error line", fill: "#6b7280", fontSize: 10 }} />
                <Bar dataKey="count" name="Frequency" fill="#38bdf8" radius={[2, 2, 0, 0]} isAnimationActive={false} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 5: Horizon Analysis */}
      {activeTab === "horizon" && (
        <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
          <div className="mb-3">
            <h4 className="text-xs font-bold text-[#f3f4f6]">
              Forecast error drops monotonically from 2,384 MW at 72h lead to 1,777 MW at 0–6h
            </h4>
            <p className="text-[11px] text-[#6b7280]">
              All WINDFOR runs for January 2026 targets grouped by lead time • Error reduces as delivery nears
            </p>
          </div>
          <div className="h-[340px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={horizonData} margin={{ top: 10, right: 15, left: 5, bottom: 15 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1c1f26" />
                <XAxis dataKey="bucket" stroke="#6b7280" fontSize={10} />
                <YAxis stroke="#6b7280" fontSize={10} domain={[0, "auto"]} tickFormatter={(v) => `${Math.round(v)} MW`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#16191f", borderColor: "#2a2e38", borderRadius: "6px", fontSize: "11px", color: "#f3f4f6" }}
                  formatter={(val: any, name: any) => [`${Number(val).toLocaleString()} MW`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                <Bar dataKey="mae" name="MAE (typical miss MW)" fill="#38bdf8" radius={[2, 2, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="rmse" name="RMSE (MW)" fill="#a855f7" radius={[2, 2, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="bias" name="Bias (MW)" fill="#f59e0b" radius={[2, 2, 0, 0]} isAnimationActive={false} />
              </RechartsBarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};
