import random
import time
import json
from datetime import datetime
from kafka import KafkaProducer

def generate_telemetry_event():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "player_id": f"player_{random.randint(1, 22)}",
        "position_x": random.uniform(0, 100),
        "position_y": random.uniform(0, 100),
        "velocity": random.uniform(0, 15),
        "heart_rate": random.randint(120, 190),
        "event_type": random.choice(["pass", "run", "tackle", "shot", "idle"])
    }

def main():
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    print("Telemetry Producer started...")
    try:
        while True:
            event = generate_telemetry_event()
            producer.send('tactical-stream', event)
            time.sleep(0.05)  # 20 Hz
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        producer.close()

if __name__ == "__main__":
    main()
