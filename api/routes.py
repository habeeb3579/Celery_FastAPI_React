import uuid
from typing import Any, Callable
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from celery.result import AsyncResult

from tasks.training import train_model
from tasks.prediction import predict, batch_predict, explain_prediction
from ml.trainer import DATASETS, MODELS


# ══════════════════════════════════════════════════════════════
# 1. CONSTANTS — seconds
# ══════════════════════════════════════════════════════════════

PREDICTION_TIMEOUT = 10   # seconds
MODEL_INFO_TIMEOUT = 5


# ══════════════════════════════════════════════════════════════
# 2. MODELS — Pydantic models for request validation and docs
# ══════════════════════════════════════════════════════════════

class TrainRequest(BaseModel):
    dataset:      str   = Field("iris",          description=f"One of: {list(DATASETS.keys())}")
    model_type:   str   = Field("random_forest", description=f"One of: {list(MODELS.keys())}")
    model_params: dict  = Field(default_factory=dict)
    test_size:    float = Field(0.2, ge=0.05, le=0.5)
    cv_folds:     int   = Field(5,   ge=2,    le=10)
    scale:        bool  = Field(True)


class PredictRequest(BaseModel):
    input_data: Any = Field(
        ...,
        description=(
            "One of: "
            "(1) named dict {'sepal length (cm)': 5.1, ...}, "
            "(2) {'features': [5.1, 3.5, 1.4, 0.2]}, "
            "(3) plain list [5.1, 3.5, 1.4, 0.2]"
        ),
    )


class BatchPredictRequest(BaseModel):
    inputs: list = Field(..., description="List of input_data items")


# ══════════════════════════════════════════════════════════════
# 3. STATE RESOLUTION — mapping Celery states to API response data
#
#    We define what each state *contributes* as pure data.
#    A single resolver merges base + extra into the response.
#
#    Each value is either:
#      - a dict    → merged directly
#      - a lambda  → called with (result) to get the extra data
# ══════════════════════════════════════════════════════════════

# Training-specific state extras (job_id is part of base, passed separately)
TRAINING_STATE_EXTRAS: dict[str, dict | Callable] = {
    "PENDING":  {"state": "pending"},
    "PROGRESS": lambda r: {"state": "running",  **r.info},
    "SUCCESS":  lambda r: {"state": "success",  "model_type":  r.get().get("model_type"),
                                                "dataset":     r.get().get("dataset"),
                                                "metrics":     r.get().get("metrics"),
                                                "model_path":  r.get().get("model_path")},
    "FAILURE":  lambda r: {"state": "failed",   "error": str(r.info)},
}

# Generic state extras (no job_id — used for /result/{task_id})
GENERIC_STATE_EXTRAS: dict[str, dict | Callable] = {
    "PENDING":  {"state": "pending"},
    "PROGRESS": lambda r: {"state": "running",  **r.info},
    "SUCCESS":  lambda r: {"state": "success",  "result": r.get()},
    "FAILURE":  lambda r: {"state": "failed",   "error": str(r.info)},
}


def _resolve(result: AsyncResult, extras: dict, base: dict) -> dict:
    """
    Merge base dict with state-specific extra data.
    Single resolver replaces all individual handler functions.
    """
    extra     = extras.get(result.state, {"state": result.state})
    extra_data = extra(result) if callable(extra) else extra
    return {**base, **extra_data}


# ══════════════════════════════════════════════════════════════
# 4. HELPER FUNCTIONS — DRY patterns extracted once
# ══════════════════════════════════════════════════════════════

def _run_task_and_wait(task, timeout: int) -> dict:
    """
    Wait up to `timeout` seconds for a Celery task.
    Falls back to async polling response if it takes too long.
    """
    try:
        return task.get(timeout=timeout)
    except Exception:
        return {
            "task_id":  task.id,
            "status":   "queued",
            "poll_url": f"/result/{task.id}",
        }


def _resolve_training(job_id: str, result: AsyncResult) -> dict:
    """Resolve training job state — includes job_id and predict_url on success."""
    base = {"job_id": job_id}
    if result.state == "SUCCESS":
        base["predict_url"] = f"/predict/{job_id}"
    return _resolve(result, TRAINING_STATE_EXTRAS, base)


def _resolve_generic(result: AsyncResult) -> dict:
    """Resolve any task state — no job context needed."""
    return _resolve(result, GENERIC_STATE_EXTRAS, {})


# ══════════════════════════════════════════════════════════════
# 5. APP — clean, thin routes with zero business logic
# ══════════════════════════════════════════════════════════════

app = FastAPI(
    title="Celery ML API",
    description="ML training and prediction with Celery + scikit-learn",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# ── Info ───────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
async def root():
    return {
        "service":            "Celery ML API",
        "docs":               "/docs",
        "available_datasets": {k: v["description"] for k, v in DATASETS.items()},
        "available_models":   list(MODELS.keys()),
    }


@app.get("/health", tags=["Info"])
async def health():
    return {"status": "ok"}


# ── Training ───────────────────────────────────────────────────

@app.post("/train", tags=["Training"])
async def start_training(req: TrainRequest):
    """Submit an async training job. Returns job_id to poll for status."""
    job_id = str(uuid.uuid4())
    task   = train_model.apply_async(args=[job_id, req.dict()], task_id=job_id)

    return {
        "job_id":     job_id,
        "task_id":    task.id,
        "status":     "queued",
        "dataset":    req.dataset,
        "model_type": req.model_type,
        "poll_url":   f"/train/{job_id}/status",
    }


@app.get("/train/{job_id}/status", tags=["Training"])
async def get_training_status(job_id: str):
    """Poll training job status and live progress."""
    return _resolve_training(job_id, AsyncResult(job_id))


# ── Prediction ─────────────────────────────────────────────────

@app.post("/predict/{model_id}", tags=["Prediction"])
async def make_prediction(model_id: str, req: PredictRequest):
    """Single prediction — waits up to 10s, then falls back to async."""
    task = predict.apply_async(args=[model_id, req.input_data])
    return _run_task_and_wait(task, PREDICTION_TIMEOUT)


@app.post("/predict/{model_id}/batch", tags=["Prediction"])
async def batch_prediction(model_id: str, req: BatchPredictRequest):
    """Async batch prediction for large input sets."""
    task = batch_predict.apply_async(args=[model_id, req.inputs])
    return {
        "task_id":  task.id,
        "status":   "queued",
        "count":    len(req.inputs),
        "poll_url": f"/result/{task.id}",
    }


@app.post("/predict/{model_id}/explain", tags=["Prediction"])
async def explain(model_id: str, req: PredictRequest):
    """Prediction + feature importances for tree models."""
    task = explain_prediction.apply_async(args=[model_id, req.input_data])
    return _run_task_and_wait(task, PREDICTION_TIMEOUT)


@app.get("/model/{model_id}/info", tags=["Prediction"])
async def model_info(model_id: str):
    """Return metadata about a trained model."""
    task   = explain_prediction.apply_async(args=[model_id, None], kwargs={"info_only": True})
    result = _run_task_and_wait(task, MODEL_INFO_TIMEOUT)

    if "task_id" in result:
        # timed out — model probably doesn't exist
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    return result


# ── Generic result polling ─────────────────────────────────────

@app.get("/result/{task_id}", tags=["Tasks"])
async def get_result(task_id: str):
    """Poll any async task by task_id."""
    return _resolve_generic(AsyncResult(task_id))