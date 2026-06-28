"use client";

import React, { createContext, useContext, useReducer, ReactNode } from "react";

// ---------------------------------------------------------------------------
// Type Definitions
// ---------------------------------------------------------------------------
export interface Position {
  x: number;
  y: number;
  z: number;
}

export interface PlayerNode {
  player_id: string;
  team: "home" | "away";
  jersey_number: number;
  role: string;
  position: Position;
  velocity: Position;
  acceleration: Position;
  speed: number;
  heart_rate: number;
  sprint_distance: number;
  total_distance: number;
  is_sprinting: boolean;
  skeleton?: Array<{ joint: string; x: number; y: number; z: number }>;
}

export interface BallNode {
  position: Position;
  velocity: Position;
  speed: number;
  angular_velocity: { x: number; y: number; z: number };
  holder_id: string | null;
  subticks?: Array<{ x: number; y: number; z: number; spin: { x: number; y: number; z: number } }>;
}

export interface TeamCompactness {
  home: number;
  away: number;
}

export interface PlayerKinematics {
  speed_kmh: number;
  acceleration: number;
  heading: number;
  sprint_distance: number;
  total_distance: number;
  is_sprinting: boolean;
  heart_rate: number;
}

export interface PassingLane {
  from: string;
  to: string;
  to_jersey: number;
  open: boolean;
  distance: number;
  blocked_by: string | null;
  start: { x: number; y: number };
  end: { x: number; y: number };
}

export interface CounterPressAlert {
  team: "home" | "away";
  message: string;
  compactness_area: number;
}

export interface OutOfPositionWarning {
  player_id: string;
  jersey_number: number;
  role: string;
  team: "home" | "away";
  deviation_meters: number;
}

export interface TelemetryFrame {
  timestamp: string;
  match_time: number;
  match_clock: string;
  playback_state: string;
  playback_speed: number;
  frame_count: number;
  players: PlayerNode[];
  ball: BallNode;
  analytics: {
    compactness: TeamCompactness;
    kinematics: Record<string, PlayerKinematics>;
    passing_lanes: PassingLane[];
  };
  marl: {
    predictions: Record<string, { suggested_action: number; confidence: number; predicted_position: { x: number; y: number } }>;
    counter_press_alerts: CounterPressAlert[];
    out_of_position_warnings: OutOfPositionWarning[];
    xg_prediction: number;
  };
  observability: {
    e2e_latency_ms: { avg: number; p50: number; p95: number; p99: number };
    throughput_fps: number;
    data_drift_score: number;
  };
}

interface TelemetryState {
  latestFrame: TelemetryFrame | null;
  wsConnected: boolean;
  selectedPlayerId: string | null;
  tacticalOverlay: "heatmap" | "zones" | "none";
}

type TelemetryAction =
  | { type: "SET_FRAME"; payload: TelemetryFrame }
  | { type: "SET_WS_CONNECTED"; payload: boolean }
  | { type: "SET_SELECTED_PLAYER"; payload: string | null }
  | { type: "SET_TACTICAL_OVERLAY"; payload: "heatmap" | "zones" | "none" };

// ---------------------------------------------------------------------------
// Reducer & Context Setup
// ---------------------------------------------------------------------------
const initialState: TelemetryState = {
  latestFrame: null,
  wsConnected: false,
  selectedPlayerId: null,
  tacticalOverlay: "none",
};

function telemetryReducer(state: TelemetryState, action: TelemetryAction): TelemetryState {
  switch (action.type) {
    case "SET_FRAME":
      return {
        ...state,
        latestFrame: action.payload,
      };
    case "SET_WS_CONNECTED":
      return {
        ...state,
        wsConnected: action.payload,
      };
    case "SET_SELECTED_PLAYER":
      return {
        ...state,
        selectedPlayerId: action.payload,
      };
    case "SET_TACTICAL_OVERLAY":
      return {
        ...state,
        tacticalOverlay: action.payload,
      };
    default:
      return state;
  }
}

const TelemetryStoreContext = createContext<{
  state: TelemetryState;
  dispatch: React.Dispatch<TelemetryAction>;
} | null>(null);

export function TelemetryStoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(telemetryReducer, initialState);

  return (
    <TelemetryStoreContext.Provider value={{ state, dispatch }}>
      {children}
    </TelemetryStoreContext.Provider>
  );
}

export function useTelemetryStore() {
  const context = useContext(TelemetryStoreContext);
  if (!context) {
    throw new Error("useTelemetryStore must be used within a TelemetryStoreProvider");
  }
  return context;
}
