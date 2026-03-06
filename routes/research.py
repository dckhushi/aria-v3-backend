"""
ARIA v3 — Research Routes
POST /api/research/run        → run deep research
POST /api/research/run-send   → run research + send to Telegram
"""

from flask import Blueprint, request, jsonify, current_app
from agents.research_agent import run_research
from tools.telegram_client import send_research_report

research_bp = Blueprint("research", __name__)


@research_bp.route("/run", methods=["POST"])
def run():
    data  = request.get_json() or {}
    query = data.get("query", "").strip()
    mode  = data.get("mode", "research")

    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        result = run_research(query, mode=mode)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@research_bp.route("/run-send", methods=["POST"])
def run_and_send():
    """Run research AND send report to Telegram."""
    data      = request.get_json() or {}
    query     = data.get("query", "").strip()
    mode      = data.get("mode", "research")
    chat_id   = data.get("chat_id")

    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        result = run_research(query, mode=mode)

        tg_result = send_research_report(
            query=query,
            report=result["report"],
            sources=result["sources"],
            chat_id=chat_id
        )

        return jsonify({
            **result,
            "telegram_sent": tg_result.get("ok", False)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
