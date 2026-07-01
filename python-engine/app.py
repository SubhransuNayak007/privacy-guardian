import time
import asyncio
import logging
import json
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import psutil

from models.manager import ModelManager
from workers.queue import queue_manager

# Setup structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("privacy_guardian")

app = FastAPI(title="Privacy Guardian v2.1")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(json.dumps({
        "event": "unhandled_exception",
        "url": str(request.url),
        "error": str(exc)
    }))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

class ScanRequest(BaseModel):
    imageBase64: str

@app.on_event("startup")
async def startup_event():
    manager = ModelManager()
    
    async def model_warmup():
        logger.info(json.dumps({"event": "model_warmup_started"}))
        try:
            # Generous 5-minute timeout for initial model downloads (FastSAM, NudeNet)
            await asyncio.wait_for(asyncio.to_thread(manager.preload_models), timeout=300.0)
            logger.info(json.dumps({"event": "model_warmup_completed"}))
        except Exception as e:
            logger.error(json.dumps({"event": "model_warmup_failed", "error": str(e)}))
        finally:
            # Start queue workers only after models are downloaded
            # This ensures no job hits a 45-second timeout because of cold-start downloads
            queue_manager.start_workers()
            logger.info(json.dumps({"event": "workers_started"}))

    # Run warmup asynchronously so the server binds the port instantly and accepts requests
    asyncio.create_task(model_warmup())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(json.dumps({"event": "shutdown_initiated"}))
    for task in queue_manager.workers:
        task.cancel()
    if queue_manager.cleanup_task:
        queue_manager.cleanup_task.cancel()

def get_model_manager():
    return ModelManager()

@app.post("/scan")
async def scan(req: ScanRequest):
    # Payload bounds checking (Max 10MB approx)
    if len(req.imageBase64) > 15_000_000:
        raise HTTPException(status_code=413, detail="Payload Too Large. Max size is ~10MB.")
    try:
        b64_data = req.imageBase64
        if b64_data.startswith("data:image"):
            parts = b64_data.split(",")
            if len(parts) > 1:
                b64_data = parts[1]
        import base64
        import binascii
        base64.b64decode(b64_data, validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid base64 payload")
        
    job_id = "job_" + str(int(time.time() * 1000))
    logger.info(json.dumps({"event": "scan_requested", "job_id": job_id}))
    
    try:
        await queue_manager.add_job(job_id, req.imageBase64)
    except Exception as e:
        if "Queue is full" in str(e):
            raise HTTPException(status_code=429, detail="Too Many Requests. Queue is full.")
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"job_id": job_id, "status": "queued"}

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    res = queue_manager.get_result(job_id)
    if not res:
        return {
            "id": job_id,
            "status": "error",
            "message": "Job not found",
            "result": {
                "riskLevel": "low",
                "detections": [],
                "image": ""
            }
        }
        
    status = res.get("status", "error")
    
    if status in ["queued", "processing"]:
        return {
            "id": job_id,
            "status": status,
            "message": res.get("message", "Processing"),
            "result": None
        }
    elif status == "completed":
        return {
            "id": job_id,
            "status": "completed",
            "message": "Success",
            "result": {
                "riskLevel": res.get("risk_level", "low").lower(),
                "detections": res.get("detections", []),
                "image": res.get("image", ""),
                "processingTime": res.get("processing_time", 0)
            }
        }
    else:
        return {
            "id": job_id,
            "status": "error",
            "message": res.get("message", "Unknown error"),
            "result": {
                "riskLevel": "low",
                "detections": [],
                "image": ""
            }
        }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/status")
async def status():
    is_warming_up = len(queue_manager.workers) == 0
    return {"status": "warming_up" if is_warming_up else "running", "uptime_info": "ok"}

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
