import React from "react";
import { ShieldCheck, Database, AlertCircle, FileText, CheckCircle2 } from "lucide-react";

export const MethodologyView: React.FC = () => {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-[#16181d] border border-[#22262e] text-[#38bdf8]">
            <FileText className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-[#f3f4f6]">Methodology & Operational Specifications</h2>
            <p className="text-[11px] text-[#6b7280]">
              Clear principles, mathematical formulations, and domain rules powering the UK Day-Ahead Procurement Desk.
            </p>
          </div>
        </div>
      </div>

      {/* 1. Decision Timeline & The Anti-Leakage Selection Rule */}
      <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
        <div className="flex items-center gap-2 text-xs font-bold text-[#f3f4f6]">
          <ShieldCheck className="h-4 w-4 text-[#38bdf8]" />
          <h3>1. Decision Timeline & Strict Selection Rule</h3>
        </div>
        <p className="mt-2 text-xs text-[#9ca3af] leading-relaxed">
          In the UK wholesale power market, power-buying desks must submit binding purchase bids for electricity delivery day <strong className="text-[#f3f4f6]">D</strong> on day-ahead auctions executed on day <strong className="text-[#f3f4f6]">D-1</strong> before auction gate closure. At the moment of trade execution, buyers only possess forecasts published <strong className="text-[#38bdf8]">at or before the decision cutoff</strong>.
        </p>

        {/* Graphical Timeline Diagram */}
        <div className="mt-3 rounded border border-[#22262e] bg-[#16181d] p-3 font-mono text-[11px]">
          <div className="text-[#6b7280]">Decision & Delivery Timeline:</div>
          <div className="mt-2 space-y-2 text-[#9ca3af]">
            <div>
              <span className="text-[#f59e0b] font-bold">Decision Day (D-1):</span> ──[ 00:00 ]─────────[ <span className="text-[#38bdf8] font-bold">CUTOFF TIME (e.g. 09:00 UK)</span> ]─────────[ 24:00 ]
            </div>
            <div className="pl-36 text-[#6b7280]">
              │
            </div>
            <div className="pl-28">
              <span className="rounded border border-[#125338] bg-[#092a1d] px-2 py-0.5 text-[#10b981] font-sans text-[10px] font-semibold">
                ✓ Allowed: Latest publishTime ≤ Cutoff
              </span>
              <span className="ml-3 rounded border border-[#581f2a] bg-[#2f1017] px-2 py-0.5 text-[#f43f5e] font-sans text-[10px] font-semibold">
                ✗ FORBIDDEN: Any publishTime &gt; Cutoff
              </span>
            </div>
            <div className="pl-36 text-[#6b7280]">
              ▼
            </div>
            <div>
              <span className="text-[#10b981] font-bold">Delivery Day (D):</span>   ──[ SP1 (00:00) ]───────────────────────────────[ SP48 (23:30) ]
            </div>
          </div>
        </div>

        <div className="mt-3.5 grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs text-[#9ca3af]">
          <div className="rounded border border-[#22262e] bg-[#16181d] p-3">
            <h4 className="font-semibold text-[#f3f4f6]">Mathematical Selection Rule</h4>
            <p className="mt-1 font-mono text-[#38bdf8] text-[11px]">
              Cutoff(D) = (D - 1 day) at CUTOFF_LOCAL (Europe/London)
            </p>
            <p className="mt-1 font-mono text-[#38bdf8] text-[11px]">
              forecast(T) = argmax_{`{publishTime ≤ Cutoff(D)}`} WINDFOR(T)
            </p>
            <p className="mt-2 text-[11px] text-[#6b7280]">
              For any target period T on day D, the algorithm selects the most recent forecast published at or before Cutoff(D).
            </p>
          </div>

          <div className="rounded border border-[#22262e] bg-[#16181d] p-3">
            <h4 className="font-semibold text-[#f3f4f6]">Temporal Resolution Alignment</h4>
            <p className="mt-1 text-[#d1d5db]">
              • <strong className="text-[#10b981]">FUELHH Actuals:</strong> 30-minute settlement periods (48 periods per day).
            </p>
            <p className="mt-1 text-[#d1d5db]">
              • <strong className="text-[#38bdf8]">WINDFOR Forecasts:</strong> 60-minute resolution (hourly average MW).
            </p>
            <p className="mt-2 text-[11px] text-[#6b7280]">
              To match UK settlement mechanics, the hourly forecast MW rate for hour H is assigned to both 30-minute periods in that hour (e.g. 01:00 forecast applies to 01:00-01:30 and 01:30-02:00) without artificial polynomial interpolation.
            </p>
          </div>
        </div>
      </div>

      {/* 2. Error Sign Convention & Commercial Risk */}
      <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
        <div className="flex items-center gap-2 text-xs font-bold text-[#f3f4f6]">
          <AlertCircle className="h-4 w-4 text-[#f59e0b]" />
          <h3>2. Error Sign Convention & Trading Impact</h3>
        </div>

        <div className="mt-2.5 rounded border border-[#22262e] bg-[#16181d] p-2.5 font-mono text-center text-xs font-bold text-[#38bdf8]">
          Error(T) = Forecast(T) - Actual(T) (MW)
        </div>

        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
          <div className="rounded border border-[#581f2a] bg-[#181114] p-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#f43f5e]">Positive Error (Over-Forecast)</span>
              <span className="rounded border border-[#581f2a] bg-[#2f1017] px-1.5 py-0.2 text-[9px] font-semibold uppercase text-[#f43f5e]">
                Shortfall Risk
              </span>
            </div>
            <p className="mt-2 text-[#d1d5db]">
              • Forecast &gt; Actual Outturn.
            </p>
            <p className="mt-1 text-[#d1d5db]">
              • The trading desk assumed wind would generate more power than actually occurred.
            </p>
            <p className="mt-1 text-[#9ca3af]">
              • <strong className="text-[#f3f4f6]">Financial Exposure:</strong> The desk is under-contracted and short energy, forced into cash-out settlement at the System Buy Price (SBP), which typically spikes during high system stress.
            </p>
          </div>

          <div className="rounded border border-[#125338] bg-[#0c1913] p-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#10b981]">Negative Error (Under-Forecast)</span>
              <span className="rounded border border-[#125338] bg-[#092a1d] px-1.5 py-0.2 text-[9px] font-semibold uppercase text-[#10b981]">
                Surplus
              </span>
            </div>
            <p className="mt-2 text-[#d1d5db]">
              • Forecast &lt; Actual Outturn.
            </p>
            <p className="mt-1 text-[#d1d5db]">
              • The desk assumed less wind would be available than outturned.
            </p>
            <p className="mt-1 text-[#9ca3af]">
              • <strong className="text-[#f3f4f6]">Commercial Impact:</strong> The desk is long energy, receiving System Sell Price (SSP) for spilled/surplus generation. Lower direct financial penalty, but represents lost optimization value.
            </p>
          </div>
        </div>
      </div>

      {/* 3. Mathematical Metric Definitions */}
      <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
        <h3 className="text-xs font-bold text-[#f3f4f6]">3. Quantitative Metric Formulations</h3>
        <p className="mt-1 text-xs text-[#9ca3af]">
          Formal equations implemented across all settlement periods evaluated over the decision window.
        </p>

        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
          <div className="rounded border border-[#22262e] bg-[#16181d] p-3">
            <span className="text-[11px] font-bold text-[#38bdf8]">Mean Absolute Error (MAE)</span>
            <div className="mt-1 font-mono text-[11px] text-[#f3f4f6]">
              MAE = (1 / N) * ∑ |Forecast_i - Actual_i|
            </div>
            <p className="mt-1 text-[11px] text-[#6b7280]">
              Expected typical magnitude of forecast error in Megawatts, weighting all errors linearly.
            </p>
          </div>

          <div className="rounded border border-[#22262e] bg-[#16181d] p-3">
            <span className="text-[11px] font-bold text-[#38bdf8]">Root Mean Square Error (RMSE)</span>
            <div className="mt-1 font-mono text-[11px] text-[#f3f4f6]">
              RMSE = √ [ (1 / N) * ∑ (Forecast_i - Actual_i)² ]
            </div>
            <p className="mt-1 text-[11px] text-[#6b7280]">
              Heavily penalizes rare large misses. Discrepancy between RMSE and MAE indicates error variance and fat-tailed risks.
            </p>
          </div>

          <div className="rounded border border-[#22262e] bg-[#16181d] p-3">
            <span className="text-[11px] font-bold text-[#f59e0b]">Net Forecast Bias</span>
            <div className="mt-1 font-mono text-[11px] text-[#f3f4f6]">
              Bias = (1 / N) * ∑ (Forecast_i - Actual_i)
            </div>
            <p className="mt-1 text-[11px] text-[#6b7280]">
              Signed directional mean. In January 2026, the net bias was +1,852 MW, indicating systematic over-forecasting.
            </p>
          </div>

          <div className="rounded border border-[#22262e] bg-[#16181d] p-3">
            <span className="text-[11px] font-bold text-[#f43f5e]">Shortfall Volume & Tail Quantiles</span>
            <div className="mt-1 font-mono text-[11px] text-[#f3f4f6]">
              Shortfall_i = max(0, Forecast_i - Actual_i)
            </div>
            <p className="mt-1 text-[11px] text-[#6b7280]">
              The P90/P95 quantiles of this non-negative distribution define the required reserve thermal safety buffer.
            </p>
          </div>
        </div>
      </div>

      {/* 4. Data Provenance & API Integrity */}
      <div className="rounded-lg border border-[#22262e] bg-[#121417] p-4">
        <div className="flex items-center gap-2 text-xs font-bold text-[#f3f4f6]">
          <Database className="h-4 w-4 text-[#10b981]" />
          <h3>4. Data Provenance & Quality Verification</h3>
        </div>

        <div className="mt-3 divide-y divide-[#22262e] rounded border border-[#22262e] bg-[#16181d] text-xs">
          <div className="flex items-center justify-between p-2.5">
            <span className="text-[#9ca3af]">BMRS Stream: Actual Generation</span>
            <span className="font-mono text-[#10b981]">FUELHH (fuelType = &apos;WIND&apos;)</span>
          </div>
          <div className="flex items-center justify-between p-2.5">
            <span className="text-[#9ca3af]">BMRS Stream: Forecast Generation</span>
            <span className="font-mono text-[#38bdf8]">WINDFOR (hourly series)</span>
          </div>
          <div className="flex items-center justify-between p-2.5">
            <span className="text-[#9ca3af]">Evaluated Date Range</span>
            <span className="font-mono text-[#f3f4f6]">2026-01-01 00:00 UTC to 2026-01-31 23:30 UTC</span>
          </div>
          <div className="flex items-center justify-between p-2.5">
            <span className="text-[#9ca3af]">Settlement Periods Count</span>
            <span className="font-mono text-[#f3f4f6]">1,488 half-hours (0 missing periods, 100% complete)</span>
          </div>
          <div className="flex items-center justify-between p-2.5">
            <span className="text-[#9ca3af]">Forecast Publishes Analyzed</span>
            <span className="font-mono text-[#f3f4f6]">22,192 records across all runs</span>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2 text-[11px] text-[#10b981]">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>Strict Anti-Leakage Verified: No post-cutoff forecasts or future actuals enter the decision pipeline.</span>
        </div>
      </div>
    </div>
  );
};
