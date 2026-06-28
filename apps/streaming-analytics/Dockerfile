FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for compiling proto/grpc
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and libs/proto
COPY src/ ./src/
COPY libs/proto/ /libs/proto/

# Setup python paths and compile proto
ENV PYTHONPATH=/app/src
ENV MARL_HOST=marl-inference-engine

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
