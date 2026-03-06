"""
ARIA v3 — Telegram Bot Client
"""
import os
import requests


def _api(endpoint):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return f"https://api.telegram.org/bot{token}/{endpoint}"

def _chat_id():
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def send_message(text: str, chat_id: str = None, parse_mode: str = "Markdown") -> dict:
    cid = chat_id or _chat_id()
    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not cid:
        return {"ok": False, "error": "Telegram not configured"}

    chunks = split_message(text, 4000)
    last = {}
    for chunk in chunks:
        resp = requests.post(_api("sendMessage"), json={
            "chat_id": cid, "text": chunk, "parse_mode": parse_mode
        }, timeout=10)
        last = resp.json()
    return last


def send_research_report(query: str, report: str, sources: list, chat_id: str = None) -> dict:
    header = f"🤖 *ARIA Research Report*\n━━━━━━━━━━━━━━━━━━━━\n🔍 *Query:* `{query}`\n━━━━━━━━━━━━━━━━━━━━\n\n"
    sources_text = "\n\n📚 *Sources:*\n"
    for i, s in enumerate(sources[:8], 1):
        sources_text += f"{i}. [{s.get('title','')[:50]}]({s.get('url','')})\n"
    footer = "\n\n━━━━━━━━━━━━━━━━━━━━\n_Sent by ARIA v3_"
    return send_message(header + report + sources_text + footer, chat_id=chat_id)


def send_calendar_confirmation(event_title, event_time, event_link=None, chat_id=None):
    msg = f"📅 *Event Created!*\n📌 {event_title}\n🕐 {event_time}\n"
    if event_link:
        msg += f"🔗 [Open Calendar]({event_link})\n"
    return send_message(msg, chat_id=chat_id)


def split_message(text, max_len=4000):
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text); break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1: split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    return chunks


def get_bot_info():
    try:
        resp = requests.get(_api("getMe"), timeout=5)
        return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}
