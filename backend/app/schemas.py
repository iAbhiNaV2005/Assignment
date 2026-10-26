"""Pydantic schemas for typed API request validation and response models."""


from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    databasePath: str
    databaseSizeBytes: int
    actualRecordsCount: int
    forecastRecordsCount: int
    dataRangeStart: str | None
    dataRangeEnd: str | None


class ConfigResponse(BaseModel):
    minDate: str
    maxDate: str
    defaultCutoff: str
    defaultPercentile: float
    timeZone: str


class PeriodDecision(BaseModel):
    startTime: str
    settlementDate: str
    settlementPeriod: int
    actual: float | None
    forecast: float | None
    error: float | None
    shortfall: float | None
    publishTime: str | None
    cutoffUtc: str


class DaySummary(BaseModel):
    date: str
    totalPeriods: int
    meanActualMw: float | None
    meanForecastMw: float | None
    maeMw: float | None
    rmseMw: float | None
    biasMw: float | None
    shortfallP90Mw: float | None


class DecisionResponse(BaseModel):
    deliveryDate: str
    cutoffLocal: str
    cutoffUtc: str
    summary: DaySummary
    periods: list[PeriodDecision]


class RevisionPoint(BaseModel):
    startTime: str
    settlementPeriod: int
    forecast: float | None


class RevisionSeries(BaseModel):
    publishTime: str
    isDecisionForecast: bool
    data: list[RevisionPoint]


class ActualPoint(BaseModel):
    startTime: str
    settlementPeriod: int
    actual: float | None


class RevisionsResponse(BaseModel):
    deliveryDate: str
    cutoffUtc: str
    decisionPublishTime: str | None
    revisions: list[RevisionSeries]
    actuals: list[ActualPoint]


class MetricsResponse(BaseModel):
    dateFrom: str
    dateTo: str
    cutoffLocal: str
    totalPeriods: int
    evaluatedPeriods: int
    coveragePct: float
    mae: float | None
    rmse: float | None
    bias: float | None
    nmae: float | None
    meanActual: float | None
    meanForecast: float | None
    p10Error: float | None
    p50Error: float | None
    p90Error: float | None
    p95AbsError: float | None
    shareOverPct: float | None
    shareUnderPct: float | None


class DailyBreakdownItem(BaseModel):
    date: str
    periods: int
    mae: float
    rmse: float
    bias: float
    meanActual: float
    meanForecast: float
    shortfallP90: float


class HourlyBreakdownItem(BaseModel):
    hour: int
    hourLabel: str
    periods: int
    mae: float
    rmse: float
    bias: float
    meanActual: float
    meanForecast: float


class WindLevelBreakdownItem(BaseModel):
    level: str
    periods: int
    pctOfTotal: float
    mae: float
    rmse: float
    bias: float
    meanActual: float


class HistogramBin(BaseModel):
    binStart: float
    binEnd: float
    binCenter: float
    count: int


class HorizonItem(BaseModel):
    bucket: str
    sampleCount: int
    mae: float
    rmse: float
    bias: float


class DailyBacktestItem(BaseModel):
    date: str
    isWarmup: bool
    calibratedBufferMw: float | None
    maxShortfallMw: float
    periodsCovered: int
    totalPeriods: int
    coveragePct: float


class BufferResponse(BaseModel):
    targetPercentile: float
    inSampleBufferMw: float
    backtestBufferAvgMw: float
    achievedCoveragePct: float
    totalEvaluatedPeriods: int
    coveredPeriods: int
    dailyBacktest: list[DailyBacktestItem]
