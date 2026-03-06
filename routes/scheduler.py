"""
ARIA v3 — Scheduler Routes
POST /api/scheduler/create  → create scheduled research job
GET  /api/scheduler/jobs    → list all jobs
DELETE /api/scheduler/jobs/<id> → remove job
"""

from flask import Blueprint, request, jsonify, current_app
from agents.scheduler_agent import (
    parse_schedule_request, create_research_job, list_jobs, remove_job
)

scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.route("/create", methods=["POST"])
def create():
    data = request.get_json() or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "text is required"}), 400

    # Parse with AI
    parsed = parse_schedule_request(text)
    if "error" in parsed:
        return jsonify(parsed), 400

    scheduler = current_app.config["SCHEDULER"]
    result = create_research_job(
        scheduler=scheduler,
        query=parsed.get("query", text),
        frequency=parsed.get("frequency", "daily"),
        hour=parsed.get("hour", 8),
        minute=parsed.get("minute", 0),
        day_of_week=parsed.get("day_of_week", "*")
    )
    return jsonify(result)


@scheduler_bp.route("/jobs", methods=["GET"])
def get_jobs():
    scheduler = current_app.config["SCHEDULER"]
    return jsonify({"jobs": list_jobs(scheduler)})


@scheduler_bp.route("/jobs/<job_id>", methods=["DELETE"])
def delete_job(job_id):
    scheduler = current_app.config["SCHEDULER"]
    result = remove_job(scheduler, job_id)
    return jsonify(result)
