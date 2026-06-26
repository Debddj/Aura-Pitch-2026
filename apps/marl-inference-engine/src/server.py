import grpc
from concurrent import futures
import torch
import ray
import tactical_stream_pb2
import tactical_stream_pb2_grpc

class MARLInferenceServicer(tactical_stream_pb2_grpc.MARLServiceServicer):
    def __init__(self):
        self.model = torch.load("models/marl_policy.pt")
        self.model.eval()

    def PredictTacticalMove(self, request, context):
        obs = torch.tensor(request.observation, dtype=torch.float32)
        with torch.no_grad():
            action = self.model(obs).argmax().item()
        return tactical_stream_pb2.TacticalResponse(
            suggested_action=action,
            confidence=0.95
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tactical_stream_pb2_grpc.add_MARLServiceServicer_to_server(
        MARLInferenceServicer(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    print("MARL Inference Engine serving on port 50051...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
