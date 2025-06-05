from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
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
    return """
    <h1>Student Collaboration Tool</h1>
    <ul>
        <li><a href='/users/'>Users</a></li>
        <li><a href='/groups/'>Groups</a></li>
        <li><a href='/projects/'>Projects</a></li>
        <li><a href='/availability/api/1'>Availabilities (demo)</a></li>
        <li><a href='/calendar/1'>Calendar (User 1 demo)</a></li>
        <li><a href='/ics/upload'>Upload calendar (.ics)</a></li>
    </ul>
    """
