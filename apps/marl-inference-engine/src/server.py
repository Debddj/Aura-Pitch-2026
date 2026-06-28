import os
import sys
import grpc
from concurrent import futures
import time

# Ensure src is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try importing torch. If not available, we will use a mock neural network fallback.
try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("Warning: PyTorch not found. Falling back to mathematical heuristic mock model.")

# Protobuf imports (might fail if not compiled yet, which is fine for editing, we compile in Docker/scripts)
try:
    import tactical_stream_pb2
    import tactical_stream_pb2_grpc
except ImportError:
    # Fallback to absolute/relative paths if run from root or different places
    try:
        from . import tactical_stream_pb2
        from . import tactical_stream_pb2_grpc
    except ImportError:
        # Dummy classes just in case compilation is done later
        pass

# Define the model structure for loading
if HAS_TORCH:
    class MARLPolicy(nn.Module):
        def __init__(self):
            super(MARLPolicy, self).__init__()
            self.fc = nn.Sequential(
                nn.Linear(10, 64),
                nn.ReLU(),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, 8)
            )
        def forward(self, x):
            return self.fc(x)

class MockModel:
    """Mathematical heuristic mock model to simulate torch inference without torch installed."""
    def __call__(self, x):
        # x is a list or 1D array/tensor of features: [x, y, vel, hr, form0, form1, form2, form3, form4, form5]
        # Return deterministic/stochastic mock outputs resembling the output layer
        # Output: 5 action logits, 1 confidence logit, 2 predicted position offsets
        val = sum(x)
        action_logits = [
            (val * 0.1) % 1.5,
            (val * 0.2) % 2.0,
            (val * 0.3) % 1.2,
            (val * 0.4) % 1.8,
            (val * 0.5) % 1.0
        ]
        confidence_logit = (val * 0.05) % 3.0
        pred_x_offset = ((val * 0.15) % 10.0) - 5.0
        pred_y_offset = ((val * 0.25) % 10.0) - 5.0
        return action_logits + [confidence_logit] + [pred_x_offset, pred_y_offset]

class MARLInferenceServicer(object): # Inherits dynamically if grpc classes are loaded
    def __init__(self):
        self.model = None
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "marl_policy.pt")
        
        if HAS_TORCH and os.path.exists(model_path):
            try:
                # Load PyTorch model
                self.model = torch.load(model_path, map_location=torch.device('cpu'))
                self.model.eval()
                print(f"Loaded PyTorch policy model from {model_path}")
            except Exception as e:
                print(f"Failed to load PyTorch model from {model_path}: {e}. Using MockModel instead.")
                self.model = MockModel()
        else:
            print("Using MockModel for inference.")
            self.model = MockModel()

    def run_inference(self, obs_features):
        """Helper to execute model or mock inference and extract outputs."""
        if HAS_TORCH and isinstance(self.model, nn.Module):
            with torch.no_grad():
                features_tensor = torch.tensor(obs_features, dtype=torch.float32).unsqueeze(0)
                outputs = self.model(features_tensor).squeeze(0).tolist()
        else:
            outputs = self.model(obs_features)

        # Action: index of max logit in the first 5 elements
        action_logits = outputs[:5]
        suggested_action = action_logits.index(max(action_logits))
        
        # Confidence: simple sigmoid logic on element 5
        import math
        conf_logit = outputs[5]
        confidence = 1.0 / (1.0 + math.exp(-max(min(conf_logit, 10), -10)))
        
        # Predicted positions (offset from current player positions)
        pred_offsets = outputs[6:8]
        
        return suggested_action, confidence, pred_offsets

    def PredictTacticalMove(self, request, context):
        try:
            # Build observation array from request
            obs_features = [
                request.position_x,
                request.position_y,
                request.velocity,
                request.heart_rate
            ]
            # Ensure team_formation has exactly 6 elements
            formation = list(request.team_formation)
            if len(formation) < 6:
                formation = formation + [0.0] * (6 - len(formation))
            elif len(formation) > 6:
                formation = formation[:6]
            obs_features.extend(formation)

            suggested_action, confidence, pred_offsets = self.run_inference(obs_features)

            # Predicted positions: offset from player's current coordinate
            pred_x = request.position_x + pred_offsets[0]
            pred_y = request.position_y + pred_offsets[1]

            return tactical_stream_pb2.TacticalResponse(
                suggested_action=suggested_action,
                confidence=confidence,
                predicted_positions=[pred_x, pred_y]
            )
        except Exception as e:
            print(f"Error in PredictTacticalMove: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return tactical_stream_pb2.TacticalResponse()

    def StreamPredictions(self, request_iterator, context):
        try:
            for request in request_iterator:
                # Build observation array from request
                obs_features = [
                    request.position_x,
                    request.position_y,
                    request.velocity,
                    request.heart_rate
                ]
                formation = list(request.team_formation)
                if len(formation) < 6:
                    formation = formation + [0.0] * (6 - len(formation))
                elif len(formation) > 6:
                    formation = formation[:6]
                obs_features.extend(formation)

                suggested_action, confidence, pred_offsets = self.run_inference(obs_features)

                pred_x = request.position_x + pred_offsets[0]
                pred_y = request.position_y + pred_offsets[1]

                yield tactical_stream_pb2.TacticalResponse(
                    suggested_action=suggested_action,
                    confidence=confidence,
                    predicted_positions=[pred_x, pred_y]
                )
        except Exception as e:
            print(f"Error in StreamPredictions: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # We dynamically compile proto and add servicer
    # We load standard naming or fallback
    try:
        import tactical_stream_pb2_grpc
        servicer_class = MARLInferenceServicer
        # In python grpc, the servicer class inherits or just implements methods
        # If we need the base class:
        try:
            class ServicerWithBase(MARLInferenceServicer, tactical_stream_pb2_grpc.MARLServiceServicer):
                pass
            servicer_instance = ServicerWithBase()
        except Exception:
            servicer_instance = MARLInferenceServicer()
            
        tactical_stream_pb2_grpc.add_MARLServiceServicer_to_server(
            servicer_instance, server
        )
    except Exception as e:
        print(f"Failed to register grpc servicer (proto compilation might be pending): {e}")

    server.add_insecure_port("[::]:50051")
    server.start()
    print("MARL Inference Engine serving on port 50051...")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    serve()
