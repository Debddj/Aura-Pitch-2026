FROM python:3.12-slim

WORKDIR /app
COPY apps/telemetry-producer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/telemetry-producer/src/ ./src/
CMD ["python", "src/producer.py"]
