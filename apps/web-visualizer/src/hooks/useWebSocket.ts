"use client";

import { useEffect, useRef, useCallback } from "react";
import { useTelemetryStore } from "./useTelemetryStore";

export function useWebSocket(url: string = "ws://localhost:8000/ws/visualizer") {
  const { state, dispatch } = useTelemetryStore();
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (socketRef.current) return;

    console.log(`Connecting to visualizer WebSocket: ${url}`);
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log("Visualizer WebSocket connected.");
      dispatch({ type: "SET_WS_CONNECTED", payload: true });
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const frame = JSON.parse(event.data);
        dispatch({ type: "SET_FRAME", payload: frame });
      } catch (err) {
        console.error("Failed to parse visualizer frame:", err);
      }
    };

    ws.onclose = (event) => {
      console.log(`Visualizer WebSocket closed. Code: ${event.code}`);
      dispatch({ type: "SET_WS_CONNECTED", payload: false });
      socketRef.current = null;

      // Exponential backoff reconnect
      const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
      reconnectAttemptsRef.current += 1;
      
      console.log(`Scheduling reconnect attempt ${reconnectAttemptsRef.current} in ${delay}ms`);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, delay);
    };

    ws.onerror = (error) => {
      console.error("Visualizer WebSocket error occurred:", error);
    };

    socketRef.current = ws;
  }, [url, dispatch]);

  const sendControl = useCallback((playbackState: string, speed: number) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "CONTROL",
          state: playbackState,
          speed: speed,
        })
      );
    } else {
      console.warn("WebSocket not connected. Sending control via REST fallback...");
      // Fallback REST request
      fetch("http://localhost:8000/api/match/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: playbackState, speed }),
      }).catch((err) => console.error("REST playback control fallback failed:", err));
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  return {
    wsConnected: state.wsConnected,
    sendControl,
  };
}
