import time
import asyncio
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import psutil

from models.manager import ModelManager
from workers.queue import queue_manager

app = FastAPI(title="Privacy Guardian v2.1")

class ScanRequest(BaseModel):
    imageBase64: str

@app.on_event("startup")
async def startup_event():
    # Force manager initialization before serving
    ModelManager()
    # Start the async workers
    queue_manager.start_workers()

def get_model_manager():
    return ModelManager()

@app.post("/scan")
async def scan(req: ScanRequest):
    job_id = "job_" + str(int(time.time() * 1000))
    await queue_manager.add_job(job_id, req.imageBase64)
    return {"job_id": job_id, "status": "queued"}

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    res = queue_manager.get_result(job_id)
    if not res:
        raise HTTPException(status_code=404, detail="Job not found")
    return res

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/status")
async def status():
    return {"status": "running", "uptime_info": "ok"}

@app.get("/models")
async def models_status(manager: ModelManager = Depends(get_model_manager)):
    return manager.get_status()

@app.get("/metrics")
async def metrics():
    return {
        "ram_usage_percent": psutil.virtual_memory().percent,
        "cpu_usage_percent": psutil.cpu_percent(),
        "queue_depth": queue_manager.get_queue_depth(),
        "active_jobs": len([j for j in queue_manager.results.values() if j["status"] in ["queued", "processing"]])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
