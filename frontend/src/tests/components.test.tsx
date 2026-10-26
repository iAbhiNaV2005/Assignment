import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { KPICard } from "../components/KPICard";
import { Navbar } from "../components/Navbar";
import { MethodologyView } from "../components/MethodologyView";
import { DecisionView } from "../components/DecisionView";

describe("KPICard Component", () => {
  it("renders metric title, value, unit, and badge properly", () => {
    render(
      <KPICard
        title="Mean absolute error"
        value="2,145"
        unit="MW"
        subtitle="Average forecast miss"
        badge={{ text: "MAE", variant: "info" }}
      />
    );

    expect(screen.getByText("Mean absolute error")).toBeInTheDocument();
    expect(screen.getByText("2,145")).toBeInTheDocument();
    expect(screen.getByText("MW")).toBeInTheDocument();
    expect(screen.getByText("Average forecast miss")).toBeInTheDocument();
    expect(screen.getByText("MAE")).toBeInTheDocument();
  });

  it("handles null values gracefully with dash placeholder", () => {
    render(<KPICard title="Empty Metric" value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("Navbar Component", () => {
  it("renders brand title and responds to tab switching", () => {
    const setActiveTab = vi.fn();
    render(
      <Navbar
        activeTab="decision"
        setActiveTab={setActiveTab}
        apiHealthStatus="healthy"
      />
    );

    expect(screen.getByText("UK Wind Power")).toBeInTheDocument();
    expect(screen.getByText("BMRS Ingested")).toBeInTheDocument();

    const accuracyTab = screen.getByText("Accuracy & Risk");
    fireEvent.click(accuracyTab);
    expect(setActiveTab).toHaveBeenCalledWith("accuracy");
  });
});

describe("DecisionView Component", () => {
  const mockDecisionData = {
    deliveryDate: "2026-01-15",
    cutoffLocal: "09:00",
    cutoffUtc: "2026-01-14T09:00:00Z",
    summary: {
      date: "2026-01-15",
      totalPeriods: 48,
      meanActualMw: 12000,
      meanForecastMw: 13500,
      maeMw: 1500,
      rmseMw: 1800,
      biasMw: 1500,
      shortfallP90Mw: 3200,
    },
    periods: [
      {
        startTime: "2026-01-15T00:00:00Z",
        settlementDate: "2026-01-15",
        settlementPeriod: 1,
        actual: 11000,
        forecast: 12500,
        error: 1500,
        shortfall: 1500,
        publishTime: "2026-01-14T07:30:00Z",
        cutoffUtc: "2026-01-14T09:00:00Z",
      },
    ],
  };

  it("renders decision summary, KPI cards, and responds to subtab clicks", () => {
    render(
      <DecisionView
        selectedDate="2026-01-15"
        setSelectedDate={vi.fn()}
        cutoffTime="09:00"
        setCutoffTime={vi.fn()}
        decisionData={mockDecisionData}
        revisionsData={{ deliveryDate: "2026-01-15", cutoffUtc: "2026-01-14T09:00:00Z", decisionPublishTime: null, revisions: [], actuals: [] }}
        isLoading={false}
        onRefresh={vi.fn()}
      />
    );

    expect(screen.getByText("Decision timeline verified for 2026-01-15")).toBeInTheDocument();
    expect(screen.getByText("13,500")).toBeInTheDocument();

    // Switch to table subtab
    const tableBtn = screen.getByText("Settlement periods table (48 periods)");
    fireEvent.click(tableBtn);
    expect(screen.getByText("48 settlement periods breakdown")).toBeInTheDocument();
    expect(screen.getAllByText("Shortfall risk").length).toBeGreaterThanOrEqual(1);
  });
});

describe("MethodologyView Component", () => {
  it("renders decision timeline, selection rule, and sign convention without crashing", () => {
    render(<MethodologyView />);
    expect(
      screen.getByText("Methodology & Operational Specifications")
    ).toBeInTheDocument();
    expect(
      screen.getByText("1. Decision Timeline & Strict Selection Rule")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Error(T) = Forecast(T) - Actual(T) (MW)")
    ).toBeInTheDocument();
  });
});
