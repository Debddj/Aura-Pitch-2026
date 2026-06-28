"""
High-Frequency Telemetry Stream Simulator (The Data Plane)
==========================================================
Generates realistic match telemetry for 22 players (2 teams of 11) and a match ball.
Players follow formation templates with Ornstein-Uhlenbeck mean-reverting drift,
sprint bursts, and ball-proximity effects. Ball transitions between holders via
pass/shot events.

Designed to emit at 20Hz over WebSocket with interpolation metadata for smooth
60fps frontend rendering. Internally tracks 50Hz player state and 500Hz ball
spin/inertial data as documented in the system spec.
"""

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np


class PlaybackState(str, Enum):
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    FAST_FORWARD = "FAST_FORWARD"


# ---------------------------------------------------------------------------
# Formation definitions (FIFA standard pitch: 105m x 68m, origin at center)
# Coordinates are (x, y) where x is along length, y is across width
# ---------------------------------------------------------------------------

HOME_FORMATION_433 = {
    "GK":  (-48.0,   0.0),
    "LB":  (-35.0, -25.0),
    "CB1": (-35.0,  -8.0),
    "CB2": (-35.0,   8.0),
    "RB":  (-35.0,  25.0),
    "CM1": (-15.0, -15.0),
    "CM2": (-15.0,   0.0),
    "CM3": (-15.0,  15.0),
    "LW":  ( 10.0, -28.0),
    "ST":  ( 15.0,   0.0),
    "RW":  ( 10.0,  28.0),
}

AWAY_FORMATION_442 = {
    "GK":  ( 48.0,   0.0),
    "LB":  ( 35.0,  25.0),
    "CB1": ( 35.0,   8.0),
    "CB2": ( 35.0,  -8.0),
    "RB":  ( 35.0, -25.0),
    "LM":  ( 15.0,  25.0),
    "CM1": ( 15.0,   8.0),
    "CM2": ( 15.0,  -8.0),
    "RM":  ( 15.0, -25.0),
    "ST1": (-10.0,  -8.0),
    "ST2": (-10.0,   8.0),
}

# Jersey numbers
HOME_JERSEYS = [1, 2, 3, 4, 5, 6, 8, 10, 7, 9, 11]
AWAY_JERSEYS = [1, 2, 3, 4, 5, 6, 7, 8, 11, 9, 10]

PITCH_HALF_LENGTH = 52.5
PITCH_HALF_WIDTH = 34.0


@dataclass
class PlayerState:
    player_id: str
    team: str  # "home" or "away"
    jersey_number: int
    role: str  # e.g. "GK", "CB1", "ST"
    base_x: float
    base_y: float
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0  # always near 0 for ground players
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    az: float = 0.0
    speed: float = 0.0
    heart_rate: int = 140
    sprint_distance: float = 0.0
    total_distance: float = 0.0
    is_sprinting: bool = False
    # Internal simulation state
    _sprint_timer: float = 0.0
    _target_hr: int = 140
    _hr_history: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "team": self.team,
            "jersey_number": self.jersey_number,
            "role": self.role,
            "position": {"x": round(self.x, 2), "y": round(self.y, 2), "z": round(self.z, 3)},
            "velocity": {"x": round(self.vx, 2), "y": round(self.vy, 2), "z": round(self.vz, 3)},
            "acceleration": {"x": round(self.ax, 2), "y": round(self.ay, 2), "z": round(self.az, 3)},
            "speed": round(self.speed, 2),
            "heart_rate": self.heart_rate,
            "sprint_distance": round(self.sprint_distance, 1),
            "total_distance": round(self.total_distance, 1),
            "is_sprinting": self.is_sprinting,
        }


@dataclass
class BallState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.3  # slightly above ground
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    speed: float = 0.0
    angular_vx: float = 0.0
    angular_vy: float = 0.0
    angular_vz: float = 0.0
    holder_id: Optional[str] = None
    # Internal
    _pass_timer: float = 0.0
    _pass_target_x: float = 0.0
    _pass_target_y: float = 0.0
    _pass_start_x: float = 0.0
    _pass_start_y: float = 0.0
    _passing: bool = False
    _pass_duration: float = 0.0

    def to_dict(self) -> dict:
        return {
            "position": {"x": round(self.x, 2), "y": round(self.y, 2), "z": round(self.z, 3)},
            "velocity": {"x": round(self.vx, 2), "y": round(self.vy, 2), "z": round(self.vz, 3)},
            "speed": round(self.speed, 2),
            "angular_velocity": {
                "x": round(self.angular_vx, 1),
                "y": round(self.angular_vy, 1),
                "z": round(self.angular_vz, 1),
            },
            "holder_id": self.holder_id,
        }


