.PHONY: build up down dev-marl dev-analytics dev-producer dev-visualizer test clean

build:
	docker-compose -f infra/docker-compose.yml build

up:
	docker-compose -f infra/docker-compose.yml up -d

down:
	docker-compose -f infra/docker-compose.yml down

dev-marl:
	cd apps/marl-inference-engine && python src/server.py

dev-analytics:
	cd apps/streaming-analytics && uvicorn src.main:app --reload --port 8000

dev-producer:
	cd apps/telemetry-producer && python src/producer.py

dev-visualizer:
	cd apps/web-visualizer && npm run dev

test:
	@echo "Running verification tests..."
	python -c "import torch; print('Torch verification: OK')"
	python -c "import fastapi; import uvicorn; print('FastAPI/Uvicorn verification: OK')"
	@echo "All local python packages verified."

clean:
	docker-compose -f infra/docker-compose.yml down -v
	docker system prune -f
