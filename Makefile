.PHONY: build up down test clean

build:
	docker-compose -f infra/docker-compose.yml build

up:
	docker-compose -f infra/docker-compose.yml up -d

down:
	docker-compose -f infra/docker-compose.yml down

test:
	@echo "Running tests..."
	# Add test commands here

clean:
	docker-compose -f infra/docker-compose.yml down -v
	docker system prune -f
