import React from "react";
import { ShieldCheck, Calendar, Clock, Database, TrendingUp, AlertCircle, FileText, CheckCircle2 } from "lucide-react";

export const MethodologyView: React.FC = () => {
  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-cyan-500/10 p-2 text-cyan-400">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Methodology & Operational Specifications</h2>
            <p className="text-xs text-slate-400">
              Clear principles, mathematical formulations, and domain rules powering the UK Day-Ahead Procurement Desk.
            </p>
          </div>
        </div>
      </div>

      {/* 1. Decision Timeline & The Anti-Leakage Selection Rule */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <ShieldCheck className="h-5 w-5 text-cyan-400" />
          <h3>1. Decision Timeline & Strict Selection Rule</h3>
        </div>
        <p className="mt-2 text-xs text-slate-300 leading-relaxed">
          In the UK wholesale power market, power-buying desks must submit binding purchase bids for electricity delivery day <strong className="text-white">D</strong> on day-ahead auctions executed on day <strong className="text-white">D-1</strong> before auction gate closure. At the moment of trade execution, buyers only possess forecasts published <strong className="text-cyan-300">at or before the decision cutoff</strong>.
        </p>

        {/* ASCII / Graphical Timeline Diagram */}
        <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs">
          <div className="text-slate-400">Decision & Delivery Timeline:</div>
          <div className="mt-3 space-y-2 text-slate-300">
            <div>
              <span className="text-amber-400 font-bold">Decision Day (D-1):</span> ──[ 00:00 ]─────────[ <span className="text-cyan-400 font-bold">CUTOFF TIME (e.g. 09:00 UK)</span> ]─────────[ 24:00 ]
            </div>
            <div className="pl-36 text-slate-500">
              │
            </div>
            <div className="pl-28">
              <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-emerald-400 font-sans text-[11px] font-semibold">
                ✓ Allowed: Latest publishTime ≤ Cutoff
              </span>
              <span className="ml-3 rounded bg-rose-500/20 px-2 py-0.5 text-rose-400 font-sans text-[11px] font-semibold">
                ✗ FORBIDDEN: Any publishTime &gt; Cutoff
              </span>
            </div>
            <div className="pl-36 text-slate-500">
              ▼
            </div>
            <div>
              <span className="text-emerald-400 font-bold">Delivery Day (D):</span>   ──[ SP1 (00:00) ]───────────────────────────────[ SP48 (23:30) ]
            </div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 text-xs text-slate-300">
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
            <h4 className="font-semibold text-white">Mathematical Selection Rule</h4>
            <p className="mt-1 font-mono text-cyan-400">
              Cutoff(D) = (D - 1 day) at CUTOFF_LOCAL (Europe/London)
            </p>
            <p className="mt-1 font-mono text-cyan-400">
              forecast(T) = argmax_{`{publishTime ≤ Cutoff(D)}`} WINDFOR(T)
            </p>
            <p className="mt-2 text-slate-400">
              For any target period T on day D, the algorithm selects the most recent forecast published at or before Cutoff(D).
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
            <h4 className="font-semibold text-white">Temporal Resolution Alignment</h4>
            <p className="mt-1 text-slate-300">
              • <strong className="text-emerald-400">FUELHH Actuals:</strong> 30-minute settlement periods (48 periods per day).
            </p>
            <p className="mt-1 text-slate-300">
              • <strong className="text-cyan-400">WINDFOR Forecasts:</strong> 60-minute resolution (hourly average MW).
            </p>
            <p className="mt-2 text-slate-400">
              To match UK settlement mechanics, the hourly forecast MW rate for hour H is assigned to both 30-minute periods in that hour (e.g. 01:00 forecast applies to 01:00-01:30 and 01:30-02:00) without artificial polynomial interpolation.
            </p>
          </div>
        </div>
      </div>

      {/* 2. Error Sign Convention & Commercial Risk */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <AlertCircle className="h-5 w-5 text-amber-400" />
          <h3>2. Error Sign Convention & Trading Impact</h3>
        </div>

        <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-center text-sm font-bold text-cyan-300">
          Error(T) = Forecast(T) - Actual(T)   (MW)
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 text-xs">
          <div className="rounded-xl border border-rose-500/20 bg-rose-950/10 p-4">
            <span className="font-bold text-rose-400">Positive Error (Error &gt; 0) = OVER-FORECAST</span>
            <p className="mt-1.5 text-slate-300">
              The buyer expected more wind than was generated.
            </p>
            <p className="mt-2 text-slate-400">
              <strong className="text-rose-300">Commercial Risk: Shortfall Risk.</strong> The trader under-procures thermal/conventional power in the day-ahead auction. During real-time delivery, the utility is &ldquo;short&rdquo; and must purchase balancing power at cashout (System Buy Price), exposing them to high imbalance penalties.
            </p>
          </div>

          <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/10 p-4">
            <span className="font-bold text-emerald-400">Negative Error (Error &lt; 0) = UNDER-FORECAST</span>
            <p className="mt-1.5 text-slate-300">
              The buyer expected less wind than was generated.
            </p>
            <p className="mt-2 text-slate-400">
              <strong className="text-emerald-300">Commercial Risk: Surplus / Curtailment.</strong> The trader over-bought conventional generation or faces spill/curtailment, selling surplus power into the balancing mechanism at discounted prices.
            </p>
          </div>
        </div>
      </div>

      {/* 3. Mathematical Metric Definitions */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <TrendingUp className="h-5 w-5 text-cyan-400" />
          <h3>3. Accuracy Metrics Formulations</h3>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3.5">
            <span className="font-bold text-white">MAE</span>
            <p className="mt-1 font-mono text-[11px] text-cyan-300">(1/N) ∑ |error|</p>
            <p className="mt-1 text-slate-400">Typical magnitude of forecast miss in Megawatts.</p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3.5">
            <span className="font-bold text-white">RMSE</span>
            <p className="mt-1 font-mono text-[11px] text-cyan-300">√ [ (1/N) ∑ error² ]</p>
            <p className="mt-1 text-slate-400">Penalizes large outlier misses heavily.</p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3.5">
            <span className="font-bold text-white">Net Bias</span>
            <p className="mt-1 font-mono text-[11px] text-cyan-300">(1/N) ∑ error</p>
            <p className="mt-1 text-slate-400">Reveals systematic over- or under-forecasting bias.</p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3.5">
            <span className="font-bold text-white">nMAE (%)</span>
            <p className="mt-1 font-mono text-[11px] text-cyan-300">MAE / Mean(Actual)</p>
            <p className="mt-1 text-slate-400">Normalized percentage safe from near-zero divisor explosion.</p>
          </div>
        </div>
      </div>

      {/* 4. Safety Buffer & Honest Walk-Forward Backtesting */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          <h3>4. Safety Buffer & Rolling Walk-Forward Backtest</h3>
        </div>

        <p className="mt-2 text-xs text-slate-300 leading-relaxed">
          To provide a decision-ready procurement recommendation, the portal computes the required extra thermal capacity buffer (in MW) to absorb wind shortfalls with high statistical confidence (e.g. 90%).
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 text-xs">
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
            <span className="font-bold text-slate-200">In-Sample Buffer (Benchmark)</span>
            <p className="mt-1.5 text-slate-400">
              The {`P90`} percentile of shortfall {`max(0, forecast - actual)`} computed retrospectively across all January periods.
            </p>
          </div>

          <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/10 p-4">
            <span className="font-bold text-cyan-300">Honest Walk-Forward Backtest (Ex-Ante)</span>
            <p className="mt-1.5 text-slate-300">
              For each delivery day D, the recommended buffer is strictly calibrated on historical shortfalls from days {`1 to D-1`}. Day D is then evaluated out-of-sample to verify whether the buffer prevented an uncontracted shortfall.
            </p>
          </div>
        </div>
      </div>

      {/* 5. Data Sources & Limitations */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <Database className="h-5 w-5 text-cyan-400" />
          <h3>5. Data Provenance & Scope Limits</h3>
        </div>

        <div className="mt-3 space-y-2 text-xs text-slate-300">
          <p>
            • <strong className="text-white">Authoritative Source:</strong> Elexon BMRS API (<code className="text-cyan-300">data.elexon.co.uk/bmrs/api/v1</code>).
          </p>
          <p>
            • <strong className="text-white">Datasets:</strong> FUELHH stream (fuelType = WIND) for national actuals; WINDFOR stream for national forecasts.
          </p>
          <p>
            • <strong className="text-white">Scope:</strong> January 2026 delivery decisions (1,488 actual half-hours, 100% data coverage, 0 nulls). Ingest pipeline incorporates publish times from December 25, 2025 to cover early January gate closures.
          </p>
          <p>
            • <strong className="text-white">Strict Compliance:</strong> No external capacity or private utility data used; pure national data as mandated by the assignment specification.
          </p>
        </div>
      </div>
    </div>
  );
};
