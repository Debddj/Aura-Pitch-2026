"""
Stateful Stream Analytics Layer (The Processing Engine)
=======================================================
Ingests raw telemetry frames and computes analytical metrics over a sliding
3-second window buffer:
  - Team Compactness (convex hull area of each defensive unit)
  - Player Kinematics (velocity, acceleration, sprint paths, directional heading)
  - Passing Lane Availability (ray-cast obstruction detection)

All computations use NumPy only (no SciPy dependency) for maximum portability.
"""

import math
from collections import deque
from typing import Optional

import numpy as np


# -----------------------------------------------------------------------
# Convex hull area via Graham scan + Shoelace (pure NumPy)
# -----------------------------------------------------------------------

def _convex_hull_area_2d(points: np.ndarray) -> float:
    """
    Compute the area of the convex hull of a set of 2D points.
    Uses a simplified monotone-chain algorithm + shoelace formula.
    Returns 0.0 if fewer than 3 points.
    """
    if len(points) < 3:
        return 0.0

    # Sort by x, then by y
    pts = points[np.lexsort((points[:, 1], points[:, 0]))]

    # Build upper and lower hulls
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return 0.0

    # Shoelace formula
    hull_arr = np.array(hull)
    x = hull_arr[:, 0]
    y = hull_arr[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


# -----------------------------------------------------------------------
# Passing lane ray-cast obstruction check
# -----------------------------------------------------------------------

def _point_to_segment_distance(px, py, ax, ay, bx, by) -> float:
    """Shortest distance from point (px, py) to segment (ax, ay)-(bx, by)."""
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-8:
        return math.sqrt((px - ax) ** 2 + (py - ay) ** 2)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)


# -----------------------------------------------------------------------
# StreamAnalytics
# -----------------------------------------------------------------------

