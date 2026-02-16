"""Admin endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.database import get_db
from app.worker.tasks import daily_monitoring_job, generate_daily_report
from app.worker.celery_app import celery_app

router = APIRouter()


@router.post("/trigger-scan")
def trigger_scan(
    current_user = Depends(require_admin),
):
    """Manually trigger monitoring scan."""
    task = daily_monitoring_job.delay()
    return {
        "message": "Scan queued successfully",
        "task_id": task.id,
        "status": "pending",
        "check_status_url": f"/api/admin/task-status/{task.id}"
    }


@router.get("/task-status/{task_id}")
def get_task_status(
    task_id: str,
    current_user = Depends(require_admin),
):
    """Get task status."""
    task = celery_app.AsyncResult(task_id)
    if task.state == "PENDING":
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": "Task is waiting to be processed"
        }
    elif task.state == "PROGRESS":
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": "Task is in progress",
            "current": task.info.get("current", 0),
            "total": task.info.get("total", 0)
        }
    elif task.state == "SUCCESS":
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": "Task completed successfully",
            "result": task.result
        }
    else:  # FAILURE or other states
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": "Task failed",
            "error": str(task.info) if task.info else "Unknown error"
        }
    return response


@router.post("/generate-report")
def trigger_report_generation(
    report_date: str = None,
    current_user = Depends(require_admin),
):
    """Manually trigger report generation."""
    if report_date:
        generate_daily_report.delay(report_date)
        return {"message": f"Report generation triggered for {report_date}"}
    else:
        generate_daily_report.delay()
        return {"message": "Report generation triggered for today"}

