"""
ARIA v3 — Calendar Agent
Natural language → Google Calendar events
"""

from tools.calendar_client import parse_event_from_text, create_event, list_upcoming_events
from tools.telegram_client import send_calendar_confirmation


def handle_calendar_request(user_text: str, notify_telegram: bool = True) -> dict:
    """
    Full pipeline:
    1. Parse natural language to event fields (Groq)
    2. Create event in Google Calendar
    3. Send Telegram confirmation
    """
    print(f"\n📅 Calendar Agent: {user_text}")

    # Step 1: Parse
    parsed = parse_event_from_text(user_text)
    if "error" in parsed:
        return {"success": False, "error": parsed["error"]}

    # Step 2: Create event
    result = create_event(
        title=parsed.get("title", "ARIA Event"),
        start_time=parsed.get("start_time"),
        end_time=parsed.get("end_time"),
        description=parsed.get("description", ""),
        location=parsed.get("location", "")
    )

    # Step 3: Telegram notification
    if result.get("success") and notify_telegram:
        send_calendar_confirmation(
            event_title=result["title"],
            event_time=f"{result['start']} – {result['end']}",
            event_link=result.get("link")
        )

    return {**result, "parsed": parsed}


def list_events_summary() -> str:
    """Return upcoming events as formatted text."""
    events = list_upcoming_events(max_results=5)
    if not events or "error" in events[0]:
        return "No upcoming events found."

    lines = ["📅 *Upcoming Events:*\n"]
    for e in events:
        lines.append(f"• *{e['title']}* — {e['start']}")

    return "\n".join(lines)
