# Variables
APP ?=
POETRY = poetry
DOCKER_COMPOSE = docker compose
SERVICE = spark

# Build the Docker image
build:
	$(DOCKER_COMPOSE) build

# Start the Docker container in background
up:
	$(DOCKER_COMPOSE) up -d

# Stop the container
down:
	$(DOCKER_COMPOSE) down

# Rebuild everything from scratch
rebuild: down build up

# Run detection inside Docker container
test:
	$(DOCKER_COMPOSE) exec $(SERVICE) python3 scripts/test_detection.py $(APP)

# Run detection CLI via Poetry
cli:
	$(POETRY) run dscc create_app $(APP)

spark:
	@if [ -z "$(APP)" ]; then \
		docker compose run spark poetry run python scripts/test_detection.py; \
	else \
		docker compose run spark poetry run python scripts/test_detection.py $(APP); \
	fi



# List apps via CLI
list-apps:
	$(POETRY) run dscc list_apps

# Delete an app
delete-app:
	$(POETRY) run dscc delete_app $(APP)

# Shell into Docker container
shell:
	$(DOCKER_COMPOSE) exec $(SERVICE) bash

check:
	@echo "🧭 Current directory: $(shell pwd)"
	@echo "📄 docker-compose file exists:" && test -f docker-compose.yml && echo "✅ Yes" || echo "❌ No"

build-frontend:
	python3 frontend/build.py

validate-index:
	poetry run python scripts/validate_index_yaml.py

# Run FastAPI (local dev)
serve:
	uvicorn web.main:app --reload --port 8000

# Trigger full detection run through the Spark API
run-all:
	curl -u $$SPARK_API_USER:$$SPARK_API_PASS -X POST http://localhost:9000/run-all

test-pr:
	@echo "🧪 Generating test app submission"
	mkdir -p submission_store/uploads
	mkdir -p submission_store/jobs
	@JOB_ID=$$(uuidgen); \
	APP_NAME=testapp_$$(date +%s); \
	mkdir -p $$APP_NAME/base/config && \
	echo "name: Test detection" > $$APP_NAME/base/config/test.yaml && \
	zip -r submission_store/uploads/$$JOB_ID.zip $$APP_NAME > /dev/null && \
	echo "{ \
	\"id\": \"$$JOB_ID\", \
	\"user\": \"TestUser\", \
	\"filename\": \"$$APP_NAME.zip\", \
	\"zip_path\": \"submission_store/uploads/$$JOB_ID.zip\", \
	\"status\": \"queued\", \
	\"submitted_at\": \"$$(date -Iseconds)\" \
	}" > submission_store/jobs/$$JOB_ID.json && \
	echo "✅ Created test job $$JOB_ID for $$APP_NAME" && \
	curl -X POST http://localhost:9000/approve/$$JOB_ID \
		-H "Authorization: Bearer admin-token"
