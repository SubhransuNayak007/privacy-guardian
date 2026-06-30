import json
import logging
import os
import time
from datetime import datetime

class ProductionMonitor:
    """
    Stage 14: Production Monitoring
    Logs all failures, anomalies, low-confidence predictions, and OCR failures
    into a structured JSON file to facilitate weekly retraining schedules.
    """
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "production.log")
        
        self.logger = logging.getLogger("ProductionMonitor")
        self.logger.setLevel(logging.INFO)
        
        # Prevent adding multiple handlers if instantiated multiple times
        if not self.logger.handlers:
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def log_event(self, event_type: str, data: dict):
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "data": data
        }
        self.logger.info(json.dumps(payload))

    def log_failure(self, reason: str, exception: str = "", context: dict = None):
        self.log_event("failure", {
            "reason": reason,
            "exception": exception,
            "context": context or {}
        })

    def log_anomaly(self, anomaly_type: str, details: dict):
        self.log_event("anomaly", {
            "anomaly_type": anomaly_type,
            "details": details
        })

monitor = ProductionMonitor()
