from celery import Celery
from kombu import Queue
from config import config


def create_celery_app():
    app = Celery("ml_project")

    app.conf.update(
        broker_url=config.REDIS_URL, #"redis://redis:6379/0",
        result_backend=config.RESULT_BACKEND, #"redis://redis:6379/1",

        # ── Task discovery — tell workers which modules to import ──
        include=[
            "tasks.training",
            "tasks.prediction",
        ],

        # Serialization
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # Routing
        task_queues=(
            Queue("training", routing_key="training.#"),
            Queue("prediction", routing_key="prediction.#"),
            Queue("default"),
        ),
        task_default_queue="default",

        # Reliability
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_reject_on_worker_lost=True,

        # Limits
        task_soft_time_limit=3600,
        task_time_limit=3900,

        # Results TTL
        result_expires=86400,
    )
    return app


celery_app = create_celery_app()
