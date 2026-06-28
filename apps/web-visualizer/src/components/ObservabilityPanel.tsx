"use client";

import React, { useEffect, useState } from "react";
import { useTelemetryStore } from "../hooks/useTelemetryStore";
import { Card } from "./ui/Card";
import { Badge } from "./ui/Badge";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { Gauge, Activity, RefreshCw } from "lucide-react";

interface HistoryData {
  time: string;
  p50: number;
  p95: number;
  drift: number;
}

export default function ObservabilityPanel() {
  const { state } = useTelemetryStore();
  const frame = state.latestFrame;
  const metrics = frame?.observability || {
    e2e_latency_ms: { avg: 4.5, p50: 4.2, p95: 5.8, p99: 7.2 },
    throughput_fps: 20.0,
    data_drift_score: 0.08
  };

  const [history, setHistory] = useState<HistoryData[]>([]);

  // Collect history points for the charts
  useEffect(() => {
    if (!frame) return;

    const clockStr = frame.match_clock;
    setHistory((prev) => {
      const next = [
        ...prev,
        {
          time: clockStr,
          p50: metrics.e2e_latency_ms.p50,
          p95: metrics.e2e_latency_ms.p95,
          drift: metrics.data_drift_score,
        },
      ];
      // Keep last 15 ticks for chart readability
      if (next.length > 15) {
        return next.slice(1);
      }
      return next;
    });
  }, [frame, metrics.e2e_latency_ms.p50, metrics.e2e_latency_ms.p95, metrics.data_drift_score]);

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-12rem)] overflow-y-auto pr-1">
      
      {/* Top Cards Grid */}
      <div className="grid grid-cols-2 gap-2">
        <Card className="flex flex-col justify-between">
          <div>
            <span className="text-[9px] font-mono text-cyber-muted uppercase tracking-wider block">Throughput Scale</span>
            <span className="text-2xl font-mono font-bold text-glow text-cyber-primary mt-1 block">
              {metrics.throughput_fps.toFixed(1)}
            </span>
          </div>
          <span className="text-[8px] font-mono text-cyber-muted mt-2 uppercase tracking-wide flex items-center gap-1">
            <Activity size={10} className="animate-pulse text-cyber-primary" /> events / sec
          </span>
        </Card>

        <Card className="flex flex-col justify-between">
          <div>
            <span className="text-[9px] font-mono text-cyber-muted uppercase tracking-wider block">Data Drift Index</span>
            <span className={`text-2xl font-mono font-bold text-glow mt-1 block ${
              metrics.data_drift_score > 0.4 ? "text-cyber-warning" : "text-cyber-success"
            }`}>
              {metrics.data_drift_score.toFixed(3)}
            </span>
          </div>
          <span className="text-[8px] font-mono text-cyber-muted mt-2 uppercase tracking-wide flex items-center gap-1">
            <RefreshCw size={10} className="text-cyber-muted" /> Kolmogorov-Smirnov
          </span>
        </Card>
      </div>

      {/* Latency Percentiles Card */}
      <Card>
        <div className="flex justify-between items-center mb-3">
          <h4 className="text-xs font-mono font-bold text-cyber-text uppercase tracking-wider">
            Latency Percentiles (E2E)
          </h4>
          <Badge variant="primary">p50 / p95 / p99</Badge>
        </div>

        <div className="grid grid-cols-3 gap-1 bg-cyber-bg/60 p-2 rounded-lg border border-cyber-border/30 text-center font-mono mb-4">
          <div>
            <span className="text-[8px] text-cyber-muted uppercase">p50 (Median)</span>
            <span className="text-sm font-bold text-cyber-text block mt-0.5">
              {metrics.e2e_latency_ms.p50.toFixed(1)}ms
            </span>
          </div>
          <div>
            <span className="text-[8px] text-cyber-muted uppercase">p95 (95th)</span>
            <span className="text-sm font-bold text-cyber-primary block mt-0.5">
              {metrics.e2e_latency_ms.p95.toFixed(1)}ms
            </span>
          </div>
          <div>
            <span className="text-[8px] text-cyber-muted uppercase">p99 (Spike)</span>
            <span className="text-sm font-bold text-cyber-warning block mt-0.5">
              {metrics.e2e_latency_ms.p99.toFixed(1)}ms
            </span>
          </div>
        </div>

        {/* Real-time Latency Chart */}
        <div className="h-44 w-full text-xs">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
              <XAxis dataKey="time" stroke="#71717a" fontSize={9} tickLine={false} />
              <YAxis stroke="#71717a" fontSize={9} tickLine={false} domain={[0, 'auto']} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
                labelStyle={{ color: '#a1a1aa', fontFamily: 'monospace', fontSize: 10 }}
                itemStyle={{ color: '#06b6d4', fontFamily: 'monospace', fontSize: 10 }}
              />
              <Line type="monotone" dataKey="p50" stroke="#06b6d4" strokeWidth={1.5} dot={false} name="p50 Med" />
              <Line type="monotone" dataKey="p95" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="p95 Spike" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Spatial Drift Distribution Card */}
      <Card>
        <h4 className="text-xs font-mono font-bold text-cyber-text uppercase tracking-wider mb-2">
          Model Drift Over Match Clock
        </h4>
        <p className="text-[10px] font-mono text-cyber-muted leading-relaxed mb-3">
          Statistical variance in spatial player trajectories. High index represents play divergence from standard baseline templates.
        </p>

        {/* Drift Timeline Chart */}
        <div className="h-28 w-full text-xs">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
              <XAxis dataKey="time" stroke="#71717a" fontSize={9} tickLine={false} />
              <YAxis stroke="#71717a" fontSize={9} tickLine={false} domain={[0, 1.0]} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
                labelStyle={{ color: '#a1a1aa', fontFamily: 'monospace', fontSize: 10 }}
                itemStyle={{ color: '#10b981', fontFamily: 'monospace', fontSize: 10 }}
              />
              <Line type="monotone" dataKey="drift" stroke="#10b981" strokeWidth={1.5} dot={false} name="Drift Score" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
      
    </div>
  );
}
