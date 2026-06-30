import asyncio
from typing import Dict, Any

class AsyncQueueManager:
    def __init__(self, num_workers=2):
        self.queue = asyncio.Queue()
        self.results: Dict[str, Any] = {}
        self.num_workers = num_workers
        self.workers = []

    async def add_job(self, job_id: str, payload: Any):
        self.results[job_id] = {"status": "queued"}
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
                # We use asyncio.to_thread to prevent blocking the event loop 
                # since execute_pipeline has synchronous CPU-bound cv2/torch code
                b64_out, dets, ptime = await asyncio.to_thread(execute_pipeline, payload)
                
                self.results[job_id] = {
                    "status": "completed",
                    "image": b64_out,
                    "detections": dets,
                    "processing_time": ptime,
                    "worker_id": worker_id
                }
            except Exception as e:
                self.results[job_id] = {"status": "error", "message": str(e)}
            finally:
                self.queue.task_done()

    def start_workers(self):
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(task)
            
    def get_queue_depth(self):
        return self.queue.qsize()

# Singleton instance
queue_manager = AsyncQueueManager(num_workers=2)
