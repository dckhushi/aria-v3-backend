# tools/telegram_tool.py
# Send messages, reports, and formatted results to Telegram

import os
import requests

def _get_config():
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def send_message(text: str, chat_id: str = None, parse_mode: str = "Markdown") -> dict:
    """Send a plain text or Markdown message to Telegram."""
    token, default_chat = _get_config()
    chat_id = chat_id or default_chat

    if not token or not chat_id:
        return {"ok": False, "error": "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"}

    # Telegram has 4096 char limit — split if needed
    chunks = _split_message(text, 4000)
    results = []

    for chunk in chunks:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id":    chat_id,
            "text":       chunk,
            "parse_mode": parse_mode
        }, timeout=10)
        results.append(resp.json())

    return results[-1] if results else {"ok": False}


def send_research_report(query: str, report: str, sources: list[dict] = None) -> dict:
    """Send a beautifully formatted research report to Telegram."""
    lines = [
        "🔬 *ARIA RESEARCH REPORT*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"📌 *Query:* `{query}`",
        "",
        report,
    ]

    if sources:
        lines.append("\n📚 *Sources:*")
        for i, s in enumerate(sources[:5], 1):
            title = s.get("title", "Source")[:50]
            url   = s.get("url", "")
            lines.append(f"{i}\\. [{title}]({url})")

    lines.append("\n_Powered by ARIA v3 · Groq · Llama 3.3_")

    return send_message("\n".join(lines))


def send_calendar_confirmation(event_title: str, date_time: str, event_link: str = None) -> dict:
    """Send calendar event creation confirmation to Telegram."""
    text = (
        f"📅 *Calendar Event Created!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *{event_title}*\n"
        f"🕒 {date_time}\n"
    )
    if event_link:
        text += f"🔗 [View in Google Calendar]({event_link})\n"
    text += "\n_Created by ARIA v3 Agent_"
    return send_message(text)


def send_scheduled_digest(digest: str, digest_type: str = "Daily") -> dict:
    """Send a scheduled digest message."""
    text = (
        f"⏰ *ARIA {digest_type} Digest*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{digest}\n"
        f"\n_Auto-sent by ARIA Scheduler_"
    )
    return send_message(text)


def _split_message(text: str, max_len: int) -> list[str]:
    """Split long messages into chunks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks


def get_chat_id(token: str = None) -> dict:
    """Helper: get your chat ID from the last message sent to the bot."""
    token = token or _get_config()[0]
    if not token:
        return {"error": "No token"}
    url  = f"https://api.telegram.org/bot{token}/getUpdates"
    resp = requests.get(url, timeout=10)
    data = resp.json()
    if data.get("ok") and data.get("result"):
        last = data["result"][-1]
        chat = last.get("message", {}).get("chat", {})
        return {"chat_id": chat.get("id"), "username": chat.get("username")}
    return {"error": "No messages found. Send a message to your bot first."}
