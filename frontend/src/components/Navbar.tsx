"use client";

import React from "react";
import { Activity, BarChart3, BookOpen, ExternalLink, ShieldCheck } from "lucide-react";

interface NavbarProps {
  activeTab: "decision" | "accuracy" | "methodology";
  setActiveTab: (tab: "decision" | "accuracy" | "methodology") => void;
  apiHealthStatus?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, apiHealthStatus }) => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#22262e] bg-[#0e1013]">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-2.5 sm:px-6">
        {/* Brand & Terminal Scope */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-[#0284c7] text-white shadow-none">
            {/* Geometric Wind turbine / Terminal monogram */}
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2v20" />
              <path d="M12 12 4 8" />
              <path d="M12 12l8 4" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-[#f3f4f6]">UK Wind Power</span>
              <span className="rounded border border-[#2a2e37] bg-[#16181d] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#9ca3af]">
                BMRS Day-Ahead Desk
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Segmented Control */}
        <nav className="flex items-center gap-1 rounded-lg border border-[#22262e] bg-[#14161b] p-0.5">
          <button
            onClick={() => setActiveTab("decision")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "decision"
                ? "bg-[#22262e] text-[#f3f4f6]"
                : "text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1a1d24]"
            }`}
          >
            <Activity className="h-3.5 w-3.5 text-[#38bdf8]" />
            Decision Desk
          </button>
          <button
            onClick={() => setActiveTab("accuracy")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "accuracy"
                ? "bg-[#22262e] text-[#f3f4f6]"
                : "text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1a1d24]"
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5 text-[#38bdf8]" />
            Accuracy & Risk
          </button>
          <button
            onClick={() => setActiveTab("methodology")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "methodology"
                ? "bg-[#22262e] text-[#f3f4f6]"
                : "text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1a1d24]"
            }`}
          >
            <BookOpen className="h-3.5 w-3.5 text-[#38bdf8]" />
            Methodology & Specs
          </button>
        </nav>

        {/* Status Indicators & Docs */}
        <div className="hidden items-center gap-3 sm:flex">
          <div className="flex items-center gap-1.5 rounded border border-[#1b2f23] bg-[#0c1a13] px-2 py-0.5 text-[11px] font-medium text-[#10b981]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#10b981]" />
            {apiHealthStatus === "healthy" ? "BMRS Ingested" : "Ready"}
          </div>

          <div className="flex items-center gap-1 rounded border border-[#22262e] bg-[#14161b] px-2 py-0.5 text-[11px] text-[#9ca3af]">
            <ShieldCheck className="h-3 w-3 text-[#38bdf8]" />
            Strict Anti-Leakage
          </div>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-[11px] text-[#9ca3af] transition-colors hover:text-[#f3f4f6]"
            title="FastAPI Swagger Documentation"
          >
            API Docs
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </header>
  );
};
