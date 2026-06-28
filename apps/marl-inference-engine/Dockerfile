FROM python:3.12-slim

WORKDIR /app
COPY apps/marl-inference-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/marl-inference-engine/models/ ./models/
COPY apps/marl-inference-engine/src/ ./src/
COPY libs/proto/tactical_stream.proto ./proto/

RUN python -m grpc_tools.protoc -I./proto --python_out=./src --grpc_python_out=./src tactical_stream.proto

CMD ["python", "src/server.py"]
