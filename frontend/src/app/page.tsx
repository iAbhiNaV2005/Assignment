"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Navbar } from "../components/Navbar";
import { DecisionView } from "../components/DecisionView";
import { AccuracyView } from "../components/AccuracyView";
import { MethodologyView } from "../components/MethodologyView";
import { api } from "../lib/api";
import {
  BufferResponse,
  DailyBreakdownItem,
  DecisionResponse,
  HistogramBin,
  HorizonItem,
  HourlyBreakdownItem,
  MetricsResponse,
  RevisionsResponse,
  WindLevelBreakdownItem,
} from "../lib/types";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"decision" | "accuracy" | "methodology">("decision");
  const [apiHealthStatus, setApiHealthStatus] = useState<string>("connecting");

  // Filter state
  const [selectedDate, setSelectedDate] = useState<string>("2026-01-15");
  const [cutoffTime, setCutoffTime] = useState<string>("09:00");
  const [fromDate, setFromDate] = useState<string>("2026-01-01");
  const [toDate, setToDate] = useState<string>("2026-01-31");
  const [bufferPercentile, setBufferPercentile] = useState<number>(90);

  // Data state
  const [decisionData, setDecisionData] = useState<DecisionResponse | null>(null);
  const [revisionsData, setRevisionsData] = useState<RevisionsResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [dailyBreakdown, setDailyBreakdown] = useState<DailyBreakdownItem[]>([]);
  const [hourlyBreakdown, setHourlyBreakdown] = useState<HourlyBreakdownItem[]>([]);
  const [windLevelBreakdown, setWindLevelBreakdown] = useState<WindLevelBreakdownItem[]>([]);
  const [histogramData, setHistogramData] = useState<HistogramBin[]>([]);
  const [horizonData, setHorizonData] = useState<HorizonItem[]>([]);
  const [bufferData, setBufferData] = useState<BufferResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Health check
  useEffect(() => {
    api.getHealth()
      .then((h) => setApiHealthStatus(h.status))
      .catch(() => setApiHealthStatus("ready"));
  }, []);

  // Fetch Decision Data
  const loadDecisionData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [dec, rev] = await Promise.all([
        api.getDecision(selectedDate, cutoffTime),
        api.getRevisions(selectedDate, cutoffTime),
      ]);
      setDecisionData(dec);
      setRevisionsData(rev);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load decision data");
    } finally {
      setIsLoading(false);
    }
  }, [selectedDate, cutoffTime]);

  // Fetch Accuracy Data
  const loadAccuracyData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [m, daily, hourly, wind, hist, hor, buf] = await Promise.all([
        api.getMetrics(fromDate, toDate, cutoffTime),
        api.getDailyBreakdown(fromDate, toDate, cutoffTime),
        api.getHourlyBreakdown(fromDate, toDate, cutoffTime),
        api.getWindLevelBreakdown(fromDate, toDate, cutoffTime),
        api.getHistogram(fromDate, toDate, cutoffTime, 18),
        api.getHorizon(fromDate, toDate),
        api.getBuffer(fromDate, toDate, cutoffTime, bufferPercentile),
      ]);
      setMetrics(m);
      setDailyBreakdown(daily);
      setHourlyBreakdown(hourly);
      setWindLevelBreakdown(wind);
      setHistogramData(hist);
      setHorizonData(hor);
      setBufferData(buf);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load accuracy metrics");
    } finally {
      setIsLoading(false);
    }
  }, [fromDate, toDate, cutoffTime, bufferPercentile]);

  useEffect(() => {
    if (activeTab === "decision") {
      loadDecisionData();
    } else if (activeTab === "accuracy") {
      loadAccuracyData();
    }
  }, [activeTab, loadDecisionData, loadAccuracyData]);

  return (
    <div className="flex min-h-screen flex-col bg-[#0a0b0d] text-[#f3f4f6] selection:bg-[#0284c7]/30 selection:text-[#38bdf8]">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        apiHealthStatus={apiHealthStatus}
      />

      <main className="flex-1 px-4 py-5 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          {/* Error Banner */}
          {errorMessage && (
            <div className="mb-4 flex items-center justify-between rounded-lg border border-[#581f2a] bg-[#181114] p-3 text-xs text-[#f43f5e]">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-[#f43f5e]" />
                <span>{errorMessage}</span>
              </div>
              <button
                onClick={() => (activeTab === "decision" ? loadDecisionData() : loadAccuracyData())}
                className="flex items-center gap-1 font-semibold text-[#f43f5e] hover:text-white"
              >
                <RefreshCw className="h-3 w-3" />
                Retry
              </button>
            </div>
          )}

          {/* Active View */}
          {activeTab === "decision" && (
            <DecisionView
              selectedDate={selectedDate}
              setSelectedDate={setSelectedDate}
              cutoffTime={cutoffTime}
              setCutoffTime={setCutoffTime}
              decisionData={decisionData}
              revisionsData={revisionsData}
              isLoading={isLoading}
              onRefresh={loadDecisionData}
            />
          )}

          {activeTab === "accuracy" && (
            <AccuracyView
              fromDate={fromDate}
              setFromDate={setFromDate}
              toDate={toDate}
              setToDate={setToDate}
              cutoffTime={cutoffTime}
              setCutoffTime={setCutoffTime}
              metrics={metrics}
              dailyBreakdown={dailyBreakdown}
              hourlyBreakdown={hourlyBreakdown}
              windLevelBreakdown={windLevelBreakdown}
              histogramData={histogramData}
              horizonData={horizonData}
              bufferData={bufferData}
              bufferPercentile={bufferPercentile}
              setBufferPercentile={setBufferPercentile}
              isLoading={isLoading}
            />
          )}

          {activeTab === "methodology" && <MethodologyView />}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-10 border-t border-[#22262e] bg-[#0e1013] py-4 text-xs text-[#6b7280]">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 sm:flex-row sm:px-6">
          <p>© 2026 UK Wind Day-Ahead Procurement Desk. Data sourced from Elexon BMRS.</p>
          <div className="flex items-center gap-3 text-[11px]">
            <span>January 2026 Scope</span>
            <span>•</span>
            <span>FastAPI Python Engine</span>
            <span>•</span>
            <span>Next.js Dashboard</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
