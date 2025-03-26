# dscc
Databricks Security Content Center

Welcome to the databricks Security Content Centre

This project provides access to a comprehensive collection of security content, guides, and background information aligned with the MITRE ATT&CK framework. It includes detection strategies, machine learning use cases, and playbooks—where available—to support threat hunting, detection, and investigation, all powered by the Databricks platform.


# 🛡️ Databricks Security Content Center (DSCC)

A modern detection-as-code platform for developing, testing, and delivering security detections for Databricks.

This project includes:

- ✅ PySpark-based detection logic using sample data
- ✅ YAML-driven configuration for each detection
- ✅ A web frontend to view and download apps
- ✅ A CLI (via `fire`) for creating new detection apps
- ✅ Dockerized environment for local development and testing

---

## 🗂️ Project Structure

apps/ ├── my_app/ │ ├── base/config/detection.yaml # YAML config for detection │ └── sample_data.csv # Sample log data

docker/ ├── Dockerfile.spark # Spark runtime image ├── Dockerfile.web # FastAPI + frontend server

frontend/ ├── build.py # Generates detections.json from YAML ├── templates/index.html # HTML UI template ├── static/detections.json # Web-visible detection index (built)

scripts/ ├── test_detection.py # PySpark runner for testing detections

web/ ├── main.py # FastAPI backend (serves HTML + downloads)

dscc/ ├── cli.py # CLI for managing apps (uses fire)

Makefile # Easy dev commands docker-compose.yml # Container orchestration pyproject.toml # Poetry project definition


---

## 🚀 Quick Start

### 🔧 Build both containers

```bash
make build
```

Or clean rebuild
```bash
make rebuild
```

### Run the web UI

```bash
make web
```

Then visit http://localhost:8000

🔬 Run a detection in Spark

```bash
make spark APP=my_app
```
Runs detection logic using PySpark against sample data.

🧪 Run test locally (optional)

```bash
make test-local APP=my_app
```

🧰 CLI Usage (via Poetry + Fire)

```bash
poetry run dscc create_app my_app         # Scaffold a new detection app
poetry run dscc list_apps                 # List all detection apps
poetry run dscc delete_app my_app         # Remove an existing app
```

🧱 Rebuild Frontend Metadata

```bash
make build-frontend

```
🐳 Docker Compose Services

web – FastAPI app that serves frontend + downloads

spark – PySpark engine for detection testing