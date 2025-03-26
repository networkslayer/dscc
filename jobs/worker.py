# jobs/worker.py

import redis
import json
import time
import zipfile
import shutil
import requests
from pathlib import Path

r = redis.Redis(host="redis", port=6379, decode_responses=True)

SUBMISSION_DIR = Path("submission_store")
EXTRACT_DIR = Path("/tmp/dscc_submissions")

SPARK_API_URL = "http://spark-api:9000/run"


def trigger_spark(app_name):
    try:
        response = requests.post(SPARK_API_URL, json={"app": app_name}, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}


def process_job(job_id):
    job_file = SUBMISSION_DIR / "jobs" / f"{job_id}.json"
    with open(job_file) as f:
        job = json.load(f)

    zip_path = Path(job["zip_path"])
    extract_path = EXTRACT_DIR / job_id
    if extract_path.exists():
        shutil.rmtree(extract_path)
    extract_path.mkdir(parents=True)

    # Extract zip
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    # Assume folder name = app name
    app_dirs = list(extract_path.iterdir())
    if not app_dirs:
        print(f"No folder found inside {zip_path}")
        return

    app_dir = app_dirs[0]
    target_app_dir = Path("apps") / app_dir.name
    if target_app_dir.exists():
        shutil.rmtree(target_app_dir)
    shutil.move(str(app_dir), target_app_dir)

    result = trigger_spark(app_dir.name)
    result["review_state"] = "pending"
    result["note"] = "Initial checks OK — waiting for manual approval"


    result_file = SUBMISSION_DIR / "results" / f"{job_id}.json"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    with open(result_file, "w") as f:
        json.dump(result, f)


def run_worker():
    print("👷 DSCC Spark Worker Running")
    while True:
        job_id = r.brpop("dscc_jobs", timeout=5)
        if job_id:
            job_id = job_id[1]  # Redis returns (queue, value)
            print(f"🧪 Running job: {job_id}")
            process_job(job_id)
        else:
            time.sleep(1)


if __name__ == "__main__":
    run_worker()