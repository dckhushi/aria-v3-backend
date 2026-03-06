# tools/calendar_tool.py
# Google Calendar integration — create, list, search events

import os
import json
from datetime import datetime, timedelta
import re

def _get_service():
    """Build Google Calendar service. Uses credentials from env or file."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

        if creds_json:
            # Railway/production: credentials stored as JSON string in env var
            info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/calendar"]
            )
        elif os.path.exists(creds_path):
            # Local development: credentials file
            creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=["https://www.googleapis.com/auth/calendar"]
            )
        else:
            return None, "No Google credentials found. Set GOOGLE_CREDENTIALS_JSON env var."

        service = build("calendar", "v3", credentials=creds)
        return service, None

    except Exception as e:
        return None, str(e)


def create_event(title: str, date_str: str, time_str: str = "10:00",
                 duration_minutes: int = 60, description: str = "",
                 calendar_id: str = None) -> dict:
    """
    Create a Google Calendar event.
    date_str: 'YYYY-MM-DD' or natural like 'tomorrow', '2025-12-25'
    time_str: 'HH:MM' (24h)
    """
    service, err = _get_service()
    if err:
        return {"success": False, "error": err,
                "mock": True,
                "message": f"[MOCK] Would create: '{title}' on {date_str} at {time_str}"}

    try:
        calendar_id = calendar_id or os.getenv("GOOGLE_CALENDAR_ID", "primary")

        # Parse date
        start_dt = _parse_datetime(date_str, time_str)
        end_dt   = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary":     title,
            "description": description or f"Created by ARIA v3 Agent",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
            "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Kolkata"},
        }

        created = service.events().insert(calendarId=calendar_id, body=event).execute()
        return {
            "success":    True,
            "event_id":   created.get("id"),
            "event_link": created.get("htmlLink"),
            "title":      title,
            "start":      start_dt.strftime("%B %d, %Y at %I:%M %p"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def list_events(days_ahead: int = 7, max_results: int = 10,
                calendar_id: str = None) -> dict:
    """List upcoming calendar events."""
    service, err = _get_service()
    if err:
        return {"success": False, "error": err,
                "mock": True, "events": [
                    {"title": "Team Standup", "start": "Tomorrow 9:00 AM"},
                    {"title": "Project Review", "start": "Friday 2:00 PM"},
                ]}

    try:
        calendar_id = calendar_id or os.getenv("GOOGLE_CALENDAR_ID", "primary")
        now     = datetime.utcnow().isoformat() + "Z"
        end     = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

        result = service.events().list(
            calendarId=calendar_id,
            timeMin=now, timeMax=end,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = []
        for e in result.get("items", []):
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            events.append({
                "title": e.get("summary", "No title"),
                "start": start,
                "link":  e.get("htmlLink", "")
            })

        return {"success": True, "events": events, "count": len(events)}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _parse_datetime(date_str: str, time_str: str) -> datetime:
    """Parse date string into datetime object."""
    today = datetime.now()
    date_str = date_str.lower().strip()

    if date_str in ("today",):
        base = today
    elif date_str in ("tomorrow",):
        base = today + timedelta(days=1)
    elif date_str.startswith("next "):
        day_name = date_str.replace("next ", "")
        days = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,
                "friday":4,"saturday":5,"sunday":6}
        target = days.get(day_name, 0)
        current = today.weekday()
        delta = (target - current) % 7 or 7
        base = today + timedelta(days=delta)
    else:
        try:
            base = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            base = today + timedelta(days=1)  # fallback: tomorrow

    # Parse time
    try:
        t = datetime.strptime(time_str, "%H:%M")
        return base.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    except:
        return base.replace(hour=10, minute=0, second=0, microsecond=0)
