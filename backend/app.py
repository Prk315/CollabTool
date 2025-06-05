from flask import Flask, render_template
from dotenv import load_dotenv
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure app with correct template and static folders
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
           static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend/static'))
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# register blueprints
from backend.routes import (
    users,
    groups,
    projects,
    availability_api,
    schedule,
    calendar,
    ics_upload
)

app.register_blueprint(users.bp)
app.register_blueprint(groups.bp)
app.register_blueprint(projects.bp)
app.register_blueprint(availability_api.bp)
app.register_blueprint(schedule.bp)
app.register_blueprint(calendar.bp)
app.register_blueprint(ics_upload.bp)

# APScheduler / reminders (unchanged from before)
from apscheduler.schedulers.background import BackgroundScheduler
from backend.reminder import deadline_reminder_job
from datetime import datetime

if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        deadline_reminder_job,
        "interval",
        hours=1,
        next_run_time=datetime.utcnow()
    )
    scheduler.start()

@app.route("/")
def home():
    try:
        return render_template('home.html')
    except Exception as e:
        logger.error(f"Error rendering home.html: {str(e)}")
        return f"Error loading the home page: {str(e)}", 500
