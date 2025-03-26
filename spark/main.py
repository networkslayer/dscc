# spark/main.py

from fastapi import FastAPI, Request, HTTPException, Depends, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
import subprocess
import os
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

from fastapi import APIRouter, HTTPException


app = FastAPI()
templates = Jinja2Templates(directory="frontend/templates")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

USERNAME = os.getenv("SPARK_API_USER", "admin")
PASSWORD = os.getenv("SPARK_API_PASS", "changeme")

tokens = {"admin-token": USERNAME}  # simplistic token mapping for now

class RunRequest(BaseModel):
    app: str | None = None


def verify_token(token: str = Depends(oauth2_scheme)):
    if token not in tokens:
        raise HTTPException(status_code=401, detail="Invalid token")
    return tokens[token]


def extract_zip_flat(zip_path: Path, target_dir: Path, app_name: str):
    from zipfile import ZipFile

    with ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.namelist()

        for member in members:
            # ✅ Skip Mac metadata folders
            if member.startswith("__MACOSX/") or "__MACOSX" in Path(member).parts:
                continue

            path_parts = Path(member).parts
            if not path_parts:
                continue

            # Strip top-level folder if it matches the app name
            if path_parts[0] == app_name:
                relative_path = Path(*path_parts[1:])
            else:
                relative_path = Path(*path_parts)

            if not relative_path:
                continue

            dest_path = target_dir / relative_path

            if member.endswith("/"):
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(zip_ref.read(member))

    return

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open("frontend/templates/login.html") as f:
        return HTMLResponse(content=f.read())


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == USERNAME and form_data.password == PASSWORD:
        return {"access_token": "admin-token", "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect username or password")


@app.post("/run")
async def run_detection(request: RunRequest):
    cmd = ["poetry", "run", "python", "scripts/test_detection.py"]
    if request.app:
        cmd.append(request.app)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "code": result.returncode,
            "review_state": "pending",
            "note": "Initial checks OK — waiting for manual approval"
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Spark test timed out."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/run-all")
async def run_all_detections(user: str = Depends(verify_token)):
    cmd = ["poetry", "run", "python", "scripts/test_detection.py"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Spark test timed out."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/status/{job_id}", response_class=HTMLResponse)
async def check_status_page(request: Request, job_id: str):
    job_path = Path("submission_store/jobs") / f"{job_id}.json"
    result_path = Path("submission_store/results") / f"{job_id}.json"

    if not job_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with open(job_path) as f:
        job_data = json.load(f)

    result_data = None
    if result_path.exists():
        with open(result_path) as f:
            result_data = json.load(f)

    return templates.TemplateResponse("status.html", {
        "request": request,
        "job": job_data,
        "result": result_data
    })

@app.get("/submissions", response_class=HTMLResponse)
async def serve_submissions_page(request: Request):
    return templates.TemplateResponse("submissions.html", {"request": request})

@app.get("/api/submissions", response_class=JSONResponse)
async def api_submissions(user: str = Depends(verify_token)):
    jobs_dir = Path("submission_store/jobs")
    results_dir = Path("submission_store/results")
    job_entries = []

    for job_file in jobs_dir.glob("*.json"):
        job_id = job_file.stem
        with open(job_file) as f:
            job_data = json.load(f)
        result_path = results_dir / f"{job_id}.json"
        result_data = None
        if result_path.exists():
            with open(result_path) as f:
                result_data = json.load(f)
        job_entries.append({
            "id": job_id,
            "user": job_data.get("user"),
            "submitted_at": job_data.get("submitted_at"),
            "filename": job_data.get("filename"),
            "status": result_data.get("status") if result_data else "Pending",
            "note": result_data.get("note") if result_data else "Awaiting result"
        })

    return job_entries

def create_branch_and_pr(job_id: str, app_path: str, app_name: str):
    branch_name = f"submission/{job_id}"

    subprocess.run(["git", "config", "--global", "user.email", "derekking001@gmail.com"], check=True)
    subprocess.run(["git", "config", "--global", "user.name", "networkslayer"], check=True)
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)

    # Only add and commit the app_path to avoid committing unrelated changes
    subprocess.run(["git", "add", app_path], check=True)
    subprocess.run(["git", "status"], check=True)
    commit_result = subprocess.run(["git", "commit", "-m", f"Add app submission for {app_name} via job {job_id}"], capture_output=True, text=True)

    if commit_result.returncode != 0:
        print("⚠️ Nothing to commit:", commit_result.stderr)
        return

    # Force HTTPS remote for GitHub
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    REPO_URL = os.getenv("GITHUB_REPO", "")
    
    print(f"https://x-access-token:{GITHUB_TOKEN}@{REPO_URL}")
    https_url = f"https://x-access-token:{GITHUB_TOKEN}@{REPO_URL}"

    subprocess.run(["git", "remote", "set-url", "origin", https_url], check=True)

    subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)

    # 💡 Authenticate GitHub CLI non-interactively

    gh_token = os.getenv("GH_TOKEN", GITHUB_TOKEN)
    # subprocess.run(["gh", "auth", "login", "--with-token"], input=gh_token.encode(), check=True)
    subprocess.run([
        "gh", "pr", "create",
        "--base", "main",
        "--head", branch_name,
        "--title", f"App submission: {app_name}",
        "--body", f"Auto-submitted app from job `{job_id}`"
    ], check=True)

    return

