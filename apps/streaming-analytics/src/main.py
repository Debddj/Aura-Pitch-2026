import asyncio
import json
import math
import os
import sys
import time
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure src is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telemetry_engine import TelemetryEngine, PlaybackState
from stream_analytics import StreamAnalytics
from marl_inference import MARLClient
from observability import ObservabilitySuite

app = FastAPI(title="AuraPitch Streaming Analytics & Processing Backend")

# Enable CORS for the web visualizer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global State
# ---------------------------------------------------------------------------
# Visualizer UI clients
visualizer_clients: Set[WebSocket] = set()
# Producer WebSocket connection
producer_ws: WebSocket = None

# Internal engine used as:
# 1. Playback state coordinator (stores current state, speed)
# 2. Fallback simulation engine if external producer is offline
telemetry_engine = TelemetryEngine()
analytics_engine = StreamAnalytics()
marl_client = MARLClient(host=os.getenv("MARL_HOST", "localhost"), port=50051)
observability_suite = ObservabilitySuite()

# Track when the last external frame was received
last_external_frame_time = 0.0

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class PlaybackControlSchema(BaseModel):
    state: str
    speed: float = 1.0

class SetPieceSchema(BaseModel):
    type: str  # CORNER_KICK or FREE_KICK

# Set-piece simulation state
active_set_piece = False
set_piece_type = ""
set_piece_expiry_time = 0.0

# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "producer_connected": producer_ws is not None,
        "marl_engine_connected": marl_client._connected,
        "active_clients": len(visualizer_clients),
        "playback_state": telemetry_engine.playback_state.value,
        "playback_speed": telemetry_engine.playback_speed
    }

@app.post("/api/match/control")
async def match_control(control: PlaybackControlSchema):
    """Updates playback state and propagates commands to the external producer."""
    state_str = control.state.upper()
    telemetry_engine.set_playback_state(state_str, control.speed)
    
    # Propagate to external producer if connected
    if producer_ws:
        try:
            await producer_ws.send_json({
                "type": "CONTROL",
                "state": state_str,
                "speed": control.speed
            })
        except Exception as e:
            print(f"Failed to forward control to producer: {e}")
            
    return {
        "status": "success",
        "state": telemetry_engine.playback_state.value,
        "speed": telemetry_engine.playback_speed
    }

@app.post("/api/match/setpiece")
async def match_setpiece(setpiece: SetPieceSchema):
    """Triggers a Corner or Free Kick set piece simulation phase."""
    global active_set_piece, set_piece_type, set_piece_expiry_time
    active_set_piece = True
    set_piece_type = setpiece.type.upper()
    set_piece_expiry_time = time.time() + 5.0  # Active for 5 seconds
    
    # Propagate to external producer if connected
    if producer_ws:
        try:
            await producer_ws.send_json({
                "type": "SET_PIECE",
                "set_piece_type": set_piece_type
            })
        except Exception as e:
            print(f"Failed to forward set-piece to producer: {e}")
            
    return {
        "status": "success",
        "type": set_piece_type,
        "expires_in": 5.0
    }

