from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "mediageneration",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.media_generation"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)