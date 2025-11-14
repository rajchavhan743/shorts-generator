import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from uuid import uuid4
from pathlib import Path
from .video_maker import build_video

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))

@app.get("/", response_class=HTMLResponse)
def index():
    template = env.get_template("index.html")
    return template.render()

@app.post("/generate")
async def generate(
    images: list[UploadFile] = File(...),
    audio: UploadFile = File(...),
    subtitle_text: str = Form(...)
):
    # Save inputs
    job_id = str(uuid4())[:8]
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    img_paths = []
    for idx, img in enumerate(images):
        ext = Path(img.filename).suffix or ".jpg"
        p = job_dir / f"img{idx+1}{ext}"
        with p.open("wb") as f:
            f.write(await img.read())
        img_paths.append(str(p))

    audio_ext = Path(audio.filename).suffix or ".mp3"
    audio_path = job_dir / f"audio{audio_ext}"
    with audio_path.open("wb") as f:
        f.write(await audio.read())

    output_path = OUTPUT_DIR / f"{job_id}.mp4"
    # call builder
    try:
        build_video(img_paths, str(audio_path), subtitle_text, str(output_path), zoom_speed=0.03)
    except Exception as e:
        return {"error": str(e)}

    # Provide download link
    return RedirectResponse(url=f"/download/{job_id}", status_code=303)

@app.get("/download/{job_id}")
def download(job_id: str):
    file_path = OUTPUT_DIR / f"{job_id}.mp4"
    if not file_path.exists():
        return {"error":"file not found"}
    return FileResponse(path=str(file_path), media_type="video/mp4", filename=f"{job_id}.mp4")