@app.post("/approve/{job_id}")
async def approve(job_id: str, user: str = Depends(verify_token)):
    job_file = Path(f"submission_store/jobs/{job_id}.json")
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with open(job_file) as f:
        job_data = json.load(f)

    zip_path = Path(job_data["zip_path"])
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Zip file not found")

    app_name = Path(job_data["filename"]).stem
    target_dir = Path(f"apps/{app_name}")
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)

    # extract_zip_flat(zip_path, target_dir, app_name)

    # Unzip to temp, copy only app/<name> into branch:
    extract_path = Path("/tmp") / f"{job_id}_extract"
    if extract_path.exists():
        shutil.rmtree(extract_path)
    extract_path.mkdir(parents=True)

    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    # Find correct app dir inside zip (heuristic match)
    inner_dirs = [d for d in extract_path.rglob("*") if d.is_dir() and d.name == app_name]
    if not inner_dirs:
        raise HTTPException(status_code=400, detail="Could not locate app directory inside ZIP")
    submitted_app_path = inner_dirs[0]

    # Move to apps/<app_name> in working tree
    final_app_path = Path(f"apps/{app_name}")
    if final_app_path.exists():
        shutil.rmtree(final_app_path)
    shutil.copytree(submitted_app_path, final_app_path)

    macosx_path = Path("apps") / "__MACOSX"
    if macosx_path.exists() and macosx_path.is_dir():
        shutil.rmtree(macosx_path)

    #try:
    #    subprocess.run(["python", "frontend/build.py"], check=True)
    #except Exception as e:
    #    print("⚠️ Failed to rebuild detections.json:", e)

    try:
        create_branch_and_pr(job_id, f"apps/{app_name}", app_name)
    except Exception as e:
        print("⚠️ Failed to create pull request:", e)

    result_path = Path(f"submission_store/results/{job_id}.json")
    result_path.write_text(json.dumps({
        "status": "approved",
        "note": "Approved and submitted as PR"
    }, indent=2))

    return {"message": "App approved and PR created"}

"""
@app.post("/approve/{job_id}")
async def approve(job_id: str, user: str = Depends(verify_token)):
    job_file = Path(f"submission_store/jobs/{job_id}.json")
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with open(job_file) as f:
        job_data = json.load(f)

    zip_path = Path(job_data["zip_path"])
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Zip file not found")

    # Extract app name from filename (strip .zip)
    app_name = Path(job_data["filename"]).stem
    target_dir = Path(f"apps/{app_name}")
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)

    extract_zip_flat(zip_path, target_dir, app_name)

    # FIX -- not sure why this gets generated on upload...
    macosx_path = Path("apps") / "__MACOSX"
    if macosx_path.exists() and macosx_path.is_dir():
        shutil.rmtree(macosx_path)

    try:
        import subprocess
        subprocess.run(["python", "frontend/build.py"], check=True)
    except Exception as e:
        print("⚠️ Failed to refresh detections.json:", e)

    result_path = Path(f"submission_store/results/{job_id}.json")
    result_path.write_text(json.dumps({
        "status": "approved",
        "note": "Approved and added to apps directory"
    }, indent=2))

    return {"message": "App approved and deployed"}
"""

@app.post("/reject/{job_id}")
async def reject(job_id: str, user: str = Depends(verify_token)):
    job_file = Path(f"submission_store/jobs/{job_id}.json")
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    result_path = Path(f"submission_store/results/{job_id}.json")
    result_path.write_text(json.dumps({
        "status": "rejected",
        "note": "Rejected by reviewer"
    }, indent=2))

    return {"message": "App rejected"}

"""
@app.post("/approve/{job_id}")
async def approve_submission(job_id: str, user: str = Depends(verify_token)):
    extract_path = Path("/tmp/dscc_submissions") / job_id
    extracted_dirs = list(extract_path.iterdir()) if extract_path.exists() else []

    if not extracted_dirs:
        raise HTTPException(status_code=400, detail="No extracted app found.")

    app_dir = extracted_dirs[0]
    target_path = Path("apps") / app_dir.name

    if target_path.exists():
        shutil.rmtree(target_path)

    shutil.move(str(app_dir), target_path)

    return RedirectResponse(url="/submissions", status_code=303)


@app.post("/reject/{job_id}")
async def reject_submission(job_id: str, user: str = Depends(verify_token)):
    extract_path = Path("/tmp/dscc_submissions") / job_id
    job_file = Path("submission_store/jobs") / f"{job_id}.json"
    result_file = Path("submission_store/results") / f"{job_id}.json"

    if extract_path.exists():
        shutil.rmtree(extract_path)
    if job_file.exists():
        job_file.unlink()
    if result_file.exists():
        result_file.unlink()

    return RedirectResponse(url="/submissions", status_code=303)

"""

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return await http_exception_handler(request, exc)

@app.get("/api/status/{job_id}", response_class=JSONResponse)
async def api_job_status(job_id: str):
    result_file = Path(f"submission_store/results/{job_id}.json")
    if result_file.exists():
        with open(result_file) as f:
            return json.load(f)
    return {"status": "pending", "note": "Awaiting result"}

@app.get("/status/{job_id}", response_class=HTMLResponse)
async def serve_status_page(request: Request, job_id: str):
    return templates.TemplateResponse("status.html", {"request": request, "job_id": job_id})

