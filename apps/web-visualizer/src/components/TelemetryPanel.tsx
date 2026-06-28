"use client";

import React, { useState, useMemo } from "react";
import { useTelemetryStore } from "../hooks/useTelemetryStore";
import { Badge } from "./ui/Badge";
import { Search, Heart, Shield, Award, Zap } from "lucide-react";

export default function TelemetryPanel() {
  const { state, dispatch } = useTelemetryStore();
  const [teamFilter, setTeamFilter] = useState<"all" | "home" | "away">("all");
  const [searchTerm, setSearchTerm] = useState("");

  const frame = state.latestFrame;
  const players = frame?.players || [];
  const kinematics = frame?.analytics?.kinematics || {};
  const selectedPlayerId = state.selectedPlayerId;

  // Filter and sort players
  const filteredPlayers = useMemo(() => {
    return players
      .filter((p) => {
        const matchesTeam = teamFilter === "all" || p.team === teamFilter;
        const matchesSearch =
          p.player_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
          p.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
          p.jersey_number.toString().includes(searchTerm);
        return matchesTeam && matchesSearch;
      })
      .sort((a, b) => {
        // Sort home first, then away; and GK/Defenders/Midfielders/Forwards
        if (a.team !== b.team) return a.team === "home" ? -1 : 1;
        return a.jersey_number - b.jersey_number;
      });
  }, [players, teamFilter, searchTerm]);

  const handleSelectPlayer = (id: string) => {
    if (selectedPlayerId === id) {
      dispatch({ type: "SET_SELECTED_PLAYER", payload: null });
    } else {
      dispatch({ type: "SET_SELECTED_PLAYER", payload: id });
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      {/* Filters Bar */}
      <div className="flex gap-2 mb-3">
        <button
          onClick={() => setTeamFilter("all")}
          className={`flex-1 py-1 rounded text-xs font-mono font-medium border ${
            teamFilter === "all"
              ? "bg-cyber-primary/10 text-cyber-primary border-cyber-primary/30"
              : "text-cyber-muted border-cyber-border/40 hover:text-cyber-text"
          }`}
        >
          All
        </button>
        <button
          onClick={() => setTeamFilter("home")}
          className={`flex-1 py-1 rounded text-xs font-mono font-medium border ${
            teamFilter === "home"
              ? "bg-cyber-primary/10 text-cyber-primary border-cyber-primary/30"
              : "text-cyber-muted border-cyber-border/40 hover:text-cyber-text"
          }`}
        >
          Home
        </button>
        <button
          onClick={() => setTeamFilter("away")}
          className={`flex-1 py-1 rounded text-xs font-mono font-medium border ${
            teamFilter === "away"
              ? "bg-cyber-primary/10 text-cyber-primary border-cyber-primary/30"
              : "text-cyber-muted border-cyber-border/40 hover:text-cyber-text"
          }`}
        >
          Away
        </button>
      </div>

      {/* Search Input */}
      <div className="relative mb-3">
        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-cyber-muted">
          <Search size={12} />
        </span>
        <input
          type="text"
          placeholder="Search by ID, role, jersey..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-8 pr-3 py-1.5 bg-cyber-bg/80 border border-cyber-border/40 rounded-lg text-xs font-mono text-cyber-text focus:outline-none focus:border-cyber-primary/60 transition-colors"
        />
      </div>

      {/* Telemetry Grid Table */}
      <div className="flex-1 overflow-y-auto border border-cyber-border/30 rounded-xl bg-cyber-bg/40">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-cyber-border/40 bg-cyber-card/60 text-[9px] font-mono uppercase tracking-wider text-cyber-muted sticky top-0 z-10">
              <th className="py-2 px-3">Player</th>
              <th className="py-2 px-2 text-right">Speed</th>
              <th className="py-2 px-2 text-right">Heart Rate</th>
              <th className="py-2 px-3 text-right">Sprint Dst</th>
            </tr>
          </thead>
          <tbody>
            {filteredPlayers.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-xs font-mono text-cyber-muted">
                  No telemetry nodes found.
                </td>
              </tr>
            ) : (
              filteredPlayers.map((p) => {
                const k = kinematics[p.player_id] || {
                  speed_kmh: 0,
                  acceleration: 0,
                  is_sprinting: false,
                  heart_rate: 130,
                  sprint_distance: 0,
                };
                const isSelected = selectedPlayerId === p.player_id;
                const isHome = p.team === "home";
                const rowGlow = isSelected
                  ? "bg-cyber-primary/10 border-l-2 border-cyber-primary"
                  : k.is_sprinting
                  ? "bg-cyber-success/5 hover:bg-cyber-card/60"
                  : "hover:bg-cyber-card/40";

                return (
                  <tr
                    key={p.player_id}
                    onClick={() => handleSelectPlayer(p.player_id)}
                    className={`border-b border-cyber-border/20 cursor-pointer transition-colors duration-150 ${rowGlow}`}
                  >
                    {/* Player Info */}
                    <td className="py-2 px-3 flex items-center gap-2">
                      <div
                        className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border ${
                          isHome
                            ? "bg-cyber-primary/20 text-cyber-primary border-cyber-primary/30"
                            : "bg-cyber-warning/20 text-cyber-warning border-cyber-warning/30"
                        }`}
                      >
                        {p.jersey_number}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[11px] font-mono font-medium text-cyber-text">
                          {p.role}
                        </span>
                        <span className="text-[9px] font-mono text-cyber-muted">
                          {p.player_id}
                        </span>
                      </div>
                    </td>

                    {/* Speed */}
                    <td className="py-2 px-2 text-right">
                      <div className="flex flex-col items-end">
                        <span className="text-[11px] font-mono font-semibold text-cyber-text">
                          {k.speed_kmh} <span className="text-[8px] text-cyber-muted font-normal">km/h</span>
                        </span>
                        {k.is_sprinting && (
                          <Badge variant="success" className="text-[7px] px-1 py-0 mt-0.5">
                            SPRINT
                          </Badge>
                        )}
                      </div>
                    </td>

                    {/* Heart Rate */}
                    <td className="py-2 px-2 text-right">
                      <div className="flex items-center justify-end gap-1 font-mono text-[11px] font-semibold text-cyber-text">
                        <Heart
                          size={10}
                          className={`${
                            k.heart_rate > 175
                              ? "text-cyber-danger fill-cyber-danger animate-pulse"
                              : "text-cyber-muted"
                          }`}
                        />
                        <span
                          className={
                            k.heart_rate > 175
                              ? "text-cyber-danger"
                              : k.heart_rate > 155
                              ? "text-cyber-warning"
                              : "text-cyber-text"
                          }
                        >
                          {k.heart_rate}
                        </span>
                      </div>
                    </td>

                    {/* Sprint Distance */}
                    <td className="py-2 px-3 text-right text-[11px] font-mono font-semibold text-cyber-text">
                      {k.sprint_distance.toFixed(1)} <span className="text-[8px] text-cyber-muted font-normal">m</span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
