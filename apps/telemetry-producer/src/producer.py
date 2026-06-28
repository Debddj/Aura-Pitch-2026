import asyncio
import json
import math
import os
import random
import sys
import time
from typing import Dict, List, Optional
import websockets

# Constants for Pitch Size
PITCH_HALF_LENGTH = 52.5
PITCH_HALF_WIDTH = 34.0

# Joint structure names (29 key points)
JOINT_NAMES = [
    "pelvis", "spine_navel", "spine_chest", "neck", "head",
    "left_clavicle", "left_shoulder", "left_elbow", "left_wrist",
    "right_clavicle", "right_shoulder", "right_elbow", "right_wrist",
    "left_hip", "left_knee", "left_ankle", "left_foot",
    "right_hip", "right_knee", "right_ankle", "right_foot",
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_hand", "right_hand", "chest_mid"
]

# Formations (Home: 4-3-3, Away: 4-4-2)
HOME_BASE_POSITIONS = {
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

AWAY_BASE_POSITIONS = {
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

class TelemetryProducer:
    def __init__(self):
        self.playback_state = "PLAYING"
        self.playback_speed = 1.0
        self.match_time = 0.0
        self.frame_count = 0
        
        # Initialize players
        self.players = []
        self._init_players()
        
        # Initialize ball
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.ball_z = 0.3
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.ball_vz = 0.0
        self.ball_spin_x = 0.0
        self.ball_spin_y = 0.0
        self.ball_spin_z = 0.0
        self.ball_holder_id = "home_7" # Start with CM2 holding the ball
        
        # Ball passing logic
        self.is_passing = False
        self.pass_start_x = 0.0
        self.pass_start_y = 0.0
        self.pass_target_x = 0.0
        self.pass_target_y = 0.0
        self.pass_timer = 0.0
        self.pass_duration = 0.0

    def _init_players(self):
        # Home jerseys & roles
        home_roles = list(HOME_BASE_POSITIONS.keys())
        home_jerseys = [1, 2, 3, 4, 5, 6, 8, 10, 7, 9, 11]
        for i, role in enumerate(home_roles):
            bx, by = HOME_BASE_POSITIONS[role]
            self.players.append({
                "player_id": f"home_{i+1}",
                "team": "home",
                "jersey_number": home_jerseys[i],
                "role": role,
                "base_x": bx,
                "base_y": by,
                "x": bx + random.uniform(-1, 1),
                "y": by + random.uniform(-1, 1),
                "z": 0.0,
                "vx": 0.0,
                "vy": 0.0,
                "vz": 0.0,
                "ax": 0.0,
                "ay": 0.0,
                "az": 0.0,
                "speed": 0.0,
                "heart_rate": 130,
                "sprint_distance": 0.0,
                "total_distance": 0.0,
                "is_sprinting": False,
                "sprint_timer": 0.0,
                "phase": random.uniform(0, 2 * math.pi)
            })

        # Away jerseys & roles
        away_roles = list(AWAY_BASE_POSITIONS.keys())
        away_jerseys = [1, 2, 3, 4, 5, 6, 7, 8, 11, 9, 10]
        for i, role in enumerate(away_roles):
            bx, by = AWAY_BASE_POSITIONS[role]
            self.players.append({
                "player_id": f"away_{i+1}",
                "team": "away",
                "jersey_number": away_jerseys[i],
                "role": role,
                "base_x": bx,
                "base_y": by,
                "x": bx + random.uniform(-1, 1),
                "y": by + random.uniform(-1, 1),
                "z": 0.0,
                "vx": 0.0,
                "vy": 0.0,
                "vz": 0.0,
                "ax": 0.0,
                "ay": 0.0,
                "az": 0.0,
                "speed": 0.0,
                "heart_rate": 130,
                "sprint_distance": 0.0,
                "total_distance": 0.0,
                "is_sprinting": False,
                "sprint_timer": 0.0,
                "phase": random.uniform(0, 2 * math.pi)
            })

    def _generate_skeletal_data(self, p: dict, speed: float) -> List[Dict]:
        """
        Generates a 29-joint spatial skeleton layout.
        Applies mathematical walking/sprinting gait offsets relative to the player's position
        based on velocity heading and stride phase.
        """
        heading = math.atan2(p["vy"], p["vx"]) if speed > 0.1 else 0.0
        phase = p["phase"]
        
        # Higher speed increases stride frequency and amplitude
        stride_freq = 2.0 + 3.0 * (speed / 8.0)
        stride_amp = 0.1 + 0.3 * (speed / 8.0)
        
        # Dynamic phase update
        p["phase"] = (phase + stride_freq * 0.02) % (2 * math.pi)
        
        # Base height of joints (meters)
        heights = {
            "pelvis": 0.95, "spine_navel": 1.15, "spine_chest": 1.35, "neck": 1.55, "head": 1.70,
            "left_clavicle": 1.45, "left_shoulder": 1.45, "left_elbow": 1.15, "left_wrist": 0.95,
            "right_clavicle": 1.45, "right_shoulder": 1.45, "right_elbow": 1.15, "right_wrist": 0.95,
            "left_hip": 0.90, "left_knee": 0.50, "left_ankle": 0.12, "left_foot": 0.0,
            "right_hip": 0.90, "right_knee": 0.50, "right_ankle": 0.12, "right_foot": 0.0,
            "nose": 1.70, "left_eye": 1.72, "right_eye": 1.72, "left_ear": 1.70, "right_ear": 1.70,
            "left_hand": 0.90, "right_hand": 0.90, "chest_mid": 1.40
        }
        
        skeleton = []
        for joint in JOINT_NAMES:
            # Base local offset relative to player center
            lx = 0.0
            ly = 0.0
            lz = heights.get(joint, 1.0)
            
            # Simple gait simulation for limbs
            cos_ph = math.cos(p["phase"])
            sin_ph = math.sin(p["phase"])
            
            # Left side vs Right side alternation
            if "left" in joint:
                mult = 1.0
            else:
                mult = -1.0
                
            # Gait offsets
            if "shoulder" in joint or "wrist" in joint or "hand" in joint:
                # Arm swing: back/forth along heading direction
                swing = mult * cos_ph * stride_amp * 1.5
                lx += swing * math.cos(heading)
                ly += swing * math.sin(heading)
            elif "hip" in joint or "knee" in joint or "ankle" in joint or "foot" in joint:
                # Leg swing: opposite to arm swing
                swing = -mult * cos_ph * stride_amp * 2.0
                lx += swing * math.cos(heading)
                ly += swing * math.sin(heading)
                
                # Knee bend/lift
                if "knee" in joint:
                    lz += max(0.0, -mult * sin_ph * stride_amp * 0.8)
                # Foot lift
                if "ankle" in joint or "foot" in joint:
                    lz += max(0.0, -mult * sin_ph * stride_amp * 1.2)
                    
            # Lateral offsets for shoulders/hips
            if "shoulder" in joint or "clavicle" in joint:
                lx += 0.25 * mult * math.cos(heading + math.pi/2)
                ly += 0.25 * mult * math.sin(heading + math.pi/2)
            elif "hip" in joint:
                lx += 0.15 * mult * math.cos(heading + math.pi/2)
                ly += 0.15 * mult * math.sin(heading + math.pi/2)
                
            skeleton.append({
                "joint": joint,
                "x": round(p["x"] + lx, 3),
                "y": round(p["y"] + ly, 3),
                "z": round(p["z"] + lz, 3)
            })
            
        return skeleton

    def tick(self, dt: float):
        """Advances the spatial physics loop by dt seconds."""
        if self.playback_state == "PAUSED":
            return
            
        eff_dt = dt * self.playback_speed
        
        # 1. Update player coordinates (at 50Hz)
        for p in self.players:
            # Ornstein-Uhlenbeck drift to base
            theta = 0.5
            sigma = 1.5
            
            drift_x = theta * (p["base_x"] - p["x"])
            drift_y = theta * (p["base_y"] - p["y"])
            
            # Attract players to the ball
            ball_dx = self.ball_x - p["x"]
            ball_dy = self.ball_y - p["y"]
            ball_dist = math.sqrt(ball_dx**2 + ball_dy**2) + 0.01
            
            if ball_dist < 20.0 and p["role"] != "GK":
                drift_x += (0.3 / ball_dist) * ball_dx
                drift_y += (0.3 / ball_dist) * ball_dy
                
            # Sprint cycles
            if p["sprint_timer"] > 0:
                p["sprint_timer"] -= eff_dt
                p["is_sprinting"] = True
                sprint_mult = 3.0
            else:
                p["is_sprinting"] = False
                sprint_mult = 1.0
                if random.random() < 0.005:
                    p["sprint_timer"] = 1.0 + random.random() * 2.0
                    
            noise_x = sigma * random.normalvariate(0, 1) * math.sqrt(eff_dt)
            noise_y = sigma * random.normalvariate(0, 1) * math.sqrt(eff_dt)
            
            prev_vx, prev_vy = p["vx"], p["vy"]
            p["vx"] = (drift_x + noise_x * sprint_mult) / eff_dt
            p["vy"] = (drift_y + noise_y * sprint_mult) / eff_dt
            
            # Max speed restrictions
            max_speed = 9.5 if p["is_sprinting"] else 4.0
            p["speed"] = math.sqrt(p["vx"]**2 + p["vy"]**2)
            if p["speed"] > max_speed:
                p["vx"] = (p["vx"] / p["speed"]) * max_speed
                p["vy"] = (p["vy"] / p["speed"]) * max_speed
                p["speed"] = max_speed
                
            p["x"] += p["vx"] * eff_dt
            p["y"] += p["vy"] * eff_dt
            
            # Pitch limits
            p["x"] = max(-PITCH_HALF_LENGTH, min(PITCH_HALF_LENGTH, p["x"]))
            p["y"] = max(-PITCH_HALF_WIDTH, min(PITCH_HALF_WIDTH, p["y"]))
            
            # Acceleration
            p["ax"] = (p["vx"] - prev_vx) / eff_dt
            p["ay"] = (p["vy"] - prev_vy) / eff_dt
            
            # Distance statistics
            dist_step = p["speed"] * eff_dt
            p["total_distance"] += dist_step
            if p["is_sprinting"]:
                p["sprint_distance"] += dist_step
                
            # Heart rate
            target_hr = 190 if p["is_sprinting"] else (135 + int(p["speed"] * 5.0))
            p["heart_rate"] = int(p["heart_rate"] + 0.08 * (target_hr - p["heart_rate"]))
            p["heart_rate"] = max(110, min(198, p["heart_rate"]))

        # 2. Update Ball coordinates (with 500Hz sub-tick physics simulation)
        # We run 10 internal sub-ticks for the ball during one 50Hz frame
        ball_history = []
        ball_sub_dt = eff_dt / 10.0
        
        for _ in range(10):
            if self.is_passing:
                self.pass_timer += ball_sub_dt
                t = min(self.pass_timer / max(self.pass_duration, 0.01), 1.0)
                
                # Trajectory parabola
                self.ball_x = self.pass_start_x + t * (self.pass_target_x - self.pass_start_x)
                self.ball_y = self.pass_start_y + t * (self.pass_target_y - self.pass_start_y)
                self.ball_z = 0.3 + 3.0 * t * (1.0 - t) # peak height of 0.75m
                
                # Spin decay
                self.ball_spin_x *= 0.99
                self.ball_spin_y *= 0.99
                self.ball_spin_z *= 0.99
                
                if t >= 1.0:
                    self.is_passing = False
                    self.ball_z = 0.3
                    
                    # Determine receiver
                    best_receiver = None
                    min_dist = 999.0
                    for p in self.players:
                        d = math.sqrt((p["x"] - self.ball_x)**2 + (p["y"] - self.ball_y)**2)
                        if d < min_dist:
                            min_dist = d
                            best_receiver = p
                            
                    if best_receiver and min_dist < 4.0:
                        self.ball_holder_id = best_receiver["player_id"]
                    else:
                        self.ball_holder_id = None # loose ball
            
            elif self.ball_holder_id:
                holder = next((p for p in self.players if p["player_id"] == self.ball_holder_id), None)
                if holder:
                    # ball positioned ahead of the carrier
                    heading = math.atan2(holder["vy"], holder["vx"]) if holder["speed"] > 0.1 else 0.0
                    self.ball_x = holder["x"] + 0.6 * math.cos(heading)
                    self.ball_y = holder["y"] + 0.6 * math.sin(heading)
                    self.ball_z = 0.3
                    
                    # Check pass trigger
                    if random.random() < 0.002: # chance of passing on sub-tick
                        self._trigger_pass(holder)
            else:
                # Loose ball kinematics
                self.ball_vx *= 0.95 # friction
                self.ball_vy *= 0.95
                self.ball_x += self.ball_vx * ball_sub_dt
                self.ball_y += self.ball_vy * ball_sub_dt
                
                # Check interception
                best_interceptor = None
                min_dist = 999.0
                for p in self.players:
                    d = math.sqrt((p["x"] - self.ball_x)**2 + (p["y"] - self.ball_y)**2)
                    if d < min_dist:
                        min_dist = d
                        best_interceptor = p
                if best_interceptor and min_dist < 2.0:
                    self.ball_holder_id = best_interceptor["player_id"]

            ball_history.append({
                "x": round(self.ball_x, 3),
                "y": round(self.ball_y, 3),
                "z": round(self.ball_z, 3),
                "spin": {
                    "x": round(self.ball_spin_x, 1),
                    "y": round(self.ball_spin_y, 1),
                    "z": round(self.ball_spin_z, 1)
                }
            })
            
        self.match_time += eff_dt
        self.frame_count += 1
        return ball_history

    def _trigger_pass(self, holder: dict):
        teammates = [p for p in self.players if p["team"] == holder["team"] and p["player_id"] != holder["player_id"]]
        if not teammates:
            return
            
        # Target closest forward player
        target = random.choice(teammates)
        
        self.ball_holder_id = None
        self.is_passing = True
        self.pass_start_x = self.ball_x
        self.pass_start_y = self.ball_y
        self.pass_target_x = target["x"]
        self.pass_target_y = target["y"]
        self.pass_timer = 0.0
        
        dist = math.sqrt((target["x"] - holder["x"])**2 + (target["y"] - holder["y"])**2)
        # Average pass velocity ~16 m/s
        self.pass_duration = dist / 16.0
        
        # Spin initialization
        self.ball_spin_x = random.uniform(-10, 10)
        self.ball_spin_y = random.uniform(-10, 10)
        self.ball_spin_z = random.uniform(-30, 30) # curl

    def snapshot(self, ball_history: List[Dict]) -> dict:
        from datetime import datetime
        
        # Generate full player array with skeletal nodes included
        serialized_players = []
        for p in self.players:
            skeleton = self._generate_skeletal_data(p, p["speed"])
            serialized_players.append({
                "player_id": p["player_id"],
                "team": p["team"],
                "jersey_number": p["jersey_number"],
                "role": p["role"],
                "position": {"x": round(p["x"], 2), "y": round(p["y"], 2), "z": round(p["z"], 2)},
                "velocity": {"x": round(p["vx"], 2), "y": round(p["vy"], 2), "z": round(p["vz"], 2)},
                "acceleration": {"x": round(p["ax"], 2), "y": round(p["ay"], 2), "z": round(p["az"], 2)},
                "speed": round(p["speed"], 2),
                "heart_rate": p["heart_rate"],
                "sprint_distance": round(p["sprint_distance"], 1),
                "total_distance": round(p["total_distance"], 1),
                "is_sprinting": p["is_sprinting"],
                "skeleton": skeleton
            })
            
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "match_time": round(self.match_time, 2),
            "match_clock": f"{int(self.match_time // 60):02d}:{int(self.match_time % 60):02d}",
            "playback_state": self.playback_state,
            "playback_speed": self.playback_speed,
            "frame_count": self.frame_count,
            "players": serialized_players,
            "ball": {
                "position": {"x": round(self.ball_x, 2), "y": round(self.ball_y, 2), "z": round(self.ball_z, 3)},
                "velocity": {"x": round(self.ball_vx, 2), "y": round(self.ball_vy, 2), "z": round(self.ball_vz, 3)},
                "speed": round(math.sqrt(self.ball_vx**2 + self.ball_vy**2), 2),
                "angular_velocity": {
                    "x": round(self.ball_spin_x, 1),
                    "y": round(self.ball_spin_y, 1),
                    "z": round(self.ball_spin_z, 1)
                },
                "holder_id": self.ball_holder_id,
                "subticks": ball_history # 500Hz sub-tick data
            }
        }

async def run_simulation(ws_url: str):
    producer = TelemetryProducer()
    dt = 0.02 # 50Hz main tick rate
    
    print(f"Connecting to streaming analytics websocket at {ws_url}...")
    while True:
        try:
            async with websockets.connect(ws_url) as websocket:
                print("Connected to streaming analytics. Initiating 50Hz telemetry output...")
                
                # Listen task for backend playback controls
                async def control_listener():
                    try:
                        async for message in websocket:
                            cmd = json.loads(message)
                            if cmd.get("type") == "CONTROL":
                                producer.playback_state = cmd.get("state", "PLAYING")
                                producer.playback_speed = cmd.get("speed", 1.0)
                                print(f"Synced playback: state={producer.playback_state}, speed={producer.playback_speed}")
                    except Exception as e:
                        print(f"Control channel error: {e}")

                listener_task = asyncio.create_task(control_listener())
                
                # Telemetry generation loop
                try:
                    while True:
                        start_time = time.time()
                        
                        ball_history = producer.tick(dt)
                        if producer.playback_state != "PAUSED":
                            frame = producer.snapshot(ball_history)
                            await websocket.send(json.dumps(frame))
                            
                        # Keep stable 50Hz frequency
                        elapsed = time.time() - start_time
                        sleep_time = max(0.001, dt - elapsed)
                        # Speed scaling
                        if producer.playback_state == "FAST_FORWARD":
                            sleep_time /= max(0.5, producer.playback_speed)
                            
                        await asyncio.sleep(sleep_time)
                finally:
                    listener_task.cancel()
                    
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
            print("Analytics server unavailable. Retrying in 2 seconds...")
            await asyncio.sleep(2.0)
        except Exception as e:
            print(f"Simulation loop crash, resetting: {e}")
            await asyncio.sleep(2.0)

def main():
    ws_url = os.getenv("ANALYTICS_WS_URL", "ws://localhost:8000/ws/telemetry")
    asyncio.run(run_simulation(ws_url))

if __name__ == "__main__":
    main()
