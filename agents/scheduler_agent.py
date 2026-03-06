"""
ARIA v3 — Scheduler Agent
Uses APScheduler to run recurring research jobs
e.g. "Send me AI news every morning at 8am"
"""

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from agents.research_agent import run_research
from tools.telegram_client import send_research_report
from tools.groq_client import simple_chat
import json
import re


def parse_schedule_request(user_text: str) -> dict:
    """
    Use Groq to parse a schedule request into job config.
    e.g. "Send me AI news every morning at 8am"
    """
    prompt = f"""Parse this scheduling request into a JSON job config.
Request: "{user_text}"

Return ONLY valid JSON:
{{
  "query": "what to research",
  "frequency": "daily|hourly|weekly",
  "hour": 8,
  "minute": 0,
  "day_of_week": "mon-fri or *",
  "description": "human readable description"
}}

Examples:
- "AI news every morning at 8am" → frequency=daily, hour=8, minute=0, query="latest AI news"
- "stock market update every weekday at 9am" → frequency=weekly (mon-fri), hour=9
- "weather report every 6 hours" → frequency=interval (hours=6)"""

    response = simple_chat(
        system="You are a schedule parser. Return only valid JSON.",
        user=prompt
    )

    match = re.search(r"\{.*\}", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return {"error": "Could not parse schedule"}


def create_research_job(scheduler, query: str, frequency: str,
                         hour: int = 8, minute: int = 0,
                         day_of_week: str = "*", job_id: str = None) -> dict:
    """
    Create a scheduled research job.
    """
    job_id = job_id or f"aria_job_{query[:20].replace(' ', '_')}"

    def run_job():
        print(f"\n⏰ Running scheduled job: {query}")
        result = run_research(query)
        send_research_report(
            query=query,
            report=result["report"],
            sources=result["sources"]
        )

    # Remove existing job with same ID
    try:
        scheduler.remove_job(job_id)
    except:
        pass

    # Add new job
    if frequency == "daily":
        trigger = CronTrigger(hour=hour, minute=minute)
    elif frequency == "weekly":
        trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
    elif frequency == "interval":
        trigger = IntervalTrigger(hours=hour or 6)
    else:
        trigger = CronTrigger(hour=hour, minute=minute)

    job = scheduler.add_job(run_job, trigger=trigger, id=job_id, replace_existing=True)

    return {
        "success":     True,
        "job_id":      job_id,
        "query":       query,
        "frequency":   frequency,
        "next_run":    str(job.next_run_time),
        "description": f"Will research '{query}' and send to Telegram"
    }


def list_jobs(scheduler) -> list:
    jobs = scheduler.get_jobs()
    return [
        {
            "id":       j.id,
            "next_run": str(j.next_run_time),
            "trigger":  str(j.trigger)
        }
        for j in jobs
    ]


def remove_job(scheduler, job_id: str) -> dict:
    try:
        scheduler.remove_job(job_id)
        return {"success": True, "message": f"Job {job_id} removed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
