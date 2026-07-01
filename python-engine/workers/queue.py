import asyncio
from typing import Dict, Any

import time

class AsyncQueueManager:
    def __init__(self, num_workers=2):
        self.queue = asyncio.Queue(maxsize=100)
        self.results: Dict[str, Any] = {}
        self.num_workers = num_workers
        self.workers = []
        self.cleanup_task = None

    async def add_job(self, job_id: str, payload: Any):
        if self.queue.full():
            raise Exception("Queue is full")
        self.results[job_id] = {"status": "queued", "timestamp": time.time()}
        await self.queue.put({"job_id": job_id, "payload": payload})

    def get_result(self, job_id: str):
        return self.results.get(job_id)

    async def _worker_loop(self, worker_id: int):
        from pipeline import execute_pipeline
        while True:
            job = await self.queue.get()
            job_id = job["job_id"]
            payload = job["payload"]
            
            self.results[job_id]["status"] = "processing"
            try:
                # since execute_pipeline has synchronous CPU-bound cv2/torch code
                # Enforce a strict 200-second timeout to prevent permanent hangs
                task = asyncio.to_thread(execute_pipeline, payload)
                b64_out, dets, ptime, risk_level = await asyncio.wait_for(task, timeout=200.0)
                
                self.results[job_id].update({
                    "status": "completed",
                    "image": b64_out,
                    "detections": dets,
                    "processing_time": ptime,
                    "risk_level": risk_level,
                    "worker_id": worker_id
                })
                
                import logging, json
                logger = logging.getLogger("privacy_guardian")
                logger.info(json.dumps({
                    "event": "job_completed",
                    "job_id": job_id,
                    "processing_time_ms": ptime,
                    "risk_level": risk_level,
                    "detections_count": len(dets)
                }))
                
            except asyncio.TimeoutError:
                self.results[job_id].update({"status": "error", "message": "Job timed out after 200 seconds"})
                import logging, json
                logger = logging.getLogger("privacy_guardian")
                logger.error(json.dumps({"event": "job_timeout", "job_id": job_id}))
            except Exception as e:
                self.results[job_id].update({"status": "error", "message": str(e)})
                import logging, json
                logger = logging.getLogger("privacy_guardian")
                logger.error(json.dumps({
                    "event": "job_failed",
                    "job_id": job_id,
                    "error": str(e)
                }))
            finally:
                self.queue.task_done()

    async def _cleanup_loop(self):
        # Run every 5 minutes to clean up results older than 1 hour
        while True:
            await asyncio.sleep(300)
            now = time.time()
            to_delete = []
            for jid, data in self.results.items():
                if "timestamp" in data and now - data["timestamp"] > 3600:
                    to_delete.append(jid)
            for jid in to_delete:
                del self.results[jid]

    def start_workers(self):
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(task)
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    def get_queue_depth(self):
        return self.queue.qsize()

# Singleton instance
queue_manager = AsyncQueueManager(num_workers=2)
