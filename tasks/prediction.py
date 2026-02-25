import time
from celery.utils.log import get_task_logger
from celery_app import celery_app
from ml.predictor import ModelPredictor

logger = get_task_logger(__name__)


# ══════════════════════════════════════════════════════════════
# 1. CONSTANTS
# ══════════════════════════════════════════════════════════════

RETRY_BASE_COUNTDOWN = 2   # seconds, doubles on each retry


# ══════════════════════════════════════════════════════════════
# 2. MODEL CACHE — setdefault replaces manual if-not-in pattern
# ══════════════════════════════════════════════════════════════

_model_cache: dict[str, ModelPredictor] = {}


def get_model(model_id: str) -> ModelPredictor:
    """Cache models in worker memory — avoids reloading on every request."""
    if model_id not in _model_cache:
        logger.info(f"Loading model '{model_id}' into worker cache")
        _model_cache[model_id] = ModelPredictor.load(model_id)
    return _model_cache[model_id]


# ══════════════════════════════════════════════════════════════
# 3. shared response builder + timing helper
#    predict() and batch_predict() both built the same
#    base dict with model_id, dataset, model_type, latency_ms
#    Extracted once, used everywhere
# ══════════════════════════════════════════════════════════════

def _base_response(model: ModelPredictor, model_id: str, start: float) -> dict:
    """Common fields shared by all prediction responses."""
    return {
        "status":     "success",
        "model_id":   model_id,
        "dataset":    model.dataset_name,
        "model_type": model.model_type,
        "latency_ms": _elapsed_ms(start),
    }


def _elapsed_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


def _retry_countdown(retries: int) -> int:
    return RETRY_BASE_COUNTDOWN ** retries


# ══════════════════════════════════════════════════════════════
# 4. explain dispatch replaces if info_only branch
#    Each action is a named function, independently testable
# ══════════════════════════════════════════════════════════════

def _run_explain(model: ModelPredictor, model_id: str, input_data) -> dict:
    return {"status": "success", "model_id": model_id, **model.explain(input_data)}


def _run_info(model: ModelPredictor, model_id: str, input_data) -> dict:
    return model.model_info()


EXPLAIN_ACTIONS: dict[bool, callable] = {
    False: _run_explain,
    True:  _run_info,
}


# ══════════════════════════════════════════════════════════════
# 5. TASKS — thin, delegate to helpers above
# ══════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    queue="prediction",
    name="tasks.prediction.predict",
    max_retries=3,
    soft_time_limit=30,
    time_limit=60,
)
def predict(self, model_id: str, input_data):
    start = time.time()
    try:
        model = get_model(model_id)
        return {**_base_response(model, model_id, start), **model.predict(input_data)}
    except Exception as exc:
        logger.error(f"Prediction failed for model '{model_id}': {exc}")
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@celery_app.task(
    queue="prediction",
    name="tasks.prediction.batch_predict",
    soft_time_limit=120,
    time_limit=180,
)
def batch_predict(model_id: str, batch: list):
    start       = time.time()
    model       = get_model(model_id)
    predictions = model.predict_batch(batch)
    return {
        **_base_response(model, model_id, start),
        "count":       len(predictions),
        "predictions": predictions,
    }


@celery_app.task(
    bind=True,
    queue="prediction",
    name="tasks.prediction.explain_prediction",
    max_retries=3,
    soft_time_limit=30,
    time_limit=60,
)
def explain_prediction(self, model_id: str, input_data, info_only: bool = False):
    try:
        model  = get_model(model_id)
        action = EXPLAIN_ACTIONS[info_only]
        return action(model, model_id, input_data)
    except Exception as exc:
        logger.error(f"Explain failed for model '{model_id}': {exc}")
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))