# ---------------------------------------------------------------------------
# Processing and Broadcast Pipeline
# ---------------------------------------------------------------------------
async def process_and_broadcast_frame(raw_frame: dict):
    """
    Ingests raw telemetry frame, performs stateful streaming analytics,
    runs MARL inference predictions (gRPC or local fallback), updates MLOps,
    and broadcasts the combined state to all Next.js web clients.
    """
    global active_set_piece, set_piece_expiry_time
    # 1. Register frame in observability suite
    timestamp = raw_frame.get("timestamp", "")
    if not timestamp:
        # Create timestamp if missing
        from datetime import datetime
        timestamp = datetime.utcnow().isoformat()
        raw_frame["timestamp"] = timestamp
    
    observability_suite.record_frame(timestamp)

    # 2. Stateful stream analytics (sliding 3s window)
    analytics_engine.ingest(raw_frame)
    analytics = analytics_engine.compute(raw_frame)

    # 3. MARL Inference Query
    # Run MARL for all outfield players to provide tactical recommendations
    players = raw_frame.get("players", [])
    ball = raw_frame.get("ball", {})
    
    marl_predictions = {}
    out_of_position_warnings = []
    
    # Manage set-piece simulation timeout
    if active_set_piece and time.time() > set_piece_expiry_time:
        active_set_piece = False
        
    opponent_fingerprint = analytics.get("opponent_fingerprint", "CALIBRATING...")
    timestep = analytics.get("timestep", 0)
    
    for p in players:
        p_id = p["player_id"]
        # Basic team formation vectors as list of floats (using player x, y as context)
        # In a real setup, we pass neighbor locations. We feed current player coords and ball coord
        team_formation = [p["position"]["x"], p["position"]["y"], ball.get("position", {}).get("x", 0.0), ball.get("position", {}).get("y", 0.0), 0.0, 0.0]
        
        pred = marl_client.predict(
            player_id=p_id,
            x=p["position"]["x"],
            y=p["position"]["y"],
            velocity=p["speed"],
            heart_rate=p["heart_rate"],
            team_formation=team_formation,
            opponent_fingerprint=opponent_fingerprint,
            is_set_piece=active_set_piece,
            timestep=timestep
        )
        marl_predictions[p_id] = pred
        
        # Heuristic: Out of position warning if suggested action is idle but speed is low and far from base formation
        # The base positions are stored in telemetry_engine (roles & base coords)
        # We flag players whose distance to their theoretical base position is excessive (>20m)
        bx = p.get("base_x", 0.0) # wait, base_x isn't serialized by default in PlayerState.to_dict
        # We can approximate based on role
        if p["role"] != "GK":
            # approximate distance
            cx = p["position"]["x"]
            cy = p["position"]["y"]
            # base coords logic based on team side
            side_multiplier = -1 if p["team"] == "home" else 1
            # Simple role mapping
            role_base_x = 0.0
            if "CB" in p["role"] or p["role"] in ["LB", "RB"]:
                role_base_x = -35.0 * side_multiplier
            elif "CM" in p["role"] or p["role"] in ["LM", "RM"]:
                role_base_x = -15.0 * side_multiplier
            elif p["role"] in ["ST", "LW", "RW", "ST1", "ST2"]:
                role_base_x = 15.0 * side_multiplier
                
            dist_to_base = abs(cx - role_base_x)
            if dist_to_base > 28.0:
                out_of_position_warnings.append({
                    "player_id": p_id,
                    "jersey_number": p["jersey_number"],
                    "role": p["role"],
                    "team": p["team"],
                    "deviation_meters": round(dist_to_base, 1)
                })

    # Tactical highlights: compactness-based counter-pressing alert
    # Trigger alert if home or away compactness drops below threshold (highly spread thin)
    compactness = analytics["team_compactness"]
    counter_press_alerts = []
    if compactness["home"] > 800.0:
        counter_press_alerts.append({
            "team": "home",
            "message": "High dispersion detected. Initiate counter-pressing transition.",
            "compactness_area": compactness["home"]
        })
    if compactness["away"] > 800.0:
        counter_press_alerts.append({
            "team": "away",
            "message": "Defensive structure compromise. Tighten press lanes.",
            "compactness_area": compactness["away"]
        })

    # Expected Goals (xG) calculation:
    # Based on ball holder proximity to opponent goal
    # Home attacks away goal (+52.5, 0), Away attacks home goal (-52.5, 0)
    xg_prediction = 0.01
    holder_id = ball.get("holder_id")
    if holder_id:
        holder_p = next((p for p in players if p["player_id"] == holder_id), None)
        if holder_p:
            hx = holder_p["position"]["x"]
            hy = holder_p["position"]["y"]
            target_goal_x = 52.5 if holder_p["team"] == "home" else -52.5
            dist_to_goal = math.sqrt((target_goal_x - hx)**2 + hy**2)
            # Standard logistic decay
            xg_prediction = 1.0 / (1.0 + math.exp((dist_to_goal - 12.0) / 6.0))
            # Caps and scale
            xg_prediction = min(0.95, max(0.01, xg_prediction))

    # 4. Compile MLOps Metrics
    mops_metrics = observability_suite.get_metrics(players)

    # 5. Build consolidated broadcast payload
    payload = {
        "timestamp": raw_frame.get("timestamp"),
        "match_time": raw_frame.get("match_time"),
        "match_clock": raw_frame.get("match_clock"),
        "playback_state": raw_frame.get("playback_state"),
        "playback_speed": raw_frame.get("playback_speed"),
        "frame_count": raw_frame.get("frame_count"),
        
        # Telemetry nodes
        "players": players,
        "ball": ball,
        
        # Analytics calculations
        "analytics": {
            "compactness": compactness,
            "kinematics": analytics["kinematics"],
            "passing_lanes": analytics["passing_lanes"],
        },
        
        # MARL Intelligence Suggestions
        "marl": {
            "predictions": marl_predictions,
            "counter_press_alerts": counter_press_alerts,
            "out_of_position_warnings": out_of_position_warnings,
            "xg_prediction": round(xg_prediction, 2),
            "opponent_fingerprint": opponent_fingerprint,
            "is_set_piece": active_set_piece,
            "set_piece_type": set_piece_type if active_set_piece else ""
        },
        
        # MLOps Monitoring
        "observability": mops_metrics
    }

    # 6. Broadcast to all active UI clients
    if visualizer_clients:
        dead_clients = set()
        message_str = json.dumps(payload)
        for client in visualizer_clients:
            try:
                await client.send_text(message_str)
            except Exception:
                dead_clients.add(client)
        
        # Clean up disconnected visualizers
        for client in dead_clients:
            visualizer_clients.remove(client)

