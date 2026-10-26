import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { KPICard } from "../components/KPICard";
import { Navbar } from "../components/Navbar";
import { MethodologyView } from "../components/MethodologyView";

describe("KPICard Component", () => {
  it("renders metric title, value, unit, and badge properly", () => {
    render(
      <KPICard
        title="Mean Absolute Error"
        value="2,145"
        unit="MW"
        subtitle="Average forecast miss"
        badge={{ text: "MAE", variant: "info" }}
      />
    );

    expect(screen.getByText("Mean Absolute Error")).toBeInTheDocument();
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
