FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY models/ ./models/
COPY src/ ./src/
COPY libs/proto/tactical_stream.proto ./proto/

RUN python -m grpc_tools.protoc -I./proto --python_out=./src --grpc_python_out=./src tactical_stream.proto

CMD ["python", "src/server.py"]
