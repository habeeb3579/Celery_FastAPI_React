from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from celery_app import celery_app
from ml.trainer import ModelTrainer
import traceback

logger = get_task_logger(__name__)


# ══════════════════════════════════════════════════════════════
# 1. CONSTANTS — no magic numbers inline
# ══════════════════════════════════════════════════════════════

PROGRESS_TRAINING_START = 10   # % progress when training begins
PROGRESS_SAVING         = 90   # % progress when saving begins
RETRY_BASE_COUNTDOWN    = 60   # seconds, doubles on each retry


# ══════════════════════════════════════════════════════════════
# 2. progress reporting as pure data
#    update_state was called 3x with repetitive dicts
#    One helper replaces all three call sites
# ══════════════════════════════════════════════════════════════

def _progress(task, job_id: str, stage: str, progress: int, **extra):
    """Emit a PROGRESS state update — single source of truth."""
    task.update_state(
        state="PROGRESS",
        meta={"stage": stage, "progress": progress, "job_id": job_id, **extra},
    )


def _calc_epoch_progress(epoch: int, total_epochs: int) -> int:
    """Map epoch number to a progress percentage between 10–90."""
    return int((epoch / total_epochs) * 80) + PROGRESS_TRAINING_START


# ══════════════════════════════════════════════════════════════
# 3. epoch callback lifted out of the task function
#    Nested functions make code hard to read and test.
#    This is now a standalone named function.
# ══════════════════════════════════════════════════════════════

def _make_epoch_callback(task, job_id: str):
    """
    Returns an epoch callback bound to this task + job_id.
    Lifted out of train_model so it is independently readable.
    """
    def on_epoch_end(epoch: int, total_epochs: int, metrics: dict):
        _progress(
            task, job_id,
            stage    = "training",
            progress = _calc_epoch_progress(epoch, total_epochs),
            epoch    = epoch,
            metrics  = metrics,
        )
    return on_epoch_end


# ══════════════════════════════════════════════════════════════
# 4. TASK — now just orchestrates, no inline logic
# ══════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    queue="training",
    name="tasks.training.train_model",
    max_retries=2,
    soft_time_limit=7200,
    time_limit=7500,
)
def train_model(self, job_id: str, config: dict):
    """Long-running training task with live progress updates."""
    logger.info(f"Starting training job {job_id}")
    trainer = ModelTrainer(config)

    try:
        _progress(self, job_id, stage="loading_data", progress=0)
        trainer.load_data()

        _progress(self, job_id, stage="training", progress=PROGRESS_TRAINING_START)
        result = trainer.train(epoch_callback=_make_epoch_callback(self, job_id))

        _progress(self, job_id, stage="saving", progress=PROGRESS_SAVING)
        model_path = trainer.save(job_id)

        return {
            "status":     "success",
            "job_id":     job_id,
            "model_path": model_path,
            "metrics":    result["metrics"],
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Training job {job_id} timed out")
        trainer.cleanup()
        raise

    except Exception as exc:
        logger.error(f"Training failed:\n{traceback.format_exc()}")
        raise self.retry(exc=exc, countdown=RETRY_BASE_COUNTDOWN * (2 ** self.request.retries))