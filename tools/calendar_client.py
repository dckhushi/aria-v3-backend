"""
ARIA v3 — Google Calendar Client
Create, list, and manage calendar events
"""
import os
import json
from datetime import datetime, timedelta
from config import GOOGLE_CREDENTIALS_JSON, GOOGLE_TOKEN_JSON

# Google Calendar uses OAuth2
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("⚠️  Google Calendar libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib")

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    """Authenticate and return Google Calendar service."""
    if not GOOGLE_AVAILABLE:
        raise Exception("Google Calendar libraries not installed")

    creds = None
    token_path = GOOGLE_TOKEN_JSON or "token.json"
    creds_path = GOOGLE_CREDENTIALS_JSON or "credentials.json"

    # Load existing token
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh or create new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(creds_path):
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise Exception("No Google credentials found. Add credentials.json")

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_event(title: str, start_time: str, end_time: str = None,
                 description: str = "", location: str = "") -> dict:
    """
    Create a Google Calendar event.
    start_time: ISO format string e.g. '2025-03-10T15:00:00'
    end_time:   ISO format string (default: 1 hour after start)
    """
    try:
        service = get_calendar_service()

        # Parse and set end time
        start_dt = datetime.fromisoformat(start_time)
        if end_time:
            end_dt = datetime.fromisoformat(end_time)
        else:
            end_dt = start_dt + timedelta(hours=1)

        # Get local timezone
        import subprocess
        try:
            tz = subprocess.check_output(["date", "+%Z"]).decode().strip()
        except:
            tz = "Asia/Kolkata"  # Default for India

        event_body = {
            "summary":     title,
            "description": description,
            "location":    location,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Asia/Kolkata"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Kolkata"
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup",  "minutes": 30},
                    {"method": "email",  "minutes": 60}
                ]
            }
        }

        event = service.events().insert(calendarId="primary", body=event_body).execute()

        return {
            "success":   True,
            "event_id":  event.get("id"),
            "title":     title,
            "start":     start_dt.strftime("%B %d, %Y at %I:%M %p"),
            "end":       end_dt.strftime("%I:%M %p"),
            "link":      event.get("htmlLink"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def list_upcoming_events(max_results: int = 10) -> list:
    """
    List upcoming calendar events.
    """
    try:
        service = get_calendar_service()
        now = datetime.utcnow().isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        result = []

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            result.append({
                "id":          event.get("id"),
                "title":       event.get("summary", "No title"),
                "start":       start,
                "description": event.get("description", ""),
                "link":        event.get("htmlLink", "")
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]


def parse_event_from_text(text: str) -> dict:
    """
    Use Groq to parse natural language into event fields.
    e.g. "Schedule a meeting tomorrow at 3pm with John about project"
    """
    from tools.groq_client import simple_chat
    from datetime import date

    today = date.today().isoformat()
    prompt = f"""Today is {today}. Parse this text into a calendar event JSON.
Text: "{text}"

Return ONLY valid JSON with these fields:
{{
  "title": "event title",
  "start_time": "YYYY-MM-DDTHH:MM:00",
  "end_time": "YYYY-MM-DDTHH:MM:00",
  "description": "any details",
  "location": "location if mentioned"
}}

If time is ambiguous, default to 10:00 AM. Use today's date for 'today', tomorrow for 'tomorrow', etc."""

    response = simple_chat(
        system="You are a calendar event parser. Return only valid JSON.",
        user=prompt
    )

    # Extract JSON from response
    import re
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return {"error": "Could not parse event from text"}
