import os
import sys
import grpc
import math
import random

# Compile proto if not already compiled
src_dir = os.path.dirname(os.path.abspath(__file__))
proto_path = os.path.abspath(os.path.join(src_dir, "../../../libs/proto"))
proto_file = "tactical_stream.proto"

def compile_proto():
    try:
        import grpc_tools.protoc
    except ImportError:
        # Install grpc-tools if missing in dev environment
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "grpcio-tools", "--quiet"])
    
    # Run compiler
    import grpc_tools.protoc
    args = [
        "grpc_tools.protoc",
        f"-I{proto_path}",
        f"--python_out={src_dir}",
        f"--grpc_python_out={src_dir}",
        os.path.join(proto_path, proto_file)
    ]
    # Execute protoc
    import sys
    orig_sys_path = sys.path[:]
    try:
        grpc_tools.protoc.main(args)
    except Exception as e:
        print(f"Proto compilation warning: {e}")

# Try importing, compile if failed
try:
    import tactical_stream_pb2
    import tactical_stream_pb2_grpc
except ImportError:
    print("Protobuf modules not found. Compiling tactical_stream.proto...")
    compile_proto()
    sys.path.append(src_dir)
    try:
        import tactical_stream_pb2
        import tactical_stream_pb2_grpc
    except ImportError:
        print("Protobuf compilation failed or modules still not importable. Using strict mock fallback.")

class MARLClient:
    """
    gRPC Client that queries the marl-inference-engine.
    If the server is down, it fails back to a heuristic mock local calculation
    to ensure zero-downtime robustness in the stream processing.
    """
    def __init__(self, host="localhost", port=50051):
        self.target = f"{host}:{port}"
        self.channel = None
        self.stub = None
        self._connected = False
        self._last_connect_try = 0
        self._connect()

    def _connect(self):
        now = time.time() if 'time' in globals() else 0
        if now - self._last_connect_try < 5:  # Rate limit connection attempts
            return
        self._last_connect_try = now
        try:
            self.channel = grpc.insecure_channel(
                self.target,
                options=[
                    ('grpc.enable_http2', 1),
                    ('grpc.max_receive_message_length', 1024*1024),
                    ('grpc.max_send_message_length', 1024*1024),
                    ('grpc.connect_timeout_ms', 500) # Fast timeout
                ]
            )
            # Use import statement from local scope if needed
            self.stub = tactical_stream_pb2_grpc.MARLServiceStub(self.channel)
            self._connected = True
        except Exception as e:
            print(f"Failed to connect to gRPC server at {self.target}: {e}. Fallback enabled.")
            self._connected = False

    def predict(self, player_id: str, x: float, y: float, velocity: float, heart_rate: int, team_formation: list) -> dict:
        """
        Sends player state to the MARL service and gets action suggestion,
        falling back to high-fidelity mathematical heuristic calculations if offline.
        """
        if not self._connected or not self.stub:
            self._connect()

        if self._connected and self.stub:
            try:
                # Ensure exactly 6 elements
                formation = list(team_formation)
                if len(formation) < 6:
                    formation = formation + [0.0] * (6 - len(formation))
                else:
                    formation = formation[:6]

                request = tactical_stream_pb2.TacticalObservation(
                    player_id=player_id,
                    position_x=x,
                    position_y=y,
                    velocity=velocity,
                    heart_rate=heart_rate,
                    team_formation=formation
                )
                
                response = self.stub.PredictTacticalMove(request, timeout=0.08) # Tight timeout (80ms)
                return {
                    "suggested_action": response.suggested_action,
                    "confidence": round(response.confidence, 2),
                    "predicted_position": {
                        "x": round(response.predicted_positions[0], 2) if len(response.predicted_positions) > 0 else x,
                        "y": round(response.predicted_positions[1], 2) if len(response.predicted_positions) > 1 else y
                    }
                }
            except Exception as e:
                # print(f"gRPC predict failed: {e}. Falling back.")
                pass

        # Fallback Heuristic
        # Outputs: 0: pass, 1: run, 2: tackle, 3: shot, 4: idle
        # Basic logic: close to goal -> shot, high velocity -> run, low velocity -> idle, etc.
        suggested_action = 4 # idle
        dist_to_goal = math.sqrt((52.5 - abs(x))**2 + y**2)
        if dist_to_goal < 15:
            suggested_action = 3 # shot
        elif velocity > 5.0:
            suggested_action = 1 # run
        elif random.random() < 0.2:
            suggested_action = 0 # pass
        elif random.random() < 0.1:
            suggested_action = 2 # tackle

        confidence = 0.5 + 0.4 * (1.0 / (1.0 + math.exp(-velocity/3)))
        
        # Predicted position: forward in heading
        pred_x = x + (1.2 if x > 0 else -1.2) * velocity * 0.1
        pred_y = y + random.uniform(-1, 1)

        return {
            "suggested_action": suggested_action,
            "confidence": round(confidence, 2),
            "predicted_position": {
                "x": round(pred_x, 2),
                "y": round(pred_y, 2)
            }
        }

# Import time safely
import time