class StreamAnalytics:
    """
    Maintains a sliding window of telemetry frames and computes analytics.
    """

    WINDOW_SECONDS = 3.0
    DEFENSIVE_RADIUS = 2.0  # metres — opponent interception radius for passing lanes

    def __init__(self, fps: int = 20):
        self.fps = fps
        max_frames = int(self.WINDOW_SECONDS * fps)
        self._buffer: deque[dict] = deque(maxlen=max_frames)
        self.timestep = 0
        self.opponent_history = []
        self.detected_fingerprint = "CALIBRATING..."

    def ingest(self, frame: dict):
        """Add a telemetry frame to the sliding buffer."""
        self._buffer.append(frame)

    def update_fingerprint(self, frame: dict):
        self.timestep += 1
        players = frame.get("players", [])
        away_players = [p for p in players if p["team"] == "away"]
        if not away_players:
            return

        pts = np.array([[p["position"]["x"], p["position"]["y"]] for p in away_players])
        speeds = [p["speed"] for p in away_players]
        self.opponent_history.append((pts, speeds))

        # Once we have 60 frames (3s at 20fps), we classify the tactical fingerprint
        if len(self.opponent_history) >= 60:
            def_outfield = [p for p in away_players if p.get("role") != "GK"]
            if len(def_outfield) >= 3:
                def_pts = np.array([[p["position"]["x"], p["position"]["y"]] for p in def_outfield])
                area = _convex_hull_area_2d(def_pts)
            else:
                area = 500.0

            pressing = "HIGH_PRESS" if area < 400.0 else "LOW_BLOCK"

            defenders = [p for p in away_players if "CB" in p["role"] or p["role"] in ["LB", "RB"]]
            if defenders:
                mean_x = np.mean([p["position"]["x"] for p in defenders])
                line_depth = "DEEP_LINE" if mean_x > 28.0 else "HIGH_LINE"
            else:
                line_depth = "DEEP_LINE"

            avg_speed = np.mean([np.mean(h[1]) for h in self.opponent_history[-60:]])
            transition = "FAST_BREAK" if avg_speed > 3.0 else "SLOW_BUILD"

            self.detected_fingerprint = f"{pressing} | {line_depth} | {transition}"

    def compute(self, frame: dict) -> dict:
        """
        Compute all analytics for the current frame.
        Returns a dict that will be merged into the WebSocket broadcast.
        """
        self.update_fingerprint(frame)
        players = frame.get("players", [])
        ball = frame.get("ball", {})

        home_players = [p for p in players if p["team"] == "home"]
        away_players = [p for p in players if p["team"] == "away"]

        compactness = self._compute_compactness(home_players, away_players)
        kinematics = self._compute_kinematics(players)
        passing_lanes = self._compute_passing_lanes(players, ball)

        return {
            "team_compactness": compactness,
            "kinematics": kinematics,
            "passing_lanes": passing_lanes,
            "opponent_fingerprint": self.detected_fingerprint,
            "timestep": self.timestep
        }

    # ------------------------------------------------------------------
    # Team Compactness (convex hull area of outfield players)
    # ------------------------------------------------------------------

    def _compute_compactness(self, home: list, away: list) -> dict:
        def hull_area(team_players):
            outfield = [p for p in team_players if p.get("role") != "GK"]
            if len(outfield) < 3:
                return 0.0
            pts = np.array([[p["position"]["x"], p["position"]["y"]] for p in outfield])
            return _convex_hull_area_2d(pts)

        return {
            "home": round(hull_area(home), 1),
            "away": round(hull_area(away), 1),
        }

    # ------------------------------------------------------------------
    # Player Kinematics
    # ------------------------------------------------------------------

    def _compute_kinematics(self, players: list) -> dict:
        result = {}
        for p in players:
            vx = p["velocity"]["x"]
            vy = p["velocity"]["y"]
            speed = p["speed"]
            heading = math.degrees(math.atan2(vy, vx)) % 360

            ax = p["acceleration"]["x"]
            ay = p["acceleration"]["y"]
            accel_mag = math.sqrt(ax**2 + ay**2)

            result[p["player_id"]] = {
                "speed_kmh": round(speed * 3.6, 1),  # m/s to km/h
                "acceleration": round(accel_mag, 2),
                "heading": round(heading, 1),
                "sprint_distance": p["sprint_distance"],
                "total_distance": p["total_distance"],
                "is_sprinting": p["is_sprinting"],
                "heart_rate": p["heart_rate"],
            }
        return result

    # ------------------------------------------------------------------
    # Passing Lane Availability
    # ------------------------------------------------------------------

    def _compute_passing_lanes(self, players: list, ball: dict) -> list:
        holder_id = ball.get("holder_id")
        if not holder_id:
            return []

        holder = next((p for p in players if p["player_id"] == holder_id), None)
        if not holder:
            return []

        holder_team = holder["team"]
        hx = holder["position"]["x"]
        hy = holder["position"]["y"]

        teammates = [p for p in players if p["team"] == holder_team and p["player_id"] != holder_id]
        opponents = [p for p in players if p["team"] != holder_team]

        lanes = []
        for tm in teammates:
            tx = tm["position"]["x"]
            ty = tm["position"]["y"]
            lane_dist = math.sqrt((tx - hx) ** 2 + (ty - hy) ** 2)

            # Check obstruction by each opponent
            blocked_by: Optional[str] = None
            is_open = True
            for opp in opponents:
                ox = opp["position"]["x"]
                oy = opp["position"]["y"]
                dist = _point_to_segment_distance(ox, oy, hx, hy, tx, ty)
                if dist < self.DEFENSIVE_RADIUS:
                    is_open = False
                    blocked_by = opp["player_id"]
                    break

            lanes.append({
                "from": holder_id,
                "to": tm["player_id"],
                "to_jersey": tm["jersey_number"],
                "open": is_open,
                "distance": round(lane_dist, 1),
                "blocked_by": blocked_by,
                "start": {"x": round(hx, 2), "y": round(hy, 2)},
                "end": {"x": round(tx, 2), "y": round(ty, 2)},
            })

        return lanes
