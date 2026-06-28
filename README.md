# AuraPitch 2026 — Distributed Multi-Agent Tactical Synthesizer

AuraPitch 2026 is a production-grade, highly performant real-time sports analytics platform and 3D digital twin simulator designed for the FIFA World Cup 2026. The system simulates high-frequency match telemetry, statefully aggregates player kinetics and passing lane options over sliding time windows, runs multi-agent reinforcement learning (MARL) suggestions, and renders live visualizations on an interactive 3D WebGL pitch along with enterprise-grade system observability.

---

## System Architecture

```mermaid
graph TD
    A[Telemetry Producer] -- "50Hz Skeletal / 500Hz Ball (WebSockets)" --> B[Streaming Analytics (FastAPI)]
    C[MARL Inference Engine] -- "gRPC / Protobuf (Port 50051)" --> B
    B -- "Processed State + MLOps (WebSockets)" --> D[Web Visualizer (Next.js + R3F)]
```

### 1. Telemetry Producer (`apps/telemetry-producer`)
- **Physics Simulator**: Generates real-time 50Hz coordinates for 22 players and 500Hz spin/trajectory ticks for the match ball.
- **Skeletal Simulation**: Applies walking/running gait cycles (sinusoidal joint angles) across a 29-point body skeleton relative to each player node's heading.
- **Biometric Mock**: Tracks player heart rates, sprint count, and cumulative physical metrics.

### 2. Streaming Analytics (`apps/streaming-analytics`)
- **FastAPI Core**: Serves as the centralized processing hub connecting producers, MARL agents, and web clients.
- **Stateful Engine**: Performs rolling calculations over a sliding 3-second buffer:
  - *Team Compactness*: Monotone-chain convex hull area (m²) occupied by outfield players.
  - *Kinematics*: Live velocity vectors, acceleration, heading angles, and cumulative sprint distances.
  - *Passing Lanes*: Real-time ray-casting checks between the ball holder and teammates, calculating line-of-sight obstructions against defensive radii (2.0m) of opponent nodes.
- **Robustness Fallback**: Dynamically spins up an internal telemetry generator loop if the external producer disconnects, guaranteeing continuous WebGL simulation.

### 3. MARL Inference Engine (`apps/marl-inference-engine`)
- **gRPC Service**: Exposes `PredictTacticalMove` and `StreamPredictions` endpoints over port 50051.
- **PyTorch Policy**: Evaluates spatial states using a pre-saved neural network checkpoint (`marl_policy.pt`).
- **Tactical Decisions**: Suggests optimal player behaviors (PASS, RUN, TACKLE, SHOT, IDLE) with model confidence, and projects target landing coordinates.

### 4. Web Visualizer (`apps/web-visualizer`)
- **3D Canvas**: Renders the digital twin using React Three Fiber, custom shaders, and Drei helper primitives. Includes OrbitControls for rotation, panning, and zoom.
- **Real-Time Tables**: Displays a grid of player biometrics, highlighting sprint states and heart rate spikes.
- **MARL Feed**: Provides tactical overrides, counter-pressing notifications, and expected goals (xG) metrics.
- **MLOps Monitor**: Visualizes end-to-end latency percentiles (p50/p95/p99) and spatial Kolmogorov-Smirnov data drift.

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Node.js v18+ & npm
- Git

### 1. Start the MARL Inference Engine
```bash
cd apps/marl-inference-engine
pip install -r requirements.txt
python src/server.py
```

### 2. Start the Streaming Analytics Backend
```bash
cd apps/streaming-analytics
pip install -r requirements.txt
uvicorn src.main:app --port 8000 --reload
```

### 3. Start the Next.js Frontend
```bash
cd apps/web-visualizer
npm install
npm run dev
```

### 4. Start the Telemetry Producer
```bash
cd apps/telemetry-producer
pip install -r requirements.txt
python src/producer.py
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Docker Compose Deployment

To build and run all services in a single command using Docker:

```bash
# Build all service containers
make build

# Start services in the background
make up

# Stop all containers
make down
```

---

## WebSocket & REST Protocol Specification

### REST Endpoints
- `GET /api/health`: Returns service health status, client count, and connected modules.
- `POST /api/match/control`: Receives play, pause, and speed settings.
  ```json
  {
    "state": "PLAYING",
    "speed": 2.0
  }
  ```

### WebSocket Ingestion (`/ws/telemetry`)
Inbound payload from the simulation producer containing player coordinates, 29-joint skeleton structures, and high-frequency ball sub-ticks.

### WebSocket Broadcast (`/ws/visualizer`)
Outbound unified broadcast frame sent to Next.js clients:
- Player spatial positions and skeletal nodes.
- Ball positions and spin velocity.
- Convex hull area indices.
- Obstructed/Open passing lines.
- Expected goals (xG) index.
- System throughput, data drift scores, and E2E latency percentiles.
