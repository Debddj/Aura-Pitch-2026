"use client";

import React, { useState } from "react";
import { TelemetryStoreProvider, useTelemetryStore } from "../hooks/useTelemetryStore";
import { useWebSocket } from "../hooks/useWebSocket";
import TacticalCanvas from "../components/TacticalCanvas";
import PlaybackControls from "../components/PlaybackControls";
import TelemetryPanel from "../components/TelemetryPanel";
import MARLPanel from "../components/MARLPanel";
import ObservabilityPanel from "../components/ObservabilityPanel";
import { Tabs } from "../components/ui/Tabs";
import { Cpu, Activity, Info, LogIn } from "lucide-react";

function VisualizerDashboard() {
  const { state } = useTelemetryStore();
  const { wsConnected } = useWebSocket();
  const [activeTab, setActiveTab] = useState("telemetry");

  const tabs = [
    { id: "telemetry", label: "Telemetry Stream" },
    { id: "marl", label: "MARL Inference" },
    { id: "observability", label: "MLOps Metrics" },
  ];

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-cyber-bg text-cyber-text">
      {/* Dynamic Cyberpunk Header */}
      <header className="h-14 border-b border-cyber-border/40 px-6 flex items-center justify-between glass shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyber-primary/20 border border-cyber-primary/30 flex items-center justify-center text-cyber-primary">
            <Cpu size={18} className="animate-pulse" />
          </div>
          <div>
            <h1 className="text-sm font-mono font-bold tracking-wider uppercase text-glow text-cyber-text">
              AuraPitch 2026
            </h1>
            <span className="text-[9px] font-mono text-cyber-muted uppercase tracking-widest block">
              Distributed Multi-Agent Tactical Synthesizer
            </span>
          </div>
        </div>

        {/* Global Connection Details */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="hidden md:flex flex-col items-end">
            <span className="text-[8px] text-cyber-muted uppercase">Observer Mode</span>
            <span className="text-[11px] text-cyber-primary font-bold">FIFA World Cup 2026 (Digital Twin)</span>
          </div>

          <div className="h-6 w-px bg-cyber-border/40" />

          {/* Connection Pill */}
          <div className={`px-2.5 py-1 rounded-full border text-[10px] font-semibold tracking-wider uppercase flex items-center gap-1.5 ${
            wsConnected 
              ? "bg-cyber-success/10 text-cyber-success border-cyber-success/20 shadow-glow-success/10" 
              : "bg-cyber-danger/10 text-cyber-danger border-cyber-danger/20 shadow-glow-warning/10"
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? "bg-cyber-success" : "bg-cyber-danger animate-ping"}`} />
            {wsConnected ? "Sync: active" : "Sync: searching"}
          </div>
        </div>
      </header>

      {/* Main Grid View */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Side: 3D Tactical Canvas View (~60%) */}
        <section className="flex-1 relative border-r border-cyber-border/40 bg-cyber-bg">
          {/* 3D WebGL tactical viewport */}
          <TacticalCanvas />

          {/* Floaters overlays */}
          <PlaybackControls />
          
          {/* Explanatory Overlay Badge */}
          <div className="absolute bottom-4 left-4 z-10 glass rounded-lg p-2 max-w-xs border border-cyber-border/40 pointer-events-none">
            <span className="text-[9px] font-mono text-cyber-muted block flex items-center gap-1">
              <Info size={10} /> Camera Controls
            </span>
            <p className="text-[8px] font-mono text-cyber-muted leading-relaxed mt-1">
              Left Click + Drag: Rotate View. Right Click + Drag: Pan. Scroll wheel: Zoom. Select jersey nodes to display MARL insights.
            </p>
          </div>
        </section>

        {/* Right Side: Analytical Panels Switcher (~40% width, min 380px, max 480px) */}
        <section className="w-[390px] xl:w-[450px] h-full flex flex-col p-4 glass shrink-0 overflow-hidden">
          {/* Section Selector tabs */}
          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          {/* Active Panel container */}
          <div className="flex-1 overflow-hidden">
            {activeTab === "telemetry" && <TelemetryPanel />}
            {activeTab === "marl" && <MARLPanel />}
            {activeTab === "observability" && <ObservabilityPanel />}
          </div>
        </section>
      </main>
    </div>
  );
}

export default function Page() {
  return (
    <TelemetryStoreProvider>
      <VisualizerDashboard />
    </TelemetryStoreProvider>
  );
}
