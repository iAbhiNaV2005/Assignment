"use client";

import React from "react";
import { Activity, BarChart3, BookOpen, ExternalLink, ShieldCheck, Zap } from "lucide-react";

interface NavbarProps {
  activeTab: "decision" | "accuracy" | "methodology";
  setActiveTab: (tab: "decision" | "accuracy" | "methodology") => void;
  apiHealthStatus?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, apiHealthStatus }) => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-white">UK Wind Power</span>
              <span className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 text-xs font-semibold text-cyan-400">
                Day-Ahead Desk
              </span>
            </div>
            <p className="text-xs text-slate-400">Elexon BMRS Procurement & Risk Decision Portal</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/60 p-1">
          <button
            onClick={() => setActiveTab("decision")}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium transition-all ${
              activeTab === "decision"
                ? "bg-cyan-500 text-white shadow-sm shadow-cyan-500/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            Decision Desk
          </button>
          <button
            onClick={() => setActiveTab("accuracy")}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium transition-all ${
              activeTab === "accuracy"
                ? "bg-cyan-500 text-white shadow-sm shadow-cyan-500/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5" />
            Accuracy & Risk
          </button>
          <button
            onClick={() => setActiveTab("methodology")}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium transition-all ${
              activeTab === "methodology"
                ? "bg-cyan-500 text-white shadow-sm shadow-cyan-500/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <BookOpen className="h-3.5 w-3.5" />
            Methodology & Specs
          </button>
        </nav>

        {/* Status Indicators & Docs */}
        <div className="hidden items-center gap-3 sm:flex">
          <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            {apiHealthStatus === "healthy" ? "BMRS Ingested" : "Ready"}
          </div>

          <div className="flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs text-slate-300">
            <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
            Strict Anti-Leakage
          </div>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-xs text-slate-400 transition hover:text-cyan-400"
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