# ---------------------------------------------------------------------------
# WebSocket Handlers
# ---------------------------------------------------------------------------
@app.websocket("/ws/telemetry")
async def telemetry_input_ws(websocket: WebSocket):
    """
    Accepts real-time raw telemetry streams from the telemetry-producer.
    """
    global producer_ws, last_external_frame_time
    await websocket.accept()
    producer_ws = websocket
    print("Telemetry producer connected.")
    
    # Sync current playback state to producer
    try:
        await websocket.send_json({
            "type": "CONTROL",
            "state": telemetry_engine.playback_state.value,
            "speed": telemetry_engine.playback_speed
        })
    except Exception as e:
        print(f"Failed to sync playback state to producer: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            frame = json.loads(data)
            last_external_frame_time = time.time()
            
            # Process and broadcast the received telemetry frame
            await process_and_broadcast_frame(frame)
    except WebSocketDisconnect:
        print("Telemetry producer disconnected.")
    except Exception as e:
        print(f"Error in telemetry input socket: {e}")
    finally:
        producer_ws = None

@app.websocket("/ws/visualizer")
async def visualizer_output_ws(websocket: WebSocket):
    """
    Broadcasts stateful analytics, telemetry, and MLOps metrics to Next.js clients.
    """
    await websocket.accept()
    visualizer_clients.add(websocket)
    print(f"Web visualizer client connected. Total clients: {len(visualizer_clients)}")
    
    try:
        while True:
            # Keep connection alive, listen for any UI control frames
            data = await websocket.receive_text()
            # If visualizer sends playback commands via socket
            try:
                msg = json.loads(data)
                if msg.get("type") == "CONTROL":
                    state_str = msg.get("state", "PLAYING").upper()
                    speed = msg.get("speed", 1.0)
                    telemetry_engine.set_playback_state(state_str, speed)
                    if producer_ws:
                        await producer_ws.send_json({
                            "type": "CONTROL",
                            "state": state_str,
                            "speed": speed
                        })
            except Exception:
                pass
    except WebSocketDisconnect:
        print("Web visualizer client disconnected.")
    finally:
        visualizer_clients.discard(websocket)

# ---------------------------------------------------------------------------
# Fallback Background Task
# ---------------------------------------------------------------------------
async def fallback_simulator_loop():
    """
    Generates internal telemetry states if no external telemetry-producer is
    connected, ensuring Next.js dashboard remains fully operational.
    """
    print("Fallback simulation loop active.")
    dt = 1.0 / telemetry_engine.EMIT_HZ
    
    while True:
        try:
            # Check if external producer has timed out
            now = time.time()
            if producer_ws is None or (now - last_external_frame_time > 2.0):
                if telemetry_engine.playback_state != PlaybackState.PAUSED:
                    # Tick the physics engine
                    telemetry_engine.tick(dt)
                    frame = telemetry_engine.snapshot()
                    # Feed frame into stream pipeline
                    await process_and_broadcast_frame(frame)
            
            # Control tick frequency
            # Adjust sleep duration based on playback speed (1.0 = 50ms, 2.0 = 25ms)
            sleep_time = dt
            if telemetry_engine.playback_state == PlaybackState.FAST_FORWARD:
                sleep_time = dt / max(0.5, telemetry_engine.playback_speed)
                
            await asyncio.sleep(sleep_time)
        except Exception as e:
            print(f"Error in fallback simulator: {e}")
            await asyncio.sleep(1.0)

@app.on_event("startup")
async def startup_event():
    # Start the fallback simulation loop in background
    asyncio.create_task(fallback_simulator_loop())
