"use client";

import React, { useRef, useEffect } from "react";
import { useTelemetryStore } from "../hooks/useTelemetryStore";
import { Badge } from "./ui/Badge";
import { Card } from "./ui/Card";
import { Target, Shield, AlertTriangle, Crosshair, ArrowUpRight, Cpu } from "lucide-react";

export default function MARLPanel() {
  const { state } = useTelemetryStore();
  const frame = state.latestFrame;
  const selectedPlayerId = state.selectedPlayerId;

  const compactness = frame?.analytics?.compactness || { home: 0, away: 0 };
  const marlData = frame?.marl || {
    predictions: {},
    counter_press_alerts: [],
    out_of_position_warnings: [],
    xg_prediction: 0.05
  };

  // Refs for progress bars to avoid inline style linter warnings
  const xgBarRef = useRef<HTMLDivElement>(null);
  const homeCompRef = useRef<HTMLDivElement>(null);
  const awayCompRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (xgBarRef.current) {
      xgBarRef.current.style.width = `${marlData.xg_prediction * 100}%`;
    }
  }, [marlData.xg_prediction]);

  useEffect(() => {
    if (homeCompRef.current) {
      homeCompRef.current.style.width = `${Math.min(100, (compactness.home / 1000) * 100)}%`;
    }
  }, [compactness.home]);

  useEffect(() => {
    if (awayCompRef.current) {
      awayCompRef.current.style.width = `${Math.min(100, (compactness.away / 1000) * 100)}%`;
    }
  }, [compactness.away]);

  // Actions map
  const ACTIONS = ["PASS", "RUN", "TACKLE", "SHOT", "IDLE"];

  // Find selected player prediction details
  const selectedPrediction = selectedPlayerId ? marlData.predictions[selectedPlayerId] : null;
  const selectedPlayer = selectedPlayerId
    ? frame?.players.find((p) => p.player_id === selectedPlayerId)
    : null;

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-12rem)] overflow-y-auto pr-1">
      {/* Target/xG Prediction Metric */}
      <Card className="relative overflow-hidden border-cyber-primary/20">
        <div className="absolute top-0 right-0 p-1 px-2 bg-cyber-primary/10 border-l border-b border-cyber-primary/20 rounded-bl text-[8px] font-mono text-cyber-primary uppercase tracking-wider flex items-center gap-1">
          <Target size={8} /> Live xG Metric
        </div>
        <span className="text-[10px] font-mono text-cyber-muted uppercase tracking-wider block">Expected Goals (xG)</span>
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-3xl font-mono font-bold text-glow text-cyber-primary">
            {marlData.xg_prediction.toFixed(2)}
          </span>
          <span className="text-xs font-mono text-cyber-muted">probability</span>
        </div>
        {/* Progress Bar */}
        <div className="w-full bg-cyber-border/40 h-1.5 rounded-full mt-3 overflow-hidden">
          <div
            ref={xgBarRef}
            className="bg-gradient-to-r from-cyber-primary to-cyber-success h-full transition-all duration-300 shadow-glow"
          />
        </div>
      </Card>

      {/* Selected Player Agent Recommendations */}
      <Card className={selectedPlayer ? "border-cyber-primary/40 shadow-glow/5" : "border-cyber-border/40"}>
        <div className="flex items-center gap-2 mb-3">
          <Cpu size={14} className="text-cyber-primary" />
          <h3 className="text-xs font-mono font-bold text-cyber-text uppercase tracking-wider">
            MARL Tactical Override Suggestions
          </h3>
        </div>

        {selectedPlayer ? (
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center bg-cyber-bg/60 p-2 rounded-lg border border-cyber-border/30">
              <div className="flex items-center gap-2">
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    selectedPlayer.team === "home"
                      ? "bg-cyber-primary/20 text-cyber-primary"
                      : "bg-cyber-warning/20 text-cyber-warning"
                  }`}
                >
                  {selectedPlayer.jersey_number}
                </span>
                <div className="flex flex-col">
                  <span className="text-[11px] font-mono font-medium text-cyber-text">
                    {selectedPlayer.role}
                  </span>
                  <span className="text-[9px] font-mono text-cyber-muted">{selectedPlayer.player_id}</span>
                </div>
              </div>
              <Badge variant={selectedPlayer.team === "home" ? "primary" : "warning"}>
                {selectedPlayer.team.toUpperCase()}
              </Badge>
            </div>

            {selectedPrediction ? (
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-cyber-bg/40 p-2 rounded-lg border border-cyber-border/20">
                  <span className="text-[9px] text-cyber-muted uppercase block">Suggested Action</span>
                  <span className="font-bold text-cyber-success mt-0.5 block text-sm">
                    {ACTIONS[selectedPrediction.suggested_action]}
                  </span>
                </div>
                <div className="bg-cyber-bg/40 p-2 rounded-lg border border-cyber-border/20">
                  <span className="text-[9px] text-cyber-muted uppercase block">Model Confidence</span>
                  <span className="font-bold text-cyber-primary mt-0.5 block text-sm">
                    {(selectedPrediction.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="col-span-2 bg-cyber-bg/40 p-2 rounded-lg border border-cyber-border/20 flex justify-between items-center">
                  <div>
                    <span className="text-[9px] text-cyber-muted uppercase block">Predicted Landing Coordinates</span>
                    <span className="text-[10px] text-cyber-text font-bold mt-0.5 block">
                      X: {selectedPrediction.predicted_position.x.toFixed(1)}m, Y: {selectedPrediction.predicted_position.y.toFixed(1)}m
                    </span>
                  </div>
                  <Crosshair size={14} className="text-cyber-muted" />
                </div>
              </div>
            ) : (
              <span className="text-[10px] font-mono text-cyber-muted italic">
                Awaiting agent state evaluation frame...
              </span>
            )}
          </div>
        ) : (
          <div className="text-center py-6 text-xs font-mono text-cyber-muted italic">
            Select a player on the canvas or table to view custom MARL recommendations.
          </div>
        )}
      </Card>

      {/* Team Compactness Areas */}
      <Card>
        <h4 className="text-xs font-mono font-bold text-cyber-text uppercase tracking-wider mb-3">
          Tactical Coverage Compactness
        </h4>
        <div className="flex flex-col gap-3 font-mono text-xs">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-cyber-primary font-medium">Home Outfield (Convex Hull)</span>
              <span>{compactness.home.toFixed(0)} m²</span>
            </div>
            <div className="w-full bg-cyber-border/40 h-2 rounded-full overflow-hidden">
              <div
                ref={homeCompRef}
                className="bg-cyber-primary h-full transition-all duration-300"
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-cyber-warning font-medium">Away Outfield (Convex Hull)</span>
              <span>{compactness.away.toFixed(0)} m²</span>
            </div>
            <div className="w-full bg-cyber-border/40 h-2 rounded-full overflow-hidden">
              <div
                ref={awayCompRef}
                className="bg-cyber-warning h-full transition-all duration-300"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Dynamic Alerts Feed */}
      <div className="flex-1 flex flex-col gap-2">
        <h4 className="text-xs font-mono font-bold text-cyber-text uppercase tracking-wider">
          Live Tactical Intelligence Alert Feed
        </h4>

        <div className="flex-1 overflow-y-auto flex flex-col gap-2 max-h-[14rem]">
          {marlData.counter_press_alerts.map((alert, idx) => (
            <div
              key={`cp-${idx}`}
              className="p-2.5 rounded-lg border border-cyber-danger/30 bg-cyber-danger/5 flex items-start gap-2 animate-pulse"
            >
              <AlertTriangle size={14} className="text-cyber-danger mt-0.5 shrink-0" />
              <div className="font-mono text-xs">
                <div className="flex items-center gap-1.5 font-bold text-cyber-danger uppercase text-[10px]">
                  <span>{alert.team} Team Alert</span>
                  <Badge variant="danger" className="text-[7px] px-1">Press Warning</Badge>
                </div>
                <p className="text-[11px] text-cyber-text/90 mt-1">{alert.message}</p>
                <span className="text-[8px] text-cyber-muted mt-1 block">
                  Area: {alert.compactness_area.toFixed(0)} m²
                </span>
              </div>
            </div>
          ))}

          {marlData.out_of_position_warnings.map((warn, idx) => (
            <div
              key={`oop-${idx}`}
              className="p-2.5 rounded-lg border border-cyber-warning/30 bg-cyber-warning/5 flex items-start gap-2"
            >
              <AlertTriangle size={14} className="text-cyber-warning mt-0.5 shrink-0" />
              <div className="font-mono text-xs">
                <div className="flex items-center gap-1.5 font-bold text-cyber-warning uppercase text-[10px]">
                  <span>{warn.player_id} Warn</span>
                  <Badge variant="warning" className="text-[7px] px-1">Out of Position</Badge>
                </div>
                <p className="text-[11px] text-cyber-text/90 mt-0.5">
                  {warn.role} (Jersey {warn.jersey_number}) deviated by {warn.deviation_meters}m from defensive templates.
                </p>
              </div>
            </div>
          ))}

          {marlData.counter_press_alerts.length === 0 &&
            marlData.out_of_position_warnings.length === 0 && (
              <div className="text-center py-6 text-xs font-mono text-cyber-muted italic border border-cyber-border/20 rounded-xl bg-cyber-bg/20">
                Structural configurations nominal. No anomalies detected.
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
