"use client";

import React from "react";
import { useTelemetryStore } from "../hooks/useTelemetryStore";
import { useWebSocket } from "../hooks/useWebSocket";
import { Play, Pause, FastForward, Activity, CheckCircle, AlertTriangle } from "lucide-react";
import { Badge } from "./ui/Badge";

export default function PlaybackControls() {
  const { state } = useTelemetryStore();
  const { sendControl } = useWebSocket();
  const frame = state.latestFrame;

  const clock = frame?.match_clock || "00:00";
  const playbackState = frame?.playback_state || "PLAYING";
  const playbackSpeed = frame?.playback_speed || 1.0;
  const isConnected = state.wsConnected;

  const handlePlay = () => sendControl("PLAYING", 1.0);
  const handlePause = () => sendControl("PAUSED", 1.0);
  const handleFF = () => {
    let nextSpeed = 2.0;
    if (playbackState === "FAST_FORWARD") {
      nextSpeed = playbackSpeed === 2.0 ? 4.0 : 2.0;
    }
    sendControl("FAST_FORWARD", nextSpeed);
  };

  const triggerSetPiece = async (type: "CORNER_KICK" | "FREE_KICK") => {
    try {
      await fetch("http://localhost:8000/api/match/setpiece", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type })
      });
    } catch (e) {
      console.error("Failed to trigger set piece:", e);
    }
  };

  return (
    <div className="absolute top-4 left-4 z-10 glass-cyan rounded-xl p-3 flex items-center gap-4 shadow-glow">
      {/* Connection Indicator */}
      <div className="flex items-center gap-2 border-r border-cyber-border/40 pr-3">
        {isConnected ? (
          <>
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyber-success opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyber-success"></span>
            </span>
            <span className="text-[10px] font-mono text-cyber-success font-semibold tracking-wider uppercase">LIVE</span>
          </>
        ) : (
          <>
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-pulse absolute inline-flex h-full w-full rounded-full bg-cyber-danger opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyber-danger"></span>
            </span>
            <span className="text-[10px] font-mono text-cyber-danger font-semibold tracking-wider uppercase">OFFLINE</span>
          </>
        )}
      </div>

      {/* Match Clock */}
      <div className="flex flex-col">
        <span className="text-[10px] font-mono text-cyber-muted uppercase tracking-wider">Match Time</span>
        <span className="text-xl font-mono font-bold text-glow text-cyber-text tracking-widest">{clock}</span>
      </div>

      {/* Control Buttons */}
      <div className="flex items-center gap-1.5 bg-cyber-bg/60 p-1 rounded-lg border border-cyber-border/30">
        <button
          onClick={handlePlay}
          disabled={!isConnected}
          className={`p-1.5 rounded transition-all duration-200 ${
            playbackState === "PLAYING"
              ? "bg-cyber-primary/20 text-cyber-primary"
              : "text-cyber-muted hover:text-cyber-text hover:bg-cyber-card/40"
          }`}
          title="Play"
        >
          <Play size={14} className="fill-current" />
        </button>

        <button
          onClick={handlePause}
          disabled={!isConnected}
          className={`p-1.5 rounded transition-all duration-200 ${
            playbackState === "PAUSED"
              ? "bg-cyber-primary/20 text-cyber-primary"
              : "text-cyber-muted hover:text-cyber-text hover:bg-cyber-card/40"
          }`}
          title="Pause"
        >
          <Pause size={14} className="fill-current" />
        </button>

        <button
          onClick={handleFF}
          disabled={!isConnected}
          className={`p-1.5 rounded transition-all duration-200 flex items-center gap-1 ${
            playbackState === "FAST_FORWARD"
              ? "bg-cyber-primary/20 text-cyber-primary"
              : "text-cyber-muted hover:text-cyber-text hover:bg-cyber-card/40"
          }`}
          title="Fast Forward"
        >
          <FastForward size={14} className="fill-current" />
          {playbackState === "FAST_FORWARD" && (
            <span className="text-[9px] font-mono font-bold">{playbackSpeed}x</span>
          )}
        </button>

        {/* Set Pieces Simulators */}
        <button
          onClick={() => triggerSetPiece("CORNER_KICK")}
          disabled={!isConnected}
          className="p-1.5 rounded transition-all duration-200 text-cyber-muted hover:text-cyber-text hover:bg-cyber-card/40 text-[9px] font-mono font-bold uppercase tracking-wider px-2 border border-cyber-border/30 bg-cyber-bg/40 ml-2"
          title="Simulate Corner Kick"
        >
          Corner
        </button>
        <button
          onClick={() => triggerSetPiece("FREE_KICK")}
          disabled={!isConnected}
          className="p-1.5 rounded transition-all duration-200 text-cyber-muted hover:text-cyber-text hover:bg-cyber-card/40 text-[9px] font-mono font-bold uppercase tracking-wider px-2 border border-cyber-border/30 bg-cyber-bg/40"
          title="Simulate Free Kick"
        >
          Free Kick
        </button>
      </div>

      {/* Simulation Info */}
      {frame && (
        <div className="hidden sm:flex flex-col border-l border-cyber-border/40 pl-3">
          <span className="text-[9px] font-mono text-cyber-muted uppercase tracking-wider">Frames</span>
          <span className="text-[11px] font-mono font-medium text-cyber-text">{frame.frame_count}</span>
        </div>
      )}
    </div>
  );
}
