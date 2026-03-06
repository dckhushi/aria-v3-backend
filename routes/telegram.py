"""
ARIA v3 — Telegram Routes
POST /api/telegram/send      → send custom message
POST /api/telegram/webhook   → receive Telegram messages (bot commands)
GET  /api/telegram/test      → test bot connection
"""

from flask import Blueprint, request, jsonify
from tools.telegram_client import send_message, get_bot_info
from agents.research_agent import run_research
from agents.calendar_agent import handle_calendar_request, list_events_summary
from tools.telegram_client import send_research_report

telegram_bp = Blueprint("telegram", __name__)


@telegram_bp.route("/test", methods=["GET"])
def test():
    info = get_bot_info()
    return jsonify(info)


@telegram_bp.route("/send", methods=["POST"])
def send():
    data = request.get_json() or {}
    text = data.get("text", "")
    chat_id = data.get("chat_id")

    if not text:
        return jsonify({"error": "text is required"}), 400

    result = send_message(text, chat_id=chat_id)
    return jsonify(result)


@telegram_bp.route("/webhook", methods=["POST"])
def webhook():
    """
    Telegram webhook — handles bot commands from users.
    Commands:
      /research <query>   → run research + reply
      /compare <query>    → run comparison
      /calendar <text>    → create calendar event
      /events             → list upcoming events
      /help               → show commands
    """
    update = request.get_json() or {}
    message = update.get("message", {})
    text    = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not text or not chat_id:
        return jsonify({"ok": True})

    # ── Handle commands ────────────────────────────────────────────────────
    if text.startswith("/research "):
        query = text[10:].strip()
        send_message(f"🔍 Researching: *{query}*\n_This may take 20-30 seconds..._", chat_id=chat_id)
        result = run_research(query)
        send_research_report(query=query, report=result["report"], sources=result["sources"], chat_id=chat_id)

    elif text.startswith("/compare "):
        query = text[9:].strip()
        send_message(f"⚖️ Comparing: *{query}*\n_Analyzing sources..._", chat_id=chat_id)
        result = run_research(query, mode="compare")
        send_research_report(query=query, report=result["report"], sources=result["sources"], chat_id=chat_id)

    elif text.startswith("/shop "):
        query = text[6:].strip()
        send_message(f"🛍️ Shopping research: *{query}*\n_Checking prices..._", chat_id=chat_id)
        result = run_research(query, mode="shopping")
        send_research_report(query=query, report=result["report"], sources=result["sources"], chat_id=chat_id)

    elif text.startswith("/factcheck "):
        query = text[11:].strip()
        send_message(f"✅ Fact-checking: *{query}*\n_Verifying..._", chat_id=chat_id)
        result = run_research(query, mode="factcheck")
        send_research_report(query=query, report=result["report"], sources=result["sources"], chat_id=chat_id)

    elif text.startswith("/calendar "):
        event_text = text[10:].strip()
        send_message(f"📅 Creating event: *{event_text}*", chat_id=chat_id)
        result = handle_calendar_request(event_text, notify_telegram=False)
        if result.get("success"):
            msg = f"✅ *Event Created!*\n📌 {result['title']}\n🕐 {result['start']}"
            if result.get("link"):
                msg += f"\n🔗 [Open Calendar]({result['link']})"
        else:
            msg = f"❌ Error: {result.get('error', 'Unknown error')}"
        send_message(msg, chat_id=chat_id)

    elif text == "/events":
        summary = list_events_summary()
        send_message(summary, chat_id=chat_id)

    elif text == "/help" or text == "/start":
        help_text = """🤖 *ARIA v3 — Agentic Research Assistant*
━━━━━━━━━━━━━━━━━━━━
*Commands:*

🔍 `/research <query>` — Deep web research (top 10 sources)
⚖️ `/compare <query>` — Compare products or topics
🛍️ `/shop <product>` — Shopping research & prices
✅ `/factcheck <claim>` — Verify a claim
📅 `/calendar <event>` — Create a calendar event
📋 `/events` — List upcoming events
❓ `/help` — Show this menu

*Examples:*
• `/research climate change solutions 2025`
• `/shop iPhone 16 vs Samsung S25`
• `/calendar meeting tomorrow at 3pm`
• `/factcheck India is the largest democracy`

_Powered by ARIA v3 + Groq + Llama 3.3_"""
        send_message(help_text, chat_id=chat_id)

    else:
        # Natural language fallback — treat as research
        send_message(f"🔍 Researching: *{text}*\n_Processing..._", chat_id=chat_id)
        result = run_research(text)
        send_research_report(query=text, report=result["report"], sources=result["sources"], chat_id=chat_id)

    return jsonify({"ok": True})
