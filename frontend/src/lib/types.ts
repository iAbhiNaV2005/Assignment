export interface HealthResponse {
  status: string;
  databasePath: string;
  databaseSizeBytes: number;
  actualRecordsCount: number;
  forecastRecordsCount: number;
  dataRangeStart: string | null;
  dataRangeEnd: string | null;
}

export interface ConfigResponse {
  minDate: string;
  maxDate: string;
  defaultCutoff: string;
  defaultPercentile: number;
  timeZone: string;
}

export interface PeriodDecision {
  startTime: string;
  settlementDate: string;
  settlementPeriod: number;
  actual: number | null;
  forecast: number | null;
  error: number | null;
  shortfall: number | null;
  publishTime: string | null;
  cutoffUtc: string;
}

export interface DaySummary {
  date: string;
  totalPeriods: number;
  meanActualMw: number | null;
  meanForecastMw: number | null;
  maeMw: number | null;
  rmseMw: number | null;
  biasMw: number | null;
  shortfallP90Mw: number | null;
}

export interface DecisionResponse {
  deliveryDate: string;
  cutoffLocal: string;
  cutoffUtc: string;
  summary: DaySummary;
  periods: PeriodDecision[];
}

export interface RevisionPoint {
  startTime: string;
  settlementPeriod: number;
  forecast: number | null;
}

export interface RevisionSeries {
  publishTime: string;
  isDecisionForecast: boolean;
  data: RevisionPoint[];
}

export interface ActualPoint {
  startTime: string;
  settlementPeriod: number;
  actual: number | null;
}

export interface RevisionsResponse {
  deliveryDate: string;
  cutoffUtc: string;
  decisionPublishTime: string | null;
  revisions: RevisionSeries[];
  actuals: ActualPoint[];
}

export interface MetricsResponse {
  dateFrom: string;
  dateTo: string;
  cutoffLocal: string;
  totalPeriods: number;
  evaluatedPeriods: number;
  coveragePct: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  nmae: number | null;
  meanActual: number | null;
  meanForecast: number | null;
  p10Error: number | null;
  p50Error: number | null;
  p90Error: number | null;
  p95AbsError: number | null;
  shareOverPct: number | null;
  shareUnderPct: number | null;
}

export interface DailyBreakdownItem {
  date: string;
  periods: number;
  mae: number;
  rmse: number;
  bias: number;
  meanActual: number;
  meanForecast: number;
  shortfallP90: number;
}

export interface HourlyBreakdownItem {
  hour: number;
  hourLabel: string;
  periods: number;
  mae: number;
  rmse: number;
  bias: number;
  meanActual: number;
  meanForecast: number;
}

export interface WindLevelBreakdownItem {
  level: string;
  periods: number;
  pctOfTotal: number;
  mae: number;
  rmse: number;
  bias: number;
  meanActual: number;
}

export interface HistogramBin {
  binStart: number;
  binEnd: number;
  binCenter: number;
  count: number;
}

export interface HorizonItem {
  bucket: string;
  sampleCount: number;
  mae: number;
  rmse: number;
  bias: number;
}

export interface DailyBacktestItem {
  date: string;
  isWarmup: boolean;
  calibratedBufferMw: number | null;
  maxShortfallMw: number;
  periodsCovered: number;
  totalPeriods: number;
  coveragePct: number;
}

export interface BufferResponse {
  targetPercentile: number;
  inSampleBufferMw: number;
  backtestBufferAvgMw: number;
  achievedCoveragePct: number;
  totalEvaluatedPeriods: number;
  coveredPeriods: number;
  dailyBacktest: DailyBacktestItem[];
}
