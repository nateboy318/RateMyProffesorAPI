from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, PlainTextResponse
import os
import subprocess
import threading

app = FastAPI()

DATASET_PATH = "professors_dataset.jsonl"

process_lock = threading.Lock()
build_process = None

@app.get("/count", response_class=PlainTextResponse)
def get_count():
    if not os.path.exists(DATASET_PATH):
        return Response(content="0", media_type="text/plain")
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        count = sum(1 for _ in f)
    return str(count)

@app.get("/download")
def download_file():
    if not os.path.exists(DATASET_PATH):
        return Response(content="File not found", status_code=404)
    return FileResponse(DATASET_PATH, filename="professors_dataset.jsonl", media_type="application/octet-stream")

@app.post("/start")
def start_build():
    global build_process
    with process_lock:
        if build_process is not None and build_process.poll() is None:
            return {"status": "already running"}
        build_process = subprocess.Popen(["python", "build_dataset.py"])
        return {"status": "started"}

@app.post("/pause")
def pause_build():
    global build_process
    with process_lock:
        if build_process is None or build_process.poll() is not None:
            return {"status": "not running"}
        build_process.terminate()
        build_process.wait()
        build_process = None
        return {"status": "paused"}

@app.get("/status")
def build_status():
    global build_process
    with process_lock:
        running = build_process is not None and build_process.poll() is None
        return {"running": running} 