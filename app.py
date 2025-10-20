from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import os
from contextlib import asynccontextmanager

MODEL_PATH = os.getenv("MODEL_PATH", "model/best_pod_failure_model.pkl")



@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"Model not found at {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)
    yield  # App runs here
    # Cleanup (if needed) happens after this line when the app shuts down

app = FastAPI(title="Kubernetes Crash Predictor", lifespan=lifespan)

class Features(BaseModel):
    failure_type: int
    failure_injected: int
    failure_detected: int
    cpu_usage_cores: float
    memory_usage_bytes: float
    disk_io_read_bytes: float
    disk_io_write_bytes: float
    network_rx_bytes: float
    network_tx_bytes: float
    oom_killed: int
    restart_count: int
    latency_ms: float
    container_ready: int
    pod_scheduled: int
    node_cpu_allocatable_cores: float
    node_memory_allocatable_bytes: float

@app.post("/predict")
def predict(features: Features):
    try:
        x = np.array([[
            features.failure_type,
            features.failure_injected,
            features.failure_detected,
            features.cpu_usage_cores,
            features.memory_usage_bytes,
            features.disk_io_read_bytes,
            features.disk_io_write_bytes,
            features.network_rx_bytes,
            features.network_tx_bytes,
            features.oom_killed,
            features.restart_count,
            features.latency_ms,
            features.container_ready,
            features.pod_scheduled,
            features.node_cpu_allocatable_cores,
            features.node_memory_allocatable_bytes
        ]])

        prob = float(model.predict_proba(x)[0, 1])
        will_fail = bool(prob > 0.5)
        return {"probability_of_failure": prob, "will_fail_soon": will_fail}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
