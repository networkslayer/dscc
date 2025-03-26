from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
from pathlib import Path

import uuid
import shutil
import redis
from fastapi import UploadFile, Form
from fastapi import File
from pathlib import Path
import json
from datetime import datetime


# Connect to Redis
r = redis.Redis(host="redis", port=6379, decode_responses=True)

SUBMISSION_DIR = Path("submission_store")
SUBMISSION_DIR.mkdir(exist_ok=True)
(SUBMISSION_DIR / "uploads").mkdir(parents=True, exist_ok=True)
(SUBMISSION_DIR / "jobs").mkdir(parents=True, exist_ok=True)


app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/download/{app_name}")
def download_app(app_name: str):
    src_dir = Path(f"apps/{app_name}")
    if not src_dir.exists():
        raise HTTPException(status_code=404, detail="App not found")

    zip_path = Path(f"/tmp/{app_name}.zip")
    if zip_path.exists():
        zip_path.unlink()

    shutil.make_archive(str(zip_path).replace(".zip", ""), 'zip', root_dir=src_dir)
    return FileResponse(zip_path, media_type="application/zip", filename=f"{app_name}.zip")

@app.post("/upload")
async def upload_app(file: UploadFile = File(...), user: str = Form(...)):
    job_id = str(uuid.uuid4())
    zip_path = SUBMISSION_DIR / "uploads" / f"{job_id}.zip"

    # Save uploaded zip
    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create job metadata
    job_data = {
    "id": job_id,
    "user": user,
    "filename": file.filename,
    "status": "queued",
    "zip_path": str(zip_path),
    "submitted_at": datetime.utcnow().isoformat() + "Z"
    }

    # Save metadata
    with open(SUBMISSION_DIR / "jobs" / f"{job_id}.json", "w") as f:
        json.dump(job_data, f)

    # Enqueue job
    r.lpush("dscc_jobs", job_id)

    return {"message": "Upload successful", "job_id": job_id}

@app.get("/status/{job_id}")
def check_status(job_id: str):
    job_path = SUBMISSION_DIR / "jobs" / f"{job_id}.json"
    result_path = SUBMISSION_DIR / "results" / f"{job_id}.json"

    if not job_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with open(job_path) as f:
        job_data = json.load(f)

    result_data = None
    if result_path.exists():
        with open(result_path) as f:
            result_data = json.load(f)

    return {
        "job": job_data,
        "result": result_data or "pending"
    }

@app.post("/approve/{job_id}")
def approve_submission(job_id: str):
    job_path = SUBMISSION_DIR / "jobs" / f"{job_id}.json"
    extract_path = Path("/tmp/dscc_submissions") / job_id

    if not job_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with open(job_path) as f:
        job_data = json.load(f)

    extracted_dirs = list(extract_path.iterdir())
    if not extracted_dirs:
        raise HTTPException(status_code=400, detail="No extracted app found.")

    app_dir = extracted_dirs[0]
    target_path = Path("apps") / app_dir.name

    if target_path.exists():
        shutil.rmtree(target_path)

    shutil.move(str(app_dir), target_path)

    return {"message": f"App {app_dir.name} approved and published."}


@app.get("/submissions.html", response_class=HTMLResponse)
async def submissions_page():
    return FileResponse("frontend/templates/submissions.html")

@app.get("/upload_form", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload_form.html", {"request": request})


