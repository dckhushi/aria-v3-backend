# agents/aria_agent.py
# ARIA v3 — Main Agentic Orchestrator
# Uses Groq (Llama 3.3 70B) with tool-calling loop

import os
import json
from groq import Groq
from tools.web_research import deep_research, format_for_llm
from tools.telegram_tool import send_research_report, send_message, send_calendar_confirmation
from tools.calendar_tool import create_event, list_events

# ── Groq client ───────────────────────────────────────────────────────────────
def get_groq_client(api_key: str = None):
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not set")
    return Groq(api_key=key)

MODEL = "llama-3.3-70b-versatile"

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "deep_web_research",
            "description": (
                "Perform deep web research on any topic. Searches DuckDuckGo, "
                "scrapes the top 10 pages, and returns structured content for analysis. "
                "Use for any research, comparison, product search, news, or fact-finding task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Number of pages to scrape (default 10, max 10)", "default": 10}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_to_telegram",
            "description": "Send the research report or any message to the user's Telegram. Always call this after completing research to deliver results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Full formatted message to send"},
                    "report_type": {"type": "string", "description": "Type: 'research' | 'calendar' | 'general'", "default": "general"}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a Google Calendar event. Use when user says 'schedule', 'remind me', 'add to calendar', 'book a meeting', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":            {"type": "string",  "description": "Event title"},
                    "date":             {"type": "string",  "description": "Date: 'YYYY-MM-DD', 'tomorrow', 'next Monday', etc."},
                    "time":             {"type": "string",  "description": "Time in HH:MM 24h format (e.g. '14:30')"},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes (default 60)"},
                    "description":      {"type": "string",  "description": "Event description/notes"}
                },
                "required": ["title", "date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_calendar_events",
            "description": "List upcoming Google Calendar events. Use when user asks 'what's on my calendar', 'my schedule', 'upcoming events'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "How many days ahead to look (default 7)"}
                }
            }
        }
    }
]

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are ARIA v3, an elite Autonomous Research & Intelligence Agent.

You have access to powerful tools:
1. deep_web_research — Search + scrape top 10 web pages on any topic
2. send_to_telegram — Send results, reports, summaries to the user's Telegram
3. create_calendar_event — Create Google Calendar events
4. list_calendar_events — List upcoming events

BEHAVIOR RULES:
- For ANY research/search task → call deep_web_research first, then analyze the results thoroughly
- After completing research → ALWAYS call send_to_telegram to deliver results to user
- For calendar requests → create/list events AND send confirmation via Telegram
- Be analytical: compare, summarize, rank, find patterns across the scraped sources
- Format reports clearly with sections: Summary, Key Findings, Comparison (if applicable), Recommendation, Sources
- If user asks for shopping (Flipkart, Amazon etc.) → research that product, compare prices/reviews

OUTPUT FORMAT for Telegram (use Markdown):
*ARIA RESEARCH REPORT*
📌 Query: <query>
📊 Sources analyzed: <N>

*Summary*
<2-3 line summary>

*Key Findings*
• Finding 1
• Finding 2

*Analysis / Comparison*
<detailed comparison if multiple products/sources>

*Recommendation*
<clear actionable recommendation>

Always be helpful, concise, and deliver real value from the research."""

# ── Main agent runner ─────────────────────────────────────────────────────────
def run_agent(query: str, groq_api_key: str = None, progress_callback=None) -> dict:
    """
    Run the full ARIA agent pipeline.
    progress_callback(step, message) — optional live updates
    Returns: { finalReport, toolsUsed, telegramSent, calendarEvents }
    """
    client = get_groq_client(groq_api_key)

    def log(step, msg):
        print(f"[ARIA] [{step}] {msg}")
        if progress_callback:
            progress_callback(step, msg)

    log("INIT", f"Starting agent for: {query}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": query}
    ]

    tools_used       = []
    telegram_sent    = False
    calendar_events  = []
    research_data    = None
    iterations       = 0
    max_iterations   = 8

    while iterations < max_iterations:
        iterations += 1
        log("LLM", f"Calling Groq (iteration {iterations})...")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=2048,
            temperature=0.5,
        )

        choice = response.choices[0]
        msg    = choice.message
        messages.append(msg)

        # ── Final answer ──────────────────────────────────────────────────────
        if choice.finish_reason == "stop" or not msg.tool_calls:
            log("DONE", "Agent completed.")
            return {
                "finalReport":    msg.content or "Research complete.",
                "toolsUsed":      tools_used,
                "telegramSent":   telegram_sent,
                "calendarEvents": calendar_events,
                "iterations":     iterations,
                "researchData":   research_data,
            }

        # ── Tool calls ────────────────────────────────────────────────────────
        tool_results = []
        for tc in msg.tool_calls:
            fn   = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            result_content = ""

            log("TOOL", f"Calling: {fn}({list(args.keys())})")

            # ── deep_web_research ─────────────────────────────────────────────
            if fn == "deep_web_research":
                q = args.get("query", query)
                n = min(args.get("max_results", 10), 10)
                log("SRCH", f"Deep research: '{q}' ({n} sources)...")
                data = deep_research(q, n)
                research_data = data
                result_content = format_for_llm(data)
                tools_used.append({"tool": "deep_web_research", "query": q, "sources": data["count"]})
                log("SRCH", f"Scraped {data['count']} pages ✓")

            # ── send_to_telegram ──────────────────────────────────────────────
            elif fn == "send_to_telegram":
                msg_text = args.get("message", "")
                log("TG", "Sending to Telegram...")
                tg_result = send_message(msg_text)
                telegram_sent = tg_result.get("ok", False)
                result_content = f"Telegram: {'sent ✓' if telegram_sent else 'failed — ' + str(tg_result)}"
                tools_used.append({"tool": "send_to_telegram", "sent": telegram_sent})
                log("TG", f"Telegram status: {result_content}")

            # ── create_calendar_event ─────────────────────────────────────────
            elif fn == "create_calendar_event":
                log("CAL", f"Creating event: {args.get('title')}")
                evt = create_event(
                    title=args.get("title", "ARIA Event"),
                    date_str=args.get("date", "tomorrow"),
                    time_str=args.get("time", "10:00"),
                    duration_minutes=args.get("duration_minutes", 60),
                    description=args.get("description", "")
                )
                calendar_events.append(evt)
                tools_used.append({"tool": "create_calendar_event", "event": evt})

                # Auto-notify Telegram
                if evt.get("success") or evt.get("mock"):
                    tg = send_calendar_confirmation(
                        event_title=args.get("title"),
                        date_time=evt.get("start", args.get("date") + " " + args.get("time")),
                        event_link=evt.get("event_link")
                    )
                    telegram_sent = tg.get("ok", False)

                result_content = json.dumps(evt)
                log("CAL", f"Event result: {evt.get('success') or evt.get('mock')}")

            # ── list_calendar_events ──────────────────────────────────────────
            elif fn == "list_calendar_events":
                days = args.get("days_ahead", 7)
                log("CAL", f"Listing events for next {days} days")
                evt_list = list_events(days_ahead=days)
                tools_used.append({"tool": "list_calendar_events"})
                result_content = json.dumps(evt_list)

            tool_results.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result_content or "Done."
            })

        messages.extend(tool_results)

    # Max iterations fallback
    last_text = next((m.content for m in reversed(messages) if hasattr(m, "content") and m.content), "Done.")
    return {
        "finalReport":    last_text,
        "toolsUsed":      tools_used,
        "telegramSent":   telegram_sent,
        "calendarEvents": calendar_events,
        "iterations":     iterations,
        "researchData":   research_data,
    }
