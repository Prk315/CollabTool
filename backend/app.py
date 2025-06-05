# backend/app.py
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from backend.reminder import deadline_reminder_job
from backend.db import get_db_connection

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")  # needed for flash()

# --- register blueprints ---
from backend.routes import users, groups, projects, availability, schedule, calendar, ics_upload

app.register_blueprint(users.bp)
app.register_blueprint(groups.bp)
app.register_blueprint(projects.bp)
app.register_blueprint(availability.bp)
app.register_blueprint(schedule.bp)
app.register_blueprint(calendar.bp)
app.register_blueprint(ics_upload.bp)   # ← already present but keep this


@app.route("/")
def home():
    return render_template('home.html')

# ------------ Health Check and Status Endpoints ----------------------
@app.route("/status")
def status():
    """Simple status endpoint to check if the app is running"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route("/db-check")
def db_check():
    """Check database connectivity"""
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            return jsonify({"status": "ok", "database": "connected"})
        else:
            return jsonify({"status": "error", "database": "connection failed"}), 503
    except Exception as e:
        app.logger.error(f"Database connection error: {e}")
        return jsonify({
            "status": "error", 
            "database": "connection failed",
            "message": str(e)
        }), 503

# ------------ Error Handlers ----------------------------------------
@app.errorhandler(500)
def handle_500(e):
    app.logger.error(f"500 error: {e}")
    return render_template('error.html', 
                          error="Internal Server Error", 
                          message="The server encountered an unexpected error. Database might be unavailable."), 500

@app.errorhandler(404)
def handle_404(e):
    return render_template('error.html', 
                          error="Page Not Found", 
                          message="The requested page does not exist."), 404

# ---------------- start background scheduler -------------------
if os.environ.get("WERKZEUG_RUN_MAIN") == "true":  # avoid double start under reloader
    try:
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(deadline_reminder_job, "interval", hours=1,
                        next_run_time=datetime.utcnow())  # run immediately once
        scheduler.start()
        app.logger.info("Background scheduler started successfully")
    except Exception as e:
        app.logger.error(f"Failed to start background scheduler: {e}")