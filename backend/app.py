from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Flask app instance
app = Flask(__name__)

# Register route blueprints
from backend.routes import users, groups, projects, availability, schedule
app.register_blueprint(users.bp)
app.register_blueprint(groups.bp)
app.register_blueprint(projects.bp)
app.register_blueprint(availability.bp)
app.register_blueprint(schedule.bp)




# Basic home route
@app.route('/')
def home():
    return '''
        <h1>Welcome to the Student Collaboration Tool</h1>
        <ul>
            <li><a href="/users/">Users</a></li>
            <li><a href="/groups/">Groups</a></li>
            <li><a href="/projects/">Projects</a></li>
        </ul>
    '''
