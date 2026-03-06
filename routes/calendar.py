"""
ARIA v3 — Calendar Routes
POST /api/calendar/create    → create event from natural language
GET  /api/calendar/events    → list upcoming events
"""

from flask import Blueprint, request, jsonify
from agents.calendar_agent import handle_calendar_request, list_events_summary
from tools.calendar_client import list_upcoming_events

calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/create", methods=["POST"])
def create():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    notify = data.get("notify_telegram", True)

    if not text:
        return jsonify({"error": "text is required"}), 400

    result = handle_calendar_request(text, notify_telegram=notify)
    return jsonify(result)


@calendar_bp.route("/events", methods=["GET"])
def events():
    max_results = int(request.args.get("max", 10))
    events = list_upcoming_events(max_results=max_results)
    return jsonify({"events": events})
