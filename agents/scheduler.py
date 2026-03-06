# agents/scheduler.py
# APScheduler — runs daily/weekly automated ARIA research jobs

import os
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

_scheduler = None
_jobs_store = {}  # in-memory job config: {job_id: config}

def get_scheduler():
    global _scheduler
    if _scheduler is None:
        jobstores  = {"default": MemoryJobStore()}
        executors  = {"default": ThreadPoolExecutor(4)}
        _scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)
        _scheduler.start()
        print("[Scheduler] Started ✓")
    return _scheduler


def add_research_job(job_id: str, query: str, cron_hour: int = 8,
                     cron_minute: int = 0, groq_key: str = None) -> dict:
    """
    Add a daily research job.
    Runs every day at cron_hour:cron_minute and sends results to Telegram.
    """
    from agents.aria_agent import run_agent

    scheduler = get_scheduler()

    # Remove existing job with same ID
    try:
        scheduler.remove_job(job_id)
    except:
        pass

    groq_key = groq_key or os.getenv("GROQ_API_KEY")

    def job_fn():
        print(f"[Scheduler] Running job '{job_id}': {query}")
        try:
            result = run_agent(
                query=f"{query} (latest news and updates as of today)",
                groq_api_key=groq_key
            )
            print(f"[Scheduler] Job '{job_id}' done. Telegram: {result.get('telegramSent')}")
        except Exception as e:
            print(f"[Scheduler] Job '{job_id}' ERROR: {e}")
            from tools.telegram_tool import send_message
            send_message(f"⚠️ ARIA Scheduler error for job '{job_id}':\n{str(e)}")

    scheduler.add_job(
        job_fn,
        trigger="cron",
        hour=cron_hour,
        minute=cron_minute,
        id=job_id,
        replace_existing=True,
        misfire_grace_time=300
    )

    _jobs_store[job_id] = {
        "id":       job_id,
        "query":    query,
        "schedule": f"Daily at {cron_hour:02d}:{cron_minute:02d}",
        "created":  datetime.now().isoformat()
    }

    print(f"[Scheduler] Job '{job_id}' scheduled: daily at {cron_hour:02d}:{cron_minute:02d}")
    return {"success": True, "job_id": job_id, "schedule": f"Daily at {cron_hour:02d}:{cron_minute:02d}"}


def remove_job(job_id: str) -> dict:
    try:
        get_scheduler().remove_job(job_id)
        _jobs_store.pop(job_id, None)
        return {"success": True, "job_id": job_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_jobs() -> list:
    return list(_jobs_store.values())


def run_job_now(job_id: str) -> dict:
    """Immediately trigger a scheduled job."""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    if not job:
        return {"success": False, "error": f"Job '{job_id}' not found"}
    job.func()
    return {"success": True, "job_id": job_id}


def setup_default_jobs():
    """Set up default example jobs on startup (can be disabled)."""
    pass  # Add default jobs here if needed
