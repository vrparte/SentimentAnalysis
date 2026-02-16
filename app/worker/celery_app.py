"""Celery application configuration."""

import logging
from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "director_monitoring",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.timezone,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    # Import tasks when worker starts
    imports=("app.worker.tasks",),
)

# Parse run time (HH:MM format)
try:
    run_hour, run_minute = map(int, settings.run_time_hhmm.split(":"))
except Exception:
    run_hour, run_minute = 7, 30

# Celery Beat schedule
# Note: timezone is set globally in celery_app.conf.timezone above
celery_app.conf.beat_schedule = {
    "daily-monitoring": {
        "task": "app.worker.tasks.daily_monitoring_job",
        "schedule": crontab(hour=run_hour, minute=run_minute),
    },
    "weekly-cleanup": {
        "task": "app.worker.tasks.cleanup_old_data",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2 AM
    },
}

# Import tasks to register them
# This ensures tasks are discovered when the module is loaded
from app.worker import tasks  # noqa: E402, F401
