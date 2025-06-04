from flask import Blueprint, render_template_string, request, redirect, url_for
from backend.db import get_db_connection
from datetime import datetime

bp = Blueprint('projects', __name__, url_prefix='/projects')

@bp.route('/')
def list_projects():
    conn = get_db_connection()
    cur = conn.cursor()
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
        <li>
            <strong>
                <a href="{{ url_for('schedule.project_schedule', project_id=pid) }}">
                {{ pid }} – {{ pname }}
                </a>
            </strong>
            (Group: {{ gname }}) |
            Deadline: {{ ddl.strftime('%Y-%m-%d %H:%M') }} |
            Est. hrs: {{ hrs }}
         </li>

        {% endfor %}
        </ul>
        <a href="{{ url_for('projects.create_project') }}">Create new project</a> |
        <a href="/">Home</a>
    """, projects=projects)

@bp.route('/new', methods=['GET', 'POST'])
def create_project():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT group_id, group_name FROM groups ORDER BY group_name;")
    groups = cur.fetchall()

    if request.method == 'POST':
        name = request.form['project_name']
        group_id = int(request.form['group_id'])
        deadline = datetime.fromisoformat(request.form['deadline'])
        hours = int(request.form['hours'])
        cur.execute(
            "INSERT INTO projects (project_name, group_id, deadline, estimated_hours_needed) "
            "VALUES (%s, %s, %s, %s)",
            (name, group_id, deadline, hours)
        )
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('projects.list_projects'))

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
        <a href="{{ url_for('projects.list_projects') }}">Back to projects</a>
    """, groups=groups)

@bp.route('/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT project_name, group_id, deadline, estimated_hours_needed FROM projects WHERE project_id = %s", (project_id,))
    project = cur.fetchone()

    cur.execute("SELECT group_id, group_name FROM groups ORDER BY group_name;")
    groups = cur.fetchall()

    if request.method == 'POST':
        name = request.form['project_name']
        group_id = int(request.form['group_id'])
        deadline = datetime.fromisoformat(request.form['deadline'])
        hours = int(request.form['hours'])
        cur.execute("""
            UPDATE projects
            SET project_name = %s, group_id = %s, deadline = %s, estimated_hours_needed = %s
            WHERE project_id = %s
        """, (name, group_id, deadline, hours, project_id))
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('projects.list_projects'))

    cur.close(); conn.close()
    return render_template_string("""
        <h2>Edit Project</h2>
        <form method="POST">
            Project name: <input name="project_name" value="{{ project[0] }}" required><br>
            Group:
            <select name="group_id" required>
                {% for gid, gname in groups %}
                  <option value="{{ gid }}" {% if gid == project[1] %}selected{% endif %}>{{ gname }}</option>
                {% endfor %}
            </select><br>
            Deadline: <input type="datetime-local" name="deadline" value="{{ project[2].strftime('%Y-%m-%dT%H:%M') }}" required><br>
            Estimated hours needed: <input type="number" name="hours" value="{{ project[3] }}" required><br>
            <button type="submit">Update</button>
        </form>
        <a href="{{ url_for('projects.list_projects') }}">Cancel</a>
    """, project=project, groups=groups)

@bp.route('/delete/<int:project_id>')
def delete_project(project_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('projects.list_projects'))
