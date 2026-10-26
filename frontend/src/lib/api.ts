import {
  BufferResponse,
  ConfigResponse,
  DailyBreakdownItem,
  DecisionResponse,
  HealthResponse,
  HistogramBin,
  HorizonItem,
  HourlyBreakdownItem,
  MetricsResponse,
  RevisionsResponse,
  WindLevelBreakdownItem,
} from "./types";

const rawBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").trim();
const API_BASE_URL = rawBase.replace(/\/+$/, "");

async function apiFetch<T>(endpoint: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = new URL(`${API_BASE_URL}${cleanEndpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  const response = await fetch(url.toString(), {
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let errorDetail = `API request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  getHealth: () => apiFetch<HealthResponse>("/api/health"),
  getConfig: () => apiFetch<ConfigResponse>("/api/config"),
  getDecision: (date: string, cutoff: string) =>
    apiFetch<DecisionResponse>("/api/decision", { date, cutoff }),
  getRevisions: (date: string, cutoff: string) =>
    apiFetch<RevisionsResponse>("/api/revisions", { date, cutoff }),
  getMetrics: (fromDate: string, toDate: string, cutoff: string) =>
    apiFetch<MetricsResponse>("/api/metrics", { from: fromDate, to: toDate, cutoff }),
  getDailyBreakdown: (fromDate: string, toDate: string, cutoff: string) =>
    apiFetch<DailyBreakdownItem[]>("/api/metrics/breakdown", { by: "day", from: fromDate, to: toDate, cutoff }),
  getHourlyBreakdown: (fromDate: string, toDate: string, cutoff: string) =>
    apiFetch<HourlyBreakdownItem[]>("/api/metrics/breakdown", { by: "hour", from: fromDate, to: toDate, cutoff }),
  getWindLevelBreakdown: (fromDate: string, toDate: string, cutoff: string) =>
    apiFetch<WindLevelBreakdownItem[]>("/api/metrics/breakdown", { by: "wind_level", from: fromDate, to: toDate, cutoff }),
  getHistogram: (fromDate: string, toDate: string, cutoff: string, bins: number = 18) =>
    apiFetch<HistogramBin[]>("/api/metrics/histogram", { from: fromDate, to: toDate, cutoff, bins }),
  getHorizon: (fromDate: string, toDate: string) =>
    apiFetch<HorizonItem[]>("/api/horizon", { from: fromDate, to: toDate }),
  getBuffer: (fromDate: string, toDate: string, cutoff: string, percentile: number = 90.0) =>
    apiFetch<BufferResponse>("/api/buffer", { from: fromDate, to: toDate, cutoff, percentile }),
  getExportCsvUrl: (fromDate: string, toDate: string, cutoff: string) => {
    return `${API_BASE_URL}/api/export.csv?from=${encodeURIComponent(fromDate)}&to=${encodeURIComponent(toDate)}&cutoff=${encodeURIComponent(cutoff)}`;
  },
};
