"""
ARIA v3 — Agentic Research Intelligence Assistant
Flask Backend — Main Entry Point
"""

from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import os

from routes.research  import research_bp
from routes.telegram  import telegram_bp
from routes.calendar  import calendar_bp
from routes.scheduler import scheduler_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(research_bp,  url_prefix="/api/research")
app.register_blueprint(telegram_bp,  url_prefix="/api/telegram")
app.register_blueprint(calendar_bp,  url_prefix="/api/calendar")
app.register_blueprint(scheduler_bp, url_prefix="/api/scheduler")

scheduler = BackgroundScheduler()
scheduler.start()
app.config["SCHEDULER"] = scheduler

@app.route("/")
def health():
    return {
        "status": "online",
        "version": "3.0.0",
        "name": "ARIA — Agentic Research Intelligence Assistant",
        "endpoints": ["/api/research", "/api/telegram", "/api/calendar", "/api/scheduler"]
    }

@app.route("/ping")
def ping():
    return {"pong": True}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n ARIA v3 Backend running on port {port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)


@app.route("/debug")
def debug():
    """Check what env vars are actually loaded on the server."""
    import os
    key = os.environ.get("OPENROUTER_API_KEY", "")
    tg  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return {
        "openrouter_key_set":    bool(key),
        "openrouter_key_prefix": key[:8] + "..." if key else "NOT SET",
        "openrouter_key_length": len(key),
        "telegram_set":    bool(tg),
        "telegram_prefix": tg[:10] + "..." if tg else "NOT SET",
    }
