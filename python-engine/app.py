import time
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
import psutil

from models.manager import ModelManager
from pipeline import execute_pipeline

app = FastAPI(title="Privacy Guardian v2.1")

class ScanRequest(BaseModel):
    imageBase64: str

job_results = {}

def get_model_manager():
    return ModelManager()

def process_job(job_id: str, b64_str: str):
    try:
        b64_out, dets, ptime = execute_pipeline(b64_str)
        job_results[job_id] = {
            "status": "completed",
            "image": b64_out,
            "detections": dets,
            "processing_time": ptime
        }
    except Exception as e:
        job_results[job_id] = {"status": "error", "message": str(e)}

@app.post("/scan")
async def scan(req: ScanRequest, background_tasks: BackgroundTasks):
    job_id = "job_" + str(int(time.time() * 1000))
    job_results[job_id] = {"status": "processing"}
    background_tasks.add_task(process_job, job_id, req.imageBase64)
    return {"job_id": job_id, "status": "processing"}

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    if job_id not in job_results:
        raise HTTPException(status_code=404)
    return job_results[job_id]

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/models")
async def models_status(manager: ModelManager = Depends(get_model_manager)):
    return manager.get_status()

@app.get("/metrics")
async def metrics():
    return {
        "ram_usage_percent": psutil.virtual_memory().percent,
        "cpu_usage_percent": psutil.cpu_percent(),
        "active_jobs": len([j for j in job_results.values() if j["status"] == "processing"])
    }

if __name__ == "__main__":
    import uvicorn
    # Force manager initialization before serving
    ModelManager()
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