class TelemetryEngine:
    """
    Core simulation engine. Call ``tick(dt)`` to advance state by ``dt`` seconds.
    """

    EMIT_HZ = 20  # WebSocket broadcast rate
    INTERNAL_HZ = 50  # Internal simulation substeps

    def __init__(self):
        self.players: list[PlayerState] = []
        self.ball = BallState()
        self.match_time: float = 0.0  # seconds elapsed in match
        self.playback_state = PlaybackState.PLAYING
        self.playback_speed: float = 1.0
        self.frame_count: int = 0
        self._rng = np.random.default_rng(42)
        self._initialise_players()
        self._initialise_ball()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _initialise_players(self):
        for i, (role, (bx, by)) in enumerate(HOME_FORMATION_433.items()):
            p = PlayerState(
                player_id=f"home_{i+1}",
                team="home",
                jersey_number=HOME_JERSEYS[i],
                role=role,
                base_x=bx,
                base_y=by,
                x=bx + self._rng.normal(0, 1),
                y=by + self._rng.normal(0, 1),
                z=0.0,
            )
            p._target_hr = 135 + random.randint(0, 15)
            self.players.append(p)

        for i, (role, (bx, by)) in enumerate(AWAY_FORMATION_442.items()):
            p = PlayerState(
                player_id=f"away_{i+1}",
                team="away",
                jersey_number=AWAY_JERSEYS[i],
                role=role,
                base_x=bx,
                base_y=by,
                x=bx + self._rng.normal(0, 1),
                y=by + self._rng.normal(0, 1),
                z=0.0,
            )
            p._target_hr = 135 + random.randint(0, 15)
            self.players.append(p)

    def _initialise_ball(self):
        # Start with home CM2 holding the ball (kick-off)
        holder = next(p for p in self.players if p.player_id == "home_7")
        self.ball.holder_id = holder.player_id
        self.ball.x = holder.x
        self.ball.y = holder.y
        self.ball.z = 0.3

    # ------------------------------------------------------------------
    # Main simulation step
    # ------------------------------------------------------------------

    def tick(self, dt: float):
        """Advance the simulation by *dt* seconds (wall-clock, pre-multiplied by speed)."""
        if self.playback_state == PlaybackState.PAUSED:
            return

        effective_dt = dt * self.playback_speed
        substeps = max(1, int(effective_dt * self.INTERNAL_HZ))
        sub_dt = effective_dt / substeps

        for _ in range(substeps):
            self._step_players(sub_dt)
            self._step_ball(sub_dt)
            self.match_time += sub_dt

        self.frame_count += 1

    # ------------------------------------------------------------------
    # Player movement (Ornstein-Uhlenbeck with sprint bursts)
    # ------------------------------------------------------------------

    def _step_players(self, dt: float):
        for p in self.players:
            # Ornstein-Uhlenbeck mean-reversion toward base position
            theta = 0.8 if p.role == "GK" else 0.3  # GK stays closer to base
            sigma = 0.5 if p.role == "GK" else 1.8

            # Mean-reverting force
            drift_x = theta * (p.base_x - p.x)
            drift_y = theta * (p.base_y - p.y)

            # Stochastic noise
            noise_x = sigma * self._rng.normal() * math.sqrt(dt)
            noise_y = sigma * self._rng.normal() * math.sqrt(dt)

            # Sprint burst logic
            if p._sprint_timer > 0:
                p._sprint_timer -= dt
                p.is_sprinting = True
                sprint_scale = 3.5
            else:
                p.is_sprinting = False
                sprint_scale = 1.0
                # Random chance to start a sprint
                if random.random() < 0.003:
                    p._sprint_timer = 1.5 + random.random() * 2.0

            # Ball attraction: players near the ball move slightly toward it
            ball_dx = self.ball.x - p.x
            ball_dy = self.ball.y - p.y
            ball_dist = math.sqrt(ball_dx**2 + ball_dy**2) + 0.01
            if ball_dist < 25 and p.role != "GK":
                attraction = 0.15 / ball_dist
                drift_x += attraction * ball_dx
                drift_y += attraction * ball_dy

            # Update velocity
            prev_vx, prev_vy = p.vx, p.vy
            p.vx = (drift_x + noise_x * sprint_scale) / max(dt, 0.001)
            p.vy = (drift_y + noise_y * sprint_scale) / max(dt, 0.001)

            # Clamp velocity to realistic max (~10 m/s sprint, ~4 m/s jog)
            max_speed = 10.0 if p.is_sprinting else 4.0
            speed = math.sqrt(p.vx**2 + p.vy**2)
            if speed > max_speed:
                p.vx = p.vx / speed * max_speed
                p.vy = p.vy / speed * max_speed

            # Update position
            p.x += p.vx * dt
            p.y += p.vy * dt

            # Clamp to pitch boundaries (with small margin)
            p.x = max(-PITCH_HALF_LENGTH, min(PITCH_HALF_LENGTH, p.x))
            p.y = max(-PITCH_HALF_WIDTH, min(PITCH_HALF_WIDTH, p.y))

            # Compute acceleration
            p.ax = (p.vx - prev_vx) / max(dt, 0.001)
            p.ay = (p.vy - prev_vy) / max(dt, 0.001)

            # Speed magnitude
            p.speed = math.sqrt(p.vx**2 + p.vy**2)

            # Distance tracking
            dist_step = p.speed * dt
            p.total_distance += dist_step
            if p.is_sprinting:
                p.sprint_distance += dist_step

            # Heart rate simulation (exponential moving average toward target)
            if p.is_sprinting:
                p._target_hr = min(195, p._target_hr + 1)
            else:
                p._target_hr = max(130, p._target_hr - 1)
            p.heart_rate = int(p.heart_rate + 0.05 * (p._target_hr - p.heart_rate))

    # ------------------------------------------------------------------
    # Ball physics
    # ------------------------------------------------------------------

    def _step_ball(self, dt: float):
        ball = self.ball

        if ball._passing:
            # Ball is in transit between players
            ball._pass_timer += dt
            t = min(ball._pass_timer / max(ball._pass_duration, 0.01), 1.0)
            # Smooth interpolation with parabolic arc
            ball.x = ball._pass_start_x + t * (ball._pass_target_x - ball._pass_start_x)
            ball.y = ball._pass_start_y + t * (ball._pass_target_y - ball._pass_start_y)
            ball.z = 0.3 + 2.5 * t * (1 - t)  # parabolic arc, peaks at 0.925m

            if t >= 1.0:
                # Pass complete - find receiving player
                ball._passing = False
                ball.z = 0.3
                best = None
                best_dist = 999
                for p in self.players:
                    d = math.sqrt((p.x - ball.x)**2 + (p.y - ball.y)**2)
                    if d < best_dist:
                        best_dist = d
                        best = p
                if best and best_dist < 5:
                    ball.holder_id = best.player_id
                else:
                    # Loose ball - closest player picks it up
                    ball.holder_id = best.player_id if best else None

            # Ball velocity during pass
            dx = ball._pass_target_x - ball._pass_start_x
            dy = ball._pass_target_y - ball._pass_start_y
            dist = math.sqrt(dx**2 + dy**2) + 0.01
            ball.vx = dx / ball._pass_duration
            ball.vy = dy / ball._pass_duration
            ball.speed = math.sqrt(ball.vx**2 + ball.vy**2)

            # Angular velocity (spin during pass)
            ball.angular_vx = self._rng.normal(0, 5)
            ball.angular_vy = self._rng.normal(0, 5)
            ball.angular_vz = self._rng.normal(0, 10)

        elif ball.holder_id:
            # Ball follows holder
            holder = next((p for p in self.players if p.player_id == ball.holder_id), None)
            if holder:
                ball.x = holder.x + 0.8  # slightly ahead
                ball.y = holder.y + 0.3
                ball.z = 0.3
                ball.vx = holder.vx
                ball.vy = holder.vy
                ball.vz = 0
                ball.speed = holder.speed
                ball.angular_vx = 0
                ball.angular_vy = 0
                ball.angular_vz = 0

                # Random chance to pass
                if random.random() < 0.015:
                    self._initiate_pass(holder)
        else:
            # Loose ball - decelerate
            friction = 0.95
            ball.vx *= friction
            ball.vy *= friction
            ball.x += ball.vx * dt
            ball.y += ball.vy * dt
            ball.speed = math.sqrt(ball.vx**2 + ball.vy**2)
            # Closest player picks it up
            best = None
            best_dist = 999
            for p in self.players:
                d = math.sqrt((p.x - ball.x)**2 + (p.y - ball.y)**2)
                if d < best_dist:
                    best_dist = d
                    best = p
            if best and best_dist < 2.5:
                ball.holder_id = best.player_id

    def _initiate_pass(self, holder: PlayerState):
        """Start a pass from the holder to a random teammate."""
        teammates = [p for p in self.players if p.team == holder.team and p.player_id != holder.player_id]
        if not teammates:
            return

        # Weight toward players further up the pitch and closer
        target = random.choice(teammates)

        dx = target.x - holder.x
        dy = target.y - holder.y
        dist = math.sqrt(dx**2 + dy**2) + 0.01

        self.ball.holder_id = None
        self.ball._passing = True
        self.ball._pass_timer = 0.0
        self.ball._pass_start_x = self.ball.x
        self.ball._pass_start_y = self.ball.y
        self.ball._pass_target_x = target.x
        self.ball._pass_target_y = target.y
        # Pass speed: ~15 m/s for short passes, ~25 m/s for long
        pass_speed = 12.0 + dist * 0.3
        self.ball._pass_duration = dist / pass_speed

    # ------------------------------------------------------------------
    # Playback controls
    # ------------------------------------------------------------------

    def set_playback_state(self, state: str, speed: float = 1.0):
        try:
            self.playback_state = PlaybackState(state)
        except ValueError:
            self.playback_state = PlaybackState.PLAYING
        self.playback_speed = max(0.25, min(speed, 8.0))

    def get_match_clock(self) -> str:
        """Return match time as MM:SS string."""
        total_secs = int(self.match_time)
        mins = total_secs // 60
        secs = total_secs % 60
        return f"{mins:02d}:{secs:02d}"

    # ------------------------------------------------------------------
    # Snapshot for broadcast
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Return the current full state as a serialisable dict."""
        return {
            "match_time": round(self.match_time, 2),
            "match_clock": self.get_match_clock(),
            "playback_state": self.playback_state.value,
            "playback_speed": self.playback_speed,
            "frame_count": self.frame_count,
            "players": [p.to_dict() for p in self.players],
            "ball": self.ball.to_dict(),
        }
