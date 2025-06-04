from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# ---------- DB CONNECTION ----------------------------------------------------
def get_db_connection():
    return psycopg2.connect(
        dbname="collabtool",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host="localhost"
    )

# ---------- HOME -------------------------------------------------------------
@app.route('/')
def home():
    return render_template_string("""
        <h1>Welcome to the Student Collaboration Tool</h1>
        <ul>
          <li><a href="{{ url_for('register') }}">Register user</a></li>
          <li><a href="{{ url_for('list_users') }}">View users</a></li>
          <li><a href="{{ url_for('list_groups') }}">View groups</a></li>
          <li><a href="{{ url_for('list_projects') }}">View projects</a></li>
        </ul>
    """)

# ---------- USERS ------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password)
        )
        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('home'))

    return render_template_string('''
        <h2>Register</h2>
        <form method="POST">
            Username: <input name="username"><br>
            Email: <input name="email" type="email"><br>
            Password: <input name="password" type="password"><br>
            <button type="submit">Register</button>
        </form>
    ''')

@app.route('/users')
def list_users():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT user_id, username, email FROM users ORDER BY user_id;")
    users = cur.fetchall()
    cur.close(); conn.close()

    return render_template_string("""
        <h2>Registered Users</h2>
        <ul>
        {% for uid, uname, mail in users %}
          <li><strong>{{ uid }}</strong> – {{ uname }} ({{ mail }})</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('home') }}">Home</a>
    """, users=users)

# ---------- GROUPS -----------------------------------------------------------
@app.route('/groups')
def list_groups():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT group_id, group_name, description FROM groups ORDER BY group_id;")
    groups = cur.fetchall()
    cur.close(); conn.close()

    return render_template_string("""
        <h2>Groups</h2>
        <ul>
        {% for gid, gname, desc in groups %}
          <li><strong>{{ gid }} – {{ gname }}</strong>{% if desc %}: {{ desc }}{% endif %}</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('create_group') }}">Create new group</a> |
        <a href="{{ url_for('home') }}">Home</a>
    """, groups=groups)

@app.route('/groups/new', methods=['GET', 'POST'])
def create_group():
    if request.method == 'POST':
        name = request.form['group_name']
        desc = request.form['description']

        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO groups (group_name, description) VALUES (%s, %s)",
            (name, desc)
        )
        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('list_groups'))

    return render_template_string("""
        <h2>Create Group</h2>
        <form method="POST">
            Group name: <input name="group_name" required><br>
            Description: <input name="description"><br>
            <button type="submit">Create</button>
        </form>
        <a href="{{ url_for('list_groups') }}">Back to groups</a>
    """)

# ---------- PROJECTS ---------------------------------------------------------
@app.route('/projects')
def list_projects():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT p.project_id, p.project_name, g.group_name, p.deadline, p.estimated_hours_needed
        FROM projects p
        JOIN groups g ON p.group_id = g.group_id
        ORDER BY p.project_id;
    """)
    projects = cur.fetchall()
    cur.close(); conn.close()

    return render_template_string("""
        <h2>Projects</h2>
        <ul>
        {% for pid, pname, gname, ddl, hrs in projects %}
          <li><strong>{{ pid }} – {{ pname }}</strong> (Group: {{ gname }}) |
              Deadline: {{ ddl.strftime('%Y-%m-%d %H:%M') }} |
              Est. hrs: {{ hrs }}</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('create_project') }}">Create new project</a> |
        <a href="{{ url_for('home') }}">Home</a>
    """, projects=projects)

@app.route('/projects/new', methods=['GET', 'POST'])
def create_project():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT group_id, group_name FROM groups ORDER BY group_name;")
    groups = cur.fetchall()

    if request.method == 'POST':
        name     = request.form['project_name']
        group_id = int(request.form['group_id'])
        deadline = datetime.fromisoformat(request.form['deadline'])
        hours    = int(request.form['hours'])

        cur.execute(
            "INSERT INTO projects (project_name, group_id, deadline, estimated_hours_needed) "
            "VALUES (%s, %s, %s, %s)",
            (name, group_id, deadline, hours)
        )
        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('list_projects'))

    cur.close(); conn.close()
    return render_template_string("""
        <h2>Create Project</h2>
        <form method="POST">
            Project name: <input name="project_name" required><br>
            Group:
            <select name="group_id" required>
                {% for gid, gname in groups %}
                  <option value="{{ gid }}">{{ gname }}</option>
                {% endfor %}
            </select><br>
            Deadline: <input type="datetime-local" name="deadline" required><br>
            Estimated hours needed: <input type="number" name="hours" min="1" required><br>
            <button type="submit">Create</button>
        </form>
        <a href="{{ url_for('list_projects') }}">Back to projects</a>
    """, groups=groups)

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    app.run()
