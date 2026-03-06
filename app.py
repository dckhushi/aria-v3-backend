"""
ARIA v3 — Flask Backend
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

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
def index():
    return {"status": "online", "version": "3.0.0", "name": "ARIA v3"}

@app.route("/ping")
def ping():
    return {"pong": True}

@app.route("/debug")
def debug():
    key = os.environ.get("OPENROUTER_API_KEY", "")
    tg  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return {
        "openrouter_key_set":    bool(key),
        "openrouter_key_prefix": key[:10] + "..." if key else "NOT SET",
        "telegram_set":          bool(tg),
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)