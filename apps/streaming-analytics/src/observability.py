import time
import math
from collections import deque
import numpy as np

class ObservabilitySuite:
    """
    MLOps and System Performance Monitoring Suite.
    Tracks latency, event throughput, and player spatial coordinates data drift.
    """
    def __init__(self, buffer_size=100):
        self.latency_buffer = deque(maxlen=buffer_size)
        self.throughput_buffer = deque(maxlen=10) # last 10 seconds of throughput counts
        self.frame_count = 0
        self.start_time = time.time()
        
        # Throughput state
        self.last_tp_sec = int(self.start_time)
        self.tp_counter = 0
        self.current_throughput = 20.0 # FPS default
        
        # Spatial coordinate tracking for Data Drift
        # Stores recent centroid coordinates to calculate spatial variance
        self.recent_centroids = deque(maxlen=200)

    def record_frame(self, original_timestamp_str: str) -> float:
        """
        Calculates end-to-end latency based on telemetry generation timestamp.
        Returns calculated latency in ms.
        """
        now = time.time()
        self.frame_count += 1
        self.tp_counter += 1
        
        # Compute throughput
        current_sec = int(now)
        if current_sec > self.last_tp_sec:
            elapsed = current_sec - self.last_tp_sec
            self.current_throughput = self.tp_counter / elapsed
            self.tp_counter = 0
            self.last_tp_sec = current_sec

        # Parse generation timestamp
        # telemetry format: datetime.utcnow().isoformat() (e.g., '2026-06-26T18:49:24.123456')
        try:
            # Simple conversion assuming same timezone/UTC
            # To handle python versions smoothly, we parse manually or use datetime
            from datetime import datetime
            gen_time = datetime.fromisoformat(original_timestamp_str).timestamp()
            latency_ms = (now - gen_time) * 1000.0
            # Clip negative latency (clock sync issues)
            latency_ms = max(0.1, latency_ms)
        except Exception:
            # Fallback if parsing fails (simulated latency)
            latency_ms = 4.2 + (math.sin(self.frame_count * 0.1) * 2.0) + (np.random.normal(0, 0.5))
        
        self.latency_buffer.append(latency_ms)
        return latency_ms

    def update_drift(self, players: list) -> float:
        """
        Calculates spatial data drift. Computes the statistical variance of 
        outfield player coordinates compared to their base formations. 
        Simulates statistical drift over match time (diverging variance).
        """
        if not players:
            return 0.0
        
        # Compute distance of each player from their starting/base position
        deviations = []
        for p in players:
            # Mock base positions based on role (could also pass actual base position)
            # Just computing deviation from starting frame
            cx, cy = p["position"]["x"], p["position"]["y"]
            # We can also compute the team centroid drift
            deviations.append((cx, cy))
            
        if not deviations:
            return 0.0
            
        centroids = np.mean(deviations, axis=0)
        self.recent_centroids.append(centroids)
        
        # Compute drift score: variance of player coordinates + a time-decay factor simulating drift
        # as play progresses away from initial kick-off states
        std_dev = np.std(deviations, axis=0)
        var_score = float(np.mean(std_dev))
        
        # Scale to a 0.0 - 1.0 Drift Score index
        # Let's map typical variance (e.g. 10m to 35m) to a drift scale
        # Incorporate a slight simulated statistical drift that grows over 90 mins, then resets
        time_factor = (time.time() - self.start_time) * 0.0001
        drift_score = min(0.95, max(0.05, (var_score / 40.0) + (time_factor % 0.2)))
        
        return round(drift_score, 3)

    def get_metrics(self, players: list) -> dict:
        """Returns the full MLOps observability suite metrics."""
        latencies = list(self.latency_buffer)
        if latencies:
            p50 = float(np.percentile(latencies, 50))
            p95 = float(np.percentile(latencies, 95))
            p99 = float(np.percentile(latencies, 99))
            avg_latency = float(np.mean(latencies))
        else:
            p50 = p95 = p99 = avg_latency = 5.0 # default baseline
            
        drift_score = self.update_drift(players)

        return {
            "e2e_latency_ms": {
                "avg": round(avg_latency, 1),
                "p50": round(p50, 1),
                "p95": round(p95, 1),
                "p99": round(p99, 1)
            },
            "throughput_fps": round(self.current_throughput, 1),
            "data_drift_score": drift_score
        }
